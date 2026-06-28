# @module models.geo_urbano — Topografia & Geo / Geo Urbano (Remembramento — Fase 1)
#
# Módulo IRMÃO do Georreferenciamento (rural/SIGEF). Atende imóveis URBANOS:
# Remembramento (unificação de lotes), e — nas fases seguintes — Desdobro,
# Retificação, REURB e Usucapião. O núcleo é a extração FIEL da certidão de
# inteiro teor (matrícula por matrícula) reconciliada com o BCI municipal, o
# Memorial gerado a partir da planilha do mapa, e o Requerimento em DUAS VIAS
# (Cartório de RI + Superintendência de Habitação e Regularização Fundiária).
#
# Convenções do projeto: id = uuid string (sem alias _id), isolamento por
# user_id, datetime timezone-aware, persistência via model_dump(mode="json").
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
# Enums
# ──────────────────────────────────────────────────────────────────────────────
TipoServico = Literal[
    "remembramento", "desdobro", "retificacao", "reurb", "usucapiao",
]
StatusProjeto = Literal["rascunho", "extracao", "conferencia", "assinatura", "concluido"]
TemaPdf = Literal["tradicional", "prime_i", "prime_ii"]
# Regularidade fiscal de CADA matrícula: CND negativa vigente OU guia paga (DAM
# + comprovante de quitação) quando havia débito em aberto.
ViaRegularidade = Literal["cnd", "guia_paga"]


# ──────────────────────────────────────────────────────────────────────────────
# Confrontação registral (uma por lado da matrícula — FIEL à certidão)
# ──────────────────────────────────────────────────────────────────────────────
class Confrontacao(BaseModel):
    lado: str = ""                 # frente | lateral_direita | lateral_esquerda | fundo
    medida_m: Optional[float] = None
    confrontante: Optional[str] = None  # "Rua Inglaterra", "Lote nº 02", ...


# Ato da cadeia dominical de uma matrícula (R-/AV-)
class CadeiaAto(BaseModel):
    ato: str = ""                  # "R-01/34.161"
    protocolo: Optional[str] = None
    data: Optional[str] = None
    tipo: Optional[str] = None     # "Compra e Venda", "Doação"...
    transmitente: Optional[str] = None
    adquirente: Optional[str] = None


# Titular (proprietário) — PF ou PJ
class Titular(BaseModel):
    nome: Optional[str] = None
    doc: Optional[str] = None      # CPF/CNPJ


# ──────────────────────────────────────────────────────────────────────────────
# Matrícula de ORIGEM (imóvel a ser remembrado) — extraída da certidão
# ──────────────────────────────────────────────────────────────────────────────
class Matricula(BaseModel):
    id: str = Field(default_factory=_uid)
    ordem: int = 0                 # ordem de transcrição no requerimento
    matricula: str = ""            # "34.161"
    livro: Optional[str] = None    # "2-HN"
    folhas: Optional[str] = None   # "70"
    cri: Optional[str] = None      # Cartório do 1º Ofício Extrajudicial de Açailândia/MA
    natureza: Optional[str] = "UM TERRENO"
    lote_origem: Optional[str] = None  # "01"
    quadra: Optional[str] = None       # "41"
    loteamento: Optional[str] = None   # "Parque das Nações"
    endereco: Optional[str] = None     # "Rua Inglaterra"
    numero: Optional[str] = None
    cod_imovel: Optional[str] = None       # casa com o BCI
    loc_cartografica: Optional[str] = None  # 01.10.041.0001.00001
    area_m2: Optional[float] = None
    confrontacoes: List[Confrontacao] = Field(default_factory=list)
    registro_anterior: Optional[str] = None
    proprietario_registral: Titular = Field(default_factory=Titular)
    cadeia: List[CadeiaAto] = Field(default_factory=list)
    texto_certidao_bruto: Optional[str] = None  # recorte literal p/ auditoria
    extraido_de: Optional[str] = None           # id do documento de origem


