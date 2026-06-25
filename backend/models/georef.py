# @module models.georef — Topografia & Geo (Georreferenciamento / Requerimentos Cartoriais)
#
# Modelos Pydantic v2 do módulo Topografia & Geo. Espelha o SIGEF/INCRA: o usuário
# sobe Memorial + Mapa + CCIR + documento do cliente, o extractor popula estes
# modelos e os geradores produzem Memorial, Requerimento, DRL(s), Laudo Técnico,
# Shapefile (Prov. CNJ 195/2025) e Dossiê consolidado.
#
# Convenções do projeto: id = uuid string (sem alias _id), isolamento por user_id,
# datetime timezone-aware, persistência via model_dump(mode="json").
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


def _uid() -> str:
    return str(uuid.uuid4())


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────────
# Vértice da poligonal (linha da tabela "DESCRIÇÃO DA PARCELA" do SIGEF)
# ──────────────────────────────────────────────────────────────────────────────
class Vertice(BaseModel):
    codigo: str = ""                       # FQNS-M-A016
    longitude_dms: Optional[str] = None    # -47°15'52,043"
    latitude_dms: Optional[str] = None     # -5°11'46,392"
    longitude: Optional[float] = None      # decimal (EPSG:4674)
    latitude: Optional[float] = None
    altitude: Optional[float] = None
    tipo: Optional[str] = None             # M / P / V / O (do código do vértice)
    # segmento vante
    vante_codigo: Optional[str] = None
    azimute: Optional[str] = None          # 147°02'
    distancia: Optional[float] = None      # m
    confrontacao_raw: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Confrontante agrupado (para a DRL — uma por confrontante)
# ──────────────────────────────────────────────────────────────────────────────
class Confrontante(BaseModel):
    key: str = ""                          # matricula|descricao (chave de agrupamento)
    nome: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    imovel: Optional[str] = None
    matricula: Optional[str] = None
    cns: Optional[str] = None
    incra: Optional[str] = None
    certificacao: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None             # "particular" | "via_publica" | "proprio"
    segmentos: List[str] = Field(default_factory=list)  # códigos de vértice (origem)


# ──────────────────────────────────────────────────────────────────────────────
# Cadeia dominial (cada ato da matrícula: R-1, R-2, Av-1...)
# ──────────────────────────────────────────────────────────────────────────────
class CadeiaDominialAto(BaseModel):
    ordem: int = 0
    ato: str = ""                          # "R-1", "Av-3", "Matrícula", "Transcrição"
    tipo: Optional[str] = None             # compra e venda, doação, partilha, georref...
    data: Optional[str] = None
    partes: Optional[str] = None           # transmitente -> adquirente
    titulo: Optional[str] = None           # escritura, formal de partilha, etc.
    area_ha: Optional[float] = None
    observacao: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Dados do imóvel (cabeçalho do memorial + CCIR + certidão)
# ──────────────────────────────────────────────────────────────────────────────
class DadosImovel(BaseModel):
    denominacao: Optional[str] = None
    proprietario_nome: Optional[str] = None
    proprietario_cpf_cnpj: Optional[str] = None
    proprietario_nacionalidade: Optional[str] = "Brasileira"
    proprietario_estado_civil: Optional[str] = None
    proprietario_profissao: Optional[str] = None
    proprietario_endereco: Optional[str] = None
    matricula: Optional[str] = None
    livro: Optional[str] = None
    natureza_area: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    cod_incra: Optional[str] = None        # 9510990828483
    cartorio_cns: Optional[str] = None     # 03.169-0
    cartorio_nome: Optional[str] = None    # Serventia Extrajudicial de... (do CNS)
    cartorio_municipio: Optional[str] = None  # comarca/cidade da serventia (do CNS)
    cartorio_uf: Optional[str] = None      # UF da serventia (do CNS)
    area_ha: Optional[float] = None        # 96.8180
    perimetro_m: Optional[float] = None    # 4095.92
    sistema_geodesico: Optional[str] = "SIRGAS 2000"
    certificacao_sigef: Optional[str] = None
    data_certificacao: Optional[str] = None
    # CCIR
    ccir_codigo: Optional[str] = None
    ccir_area_total: Optional[float] = None
    ccir_classificacao: Optional[str] = None
    ccir_modulo_fiscal: Optional[float] = None
    ccir_fmp: Optional[float] = None
    # certidão de matrícula / cadeia dominial
    certidao_numero: Optional[str] = None
    certidao_cns: Optional[str] = None
    cadeia_dominial: List[CadeiaDominialAto] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Responsável Técnico (preenchido do memorial SIGEF + perfil do avaliador)
# ──────────────────────────────────────────────────────────────────────────────
class ResponsavelTecnico(BaseModel):
    nome: str = "José Romário Pinto Bezerra"
    formacao: str = "Técnico Industrial em Agrimensura"
    conselho: str = "CFT/MA 01209185369"
    credenciamento_incra: str = "FQNS"
    art_trt: Optional[str] = None          # CFT2605953795-MA (do RT no SIGEF)
    cnai: Optional[str] = "031161"
    creci: Optional[str] = "CRECI/MA 4.705"


