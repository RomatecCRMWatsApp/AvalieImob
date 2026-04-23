# @module models.tvi — Modelos Pydantic para o Kit TVI (Termo de Vistoria de Imóvel)
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from models.common import _id, _now


# ── Campos comuns de identificação presentes em todos os modelos ────────────
class AmbienteItem(BaseModel):
    nome: str = ""
    descricao: str = ""
    estado_conservacao: str = ""
    observacoes: str = ""


class FotoItem(BaseModel):
    url: str = ""
    ambiente: str = ""
    legenda: str = ""


# ── vistoria_models — Modelos/templates de formulário ──────────────────────
class VistoriaModelBase(BaseModel):
    nome: str
    tipo: str                          # slug único, ex: "locacao_entrada"
    categoria: str                     # ex: "LOCAÇÃO"
    descricao: Optional[str] = ""
    campos: List[Dict[str, Any]] = Field(default_factory=list)  # JSON Schema dos campos
    campos_especificos: List[Dict[str, Any]] = Field(default_factory=list)
    ativo: bool = True


class VistoriaModel(VistoriaModelBase):
    id: str = Field(default_factory=_id)
    created_at: datetime = Field(default_factory=_now)


# ── vistorias — Vistorias preenchidas ──────────────────────────────────────
class VistoriaBase(BaseModel):
    model_config = ConfigDict(extra="allow")  # aceita campos dinâmicos do TVI

    # Identificação
    model_id: str
    modelo_nome: Optional[str] = ""
    categoria: Optional[str] = ""
    numero_tvi: Optional[str] = None

    # Cliente / Solicitante
    cliente_nome: Optional[str] = ""
    cliente_cpf_cnpj: Optional[str] = ""
    cliente_telefone: Optional[str] = ""
    cliente_email: Optional[str] = ""

    # Imóvel
    imovel_endereco: Optional[str] = ""
    imovel_bairro: Optional[str] = ""
    imovel_cidade: Optional[str] = ""
    imovel_uf: Optional[str] = ""
    imovel_cep: Optional[str] = ""
    imovel_matricula: Optional[str] = ""
    imovel_tipo: Optional[str] = ""

    # Responsável Técnico
    responsavel_nome: Optional[str] = ""
    responsavel_crea: Optional[str] = ""
    responsavel_cau: Optional[str] = ""
    responsavel_cftma: Optional[str] = ""
    art_trt_numero: Optional[str] = ""

    # Vistoria
    objetivo: Optional[str] = ""
    metodologia: Optional[str] = ""
    data_vistoria: Optional[str] = ""
    hora_vistoria: Optional[str] = ""
    condicoes_climaticas: Optional[str] = ""

    # Ambientes (array dinâmico)
    ambientes: List[AmbienteItem] = Field(default_factory=list)

    # Conclusão
    conclusao_tecnica: Optional[str] = ""

    # Campos extras conforme categoria/tipo (flexível)
    campos_extras: Dict[str, Any] = Field(default_factory=dict)

    # D4Sign — Assinatura Digital com Validade Juridica (Lei 14.063/2020 + MP 2.200-2/2001)
    d4sign_document_uuid: Optional[str] = None
    d4sign_status: Optional[str] = None   # pendente|aguardando|assinado|cancelado
    d4sign_enviado_em: Optional[datetime] = None
    d4sign_assinado_em: Optional[datetime] = None
    d4sign_signatarios: Optional[List[dict]] = []
    d4sign_pdf_assinado_url: Optional[str] = None

    status: str = "Rascunho"


class Vistoria(VistoriaBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# ── vistoria_photos ────────────────────────────────────────────────────────
class GpsCoord(BaseModel):
    lat: float
    lng: float


class VistoriaPhotoBase(BaseModel):
    vistoria_id: str
    url: str
    ambiente: Optional[str] = ""
    legenda: Optional[str] = ""
    gps: Optional[GpsCoord] = None
    timestamp: Optional[str] = None


class VistoriaPhoto(VistoriaPhotoBase):
    id: str = Field(default_factory=_id)
    created_at: datetime = Field(default_factory=_now)


# ── vistoria_signatures ────────────────────────────────────────────────────
class VistoriaSignatureBase(BaseModel):
    vistoria_id: str
    data_b64: str           # assinatura em base64
    signatario: str
    cargo: Optional[str] = ""


class VistoriaSignature(VistoriaSignatureBase):
    id: str = Field(default_factory=_id)
    created_at: datetime = Field(default_factory=_now)


# ── vistoria_shares — log de compartilhamentos ─────────────────────────────
class VistoriaShareBase(BaseModel):
    vistoria_id: str
    canal: str              # "email" | "whatsapp"
    destinatario: str
    mensagem: Optional[str] = ""


class VistoriaShare(VistoriaShareBase):
    id: str = Field(default_factory=_id)
    enviado_em: datetime = Field(default_factory=_now)


# ── Request bodies para endpoints específicos ──────────────────────────────
class PhotoUploadRequest(BaseModel):
    url: str
    ambiente: Optional[str] = ""
    legenda: Optional[str] = ""
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    timestamp: Optional[str] = None


class SignatureRequest(BaseModel):
    data_b64: str
    signatario: str
    cargo: Optional[str] = ""
