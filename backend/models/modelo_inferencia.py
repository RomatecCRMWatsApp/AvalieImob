# @module models.modelo_inferencia — modelo de regressão (MCDDM) persistido.
#
# Coleção própria `modelos_inferencia`: o modelo é iterado dezenas de vezes antes
# do fechamento, então NÃO é embutido na avaliação (MD §4).
#
# ADAPTAÇÃO à convenção do repo: o MD fala em `tenant_id`; no AvalieImob o
# isolamento é por `user_id` (dono da conta) — é o campo que TODA query filtra,
# como no resto do sistema. Gravamos `tenant_id` como espelho para leitura futura.
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from models.common import _id, _now

StatusModelo = Literal["rascunho", "estimado", "homologado"]
TipoImovel = Literal["urbano", "rural"]
TipoVariavel = Literal["quantitativa", "dicotomica", "codigo_alocado"]
Transformacao = Literal["identidade", "ln", "inverso", "quadrado", "raiz"]


class DadoAmostra(BaseModel):
    dado_id: str = ""
    utilizado: bool = True
    motivo_descarte: Optional[str] = None
    variaveis: Dict[str, Any] = Field(default_factory=dict)


class RegressorSpec(BaseModel):
    campo: str
    transformacao: Transformacao = "identidade"
    tipo: TipoVariavel = "quantitativa"
    rotulo: Optional[str] = None


class DependenteSpec(BaseModel):
    campo: str = "vu"
    transformacao: Transformacao = "identidade"


class EspecificacaoSpec(BaseModel):
    dependente: DependenteSpec = Field(default_factory=DependenteSpec)
    regressores: List[RegressorSpec] = Field(default_factory=list)
    intercepto: bool = True


class ModeloInferencia(BaseModel):
    id: str = Field(default_factory=_id)
    user_id: str = ""                 # dono — filtro obrigatório em toda query
    tenant_id: str = ""               # espelho de user_id (nomenclatura do MD)
    avaliacao_id: Optional[str] = None
    ptam_id: Optional[str] = None
    nome: str = "Modelo 01"
    tipo_imovel: TipoImovel = "urbano"
    norma: str = "14653-2"

    amostra: List[DadoAmostra] = Field(default_factory=list)
    especificacao: EspecificacaoSpec = Field(default_factory=EspecificacaoSpec)
    avaliando: Dict[str, Any] = Field(default_factory=dict)
    area_total_avaliando: Optional[float] = None   # p/ o valor TOTAL além do unitário

    resultado: Optional[Dict[str, Any]] = None
    enquadramento: Optional[Dict[str, Any]] = None
    graficos: Dict[str, Any] = Field(default_factory=dict)
    checklist_manual: Dict[str, bool] = Field(default_factory=dict)

    status: StatusModelo = "rascunho"
    versao: int = 1
    origem_versao_id: Optional[str] = None   # modelo do qual esta versão derivou
    homologado_em: Optional[datetime] = None
    estimado_em: Optional[datetime] = None
    criado_em: datetime = Field(default_factory=_now)
    atualizado_em: datetime = Field(default_factory=_now)


# ── Corpos de requisição ─────────────────────────────────────────────────────
class CriarModeloBody(BaseModel):
    nome: Optional[str] = None
    avaliacao_id: Optional[str] = None
    ptam_id: Optional[str] = None
    tipo_imovel: TipoImovel = "urbano"
    norma: Optional[str] = None
    amostra: List[DadoAmostra] = Field(default_factory=list)
    especificacao: Optional[EspecificacaoSpec] = None
    avaliando: Dict[str, Any] = Field(default_factory=dict)
    area_total_avaliando: Optional[float] = None


class EspecificacaoBody(BaseModel):
    especificacao: EspecificacaoSpec
    avaliando: Optional[Dict[str, Any]] = None
    area_total_avaliando: Optional[float] = None
    nome: Optional[str] = None


class ItemAmostraBody(BaseModel):
    """Marca um dado como utilizado/descartado. Motivo é OBRIGATÓRIO ao descartar."""
    dado_id: str
    utilizado: bool
    motivo_descarte: Optional[str] = None


class AmostraBody(BaseModel):
    itens: List[ItemAmostraBody] = Field(default_factory=list)
    substituir: Optional[List[DadoAmostra]] = None   # troca a amostra inteira


class PredizerBody(BaseModel):
    avaliando: Optional[Dict[str, Any]] = None
    area_total_avaliando: Optional[float] = None


class HomologarBody(BaseModel):
    checklist_manual: Dict[str, bool] = Field(default_factory=dict)
    ptam_id: Optional[str] = None
    forcar: bool = False        # homologar mesmo sem Grau III (registra o motivo)
    observacao: Optional[str] = None


class ImportarAmostrasBody(BaseModel):
    """Puxa dados de `amostras_mercado` para dentro do modelo."""
    categoria: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    limite: int = 200
    campos: List[str] = Field(default_factory=list)   # variáveis a trazer