# ──────────────────────────────────────────────────────────────────────────────
# Projeto (documento raiz da collection georef_projetos)
# ──────────────────────────────────────────────────────────────────────────────
TipoServico = Literal[
    "georreferenciamento", "desmembramento", "remembramento",
    "desdobro", "retificacao", "certificacao",
]
StatusProjeto = Literal["rascunho", "extraido", "documentos_gerados", "concluido"]
TemaPdf = Literal["tradicional", "prime_i", "prime_ii"]


class Parcela(BaseModel):
    """Parcela resultante de desmembramento/remembramento (Parte II, III...).

    A 'Parte I' é o próprio topo do projeto (imovel/vertices/confrontantes);
    estas são as parcelas ADICIONAIS, cada uma com seu Memorial/Mapa próprios.
    """
    id: str = Field(default_factory=_uid)
    rotulo: str = ""                       # "Parte II"
    denominacao: Optional[str] = None
    natureza_area: Optional[str] = None
    area_ha: Optional[float] = None
    perimetro_m: Optional[float] = None
    sistema_geodesico: Optional[str] = "SIRGAS 2000"
    certificacao_sigef: Optional[str] = None
    vertices: List[Vertice] = Field(default_factory=list)
    confrontantes: List[Confrontante] = Field(default_factory=list)
    uploads: dict = Field(default_factory=dict)  # {memorial: {...}, mapa: {...}}


class GeorefProjeto(BaseModel):
    id: str = Field(default_factory=_uid)
    user_id: str = ""
    nome_projeto: str = ""
    tipo_servico: TipoServico = "georreferenciamento"
    status: StatusProjeto = "rascunho"
    imovel: DadosImovel = Field(default_factory=DadosImovel)
    responsavel_tecnico: ResponsavelTecnico = Field(default_factory=ResponsavelTecnico)
    vertices: List[Vertice] = Field(default_factory=list)
    confrontantes: List[Confrontante] = Field(default_factory=list)
    parcelas: List[Parcela] = Field(default_factory=list)  # parcelas ADICIONAIS (Parte II+)
    uploads: dict = Field(default_factory=dict)            # {memorial: key, mapa: key, ...}
    documentos_gerados: dict = Field(default_factory=dict)  # {memorial, requerimento, ...}
    campos_editados: dict = Field(default_factory=dict)     # flags p/ preservar edição manual
    tema_pdf: TemaPdf = "prime_i"
    completude: int = 0                                     # 0-100
    created_at: datetime = Field(default_factory=_agora)
    updated_at: datetime = Field(default_factory=_agora)


# ──────────────────────────────────────────────────────────────────────────────
# Payloads de API
# ──────────────────────────────────────────────────────────────────────────────
class CriarProjetoBody(BaseModel):
    nome_projeto: str
    tipo_servico: TipoServico = "georreferenciamento"
    tema_pdf: TemaPdf = "prime_i"


class AtualizarProjetoBody(BaseModel):
    """Atualização parcial — apenas campos enviados são gravados (exclude_unset)."""
    nome_projeto: Optional[str] = None
    tipo_servico: Optional[TipoServico] = None
    tema_pdf: Optional[TemaPdf] = None
    status: Optional[StatusProjeto] = None
    imovel: Optional[dict] = None
    responsavel_tecnico: Optional[dict] = None
    vertices: Optional[List[dict]] = None
    confrontantes: Optional[List[dict]] = None
    parcelas: Optional[List[dict]] = None


class AdicionarParcelaBody(BaseModel):
    rotulo: Optional[str] = None           # auto: "Parte II", "Parte III"...


class AssinarPecaBody(BaseModel):
    """Prepara uma peça do projeto p/ assinatura ICP-Brasil (módulo de assinatura)."""
    doc: str                               # memorial|laudo|requerimento|dossie|art_trt
    parcela: Optional[str] = None          # id da parcela ou "principal" (só p/ memorial)
    tema: Optional[TemaPdf] = None


class GerarDocumentosBody(BaseModel):
    documentos: List[str] = Field(
        default_factory=lambda: [
            "requerimento", "laudo_tecnico", "memorial", "drl", "shapefile", "dossie",
        ]
    )
    tema: Optional[TemaPdf] = None


# Resolve forward-refs (Pydantic v2)
DadosImovel.model_rebuild()
GeorefProjeto.model_rebuild()


# ──────────────────────────────────────────────────────────────────────────────
# Cálculo de completude (campos essenciais do imóvel + ≥1 confrontante + poligonal)
# ──────────────────────────────────────────────────────────────────────────────
_CAMPOS_OBRIGATORIOS_IMOVEL = [
    "denominacao", "proprietario_nome", "proprietario_cpf_cnpj", "matricula",
    "cod_incra", "municipio", "uf", "area_ha", "perimetro_m", "cartorio_nome",
]


def calcular_completude(projeto: dict) -> int:
    """% de preenchimento: campos do imóvel + ≥1 confrontante + poligonal fechável."""
    imovel = projeto.get("imovel") or {}
    total = len(_CAMPOS_OBRIGATORIOS_IMOVEL) + 2  # +confrontante +poligonal
    preenchidos = sum(1 for c in _CAMPOS_OBRIGATORIOS_IMOVEL if imovel.get(c))
    if projeto.get("confrontantes"):
        preenchidos += 1
    vertices = projeto.get("vertices") or []
    if len(vertices) >= 3:
        preenchidos += 1
    return int(round(100 * preenchidos / total)) if total else 0