# ──────────────────────────────────────────────────────────────────────────────
# BCI — Boletim de Cadastro Imobiliário (municipal)
# ──────────────────────────────────────────────────────────────────────────────
class BCI(BaseModel):
    id: str = Field(default_factory=_uid)
    matricula_id: Optional[str] = None     # casa com a matrícula de mesmo cod_imovel
    cod_imovel: Optional[str] = None
    loc_cartografica: Optional[str] = None
    inscricao_contribuinte: Optional[str] = None
    proprietario_cadastral: Titular = Field(default_factory=Titular)
    natureza: Optional[str] = None
    situacao: Optional[str] = None
    testada_principal_m: Optional[float] = None
    profundidade_m: Optional[float] = None
    area_terreno_m2: Optional[float] = None
    area_edificada_m2: Optional[float] = None
    endereco: Optional[str] = None
    bairro: Optional[str] = None
    data_cadastro: Optional[str] = None
    extraido_de: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Vértice da poligonal resultante (planilha do mapa de remembramento)
# ──────────────────────────────────────────────────────────────────────────────
class Vertice(BaseModel):
    id: str = Field(default_factory=_uid)
    ordem: int = 0
    de: str = ""                   # FQNS-P-PDN1
    para: Optional[str] = None     # FQNS-P-PDN2
    lote_resultante_id: Optional[str] = None   # desdobro: a qual lote pertence
    origem_mapa: Optional[str] = None          # retificação: "atual" | "retificado"
    coord_n: Optional[float] = None   # Norte (Y) — UTM
    coord_e: Optional[float] = None   # Este (X) — UTM
    azimute: Optional[str] = None     # 150°03'29"
    distancia_m: Optional[float] = None
    fator_k: Optional[float] = None
    latitude: Optional[str] = None    # 04°56'15,475979"S
    longitude: Optional[str] = None   # 47°27'59,462032"W
    confrontante_lado: Optional[str] = None  # puxado por lado p/ o memorial


# ──────────────────────────────────────────────────────────────────────────────
# Parte (requerente PF/PJ, cônjuge, representante, sócio)
# ──────────────────────────────────────────────────────────────────────────────
PapelParte = Literal["requerente", "conjuge", "representante", "socio"]
TipoPessoa = Literal["fisica", "juridica"]


class Parte(BaseModel):
    id: str = Field(default_factory=_uid)
    papel: PapelParte = "requerente"
    tipo_pessoa: TipoPessoa = "juridica"
    # PJ
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    nire: Optional[str] = None
    junta: Optional[str] = None
    sede: Optional[str] = None
    # PF / representante
    nome: Optional[str] = None
    cpf: Optional[str] = None
    rg: Optional[str] = None
    cnh: Optional[str] = None
    nacionalidade: Optional[str] = "brasileiro"
    estado_civil: Optional[str] = None
    profissao: Optional[str] = None
    nascimento: Optional[str] = None
    filiacao: Optional[str] = None
    regime_bens: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None     # WhatsApp p/ enviar o link de assinatura
    email: Optional[str] = None
    documentos: List[str] = Field(default_factory=list)  # ids de db.images / R2


# ──────────────────────────────────────────────────────────────────────────────
# Regularidade de IPTU por matrícula (CND OU guia paga)
# ──────────────────────────────────────────────────────────────────────────────
class IptuRegularidade(BaseModel):
    id: str = Field(default_factory=_uid)
    matricula_id: Optional[str] = None
    via_regularidade: ViaRegularidade = "cnd"
    situacao: Optional[str] = None  # cnd_negativa | debito_parcelado | debito_aberto | quitado
    # via CND
    cnd_numero: Optional[str] = None
    cnd_validade: Optional[str] = None
    # via guia paga
    acordo_numero: Optional[str] = None
    valor: Optional[float] = None
    vencimento: Optional[str] = None
    exercicios: List[str] = Field(default_factory=list)
    comprovante_pagamento_id: Optional[str] = None
    extraido_de: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Destinatários (Cartório de RI + Superintendência) — snapshot no projeto,
