from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid


def _id():
    return str(uuid.uuid4())


def _now():
    return datetime.utcnow()


# ---------- Users ----------
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "Profissional"
    crea: Optional[str] = ""


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
    company: Optional[str] = ""
    bio: Optional[str] = ""
    created_at: datetime = Field(default_factory=_now)


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    role: str
    crea: str
    plan: str
    company: Optional[str] = ""
    bio: Optional[str] = ""


class AuthResponse(BaseModel):
    user: UserPublic
    token: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    crea: Optional[str] = None
    company: Optional[str] = None
    bio: Optional[str] = None


# ---------- Clients ----------
class ClientBase(BaseModel):
    name: str
    type: str = "Pessoa Física"  # or "Pessoa Jurídica"
    doc: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    city: Optional[str] = ""


class Client(ClientBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)


# ---------- Properties ----------
class PropertyBase(BaseModel):
    ref: str
    client_id: Optional[str] = ""
    type: str = "Urbano"  # Urbano | Rural | Garantia
    subtype: str = ""
    address: str = ""
    city: str = ""
    area: float = 0
    built_area: float = 0
    value: float = 0
    status: str = "Rascunho"


class Property(PropertyBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)


# ---------- Samples ----------
class SampleBase(BaseModel):
    ref: str
    type: str = ""
    area: float = 0
    value: float = 0
    source: Optional[str] = ""
    neighborhood: Optional[str] = ""
    date: Optional[str] = ""


class Sample(SampleBase):
    id: str = Field(default_factory=_id)
    user_id: str
    price_per_sqm: float = 0
    created_at: datetime = Field(default_factory=_now)


# ---------- Evaluations ----------
class EvaluationBase(BaseModel):
    type: str = "PTAM"
    method: str = "Comparativo Direto"
    client_id: Optional[str] = ""
    property_id: Optional[str] = ""
    value: float = 0
    status: Optional[str] = "Rascunho"
    samples: Optional[int] = 0
    notes: Optional[str] = ""


class Evaluation(EvaluationBase):
    id: str = Field(default_factory=_id)
    user_id: str
    code: str
    date: str = Field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    created_at: datetime = Field(default_factory=_now)


# ---------- AI ----------
class AIMessage(BaseModel):
    session_id: str
    message: str


class AIMessageResponse(BaseModel):
    session_id: str
    reply: str


class AIHistoryItem(BaseModel):
    role: str
    content: str
    ts: datetime
