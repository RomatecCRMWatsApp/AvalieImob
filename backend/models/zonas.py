# @module models.zonas — Modelos Pydantic para Zonas do Plano Diretor personalizadas por usuário
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.common import _id, _now


class ZonaPlanoDiretor(BaseModel):
    id: str = Field(default_factory=_id)
    user_id: str
    codigo: str
    nome: str
    descricao: Optional[str] = ""
    municipio: Optional[str] = ""
    uf: Optional[str] = ""
    ativo: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ZonaPlanoDiretorCreate(BaseModel):
    codigo: str
    nome: str
    descricao: Optional[str] = ""
    municipio: Optional[str] = ""
    uf: Optional[str] = ""


class ZonaPlanoDiretorUpdate(BaseModel):
    codigo: Optional[str] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