# pré-preenchido com a Comarca de Açailândia/MA (editável na conferência).
# ──────────────────────────────────────────────────────────────────────────────
class DestinatarioCartorio(BaseModel):
    nome: str = "Cartório do 1º Ofício Extrajudicial da Comarca de Açailândia – MA"
    endereco: str = "Rua Bom Jesus, 236 – Centro – Açailândia/MA"
    cnpj: str = "07.504.590/0001-39"
    titular: str = "Bel. Maria Ester R. de Sampaio – Notária e Registradora"


class DestinatarioSuperintendencia(BaseModel):
    nome: str = "Superintendência de Habitação e Regularização Fundiária"
    orgao: str = "Prefeitura Municipal de Açailândia – MA"
    responsavel: str = "Davi Alexandre Sampaio Camargo"
    portaria: str = "019/2025 - GAB"
    # Carimbo/assinatura do ÓRGÃO (imagens base64 data-uri opcionais) — aplicados
    # quando o operador registra a aprovação (a Superintendência é externa).
    carimbo_b64: Optional[str] = None
    assinatura_b64: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Fluxo de Aprovação & Assinaturas (Addendum §2.2) — embutido no projeto.
# ──────────────────────────────────────────────────────────────────────────────
StatusAprovacao = Literal[
    "rascunho", "assinatura_partes", "assinatura_tecnico",
    "enviado_superintendencia", "aprovado", "oficio_emitido", "protocolado",
]


class AprovacaoTecnico(BaseModel):
    assinado: bool = False
    em: Optional[str] = None
    assinatura_id: Optional[str] = None       # peças: memorial + mapa


class AprovacaoProprietario(BaseModel):
    parte_id: Optional[str] = None
    requerimento: bool = False                 # assinou as 2 vias do requerimento
    art_trt: bool = False


class AprovacaoSuperintendencia(BaseModel):
    responsavel: Optional[str] = None
    portaria: Optional[str] = None
    enviado_em: Optional[str] = None
    memorial_aprovado: bool = False
    mapa_aprovado: bool = False
    aprovado_em: Optional[str] = None
    oficio_emitido: bool = False
    oficio_numero: Optional[str] = None
    oficio_em: Optional[str] = None


class Aprovacao(BaseModel):
    tecnico: AprovacaoTecnico = Field(default_factory=AprovacaoTecnico)
    proprietarios: List[AprovacaoProprietario] = Field(default_factory=list)
    superintendencia: AprovacaoSuperintendencia = Field(default_factory=AprovacaoSuperintendencia)
    enviado_superintendencia: bool = False
    campos: List[dict] = Field(default_factory=list)  # posições por papel (positioner)
    status_geral: StatusAprovacao = "rascunho"


# ──────────────────────────────────────────────────────────────────────────────
# Lote resultante (Desdobro — 1 matrícula-mãe → N lotes filhos)
# ──────────────────────────────────────────────────────────────────────────────
class LoteResultante(BaseModel):
    id: str = Field(default_factory=_uid)
    ordem: int = 0
    denominacao: Optional[str] = None          # "Lote 01-A"
    area_declarada_m2: Optional[float] = None
    area_calculada_m2: Optional[float] = None
    perimetro_m: Optional[float] = None
    cmi_resultante: Optional[str] = None
    confrontacoes: List[Confrontacao] = Field(default_factory=list)
    vertices: List[Vertice] = Field(default_factory=list)
    uploads: dict = Field(default_factory=dict)  # {mapa_desdobro: {...}}


# ──────────────────────────────────────────────────────────────────────────────
# Confrontante + DRL (Retificação — eixo geométrico, anuência do art. 213)
# ──────────────────────────────────────────────────────────────────────────────
TipoConfrontante = Literal["particular", "via_publica", "area_publica"]
StatusAnuencia = Literal["pendente", "assinada", "recusada", "notificado"]


class Anuencia(BaseModel):
    status: StatusAnuencia = "pendente"
    em: Optional[str] = None
    assinatura_id: Optional[str] = None


