# @module routes.payments — Integração Mercado Pago: criação de preferência e webhook
import asyncio
import logging
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from dependencies import get_admin_user, serialize_doc
from services.auth_service import get_current_user_id
from services.mercadopago_service import (
    PLAN_CONFIG, get_mp_sdk, build_preference_data,
    resolve_init_point, compute_plan_expiry,
)
from models import CreatePreferenceRequest, Transaction
from models.auditoria_acesso import derivar_status_funil, deve_revogar_acesso
from services import payment_events
from services.mp_webhook_seguranca import validar_assinatura

try:
    from email_service import send_payment_email
except ImportError:
    async def send_payment_email(*a, **kw): pass

router = APIRouter(tags=["payments"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("romatec")


@router.post("/payments/create-preference")
@limiter.limit("10/minute")
async def create_preference(request: Request, data: CreatePreferenceRequest, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    sdk = get_mp_sdk()
    preference_data = build_preference_data(uid, data.plan_id)
    result = sdk.preference().create(preference_data)
    response = result["response"]
    if result["status"] not in (200, 201):
        logger.error("MP create-preference error: %s", response)
        raise HTTPException(status_code=502, detail="Erro ao criar preferência de pagamento")
    init_point = resolve_init_point(response)
    logger.info("MP preference created: %s for user=%s plan=%s", response.get("id"), uid, data.plan_id)
    # Topo do funil: marca a INTENÇÃO de pagar. Diagnóstico apenas — não concede
    # nem promete acesso (quem decide isso é plan_status).
    try:
        await db.users.update_one(
            {"id": uid},
            {"$set": {
                "checkout_started_at": datetime.utcnow(),
                "checkout_preference_id": str(response.get("id") or ""),
                "checkout_plan_id": data.plan_id,
            }},
        )
    except Exception as e:
        logger.warning("checkout_started nao gravado para %s: %s", uid, e)
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
    # Assinatura HMAC do MP (x-signature). Só é EXIGIDA se
    # MERCADOPAGO_WEBHOOK_SECRET estiver configurado; sem o segredo a checagem
    # é pulada e vale o token em query param (não quebra produção).
    segredo_hmac = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET", "").strip()
    if not validar_assinatura(
        request.headers.get("x-signature"),
        request.headers.get("x-request-id"),
        str(resource_id),
        segredo_hmac,
    ):
        logger.warning("MP webhook rejected: assinatura HMAC invalida (id=%s)", resource_id)
        raise HTTPException(status_code=403, detail="Assinatura do webhook inválida")
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
    # Auditoria append-only: registra TODO evento — inclusive os que o fluxo
    # abaixo descarta (external_reference inválido, duplicata, status não
    # aprovado). Sem isto, esses casos somem sem rastro (`return {"ok": True}`).
    _parts_audit = external_ref.split("|", 1)
    _uid_audit = _parts_audit[0] if len(_parts_audit) == 2 else None
    _plan_audit = _parts_audit[1] if len(_parts_audit) == 2 else None
    await payment_events.registrar(db, _uid_audit, payment, _plan_audit)
    # Dedupe por (id, status): o MESMO evento é duplicata, mas uma TRANSIÇÃO de
    # status (pending -> approved, típica de boleto/PIX) precisa seguir adiante,
    # senão o cliente paga e nunca é ativado.
    existing = await db.transactions.find_one(
        {"mp_payment_id": mp_payment_id, "status": payment_status}
    )
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
            # Plano SEO/leads v1.0: notifica ZAYRA da nova assinatura.
            # ZAYRA dispara WhatsApp + Telegram pro CEO ("💰 NOVA ASSINATURA")
            # e auto-resposta WhatsApp pro cliente agradecendo a assinatura.
            from services.zayra_webhook import notify_lead
            asyncio.create_task(notify_lead(
                event_type="assinatura",
                name=user_doc.get("name", "Cliente"),
                email=user_doc.get("email", ""),
                external_id=user_id,
                phone=user_doc.get("phone"),
                role=user_doc.get("role"),
                crea=user_doc.get("crea") or None,
                # Reaproveita UTM persistida no doc do user no momento do cadastro
                utm_source=user_doc.get("utm_source"),
                utm_medium=user_doc.get("utm_medium"),
                utm_campaign=user_doc.get("utm_campaign"),
                page_origin=user_doc.get("page_origin"),
                referrer=user_doc.get("referrer"),
                assinatura_plano=plan_id,
                assinatura_valor=float(amount or 0),
                payload_raw={"mp_payment_id": mp_payment_id, "plan_label": plan_label},
            ))
    # Estorno / chargeback / cancelamento → derruba o plano, MAS só se não houver
    # um pagamento aprovado POSTERIOR sustentando a assinatura (renovação).
    if user_id and deve_revogar_acesso(payment_status, False):
        aprov_deste = await db.transactions.find_one(
            {"mp_payment_id": mp_payment_id, "status": "approved"}
        )
        ref = aprov_deste.get("created_at") if aprov_deste else None
        posterior = None
        if ref:
            posterior = await db.transactions.find_one({
                "user_id": user_id,
                "status": "approved",
                "mp_payment_id": {"$ne": mp_payment_id},
                "created_at": {"$gt": ref},
            })
        if deve_revogar_acesso(payment_status, bool(posterior)):
            await db.users.update_one(
                {"id": user_id},
                {"$set": {"plan_status": "expired", "plan_expires": datetime.utcnow()}},
            )
            logger.warning(
                "MP webhook: acesso REVOGADO por %s (user=%s, mp=%s)",
                payment_status, user_id, mp_payment_id,
            )
        else:
            logger.info(
                "MP webhook: %s de %s ignorado — ha pagamento aprovado posterior (user=%s)",
                payment_status, mp_payment_id, user_id,
            )
    # Campo DIAGNÓSTICO. Não gateia nada — quem decide acesso é plan_status.
    try:
        if _uid_audit:
            u_atual = await db.users.find_one({"id": _uid_audit})
            if u_atual:
                ultimo = await payment_events.ultimo_por_usuario(db, _uid_audit)
                await db.users.update_one(
                    {"id": _uid_audit},
                    {"$set": {"subscription_status": derivar_status_funil(u_atual, ultimo)}},
                )
    except Exception as e:
        logger.warning("subscription_status nao atualizado para %s: %s", _uid_audit, e)
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
async def change_subscription(payload: dict, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Altera o plano de um usuário (admin).

    BUG CORRIGIDO: antes gravava sempre em `uid` — o próprio admin — ignorando
    o usuário-alvo. `user_id` no payload define quem recebe a alteração; sem ele,
    mantém o comportamento antigo (o próprio admin) por compatibilidade.

    `ativar: true` também libera o acesso (usado para regularizar manualmente
    quem pagou mas não foi ativado pelo webhook).
    """
    plan_id = payload.get("plan_id", "mensal")
    if plan_id not in PLAN_CONFIG:
        raise HTTPException(status_code=400, detail="Plano inválido")
    alvo = str(payload.get("user_id") or "").strip() or uid
    campos = {"plan": plan_id}
    if payload.get("ativar"):
        campos["plan_status"] = "active"
        campos["plan_expires"] = compute_plan_expiry(plan_id)
    r = await db.users.update_one({"id": alvo}, {"$set": campos})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    logger.info(
        "Plano alterado por admin=%s: alvo=%s plano=%s ativar=%s",
        uid, alvo, plan_id, bool(payload.get("ativar")),
    )
    return {"ok": True, "plan": plan_id, "user_id": alvo, "ativado": bool(payload.get("ativar"))}
