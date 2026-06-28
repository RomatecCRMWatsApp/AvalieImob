# @module models.documento_externo — Documentos Externos (doc-ext): assinatura de PDF
# enviado por upload, via WhatsApp + ICP. Pydantic v2 + helpers puros (sem mongo).
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field

from services.contrato_exclusividade_assinatura import gerar_token

TipoPosicao = Literal["assinatura", "rubrica", "data", "nome_extenso"]
StatusSignatario = Literal["pendente", "enviado", "assinado", "recusado"]
StatusDoc = Literal["rascunho", "aguardando", "parcial", "clientes_ok", "finalizado", "cancelado"]


class PosicaoAssinatura(BaseModel):
    pagina: int                       # 0-indexed (igual ao "Posicionar")
    x_pt: float
    y_pt: float
    larg_pt: float
    alt_pt: float
    tipo: TipoPosicao = "assinatura"
    label: Optional[str] = None


class Signatario(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    nome: str
    cpf_cnpj: str = ""
    papel: str = "Signatário"          # texto livre c/ sugestões no front
    whatsapp: str = ""
    email: Optional[str] = None
    posicoes: List[PosicaoAssinatura] = Field(default_factory=list)
    token: str = Field(default_factory=gerar_token)
    status: StatusSignatario = "pendente"
    assinado_em: Optional[datetime] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lng: Optional[float] = None
    traco_b64: Optional[str] = None


class DocumentoExternoCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    valor_referencia: Optional[float] = None
    requer_icp_rt: bool = True


def _so_dig(v: Any) -> str:
    return "".join(filter(str.isdigit, str(v or "")))


def novo_signatario(data: dict) -> dict:
    """Cria o dict de um signatário a partir do input do front (id/token/status preenchidos)."""
    return Signatario(
        nome=str(data.get("nome") or "").strip() or "Signatário",
        cpf_cnpj=_so_dig(data.get("cpf_cnpj")),
        papel=str(data.get("papel") or "Signatário").strip(),
        whatsapp=_so_dig(data.get("whatsapp") or data.get("telefone")),
        email=(data.get("email") or None),
    ).model_dump(mode="json")


class DocTestemunha(BaseModel):
    """Documento de identidade da testemunha (CNH/RG) — opcionalmente anexado ao PDF."""
    tipo: Literal["CNH", "RG", "OUTRO"] = "CNH"
    frente_key: Optional[str] = None     # key R2 (foto da frente)
    verso_key: Optional[str] = None      # key R2 (foto do verso)
    pdf_key: Optional[str] = None        # key R2 (documento em PDF — CNH-e etc.)
    nome_arquivo: Optional[str] = None
    mime: Optional[str] = None
    enviado_em: Optional[datetime] = None
    anexar_ao_pdf: bool = True


class Testemunha(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    nome: str
    cpf: str = ""
    rg: str = ""                         # qualificação completa (notarial)
    orgao_emissor: str = ""
    nacionalidade: str = ""
    estado_civil: str = ""
    profissao: str = ""
    endereco: str = ""                   # endereço completo (composto)
    telefone: str = ""                   # whatsapp/contato (só dígitos)
    email: Optional[str] = None
    vinculo: str = ""                    # papel/lado (ex.: comprador/vendedor) — texto livre
    parte_vinculada_id: Optional[str] = None    # id do signatário a quem se vincula
    parte_vinculada_nome: str = ""
    posicoes: List[PosicaoAssinatura] = Field(default_factory=list)
    token: str = Field(default_factory=gerar_token)
    status: StatusSignatario = "pendente"        # pendente|enviado|assinado|recusado (+ visualizado via campo)
    visualizado_em: Optional[datetime] = None
    enviado_em: Optional[datetime] = None
    assinado_em: Optional[datetime] = None
    expira_em: Optional[datetime] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    traco_b64: Optional[str] = None
    documento: DocTestemunha = Field(default_factory=DocTestemunha)
    hash_validacao: Optional[str] = None
    criado_em: datetime = Field(default_factory=datetime.utcnow)


def nova_testemunha(data: dict) -> dict:
    """Cria o dict de uma testemunha a partir do input do front."""
    from datetime import timedelta
    pos = data.get("posicoes") or []
    return Testemunha(
        nome=str(data.get("nome") or "").strip() or "Testemunha",
        cpf=_so_dig(data.get("cpf")),
        rg=str(data.get("rg") or "").strip(),
        orgao_emissor=str(data.get("orgao_emissor") or "").strip(),
        nacionalidade=str(data.get("nacionalidade") or "").strip(),
        estado_civil=str(data.get("estado_civil") or "").strip(),
        profissao=str(data.get("profissao") or "").strip(),
        endereco=str(data.get("endereco") or "").strip(),
        telefone=_so_dig(data.get("telefone") or data.get("whatsapp")),
        email=(str(data.get("email")).strip() or None) if data.get("email") else None,
        vinculo=str(data.get("vinculo") or "").strip(),
        parte_vinculada_id=data.get("parte_vinculada_id"),
        parte_vinculada_nome=str(data.get("parte_vinculada_nome") or "").strip(),
        posicoes=[PosicaoAssinatura(**p) for p in pos if p],
        expira_em=datetime.utcnow() + timedelta(days=7),
    ).model_dump(mode="json")


def recalcular_status(doc: dict) -> StatusDoc:
    """Status global derivado dos signatários. requer_icp_rt define se 'todos assinaram'
    vira clientes_ok (falta ICP) ou finalizado direto."""
    sigs = doc.get("signatarios") or []
    if not sigs:
        return "rascunho"
    total = len(sigs)
    assinados = sum(1 for s in sigs if s.get("status") == "assinado")
    if assinados == 0:
        return "aguardando"
    if assinados < total:
        return "parcial"
    return "clientes_ok" if doc.get("requer_icp_rt") else "finalizado"
