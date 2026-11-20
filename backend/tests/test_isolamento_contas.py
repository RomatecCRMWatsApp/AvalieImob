# @module tests.test_isolamento_contas — conta A não alcança documento da conta B.
#
# Para cada módulo (PTAM, TVI, contratos, recibos, clientes) o teste percorre TODAS as
# rotas que recebem o ID do documento na URL, chama cada uma como a conta A usando o ID
# de um documento da conta B e exige:
#   - resposta 403/404 (nunca 2xx, nunca 5xx);
#   - o documento da conta B continua idêntico (nada foi alterado nem apagado).
# Um controle positivo (o dono lê o próprio documento) prova que o 404 vem do
# isolamento, e não de o dublê de banco não funcionar.
#
# As rotas são descobertas pelo próprio router: rota nova com ID entra no teste sozinha.
import copy
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber, get_authenticated_user
from tests.fake_mongo import FakeDB

A, B = "conta-A", "conta-B"
ID_B = "doc-da-conta-b"

# rotas de upload (multipart): nome do campo do arquivo
ARQUIVOS = {
    ("POST", "/tvi/vistoria/{vid}/photos"): "files",
    ("POST", "/recibos/{rid}/anexos"): "file",
}

# corpo mínimo válido para rotas cujo corpo tem campo obrigatório — sem ele a validação
# (422) responderia antes do handler e o teste não provaria nada.
CORPOS = {
    ("PUT", "/clients/{cid}"): {"name": "Invasor"},
    ("POST", "/ptam/{pid}/lacrar"): {"observacao": "x"},
    ("POST", "/ptam/{pid}/email"): {"destinatario": "x@exemplo.com"},
    ("PATCH", "/ptam/{pid}/tabela-incra"): {"tabela_incra_id": "t1"},
    ("POST", "/ptam/{pid}/recibo"): {"valor_honorarios": 100},
    ("PUT", "/tvi/vistoria/{vid}"): {"model_id": "TVI-01"},
    ("POST", "/ptam/{pid}/telegram"): {"chat_id": "1"},
    ("POST", "/ptam/{pid}/whatsapp"): {"phone": "99999999999"},
    ("POST", "/ptam/{pid}/whatsapp-link"): {"phone": "99999999999"},
    ("POST", "/recibos/{rid}/enviar-whatsapp"): {"phone": "99999999999"},
    ("POST", "/tvi/vistoria/{vid}/signature"): {
        "signatario": "x", "data_b64": "AA=="},
    ("POST", "/tvi/vistoria/{vid}/share"): {"vistoria_id": ID_B, "canal": "whatsapp", "destinatario": "99999999999"},
    ("POST", "/tvi/vistoria/{vid}/share/email"): {"destinatario": "x@exemplo.com"},
    ("POST", "/tvi/vistoria/{vid}/share/whatsapp"): {"phone": "99999999999"},
}

MODULOS = {
    "ptam": ("routes.ptam", "ptam_documents", "pid",
             {"id": ID_B, "user_id": B, "numero_ptam": "0001", "property_label": "Imóvel de B"}),
    "tvi": ("routes.tvi", "vistorias", "vid",
            {"id": ID_B, "user_id": B, "model_id": "TVI-01", "titulo": "Vistoria de B"}),
    "contratos": ("routes.contratos", "contratos", "cid",
                  {"id": ID_B, "user_id": B, "tipo_contrato": "compra_venda",
                   "numero_contrato": "CV-2026-0001", "vendedores": [], "compradores": []}),
    "recibos": ("routes.recibos", "recibos", "rid",
                {"id": ID_B, "user_id": B, "numero": "REC-2026-0001", "valor": 100.0}),
    "clientes": ("routes.clients", "clients", "cid",
                 {"id": ID_B, "user_id": B, "name": "Cliente de B"}),
}


def _app(modulo, fake, atual):
    import importlib
    router = importlib.import_module(modulo).router
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_active_subscriber] = lambda: atual["uid"]
    app.dependency_overrides[get_authenticated_user] = lambda: atual["uid"]
    return app


