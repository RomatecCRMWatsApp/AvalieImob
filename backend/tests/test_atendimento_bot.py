# @module tests.test_atendimento_bot — robô de atendimento do site (qualificação + rotas).
import re
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_admin_user
from services.atendimento import qualificacao as Q
from services.atendimento import conhecimento as KB


# ── Fake Mongo mínimo ────────────────────────────────────────────────────────
def _get(doc, path):
    cur = doc
    for p in path.split("."):
        if isinstance(cur, list):
            return [x.get(p) for x in cur if isinstance(x, dict)]
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def _cmp(v, cond):
    if isinstance(cond, dict):
        for op, x in cond.items():
            if op == "$gte" and not (v is not None and v >= x): return False
            if op == "$gt" and not (v is not None and v > x): return False
            if op == "$ne" and v == x: return False
            if op == "$nin" and v in x: return False
            if op == "$regex":
                vals = v if isinstance(v, list) else [v]
                if not any(re.search(x, str(i or ""), re.I) for i in vals): return False
            if op == "$options": continue
        return True
    return v == cond


def _match(doc, f):
    for k, cond in f.items():
        if k == "$or":
            if not any(_match(doc, sub) for sub in cond): return False
        elif not _cmp(_get(doc, k), cond):
            return False
    return True


def _setp(doc, path, val):
    ps = path.split(".")
    for p in ps[:-1]:
        doc = doc.setdefault(p, {})
    doc[ps[-1]] = val


class _R:
    def __init__(self, m=0, d=0): self.matched_count, self.deleted_count = m, d


class _Cur:
    def __init__(self, docs): self.docs = docs
    def sort(self, k, d): self.docs.sort(key=lambda x: x.get(k) or datetime.min, reverse=d < 0); return self
    def skip(self, n): self.docs = self.docs[n:]; return self
    def limit(self, n): self.docs = self.docs[:n]; return self
    def __aiter__(self): self._i = iter(self.docs); return self
    async def __anext__(self):
        try: return next(self._i)
        except StopIteration: raise StopAsyncIteration


class _Coll:
    def __init__(self): self.docs = []
    async def find_one(self, f, *a): return next((d for d in self.docs if _match(d, f)), None)
    async def insert_one(self, d): self.docs.append(dict(d))
    async def count_documents(self, f): return sum(1 for d in self.docs if _match(d, f))
    def find(self, f, proj=None): return _Cur([d for d in self.docs if _match(d, f)])
    async def delete_one(self, f):
        d = await self.find_one(f)
        if d: self.docs.remove(d); return _R(d=1)
        return _R()
    async def update_one(self, f, u):
        d = await self.find_one(f)
        if not d: return _R()
        for k, v in u.get("$set", {}).items(): _setp(d, k, v)
        for k, v in u.get("$inc", {}).items(): _setp(d, k, (_get(d, k) or 0) + v)
        for k, v in u.get("$push", {}).items(): d.setdefault(k, []).append(v)
        return _R(m=1)
    async def find_one_and_update(self, f, u):
        d = await self.find_one(f)
        if d:
            antes = dict(d); await self.update_one({"id": d["id"]}, u); return antes
        return None


class _DB:
    def __init__(self): self.c = {}
    def __getitem__(self, n): return self.c.setdefault(n, _Coll())
    def __getattr__(self, n):
        if n.startswith("_") or n == "c": raise AttributeError(n)
        return self[n]


# ── Funções puras ────────────────────────────────────────────────────────────
def test_base_tem_os_assuntos_e_precos():
    p = KB.system_prompt()
    for termo in ("PTAM", "Grau III", "SIGEF", "ONR", "Provimento CNJ 195/2025", "usucapi",
                  "R$ 189,90", "R$ 449,90", "R$ 1.199,00", "3 dias", "/cadastro", "META"):
        assert termo.lower() in p.lower(), termo