class ConfrontanteRetificacao(BaseModel):
    id: str = Field(default_factory=_uid)
    lado: Optional[str] = None
    confrontante: Optional[str] = None
    tipo: TipoConfrontante = "particular"     # via/área pública dispensam DRL
    doc: Optional[str] = None
    endereco: Optional[str] = None
    medida_m: Optional[float] = None
    telefone: Optional[str] = None            # p/ anuência via WhatsApp
    drl_doc_id: Optional[str] = None
    anuencia: Anuencia = Field(default_factory=Anuencia)


# ──────────────────────────────────────────────────────────────────────────────
# Projeto (documento raiz da collection geo_urbano_projetos)
# ──────────────────────────────────────────────────────────────────────────────
RetificacaoTipo = Literal["cadastral", "area_perimetro", "mista"]


class GeoUrbanoProjeto(BaseModel):
    id: str = Field(default_factory=_uid)
    user_id: str = ""
    numero: Optional[str] = None           # URB-AAAA-NNNN
    denominacao_imovel: str = ""           # "Lote 01 (remembrado) — Quadra 41 — Parque das Nações"
    tipo_servico: TipoServico = "remembramento"
    tema: TemaPdf = "prime_i"
    status: StatusProjeto = "rascunho"
    # localização / identificação do imóvel resultante
    municipio: Optional[str] = "Açailândia"
    uf: Optional[str] = "MA"
    bairro: Optional[str] = None
    loteamento: Optional[str] = None
    quadra: Optional[str] = None
    lote_resultante: Optional[str] = None
    endereco: Optional[str] = None
    cmi_resultante: Optional[str] = None
    cadastro_novo: Optional[str] = None
    cadastro_antigo: Optional[str] = None
    area_declarada_m2: Optional[float] = None   # soma registral declarada (oficial)
    area_calculada_m2: Optional[float] = None   # do polígono (shoelace)
    perimetro_m: Optional[float] = None
    trt_numero: Optional[str] = None
    # Desdobro (1 matrícula-mãe → N lotes resultantes)
    matricula_mae_id: Optional[str] = None
    area_mae_m2: Optional[float] = None
    qtd_lotes_resultantes: int = 0
    area_via_doacao_m2: float = 0.0            # >0 → desmembramento (abertura de via)
    lote_minimo_municipal_m2: Optional[float] = None
    testada_minima_m: Optional[float] = None
    lotes_resultantes: List[LoteResultante] = Field(default_factory=list)
    # Retificação (art. 213 Lei 6.015/73) — eixo cadastral e/ou geométrico
    retificacao_tipo: Optional[RetificacaoTipo] = None
    vertices_atual: List[Vertice] = Field(default_factory=list)  # geometria "antes"
    retificacao_analise: dict = Field(default_factory=dict)      # diffs confirmados
    confrontantes: List[ConfrontanteRetificacao] = Field(default_factory=list)  # DRL/anuência
    # coleções aninhadas
    matriculas: List[Matricula] = Field(default_factory=list)
    bci: List[BCI] = Field(default_factory=list)
    vertices: List[Vertice] = Field(default_factory=list)
    partes: List[Parte] = Field(default_factory=list)
    iptu: List[IptuRegularidade] = Field(default_factory=list)
    cartorio: DestinatarioCartorio = Field(default_factory=DestinatarioCartorio)
    superintendencia: DestinatarioSuperintendencia = Field(default_factory=DestinatarioSuperintendencia)
    aprovacao: Aprovacao = Field(default_factory=Aprovacao)
    responsavel_tecnico: dict = Field(default_factory=lambda: {
        "nome": "José Romário Pinto Bezerra",
        "formacao": "Técnico em Agrimensura",
        "conselho": "CFT/MA 01209185369",
        "credenciamento_incra": "FQNS",
    })
    uploads: dict = Field(default_factory=dict)             # {tipo: [{id,key,...}]}
    documentos_gerados: dict = Field(default_factory=dict)  # {tipo: {key, gerado_em}}
    campos_editados: dict = Field(default_factory=dict)
    completude: int = 0
    created_at: datetime = Field(default_factory=_agora)
    updated_at: datetime = Field(default_factory=_agora)


