# @module models.ptam — Modelos Pydantic para PTAM, IA, pagamentos e perfil avaliador
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.common import _id, _now


class PtamSample(BaseModel):
    number: Optional[int] = 0
    neighborhood: Optional[str] = ""
    area_total: Optional[float] = 0
    value: Optional[float] = 0
    value_per_sqm: Optional[float] = 0
    description: Optional[str] = ""
    source: Optional[str] = ""


class PtamImpactArea(BaseModel):
    name: str = "Área de Impacto 01"
    classification: Optional[str] = "Rural"
    area_sqm: float = 0
    unit_value: float = 0
    total_value: float = 0
    majoration_note: Optional[str] = ""
    samples: List[PtamSample] = Field(default_factory=list)
    notes: Optional[str] = ""


class PtamMarketSample(BaseModel):
    address: Optional[str] = ""
    neighborhood: Optional[str] = ""
    area: Optional[float] = 0
    value: Optional[float] = 0
    value_per_sqm: Optional[float] = 0
    source: Optional[str] = ""
    collection_date: Optional[str] = ""
    contact_phone: Optional[str] = ""
    notes: Optional[str] = ""
    foto: Optional[str] = None
    tipo_amostra: Optional[str] = "oferta"


class PtamBase(BaseModel):
    # Seção 1 — Identificação do Solicitante
    numero_ptam: Optional[str] = None
    number: Optional[str] = ""
    solicitante: Optional[str] = ""
    solicitante_nome: Optional[str] = ""
    solicitante_cpf_cnpj: Optional[str] = ""
    solicitante_endereco: Optional[str] = ""
    solicitante_telefone: Optional[str] = ""
    solicitante_email: Optional[str] = ""

    # Seção 2 — Objetivo da Avaliação
    purpose: Optional[str] = ""
    finalidade: Optional[str] = ""
    finalidade_outros: Optional[str] = ""
    judicial_process: Optional[str] = ""
    judicial_action: Optional[str] = ""
    forum: Optional[str] = ""
    requerente: Optional[str] = ""
    requerido: Optional[str] = ""
    judge: Optional[str] = ""

    # Seção 3 — Identificação do Imóvel
    property_label: Optional[str] = ""
    property_type: Optional[str] = ""
    property_address: Optional[str] = ""
    property_neighborhood: Optional[str] = ""
    property_city: Optional[str] = ""
    property_state: Optional[str] = ""
    property_cep: Optional[str] = ""
    property_matricula: Optional[str] = ""
    property_cartorio: Optional[str] = ""
    property_gps_lat: Optional[str] = ""
    property_gps_lng: Optional[str] = ""
    property_owner: Optional[str] = ""
    proprietarios: Optional[List[dict]] = []
    property_area_ha: float = 0
    property_area_sqm: float = 0
    property_confrontations: Optional[str] = ""
    property_description: Optional[str] = ""

    # Seção 4 — Caracterização da Região
    regiao_infraestrutura: Optional[str] = ""
    regiao_servicos_publicos: Optional[str] = ""
    regiao_uso_predominante: Optional[str] = ""
    regiao_padrao_construtivo: Optional[str] = ""
    regiao_tendencia_mercado: Optional[str] = ""
    regiao_observacoes: Optional[str] = ""

    # Seção 3 — Vistoria Técnica (15 sub-seções PTAM nº 7010)
    vistoria_date: Optional[str] = ""
    vistoria_responsavel: Optional[str] = ""
    vistoria_condicoes: Optional[str] = ""
    vistoria_objective: Optional[str] = ""
    vistoria_methodology: Optional[str] = ""
    # Sub-seções de caracterização física
    topography: Optional[str] = ""
    soil_vegetation: Optional[str] = ""
    uso_atual: Optional[str] = ""           # 3.1 Uso Atual
    cobertura_vegetal: Optional[str] = ""   # 3.2 Cobertura Vegetal
    hidrografia: Optional[str] = ""        # 3.3 Hidrografia
    benfeitorias: Optional[str] = ""
    infraestrutura_interna: Optional[str] = "" # 3.5 Infra-estrutura interna
    accessibility: Optional[str] = ""
    urban_context: Optional[str] = ""
    conservation_state: Optional[str] = ""
    situacao_fundiaria: Optional[str] = ""  # 3.8 Situação Fundiária
    passivo_ambiental: Optional[str] = ""   # 3.9 Passivo Ambiental
    potencial_exploratorio: Optional[str] = "" # 3.10 Potencial Exploratório
    aspectos_legais: Optional[str] = ""    # 3.11 Aspectos Legais/Restrições
    restricoes_uso: Optional[str] = ""     # 3.12 Restrições de Uso
    vistoria_synthesis: Optional[str] = ""

    # Seção 5 — Caracterização do Imóvel
    imovel_area_terreno: Optional[float] = 0
    imovel_area_construida: Optional[float] = 0
    imovel_area_a_considerar: Optional[float] = None  # Área efetiva usada no cálculo do valor final
    imovel_idade: Optional[int] = 0
    imovel_estado_conservacao: Optional[str] = ""
    imovel_padrao_acabamento: Optional[str] = ""
    imovel_num_quartos: Optional[int] = 0
    imovel_num_banheiros: Optional[int] = 0
    imovel_num_vagas: Optional[int] = 0
    imovel_piscina: Optional[bool] = False
    imovel_caracteristicas_adicionais: Optional[str] = ""

    # Fotos e Documentos
    fotos_imovel: List[str] = Field(default_factory=list)
    fotos_documentos: List[str] = Field(default_factory=list)

    # Seção 6 — Amostras de Mercado
    market_samples: List[PtamMarketSample] = Field(default_factory=list)
    market_analysis: Optional[str] = ""

    # Seção 7 — Metodologia
    methodology: Optional[str] = "Método Comparativo Direto de Dados de Mercado"
    methodology_justification: Optional[str] = ""

    # Seção 8 — Cálculos e Tratamento Estatístico
    calc_media: Optional[float] = 0
    calc_mediana: Optional[float] = 0
    calc_desvio_padrao: Optional[float] = 0
    calc_coef_variacao: Optional[float] = 0
    calc_grau_fundamentacao: Optional[str] = ""
    calc_fatores_homogeneizacao: Optional[str] = ""
    calc_observacoes: Optional[str] = ""

    # Seção 9 — Resultado da Avaliação
    resultado_valor_unitario: Optional[float] = 0
    resultado_valor_total: Optional[float] = 0
    resultado_intervalo_inf: Optional[float] = 0
    resultado_intervalo_sup: Optional[float] = 0
    resultado_data_referencia: Optional[str] = ""
    resultado_prazo_validade: Optional[str] = ""
    total_indemnity: float = 0
    total_indemnity_words: Optional[str] = ""

    # Seção 10 — Considerações Finais
    consideracoes_ressalvas: Optional[str] = ""
    consideracoes_pressupostos: Optional[str] = ""
    consideracoes_limitacoes: Optional[str] = ""
    responsavel_nome: Optional[str] = ""
    responsavel_creci: Optional[str] = ""
    responsavel_cnai: Optional[str] = ""
    conclusion_text: Optional[str] = ""
    conclusion_date: Optional[str] = ""
    conclusion_city: Optional[str] = ""

    # Campos normatizados adicionais NBR 14653
    documentos_analisados: List[str] = Field(default_factory=list)
    zoneamento: Optional[str] = ""
    vistoria_responsavel: Optional[str] = ""
    vistoria_condicoes: Optional[str] = ""
    grau_precisao: Optional[str] = "I"
    campo_arbitrio_min: Optional[float] = 0
    campo_arbitrio_max: Optional[float] = 0
    prazo_validade_meses: Optional[int] = 6
    tipo_profissional: Optional[str] = "corretor"
    registro_profissional: Optional[str] = ""
    art_rrt_numero: Optional[str] = ""

    # Campos Rurais
    certificacao_sigef: Optional[str] = None
    cadastro_incra: Optional[str] = None
    ccir: Optional[str] = None
    nirf_cib: Optional[str] = None
    car: Optional[str] = None
    perimetro_m: Optional[float] = None
    doc_mapa_sigef: Optional[List[str]] = []
    doc_memorial_descritivo: Optional[List[str]] = []
    doc_ccir: Optional[List[str]] = []
    doc_itr: Optional[List[str]] = []
    doc_car: Optional[List[str]] = []

    # Ponderância
    ponderancia_media: Optional[float] = None
    ponderancia_limite_inf: Optional[float] = None
    ponderancia_limite_sup: Optional[float] = None
    ponderancia_eliminadas: Optional[List[int]] = []
    ponderancia_valor_final: Optional[float] = None

    # Método de Avaliação / Depreciação
    metodo_avaliacao: Optional[str] = None
    metodo_params: Optional[dict] = {}
    depreciacao_percentual: Optional[float] = None
    valor_depreciacao: Optional[float] = None
    valor_benfeitoria: Optional[float] = None
    valor_terreno_calc: Optional[float] = None
    valor_total_metodo: Optional[float] = None

    # Legacy — Impact areas
    impact_areas: List[PtamImpactArea] = Field(default_factory=list)

    # Seção 8/9 — Avaliação por Áreas (Área 01 e Área 02 — PTAM nº 7010)
    area_01_tipo: Optional[str] = ""        # ex: "Terra Nua", "Pastagem", "Cultura"
    area_01_dados: Optional[str] = ""       # Descrição detalhada e cálculo
    area_01_valor: Optional[float] = None   # Valor total calculado (R$)
    area_02_tipo: Optional[str] = ""
    area_02_dados: Optional[str] = ""
    area_02_valor: Optional[float] = None

    # Meta
    status: str = "Rascunho"


