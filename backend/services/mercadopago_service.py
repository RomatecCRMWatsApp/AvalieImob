# @module services.mercadopago_service — Integração Mercado Pago: criação de preferência e webhook
import os
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException

logger = logging.getLogger("romatec")

PLAN_CONFIG = {
    "mensal":     {"title": "AvalieImob - Plano Mensal",      "unit_price": 89.90,  "days": 30},
    "trimestral": {"title": "AvalieImob - Plano Trimestral",  "unit_price": 239.90, "days": 90},
    "anual":      {"title": "AvalieImob - Plano Anual",        "unit_price": 849.90, "days": 365},
}

APP_URL = os.environ.get("APP_URL", "https://www.romatecavalieimob.com.br").rstrip("/")


def get_mp_sdk():
    import mercadopago
    access_token = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "")
    if not access_token:
        raise HTTPException(status_code=500, detail="Mercado Pago não configurado")
    return mercadopago.SDK(access_token)


def build_preference_data(uid: str, plan_id: str) -> dict:
    plan = PLAN_CONFIG.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Plano inválido. Use: mensal, trimestral ou anual")
    return {
        "items": [{
            "title": plan["title"],
            "quantity": 1,
            "unit_price": plan["unit_price"],
            "currency_id": "BRL",
        }],
        "back_urls": {
            "success": f"{APP_URL}/dashboard?payment=success",
            "failure": f"{APP_URL}/dashboard?payment=failure",
            "pending": f"{APP_URL}/dashboard?payment=pending",
        },
        "auto_return": "approved",
        "notification_url": f"{APP_URL}/api/payments/webhook",
        "external_reference": f"{uid}|{plan_id}",
        "statement_descriptor": "AVALIEIMOB",
        "payment_methods": {
            "excluded_payment_types": [],
            "installments": 12,
        },
    }


def resolve_init_point(response: dict) -> str:
    mp_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
    if mp_token.startswith("TEST-"):
        return response.get("sandbox_init_point") or response.get("init_point")
    return response.get("init_point") or response.get("sandbox_init_point")


def compute_plan_expiry(plan_id: str) -> datetime:
    days = PLAN_CONFIG.get(plan_id, {}).get("days", 30)
    return datetime.utcnow() + timedelta(days=days)
