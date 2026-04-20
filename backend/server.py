"""RomaTec AvalieImob - FastAPI backend with JWT auth, CRUD, Emergent LLM integration."""
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
import os
import asyncio
import logging
import uuid
import base64
import time as _time
from pathlib import Path
import httpx
from datetime import datetime, timedelta
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
    GarantiaBase, Garantia,
    SemoventeBase, Semovente,
    Transaction, CreatePreferenceRequest,
    CreateTestUserRequest, AdminUserOut,
    PerfilAvaliadorBase, PerfilAvaliador,
    LocacaoBase, Locacao,
)
from ptam_docx import generate_ptam_docx
from ptam_pdf import generate_ptam_pdf
from locacao_pdf import generate_locacao_pdf

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
    """Verifica se o usuario possui assinatura ativa. Admin bypassa a verificação."""
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    # Admin bypassa subscription check
    role = u.get("role", "user")
    if role == "admin":
        return uid
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
    defaults = {"crea": "", "role": "user", "plan": "mensal", "plan_status": "inactive", "plan_expires": None, "company": "", "bio": "", "company_logo": None}
    pub = UserPublic(**{k: u.get(k) if u.get(k) is not None else defaults.get(k, "") for k in UserPublic.model_fields})
    return AuthResponse(user=pub, token=token)


@api.get("/auth/me", response_model=UserPublic)
async def me(uid: str = Depends(get_current_user_id)):
    u = await _user_doc(uid)
    defaults = {"crea": "", "role": "user", "plan": "mensal", "plan_status": "inactive", "plan_expires": None, "company": "", "bio": "", "company_logo": None}
    fields = {k: u.get(k) if u.get(k) is not None else defaults.get(k, "") for k in UserPublic.model_fields}
    return UserPublic(**fields)


