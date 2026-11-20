# @module tests.test_privacidade — canal de titulares, exportação escopada e trilha.
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_admin_user, get_current_user_id
from services import privacidade as PV


class _Cur:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, k, d=1):
        self.docs = sorted(self.docs, key=lambda x: x.get(k) or datetime.min, reverse=d < 0)
        return self

    async def to_list(self, n=None):
        return [dict(x) for x in self.docs[:n]]


class _Coll:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def _m(self, d, f):
        return all(d.get(k) == v for k, v in (f or {}).items())

    def find(self, f=None):
        return _Cur([d for d in self.docs if self._m(d, f)])

    async def find_one(self, f):
        return next((dict(d) for d in self.docs if self._m(d, f)), None)

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, f, upd):
        for d in self.docs:
            if self._m(d, f):
                d.update(upd.get("$set", {}))
                for k, v in upd.get("$push", {}).items():
                    d.setdefault(k, []).append(v)
                return


class _DB:
    def __init__(self):
        self.cols = {
            "users": _Coll([
                {"id": "u1", "name": "Ana Souza", "email": "ana@ex.com", "password_hash": "HASH-SECRETO",
                 "reset_token_hash": "x"},
                {"id": "u2", "name": "Beto", "email": "beto@ex.com", "password_hash": "OUTRO"},
            ]),
            "clients": _Coll([
                {"user_id": "u1", "name": "Cliente da Ana", "doc": "123"},
                {"user_id": "u2", "name": "Cliente do Beto", "doc": "999"},
            ]),
            "ptam_documents": _Coll([
                {"user_id": "u1", "numero": "PTAM-1", "link_publico_token": "TOKEN-SECRETO",
                 "fotos": [{"data_b64": "A" * 500}]},
            ]),
            "certificados": _Coll([{"user_id": "u1", "pfx_encrypted": "PFX"}]),
            "credenciais": _Coll([{"user_id": "u1", "api_key": "K"}]),
            "sys_config": _Coll(),
            PV.COL_PEDIDOS: _Coll(),
        }

    def __getattr__(self, nome):
        return self.cols.setdefault(nome, _Coll())

    def __getitem__(self, nome):
        return self.cols.setdefault(nome, _Coll())

    async def list_collection_names(self):
        return list(self.cols)


def _app(fake, uid="u1", admin=False):
    from routes.privacidade import admin_router, router
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_current_user_id] = lambda: uid
    if admin:
        app.dependency_overrides[get_admin_user] = lambda: "admin1"
    return TestClient(app)


def test_exportacao_so_traz_dados_da_propria_conta_e_sem_segredos():
    fake = _DB()
    r = _app(fake, uid="u1").get("/api/privacidade/meus-dados")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert r.headers["cache-control"] == "no-store"
    corpo = r.text
    assert "Cliente da Ana" in corpo and "PTAM-1" in corpo
    # outra conta nunca aparece
    assert "Cliente do Beto" not in corpo and "beto@ex.com" not in corpo
    # segredos e binários não saem
    for segredo in ("HASH-SECRETO", "TOKEN-SECRETO", "PFX", '"K"', "AAAAAAAAAA"):
        assert segredo not in corpo
    assert "certificados" not in r.json()["colecoes"] and "credenciais" not in r.json()["colecoes"]


def test_pedido_publico_sem_conta_gera_protocolo_e_nao_apaga_nada():
    fake = _DB()
    c = _app(fake)
    r = c.post("/api/privacidade/solicitacao", json={
        "tipo": "eliminacao", "nome": "Carla Lima", "email": "carla@ex.com", "relacao": "titular",
        "descricao": "Sou cliente de um avaliador e quero saber quais dados meus estão no sistema."})
    assert r.status_code == 200 and r.json()["protocolo"].startswith("PRIV-")
    p = fake.cols[PV.COL_PEDIDOS].docs[0]
    assert p["origem"] == "publico" and p["identidade"] == "pendente" and p["status"] == "recebida"
    assert len(fake.cols["clients"].docs) == 2  # nada foi apagado


def test_pedido_publico_valida_e_descarta_robo():
    fake = _DB()
    c = _app(fake)
    assert c.post("/api/privacidade/solicitacao", json={
        "tipo": "eliminacao", "nome": "X", "email": "nao-e-email", "relacao": "titular",
        "descricao": "curta"}).status_code == 422
    r = c.post("/api/privacidade/solicitacao", json={
        "tipo": "eliminacao", "nome": "Robô Spam", "email": "r@ex.com", "relacao": "titular",
        "descricao": "texto qualquer longo", "website": "http://spam"})
    assert r.status_code == 200 and r.json()["protocolo"] is None
    assert fake.cols[PV.COL_PEDIDOS].docs == []


def test_encerrar_conta_abre_pedido_sem_apagar_carteira():
    fake = _DB()
    c = _app(fake, uid="u1")
    r = c.post("/api/privacidade/minhas-solicitacoes",
               json={"tipo": "exclusao_conta", "descricao": "Quero encerrar minha conta no sistema."})
    assert r.status_code == 200 and r.json()["status"] == "recebida"
    p = fake.cols[PV.COL_PEDIDOS].docs[0]
    assert p["user_id"] == "u1" and p["identidade"] == "verificada_login"
    assert any(d["user_id"] == "u1" for d in fake.cols["clients"].docs)
    # a outra conta não vê o pedido
    assert _app(fake, uid="u2").get("/api/privacidade/minhas-solicitacoes").json()["solicitacoes"] == []


def test_admin_muda_status_com_trilha_e_recusa_status_invalido():
    fake = _DB()
    pedido = PV.montar_pedido({"tipo": "correcao", "nome": "Dani Melo", "email": "d@ex.com",
                               "relacao": "titular", "descricao": "Meu telefone está errado."})
    fake.cols[PV.COL_PEDIDOS].docs.append(pedido)
    c = _app(fake, admin=True)
    assert c.patch(f"/api/admin/privacidade/solicitacoes/{pedido['protocolo']}",
                   json={"status": "apagado"}).status_code == 422
    r = c.patch(f"/api/admin/privacidade/solicitacoes/{pedido['protocolo']}",
                json={"status": "atendida", "nota": "Telefone corrigido no cadastro."})
    assert r.status_code == 200
    p = fake.cols[PV.COL_PEDIDOS].docs[0]
    assert p["status"] == "atendida" and p["concluida_em"]
    assert [h["status"] for h in p["historico"]] == ["recebida", "atendida"]


def test_admin_exige_perfil_admin():
    fake = _DB()
    r = _app(fake).get("/api/admin/privacidade/solicitacoes")
    assert r.status_code in (401, 403)
