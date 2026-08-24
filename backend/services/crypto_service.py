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


def status() -> dict:
    """Diagnóstico da chave — SEM expor a chave nem qualquer credencial.

    Serve para responder, da própria plataforma, a pergunta que só os logs do
    servidor respondiam: a `CREDENCIAIS_FERNET_KEY` está válida ou o sistema caiu
    no fallback derivado do JWT_SECRET (que não sobrevive à troca do segredo)?
    """
    raw = os.getenv("CREDENCIAIS_FERNET_KEY", "").strip()
    saida = {"configurada": bool(raw), "valida": False, "origem": "jwt_secret",
             "pronto_para_producao": False, "mensagem": ""}
    if raw:
        try:
            Fernet(raw.encode())
            saida.update({"valida": True, "origem": "env", "pronto_para_producao": True,
                          "mensagem": "Chave dedicada configurada e válida."})
        except Exception as e:  # noqa: BLE001
            saida["mensagem"] = (
                f"CREDENCIAIS_FERNET_KEY está definida mas é INVÁLIDA ({type(e).__name__}). "
                "Precisa ser uma chave Fernet de 32 bytes em base64 url-safe (44 caracteres, "
                "terminando em '='). Gere outra e substitua no Railway.")
            return saida
    else:
        saida["mensagem"] = (
            "CREDENCIAIS_FERNET_KEY não está definida — as credenciais são cifradas com uma "
            "chave derivada do JWT_SECRET. Funciona, mas trocar o JWT_SECRET tornaria as "
            "credenciais salvas ilegíveis.")

    # Prova real: cifra e decifra um valor de teste com a chave em uso.
    try:
        assert decrypt_json(encrypt_json({"ping": "ok"})) == {"ping": "ok"}
        saida["ciclo_de_teste"] = "ok"
    except Exception as e:  # noqa: BLE001
        saida["ciclo_de_teste"] = f"falhou: {type(e).__name__}"
        saida["pronto_para_producao"] = False
    return saida