def test_detecta_assuntos_e_gel_vira_georref():
    assert "georref" in Q.detectar_assuntos("vocês fazem GEL de fazenda?")
    assert "onr" in Q.detectar_assuntos("como gero o arquivo do ONR")
    assert "pericia" in Q.detectar_assuntos("preciso de perícia judicial")


def test_separa_meta_e_nao_vaza_para_o_cliente():
    txt, meta = Q.separar_meta('Olá! Quer testar?\n<<META {"estagio": "interessado", "perfil": "profissional", "assuntos": ["ptam"]}>>')
    assert txt == "Olá! Quer testar?" and meta["estagio"] == "interessado"
    txt2, meta2 = Q.separar_meta("Resposta <<META {quebrado")
    assert "META" not in txt2 and meta2 == {}


def test_extrai_contato_livre():
    c = Q.extrair_contato("me chamo Maria Souza, meu zap é (99) 98515-7964 e email maria@x.com")
    assert c == {"nome": "Maria Souza", "whatsapp": "5599985157964", "email": "maria@x.com"}


def test_estagio_so_sobe():
    assert Q.subir_estagio("qualificado", "curioso") == "qualificado"
    av = Q.avaliar({"estagio": "interessado"}, "ok", {"estagio": "curioso"})
    assert av["estagio"] == "interessado"


def test_quem_quer_contratar_vira_qualificado_e_pede_contato():
    av = Q.avaliar({}, "quero contratar um laudo do meu terreno", {})
    assert av["estagio"] == "qualificado" and av["perfil"] == "cliente_servico" and av["pedir_contato"]


def test_so_encaminha_quente_com_contato_e_uma_vez():
    assert not Q.deve_encaminhar({"estagio": "qualificado"})
    assert Q.deve_encaminhar({"estagio": "qualificado", "whatsapp": "5599"})
    assert not Q.deve_encaminhar({"estagio": "qualificado", "whatsapp": "5599", "notificado_em": 1})
    assert not Q.deve_encaminhar({"estagio": "interessado", "whatsapp": "5599"})


# ── Rotas ────────────────────────────────────────────────────────────────────
@pytest.fixture()
def cli(monkeypatch):
    from routes import atendimento as A
    from services.ratelimit import pub_limiter
    pub_limiter.enabled = False
    fake = _DB()
    avisos = []

    async def ia(msgs, max_tokens=700):
        ultima = msgs[-1]["content"].lower()
        if "contratar" in ultima:
            return ('Perfeito! Me passa seu nome e WhatsApp?\n<<META {"estagio": "qualificado", '
                    '"perfil": "cliente_servico", "assuntos": ["georref"], "pedir_contato": true}>>'), "fake"
        return ('O georreferenciamento gera o dossiê completo. Você é profissional?\n<<META {"estagio": '
                '"curioso", "perfil": "indefinido", "assuntos": ["georref"]}>>'), "fake"

    async def notificar(db, texto):
        avisos.append(texto)

    async def cfg(db):
        return {"email_lead_ativo": False}

    monkeypatch.setattr("routes.ai._roma_ia_cascata", ia)
    monkeypatch.setattr("routes.avaliacao_publica._notificar_avaliador", notificar)
    monkeypatch.setattr("services.notificacao_lead.carregar_config", cfg)
    app = FastAPI()
    app.include_router(A.router)
    app.include_router(A.admin_router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_admin_user] = lambda: "admin1"
    with TestClient(app) as c:
        c.fake, c.avisos = fake, avisos
        yield c
    pub_limiter.enabled = True


SID = "sessao_teste_123"


