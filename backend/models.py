from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ---------- Users ----------
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "Profissional"
    crea: Optional[str] = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    email: str
    role: str = "Profissional"
    crea: str = ""
    plan: str = "mensal"
    plan_status: str = "inactive"  # active, inactive, expired
    plan_expires: Optional[datetime] = None
    company: Optional[str] = ""
    bio: Optional[str] = ""
    company_logo: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    role: str
    crea: str
    plan: str
    plan_status: str = "inactive"
    plan_expires: Optional[datetime] = None
    company: Optional[str] = ""
    bio: Optional[str] = ""
    company_logo: Optional[str] = None


class AuthResponse(BaseModel):
    user: UserPublic
    token: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    crea: Optional[str] = None
    company: Optional[str] = None
    bio: Optional[str] = None
    company_logo: Optional[str] = None


# ---------- Clients ----------
class ClientBase(BaseModel):
    name: str
    type: str = "Pessoa Física"  # or "Pessoa Jurídica"
    doc: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    city: Optional[str] = ""


class Client(ClientBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)


# ---------- Properties ----------
class PropertyBase(BaseModel):
    ref: str
    client_id: Optional[str] = ""
    type: str = "Urbano"  # Urbano | Rural | Garantia
    subtype: str = ""
    address: str = ""
    city: str = ""
    area: float = 0
    built_area: float = 0
    value: float = 0
    status: str = "Rascunho"


class Property(PropertyBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)


# ---------- Samples ----------
class SampleBase(BaseModel):
    ref: str
    type: str = ""
    area: float = 0
    value: float = 0
    source: Optional[str] = ""
    neighborhood: Optional[str] = ""
    date: Optional[str] = ""


class Sample(SampleBase):
    id: str = Field(default_factory=_id)
    user_id: str
    price_per_sqm: float = 0
    created_at: datetime = Field(default_factory=_now)


# ---------- Evaluations ----------
class EvaluationBase(BaseModel):
    type: str = "PTAM"
    method: str = "Comparativo Direto"
    client_id: Optional[str] = ""
    property_id: Optional[str] = ""
    value: float = 0
    status: Optional[str] = "Rascunho"
    samples: Optional[int] = 0
    notes: Optional[str] = ""


class Evaluation(EvaluationBase):
    id: str = Field(default_factory=_id)


# ---------- PTAM (Parecer Técnico de Avaliação Mercadológica) ----------

class PtamSample(BaseModel):
    """Amostra de impacto (legacy — mantido para compatibilidade com PDF)."""
    number: Optional[int] = 0
    neighborhood: Optional[str] = ""
    area_total: Optional[float] = 0
    value: Optional[float] = 0
    value_per_sqm: Optional[float] = 0
    description: Optional[str] = ""
    source: Optional[str] = ""


class PtamImpactArea(BaseModel):
    """Área de impacto (legacy — mantido para PTAMs de desapropriação)."""
    name: str = "Área de Impacto 01"
    classification: Optional[str] = "Rural"  # Rural | Urbana | Mista
    area_sqm: float = 0
    unit_value: float = 0
    total_value: float = 0
    majoration_note: Optional[str] = ""
    samples: List[PtamSample] = Field(default_factory=list)
    notes: Optional[str] = ""


class PtamMarketSample(BaseModel):
    """Amostra de mercado coletada para PTAM mercadológico (Seção 6)."""
    address: Optional[str] = ""
    neighborhood: Optional[str] = ""
    area: Optional[float] = 0
    value: Optional[float] = 0
    value_per_sqm: Optional[float] = 0
    source: Optional[str] = ""
    collection_date: Optional[str] = ""
    contact_phone: Optional[str] = ""
    notes: Optional[str] = ""
    foto: Optional[str] = None  # ID da imagem da amostra


