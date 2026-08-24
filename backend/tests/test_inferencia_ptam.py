# @module tests.test_inferencia_ptam — o laudo PTAM alimentado pela regressão.
#
# Regras: só modelo HOMOLOGADO entra no laudo; o snapshot é congelado (versionar
# o modelo depois não muda o laudo); e o PDF reproduz os números do modelo.
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber
from routes.inferencia import router
from services.inferencia import Especificacao, estimar, serializavel
from services.inferencia import vinculo_ptam as VP
from tests.fixtures.amostra_inferencia import (AVALIANDO, ESPECIFICACAO, amostra_dicts,
                                               gerar_amostra)
from tests.test_inferencia_rotas import _CollFOU
from tests.test_trial_acesso import _Coll

USER_A, USER_B = "userA", "userB"


class _DB:
    def __init__(self):
        self.modelos_inferencia = _CollFOU()
        self.ptam_documents = _CollFOU()
        self.amostras_mercado = _Coll()

    def __getitem__(self, nome):
        return getattr(self, nome)


def _resultado():
    esp = Especificacao.from_dict(ESPECIFICACAO)
    return serializavel(estimar(gerar_amostra(), esp, AVALIANDO, quantidade_total=450))


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


def _modelo(fake, status="homologado", uid=USER_A, mid="m1"):
    r = _resultado()
    fake.modelos_inferencia.docs.append({
        "id": mid, "user_id": uid, "nome": "Modelo 03 — ln(VU)", "versao": 1,
        "status": status, "norma": "14653-2", "tipo_imovel": "urbano",
        "amostra": amostra_dicts(), "especificacao": ESPECIFICACAO,
        "avaliando": AVALIANDO, "area_total_avaliando": 450,
        "resultado": r, "enquadramento": r["enquadramento"], "graficos": {},
    })
    return r


def _ptam(fake, pid="p1", uid=USER_A, **extra):
    doc = {"id": pid, "user_id": uid, "numero_ptam": "PTAM-0001"}
    doc.update(extra)
    fake.ptam_documents.docs.append(doc)
    return doc


# ── Vínculo ──────────────────────────────────────────────────────────────────
def test_laudo_passa_a_tirar_o_valor_da_regressao(ctx):
    r = _modelo(ctx.fake)
    _ptam(ctx.fake)
    resp = ctx.post("/inferencia/modelos/m1/vincular-ptam/p1")
    assert resp.status_code == 200, resp.text

    ptam = ctx.fake.ptam_documents.docs[0]
    pred = r["predicao"]
    assert ptam["inferencia_modelo_id"] == "m1"
    assert ptam["resultado_valor_unitario"] == round(pred["valor_central"], 2)
    assert ptam["resultado_valor_total"] == round(pred["total"]["valor_central"], 2)
    # O intervalo do laudo é o IP 80% (não o IC) — é ele que define a Precisão.
    assert ptam["resultado_intervalo_inf"] == round(pred["total"]["ip80"]["inferior"], 2)
    assert ptam["resultado_intervalo_sup"] == round(pred["total"]["ip80"]["superior"], 2)
    assert ptam["grau_precisao"] == "Grau III"
    assert ptam["fundamentacao_grau"] == "Grau III"
    assert "inferência estatística" in ptam["methodology"]


def test_modelo_nao_homologado_nao_entra_no_laudo(ctx):
    for status in ("rascunho", "estimado"):
        ctx.fake.modelos_inferencia.docs.clear()
        ctx.fake.ptam_documents.docs.clear()
        _modelo(ctx.fake, status=status)
        _ptam(ctx.fake)
        r = ctx.post("/inferencia/modelos/m1/vincular-ptam/p1")
        assert r.status_code == 409
        assert "HOMOLOGADO" in r.json()["detail"]
        assert "inferencia_modelo_id" not in ctx.fake.ptam_documents.docs[0]


def test_laudo_assinado_nao_troca_de_metodo(ctx):
    _modelo(ctx.fake)
    _ptam(ctx.fake, locked=True)
    r = ctx.post("/inferencia/modelos/m1/vincular-ptam/p1")
    assert r.status_code == 409 and "assinado" in r.json()["detail"].lower()


