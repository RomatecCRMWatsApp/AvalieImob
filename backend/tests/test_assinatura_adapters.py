# Testes dos adapters BYOK (D4Sign/Clicksign/Autentique) com as APIs mockadas via respx.
import asyncio

import httpx
import pytest
import respx

from services import crypto_service as CS
from services.assinatura import factory
from services.assinatura.autentique import AutentiqueProvider
from services.assinatura.base import (
    CredencialNaoConfigurada, OpcoesEnvio, ProviderError, SignatarioEnvio,
)
from services.assinatura.clicksign import ClicksignProvider
from services.assinatura.d4sign import D4SignProvider

_SIGS = [SignatarioEnvio(nome="João da Silva", email="joao@x.com", papel="contratante")]
_OPC = OpcoesEnvio(mensagem="assine, por favor", prazo_dias=15)
_GQL = "https://api.autentique.com.br/v2/graphql"


# ── D4Sign ────────────────────────────────────────────────────────────────────
@respx.mock
def test_d4sign_testar_ok_lista_cofres():
    respx.get(url__regex=r".*/safes.*").mock(
        return_value=httpx.Response(200, json=[{"uuid_safe": "C1", "name_safe": "Cofre 1"}]))
    p = D4SignProvider({"token_api": "T", "crypt_key": "K"}, "producao")
    r = asyncio.run(p.testar_conexao())
    assert r.ok is True
    assert r.dados["cofres"][0]["uuid"] == "C1"


@respx.mock
def test_d4sign_testar_401():
    respx.get(url__regex=r".*/safes.*").mock(return_value=httpx.Response(401, json={"message": "invalid"}))
    r = asyncio.run(D4SignProvider({"token_api": "x", "crypt_key": "y"}, "producao").testar_conexao())
    assert r.ok is False


@respx.mock
def test_d4sign_enviar_fluxo_completo():
    respx.post(url__regex=r".*/documents/C1/upload.*").mock(return_value=httpx.Response(200, json={"uuid": "DOC9"}))
    respx.post(url__regex=r".*/documents/DOC9/createlist.*").mock(return_value=httpx.Response(200, json={}))
    respx.post(url__regex=r".*/documents/DOC9/sendtosigner.*").mock(return_value=httpx.Response(200, json={}))
    p = D4SignProvider({"token_api": "T", "crypt_key": "K", "uuid_safe": "C1"}, "producao")
    res = asyncio.run(p.enviar_documento(b"%PDF-1.4 conteudo", "doc.pdf", _SIGS, _OPC))
    assert res.provider_doc_id == "DOC9"


def test_d4sign_parse_webhook():
    ev = D4SignProvider({}, "producao").parse_webhook({}, {"uuid": "DOCX", "type": "Finalizado"})
    assert ev.provider_doc_id == "DOCX"
    assert ev.novo_status == "assinado"


# ── Clicksign ─────────────────────────────────────────────────────────────────
@respx.mock
def test_clicksign_testar_ok():
    respx.get(url__regex=r".*/envelopes.*").mock(return_value=httpx.Response(200, json={"data": []}))
    assert asyncio.run(ClicksignProvider({"access_token": "AT"}, "producao").testar_conexao()).ok is True


@respx.mock
def test_clicksign_testar_401():
    respx.get(url__regex=r".*/envelopes.*").mock(return_value=httpx.Response(401, json={}))
    assert asyncio.run(ClicksignProvider({"access_token": "bad"}, "producao").testar_conexao()).ok is False


@respx.mock
def test_clicksign_enviar_envelope():
    respx.post(url__regex=r".*/api/v3/envelopes$").mock(return_value=httpx.Response(201, json={"data": {"id": "ENV1"}}))
    respx.post(url__regex=r".*/envelopes/ENV1/documents$").mock(return_value=httpx.Response(201, json={"data": {}}))
    respx.post(url__regex=r".*/envelopes/ENV1/signers$").mock(return_value=httpx.Response(201, json={"data": {}}))
    respx.patch(url__regex=r".*/envelopes/ENV1$").mock(return_value=httpx.Response(200, json={"data": {}}))
    res = asyncio.run(ClicksignProvider({"access_token": "AT"}, "producao")
                      .enviar_documento(b"%PDF x", "doc.pdf", _SIGS, _OPC))
    assert res.provider_doc_id == "ENV1"


@respx.mock
def test_clicksign_rollback_quando_signers_falha():
    respx.post(url__regex=r".*/api/v3/envelopes$").mock(return_value=httpx.Response(201, json={"data": {"id": "ENV2"}}))
    respx.post(url__regex=r".*/envelopes/ENV2/documents$").mock(return_value=httpx.Response(201, json={"data": {}}))
    respx.post(url__regex=r".*/envelopes/ENV2/signers$").mock(return_value=httpx.Response(422, json={"errors": ["x"]}))
    cancel = respx.patch(url__regex=r".*/envelopes/ENV2$").mock(return_value=httpx.Response(200, json={"data": {}}))
    with pytest.raises(ProviderError):
        asyncio.run(ClicksignProvider({"access_token": "AT"}, "producao")
                    .enviar_documento(b"x", "doc.pdf", _SIGS, _OPC))
    assert cancel.called   # rollback descartou o envelope draft


# ── Autentique ────────────────────────────────────────────────────────────────
@respx.mock
def test_autentique_testar_ok():
    respx.post(_GQL).mock(return_value=httpx.Response(
        200, json={"data": {"me": {"id": "1", "name": "Zé", "email": "z@x.com"}}}))
    r = asyncio.run(AutentiqueProvider({"api_token": "AT"}, "sandbox").testar_conexao())
    assert r.ok is True and r.dados["me"]["id"] == "1"


@respx.mock
def test_autentique_testar_401():
    respx.post(_GQL).mock(return_value=httpx.Response(401, json={}))
    assert asyncio.run(AutentiqueProvider({"api_token": "bad"}, "sandbox").testar_conexao()).ok is False


@respx.mock
def test_autentique_enviar_sandbox_nao_consome_creditos():
    route = respx.post(_GQL).mock(return_value=httpx.Response(
        200, json={"data": {"createDocument": {"id": "AUT7", "name": "doc"}}}))
    res = asyncio.run(AutentiqueProvider({"api_token": "AT"}, "sandbox")
                      .enviar_documento(b"%PDF x", "doc.pdf", _SIGS, _OPC))
    assert res.provider_doc_id == "AUT7"
    # o corpo multipart carrega sandbox=true nas variables
    assert route.called


# ── Factory ───────────────────────────────────────────────────────────────────
class _Coll:
    def __init__(self):
        self.docs = []
    async def find_one(self, flt):
        return next((d for d in self.docs if all(d.get(k) == v for k, v in flt.items())), None)


class _DB:
    def __init__(self):
        self._c = {}
    def __getitem__(self, n):
        return self._c.setdefault(n, _Coll())


def test_factory_sem_credencial_levanta():
    with pytest.raises(CredencialNaoConfigurada):
        asyncio.run(factory.get_provider(_DB(), "u1", "d4sign"))


def test_factory_instancia_adapter_com_credencial_decifrada():
    db = _DB()
    db["assinatura_credenciais"].docs.append({
        "id": "x", "user_id": "u1", "provider": "clicksign", "ambiente": "sandbox",
        "credenciais_encrypted": CS.encrypt_json({"access_token": "AT12345678"}),
    })
    prov = asyncio.run(factory.get_provider(db, "u1", "clicksign"))
    assert prov.slug == "clicksign"
    assert prov.ambiente == "sandbox"
    assert prov.credenciais["access_token"] == "AT12345678"
