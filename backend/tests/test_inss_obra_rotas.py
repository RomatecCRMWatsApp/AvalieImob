# Rotas /inss-obra com DB e R2 falsos: cadastro → simulação → PDF → checklist → isolamento.
import copy

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber


class _Cur:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, k, d=1):
        self.docs.sort(key=lambda x: x.get(k) or "", reverse=d == -1)
        return self

    async def to_list(self, n=None):
        return self.docs


class _Coll:
    def __init__(self):
        self.docs = []

    def _m(self, d, f):
        return all(d.get(k) == v for k, v in f.items())

    def find(self, f=None):
        return _Cur([copy.deepcopy(d) for d in self.docs if self._m(d, f or {})])

    async def find_one(self, f):
        for d in self.docs:
            if self._m(d, f):
                return copy.deepcopy(d)
        return None

    async def insert_one(self, doc):
        self.docs.append(copy.deepcopy(doc))

    async def delete_one(self, f):
        self.docs = [d for d in self.docs if not self._m(d, f)]

    async def update_one(self, f, upd):
        for d in self.docs:
            if self._m(d, f):
                for k, v in (upd.get("$set") or {}).items():
                    alvo = d
                    partes = k.split(".")
                    for p in partes[:-1]:
                        alvo = alvo.setdefault(p, {})
                    alvo[partes[-1]] = copy.deepcopy(v)
                for k in (upd.get("$unset") or {}):
                    partes = k.split(".")
                    alvo = d
                    for p in partes[:-1]:
                        alvo = alvo.get(p, {})
                    alvo.pop(partes[-1], None)
                for k, v in (upd.get("$push") or {}).items():
                    d.setdefault(k, []).append(copy.deepcopy(v))
                return


class _Counters:
    def __init__(self):
        self.n = {}

    async def find_one_and_update(self, f, upd, upsert=False, return_document=True):
        self.n[f["_id"]] = self.n.get(f["_id"], 0) + 1
        return {"seq": self.n[f["_id"]]}


class _DB:
    def __init__(self):
        self.inss_obras = _Coll()
        self.counters = _Counters()
        self.perfil_avaliador = _Coll()
        self.users = _Coll()

    def __getitem__(self, k):
        return getattr(self, k)


@pytest.fixture()
def app(monkeypatch):
    import routes.inss_obra as R
    store = {}
    monkeypatch.setattr(R.r2_storage, "upload_bytes", lambda data, key, ct: store.__setitem__(key, data))
    monkeypatch.setattr(R.r2_storage, "download_bytes", lambda key: store[key])

    async def _sem_logo(db, uid):
        return None
    monkeypatch.setattr(R, "_logo", _sem_logo)
    fake = _DB()
    a = FastAPI()
    a.include_router(R.router)
    a.dependency_overrides[get_db] = lambda: fake
    usuario = {"uid": "u1"}
    a.dependency_overrides[get_active_subscriber] = lambda: usuario["uid"]
    with TestClient(a) as c:
        c.usuario = usuario
        yield c


OBRA = {
    "cliente_nome": "Maria Teste", "cpf_cnpj": "123.456.789-09", "responsavel": "PF",
    "municipio": "Açailândia", "uf": "MA", "data_inicio": "2025-02-01", "data_fim": "2025-12-15",
    "data_afericao": "2026-11-14",
    "areas": [{"destinacao": "residencial_unifamiliar", "categoria": "obra_nova", "tipo": "alvenaria",
               "classe": "principal", "area_m2": 150},
              {"destinacao": "residencial_unifamiliar", "categoria": "obra_nova", "tipo": "alvenaria",
               "classe": "complementar_descoberta", "area_m2": 30}],
    "vau": {"residencial_unifamiliar": "2500,00"}, "vau_competencia": "11/2026",
}


def test_fluxo_completo(app):
    r = app.post("/inss-obra/obras", json=OBRA)
    assert r.status_code == 201, r.text
    oid = r.json()["id"]
    assert r.json()["numero"].startswith("INSS-")
    assert any(p["chave"] == "cno" for p in r.json()["prazos"])

    r = app.post(f"/inss-obra/obras/{oid}/simular")
    assert r.status_code == 200, r.text
    res = r.json()["resultado"]
    # 150×0,89×2500 = 333.750 ; 30×0,25×2500 = 18.750 ; FS 180 m² = 40% ; 20% M.O.
    assert res["cod_total"] == "352500.00"
    assert res["rmt_total"] == "28200.00"
    assert res["total"] == "10377.60"  # 28.200 × 36,8%

    r = app.post(f"/inss-obra/obras/{oid}/simular")  # segunda simulação não apaga a primeira
    assert app.get(f"/inss-obra/obras/{oid}").json()["simulacoes_qtd"] == 2

    r = app.get(f"/inss-obra/obras/{oid}/pdf")
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"

    r = app.post(f"/inss-obra/obras/{oid}/checklist/cno",
                 files={"file": ("cno.pdf", b"%PDF-1.4 teste", "application/pdf")})
    assert r.status_code == 200
    item = next(i for i in r.json()["checklist_itens"] if i["chave"] == "cno")
    assert item["status"] == "ok" and "key" not in item
    assert app.get(f"/inss-obra/obras/{oid}/checklist/cno/arquivo").content == b"%PDF-1.4 teste"

    r = app.post(f"/inss-obra/obras/{oid}/sero-oficial", json={"total": "10.380,15"})
    assert r.json()["sero_oficial"]["total"] == "10380.15"


def test_erro_de_dado_vira_422(app):
    oid = app.post("/inss-obra/obras", json={**OBRA, "vau": {}}).json()["id"]
    r = app.post(f"/inss-obra/obras/{oid}/simular")
    assert r.status_code == 422 and "VAU" in r.json()["detail"]


def test_isolamento_entre_contas(app):
    oid = app.post("/inss-obra/obras", json=OBRA).json()["id"]
    app.usuario["uid"] = "outro"
    assert app.get(f"/inss-obra/obras/{oid}").status_code == 404
    assert app.post(f"/inss-obra/obras/{oid}/simular").status_code == 404
    assert app.get(f"/inss-obra/obras/{oid}/pdf").status_code == 404
    assert app.get("/inss-obra/obras").json() == []
