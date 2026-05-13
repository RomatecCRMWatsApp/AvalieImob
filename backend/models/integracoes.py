# @module models.integracoes — Credenciais por usuário pra integrações externas
# (Z-API WhatsApp, Telegram bot, etc.) — multi-tenant SaaS.
"""
Cada usuário (avaliador/cliente do AvalieImob) cadastra suas próprias
credenciais nas Configurações. O backend usa essas credenciais nas chamadas
externas (envio de PDF via Z-API, Telegram, etc.) — não usa env vars do
servidor.

Tokens sensíveis (Z-API token, Telegram bot_token) são armazenados em claro
no MongoDB neste momento — se houver demanda futura por encryption-at-rest,
podemos reaproveitar services/cert_crypto.py.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from models.common import _id, _now


class IntegracoesBase(BaseModel):
    # ── Provedor WhatsApp escolhido ────────────────────────────────────
    # "zapi" (Z-API) ou "meta" (WhatsApp Business Cloud API oficial)
    whatsapp_provider: Optional[str] = "zapi"

    # ── Z-API (WhatsApp Business API — não-oficial mas barato) ────────
    zapi_instance_id: Optional[str] = None
    zapi_token: Optional[str] = None
    zapi_security_token: Optional[str] = None  # Client-Token (header de segurança)
    zapi_ativo: bool = False

    # ── Meta WhatsApp Cloud API (oficial) ──────────────────────────────
    meta_phone_number_id: Optional[str] = None
    meta_access_token: Optional[str] = None      # token permanente do app
    meta_business_account_id: Optional[str] = None
    meta_ativo: bool = False

    # ── Telegram Bot ──────────────────────────────────────────────────
    telegram_bot_token: Optional[str] = None
    telegram_chat_id_default: Optional[str] = None  # Chat padrão (cliente)
    telegram_ativo: bool = False


class Integracoes(IntegracoesBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class IntegracoesPublic(IntegracoesBase):
    """Versão segura — mascara tokens nas APIs."""
    id: Optional[str] = None
    user_id: Optional[str] = None
    # Indicadores se está configurado (sem expor o valor cru)
    has_zapi: bool = False
    has_meta: bool = False
    has_telegram: bool = False


def mascarar_token(token: Optional[str]) -> Optional[str]:
    """Retorna versão truncada do token pra exibição na UI (****abc)."""
    if not token:
        return None
    if len(token) <= 8:
        return "****"
    return f"****{token[-4:]}"
