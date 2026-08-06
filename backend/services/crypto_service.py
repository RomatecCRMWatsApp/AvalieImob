# @module services.crypto_service — Criptografia das credenciais BYOK (assinatura externa).
"""
Fernet (AES-128-CBC + HMAC) para as credenciais das plataformas de assinatura.
Chave em ENV `CREDENCIAIS_FERNET_KEY` (chave Fernet: 32 bytes url-safe base64).

Segue o padrão de services.cert_crypto: se a env não estiver setada, deriva uma
chave de desenvolvimento do JWT_SECRET (com aviso LOUD). Em produção, DEFINA
`CREDENCIAIS_FERNET_KEY` — gere com:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Nunca retornar a credencial em claro: use `mascarar` no serializer de saída.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os

from cryptography.fernet import Fernet

logger = logging.getLogger("romatec")


def _fernet_key() -> bytes:
    raw = os.getenv("CREDENCIAIS_FERNET_KEY", "").strip()
    if raw:
        try:
            Fernet(raw.encode())          # valida o formato
            return raw.encode()
        except Exception as e:            # noqa: BLE001
            logger.error("CREDENCIAIS_FERNET_KEY inválida: %s", e)
            raise
    # Fallback de desenvolvimento — deriva do JWT_SECRET. NÃO usar em produção.
    secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
    derived = base64.urlsafe_b64encode(hashlib.sha256(("cred-fernet:" + secret).encode()).digest())
    logger.warning(
        "CREDENCIAIS_FERNET_KEY não configurada — derivando de JWT_SECRET (NÃO usar em produção). "
        "Gere com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )
    return derived


def _fernet() -> Fernet:
    # Sem cache: relê a env a cada chamada (barato; permite rotação/testes de chave).
    return Fernet(_fernet_key())


def encrypt_json(data: dict) -> str:
    """Serializa um dict e cifra → token Fernet (str)."""
    payload = json.dumps(data or {}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _fernet().encrypt(payload).decode("ascii")


def decrypt_json(token: str) -> dict:
    """Decifra o token Fernet → dict. Levanta em token/chave inválidos."""
    return json.loads(_fernet().decrypt(str(token).encode("ascii")).decode("utf-8"))


def mascarar(value) -> str:
    """Máscara p/ exibição: '••••••••3f2a' (últimos 4). Curto → só bolinhas."""
    s = "" if value is None else str(value)
    if not s:
        return ""
    if len(s) <= 4:
        return "•" * len(s)
    return "•" * 8 + s[-4:]


def mascarar_credenciais(cred: dict) -> dict:
    """Mascara todos os valores de um dict de credenciais para o GET."""
    return {k: mascarar(v) for k, v in (cred or {}).items()}
