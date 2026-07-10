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
    """Normaliza o telefone para o formato exigido pelo Z-API: 55 + DDD + número.

    O Z-API exige o DDI. Sem ele, a API responde 200 mas NÃO entrega a mensagem.
    Regra (Brasil): números com 10 ou 11 dígitos (DDD + fixo/celular) recebem o
    prefixo 55. Números já com 12-13 dígitos iniciando em 55 passam direto.
    Comprimentos fora desse padrão (internacionais) são mantidos como vieram.
    """
    digits = "".join(c for c in (phone or "") if c.isdigit())
    # Remove zeros à esquerda de discagem (ex.: 0XX) que não fazem parte do número E.164.
    if len(digits) in (10, 11):
        # DDD + número local → falta o DDI do Brasil.
        return "55" + digits
    return digits


def _validar_resposta_zapi(data: dict) -> dict:
    """Levanta erro quando o Z-API responde 200 mas com falha no corpo.

    Sucesso real traz zaapId/messageId/id. Falhas comuns (número sem WhatsApp,
    instância sem sessão) vêm como {"error": ...} ou {"value": false} com 200.
    """
    logger.info("Z-API resposta: %s", str(data)[:400])
    if isinstance(data, dict):
        if data.get("error"):
            raise RuntimeError(f"Z-API recusou o envio: {data.get('error')}")
        if data.get("value") is False:
            raise RuntimeError("Z-API não entregou a mensagem (número pode não ter WhatsApp).")
        if not (data.get("messageId") or data.get("zaapId") or data.get("id")):
            raise RuntimeError(f"Z-API não confirmou o envio (resposta sem messageId): {str(data)[:200]}")
    return data


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
        return _validar_resposta_zapi(r.json())


_EXT_BY_CT = {
    "application/pdf": "pdf",
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}


async def send_document(
    *,
    instance_id: str,
    token: str,
    security_token: Optional[str],
    phone: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    caption: str = "",
) -> dict:
    """Envia um documento/imagem genérico via Z-API (anexos de recibo)."""
    phone_n = _normalize_phone(phone)
    if not phone_n:
        raise ValueError("Telefone inválido")

    ct = (content_type or "application/octet-stream").lower()
    ext = _EXT_BY_CT.get(ct, "pdf")
    url = f"{ZAPI_BASE}/instances/{instance_id}/token/{token}/send-document/{ext}"

    b64 = base64.b64encode(file_bytes).decode("ascii")
    payload = {
        "phone": phone_n,
        "document": f"data:{ct};base64,{b64}",
        "fileName": filename,
        "caption": caption,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload, headers=_headers(security_token))
        if r.status_code >= 400:
            raise RuntimeError(f"Z-API erro {r.status_code}: {r.text[:300]}")
        return _validar_resposta_zapi(r.json())


async def set_webhook_received(
    *,
    instance_id: str,
    token: str,
    security_token: Optional[str],
    url: str,
) -> dict:
    """Configura o webhook 'ao receber' (mensagens recebidas) da instância Z-API."""
    endpoint = f"{ZAPI_BASE}/instances/{instance_id}/token/{token}/update-webhook-received"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.put(endpoint, json={"value": url}, headers=_headers(security_token))
        if r.status_code >= 400:
            raise RuntimeError(f"Z-API erro {r.status_code}: {r.text[:300]}")
        try:
            return r.json()
        except Exception:  # noqa: BLE001
            return {"ok": True}


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
        return _validar_resposta_zapi(r.json())