def test_snapshot_congelado_nao_muda_se_o_modelo_for_versionado(ctx):
    _modelo(ctx.fake)
    _ptam(ctx.fake)
    ctx.post("/inferencia/modelos/m1/vincular-ptam/p1")
    snap_antes = dict(ctx.fake.ptam_documents.docs[0]["inferencia_snapshot"])

    # modelo evolui depois do laudo emitido
    ctx.fake.modelos_inferencia.docs[0]["nome"] = "Modelo 04"
    ctx.fake.modelos_inferencia.docs[0]["resultado"]["predicao"]["valor_central"] = 999.99

    snap_depois = ctx.fake.ptam_documents.docs[0]["inferencia_snapshot"]
    assert snap_depois["nome"] == snap_antes["nome"] == "Modelo 03 — ln(VU)"
    assert (snap_depois["resultado"]["predicao"]["valor_central"]
            != 999.99), "snapshot do laudo não pode seguir o modelo vivo"


def test_desvincular_volta_ao_tratamento_por_fatores(ctx):
    _modelo(ctx.fake)
    _ptam(ctx.fake)
    ctx.post("/inferencia/modelos/m1/vincular-ptam/p1")
    assert ctx.delete("/inferencia/ptam/p1/vinculo").status_code == 200
    ptam = ctx.fake.ptam_documents.docs[0]
    assert ptam["inferencia_modelo_id"] is None and ptam["inferencia_snapshot"] is None


def test_so_modelos_homologados_sao_oferecidos_ao_laudo(ctx):
    _modelo(ctx.fake, status="homologado", mid="m1")
    _modelo(ctx.fake, status="estimado", mid="m2")
    _ptam(ctx.fake)
    d = ctx.get("/inferencia/ptam/p1/modelos-disponiveis").json()
    assert [m["id"] for m in d["modelos"]] == ["m1"]


def test_isolamento_no_vinculo(ctx):
    _modelo(ctx.fake)
    _ptam(ctx.fake)
    ctx.como(USER_B)
    assert ctx.post("/inferencia/modelos/m1/vincular-ptam/p1").status_code == 404
    assert ctx.delete("/inferencia/ptam/p1/vinculo").status_code == 404


def test_laudo_de_outro_dono_nao_recebe_meu_modelo(ctx):
    _modelo(ctx.fake, uid=USER_A)
    _ptam(ctx.fake, pid="p9", uid=USER_B)          # laudo do B
    assert ctx.post("/inferencia/modelos/m1/vincular-ptam/p9").status_code == 404


# ── O PDF do laudo reproduz os números ───────────────────────────────────────
def test_pdf_do_ptam_traz_a_regressao_e_os_mesmos_numeros(ctx):
    import io as _io
    import pypdf
    from services.ptam_pdf_v2 import generate_ptam_pdf_v2

    r = _modelo(ctx.fake)
    _ptam(ctx.fake, number="PTAM-0001", property_city="Açailândia",
          imovel_area_a_considerar=450)
    ctx.post("/inferencia/modelos/m1/vincular-ptam/p1")
    ptam = dict(ctx.fake.ptam_documents.docs[0])

    blob = generate_ptam_pdf_v2(ptam)
    assert blob[:5] == b"%PDF-"
    texto = "\n".join((p.extract_text() or "")
                      for p in pypdf.PdfReader(_io.BytesIO(blob)).pages)

    # Metodologia declara o tratamento científico e os graus
    assert "inferência estatística" in texto or "inferencia estatistica" in texto
    assert "Grau III" in texto
    # Seções do tratamento: equação, pressupostos e enquadramento
    assert "ln(VU)" in texto
    assert "Durbin-Watson" in texto
    assert "Breusch-Pagan" in texto
    # E o valor impresso é o da regressão
    esperado = f"{round(r['predicao']['total']['valor_central'], 2):,.2f}" \
        .replace(",", "@").replace(".", ",").replace("@", ".")
    assert esperado.split(",")[0] in texto


def test_ptam_sem_modelo_nao_ganha_secao_nenhuma(ctx):
    """Laudo por fatores não pode mudar em nada — o bloco é condicional."""
    import io as _io
    import pypdf
    from services.ptam_pdf_v2 import generate_ptam_pdf_v2

    blob = generate_ptam_pdf_v2({"id": "p2", "number": "PTAM-0002",
                              "property_city": "Açailândia"})
    texto = "\n".join((p.extract_text() or "")
                      for p in pypdf.PdfReader(_io.BytesIO(blob)).pages)
    assert "Durbin-Watson" not in texto
    assert "Modelo de Regressão Adotado" not in texto