class PtamBase(BaseModel):
    # ── Seção 1 — Identificação do Solicitante ────────────────────────────────
    number: Optional[str] = ""
    solicitante: Optional[str] = ""          # legacy alias
    solicitante_nome: Optional[str] = ""
    solicitante_cpf_cnpj: Optional[str] = ""
    solicitante_endereco: Optional[str] = ""
    solicitante_telefone: Optional[str] = ""
    solicitante_email: Optional[str] = ""

    # ── Seção 2 — Objetivo da Avaliação ──────────────────────────────────────
    purpose: Optional[str] = ""
    finalidade: Optional[str] = ""   # compra_venda | financiamento | judicial | inventario | locacao | garantia | outros
    finalidade_outros: Optional[str] = ""
    judicial_process: Optional[str] = ""
    judicial_action: Optional[str] = ""
    forum: Optional[str] = ""
    requerente: Optional[str] = ""
    requerido: Optional[str] = ""
    judge: Optional[str] = ""

    # ── Seção 3 — Identificação do Imóvel ────────────────────────────────────
    property_label: Optional[str] = ""
    property_type: Optional[str] = ""   # casa | apartamento | terreno | rural | comercial | industrial
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
    property_area_ha: float = 0
    property_area_sqm: float = 0
    property_confrontations: Optional[str] = ""
    property_description: Optional[str] = ""

    # ── Seção 4 — Caracterização da Região ───────────────────────────────────
    regiao_infraestrutura: Optional[str] = ""
    regiao_servicos_publicos: Optional[str] = ""
    regiao_uso_predominante: Optional[str] = ""
    regiao_padrao_construtivo: Optional[str] = ""
    regiao_tendencia_mercado: Optional[str] = ""
    regiao_observacoes: Optional[str] = ""
    # Legacy vistoria fields (backward compat with PDF)
    vistoria_date: Optional[str] = ""
    vistoria_objective: Optional[str] = ""
    vistoria_methodology: Optional[str] = ""
    topography: Optional[str] = ""
    soil_vegetation: Optional[str] = ""
    benfeitorias: Optional[str] = ""
    accessibility: Optional[str] = ""
    urban_context: Optional[str] = ""
    conservation_state: Optional[str] = ""
    vistoria_synthesis: Optional[str] = ""

    # ── Seção 5 — Caracterização do Imóvel ───────────────────────────────────
    imovel_area_terreno: Optional[float] = 0
    imovel_area_construida: Optional[float] = 0
    imovel_idade: Optional[int] = 0
    imovel_estado_conservacao: Optional[str] = ""   # otimo | bom | regular | ruim | pessimo
    imovel_padrao_acabamento: Optional[str] = ""    # alto | medio | simples | minimo
    imovel_num_quartos: Optional[int] = 0
    imovel_num_banheiros: Optional[int] = 0
    imovel_num_vagas: Optional[int] = 0
    imovel_piscina: Optional[bool] = False
    imovel_caracteristicas_adicionais: Optional[str] = ""

    # ── Seção 3 — Fotos e Documentos do Imóvel ───────────────────────────────
    fotos_imovel: List[str] = Field(default_factory=list)       # IDs de imagens do imóvel
    fotos_documentos: List[str] = Field(default_factory=list)   # IDs de documentos fotografados

    # ── Seção 6 — Amostras de Mercado ────────────────────────────────────────
    market_samples: List[PtamMarketSample] = Field(default_factory=list)
    market_analysis: Optional[str] = ""   # texto descritivo opcional

    # ── Seção 7 — Metodologia ─────────────────────────────────────────────────
    methodology: Optional[str] = "Método Comparativo Direto de Dados de Mercado"
    methodology_justification: Optional[str] = ""

    # ── Seção 8 — Cálculos e Tratamento Estatístico ──────────────────────────
    calc_media: Optional[float] = 0
    calc_mediana: Optional[float] = 0
    calc_desvio_padrao: Optional[float] = 0
    calc_coef_variacao: Optional[float] = 0
    calc_grau_fundamentacao: Optional[str] = ""   # I | II | III
    calc_fatores_homogeneizacao: Optional[str] = ""
    calc_observacoes: Optional[str] = ""

    # ── Seção 9 — Resultado da Avaliação ─────────────────────────────────────
    resultado_valor_unitario: Optional[float] = 0
    resultado_valor_total: Optional[float] = 0
    resultado_intervalo_inf: Optional[float] = 0
    resultado_intervalo_sup: Optional[float] = 0
    resultado_data_referencia: Optional[str] = ""
    resultado_prazo_validade: Optional[str] = ""
    total_indemnity: float = 0           # legacy alias
    total_indemnity_words: Optional[str] = ""

    # ── Seção 10 — Considerações Finais ──────────────────────────────────────
    consideracoes_ressalvas: Optional[str] = ""
    consideracoes_pressupostos: Optional[str] = ""
    consideracoes_limitacoes: Optional[str] = ""
    responsavel_nome: Optional[str] = ""
    responsavel_creci: Optional[str] = ""
    responsavel_cnai: Optional[str] = ""
    conclusion_text: Optional[str] = ""  # legacy
    conclusion_date: Optional[str] = ""  # legacy
    conclusion_city: Optional[str] = ""  # legacy

    # ── Seção NBR 14653 — Campos normatizados adicionais ─────────────────────
    # Documentação analisada (checklist)
    documentos_analisados: List[str] = Field(default_factory=list)  # matricula, IPTU, planta, escritura, fotos
    # Zoneamento conforme Plano Diretor
    zoneamento: Optional[str] = ""  # ZR1, ZR2, ZC, ZI, ZEI, etc.
    # Vistoria técnica detalhada
    vistoria_responsavel: Optional[str] = ""
    vistoria_condicoes: Optional[str] = ""  # condicoes de acesso / observacoes da vistoria
    # Grau de precisão (NBR 14653-1 item 9)
    grau_precisao: Optional[str] = "I"  # I | II | III
    # Campo de arbítrio ±15% (NBR 14653-1 item 9.2.4)
    campo_arbitrio_min: Optional[float] = 0  # valor -15%
    campo_arbitrio_max: Optional[float] = 0  # valor +15%
    # Prazo de validade do laudo
    prazo_validade_meses: Optional[int] = 6  # default 6 meses
    # Tipo de profissional responsável
    tipo_profissional: Optional[str] = "corretor"  # corretor | engenheiro | arquiteto | perito_judicial
    # Número de registro profissional (CRECI/CREA/CAU)
    registro_profissional: Optional[str] = ""
    # Número da ART ou RRT (opcional)
    art_rrt_numero: Optional[str] = ""

    # ── Campos Rurais (aparecem apenas quando property_type == 'rural') ─────────
    certificacao_sigef: Optional[str] = None   # Sistema de Gestão Fundiária (SIGEF/INCRA)
    cadastro_incra: Optional[str] = None        # Número de cadastro no INCRA
    ccir: Optional[str] = None                  # Certificado de Cadastro de Imóvel Rural
    nirf_cib: Optional[str] = None              # NIRF / CIB — Receita Federal / Sefaz
    car: Optional[str] = None                   # Cadastro Ambiental Rural (ex: MA-1234567-XXXXX)
    perimetro_m: Optional[float] = None         # Perímetro do imóvel em metros

    # ── Documentos rurais (uploads) ───────────────────────────────────────────
    doc_mapa_sigef: Optional[List[str]] = []         # Mapa Georreferenciado / Certificado SIGEF
    doc_memorial_descritivo: Optional[List[str]] = [] # Memorial Descritivo Topográfico / SIGEF
    doc_ccir: Optional[List[str]] = []               # CCIR — Certificado de Cadastro de Imóvel Rural
    doc_itr: Optional[List[str]] = []                # ITR — últimos 5 exercícios (até 5 arquivos)
    doc_car: Optional[List[str]] = []                # CAR — Cadastro Ambiental Rural

    # ── Legacy — Impact areas (desapropriação/servidão) ───────────────────────
    impact_areas: List[PtamImpactArea] = Field(default_factory=list)

    # ── Meta ──────────────────────────────────────────────────────────────────
    status: str = "Rascunho"  # Rascunho | Em revisão | Emitido


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
    status: str = "pending"  # pending, approved, rejected
    mp_payment_id: str = ""
    created_at: datetime = Field(default_factory=_now)


