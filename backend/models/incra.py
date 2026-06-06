# @module models.incra — Tabelas de referência INCRA (Valores de Terra Nua) por região/município
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class IncraFaixa(BaseModel):
    """Faixa de valor de terra nua (R$/ha) por classe de aptidão/dimensão."""
    faixa: str                       # ex: "Até 1 módulo fiscal"
    vr_min: float = 0.0              # R$/ha mínimo
    vr_max: float = 0.0              # R$/ha máximo
    vr_medio: float = 0.0            # R$/ha médio (informado ou (min+max)/2)


class IncraTabelaBase(BaseModel):
    """Payload de cadastro de uma tabela INCRA."""
    regiao: str                      # ex: "Médio Mearim / MA"
    municipio: Optional[str] = None  # opcional, tabelas municipalizadas
    ano: int
    mes: int = Field(ge=1, le=12)
    vigencia: str                    # ex: "Jan/2025"
    fonte: str                       # ex: "INCRA/SR-26/MA"
    faixas: List[IncraFaixa] = []


class IncraTabela(IncraTabelaBase):
    """Documento persistido em db.incra_tabelas."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None    # quem cadastrou
    ativo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
