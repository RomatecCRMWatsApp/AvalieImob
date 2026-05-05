# @module models.user — Modelos Pydantic para usuários, autenticação e admin
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from models.common import _id, _now


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "Profissional"
    crea: Optional[str] = ""
    # Plano SEO/leads v1.0: rastreamento de origem do trafego (UTM tags + page).
    # Frontend captura em sessionStorage e envia no submit. ZAYRA recebe via
    # webhook e usa pra notificar o CEO com a origem.
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    page_origin: Optional[str] = None
    referrer: Optional[str] = None
    phone: Optional[str] = None  # opcional, ZAYRA usa pra auto-resposta WhatsApp


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    email: str
    role: str = "Profissional"
    crea: str = ""
    plan: str = "mensal"
    plan_status: str = "inactive"
    plan_expires: Optional[datetime] = None
    company: Optional[str] = ""
    bio: Optional[str] = ""
    company_logo: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    role: str
    crea: str
    plan: str
    plan_status: str = "inactive"
    plan_expires: Optional[datetime] = None
    company: Optional[str] = ""
    bio: Optional[str] = ""
    company_logo: Optional[str] = None


class AuthResponse(BaseModel):
    user: UserPublic
    token: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    crea: Optional[str] = None
    company: Optional[str] = None
    bio: Optional[str] = None
    company_logo: Optional[str] = None


class CreateTestUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    plan: str = "mensal"
    plan_status: str = "active"


class AdminUserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    plan: str
    plan_status: str
    plan_expires: Optional[datetime] = None
    created_at: Optional[datetime] = None
