# @module services.assinatura.factory — Resolve o adapter do provedor a partir da credencial do usuário.
from __future__ import annotations

from services.assinatura import credenciais as CRED
from services.assinatura.autentique import AutentiqueProvider
from services.assinatura.base import CredencialNaoConfigurada, SignatureProvider
from services.assinatura.clicksign import ClicksignProvider
from services.assinatura.d4sign import D4SignProvider

_ADAPTERS = {
    "d4sign": D4SignProvider,
    "clicksign": ClicksignProvider,
    "autentique": AutentiqueProvider,
}


def adapter_class(slug: str):
    return _ADAPTERS.get(slug)


def instanciar(slug: str, credenciais: dict, ambiente: str) -> SignatureProvider:
    cls = _ADAPTERS.get(slug)
    if not cls:
        raise CredencialNaoConfigurada(f"provider desconhecido: {slug}")
    return cls(credenciais or {}, ambiente or "producao")


async def get_provider(db, user_id: str, provider_slug: str) -> SignatureProvider:
    """Carrega e descriptografa a credencial do usuário e instancia o adapter.
    Levanta CredencialNaoConfigurada (HTTP 409) se o provedor não estiver configurado."""
    if provider_slug not in _ADAPTERS:
        raise CredencialNaoConfigurada(f"provider desconhecido: {provider_slug}")
    doc, cred = await CRED.obter_decifrada(db, user_id, provider_slug)
    if not doc or cred is None:
        raise CredencialNaoConfigurada(f"credencial não configurada para {provider_slug}")
    return _ADAPTERS[provider_slug](cred, doc.get("ambiente", "producao"))
