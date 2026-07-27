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

# O nginx na frente do Z-API rejeita o corpo da requisição acima de ~10 MB com
# HTTP 413 "Request Entity Too Large". Como o documento vai base64 no corpo
# (+~33% de overhead + JSON), qualquer PDF acima de ~5 MB de bytes crus arrisca
# estourar esse limite (foi a causa do 413 ao enviar laudos PTAM com muitas
# fotos). Acima deste teto, subimos o arquivo no R2 e mandamos ao Z-API só a
# URL pública — o Z-API baixa o arquivo server-side e o corpo fica minúsculo,
# eliminando o 413 para qualquer tamanho de documento.
_ZAPI_INLINE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB crus → ~6,7 MB em base64


def _upload_para_url(data: bytes, content_type: str, filename: str) -> Optional[str]:
    """Sobe `data` no R2 e devolve uma URL pública, ou None se o R2 estiver
    indisponível. Usado para contornar o limite de tamanho (413) do endpoint
    base64 do Z-API: documentos grandes vão por URL (o Z-API baixa server-side).

    O objeto vai num prefixo temporário próprio (`zapi-tmp/`) para não colidir
    com PDFs de assinatura (bucket com lifecycle de limpeza) nem com outros
    módulos. A URL (pré-assinada por 7 dias ou via CDN) sobrevive de sobra ao
    fetch imediato do Z-API.
    """
    try:
        import uuid

        from services import r2_storage

        safe = "".join(c for c in (filename or "documento") if c.isalnum() or c in "-_.")
        safe = safe or "documento"
        key = f"zapi-tmp/{uuid.uuid4().hex}_{safe}"
        return r2_storage.upload_bytes(
            data, key, content_type, cache_control="public, max-age=3600"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Z-API: upload R2 p/ envio por URL falhou (cai p/ base64): %s", exc)
        return None


async def _postar_documento(
    *,
    url: str,
    security_token: Optional[str],
    phone_n: str,
    data: bytes,
    content_type: str,
    filename: str,
    caption: str,
) -> dict:
    """Posta um documento no Z-API escolhendo base64 (arquivo pequeno) ou URL do
    R2 (arquivo grande), com retry automático por URL caso o Z-API responda 413.

    Corrige de vez o "Z-API erro 413: 413 Request Entity Too Large" (payload
    base64 excedendo o limite do nginx do Z-API) para TODOS os chamadores.
    """
    def _payload(doc_field: str) -> dict:
        return {
            "phone": phone_n,
            "document": doc_field,
            "fileName": filename,
            "caption": caption,
        }

    grande = len(data) > _ZAPI_INLINE_MAX_BYTES
    doc_field: Optional[str] = None
    usou_base64 = False

    if grande:
        doc_field = _upload_para_url(data, content_type, filename)
    if not doc_field:
        doc_field = f"data:{content_type};base64," + base64.b64encode(data).decode("ascii")
        usou_base64 = True

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, json=_payload(doc_field), headers=_headers(security_token))
        # Rede de segurança: se o base64 estourou o limite do Z-API (413),
        # sobe no R2 e reenvia por URL antes de desistir.
        if r.status_code == 413 and usou_base64:
            logger.warning("Z-API 413 no base64 (%d bytes) — reenviando por URL do R2.", len(data))
            publico = _upload_para_url(data, content_type, filename)
            if not publico:
                raise RuntimeError(
                    "Z-API erro 413: documento grande demais para envio inline e "
                    "R2 indisponível para envio por URL. Verifique as credenciais do R2."
                )
            r = await client.post(url, json=_payload(publico), headers=_headers(security_token))
        if r.status_code >= 400:
            raise RuntimeError(f"Z-API erro {r.status_code}: {r.text[:300]}")
        return _validar_resposta_zapi(r.json())


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

    # Envia via base64 (pequeno) ou URL do R2 (grande) — evita o 413 do Z-API.
    return await _postar_documento(
        url=url,
        security_token=security_token,
        phone_n=phone_n,
        data=pdf_bytes,
        content_type="application/pdf",
        filename=filename,
        caption=caption,
    )


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

    # Envia via base64 (pequeno) ou URL do R2 (grande) — evita o 413 do Z-API.
    return await _postar_documento(
        url=url,
        security_token=security_token,
        phone_n=phone_n,
        data=file_bytes,
        content_type=ct,
        filename=filename,
        caption=caption,
    )


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