# ──────────────────────────────────────────────────────────────────────────────
# Payloads de API
# ──────────────────────────────────────────────────────────────────────────────
class CriarProjetoBody(BaseModel):
    denominacao_imovel: str
    tipo_servico: TipoServico = "remembramento"
    tema: TemaPdf = "prime_i"
    municipio: Optional[str] = "Açailândia"
    uf: Optional[str] = "MA"


class AtualizarProjetoBody(BaseModel):
    """Atualização parcial — só campos enviados são gravados (exclude_unset)."""
    denominacao_imovel: Optional[str] = None
    tipo_servico: Optional[TipoServico] = None
    tema: Optional[TemaPdf] = None
    status: Optional[StatusProjeto] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    bairro: Optional[str] = None
    loteamento: Optional[str] = None
    quadra: Optional[str] = None
    lote_resultante: Optional[str] = None
    endereco: Optional[str] = None
    cmi_resultante: Optional[str] = None
    cadastro_novo: Optional[str] = None
    cadastro_antigo: Optional[str] = None
    area_declarada_m2: Optional[float] = None
    perimetro_m: Optional[float] = None
    trt_numero: Optional[str] = None
    matriculas: Optional[List[dict]] = None
    bci: Optional[List[dict]] = None
    vertices: Optional[List[dict]] = None
    partes: Optional[List[dict]] = None
    iptu: Optional[List[dict]] = None
    cartorio: Optional[dict] = None
    superintendencia: Optional[dict] = None
    responsavel_tecnico: Optional[dict] = None
    # Desdobro
    area_mae_m2: Optional[float] = None
    qtd_lotes_resultantes: Optional[int] = None
    area_via_doacao_m2: Optional[float] = None
    lote_minimo_municipal_m2: Optional[float] = None
    testada_minima_m: Optional[float] = None
    lotes_resultantes: Optional[List[dict]] = None
    # Retificação
    retificacao_tipo: Optional[RetificacaoTipo] = None
    vertices_atual: Optional[List[dict]] = None
    retificacao_analise: Optional[dict] = None
    confrontantes: Optional[List[dict]] = None


class GerarDocumentosBody(BaseModel):
    documentos: List[str] = Field(
        default_factory=lambda: [
            "requerimento_cartorio", "requerimento_superintendencia",
            "memorial_descritivo", "cadeia_dominical", "dossie",
        ]
    )
    tema: Optional[TemaPdf] = None


class AssinarPecaBody(BaseModel):
    """Prepara uma peça do projeto p/ assinatura ICP-Brasil (módulo de assinatura)."""
    doc: str                       # requerimento_superintendencia | requerimento_cartorio | dossie | ...
    tema: Optional[TemaPdf] = None


class AprovacaoSuperintendenciaBody(BaseModel):
    """Operador registra a aprovação do órgão (Memorial e/ou Mapa)."""
    memorial_aprovado: Optional[bool] = None
    mapa_aprovado: Optional[bool] = None


class CamposAssinaturaBody(BaseModel):
    """Posições dos campos de assinatura por papel (positioner)."""
    campos: List[dict] = Field(default_factory=list)


# Resolve forward-refs (Pydantic v2)
Matricula.model_rebuild()
LoteResultante.model_rebuild()
ConfrontanteRetificacao.model_rebuild()
GeoUrbanoProjeto.model_rebuild()


# ──────────────────────────────────────────────────────────────────────────────
# Completude (matrículas + partes + vértices + identificação do resultante)
# ──────────────────────────────────────────────────────────────────────────────
def calcular_completude(projeto: dict) -> int:
    pontos = 0
    total = 6
    if projeto.get("matriculas"):
        pontos += 1
    # toda matrícula com confrontações
    mats = projeto.get("matriculas") or []
    if mats and all((m.get("confrontacoes") for m in mats)):
        pontos += 1
    if projeto.get("bci"):
        pontos += 1
    if projeto.get("partes"):
        pontos += 1
    if len(projeto.get("vertices") or []) >= 3:
        pontos += 1
    if projeto.get("area_declarada_m2") and projeto.get("cmi_resultante"):
        pontos += 1
    return int(round(100 * pontos / total)) if total else 0
