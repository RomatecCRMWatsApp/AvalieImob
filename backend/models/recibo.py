# @module models.recibo — Recibo de pagamento (honorários, serviços, mão de obra...)
"""
Modelo de Recibo independente — não vinculado obrigatoriamente a PTAM.
Pode ser usado pra qualquer cobrança de serviço pelo avaliador.

Numeração automática: REC-{TIPO_ABREV}-{ANO}-{SEQ}
ex: REC-HON-2026-0001 (honorários), REC-MO-2026-0042 (mão de obra)
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from models.common import _id, _now


# Tipos de recibo (drives a numeração e o título do PDF)
TIPOS_RECIBO = {
    "personalizado": {"abrev": "GEN", "label": "Personalizado"},
    "honorarios":    {"abrev": "HON", "label": "Honorários técnicos"},
    "servico":       {"abrev": "SRV", "label": "Prestação de serviço"},
    "mao_obra":      {"abrev": "MO",  "label": "Mão de obra"},
    "aluguel":       {"abrev": "ALU", "label": "Aluguel"},
    "comissao":      {"abrev": "COM", "label": "Comissão"},
    "consultoria":   {"abrev": "CON", "label": "Consultoria"},
    "vistoria":      {"abrev": "VTO", "label": "Vistoria"},
}

FORMAS_PAGAMENTO = [
    "PIX", "Dinheiro", "Transferência bancária", "Boleto",
    "Cartão de crédito", "Cartão de débito", "Cheque",
]


class ReciboBase(BaseModel):
    # ── Emitente (snapshot do usuário no momento da emissão) ────────────
    emitente_perfil: str = "PJ"  # "PJ" | "PF"
    emitente_nome: str = ""
    emitente_documento: str = ""  # CPF ou CNPJ
    emitente_endereco: str = ""
    emitente_telefone: str = ""
    emitente_email: str = ""
    emitente_logo_id: Optional[str] = None
    emitente_dados_bancarios: Optional[str] = ""  # PIX, banco, etc.

    # ── Tipo / categoria ─────────────────────────────────────────────────
    tipo: str = "personalizado"
    categoria: Optional[str] = ""
    servico: Optional[str] = ""

    # ── Destinatário ─────────────────────────────────────────────────────
    destinatario_nome: str
    destinatario_whatsapp: Optional[str] = ""
    destinatario_cpf_cnpj: Optional[str] = ""
    destinatario_email: Optional[str] = ""

    # ── Pagamento ────────────────────────────────────────────────────────
    valor: float
    forma_pagamento: str = "PIX"
    validade_dias: int = 7
    data_pagamento: Optional[str] = None  # ISO date — quando foi pago
    descricao: Optional[str] = ""

    # ── Vínculos opcionais ───────────────────────────────────────────────
    ptam_id: Optional[str] = None  # se gerado a partir de um PTAM
    cliente_id: Optional[str] = None

    # ── Status ───────────────────────────────────────────────────────────
    status: str = "rascunho"  # rascunho | emitido | enviado | cancelado


class Recibo(ReciboBase):
    id: str = Field(default_factory=_id)
    user_id: str
    numero: Optional[str] = None  # REC-HON-2026-0001 (preenchido ao emitir)
    sequencia: Optional[int] = None
    enviado_em: Optional[datetime] = None
    enviado_via: Optional[str] = None  # whatsapp | telegram | email
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ReciboCreate(ReciboBase):
    """Payload de criação — destinatario_nome e valor obrigatórios."""
    pass


class ReciboUpdate(BaseModel):
    """Patch parcial."""
    emitente_perfil: Optional[str] = None
    emitente_nome: Optional[str] = None
    emitente_documento: Optional[str] = None
    emitente_endereco: Optional[str] = None
    emitente_telefone: Optional[str] = None
    emitente_email: Optional[str] = None
    emitente_logo_id: Optional[str] = None
    emitente_dados_bancarios: Optional[str] = None
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    servico: Optional[str] = None
    destinatario_nome: Optional[str] = None
    destinatario_whatsapp: Optional[str] = None
    destinatario_cpf_cnpj: Optional[str] = None
    destinatario_email: Optional[str] = None
    valor: Optional[float] = None
    forma_pagamento: Optional[str] = None
    validade_dias: Optional[int] = None
    data_pagamento: Optional[str] = None
    descricao: Optional[str] = None
    status: Optional[str] = None
    ptam_id: Optional[str] = None
    cliente_id: Optional[str] = None
