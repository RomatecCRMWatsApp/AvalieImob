# @module models.clients — Modelos para clientes, imóveis, amostras e avaliações
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.common import _id, _now


class ClientBase(BaseModel):
    name: str
    type: str = "Pessoa Física"
    doc: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    city: Optional[str] = ""


class Client(ClientBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)


class PropertyBase(BaseModel):
    ref: str
    client_id: Optional[str] = ""
    type: str = "Urbano"
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
