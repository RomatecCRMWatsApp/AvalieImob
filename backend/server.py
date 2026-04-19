"""RomaTec AvalieImob - FastAPI backend with JWT auth, CRUD, Emergent LLM integration."""
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from auth import hash_password, verify_password, create_token, get_current_user_id
from models import (
    UserRegister, UserLogin, User, UserPublic, AuthResponse, UserUpdate,
    ClientBase, Client,
    PropertyBase, Property,
    SampleBase, Sample,
    EvaluationBase, Evaluation,
    AIMessage, AIMessageResponse,
    PtamBase, Ptam,
    Transaction, CreatePreferenceRequest,
)
from ptam_docx import generate_ptam_docx
from ptam_pdf import generate_ptam_pdf

# Optional email service (graceful import)
try:
    from email_service import send_welcome_email, send_payment_email, send_ptam_issued_email
    _email_enabled = True
except ImportError:
    _email_enabled = False
    async def send_welcome_email(*a, **kw): pass
    async def send_payment_email(*a, **kw): pass
    async def send_ptam_issued_email(*a, **kw): pass

# MongoDB
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# ===== RATE LIMITER =================================================
limiter = Limiter(key_func=get_remote_address, default_limits=["100/10minutes"])

app = FastAPI(title="RomaTec AvalieImob API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api = APIRouter(prefix="/api")

logger = logging.getLogger("romatec")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# ===== SECURITY HEADERS MIDDLEWARE ==================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


# ===== SUBSCRIPTION GUARD DEPENDENCY ================================
async def get_active_subscriber(uid: str = Depends(get_current_user_id)):
    """Verifica se o usuario possui assinatura ativa. Rejeita com 403 se inativa/expirada."""
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    plan_status = u.get("plan_status", "inactive")
    plan_expires = u.get("plan_expires")
    now = datetime.utcnow()
    # Expirou: atualiza status e rejeita
    if plan_status == "active" and plan_expires and plan_expires < now:
        plan_status = "expired"
        await db.users.update_one({"id": uid}, {"$set": {"plan_status": "expired"}})
    if plan_status != "active":
        raise HTTPException(
            status_code=403,
            detail="Assinatura inativa. Acesse a página de assinatura para ativar seu plano."
        )
    return uid


# Helpers ------------------------------------------------------------
def _serialize(doc):
    if not doc:
        return doc
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


async def _user_doc(user_id: str):
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return u


# ===== AUTH =========================================================
@api.post("/auth/register", response_model=AuthResponse)
@limiter.limit("3/minute")
async def register(request: Request, data: UserRegister):
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 6 caracteres")
    user = User(name=data.name, email=data.email.lower(), role=data.role or "Profissional", crea=data.crea or "")
    doc = user.model_dump()
    doc["password_hash"] = hash_password(data.password)
    await db.users.insert_one(doc)
    token = create_token(user.id)
    import asyncio
    asyncio.create_task(send_welcome_email(user.email, user.name))
    return AuthResponse(user=UserPublic(**user.model_dump()), token=token)


@api.post("/auth/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(request: Request, data: UserLogin):
    u = await db.users.find_one({"email": data.email.lower()})
    if not u or not verify_password(data.password, u.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_token(u["id"])
    defaults = {"crea": "", "plan": "mensal", "plan_status": "inactive", "plan_expires": None, "company": "", "bio": ""}
    pub = UserPublic(**{k: u.get(k) if u.get(k) is not None else defaults.get(k, "") for k in UserPublic.model_fields})
    return AuthResponse(user=pub, token=token)


@api.get("/auth/me", response_model=UserPublic)
async def me(uid: str = Depends(get_current_user_id)):
    u = await _user_doc(uid)
    defaults = {"crea": "", "plan": "mensal", "plan_status": "inactive", "plan_expires": None, "company": "", "bio": ""}
    fields = {k: u.get(k) if u.get(k) is not None else defaults.get(k, "") for k in UserPublic.model_fields}
    return UserPublic(**fields)


@api.put("/auth/me", response_model=UserPublic)
async def update_me(data: UserUpdate, uid: str = Depends(get_current_user_id)):
    u = await _user_doc(uid)
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": uid}, {"$set": updates})
    u = await _user_doc(uid)
    fields = {k: u.get(k) for k in UserPublic.model_fields}
    return UserPublic(**fields)


# ===== CLIENTS =======================================================
@api.get("/clients", response_model=List[Client])
async def list_clients(uid: str = Depends(get_active_subscriber)):
    items = await db.clients.find({"user_id": uid}).sort("created_at", -1).to_list(1000)
    return [Client(**_serialize(i)) for i in items]


@api.post("/clients", response_model=Client)
async def create_client(data: ClientBase, uid: str = Depends(get_active_subscriber)):
    c = Client(user_id=uid, **data.model_dump())
    await db.clients.insert_one(c.model_dump())
    return c


@api.put("/clients/{cid}", response_model=Client)
async def update_client(cid: str, data: ClientBase, uid: str = Depends(get_active_subscriber)):
    doc = await db.clients.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    await db.clients.update_one({"id": cid}, {"$set": data.model_dump()})
    new_doc = await db.clients.find_one({"id": cid})
    return Client(**_serialize(new_doc))


@api.delete("/clients/{cid}")
async def delete_client(cid: str, uid: str = Depends(get_active_subscriber)):
    res = await db.clients.delete_one({"id": cid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"ok": True}


# ===== PROPERTIES ====================================================
@api.get("/properties", response_model=List[Property])
async def list_properties(type: Optional[str] = None, uid: str = Depends(get_active_subscriber)):
    q = {"user_id": uid}
    if type and type.lower() != "todos":
        q["type"] = type
    items = await db.properties.find(q).sort("created_at", -1).to_list(1000)
    return [Property(**_serialize(i)) for i in items]


@api.post("/properties", response_model=Property)
async def create_property(data: PropertyBase, uid: str = Depends(get_active_subscriber)):
    p = Property(user_id=uid, **data.model_dump())
    await db.properties.insert_one(p.model_dump())
    return p


@api.put("/properties/{pid}", response_model=Property)
async def update_property(pid: str, data: PropertyBase, uid: str = Depends(get_active_subscriber)):
    doc = await db.properties.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    await db.properties.update_one({"id": pid}, {"$set": data.model_dump()})
    new_doc = await db.properties.find_one({"id": pid})
    return Property(**_serialize(new_doc))


@api.delete("/properties/{pid}")
async def delete_property(pid: str, uid: str = Depends(get_active_subscriber)):
    res = await db.properties.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return {"ok": True}


# ===== SAMPLES =======================================================
@api.get("/samples", response_model=List[Sample])
async def list_samples(uid: str = Depends(get_active_subscriber)):
    items = await db.samples.find({"user_id": uid}).sort("created_at", -1).to_list(1000)
    return [Sample(**_serialize(i)) for i in items]


@api.post("/samples", response_model=Sample)
async def create_sample(data: SampleBase, uid: str = Depends(get_active_subscriber)):
    price_per_sqm = round(data.value / data.area) if data.area else 0
    s = Sample(user_id=uid, price_per_sqm=price_per_sqm, **data.model_dump())
    await db.samples.insert_one(s.model_dump())
    return s


@api.delete("/samples/{sid}")
async def delete_sample(sid: str, uid: str = Depends(get_active_subscriber)):
    res = await db.samples.delete_one({"id": sid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Amostra não encontrada")
    return {"ok": True}


# ===== EVALUATIONS ===================================================
@api.get("/evaluations", response_model=List[Evaluation])
async def list_evaluations(uid: str = Depends(get_active_subscriber)):
    items = await db.evaluations.find({"user_id": uid}).sort("created_at", -1).to_list(1000)
    return [Evaluation(**_serialize(i)) for i in items]


@api.post("/evaluations", response_model=Evaluation)
async def create_evaluation(data: EvaluationBase, uid: str = Depends(get_active_subscriber)):
    year = datetime.utcnow().year
    prefix = {"PTAM": "PTAM", "Laudo": "LAU"}.get(data.type, "GAR")
    count = await db.evaluations.count_documents({"user_id": uid}) + 1
    code = f"{prefix}-{year}-{str(count).zfill(3)}"
    e = Evaluation(user_id=uid, code=code, **data.model_dump())
    await db.evaluations.insert_one(e.model_dump())
    return e


@api.put("/evaluations/{eid}", response_model=Evaluation)
async def update_evaluation(eid: str, data: EvaluationBase, uid: str = Depends(get_active_subscriber)):
    doc = await db.evaluations.find_one({"id": eid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")
    await db.evaluations.update_one({"id": eid}, {"$set": data.model_dump()})
    new_doc = await db.evaluations.find_one({"id": eid})
    return Evaluation(**_serialize(new_doc))


@api.delete("/evaluations/{eid}")
async def delete_evaluation(eid: str, uid: str = Depends(get_active_subscriber)):
    res = await db.evaluations.delete_one({"id": eid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")
    return {"ok": True}


# ===== DASHBOARD =====================================================
@api.get("/dashboard/stats")
async def dashboard_stats(uid: str = Depends(get_current_user_id)):
    from collections import defaultdict
    clients_count = await db.clients.count_documents({"user_id": uid})
    props_count = await db.properties.count_documents({"user_id": uid})
    evals = await db.evaluations.find({"user_id": uid}).to_list(1000)
    total_val = sum((e.get("value") or 0) for e in evals if e.get("status") == "Emitido")
    monthly = defaultdict(int)
    months_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    for e in evals:
        try:
            d = datetime.fromisoformat(e.get("date", ""))
            monthly[months_pt[d.month - 1]] += 1
        except Exception:
            pass
    now_month = datetime.utcnow().month
    order = [months_pt[(now_month - 6 + i) % 12] for i in range(6)]
    monthly_list = [{"month": m, "count": monthly.get(m, 0)} for m in order]
    return {
        "evaluations": len(evals),
        "clients": clients_count,
        "properties": props_count,
        "revenue": round(total_val * 0.01, 2),
        "monthly": monthly_list,
    }


# ===== AI (OpenAI) ===================================================
SYSTEM_PROMPT = (
    "Você é um assistente especialista em avaliação imobiliária brasileira, PTAM e laudos técnicos, "
    "seguindo rigorosamente a NBR 14.653 da ABNT (partes 1 a 7). Responda sempre em português-BR, "
    "em tom técnico, objetivo e profissional. Ajude corretores, engenheiros, peritos e avaliadores a: "
    "1) aperfeiçoar textos técnicos de laudos e pareceres; 2) gerar fundamentações pelo Método Comparativo "
    "Direto de Dados de Mercado, Método Evolutivo e avaliações agronômicas (safra, rebanho); "
    "3) sugerir estruturas para memória de cálculo e tratamento estatístico; 4) elaborar análises SWOT, "
    "memoriais descritivos e relatórios. Cite a norma quando pertinente."
)


@api.post("/ai/chat", response_model=AIMessageResponse)
@limiter.limit("10/minute")
async def ai_chat(request: Request, data: AIMessage, uid: str = Depends(get_active_subscriber)):
    from openai import AsyncOpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM não configurado")
    await db.ai_messages.insert_one({
        "user_id": uid, "session_id": data.session_id,
        "role": "user", "content": data.message, "ts": datetime.utcnow()
    })
    history = await db.ai_messages.find({"user_id": uid, "session_id": data.session_id}).sort("ts", 1).to_list(50)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    try:
        client_ai = AsyncOpenAI(api_key=api_key)
        resp = await client_ai.chat.completions.create(model="gpt-4o-mini", messages=messages, max_tokens=2000)
        reply = resp.choices[0].message.content or ""
    except Exception as e:
        logger.exception("AI error")
        raise HTTPException(status_code=500, detail=f"Erro na IA: {str(e)[:200]}")
    if not reply:
        raise HTTPException(status_code=500, detail="Resposta vazia da IA")
    await db.ai_messages.insert_one({
        "user_id": uid, "session_id": data.session_id,
        "role": "assistant", "content": reply, "ts": datetime.utcnow()
    })
    return AIMessageResponse(session_id=data.session_id, reply=reply)


@api.get("/ai/history/{session_id}")
async def ai_history(session_id: str, uid: str = Depends(get_active_subscriber)):
    items = await db.ai_messages.find({"user_id": uid, "session_id": session_id}).sort("ts", 1).to_list(1000)
    return [{"role": i["role"], "content": i["content"], "ts": i["ts"].isoformat()} for i in items]


# ===== PTAM ==========================================================
from fastapi.responses import Response


@api.get("/ptam", response_model=List[Ptam])
async def list_ptam(uid: str = Depends(get_active_subscriber)):
    items = await db.ptam_documents.find({"user_id": uid}).sort("updated_at", -1).to_list(1000)
    return [Ptam(**_serialize(i)) for i in items]


@api.get("/ptam/{pid}", response_model=Ptam)
async def get_ptam(pid: str, uid: str = Depends(get_active_subscriber)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    return Ptam(**_serialize(doc))


@api.post("/ptam", response_model=Ptam)
async def create_ptam(data: PtamBase, uid: str = Depends(get_active_subscriber)):
    number = data.number
    if not number:
        year = datetime.utcnow().year
        count = await db.ptam_documents.count_documents({"user_id": uid}) + 1
        number = f"{year}-{str(count).zfill(4)}"
    payload = data.model_dump()
    payload["number"] = number
    p = Ptam(user_id=uid, **payload)
    await db.ptam_documents.insert_one(p.model_dump())
    return p


@api.put("/ptam/{pid}", response_model=Ptam)
async def update_ptam(pid: str, data: PtamBase, uid: str = Depends(get_active_subscriber)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    await db.ptam_documents.update_one({"id": pid}, {"$set": updates})
    new_doc = await db.ptam_documents.find_one({"id": pid})
    return Ptam(**_serialize(new_doc))


@api.delete("/ptam/{pid}")
async def delete_ptam(pid: str, uid: str = Depends(get_active_subscriber)):
    res = await db.ptam_documents.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    return {"ok": True}


@api.get("/ptam/{pid}/docx")
async def download_ptam_docx(pid: str, uid: str = Depends(get_active_subscriber)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    user = await _user_doc(uid)
    data = None
    try:
        data = generate_ptam_docx(doc, user)
    except Exception as e:
        logger.exception("DOCX generation error")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar DOCX: {str(e)[:200]}")
    if not data:
        raise HTTPException(status_code=500, detail="Falha ao gerar documento")
    filename = f"PTAM_{doc.get('number', 'sem-numero').replace('/', '-')}.docx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api.get("/ptam/{pid}/pdf")
async def download_ptam_pdf(pid: str, uid: str = Depends(get_active_subscriber)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    user = await _user_doc(uid)
    try:
        data = generate_ptam_pdf(doc, user)
    except Exception as e:
        logger.exception("PDF generation error")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)[:200]}")
    if not data:
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF")
    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename = f"PTAM_{doc.get('number', 'sem-numero').replace('/', '-')}_{date_str}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===== PAYMENTS (Mercado Pago) =======================================

PLAN_CONFIG = {
    "mensal":     {"title": "AvalieImob - Plano Mensal",      "unit_price": 89.90,  "days": 30},
    "trimestral": {"title": "AvalieImob - Plano Trimestral",  "unit_price": 239.90, "days": 90},
    "anual":      {"title": "AvalieImob - Plano Anual",        "unit_price": 849.90, "days": 365},
}

APP_URL = "https://avalieimob-production.up.railway.app"


def _get_mp_sdk():
    import mercadopago
    access_token = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "")
    if not access_token:
        raise HTTPException(status_code=500, detail="Mercado Pago não configurado")
    return mercadopago.SDK(access_token)


@api.post("/payments/create-preference")
@limiter.limit("10/minute")
async def create_preference(request: Request, data: CreatePreferenceRequest, uid: str = Depends(get_current_user_id)):
    plan = PLAN_CONFIG.get(data.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Plano inválido. Use: mensal, trimestral ou anual")

    sdk = _get_mp_sdk()
    preference_data = {
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
        "external_reference": f"{uid}|{data.plan_id}",
        "statement_descriptor": "AVALIEIMOB",
        "payment_methods": {
            "excluded_payment_types": [],
            "installments": 12,
        },
    }

    result = sdk.preference().create(preference_data)
    response = result["response"]

    if result["status"] not in (200, 201):
        logger.error("MP create-preference error: %s", response)
        raise HTTPException(status_code=502, detail="Erro ao criar preferência de pagamento")

    # Use production URL when using production token, sandbox otherwise
    mp_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
    if mp_token.startswith("TEST-"):
        init_point = response.get("sandbox_init_point") or response.get("init_point")
    else:
        init_point = response.get("init_point") or response.get("sandbox_init_point")
    logger.info("MP preference created: %s for user=%s plan=%s", response.get("id"), uid, data.plan_id)
    return {"init_point": init_point, "preference_id": response.get("id")}


@api.post("/payments/webhook")
async def payment_webhook(request: Request):
    body = await request.json()
    logger.info("MP webhook received: %s", body)

    topic = body.get("topic") or body.get("type")
    resource_id = body.get("data", {}).get("id") or body.get("id")

    if not resource_id or topic not in ("payment", "merchant_order"):
        return {"ok": True}

    if topic != "payment":
        return {"ok": True}

    try:
        sdk = _get_mp_sdk()
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

    # Idempotency: skip if already processed
    existing = await db.transactions.find_one({"mp_payment_id": mp_payment_id})
    if existing:
        logger.info("MP webhook: payment %s already processed, skipping", mp_payment_id)
        return {"ok": True}

    # Parse external_reference: "{user_id}|{plan_id}"
    parts = external_ref.split("|", 1)
    if len(parts) != 2:
        logger.warning("MP webhook: invalid external_reference: %s", external_ref)
        return {"ok": True}

    user_id, plan_id = parts
    plan_cfg = PLAN_CONFIG.get(plan_id, {})

    txn = Transaction(
        user_id=user_id,
        plan_id=plan_id,
        amount=amount,
        status=payment_status,
        mp_payment_id=mp_payment_id,
    )
    await db.transactions.insert_one(txn.model_dump())

    if payment_status == "approved":
        from datetime import timedelta
        days = plan_cfg.get("days", 30)
        expires = datetime.utcnow() + timedelta(days=days)
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"plan": plan_id, "plan_status": "active", "plan_expires": expires}}
        )
        logger.info("MP webhook: activated plan=%s for user=%s until %s", plan_id, user_id, expires)

    return {"ok": True}


@api.get("/payments/status")
async def payment_status(uid: str = Depends(get_current_user_id)):
    u = await _user_doc(uid)
    now = datetime.utcnow()
    plan_expires = u.get("plan_expires")
    plan_st = u.get("plan_status", "inactive")

    if plan_st == "active" and plan_expires and plan_expires < now:
        plan_st = "expired"
        await db.users.update_one({"id": uid}, {"$set": {"plan_status": "expired"}})

    txns = await db.transactions.find({"user_id": uid}).sort("created_at", -1).to_list(50)
    for t in txns:
        t.pop("_id", None)
        if isinstance(t.get("created_at"), datetime):
            t["created_at"] = t["created_at"].isoformat()

    return {
        "plan": u.get("plan", "mensal"),
        "plan_status": plan_st,
        "plan_expires": plan_expires.isoformat() if plan_expires else None,
        "transactions": txns,
    }


# ===== Subscription (backwards compat) ===============================
@api.get("/subscription")
async def subscription(uid: str = Depends(get_current_user_id)):
    u = await _user_doc(uid)
    plan_expires = u.get("plan_expires")
    return {
        "plan": u.get("plan", "mensal"),
        "plan_status": u.get("plan_status", "inactive"),
        "plan_expires": plan_expires.isoformat() if plan_expires else None,
        "next_billing": plan_expires.strftime("%d/%m/%Y") if plan_expires else "—",
        "status": u.get("plan_status", "inactive"),
    }


@api.post("/subscription/change")
async def change_subscription(payload: dict, uid: str = Depends(get_current_user_id)):
    plan_id = payload.get("plan_id", "mensal")
    await db.users.update_one({"id": uid}, {"$set": {"plan": plan_id}})
    return {"ok": True, "plan": plan_id}


# ===== EMAIL TEST ====================================================
@api.post("/email/test")
async def email_test(uid: str = Depends(get_current_user_id)):
    """Send a test welcome email to the logged-in user."""
    u = await _user_doc(uid)
    email = u.get("email", "")
    name = u.get("name", "Usuario")
    await send_welcome_email(email, name)
    return {"ok": True, "message": f"Email de teste enviado para {email}"}


# ===== Root ==========================================================
@api.get("/")
async def root():
    return {"app": "RomaTec AvalieImob API", "version": "1.0.0"}


app.include_router(api)

# Serve React frontend build (SPA with client-side routing)
import pathlib as _pathlib
_frontend_build = _pathlib.Path(__file__).parent.parent / "frontend" / "build"
if _frontend_build.exists():
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    app.mount("/static", StaticFiles(directory=str(_frontend_build / "static")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _frontend_build / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_build / "index.html"))

# Middleware (order matters: add after routes, before startup)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
