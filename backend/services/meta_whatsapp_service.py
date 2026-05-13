# @module services.meta_whatsapp_service — Cliente WhatsApp Cloud API (Meta oficial)
"""
WhatsApp Business Cloud API (Meta Graph API).

Endpoint base: https://graph.facebook.com/v20.0/{phone_number_id}

Fluxo pra enviar PDF:
  1. POST {phone_number_id}/media (multipart) — sobe o PDF, retorna media_id
  2. POST {phone_number_id}/messages — envia type=document com media_id

Cada usuário do AvalieImob configura seu próprio phone_number_id +
access_token nas Configurações (modelo Integracoes).

Importante: Meta exige que o destinatário tenha iniciado conversa nas últimas
24h (janela de atendimento), OU receba via template aprovado. Pra envios
proativos, é necessário usar templates pré-aprovados.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

import httpx

logger = logging.getLogger("romatec")

META_BASE = "https://graph.facebook.com/v20.0"


def _normalize_phone(phone: str) -> str:
    """Remove tudo que não for dígito. Meta exige formato E.164 sem '+'."""
    return "".join(c for c in (phone or "") if c.isdigit())


def _auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


async def upload_media(
    *,
    phone_number_id: str,
    access_token: str,
    file_bytes: bytes,
    filename: str,
    mime_type: str = "application/pdf",
) -> str:
    """Sobe um arquivo pra Cloud API e retorna o media_id (válido 30 dias)."""
    url = f"{META_BASE}/{phone_number_id}/media"
    files = {
        "file": (filename, io.BytesIO(file_bytes), mime_type),
    }
    data = {
        "messaging_product": "whatsapp",
        "type": mime_type,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=_auth_headers(access_token), files=files, data=data)
        if r.status_code >= 400:
            raise RuntimeError(f"Meta upload erro {r.status_code}: {r.text[:300]}")
        return r.json().get("id")


async def send_document(
    *,
    phone_number_id: str,
    access_token: str,
    phone: str,
    media_id: str,
    filename: str,
    caption: str = "",
) -> dict:
    """Envia um documento (PDF) usando media_id previamente subido."""
    url = f"{META_BASE}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": _normalize_phone(phone),
        "type": "document",
        "document": {
            "id": media_id,
            "filename": filename,
        },
    }
    if caption:
        payload["document"]["caption"] = caption

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers={**_auth_headers(access_token), "Content-Type": "application/json"}, json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"Meta send erro {r.status_code}: {r.text[:300]}")
        return r.json()


async def send_pdf(
    *,
    phone_number_id: str,
    access_token: str,
    phone: str,
    pdf_bytes: bytes,
    filename: str = "documento.pdf",
    caption: str = "",
) -> dict:
    """Conveniência: upload + send em uma chamada."""
    media_id = await upload_media(
        phone_number_id=phone_number_id,
        access_token=access_token,
        file_bytes=pdf_bytes,
        filename=filename,
        mime_type="application/pdf",
    )
    return await send_document(
        phone_number_id=phone_number_id,
        access_token=access_token,
        phone=phone,
        media_id=media_id,
        filename=filename,
        caption=caption,
    )


async def status_check(*, phone_number_id: str, access_token: str) -> dict:
    """Valida que o phone_number_id é alcançável com o token informado."""
    url = f"{META_BASE}/{phone_number_id}?fields=display_phone_number,verified_name,quality_rating"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers=_auth_headers(access_token))
        r.raise_for_status()
        return r.json()