class CreatePreferenceRequest(BaseModel):
    plan_id: str  # mensal | trimestral | anual


# ---------- Garantias (NBR 14.653 partes 3 e 5) ----------

class GarantiaSolicitante(BaseModel):
    nome: Optional[str] = ""
    cpf_cnpj: Optional[str] = ""
    instituicao_financeira: Optional[str] = ""
    telefone: Optional[str] = ""
    email: Optional[str] = ""


class GarantiaResponsavel(BaseModel):
    nome: Optional[str] = ""
    creci: Optional[str] = ""
    cnai: Optional[str] = ""
    registro: Optional[str] = ""


class GarantiaBase(BaseModel):
    # ── Identificação ─────────────────────────────────────────────────────────
    numero: Optional[str] = ""
    tipo_garantia: Optional[str] = "imovel_rural"  # imovel_rural | graos_safra | bovinos | equipamentos | veiculos | outros
    finalidade: Optional[str] = "credito_rural"    # financiamento | credito_rural | penhor | alienacao_fiduciaria | outros

    # ── Campos Bancários / CMN 4.676/2018 ─────────────────────────────────────
    modalidade_financeira: Optional[str] = ""       # sfh_fgts | sfi_bancario | alienacao_fiduciaria | hipoteca | credito_rural
    instituicao_financeira: Optional[str] = ""      # nome do banco credor
    valor_financiamento: Optional[float] = 0
    ltv_maximo: Optional[float] = 80               # default 80% para SFH
    prazo_financiamento_meses: Optional[int] = 0
    mutuario_nome: Optional[str] = ""
    mutuario_cpf_cnpj: Optional[str] = ""
    finalidade_credito: Optional[str] = ""          # aquisicao | reforma | construcao | refinanciamento
    area_privativa_nbr12721: Optional[float] = 0
    padrao_construtivo_ibape: Optional[str] = ""    # baixo | normal | alto | luxo
    idade_real_anos: Optional[int] = 0
    idade_aparente_anos: Optional[int] = 0
    habite_se: Optional[bool] = False
    onus_reais: Optional[bool] = False
    onus_descricao: Optional[str] = ""
    inscricao_iptu: Optional[str] = ""
    valor_venal: Optional[float] = 0
    valor_liquidacao_forcada: Optional[float] = 0   # VLF para alienacao fiduciaria
    fator_desconto_vlf: Optional[float] = 0         # percentual desconto sobre valor mercado
    valor_1o_leilao: Optional[float] = 0            # Lei 9.514/97 art. 27
    valor_2o_leilao: Optional[float] = 0            # Lei 9.514/97 art. 27 par. 2
    art_numero: Optional[str] = ""
    art_data_registro: Optional[str] = ""
    grau_precisao: Optional[str] = "II"             # II ou III (NBR 14653-1)
    validade_laudo_meses: Optional[int] = 12        # 12 para SFH/FGTS
    declaracao_conflito_interesse: Optional[bool] = False
    declaracao_impedimentos: Optional[str] = ""
    # Campos adicionais de documentacao e vistoria bancaria
    cri_numero: Optional[str] = ""                  # Cartorio de Registro de Imoveis
    conformidade_plano_diretor: Optional[bool] = False
    regularidade_construtiva: Optional[bool] = False
    data_matricula: Optional[str] = ""              # data certidao matricula (max 30 dias)
    vistoria_horario: Optional[str] = ""
    vistoria_responsavel_nome: Optional[str] = ""
    vistoria_condicoes_obs: Optional[str] = ""
    # Analise metodologica bancaria
    num_amostras: Optional[int] = 0
    coeficiente_variacao: Optional[float] = 0
    fator_homogeneizacao: Optional[str] = ""        # area | padrao | localizacao | conservacao | fator_oferta
    infraestrutura_entorno: Optional[str] = ""
    liquidez_mercado: Optional[str] = ""
    # Resultado bancario
    valor_mercado: Optional[float] = 0
    valor_maximo_garantia: Optional[float] = 0
    campo_arbitrio_min: Optional[float] = 0
    campo_arbitrio_max: Optional[float] = 0
    # Responsavel tecnico bancario
    responsavel_tipo: Optional[str] = ""            # engenheiro | arquiteto
    responsavel_crea_cau: Optional[str] = ""
    responsavel_uf: Optional[str] = ""
    responsavel_empresa_cpf: Optional[str] = ""

    # ── Solicitante ───────────────────────────────────────────────────────────
    solicitante: GarantiaSolicitante = Field(default_factory=GarantiaSolicitante)

    # ── Descrição do Bem ──────────────────────────────────────────────────────
    descricao_bem: Optional[str] = ""

    # ── Localização / Vistoria ────────────────────────────────────────────────
    endereco: Optional[str] = ""
    municipio: Optional[str] = ""
    uf: Optional[str] = ""
    cep: Optional[str] = ""
    gps_lat: Optional[str] = ""
    gps_lng: Optional[str] = ""
    matricula: Optional[str] = ""
    cartorio: Optional[str] = ""
    data_vistoria: Optional[str] = ""

    # ── Campos rurais ─────────────────────────────────────────────────────────
    area_total_ha: Optional[float] = 0          # para imovel_rural
    area_construida_m2: Optional[float] = 0
    uso_atual: Optional[str] = ""               # pastagem | lavoura | floresta | misto
    benfeitorias: Optional[str] = ""
    topografia: Optional[str] = ""
    solo_vegetacao: Optional[str] = ""
    # Documentação rural específica
    certificacao_sigef: Optional[str] = None    # SIGEF — Sistema de Gestão Fundiária
    cadastro_incra: Optional[str] = None         # Número de cadastro no INCRA
    ccir: Optional[str] = None                   # Certificado de Cadastro de Imóvel Rural
    nirf_cib: Optional[str] = None               # NIRF / CIB — Receita Federal
    car: Optional[str] = None                    # Cadastro Ambiental Rural
    perimetro_m: Optional[float] = None          # Perímetro do imóvel em metros
    # Documentos rurais (uploads)
    doc_mapa_sigef: Optional[List[str]] = []         # Mapa Georreferenciado / Certificado SIGEF
    doc_memorial_descritivo: Optional[List[str]] = [] # Memorial Descritivo Topográfico / SIGEF
    doc_ccir: Optional[List[str]] = []               # CCIR — Certificado de Cadastro de Imóvel Rural
    doc_itr: Optional[List[str]] = []                # ITR — últimos 5 exercícios (até 5 arquivos)
    doc_car: Optional[List[str]] = []                # CAR — Cadastro Ambiental Rural

    # ── Campos graos/safra ────────────────────────────────────────────────────
    cultura: Optional[str] = ""                 # soja | milho | cafe | etc.
    quantidade_toneladas: Optional[float] = 0
    sacas: Optional[float] = 0
    produtividade_sc_ha: Optional[float] = 0
    local_armazenagem: Optional[str] = ""
    safra_referencia: Optional[str] = ""

    # ── Campos bovinos ────────────────────────────────────────────────────────
    raca_tipo: Optional[str] = ""
    quantidade_cabecas: Optional[int] = 0
    categoria: Optional[str] = ""              # boi_gordo | vaca | novilha | bezerro
    peso_medio_kg: Optional[float] = 0
    aptidao: Optional[str] = ""               # corte | leite | misto
    local_rebanho: Optional[str] = ""

    # ── Campos equipamentos/veículos ─────────────────────────────────────────
    marca: Optional[str] = ""
    modelo: Optional[str] = ""
    ano_fabricacao: Optional[int] = 0
    numero_serie: Optional[str] = ""
    potencia: Optional[str] = ""
    horimetro_hodometro: Optional[str] = ""

    # ── Avaliação ─────────────────────────────────────────────────────────────
    estado_conservacao: Optional[str] = "bom"  # otimo | bom | regular | precario
    valor_unitario: Optional[float] = 0
    valor_total: Optional[float] = 0
    data_avaliacao: Optional[str] = ""
    data_validade: Optional[str] = ""
    metodologia: Optional[str] = ""
    fundamentacao_legal: Optional[str] = "NBR 14.653"
    mercado_referencia: Optional[str] = ""
    fatores_depreciacao: Optional[str] = ""
    grau_fundamentacao: Optional[str] = ""    # I | II | III

    # ── Resultado ─────────────────────────────────────────────────────────────
    resultado_intervalo_inf: Optional[float] = 0
    resultado_intervalo_sup: Optional[float] = 0
    resultado_em_extenso: Optional[str] = ""

    # ── Conclusão ─────────────────────────────────────────────────────────────
    consideracoes: Optional[str] = ""
    ressalvas: Optional[str] = ""

    # ── Responsável Técnico ───────────────────────────────────────────────────
    responsavel: GarantiaResponsavel = Field(default_factory=GarantiaResponsavel)

    # ── Fotos / Documentos ────────────────────────────────────────────────────
    fotos: List[str] = Field(default_factory=list)
    observacoes: Optional[str] = ""

    # ── Meta ──────────────────────────────────────────────────────────────────
    status: str = "rascunho"  # rascunho | em_andamento | concluido


