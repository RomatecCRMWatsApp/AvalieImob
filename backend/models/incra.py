# @module models.incra — Tabelas de referência INCRA (Valores de Terra Nua) por região/município
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class IncraFaixa(BaseModel):
    """Tipologia de uso com valor de terra (R$/ha): mín / médio / máx + nº de amostras."""
    faixa: str                       # tipologia de uso, ex: "Pastagem formada — cap. alta"
    vr_min: float = 0.0              # VTI mín R$/ha
    vr_max: float = 0.0              # VTI máx R$/ha
    vr_medio: float = 0.0            # VTI médio R$/ha (informado ou (min+max)/2)
    n_amostras: Optional[int] = None  # nº de amostras da pesquisa (RAMT)


class IncraFator(BaseModel):
    """Fator de homogeneização sugerido (NBR 14653-3)."""
    fator: str                       # ex: "Localização / acesso"
    variavel: Optional[str] = ""     # ex: "Distância BR/MA, proximidade polo"
    faixa_ajuste: Optional[str] = "" # ex: "0,70 – 1,30"


class IncraTabelaBase(BaseModel):
    """Payload de cadastro de uma tabela INCRA (Relatório de Análise de Mercado de Terras)."""
    regiao: str                      # ex: "MRT Pré-Amazônico"
    municipio: Optional[str] = None  # município principal/representativo
    municipios: List[str] = []       # demais municípios cobertos pelo polo (matching)
    polo_regional: Optional[str] = None   # ex: "Imperatriz / Açailândia"
    norma: Optional[str] = "NBR 14653-3:2019"
    ano: int
    mes: int = Field(ge=1, le=12)
    vigencia: str                    # ex: "RAMT-MA 2022"
    fonte: str                       # ex: "INCRA/SR-21-MA — RAMT-MA 2022"
    faixas: List[IncraFaixa] = []
    fatores: List[IncraFator] = []   # fatores de homogeneização NBR 14653-3
    notas: Optional[str] = None      # notas técnicas (rodapé)


class IncraTabela(IncraTabelaBase):
    """Documento persistido em db.incra_tabelas."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None    # quem cadastrou
    ativo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
