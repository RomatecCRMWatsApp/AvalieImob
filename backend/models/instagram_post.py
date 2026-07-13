# @module models.instagram_post — Post do módulo Instagram Studio (marketing @avalieimob).
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Literal

from pydantic import BaseModel, Field

PILARES = ("recursos", "autoridade", "quanto_vale", "novidades")
FORMATOS = ("post_unico", "carrossel", "reel_roteiro")
STATUSES = ("ideia", "aprovado", "publicado")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Slide(BaseModel):
    titulo: str = ""
    texto: str = ""


class InstagramPostBase(BaseModel):
    pilar: Literal["recursos", "autoridade", "quanto_vale", "novidades"] = "recursos"
    formato: Literal["post_unico", "carrossel", "reel_roteiro"] = "post_unico"
    titulo: str = ""
    legenda: str = ""
    hashtags: List[str] = Field(default_factory=list)
    slides: List[Slide] = Field(default_factory=list)
    roteiro: str = ""
    cta: str = ""
    link: str = ""
    template_arte: str = "impacto"
    status: Literal["ideia", "aprovado", "publicado"] = "ideia"
    data_agendada: Optional[str] = None
    data_publicado: Optional[str] = None


class InstagramPostCreate(InstagramPostBase):
    pass


class InstagramPostUpdate(BaseModel):
    pilar: Optional[str] = None
    formato: Optional[str] = None
    titulo: Optional[str] = None
    legenda: Optional[str] = None
    hashtags: Optional[List[str]] = None
    slides: Optional[List[Any]] = None
    roteiro: Optional[str] = None
    cta: Optional[str] = None
    link: Optional[str] = None
    template_arte: Optional[str] = None
    status: Optional[str] = None
    data_agendada: Optional[str] = None
    data_publicado: Optional[str] = None


class InstagramPost(InstagramPostBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    criado_em: str = Field(default_factory=_iso)
    atualizado_em: str = Field(default_factory=_iso)