class Garantia(GarantiaBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# ---------- Semoventes (Penhor Rural Bancário) ----------
class CategoriaSemovente(BaseModel):
    categoria: str = ""  # reprodutores, matrizes, novilhas, garrotes_bezerros, bois_engorda
    quantidade: int = 0
    raca: str = ""
    faixa_etaria: str = ""
    peso_medio_kg: float = 0
    registro_genealogico: str = ""
    valor_unitario: float = 0
    valor_total: float = 0
    # matrizes
    taxa_prenhez: Optional[float] = None
    producao_leite: Optional[float] = None
    # engorda
    arrobas_estimadas: Optional[float] = None
    estagio: Optional[str] = None  # confinamento, semiconfinamento, pastagem
    # equinos
    aptidao: Optional[str] = None  # corrida, trabalho, esporte, lazer
    # aves/suinos
    fase: Optional[str] = None


class SemoventeBase(BaseModel):
    # Identificacao
    numero_laudo: Optional[str] = ""
    tipo_semovente: str = "bovino"  # bovino, equino, suino, ovino_caprino, aves
    status: str = "rascunho"  # rascunho, em_andamento, concluido

    # Operacao bancaria
    instituicao_financeira: Optional[str] = ""
    modalidade_credito: Optional[str] = "credito_rural_livre"
    valor_credito: Optional[float] = 0
    devedor_nome: Optional[str] = ""
    devedor_cpf_cnpj: Optional[str] = ""

    # Propriedade
    propriedade_nome: Optional[str] = ""
    propriedade_municipio: Optional[str] = ""
    propriedade_uf: Optional[str] = ""
    matricula_imovel: Optional[str] = ""
    cri_cartorio: Optional[str] = ""

    # Rebanho
    categorias: List[CategoriaSemovente] = Field(default_factory=list)
    total_cabecas: Optional[int] = 0
    total_ua: Optional[float] = 0  # 1 UA = 450 kg
    lotacao_ua_ha: Optional[float] = 0

    # Rastreabilidade
    brincos_sisbov: Optional[bool] = False
    brinco_inicio: Optional[str] = ""
    brinco_fim: Optional[str] = ""
    marcacao_ferro: Optional[bool] = False
    marcacao_descricao: Optional[str] = ""
    microchip: Optional[bool] = False
    situacao_esisbov: Optional[str] = ""

    # Situacao sanitaria
    vacina_aftosa_data: Optional[str] = ""
    vacina_aftosa_orgao: Optional[str] = ""
    vacina_brucelose_data: Optional[str] = ""
    teste_tuberculose: Optional[str] = "nao_realizado"
    teste_tuberculose_data: Optional[str] = ""
    vermifugacao_data: Optional[str] = ""
    vermifugacao_produto: Optional[str] = ""
    mortalidade_percentual: Optional[float] = 0
    area_livre_aftosa: Optional[bool] = False
    gta_em_dia: Optional[bool] = False

    # Infraestrutura
    capacidade_suporte_ua_ha: Optional[float] = 0
    disponibilidade_agua: Optional[str] = ""
    instalacoes: Optional[str] = ""
    estado_conservacao_instalacoes: Optional[str] = ""
    capacidade_confinamento: Optional[int] = 0

    # Avaliacao / cotacoes
    cotacao_arroba_data: Optional[str] = ""
    cotacao_arroba_valor: Optional[float] = 0
    cotacao_fonte: Optional[str] = ""
    cotacao_bezerro: Optional[float] = 0
    cotacao_vaca: Optional[float] = 0
    cotacao_touro_po: Optional[float] = 0
    valor_mercado_total: Optional[float] = 0
    fator_liquidez: Optional[float] = 0.65
    valor_garantia_aceito: Optional[float] = 0
    ltv_recomendado: Optional[float] = 65
    validade_laudo_meses: Optional[int] = 6
    seguro_recomendado_valor: Optional[float] = 0

    # Vistoria
    vistoria_data: Optional[str] = ""
    vistoria_horario: Optional[str] = ""
    contagem_fisica_presencial: Optional[bool] = False
    condicao_corporal_media: Optional[float] = 3.0  # escala 1-5
    fotos: List[str] = Field(default_factory=list)

    # Responsavel (CRMV obrigatorio para penhor rural)
    responsavel_nome: Optional[str] = ""
    crmv_numero: Optional[str] = ""
    crmv_uf: Optional[str] = ""
    especialidade: Optional[str] = ""
    art_crmv_numero: Optional[str] = ""
    art_data_registro: Optional[str] = ""

    # Declaracoes
    declaracao_contagem_presencial: Optional[bool] = False
    declaracao_sem_conflito: Optional[bool] = False
    declaracao_penhor_registrado: Optional[bool] = False
    restricoes_ressalvas: Optional[str] = ""


class Semovente(SemoventeBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# ---------- Perfil Avaliador ----------
class RegistroProfissional(BaseModel):
    tipo: str  # CRECI, CREA, CAU, CRMV, CZO, CNAI, CFT, INCRA
    numero: str
    uf: str = ""
    validade: Optional[str] = None
    status: str = "ativo"  # ativo, inativo, suspenso


class Formacao(BaseModel):
    tipo: str  # graduacao, pos_graduacao, mestrado, doutorado, tecnico, curso_livre
    curso: str
    instituicao: str
    ano_conclusao: int
    carga_horaria: Optional[int] = None


class Experiencia(BaseModel):
    cargo: str
    empresa: str
    periodo_inicio: str
    periodo_fim: Optional[str] = None  # null = atual
    descricao: str = ""


class PerfilAvaliadorBase(BaseModel):
    # Dados pessoais
    nome_completo: str = ""
    foto_perfil: Optional[str] = None
    cpf: str = ""
    rg: str = ""
    rg_orgao: str = ""
    bio_resumo: str = ""

    # Registros profissionais
    registros: List[RegistroProfissional] = []

    # Formacao academica
    formacoes: List[Formacao] = []

    # Experiencia profissional
    experiencias: List[Experiencia] = []

    # Especializacoes e habilitacoes
    especializacoes: List[str] = []
    habilitacoes: List[str] = []
    tribunais_cadastrado: List[str] = []
    bancos_habilitado: List[str] = []

    # Contato profissional
    telefone: str = ""
    email_profissional: str = ""
    site: str = ""
    endereco_escritorio: str = ""
    cidade: str = ""
    uf: str = ""
    cep: str = ""

    # Empresa
    empresa_nome: str = ""
    empresa_cnpj: str = ""
    empresa_razao_social: str = ""

    # Areas e associacoes
    areas_atuacao: List[str] = []
    membro_associacoes: List[str] = []
    numero_laudos_emitidos: int = 0


class PerfilAvaliador(PerfilAvaliadorBase):
    id: str = Field(default_factory=_id)
    user_id: str = ""
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# ---------- Admin ----------
class CreateTestUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    plan: str = "mensal"  # mensal | trimestral | anual
    plan_status: str = "active"  # active | inactive


class AdminUserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    plan: str
    plan_status: str
    plan_expires: Optional[datetime] = None
    created_at: Optional[datetime] = None
