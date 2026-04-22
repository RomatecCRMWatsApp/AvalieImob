# @module models.cnd — Modelos Pydantic para o módulo CND (Certidões Negativas de Débito)
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.common import _id, _now


class CNDConsulta(BaseModel):
    id: str = Field(default_factory=_id)
    user_id: str
    cpf_cnpj: str
    nome_parte: str
    tipo_parte: str  # vendedor | comprador | proprietario | empresa
    ptam_id: Optional[str] = None
    status: str = "pendente"  # pendente | processando | concluido | erro
    created_at: datetime = Field(default_factory=_now)


class CNDCertidao(BaseModel):
    id: str = Field(default_factory=_id)
    consulta_id: str
    provider: str  # receita | pgfn | tst | trf1 | tjma | cnib | rfb_cadastro
    resultado: str  # negativa | positiva | erro | indisponivel
    pdf_base64: Optional[str] = None
    validade: Optional[str] = None
    observacao: Optional[str] = None
    consultado_em: datetime = Field(default_factory=_now)
    tempo_ms: int = 0


class CNDLog(BaseModel):
    id: str = Field(default_factory=_id)
    user_id: str
    cpf_cnpj: str
    finalidade: str
    ip: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


# --- Request/Response helpers ---

class CNDConsultarRequest(BaseModel):
    cpf_cnpj: str
    nome_parte: str
    tipo_parte: str
    finalidade: str
    data_nascimento: Optional[str] = None
    ptam_id: Optional[str] = None


class CNDConsultarResponse(BaseModel):
    consulta_id: str
    status: str


class CNDConsultaDetail(BaseModel):
    consulta: CNDConsulta
    certidoes: List[CNDCertidao] = []
