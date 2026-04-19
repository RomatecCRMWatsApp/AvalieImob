"""RomaTec AvalieImob - FastAPI backend with JWT auth, CRUD, Emergent LLM integration."""
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional

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
)
from ptam_docx import generate_ptam_docx

# MongoDB
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="RomaTec AvalieImob API", version="1.0.0")
api = APIRouter(prefix="/api")

logger = logging.getLogger("romatec")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


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
async def register(data: UserRegister):
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
    return AuthResponse(user=UserPublic(**user.model_dump()), token=token)


@api.post("/auth/login", response_model=AuthResponse)
async def login(data: UserLogin):
    u = await db.users.find_one({"email": data.email.lower()})
    if not u or not verify_password(data.password, u.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_token(u["id"])
    pub = UserPublic(**{k: u.get(k, "") for k in UserPublic.model_fields})
    return AuthResponse(user=pub, token=token)


@api.get("/auth/me", response_model=UserPublic)
async def me(uid: str = Depends(get_current_user_id)):
    u = await _user_doc(uid)
    return UserPublic(**{k: u.get(k, "") for k in UserPublic.model_fields})


@api.put("/auth/me", response_model=UserPublic)
async def update_me(data: UserUpdate, uid: str = Depends(get_current_user_id)):
    u = await _user_doc(uid)
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": uid}, {"$set": updates})
    u = await _user_doc(uid)
    return UserPublic(**{k: u.get(k, "") for k in UserPublic.model_fields})


# ===== CLIENTS =======================================================
@api.get("/clients", response_model=List[Client])
async def list_clients(uid: str = Depends(get_current_user_id)):
    items = await db.clients.find({"user_id": uid}).sort("created_at", -1).to_list(1000)
    return [Client(**_serialize(i)) for i in items]


@api.post("/clients", response_model=Client)
async def create_client(data: ClientBase, uid: str = Depends(get_current_user_id)):
    c = Client(user_id=uid, **data.model_dump())
    await db.clients.insert_one(c.model_dump())
    return c


@api.put("/clients/{cid}", response_model=Client)
async def update_client(cid: str, data: ClientBase, uid: str = Depends(get_current_user_id)):
    doc = await db.clients.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    await db.clients.update_one({"id": cid}, {"$set": data.model_dump()})
    new_doc = await db.clients.find_one({"id": cid})
    return Client(**_serialize(new_doc))


@api.delete("/clients/{cid}")
async def delete_client(cid: str, uid: str = Depends(get_current_user_id)):
    res = await db.clients.delete_one({"id": cid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"ok": True}


# ===== PROPERTIES ====================================================
@api.get("/properties", response_model=List[Property])
async def list_properties(type: Optional[str] = None, uid: str = Depends(get_current_user_id)):
    q = {"user_id": uid}
    if type and type.lower() != "todos":
        q["type"] = type
    items = await db.properties.find(q).sort("created_at", -1).to_list(1000)
    return [Property(**_serialize(i)) for i in items]


@api.post("/properties", response_model=Property)
async def create_property(data: PropertyBase, uid: str = Depends(get_current_user_id)):
    p = Property(user_id=uid, **data.model_dump())
    await db.properties.insert_one(p.model_dump())
    return p


@api.put("/properties/{pid}", response_model=Property)
async def update_property(pid: str, data: PropertyBase, uid: str = Depends(get_current_user_id)):
    doc = await db.properties.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    await db.properties.update_one({"id": pid}, {"$set": data.model_dump()})
    new_doc = await db.properties.find_one({"id": pid})
    return Property(**_serialize(new_doc))


@api.delete("/properties/{pid}")
async def delete_property(pid: str, uid: str = Depends(get_current_user_id)):
    res = await db.properties.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return {"ok": True}


# ===== SAMPLES =======================================================
@api.get("/samples", response_model=List[Sample])
async def list_samples(uid: str = Depends(get_current_user_id)):
    items = await db.samples.find({"user_id": uid}).sort("created_at", -1).to_list(1000)
    return [Sample(**_serialize(i)) for i in items]


@api.post("/samples", response_model=Sample)
async def create_sample(data: SampleBase, uid: str = Depends(get_current_user_id)):
    price_per_sqm = round(data.value / data.area) if data.area else 0
    s = Sample(user_id=uid, price_per_sqm=price_per_sqm, **data.model_dump())
    await db.samples.insert_one(s.model_dump())
    return s


@api.delete("/samples/{sid}")
async def delete_sample(sid: str, uid: str = Depends(get_current_user_id)):
    res = await db.samples.delete_one({"id": sid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Amostra não encontrada")
    return {"ok": True}


# ===== EVALUATIONS ===================================================
@api.get("/evaluations", response_model=List[Evaluation])
async def list_evaluations(uid: str = Depends(get_current_user_id)):
    items = await db.evaluations.find({"user_id": uid}).sort("created_at", -1).to_list(1000)
    return [Evaluation(**_serialize(i)) for i in items]


@api.post("/evaluations", response_model=Evaluation)
async def create_evaluation(data: EvaluationBase, uid: str = Depends(get_current_user_id)):
    year = datetime.utcnow().year
    prefix = {"PTAM": "PTAM", "Laudo": "LAU"}.get(data.type, "GAR")
    count = await db.evaluations.count_documents({"user_id": uid}) + 1
    code = f"{prefix}-{year}-{str(count).zfill(3)}"
    e = Evaluation(user_id=uid, code=code, **data.model_dump())
    await db.evaluations.insert_one(e.model_dump())
    return e


@api.put("/evaluations/{eid}", response_model=Evaluation)
async def update_evaluation(eid: str, data: EvaluationBase, uid: str = Depends(get_current_user_id)):
    doc = await db.evaluations.find_one({"id": eid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")
    await db.evaluations.update_one({"id": eid}, {"$set": data.model_dump()})
    new_doc = await db.evaluations.find_one({"id": eid})
    return Evaluation(**_serialize(new_doc))


@api.delete("/evaluations/{eid}")
async def delete_evaluation(eid: str, uid: str = Depends(get_current_user_id)):
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
    # last 6 months order
    now_month = datetime.utcnow().month
    order = [months_pt[(now_month - 6 + i) % 12] for i in range(6)]
    monthly_list = [{"month": m, "count": monthly.get(m, 0)} for m in order]
    return {
        "evaluations": len(evals),
        "clients": clients_count,
        "properties": props_count,
        "revenue": round(total_val * 0.01, 2),  # simulated fee 1%
        "monthly": monthly_list,
    }


# ===== AI (Emergent LLM) =============================================
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
async def ai_chat(data: AIMessage, uid: str = Depends(get_current_user_id)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM não configurado")
    session_id = f"{uid}_{data.session_id}"
    # Persist user message
    await db.ai_messages.insert_one({
        "user_id": uid, "session_id": data.session_id,
        "role": "user", "content": data.message, "ts": datetime.utcnow()
    })
    reply = ""
    try:
        chat = LlmChat(api_key=api_key, session_id=session_id, system_message=SYSTEM_PROMPT).with_model("openai", "gpt-5-mini")
        reply = await chat.send_message(UserMessage(text=data.message))
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
async def ai_history(session_id: str, uid: str = Depends(get_current_user_id)):
    items = await db.ai_messages.find({"user_id": uid, "session_id": session_id}).sort("ts", 1).to_list(1000)
    return [{"role": i["role"], "content": i["content"], "ts": i["ts"].isoformat()} for i in items]


# ===== PTAM (Parecer Técnico de Avaliação Mercadológica) =============
from fastapi.responses import Response


@api.get("/ptam", response_model=List[Ptam])
async def list_ptam(uid: str = Depends(get_current_user_id)):
    items = await db.ptam_documents.find({"user_id": uid}).sort("updated_at", -1).to_list(1000)
    return [Ptam(**_serialize(i)) for i in items]


@api.get("/ptam/{pid}", response_model=Ptam)
async def get_ptam(pid: str, uid: str = Depends(get_current_user_id)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    return Ptam(**_serialize(doc))


@api.post("/ptam", response_model=Ptam)
async def create_ptam(data: PtamBase, uid: str = Depends(get_current_user_id)):
    # Auto-generate number if not provided
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
async def update_ptam(pid: str, data: PtamBase, uid: str = Depends(get_current_user_id)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    await db.ptam_documents.update_one({"id": pid}, {"$set": updates})
    new_doc = await db.ptam_documents.find_one({"id": pid})
    return Ptam(**_serialize(new_doc))


@api.delete("/ptam/{pid}")
async def delete_ptam(pid: str, uid: str = Depends(get_current_user_id)):
    res = await db.ptam_documents.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    return {"ok": True}


@api.get("/ptam/{pid}/docx")
async def download_ptam_docx(pid: str, uid: str = Depends(get_current_user_id)):
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


# ===== Subscription (MOCKED) =========================================
@api.get("/subscription")
async def subscription(uid: str = Depends(get_current_user_id)):
    u = await _user_doc(uid)
    return {"plan": u.get("plan", "mensal"), "next_billing": "2026-05-15", "status": "active"}


@api.post("/subscription/change")
async def change_subscription(payload: dict, uid: str = Depends(get_current_user_id)):
    plan_id = payload.get("plan_id", "mensal")
    await db.users.update_one({"id": uid}, {"$set": {"plan": plan_id}})
    return {"ok": True, "plan": plan_id}


# ===== Root ==========================================================
@api.get("/")
async def root():
    return {"app": "RomaTec AvalieImob API", "version": "1.0.0"}


app.include_router(api)
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
