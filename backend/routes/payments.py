# @module routes.payments — Integração Mercado Pago: criação de preferência e webhook
import asyncio
import logging
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from dependencies import serialize_doc
from services.auth_service import get_current_user_id
from services.mercadopago_service import (
    PLAN_CONFIG, get_mp_sdk, build_preference_data,
    resolve_init_point, compute_plan_expiry,
)
from models import CreatePreferenceRequest, Transaction

try:
    from email_service import send_payment_email
except ImportError:
    async def send_payment_email(*a, **kw): pass

router = APIRouter(tags=["payments"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("romatec")


@router.post("/payments/create-preference")
@limiter.limit("10/minute")
async def create_preference(request: Request, data: CreatePreferenceRequest, uid: str = Depends(get_current_user_id)):
    sdk = get_mp_sdk()
    preference_data = build_preference_data(uid, data.plan_id)
    result = sdk.preference().create(preference_data)
    response = result["response"]
    if result["status"] not in (200, 201):
        logger.error("MP create-preference error: %s", response)
        raise HTTPException(status_code=502, detail="Erro ao criar preferência de pagamento")
    init_point = resolve_init_point(response)
    logger.info("MP preference created: %s for user=%s plan=%s", response.get("id"), uid, data.plan_id)
    return {"init_point": init_point, "preference_id": response.get("id")}


@router.post("/payments/webhook")
async def payment_webhook(request: Request, db=Depends(get_db)):
    expected_token = os.environ.get("MERCADOPAGO_WEBHOOK_TOKEN", "").strip()
    if expected_token and request.query_params.get("token") != expected_token:
        logger.warning("MP webhook rejected: invalid token")
        raise HTTPException(status_code=403, detail="Webhook token inválido")

    body = await request.json()
    logger.info("MP webhook received: %s", body)
    topic = body.get("topic") or body.get("type")
    resource_id = body.get("data", {}).get("id") or body.get("id")
    if not resource_id or topic not in ("payment", "merchant_order"):
        return {"ok": True}
    if topic != "payment":
        return {"ok": True}
    try:
        sdk = get_mp_sdk()
        payment_result = sdk.payment().get(resource_id)
        payment = payment_result.get("response", {})
    except Exception:
        logger.exception("MP webhook: failed to fetch payment %s", resource_id)
        return {"ok": True}
    mp_payment_id = str(payment.get("id", resource_id))
    payment_status = payment.get("status", "")
    external_ref = payment.get("external_reference", "")
    amount = float(payment.get("transaction_amount", 0))
    logger.info("MP payment id=%s status=%s ref=%s", mp_payment_id, payment_status, external_ref)
    existing = await db.transactions.find_one({"mp_payment_id": mp_payment_id})
    if existing:
        return {"ok": True}
    parts = external_ref.split("|", 1)
    if len(parts) != 2:
        logger.warning("MP webhook: invalid external_reference: %s", external_ref)
        return {"ok": True}
    user_id, plan_id = parts
    plan_cfg = PLAN_CONFIG.get(plan_id, {})
    txn = Transaction(user_id=user_id, plan_id=plan_id, amount=amount, status=payment_status, mp_payment_id=mp_payment_id)
    await db.transactions.insert_one(txn.model_dump())
    if payment_status == "approved":
        expires = compute_plan_expiry(plan_id)
        await db.users.update_one({"id": user_id}, {"$set": {"plan": plan_id, "plan_status": "active", "plan_expires": expires}})
        logger.info("MP webhook: activated plan=%s for user=%s until %s", plan_id, user_id, expires)
        user_doc = await db.users.find_one({"id": user_id})
        if user_doc:
            plan_label = plan_cfg.get("title", plan_id).replace("AvalieImob - Plano ", "")
            asyncio.create_task(send_payment_email(
                to_email=user_doc.get("email", ""),
                name=user_doc.get("name", "Cliente"),
                plan=plan_label,
                amount=amount,
            ))
    return {"ok": True}


@router.get("/payments/status")
async def payment_status(uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    now = datetime.utcnow()
    plan_expires = u.get("plan_expires")
    plan_st = u.get("plan_status", "inactive")
    if plan_st == "active" and plan_expires and plan_expires < now:
        plan_st = "expired"
        await db.users.update_one({"id": uid}, {"$set": {"plan_status": "expired"}})
    txns = await db.transactions.find({"user_id": uid}).sort("created_at", -1).to_list(50)
    for idx, t in enumerate(txns):
        t = serialize_doc(t)
        if isinstance(t.get("created_at"), datetime):
            t["created_at"] = t["created_at"].isoformat()
        txns[idx] = t
    return {
        "plan": u.get("plan", "mensal"),
        "plan_status": plan_st,
        "plan_expires": plan_expires.isoformat() if plan_expires else None,
        "transactions": txns,
    }


@router.get("/subscription")
async def subscription(uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    plan_expires = u.get("plan_expires")
    return {
        "plan": u.get("plan", "mensal"),
        "plan_status": u.get("plan_status", "inactive"),
        "plan_expires": plan_expires.isoformat() if plan_expires else None,
        "next_billing": plan_expires.strftime("%d/%m/%Y") if plan_expires else "—",
        "status": u.get("plan_status", "inactive"),
    }


@router.post("/subscription/change")
async def change_subscription(payload: dict, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    plan_id = payload.get("plan_id", "mensal")
    await db.users.update_one({"id": uid}, {"$set": {"plan": plan_id}})
    return {"ok": True, "plan": plan_id}
