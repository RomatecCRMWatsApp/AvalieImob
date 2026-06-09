# @module models.amostra_mercado — Modelos Pydantic v2 do Banco Global de Amostras de Mercado v2.
#
# Repositório global de paradigmas (elementos comparativos — Método Comparativo Direto,
# NBR 14653). Alimentado manualmente (modais Urbano/Rural) e por sincronização automática
# a partir dos PTAMs (market_samples). Sempre isolado por user_id (multi-tenant).
#
# Convenções do projeto:
#   - id: str uuid (igual a Ptam/Evaluation) — NÃO ObjectId.
#   - Toda query/insert inclui user_id.
#   - Áreas SEMPRE armazenadas em m²; valores unitários derivados (R$/m², R$/ha).
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import date, datetime
from models.common import _id, _now


# ─── URBANO ────────────────────────────────────────────────────────────────────
class AmostraUrbanaBase(BaseModel):
    # extra="allow": tolera campos novos do form sem quebrar o contrato.
    model_config = ConfigDict(extra="allow")

    # IDENTIFICAÇÃO
    referencia: str
    tipo_imovel: Literal[
        "Casa", "Apartamento", "Terreno",
        "Sala Comercial", "Galpão", "Loja",
        "Chácara Urbana", "Outro",
    ] = "Casa"
    categoria: Literal["urbano"] = "urbano"

    # LOCALIZAÇÃO
    endereco: Optional[str] = None
    bairro: str = ""
    municipio: str = "Açailândia"
    uf: str = "MA"

    # ÁREA
    area_total_m2: float = 0
    area_construida_m2: Optional[float] = None
    area_terreno_m2: Optional[float] = None

    # CARACTERÍSTICAS
    padrao_construtivo: Optional[Literal["Simples", "Normal", "Bom", "Alto", "Luxo"]] = None
    estado_conservacao: Optional[Literal["Novo", "Bom", "Regular", "Precário", "Em Ruínas"]] = None
    idade_anos: Optional[int] = None

    # AMBIENTES (quantidade — só vai ao laudo se > 0)
    sala_estar: Optional[int] = 0
    sala_jantar_copa: Optional[int] = 0
    cozinha: Optional[int] = 0
    quarto_social: Optional[int] = 0
    suite_simples: Optional[int] = 0
    suite_master: Optional[int] = 0
    banheiro_social: Optional[int] = 0
    lavabo: Optional[int] = 0
    area_servico: Optional[int] = 0
    varanda_sacada: Optional[int] = 0
    varanda_gourmet: Optional[int] = 0
    escritorio: Optional[int] = 0
    despensa: Optional[int] = 0
    piscina: Optional[int] = 0
    garagem: Optional[int] = 0

    # TRANSAÇÃO
    valor_rs: float = 0
    rs_m2_calculado: Optional[float] = None
    tipo_amostra: Literal[
        "Oferta de Mercado", "Consolidada / Comercializada", "Aluguel",
    ] = "Oferta de Mercado"
    fonte: Optional[str] = None
    data_coleta: Optional[date] = None
    telefone_fonte: Optional[str] = None

    # MÍDIA
    foto_url: Optional[str] = None
    planta_baixa_url: Optional[str] = None
    link_anuncio: Optional[str] = None


# ─── RURAL ─────────────────────────────────────────────────────────────────────
class AmostraRuralBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    # IDENTIFICAÇÃO
    referencia: str
    tipo_imovel: Literal[
        "Fazenda", "Sítio", "Gleba", "Chácara Rural",
        "Terra Nua", "Área de Preservação", "Outro",
    ] = "Fazenda"
    categoria: Literal["rural"] = "rural"

    # LOCALIZAÇÃO
    denominacao: Optional[str] = None
    endereco_logradouro: Optional[str] = None
    bairro_localidade: Optional[str] = None
    municipio: str = "Açailândia"
    uf: str = "MA"

    # ÁREA
    area_m2: float = 0
    area_hectares: Optional[float] = None
    area_alqueires_mineiros: Optional[float] = None

    # CARACTERÍSTICAS RURAIS
    topografia: Optional[Literal[
        "Plano", "Suave Ondulado", "Ondulado",
        "Forte Ondulado", "Montanhoso", "Escarpado",
    ]] = None
    solo: Optional[Literal["Argiloso", "Arenoso", "Misto", "Rochoso", "Orgânico"]] = None
    recursos_hidricos: Optional[Literal[
        "Nenhum", "Nascente", "Rio / córrego", "Açude / represa", "Irrigação",
    ]] = None
    vegetacao: Optional[Literal[
        "Pastagem", "Pastagem Degradada", "Capoeira",
        "Mata Nativa", "Reflorestamento", "Lavoura", "Mista",
    ]] = None
    atividade_principal: Optional[Literal[
        "Pecuária", "Agricultura", "Misto", "Extrativismo", "Piscicultura", "Inativo",
    ]] = None
    lotacao_ua_ha: Optional[float] = None
    benfeitorias: Optional[Literal["Nenhuma", "Simples", "Médio", "Bom", "Alto"]] = None
    sede_casa: Optional[Literal["Nenhuma", "Simples", "Normal", "Bom"]] = None

    # TRANSAÇÃO
    valor_rs: float = 0
    rs_ha_calculado: Optional[float] = None
    tipo_amostra: Literal["Oferta de Mercado", "Consolidada / Comercializada"] = "Oferta de Mercado"
    fonte: Optional[str] = None
    data_coleta: Optional[date] = None
    telefone_fonte: Optional[str] = None

    # MÍDIA
    foto_url: Optional[str] = None
    planta_baixa_url: Optional[str] = None
    link_anuncio: Optional[str] = None


# ─── PERSISTÊNCIA (campos de controle adicionados na gravação) ──────────────────
class AmostraUrbana(AmostraUrbanaBase):
    id: str = Field(default_factory=_id)
    user_id: str
    origem: Literal["manual", "ptam"] = "manual"
    ptam_origem_id: Optional[str] = None
    ptam_origem_numero: Optional[str] = None
    ativo: bool = True
    criado_em: datetime = Field(default_factory=_now)
    atualizado_em: datetime = Field(default_factory=_now)


class AmostraRural(AmostraRuralBase):
    id: str = Field(default_factory=_id)
    user_id: str
    origem: Literal["manual", "ptam"] = "manual"
    ptam_origem_id: Optional[str] = None
    ptam_origem_numero: Optional[str] = None
    ativo: bool = True
    criado_em: datetime = Field(default_factory=_now)
    atualizado_em: datetime = Field(default_factory=_now)
