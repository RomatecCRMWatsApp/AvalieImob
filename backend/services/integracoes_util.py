# @module services.integracoes_util — Cifra/decifra de credenciais e fallback global Z-API
"""Camada de apoio às integrações por usuário (multi-tenant SaaS):

- Cifra os tokens sensíveis em repouso (AES-256-GCM via cert_crypto), de forma
  migration-safe: valores legados em texto puro continuam funcionando e passam
  a ser cifrados no próximo save.
- Loader `carregar_integracoes` que decifra os segredos e, opcionalmente, aplica
  um fallback de Z-API global (número da Romatec) lido das env vars — usado só
  quando o usuário não configurou o Z-API próprio e as env vars existem.
"""
import os
import logging

from services.cert_crypto import encrypt_str, decrypt_str

logger = logging.getLogger("romatec")

# Campos que devem ser cifrados em repouso (tokens/segredos).
SEGREDOS_INTEGRACOES = (
    "zapi_token",
    "zapi_security_token",
    "meta_access_token",
    "telegram_bot_token",
)


def cifrar_update(update: dict) -> dict:
    """Cifra os campos sensíveis presentes no dict de atualização (antes do $set)."""
    out = dict(update or {})
    for campo in SEGREDOS_INTEGRACOES:
        v = out.get(campo)
        if isinstance(v, str) and v:
            out[campo] = encrypt_str(v)
    return out


def decifrar_doc(cfg):
    """Retorna uma cópia do doc com os segredos decifrados (ou o próprio None/{})."""
    if not cfg:
        return cfg
    out = dict(cfg)
    for campo in SEGREDOS_INTEGRACOES:
        if campo in out:
            out[campo] = decrypt_str(out[campo])
    return out


def _env_primeiro(*nomes):
    for n in nomes:
        v = (os.getenv(n) or "").strip()
        if v:
            return v
    return ""


def aplicar_fallback_zapi(cfg):
    """Plano 'envio incluso': se o usuário não tem Z-API próprio mas há credenciais
    globais nas env vars, usa o número global. Só ativa se as env vars existirem —
    caso contrário não altera nada (comportamento por-usuário padrão)."""
    cfg = dict(cfg or {})
    inst = _env_primeiro("ZAPI_INSTANCE_ID", "ZAPI_INSTANCE_ID_ZAYRA")
    tok = _env_primeiro("ZAPI_TOKEN", "ZAPI_TOKEN_ZAYRA")
    sec = _env_primeiro("ZAPI_CLIENT_TOKEN", "ZAPI_SECURITY_TOKEN", "ZAPI_CLIENT_TOKEN_ZAYRA")
    tem_proprio = bool(cfg.get("zapi_instance_id") and cfg.get("zapi_token"))
    if inst and tok and not tem_proprio:
        cfg["zapi_instance_id"] = inst
        cfg["zapi_token"] = tok
        if sec and not cfg.get("zapi_security_token"):
            cfg["zapi_security_token"] = sec
        if not cfg.get("whatsapp_provider"):
            cfg["whatsapp_provider"] = "zapi"
    return cfg


async def carregar_integracoes(db, uid: str, fallback_zapi: bool = True):
    """Carrega as integrações do usuário já decifradas. Por padrão aplica o
    fallback global de Z-API (usar fallback_zapi=False ao validar credenciais
    do próprio usuário, ex.: botão Testar)."""
    cfg = await db.integracoes.find_one({"user_id": uid})
    cfg = decifrar_doc(cfg)
    if fallback_zapi:
        cfg = aplicar_fallback_zapi(cfg)
    return cfg
