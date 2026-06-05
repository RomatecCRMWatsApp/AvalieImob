# @module models.documento_anexo — Documento anexado a um imóvel (convertido se era PDF)
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TipoDocumento(str, Enum):
    # ── Documentos rurais ──
    SIGEF_MAPA         = "sigef_mapa"
    SIGEF_MEMORIAL     = "sigef_memorial"
    CCIR               = "ccir"
    ITR                = "itr"
    CAR                = "car"
    # ── Documentos do imóvel (geral) ──
    MATRICULA          = "matricula"
    PLANTA_PROJETO     = "planta_projeto"
    ESCRITURA          = "escritura"
    FOTOGRAFIAS        = "fotografias"
    GEOREFERENCIAMENTO = "georeferenciamento"
    HABITE_SE          = "habite_se"
    IPTU               = "iptu"
    OUTROS             = "outros"


class DocumentoAnexo(BaseModel):
    """Arquivo anexado a um imóvel. Se era PDF, foi convertido em TIFF 300 DPI
    (uma entrada por página) e ganhou previews JPEG; o PDF original é preservado
    para auditoria. Imagens enviadas direto não passam por conversão."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    tipo: TipoDocumento
    nome_original: str                                  # nome enviado pelo usuário
    paginas: int = 1                                    # 1 p/ imagem direta; N p/ PDF
    arquivos_tiff: list[str] = Field(default_factory=list)     # paths relativos dos TIFFs
    arquivos_preview: list[str] = Field(default_factory=list)  # paths relativos dos JPEGs
    arquivo_original_pdf: Optional[str] = None          # path relativo do PDF (auditoria)
    content_type: str = "application/octet-stream"
    tamanho_bytes: int = 0
    convertido: bool = False                            # True se passou por PDF→TIFF
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
