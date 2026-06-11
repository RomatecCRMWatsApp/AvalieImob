# @module models.clients — Modelos para clientes, imóveis, amostras e avaliações
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from models.common import _id, _now


# ── Tipos de documento do cliente (enum próprio — PR-5) ───────────────────────
TIPOS_DOCUMENTO_CLIENTE = [
    "rg", "cpf", "cnh", "comprovante_endereco", "certidao_casamento",
    "certidao_nascimento", "pacto_antenupcial", "contrato_social",
    "cartao_cnpj", "procuracao", "certidao_negativa", "outro",
]


class ClienteConjuge(BaseModel):
    """Cônjuge/companheiro(a) — outorga conjugal (CC art. 1.647). Reusa estrutura
    de pessoa (também serve para representante de PJ)."""
    nome: str = ""
    cpf: Optional[str] = ""
    rg: Optional[str] = ""
    orgao_emissor: Optional[str] = ""
    cnh: Optional[str] = ""
    cnh_orgao: Optional[str] = ""
    cnh_validade: Optional[str] = ""
    data_nascimento: Optional[str] = ""
    profissao: Optional[str] = ""
    nacionalidade: Optional[str] = "brasileiro(a)"
    telefone: Optional[str] = ""
    email: Optional[str] = ""


class ClientBase(BaseModel):
    # Identificação
    name: str
    type: str = "Pessoa Física"
    doc: Optional[str] = ""              # CPF (PF) ou CNPJ (PJ)
    # Pessoa Física — qualificação (usada em contratos/laudos)
    rg: Optional[str] = ""
    orgao_emissor: Optional[str] = ""
    cnh: Optional[str] = ""              # NOVO (PR-5)
    cnh_orgao: Optional[str] = ""        # NOVO
    cnh_validade: Optional[str] = ""     # NOVO (ISO yyyy-mm-dd)
    nacionalidade: Optional[str] = ""
    estado_civil: Optional[str] = ""     # solteiro|casado|uniao_estavel|divorciado|viuvo
    regime_bens: Optional[str] = ""      # NOVO — obrigatório se casado/união (validado na rota)
    profissao: Optional[str] = ""
    data_nascimento: Optional[str] = ""
    # Pessoa Jurídica
    nome_fantasia: Optional[str] = ""
    inscricao_estadual: Optional[str] = ""
    inscricao_municipal: Optional[str] = ""
    representante_legal: Optional[str] = ""
    representante_cpf: Optional[str] = ""
    # Cônjuge / companheiro(a) — NOVO bloco (PR-5)
    conjuge: Optional[ClienteConjuge] = None
    # Contato
    phone: Optional[str] = ""
    phone2: Optional[str] = ""
    email: Optional[str] = ""
    # Endereço
    cep: Optional[str] = ""
    endereco: Optional[str] = ""         # logradouro
    numero: Optional[str] = ""
    complemento: Optional[str] = ""
    bairro: Optional[str] = ""
    city: Optional[str] = ""             # cidade
    uf: Optional[str] = ""
    # Foto de perfil — NOVO (R2)
    foto_key: Optional[str] = None
    foto_thumb_key: Optional[str] = None
    # Anexos de documentos — NOVO (mesmo pipeline dos contratos)
    documentos: List[Any] = Field(default_factory=list)
    # Outros
    observacoes: Optional[str] = ""
    origem: Optional[str] = "manual"     # manual | ptam | contrato | proposta | recibo | importacao


class Client(ClientBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


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
