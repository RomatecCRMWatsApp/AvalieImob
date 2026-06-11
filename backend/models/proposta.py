# @module models.proposta — Proposta de Consultoria (independente; motor em services.pricing).
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any
from datetime import datetime

from models.common import _id, _now


class PropostaBase(BaseModel):
    model_config = ConfigDict(extra="allow")  # dados_imovel varia por subtipo

    subtipo: str
    # Cliente
    cliente_nome: Optional[str] = ""
    cliente_cpf_cnpj: Optional[str] = ""
    cliente_telefone: Optional[str] = ""
    cliente_email: Optional[str] = ""
    # Imóvel / proposta
    endereco_imovel: Optional[str] = ""
    validade_dias: int = 15
    observacoes: Optional[str] = ""
    # Dados estruturados que alimentam o motor de cálculo (InputAverbacao, etc.)
    dados_imovel: Dict[str, Any] = Field(default_factory=dict)


class Proposta(PropostaBase):
    id: str = Field(default_factory=_id)
    user_id: str
    numero: Optional[str] = None
    valor_total: float = 0.0
    custos_calculados: Optional[Dict[str, Any]] = None
    fontes_consulta: Optional[Dict[str, Any]] = None
    status: str = "rascunho"  # rascunho | emitida | enviada | aceita | cancelada
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class PropostaPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    subtipo: str
    dados_imovel: Dict[str, Any] = Field(default_factory=dict)