def _rotas_com_id(app, param):
    """(método, caminho) das rotas cujo caminho tem o parâmetro do documento."""
    out = []
    for r in app.routes:
        caminho = getattr(r, "path", "")
        if "{" + param + "}" not in caminho or "public" in caminho:
            continue
        for m in sorted(getattr(r, "methods", []) - {"HEAD", "OPTIONS"}):
            out.append((m, caminho))
    return out


def _url(caminho, param):
    url = caminho.replace("{" + param + "}", ID_B)
    return re.sub(r"\{[^}]+\}", "qualquer", url)  # demais parâmetros (versão, anexo…)


INTEGRACOES = {"telegram_bot_token": "t", "telegram_chat_id_default": "1",
               "whatsapp_provider": "zapi", "zapi_instance_id": "i", "zapi_token": "t",
               "zapi_security_token": "s"}


@pytest.fixture(autouse=True)
def _integracoes_configuradas(monkeypatch):
    """Com integração configurada, as rotas de envio chegam até a checagem de dono
    (sem isso elas param antes com 400 'não configurado' e o teste não prova nada)."""
    async def _cfg(*a, **kw):
        return dict(INTEGRACOES)
    import importlib
    for mod in ("routes.ptam", "routes.tvi", "routes.contratos", "routes.recibos"):
        m = importlib.import_module(mod)
        if hasattr(m, "carregar_integracoes"):
            monkeypatch.setattr(m, "carregar_integracoes", _cfg)
    monkeypatch.setattr("services.integracoes_util.carregar_integracoes", _cfg)


@pytest.mark.parametrize("nome", list(MODULOS))
def test_conta_a_nao_alcanca_documento_da_conta_b(nome):
    modulo, colecao, param, doc_b = MODULOS[nome]
    fake = FakeDB()
    getattr(fake, colecao).docs.append(copy.deepcopy(doc_b))
    fake.users.docs += [{"id": A, "email": "a@x.com", "name": "A"},
                        {"id": B, "email": "b@x.com", "name": "B"}]
    atual = {"uid": A}
    app = _app(modulo, fake, atual)
    rotas = _rotas_com_id(app, param)
    assert rotas, f"nenhuma rota com {{{param}}} encontrada em {modulo}"

    falhas = []
    with TestClient(app, raise_server_exceptions=False) as c:
        for metodo, caminho in rotas:
            corpo = CORPOS.get((metodo, caminho), {})
            if (metodo, caminho) in ARQUIVOS:
                kw = {"files": {ARQUIVOS[(metodo, caminho)]: ("a.png", b"\x89PNG", "image/png")}}
            elif metodo in ("POST", "PUT", "PATCH"):
                kw = {"json": corpo}
            else:
                kw = {}
            r = c.request(metodo, _url(caminho, param), **kw)
            if r.status_code not in (403, 404):
                falhas.append(f"{metodo} {caminho} → {r.status_code} {r.text[:120]}")

    restante = [d for d in getattr(fake, colecao).docs if d.get("id") == ID_B]
    assert len(restante) == 1, f"documento da conta B sumiu em {nome}"
    sem_id = {k: v for k, v in restante[0].items() if k != "_id"}
    assert sem_id == doc_b, f"documento da conta B foi alterado em {nome}"
    assert not falhas, "rotas que não barraram a conta A:\n" + "\n".join(falhas)


CONTROLE = {
    "ptam": ("GET", f"/ptam/{ID_B}", None),
    "tvi": ("GET", f"/tvi/vistoria/{ID_B}", None),
    "contratos": ("GET", f"/contratos/{ID_B}", None),
    "recibos": ("GET", f"/recibos/{ID_B}", None),
    "clientes": ("PUT", f"/clients/{ID_B}", {"name": "Cliente de B (editado)"}),
}


@pytest.mark.parametrize("nome", list(MODULOS))
def test_dono_alcanca_o_proprio_documento(nome):
    """Controle positivo: com o mesmo dublê, o dono recebe 200."""
    modulo, colecao, _param, doc_b = MODULOS[nome]
    fake = FakeDB()
    getattr(fake, colecao).docs.append(copy.deepcopy(doc_b))
    fake.users.docs.append({"id": B, "email": "b@x.com", "name": "B"})
    app = _app(modulo, fake, {"uid": B})
    metodo, url, corpo = CONTROLE[nome]
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.request(metodo, url, **({"json": corpo} if corpo else {}))
    assert r.status_code == 200, r.text[:300]
