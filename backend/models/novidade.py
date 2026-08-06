# @module models.novidade — Central de Novidades (anúncio de release no login).
from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel

Tag = Literal["novidade", "melhoria", "correcao", "aviso"]
PublicoAlvo = Literal["todos", "novos", "existentes"]


class NovidadeInput(BaseModel):
    """Corpo de criação/edição de uma novidade (admin)."""
    slug: str
    versao: str = ""
    titulo: str
    resumo: str = ""
    conteudo_md: str = ""
    tag: Tag = "novidade"
    imagem_url: Optional[str] = None
    cta_label: Optional[str] = None
    cta_rota: Optional[str] = None
    bloqueante: bool = False
    expira_em: Optional[datetime] = None
    publico_alvo: PublicoAlvo = "todos"
