# @module models.conformidade — Painel de Conformidade COFECI/CNAI (Feature 05)
# Multi-tenant por user_id (convenção do projeto). validade como ISO "YYYY-MM-DD".
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class Credencial(BaseModel):
    id: str = Field(default_factory=_id)
    user_id: str
    tipo: Literal["cnai", "creci", "cft", "crea", "ecpf_icpbrasil", "art_cft", "outro"]
    numero: str
    orgao_emissor: str = ""
    titular: str = ""
    validade: str                      # ISO "YYYY-MM-DD"
    ativo: bool = True
    alerta_dias: int = 60
    alertado_em: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class AlertaConformidade(BaseModel):
    id: str = Field(default_factory=_id)
    user_id: str
    tipo: Literal[
        "credencial_vencendo", "credencial_vencida", "ptam_sem_art",
        "norma_atualizada", "meta_mensal", "documento_expirando",
    ]
    titulo: str
    descricao: str
    severidade: Literal["info", "aviso", "urgente"]
    referencia_id: Optional[str] = None
    lido: bool = False
    notificado_telegram: bool = False
    created_at: datetime = Field(default_factory=_now)


class ConfigConformidade(BaseModel):
    user_id: str
    meta_ptams_mes: int = 0
    alerta_credencial: bool = True
    alerta_ptam_sem_art: bool = True
    alerta_normas: bool = True
    alerta_metas: bool = True
    prazo_art_dias: int = 30
    notificar_telegram: bool = True
    updated_at: datetime = Field(default_factory=_now)