def test_fluxo_completo_curioso_qualificado_encaminhado(cli):
    r = cli.post("/atendimento/mensagem", json={"sessao_id": SID, "mensagem": "o que é o GEL de vocês?"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert "META" not in d["resposta"] and d["estagio"] == "curioso"
    assert not cli.avisos

    d = cli.post("/atendimento/mensagem", json={"sessao_id": SID, "mensagem": "quero contratar o georreferenciamento da minha fazenda"}).json()
    assert d["estagio"] == "qualificado" and d["pedir_contato"] and not d["tem_contato"]
    assert not cli.avisos  # ainda sem contato → não avisa

    d = cli.post("/atendimento/contato", json={"sessao_id": SID, "nome": "joão silva", "whatsapp": "(99) 98888-7777",
                                                "consentimento": True}).json()
    assert d["tem_contato"] and len(cli.avisos) == 1
    assert "wa.me/5599988887777" in cli.avisos[0] and "Georreferenciamento" in cli.avisos[0]
    assert any(a["tipo"] == "whatsapp" for a in d["acoes"])

    # 2º contato não reavisa
    cli.post("/atendimento/contato", json={"sessao_id": SID, "nome": "João", "whatsapp": "99988887777", "consentimento": True})
    assert len(cli.avisos) == 1


def test_contato_exige_lgpd_e_fone_valido(cli):
    assert cli.post("/atendimento/contato", json={"sessao_id": SID, "nome": "Ana", "whatsapp": "99988887777"}).status_code == 422
    assert cli.post("/atendimento/contato", json={"sessao_id": SID, "nome": "Ana", "whatsapp": "123456789",
                                                  "consentimento": True}).status_code == 422


def test_sessao_invalida_e_ia_fora_cai_no_offline(cli, monkeypatch):
    assert cli.post("/atendimento/mensagem", json={"sessao_id": "../x", "mensagem": "oi"}).status_code == 422

    async def quebra(*a, **k):
        raise RuntimeError("sem provedor")
    monkeypatch.setattr("routes.ai._roma_ia_cascata", quebra)
    d = cli.post("/atendimento/mensagem", json={"sessao_id": "offline_123456", "mensagem": "quanto custa o plano?"}).json()
    assert d["provedor"] == "offline" and "189,90" in d["resposta"] and d["estagio"] == "interessado"
    assert any(a["tipo"] == "cadastro" for a in d["acoes"])


def test_painel_admin_conta_funil(cli):
    cli.post("/atendimento/mensagem", json={"sessao_id": "aaaaaaaa1", "mensagem": "o que é o ONR?"})
    cli.post("/atendimento/mensagem", json={"sessao_id": "bbbbbbbb2", "mensagem": "quero contratar"})
    cli.post("/atendimento/evento", json={"sessao_id": "aaaaaaaa1", "evento": "clique_cadastro"})
    st = cli.get("/admin/atendimento/stats?dias=30").json()
    assert st["conversas"] == 2 and st["mensagens_recebidas"] == 2
    assert st["por_estagio"]["qualificado"] == 1 and st["por_estagio"]["interessado"] == 1
    assert st["cliques"]["cadastro"] == 1
    lista = cli.get("/admin/atendimento/conversas?estagio=qualificado").json()
    assert lista["total"] == 1 and lista["items"][0]["id"] == "bbbbbbbb2"
    det = cli.get("/admin/atendimento/conversas/bbbbbbbb2").json()
    assert [m["role"] for m in det["mensagens"]] == ["assistant", "user", "assistant"]
    assert cli.patch("/admin/atendimento/conversas/bbbbbbbb2", json={"status_admin": "em_contato"}).status_code == 200
    assert cli.patch("/admin/atendimento/conversas/bbbbbbbb2", json={"status_admin": "xx"}).status_code == 422


def test_cadastro_marca_conversao(cli):
    import asyncio
    from routes.atendimento import marcar_conversao
    cli.post("/atendimento/mensagem", json={"sessao_id": "conv_12345678", "mensagem": "quanto custa?"})
    asyncio.run(marcar_conversao(cli.fake, "conv_12345678", "u1", "a@b.com"))
    st = cli.get("/admin/atendimento/stats?dias=30").json()
    assert st["por_estagio"]["convertido"] == 1 and st["taxa_conversao"] == 100.0