@api.put("/auth/me", response_model=UserPublic)
async def update_me(data: UserUpdate, uid: str = Depends(get_current_user_id)):
    u = await _user_doc(uid)
    raw = data.model_dump()
    # Allow company_logo to be explicitly set to None (logo removal)
    updates = {k: v for k, v in raw.items() if v is not None or k == "company_logo"}
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
    "Você é um especialista sênior em avaliação imobiliária brasileira, com domínio pleno da ABNT NBR 14653 "
    "(partes 1 a 7), da Resolução COFECI 957/2006, das normas CREA/CONFEA e do CPC art. 156. "
    "Responda sempre em português-BR, em tom técnico-jurídico, objetivo e profissional.\n\n"
    "COMPETÊNCIA NORMATIVA:\n"
    "• ABNT NBR 14653-1: Procedimentos gerais de avaliação de bens\n"
    "• ABNT NBR 14653-2: Imóveis urbanos — Método Comparativo Direto de Dados de Mercado (item 8.2)\n"
    "• ABNT NBR 14653-3: Imóveis rurais — avaliações agronômicas (safra, rebanho, gleba)\n"
    "• Resolução COFECI 957/2006: habilitação do Corretor para PTAM mercadológico\n"
    "• Lei 5.194/1966 e Lei 6.530/1978: regulamentação profissional CREA e CRECI\n"
    "• Resolução CONFEA 345/90: responsabilidade técnica ART\n"
    "• Lei 13.786/2018: patrimônio de afetação e laudos de incorporação\n"
    "• CPC art. 156: perito judicial cadastrado no tribunal\n\n"
    "ESTRUTURA DO PTAM (11 seções obrigatórias NBR 14653):\n"
    "1. Identificação e Objetivo — tipo de avaliação, finalidade (compra/venda, financiamento, inventário, judicial, locação)\n"
    "2. Documentação Analisada — matrícula, IPTU, planta, fotos, escritura\n"
    "3. Vistoria Técnica — data, condições, acessos, descrição detalhada\n"
    "4. Análise da Região — infraestrutura, liquidez, zoneamento (ZR1/ZC/ZI conforme Plano Diretor)\n"
    "5. Metodologia — Método Comparativo Direto, Evolutivo, Involutivo ou Renda\n"
    "6. Homogeneização e Tratamento Estatístico — fatores, média, mediana, desvio padrão, CV\n"
    "7. Valor de Avaliação — por extenso E algarismo\n"
    "8. Grau de Precisão — I, II ou III conforme NBR 14653-1 item 9\n"
    "9. Campo de Arbítrio — variação máxima de ±15% (NBR 14653-1 item 9.2.4)\n"
    "10. Prazo de Validade — 6 meses da data de emissão\n"
    "11. Declaração de Responsabilidade Técnica — ART ou RRT quando exigível\n\n"
    "ORIENTAÇÃO SOBRE QUEM PODE ASSINAR:\n"
    "• CRECI ativo: PTAM mercadológico (Res. COFECI 957/06) — compra/venda, locação, permuta\n"
    "• CREA ativo + ART (Res. CONFEA 345/90): Laudo técnico, SFH, financiamento bancário, perícia judicial\n"
    "• CAU + RRT: Arquiteto e Urbanista — laudos arquitetônicos\n"
    "• Perito Judicial: CPC art. 156, cadastro no tribunal + CREA ou CAU\n\n"
    "CAPACIDADES:\n"
    "1. Gerar e aperfeiçoar textos técnicos das 11 seções do PTAM\n"
    "2. Fundamentar o Método Comparativo Direto com amostragem mínima de 3 elementos homogeneizados\n"
    "3. Calcular e interpretar: média, mediana, desvio padrão, coeficiente de variação\n"
    "4. Orientar sobre homogeneização e fatores de ajuste (localização, área, padrão construtivo)\n"
    "5. Determinar grau de fundamentação (I, II, III) e grau de precisão\n"
    "6. Elaborar declaração de responsabilidade técnica e campo de arbítrio (±15%)\n"
    "7. Sugerir zoneamento urbano (ZR1, ZC, ZI) conforme Plano Diretor municipal\n"
    "8. Apoiar avaliações agronômicas: safra, rebanho, gleba rural (NBR 14653-3)\n"
    "9. Auxiliar no preenchimento de todos os campos do wizard PTAM com base nas informações fornecidas\n\n"
    "Ao responder, cite a norma ou dispositivo legal pertinente. Use formatação técnico-jurídica formal."
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


