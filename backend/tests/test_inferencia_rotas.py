# @module tests.test_inferencia_rotas — API do tratamento científico (HTTP, DB falso).
#
# Cobre os três critérios acrescentados na portagem (MD §12):
#   - modelo homologado não pode ser editado;
#   - o relatório reproduz EXATAMENTE os números da estimativa;
#   - isolamento: usuário A não acessa modelo do usuário B por ID direto.
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber
from routes.inferencia import router
from tests.fixtures.amostra_inferencia import (AVALIANDO, ESPECIFICACAO, amostra_dicts)
from tests.test_trial_acesso import _Coll


class _DB:
    def __init__(self):
        self.modelos_inferencia = _CollFOU()
        self.amostras_mercado = _Coll()

    def __getitem__(self, nome):           # o router usa db["modelos_inferencia"]
        return getattr(self, nome)


class _CollFOU(_Coll):
    """_Coll + find_one_and_update (o módulo grava sempre atomicamente)."""
    async def find_one_and_update(self, f, upd, return_document=None, upsert=False):
        d = next((d for d in self.docs if self._m(d, f)), None)
        if not d:
            return None
        d.update(upd.get("$set", {}))
        return dict(d)

    async def delete_one(self, f):
        antes = len(self.docs)
        self.docs = [d for d in self.docs if not self._m(d, f)]
        return type("R", (), {"deleted_count": antes - len(self.docs)})()

    def find(self, f=None, projecao=None, *a, **kw):
        return super().find(f)

    async def count_documents(self, f=None):
        return len([d for d in self.docs if self._m(d, f or {})])


USER_A, USER_B = "userA", "userB"


@pytest.fixture()
def ctx():
    fake = _DB()
    atual = {"uid": USER_A}
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_active_subscriber] = lambda: atual["uid"]
    with TestClient(app) as c:
        c.fake = fake
        c.como = lambda uid: atual.update({"uid": uid})
        yield c


