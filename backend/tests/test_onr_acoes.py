# @module tests.test_onr_acoes — ações do card do Arquivo ONR (HTTP, DB falso).
#
# Paridade com os demais módulos de Topografia: baixar/ver o Dossiê, enviar por
# WhatsApp, assinar com ICP e excluir. O que os testes protegem:
#   - o Dossiê é a FONTE ÚNICA dos três caminhos (download, WhatsApp e ICP);
#   - preparar a assinatura de novo NÃO duplica registro (upsert por job);
#   - isolamento: um usuário não alcança o processo de outro por ID direto.
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber
from routes.onr_sigri import router
from tests.test_trial_acesso import _Coll

USER_A, USER_B = "userA", "userB"


class _CollDel(_Coll):
    """_Coll + delete_one (o fake compartilhado não tem; a exclusão precisa)."""
    async def delete_one(self, f):
        antes = len(self.docs)
        self.docs = [d for d in self.docs if not self._m(d, f)]
        return type("R", (), {"deleted_count": antes - len(self.docs)})()


class _DB:
    def __init__(self):
        self.onr_sigri_jobs = _CollDel()
        self.onr_assinaturas = _Coll()
        self.counters = _Coll()

    def __getitem__(self, nome):
        return getattr(self, nome)


@pytest.fixture()
def ctx(monkeypatch):
    fake = _DB()
    atual = {"uid": USER_A}
    enviados = []
    subidos = {}

    # R2 e Z-API não existem no teste — trocados por dublês que registram a chamada.
    monkeypatch.setattr("services.r2_storage.upload_bytes",
                        lambda data, key, mime=None: subidos.__setitem__(key, data))

    async def _envia(**kw):
        enviados.append(kw)
        return {"ok": True}

    monkeypatch.setattr("services.zapi_service.send_document_pdf", _envia)

    async def _integra(db, uid, fallback_zapi=False):
        return {"zapi_instance_id": "i", "zapi_token": "t", "zapi_security_token": "s"}

    monkeypatch.setattr("services.integracoes_util.carregar_integracoes", _integra)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_active_subscriber] = lambda: atual["uid"]
    with TestClient(app) as c:
        c.fake, c.enviados, c.subidos = fake, enviados, subidos
        c.como = lambda uid: atual.update({"uid": uid})
        yield c


def _job(uid=USER_A, jid="j1"):
    return {"id": jid, "user_id": uid, "numero": "ONR-2026-0001",
            "nome": "CHACARA BOA VISTA", "denominacao_imovel": "CHACARA BOA VISTA",
            "municipio": "Açailândia", "uf": "MA", "status": "rascunho",
            "matriculas": [{"matricula": "9809"}], "vertices": [], "anexos": []}


@pytest.fixture()
def job(ctx):
    ctx.fake.onr_sigri_jobs.docs.append(_job())
    return "j1"


def test_baixar_dossie(ctx, job):
    r = ctx.get(f"/topografia/onr-sigri/jobs/{job}/dossie")
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF-")
    # o nome carrega a matrícula, como na tela de detalhe
    assert "Matricula-9809" in r.headers["content-disposition"]


def test_enviar_whatsapp_manda_o_mesmo_dossie(ctx, job):
    baixado = ctx.get(f"/topografia/onr-sigri/jobs/{job}/dossie").content
    r = ctx.post(f"/topografia/onr-sigri/jobs/{job}/enviar-whatsapp",
                 json={"telefone": "55 99 98151-7964"})
    assert r.status_code == 200 and r.json()["enviado"] == "5599981517964"
    assert len(ctx.enviados) == 1
    enviado = ctx.enviados[0]
    assert enviado["pdf_bytes"][:5] == b"%PDF-"
    # Mesmo tamanho do baixado: o WhatsApp não pode mandar peça diferente da
    # que o RT protocola (os PDFs variam só na data de criação interna).
    assert abs(len(enviado["pdf_bytes"]) - len(baixado)) < 200
    assert "CHACARA BOA VISTA" in enviado["caption"]


def test_whatsapp_recusa_telefone_invalido(ctx, job):
    r = ctx.post(f"/topografia/onr-sigri/jobs/{job}/enviar-whatsapp", json={"telefone": "123"})
    assert r.status_code == 422
    assert not ctx.enviados


def test_assinar_prepara_o_dossie_e_nao_duplica_registro(ctx, job):
    r1 = ctx.post(f"/topografia/onr-sigri/jobs/{job}/assinar")
    assert r1.status_code == 200 and r1.json()["assinado"] is False
    assert r1.json()["paginas"] >= 1
    # o PDF foi para o R2 e é o Dossiê
    assert any(k.startswith(f"onr-sigri/{USER_A}/{job}/assinar/") for k in ctx.subidos)
    assert list(ctx.subidos.values())[0][:5] == b"%PDF-"

    # Reassinar regenera o PDF, mas mantém o MESMO registro (senão a lista de
    # assinaturas encheria de duplicatas a cada clique).
    r2 = ctx.post(f"/topografia/onr-sigri/jobs/{job}/assinar")
    assert r2.json()["id"] == r1.json()["id"]
    assert len(ctx.fake.onr_assinaturas.docs) == 1


def test_listar_assinaturas_reflete_o_selo(ctx, job):
    aid = ctx.post(f"/topografia/onr-sigri/jobs/{job}/assinar").json()["id"]
    assert ctx.get(f"/topografia/onr-sigri/jobs/{job}/assinaturas").json()[0]["assinado"] is False

    # o motor de assinatura (routes/assinatura) marca este campo ao selar
    for d in ctx.fake.onr_assinaturas.docs:
        if d["id"] == aid:
            d["icp_status"] = "assinado"
    recs = ctx.get(f"/topografia/onr-sigri/jobs/{job}/assinaturas").json()
    assert recs[0]["assinado"] is True and recs[0]["doc"] == "dossie"


def test_excluir_remove_o_processo(ctx, job):
    assert ctx.delete(f"/topografia/onr-sigri/jobs/{job}").status_code == 200
    assert ctx.get(f"/topografia/onr-sigri/jobs/{job}/dossie").status_code == 404


@pytest.mark.parametrize("rota,metodo", [
    ("dossie", "get"), ("assinar", "post"), ("assinaturas", "get"),
])
def test_processo_de_outro_usuario_nao_e_alcancavel(ctx, job, rota, metodo):
    ctx.como(USER_B)
    r = getattr(ctx, metodo)(f"/topografia/onr-sigri/jobs/{job}/{rota}")
    assert r.status_code == 404
