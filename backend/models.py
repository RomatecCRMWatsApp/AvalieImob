from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
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


# ---------- PTAM (Parecer Técnico de Avaliação Mercadológica) ----------
class PtamSample(BaseModel):
    number: Optional[int] = 0
    neighborhood: Optional[str] = ""
    area_total: Optional[float] = 0
    value: Optional[float] = 0
    value_per_sqm: Optional[float] = 0
    description: Optional[str] = ""
    source: Optional[str] = ""


class PtamImpactArea(BaseModel):
    name: str = "Área de Impacto 01"
    classification: Optional[str] = "Rural"  # Rural | Urbana | Mista
    area_sqm: float = 0
    unit_value: float = 0
    total_value: float = 0
    majoration_note: Optional[str] = ""
    samples: List[PtamSample] = Field(default_factory=list)
    notes: Optional[str] = ""


class PtamBase(BaseModel):
    # Section 1 - Cover/Identification
    number: Optional[str] = ""  # PTAM nº
    property_label: Optional[str] = ""  # short title
    purpose: Optional[str] = ""  # Finalidade
    solicitante: Optional[str] = ""
    # Legal context
    judicial_process: Optional[str] = ""
    judicial_action: Optional[str] = ""
    forum: Optional[str] = ""
    requerente: Optional[str] = ""
    requerido: Optional[str] = ""
    judge: Optional[str] = ""
    # Section 2 - Imóvel
    property_address: Optional[str] = ""
    property_city: Optional[str] = ""
    property_matricula: Optional[str] = ""
    property_owner: Optional[str] = ""
    property_area_ha: float = 0
    property_area_sqm: float = 0
    property_confrontations: Optional[str] = ""
    property_description: Optional[str] = ""
    # Section 3 - Vistoria
    vistoria_date: Optional[str] = ""
    vistoria_objective: Optional[str] = ""
    vistoria_methodology: Optional[str] = ""
    topography: Optional[str] = ""
    soil_vegetation: Optional[str] = ""
    benfeitorias: Optional[str] = ""
    accessibility: Optional[str] = ""
    urban_context: Optional[str] = ""
    conservation_state: Optional[str] = ""
    vistoria_synthesis: Optional[str] = ""
    # Section 4 - Market analysis
    market_analysis: Optional[str] = ""
    # Section 5 - Methodology
    methodology: Optional[str] = "Método Comparativo Direto de Dados de Mercado"
    methodology_justification: Optional[str] = ""
    # Section 6 - Impact areas (array)
    impact_areas: List[PtamImpactArea] = Field(default_factory=list)
    # Section 7 - Conclusion
    total_indemnity: float = 0
    total_indemnity_words: Optional[str] = ""  # valor por extenso
    conclusion_text: Optional[str] = ""
    conclusion_date: Optional[str] = ""
    conclusion_city: Optional[str] = ""
    # Meta
    status: str = "Rascunho"  # Rascunho | Em revisão | Emitido


class Ptam(PtamBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


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
