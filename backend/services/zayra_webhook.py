# @module services.zayra_webhook — dispatch de eventos pro webhook da ZAYRA.
# Envia leads (cadastros + assinaturas) pra ZAYRA persistir e notificar o CEO
# via WhatsApp + Telegram + email opcional.
#
# Fail-safe: roda em fire-and-forget (asyncio.create_task) e tem timeout
# curto. Se ZAYRA estiver offline, o cadastro/assinatura no AvalieImob
# continua funcionando normalmente — apenas log de warning aqui.

import os
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger("romatec")

ZAYRA_WEBHOOK_URL    = os.getenv("ZAYRA_LEAD_WEBHOOK_URL", "").strip()
ZAYRA_WEBHOOK_SECRET = os.getenv("AVALIEIMOB_WEBHOOK_SECRET", "").strip()


async def notify_lead(
    event_type: str,        # 'cadastro' | 'assinatura' | 'login' | 'outro'
    name: str,
    email: str,
    *,
    external_id: Optional[str] = None,
    phone: Optional[str] = None,
    role: Optional[str] = None,
    crea: Optional[str] = None,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
    utm_content: Optional[str] = None,
    utm_term: Optional[str] = None,
    page_origin: Optional[str] = None,
    referrer: Optional[str] = None,
    assinatura_plano: Optional[str] = None,
    assinatura_valor: Optional[float] = None,
    payload_raw: Optional[Dict[str, Any]] = None,
) -> None:
    """Dispatch fire-and-forget de evento pra ZAYRA. Nao levanta excecao."""
    if not ZAYRA_WEBHOOK_URL or not ZAYRA_WEBHOOK_SECRET:
        # Em dev/staging sem ZAYRA configurada, vira no-op silencioso (debug log).
        logger.debug("[zayra_webhook] URL ou SECRET nao configurados — skip")
        return

    body = {
        "event_type": event_type,
        "name": name,
        "email": email.lower(),
        "external_id": external_id,
        "phone": phone,
        "role": role,
        "crea": crea,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "utm_content": utm_content,
        "utm_term": utm_term,
        "page_origin": page_origin,
        "referrer": referrer,
        "assinatura_plano": assinatura_plano,
        "assinatura_valor": assinatura_valor,
        "payload_raw": payload_raw,
    }
    body = {k: v for k, v in body.items() if v is not None}

    headers = {
        "X-Webhook-Secret": ZAYRA_WEBHOOK_SECRET,
        "Content-Type": "application/json",
    }

    try:
        # Timeout curto — 8s eh bem mais que suficiente pra um POST simples.
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(ZAYRA_WEBHOOK_URL, json=body, headers=headers)
            if r.status_code >= 400:
                logger.warning(
                    "[zayra_webhook] ZAYRA respondeu %d: %s",
                    r.status_code, r.text[:200],
                )
            else:
                logger.info(
                    "[zayra_webhook] ✅ %s enviado: %s -> %s",
                    event_type, email, r.json().get("lead_id"),
                )
    except httpx.TimeoutException:
        logger.warning("[zayra_webhook] timeout (8s) — ZAYRA pode estar offline")
    except Exception as e:
        # Nunca derruba o fluxo principal (cadastro/assinatura) por erro aqui.
        logger.warning("[zayra_webhook] erro: %s", str(e)[:200])
