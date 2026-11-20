# @module tests.test_ptam_lacre_e_links_publicos — lacre/versão do PTAM e links públicos.
#
# Lacre: a versão lacrada é imutável. Editar o PTAM depois do lacre cria versão nova,
# e a lacrada continua com o mesmo snapshot e o mesmo SHA-256 (verificação íntegra).
# Adulterar o snapshot gravado faz a verificação acusar.
#
# Links públicos (PTAM e contrato): token errado ou link desativado → 404; só o token
# certo com o link ativo abre. (O noindex de /laudo/{token} já é coberto em
# test_seo_html.test_telas_de_conta_noindex_sem_bloco.)
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber, get_authenticated_user
from tests.fake_mongo import FakeDB

DONO = "dono"
PID = "ptam-1"
TOKEN = "tok-certo-123"


def _cliente(modulo, fake):
    import importlib
    app = FastAPI()
    app.include_router(importlib.import_module(modulo).router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_active_subscriber] = lambda: DONO
    app.dependency_overrides[get_authenticated_user] = lambda: DONO
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def ptam():
    fake = FakeDB()
    fake.ptam_documents.docs.append({
        "id": PID, "user_id": DONO, "numero_ptam": "0007",
        "property_label": "Casa da Rua A", "finalidade": "venda",
    })
    with _cliente("routes.ptam", fake) as c:
        c.fake = fake
        yield c


def _lacrar(c):
    r = c.post(f"/ptam/{PID}/lacrar", json={"observacao": "entrega ao cliente"})
    assert r.status_code == 200, r.text
    return r.json()


def test_lacre_grava_snapshot_e_verifica_integro(ptam):
    lac = _lacrar(ptam)
    vid = lac["versao"]["id"]
    assert lac["numero_lacre"].startswith("PTAM-") and lac["numero_lacre"].endswith("-v1")
    doc = ptam.fake.ptam_documents.docs[0]
    assert doc["lacrado"] is True and doc["hash_lacrado"] == lac["hash_sha256"]

    r = ptam.get(f"/ptam/{PID}/verificar/{vid}")
    assert r.status_code == 200 and r.json()["integro"] is True


def test_editar_depois_do_lacre_cria_versao_e_preserva_a_lacrada(ptam):
    lac = _lacrar(ptam)
    vid, hash_lacre = lac["versao"]["id"], lac["hash_sha256"]

    r = ptam.put(f"/ptam/{PID}", json={"property_label": "Casa da Rua A — reformada",
                                       "finalidade": "venda"})
    assert r.status_code == 200, r.text
    assert r.json()["property_label"] == "Casa da Rua A — reformada"

    versoes = ptam.get(f"/ptam/{PID}/versoes").json()
    assert len(versoes) >= 2, versoes
    assert max(v["numero_versao"] for v in versoes) >= 2

    lacrada = ptam.get(f"/ptam/{PID}/versoes/{vid}").json()
    assert lacrada["tipo"] == "lacrado"
    assert lacrada["hash_sha256"] == hash_lacre
    assert lacrada["snapshot"]["property_label"] == "Casa da Rua A"  # não acompanhou a edição

    r = ptam.get(f"/ptam/{PID}/verificar/{vid}")
    assert r.json()["integro"] is True


def test_snapshot_adulterado_e_detectado(ptam):
    lac = _lacrar(ptam)
    vid = lac["versao"]["id"]
    versao = next(v for v in ptam.fake.ptam_versions.docs if v["id"] == vid)
    versao["snapshot"]["property_label"] = "Outro imóvel"

    r = ptam.get(f"/ptam/{PID}/verificar/{vid}")
    assert r.status_code == 200 and r.json()["integro"] is False


def test_verificar_versao_nao_lacrada_e_recusado(ptam):
    ptam.put(f"/ptam/{PID}", json={"property_label": "Editada", "finalidade": "venda"})
    auto = next(v for v in ptam.fake.ptam_versions.docs if v["tipo"] == "auto")
    r = ptam.get(f"/ptam/{PID}/verificar/{auto['id']}")
    assert r.status_code == 400


# ── links públicos ───────────────────────────────────────────────────────────
LINKS = {
    "ptam": ("routes.ptam", "ptam_documents", "/ptam/public/{t}",
             {"id": PID, "user_id": DONO, "numero_ptam": "0007", "property_label": "Casa"}),
    "contrato": ("routes.contratos", "contratos", "/contratos/public/{t}",
                 {"id": "c-1", "user_id": DONO, "tipo_contrato": "compra_venda",
                  "numero_contrato": "CV-2026-0001", "vendedores": [], "compradores": []}),
}


@pytest.mark.parametrize("nome", list(LINKS))
@pytest.mark.parametrize("token,ativo,esperado", [
    ("tok-errado", True, 404),     # token que não existe
    (TOKEN, False, 404),           # link desativado pelo dono
    ("", True, 404),               # token vazio
])
def test_link_publico_invalido_responde_404(nome, token, ativo, esperado):
    modulo, colecao, rota, doc = LINKS[nome]
    fake = FakeDB()
    getattr(fake, colecao).docs.append({**doc, "link_publico_token": TOKEN,
                                        "link_publico_ativo": ativo})
    with _cliente(modulo, fake) as c:
        url = rota.format(t=token) if token else rota.format(t="").rstrip("/") + "/%20"
        r = c.get(url, headers={"user-agent": "teste-bot"})
    assert r.status_code == esperado, r.text[:200]
    assert "user_id" not in r.text and DONO not in r.text


@pytest.mark.parametrize("nome", list(LINKS))
def test_link_publico_valido_abre(nome):
    """Controle positivo: o token certo com o link ativo abre (prova que o 404 acima
    vem da checagem do token, não de falha do dublê)."""
    modulo, colecao, rota, doc = LINKS[nome]
    fake = FakeDB()
    getattr(fake, colecao).docs.append({**doc, "link_publico_token": TOKEN,
                                        "link_publico_ativo": True})
    with _cliente(modulo, fake) as c:
        r = c.get(rota.format(t=TOKEN), headers={"user-agent": "teste-bot"})
    assert r.status_code == 200, r.text[:300]
