# @module routes.auth — Rotas de autenticação: registro, login e perfil do usuário autenticado
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from services.auth_service import hash_password, verify_password, create_token, get_current_user_id
from models import UserRegister, UserLogin, UserPublic, AuthResponse, UserUpdate

try:
    from email_service import send_welcome_email
    _email_enabled = True
except ImportError:
    _email_enabled = False
    async def send_welcome_email(*a, **kw): pass

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
@limiter.limit("3/minute")
async def register(request: Request, data: UserRegister, db=Depends(get_db)):
    from models import User
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
    asyncio.create_task(send_welcome_email(user.email, user.name))
    return AuthResponse(user=UserPublic(**user.model_dump()), token=token)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(request: Request, data: UserLogin, db=Depends(get_db)):
    u = await db.users.find_one({"email": data.email.lower()})
    if not u or not verify_password(data.password, u.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_token(u["id"])
    defaults = {"crea": "", "role": "user", "plan": "mensal", "plan_status": "inactive", "plan_expires": None, "company": "", "bio": "", "company_logo": None}
    pub = UserPublic(**{k: u.get(k) if u.get(k) is not None else defaults.get(k, "") for k in UserPublic.model_fields})
    return AuthResponse(user=pub, token=token)


@router.get("/me", response_model=UserPublic)
async def me(uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    defaults = {"crea": "", "role": "user", "plan": "mensal", "plan_status": "inactive", "plan_expires": None, "company": "", "bio": "", "company_logo": None}
    fields = {k: u.get(k) if u.get(k) is not None else defaults.get(k, "") for k in UserPublic.model_fields}
    return UserPublic(**fields)


@router.put("/me", response_model=UserPublic)
async def update_me(data: UserUpdate, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    raw = data.model_dump()
    updates = {k: v for k, v in raw.items() if v is not None or k == "company_logo"}
    if updates:
        await db.users.update_one({"id": uid}, {"$set": updates})
    u = await db.users.find_one({"id": uid})
    fields = {k: u.get(k) for k in UserPublic.model_fields}
    return UserPublic(**fields)