class Ptam(PtamBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# ---------- AI ----------
class AIMessage(BaseModel):
    session_id: str
    message: str


class AIMessageResponse(BaseModel):
    session_id: str
    reply: str


class AIHistoryItem(BaseModel):
    role: str
    content: str
    ts: datetime


# ---------- Payments / Transactions ----------
class Transaction(BaseModel):
    id: str = Field(default_factory=_id)
    user_id: str
    plan_id: str
    amount: float
    status: str = "pending"
    mp_payment_id: str = ""
    created_at: datetime = Field(default_factory=_now)


class CreatePreferenceRequest(BaseModel):
    plan_id: str


# ---------- Perfil Avaliador ----------
class RegistroProfissional(BaseModel):
    tipo: str
    numero: str
    uf: str = ""
    validade: Optional[str] = None
    status: str = "ativo"


class Formacao(BaseModel):
    tipo: str
    curso: str
    instituicao: str
    ano_conclusao: int
    carga_horaria: Optional[int] = None


class Experiencia(BaseModel):
    cargo: str
    empresa: str
    periodo_inicio: str
    periodo_fim: Optional[str] = None
    descricao: str = ""


class PerfilAvaliadorBase(BaseModel):
    nome_completo: str = ""
    foto_perfil: Optional[str] = None
    cpf: str = ""
    rg: str = ""
    rg_orgao: str = ""
    bio_resumo: str = ""
    registros: List[RegistroProfissional] = []
    formacoes: List[Formacao] = []
    experiencias: List[Experiencia] = []
    especializacoes: List[str] = []
    habilitacoes: List[str] = []
    tribunais_cadastrado: List[str] = []
    bancos_habilitado: List[str] = []
    telefone: str = ""
    email_profissional: str = ""
    site: str = ""
    endereco_escritorio: str = ""
    cidade: str = ""
    uf: str = ""
    cep: str = ""
    empresa_nome: str = ""
    empresa_cnpj: str = ""
    empresa_razao_social: str = ""
    areas_atuacao: List[str] = []
    membro_associacoes: List[str] = []
    numero_laudos_emitidos: int = 0


class PerfilAvaliador(PerfilAvaliadorBase):
    id: str = Field(default_factory=_id)
    user_id: str = ""
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