async def _next_ptam_numero() -> str:
    """Gera o próximo número global de PTAM no formato XXXX/AAAA usando contador atômico."""
    ano = datetime.utcnow().year
    result = await db.counters.find_one_and_update(
        {"_id": "ptam_numero"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,  # retorna o documento APÓS a atualização
    )
    seq = result["seq"]
    return f"{seq:04d}/{ano}"


@api.post("/ptam", response_model=Ptam)
async def create_ptam(data: PtamBase, uid: str = Depends(get_active_subscriber)):
    # Gerar numero_ptam automaticamente (contador global atômico)
    numero_ptam = await _next_ptam_numero()

    # Manter campo legado 'number' compatível
    number = data.number or numero_ptam

    payload = data.model_dump()
    payload["numero_ptam"] = numero_ptam
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
    # Fetch company logo bytes if configured
    company_logo_id = user.get("company_logo")
    if company_logo_id:
        logo_doc = await db.images.find_one({"id": company_logo_id, "user_id": uid})
        if logo_doc:
            import base64 as _b64
            user["_company_logo_bytes"] = _b64.b64decode(logo_doc["data_b64"])
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


# ===== UPLOAD DE IMAGENS =============================================

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "application/pdf"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@api.post("/upload/image")
async def upload_image(file: UploadFile = File(...), uid: str = Depends(get_active_subscriber)):
    """Recebe uma imagem ou PDF multipart, valida e salva em base64 no MongoDB.
    Retorna o ID, URL e content_type do arquivo salvo."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não permitido: {content_type}. Use jpg, jpeg, png, webp ou pdf."
        )

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Arquivo muito grande. Tamanho máximo: 5MB"
        )

    image_id = str(uuid.uuid4())
    doc = {
        "id": image_id,
        "user_id": uid,
        "filename": file.filename or "upload",
        "content_type": content_type,
        "data_b64": base64.b64encode(data).decode("utf-8"),
        "size_bytes": len(data),
        "created_at": datetime.utcnow(),
    }
    await db.images.insert_one(doc)
    logger.info("Image uploaded: id=%s user=%s size=%d", image_id, uid, len(data))
    return {"id": image_id, "url": f"/api/upload/image/{image_id}", "content_type": content_type}


@api.get("/upload/image/{image_id}")
async def get_image(image_id: str, uid: str = Depends(get_active_subscriber)):
    """Devolve a imagem salva com o Content-Type correto."""
    doc = await db.images.find_one({"id": image_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    raw = base64.b64decode(doc["data_b64"])
    return Response(content=raw, media_type=doc.get("content_type", "image/jpeg"))


@api.delete("/upload/image/{image_id}")
async def delete_image(image_id: str, uid: str = Depends(get_active_subscriber)):
    """Remove uma imagem do banco."""
    res = await db.images.delete_one({"id": image_id, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return {"ok": True}


# ===== GARANTIAS (NBR 14.653 partes 3 e 5) ===========================

@api.get("/garantias", response_model=List[Garantia])
async def list_garantias(tipo: Optional[str] = None, status: Optional[str] = None, uid: str = Depends(get_active_subscriber)):
    q: dict = {"user_id": uid}
    if tipo:
        q["tipo_garantia"] = tipo
    if status:
        q["status"] = status
    items = await db.garantias.find(q).sort("updated_at", -1).to_list(1000)
    return [Garantia(**_serialize(i)) for i in items]


@api.get("/garantias/{gid}", response_model=Garantia)
async def get_garantia(gid: str, uid: str = Depends(get_active_subscriber)):
    doc = await db.garantias.find_one({"id": gid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Garantia não encontrada")
    return Garantia(**_serialize(doc))


@api.post("/garantias", response_model=Garantia)
async def create_garantia(data: GarantiaBase, uid: str = Depends(get_active_subscriber)):
    numero = data.numero
    if not numero:
        year = datetime.utcnow().year
        count = await db.garantias.count_documents({"user_id": uid}) + 1
        numero = f"GAR-{year}-{str(count).zfill(4)}"
    payload = data.model_dump()
    payload["numero"] = numero
    g = Garantia(user_id=uid, **payload)
    await db.garantias.insert_one(g.model_dump())
    return g


@api.put("/garantias/{gid}", response_model=Garantia)
async def update_garantia(gid: str, data: GarantiaBase, uid: str = Depends(get_active_subscriber)):
    doc = await db.garantias.find_one({"id": gid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Garantia não encontrada")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    await db.garantias.update_one({"id": gid}, {"$set": updates})
    new_doc = await db.garantias.find_one({"id": gid})
    return Garantia(**_serialize(new_doc))


@api.delete("/garantias/{gid}")
async def delete_garantia(gid: str, uid: str = Depends(get_active_subscriber)):
    res = await db.garantias.delete_one({"id": gid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Garantia não encontrada")
    return {"ok": True}


# ===== SEMOVENTES (Penhor Rural Bancário) ============================

@api.get("/semoventes", response_model=List[Semovente])
async def list_semoventes(tipo: Optional[str] = None, status: Optional[str] = None, uid: str = Depends(get_active_subscriber)):
    q: dict = {"user_id": uid}
    if tipo:
        q["tipo_semovente"] = tipo
    if status:
        q["status"] = status
    items = await db.semoventes.find(q).sort("updated_at", -1).to_list(1000)
    return [Semovente(**_serialize(i)) for i in items]


@api.get("/semoventes/{sid}", response_model=Semovente)
async def get_semovente(sid: str, uid: str = Depends(get_active_subscriber)):
    doc = await db.semoventes.find_one({"id": sid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Semovente não encontrado")
    return Semovente(**_serialize(doc))


@api.post("/semoventes", response_model=Semovente)
async def create_semovente(data: SemoventeBase, uid: str = Depends(get_active_subscriber)):
    numero_laudo = data.numero_laudo
    if not numero_laudo:
        year = datetime.utcnow().year
        count = await db.semoventes.count_documents({"user_id": uid}) + 1
        numero_laudo = f"SEM-{year}-{str(count).zfill(4)}"
    payload = data.model_dump()
    payload["numero_laudo"] = numero_laudo
    s = Semovente(user_id=uid, **payload)
    await db.semoventes.insert_one(s.model_dump())
    return s


@api.put("/semoventes/{sid}", response_model=Semovente)
async def update_semovente(sid: str, data: SemoventeBase, uid: str = Depends(get_active_subscriber)):
    doc = await db.semoventes.find_one({"id": sid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Semovente não encontrado")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    await db.semoventes.update_one({"id": sid}, {"$set": updates})
    new_doc = await db.semoventes.find_one({"id": sid})
    return Semovente(**_serialize(new_doc))


@api.delete("/semoventes/{sid}")
async def delete_semovente(sid: str, uid: str = Depends(get_active_subscriber)):
    res = await db.semoventes.delete_one({"id": sid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Semovente não encontrado")
    return {"ok": True}


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

        # Send payment confirmation email
        user_doc = await db.users.find_one({"id": user_id})
        if user_doc:
            import asyncio
            plan_label = plan_cfg.get("title", plan_id).replace("AvalieImob - Plano ", "")
            asyncio.create_task(send_payment_email(
                to_email=user_doc.get("email", ""),
                name=user_doc.get("name", "Cliente"),
                plan=plan_label,
                amount=amount,
            ))

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


# ===== ADMIN =========================================================

async def get_admin_user(uid: str = Depends(get_current_user_id)) -> str:
    """Verifica se o usuario autenticado tem role == admin."""
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if u.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return uid


@api.post("/admin/create-test-user")
async def admin_create_test_user(data: CreateTestUserRequest, uid: str = Depends(get_admin_user)):
    from datetime import timedelta
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 6 caracteres")

    plan_expires = None
    if data.plan_status == "active":
        plan_expires = datetime.utcnow() + timedelta(days=365)

    user = User(
        name=data.name,
        email=data.email.lower(),
        role="user",
        plan=data.plan,
        plan_status=data.plan_status,
        plan_expires=plan_expires,
    )
    doc = user.model_dump()
    doc["password_hash"] = hash_password(data.password)
    await db.users.insert_one(doc)
    logger.info("Admin %s criou usuario de teste: %s", uid, user.email)
    return {
        "ok": True,
        "id": user.id,
        "email": user.email,
        "plan": user.plan,
        "plan_status": user.plan_status,
        "plan_expires": plan_expires.isoformat() if plan_expires else None,
    }


@api.get("/admin/users", response_model=List[AdminUserOut])
async def admin_list_users(uid: str = Depends(get_admin_user)):
    docs = await db.users.find({}).sort("created_at", -1).to_list(5000)
    result = []
    for d in docs:
        d.pop("_id", None)
        d.pop("password_hash", None)
        result.append(AdminUserOut(
            id=d.get("id", ""),
            name=d.get("name", ""),
            email=d.get("email", ""),
            role=d.get("role", "user"),
            plan=d.get("plan", "mensal"),
            plan_status=d.get("plan_status", "inactive"),
            plan_expires=d.get("plan_expires"),
            created_at=d.get("created_at"),
        ))
    return result


# ===== EMAIL TEST ====================================================
@api.post("/email/test")
async def email_test(uid: str = Depends(get_current_user_id)):
    """Send a test welcome email to the logged-in user."""
    u = await _user_doc(uid)
    email = u.get("email", "")
    name = u.get("name", "Usuario")
    await send_welcome_email(email, name)
    return {"ok": True, "message": f"Email de teste enviado para {email}"}


@api.post("/email/send-test")
async def email_send_test(uid: str = Depends(get_current_user_id)):
    """Alias for /email/test — sends a test welcome email to the logged-in user."""
    u = await _user_doc(uid)
    email = u.get("email", "")
    name = u.get("name", "Usuario")
    await send_welcome_email(email, name)
    return {"ok": True, "message": f"Email de teste enviado para {email}"}


# ===== Perfil Avaliador ==============================================
@api.get("/perfil-avaliador")
async def get_perfil_avaliador(uid: str = Depends(get_current_user_id)):
    doc = await db.perfil_avaliador.find_one({"user_id": uid})
    if not doc:
        return PerfilAvaliador(user_id=uid).model_dump(mode="json")
    doc.pop("_id", None)
    return doc


@api.put("/perfil-avaliador")
async def update_perfil_avaliador(
    body: PerfilAvaliadorBase,
    uid: str = Depends(get_current_user_id),
):
    now = datetime.utcnow()
    data = body.model_dump(mode="json")
    data["user_id"] = uid
    data["updated_at"] = now

    existing = await db.perfil_avaliador.find_one({"user_id": uid})
    if existing:
        await db.perfil_avaliador.update_one(
            {"user_id": uid},
            {"$set": data},
        )
        doc = await db.perfil_avaliador.find_one({"user_id": uid})
    else:
        data["id"] = str(uuid.uuid4())
        data["created_at"] = now
        await db.perfil_avaliador.insert_one(data)
        doc = await db.perfil_avaliador.find_one({"user_id": uid})

    doc.pop("_id", None)
    return doc


# ===== Locacao (Avaliacao de Locacao) ================================

async def _next_locacao_number() -> str:
    """Gera número sequencial automático LOC-XXXX/AAAA."""
    year = datetime.utcnow().year
    counter_doc = await db.counters.find_one_and_update(
        {"_id": f"locacao_numero_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = counter_doc.get("seq", 1)
    return f"LOC-{seq:04d}/{year}"


@api.post("/locacao", status_code=201)
async def create_locacao(
    body: LocacaoBase,
    uid: str = Depends(get_current_user_id),
):
    now = datetime.utcnow()
    data = body.model_dump(mode="json")
    data["id"] = str(uuid.uuid4())
    data["user_id"] = uid
    data["created_at"] = now
    data["updated_at"] = now
    if not data.get("numero_locacao"):
        data["numero_locacao"] = await _next_locacao_number()
    await db.locacoes.insert_one(data)
    data.pop("_id", None)
    return data


@api.get("/locacao")
async def list_locacoes(
    uid: str = Depends(get_current_user_id),
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    query: dict = {"user_id": uid}
    if tipo:
        query["tipo_locacao"] = tipo
    if status:
        query["status"] = status
    cursor = db.locacoes.find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    total = await db.locacoes.count_documents(query)
    return {"items": docs, "total": total, "skip": skip, "limit": limit}


@api.get("/locacao/{locacao_id}")
async def get_locacao(
    locacao_id: str,
    uid: str = Depends(get_current_user_id),
):
    doc = await db.locacoes.find_one({"id": locacao_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Avaliação de locação não encontrada")
    doc.pop("_id", None)
    return doc


@api.put("/locacao/{locacao_id}")
async def update_locacao(
    locacao_id: str,
    body: LocacaoBase,
    uid: str = Depends(get_current_user_id),
):
    doc = await db.locacoes.find_one({"id": locacao_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Avaliação de locação não encontrada")
    data = body.model_dump(mode="json")
    data["updated_at"] = datetime.utcnow()
    # preserve numero_locacao if already set
    if doc.get("numero_locacao") and not data.get("numero_locacao"):
        data["numero_locacao"] = doc["numero_locacao"]
    await db.locacoes.update_one({"id": locacao_id, "user_id": uid}, {"$set": data})
    updated = await db.locacoes.find_one({"id": locacao_id, "user_id": uid})
    updated.pop("_id", None)
    return updated


@api.delete("/locacao/{locacao_id}", status_code=204)
async def delete_locacao(
    locacao_id: str,
    uid: str = Depends(get_current_user_id),
):
    result = await db.locacoes.delete_one({"id": locacao_id, "user_id": uid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Avaliação de locação não encontrada")


@api.get("/locacao/{locacao_id}/pdf")
async def download_locacao_pdf(
    locacao_id: str,
    uid: str = Depends(get_current_user_id),
):
    from fastapi.responses import StreamingResponse
    import io
    doc = await db.locacoes.find_one({"id": locacao_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Avaliação de locação não encontrada")
    doc.pop("_id", None)
    pdf_bytes = generate_locacao_pdf(doc)
    numero = doc.get("numero_locacao") or locacao_id
    filename = f"avaliacao_locacao_{numero.replace('/', '-')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===== CRM Romatec - Proxy público com cache 5 min ===================

from datetime import timedelta
import time as _time

_crm_cache: dict = {"data": None, "ts": 0.0}
_CRM_CACHE_TTL = 300  # 5 minutos em segundos
_CRM_TRPC_URL = "https://romateccrm.com/api/trpc/properties.list"


def _fetch_crm_imoveis() -> list:
    """Busca e normaliza imóveis do CRM via tRPC. Roda em thread (não bloqueia event loop)."""
    import requests as _req
    resp = _req.get(_CRM_TRPC_URL, timeout=10, headers={"Accept": "application/json"})
    resp.raise_for_status()
    payload = resp.json()
    raw_items = payload.get("result", {}).get("data", {}).get("json", [])
    result = []
    for item in raw_items:
        images = item.get("images") or []
        slug = item.get("publicSlug") or ""
        area_construida = item.get("areaConstruida") or item.get("areaCasa")
        try:
            area_val = float(area_construida) if area_construida else None
        except (ValueError, TypeError):
            area_val = None
        try:
            terreno_val = float(item.get("areaTerreno") or 0) or None
        except (ValueError, TypeError):
            terreno_val = None
        try:
            preco_val = float(item.get("price") or 0)
        except (ValueError, TypeError):
            preco_val = 0.0
        quartos = item.get("bedrooms")
        banheiros = item.get("bathrooms")
        vagas = item.get("garageSpaces")
        result.append({
            "id": item.get("id"),
            "nome": item.get("denomination", ""),
            "tipo": item.get("propertyType") or "Imóvel",
            "preco": preco_val,
            "endereco": ", ".join(filter(None, [
                item.get("address", ""),
                item.get("city", ""),
                item.get("state", ""),
            ])),
            "quartos": int(quartos) if quartos else None,
            "banheiros": int(banheiros) if banheiros else None,
            "vagas": int(vagas) if vagas else None,
            "area": area_val,
            "terreno": terreno_val,
            "imagem": images[0] if images else None,
            "fotos": len(images),
            "status": "Disponível" if item.get("status") == "available" else (item.get("status") or ""),
            "link": f"https://romateccrm.com/imovel/{slug}" if slug else "https://romateccrm.com/properties",
        })
    return result


@api.get("/imoveis-crm")
async def get_imoveis_crm():
    """Retorna imóveis do CRM Romatec normalizados, com cache de 5 minutos."""
    now = _time.time()
    if _crm_cache["data"] is not None and (now - _crm_cache["ts"]) < _CRM_CACHE_TTL:
        return {
            "imoveis": _crm_cache["data"],
            "cached": True,
            "cache_age_s": int(now - _crm_cache["ts"]),
        }
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch_crm_imoveis)
        _crm_cache["data"] = data
        _crm_cache["ts"] = _time.time()
        logger.info("CRM Romatec: %d imóveis carregados", len(data))
        return {"imoveis": data, "cached": False, "cache_age_s": 0}
    except Exception as exc:
        logger.warning("Falha ao buscar CRM Romatec: %s", exc)
        fallback = _crm_cache["data"] or []
        return {
            "imoveis": fallback,
            "cached": True,
            "error": str(exc)[:200],
            "cache_age_s": int(now - _crm_cache["ts"]) if _crm_cache["data"] else -1,
        }


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