def _criar(c, **extra) -> str:
    body = {"nome": "Modelo 01", "tipo_imovel": "urbano",
            "amostra": amostra_dicts(), "especificacao": ESPECIFICACAO,
            "avaliando": AVALIANDO, "area_total_avaliando": 450}
    body.update(extra)
    r = c.post("/inferencia/modelos", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── Ciclo básico ─────────────────────────────────────────────────────────────
def test_criar_estimar_e_enquadrar(ctx):
    mid = _criar(ctx)
    r = ctx.post(f"/inferencia/modelos/{mid}/estimar")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "estimado"
    assert d["resultado"]["n"] == 32 and d["resultado"]["k"] == 4
    assert d["enquadramento"]["grau_fundamentacao"] == "III"
    assert d["enquadramento"]["grau_precisao"] == "III"
    assert d["resultado"]["predicao"]["valor_central"] > 0


def test_opcoes_traz_transformacoes_e_limites_da_norma(ctx):
    d = ctx.get("/inferencia/opcoes").json()
    assert {t["valor"] for t in d["transformacoes"]} >= {"identidade", "ln", "raiz"}
    urbana = next(n for n in d["normas"] if n["valor"] == "14653-2")
    assert urbana["params"]["amplitude_ip80_max"]["III"] == 0.30


def test_micronumerosidade_responde_422_com_explicacao(ctx):
    mid = _criar(ctx, amostra=amostra_dicts()[:10])
    r = ctx.post(f"/inferencia/modelos/{mid}/estimar")
    assert r.status_code == 422 and "Micronumerosidade" in r.json()["detail"]


def test_descarte_exige_motivo(ctx):
    mid = _criar(ctx)
    r = ctx.patch(f"/inferencia/modelos/{mid}/amostra",
                  json={"itens": [{"dado_id": "D01", "utilizado": False}]})
    assert r.status_code == 422 and "motivo" in r.json()["detail"].lower()

    r = ctx.patch(f"/inferencia/modelos/{mid}/amostra",
                  json={"itens": [{"dado_id": "D01", "utilizado": False,
                                   "motivo_descarte": "oferta desatualizada"}]})
    assert r.status_code == 200
    d = ctx.post(f"/inferencia/modelos/{mid}/estimar").json()
    assert d["resultado"]["n"] == 31


def test_alterar_especificacao_invalida_o_resultado_anterior(ctx):
    mid = _criar(ctx)
    ctx.post(f"/inferencia/modelos/{mid}/estimar")
    nova = {**ESPECIFICACAO, "regressores": ESPECIFICACAO["regressores"][:3]}
    r = ctx.patch(f"/inferencia/modelos/{mid}/especificacao", json={"especificacao": nova})
    assert r.status_code == 200
    assert r.json()["resultado"] is None and r.json()["status"] == "rascunho"


# ── Homologação: imutabilidade ───────────────────────────────────────────────
def test_homologar_exige_estimativa_e_checklist(ctx):
    mid = _criar(ctx)
    assert ctx.post(f"/inferencia/modelos/{mid}/homologar", json={}).status_code == 422

    ctx.post(f"/inferencia/modelos/{mid}/estimar")
    r = ctx.post(f"/inferencia/modelos/{mid}/homologar", json={"checklist_manual": {}})
    assert r.status_code == 422 and "checklist" in r.json()["detail"].lower()


def test_modelo_homologado_e_imutavel(ctx):
    mid = _criar(ctx)
    ctx.post(f"/inferencia/modelos/{mid}/estimar")
    r = ctx.post(f"/inferencia/modelos/{mid}/homologar", json={"checklist_manual": {
        "Caracterizacao do imovel avaliando": True,
        "Grau de identificacao e conferencia dos dados de mercado": True}})
    assert r.status_code == 200 and r.json()["status"] == "homologado"

    # Nenhuma porta de escrita pode aceitar alteração depois disso.
    assert ctx.patch(f"/inferencia/modelos/{mid}/especificacao",
                     json={"especificacao": ESPECIFICACAO}).status_code == 409
    assert ctx.patch(f"/inferencia/modelos/{mid}/amostra", json={
        "itens": [{"dado_id": "D01", "utilizado": False, "motivo_descarte": "x"}]
    }).status_code == 409
    assert ctx.post(f"/inferencia/modelos/{mid}/estimar").status_code == 409
    assert ctx.delete(f"/inferencia/modelos/{mid}").status_code == 409
    assert ctx.post(f"/inferencia/modelos/{mid}/homologar",
                    json={"checklist_manual": {}}).status_code == 409


def test_nova_versao_preserva_a_anterior(ctx):
    mid = _criar(ctx)
    ctx.post(f"/inferencia/modelos/{mid}/estimar")
    ctx.post(f"/inferencia/modelos/{mid}/homologar", json={"checklist_manual": {
        "Caracterizacao do imovel avaliando": True,
        "Grau de identificacao e conferencia dos dados de mercado": True}})
    r = ctx.post(f"/inferencia/modelos/{mid}/nova-versao")
    assert r.status_code == 201
    nova = r.json()
    assert nova["id"] != mid and nova["versao"] == 2
    assert nova["status"] == "rascunho" and nova["origem_versao_id"] == mid
    # a homologada continua intacta
    assert ctx.get(f"/inferencia/modelos/{mid}").json()["status"] == "homologado"


def test_predizer_em_modelo_homologado_nao_altera_o_registro(ctx):
    mid = _criar(ctx)
    ctx.post(f"/inferencia/modelos/{mid}/estimar")
    ctx.post(f"/inferencia/modelos/{mid}/homologar", json={"checklist_manual": {
        "Caracterizacao do imovel avaliando": True,
        "Grau de identificacao e conferencia dos dados de mercado": True}})
    antes = ctx.get(f"/inferencia/modelos/{mid}").json()
    r = ctx.post(f"/inferencia/modelos/{mid}/predizer",
                 json={"avaliando": {**AVALIANDO, "area": 500}})
    assert r.status_code == 200 and r.json()["predicao"]["valor_central"] > 0
    depois = ctx.get(f"/inferencia/modelos/{mid}").json()
    assert depois["avaliando"] == antes["avaliando"]
    assert depois["resultado"]["predicao"] == antes["resultado"]["predicao"]


# ── Relatório reproduz os números da tela ────────────────────────────────────
def test_relatorio_reproduz_exatamente_os_numeros_da_estimativa(ctx):
    mid = _criar(ctx)
    estim = ctx.post(f"/inferencia/modelos/{mid}/estimar").json()
    rel = ctx.get(f"/inferencia/modelos/{mid}/relatorio").json()

    assert rel["predicao"]["valor_central"] == estim["resultado"]["predicao"]["valor_central"]
    assert rel["predicao"]["ip80"] == estim["resultado"]["predicao"]["ip80"]
    assert rel["estatisticas"]["r2"] == estim["resultado"]["r2"]
    assert rel["equacao"] == estim["resultado"]["equacao"]
    assert (rel["enquadramento"]["grau_fundamentacao"]
            == estim["enquadramento"]["grau_fundamentacao"])
    assert len(rel["regressores"]) == len(estim["resultado"]["regressores"])


def test_relatorio_exige_estimativa(ctx):
    mid = _criar(ctx)
    assert ctx.get(f"/inferencia/modelos/{mid}/relatorio").status_code == 422


def test_pdf_do_modelo_estimado(ctx):
    mid = _criar(ctx)
    ctx.post(f"/inferencia/modelos/{mid}/estimar")
    r = ctx.get(f"/inferencia/modelos/{mid}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"


# ── Isolamento entre contas ──────────────────────────────────────────────────
def test_usuario_b_nao_acessa_modelo_do_usuario_a(ctx):
    mid = _criar(ctx)
    ctx.post(f"/inferencia/modelos/{mid}/estimar")

    ctx.como(USER_B)
    assert ctx.get(f"/inferencia/modelos/{mid}").status_code == 404
    assert ctx.post(f"/inferencia/modelos/{mid}/estimar").status_code == 404
    assert ctx.get(f"/inferencia/modelos/{mid}/relatorio").status_code == 404
    assert ctx.get(f"/inferencia/modelos/{mid}/pdf").status_code == 404
    assert ctx.delete(f"/inferencia/modelos/{mid}").status_code == 404
    assert ctx.patch(f"/inferencia/modelos/{mid}/especificacao",
                     json={"especificacao": ESPECIFICACAO}).status_code == 404
    assert ctx.get("/inferencia/modelos").json() == []


def test_listagem_so_traz_os_modelos_do_dono(ctx):
    _criar(ctx)
    ctx.como(USER_B)
    _criar(ctx, nome="Do B")
    assert [m["nome"] for m in ctx.get("/inferencia/modelos").json()] == ["Do B"]
    ctx.como(USER_A)
    assert [m["nome"] for m in ctx.get("/inferencia/modelos").json()] == ["Modelo 01"]
