# @module services.zapi_service — Cliente Z-API (WhatsApp Business)
"""
Z-API expõe a API do WhatsApp Business via instance + token.
Endpoint base: https://api.z-api.io/instances/{instance_id}/token/{token}/

Métodos usados:
  - POST /send-document/pdf       envia PDF
  - POST /send-text                envia mensagem texto
  - GET  /status                    valida que a instância está conectada

Cada usuário do AvalieImob configura seu próprio instance_id + token nas
Configurações (modelo Integracoes). O backend usa essas credenciais ao
enviar mensagens em nome do usuário.
"""
from __future__ import annotations

import base64
import logging
from typing import Optional

import httpx

logger = logging.getLogger("romatec")

ZAPI_BASE = "https://api.z-api.io"


def _normalize_phone(phone: str) -> str:
    """Remove tudo que não for dígito. Z-API aceita 5599XXXXXXXXX."""
    return "".join(c for c in (phone or "") if c.isdigit())


def _headers(security_token: Optional[str]) -> dict:
    headers = {"Content-Type": "application/json"}
    if security_token:
        headers["Client-Token"] = security_token
    return headers


async def status_instance(instance_id: str, token: str, security_token: Optional[str] = None) -> dict:
    """Retorna o status da instância (conectado, smartphoneConnected, etc.)."""
    url = f"{ZAPI_BASE}/instances/{instance_id}/token/{token}/status"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers=_headers(security_token))
        r.raise_for_status()
        return r.json()


async def send_document_pdf(
    *,
    instance_id: str,
    token: str,
    security_token: Optional[str],
    phone: str,
    pdf_bytes: bytes,
    filename: str = "documento.pdf",
    caption: str = "",
) -> dict:
    """Envia um PDF via Z-API. phone deve estar normalizado (só dígitos)."""
    phone_n = _normalize_phone(phone)
    if not phone_n:
        raise ValueError("Telefone inválido")

    url = f"{ZAPI_BASE}/instances/{instance_id}/token/{token}/send-document/pdf"

    # Z-API aceita base64 com prefixo data:
    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    payload = {
        "phone": phone_n,
        "document": f"data:application/pdf;base64,{b64}",
        "fileName": filename,
        "caption": caption,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload, headers=_headers(security_token))
        if r.status_code >= 400:
            raise RuntimeError(f"Z-API erro {r.status_code}: {r.text[:300]}")
        return r.json()


async def send_text(
    *,
    instance_id: str,
    token: str,
    security_token: Optional[str],
    phone: str,
    message: str,
) -> dict:
    """Envia mensagem de texto via Z-API."""
    phone_n = _normalize_phone(phone)
    if not phone_n:
        raise ValueError("Telefone inválido")
    url = f"{ZAPI_BASE}/instances/{instance_id}/token/{token}/send-text"
    payload = {"phone": phone_n, "message": message}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload, headers=_headers(security_token))
        if r.status_code >= 400:
            raise RuntimeError(f"Z-API erro {r.status_code}: {r.text[:300]}")
        return r.json()
