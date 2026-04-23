# @module models.garantias — Modelos Pydantic para Garantias (NBR 14.653 partes 3 e 5)
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.common import _id, _now


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
    # Identificação
    numero: Optional[str] = ""
    tipo_garantia: Optional[str] = "imovel_rural"
    finalidade: Optional[str] = "credito_rural"

    # Campos Bancários / CMN 4.676/2018
    modalidade_financeira: Optional[str] = ""
    instituicao_financeira: Optional[str] = ""
    valor_financiamento: Optional[float] = 0
    ltv_maximo: Optional[float] = 80
    prazo_financiamento_meses: Optional[int] = 0
    mutuario_nome: Optional[str] = ""
    mutuario_cpf_cnpj: Optional[str] = ""
    finalidade_credito: Optional[str] = ""
    area_privativa_nbr12721: Optional[float] = 0
    padrao_construtivo_ibape: Optional[str] = ""
    idade_real_anos: Optional[int] = 0
    idade_aparente_anos: Optional[int] = 0
    habite_se: Optional[bool] = False
    onus_reais: Optional[bool] = False
    onus_descricao: Optional[str] = ""
    inscricao_iptu: Optional[str] = ""
    valor_venal: Optional[float] = 0
    valor_liquidacao_forcada: Optional[float] = 0
    fator_desconto_vlf: Optional[float] = 0
    valor_1o_leilao: Optional[float] = 0
    valor_2o_leilao: Optional[float] = 0
    art_numero: Optional[str] = ""
    art_data_registro: Optional[str] = ""
    grau_precisao: Optional[str] = "II"
    validade_laudo_meses: Optional[int] = 12
    declaracao_conflito_interesse: Optional[bool] = False
    declaracao_impedimentos: Optional[str] = ""
    cri_numero: Optional[str] = ""
    conformidade_plano_diretor: Optional[bool] = False
    regularidade_construtiva: Optional[bool] = False
    data_matricula: Optional[str] = ""
    vistoria_horario: Optional[str] = ""
    vistoria_responsavel_nome: Optional[str] = ""
    vistoria_condicoes_obs: Optional[str] = ""
    num_amostras: Optional[int] = 0
    coeficiente_variacao: Optional[float] = 0
    fator_homogeneizacao: Optional[str] = ""
    infraestrutura_entorno: Optional[str] = ""
    liquidez_mercado: Optional[str] = ""
    valor_mercado: Optional[float] = 0
    valor_maximo_garantia: Optional[float] = 0
    campo_arbitrio_min: Optional[float] = 0
    campo_arbitrio_max: Optional[float] = 0
    responsavel_tipo: Optional[str] = ""
    responsavel_crea_cau: Optional[str] = ""
    responsavel_uf: Optional[str] = ""
    responsavel_empresa_cpf: Optional[str] = ""

    # Solicitante
    solicitante: GarantiaSolicitante = Field(default_factory=GarantiaSolicitante)

    # Descrição do Bem
    descricao_bem: Optional[str] = ""

    # Localização / Vistoria
    endereco: Optional[str] = ""
    municipio: Optional[str] = ""
    uf: Optional[str] = ""
    cep: Optional[str] = ""
    gps_lat: Optional[str] = ""
    gps_lng: Optional[str] = ""
    matricula: Optional[str] = ""
    cartorio: Optional[str] = ""
    data_vistoria: Optional[str] = ""

    # Campos rurais
    area_total_ha: Optional[float] = 0
    area_construida_m2: Optional[float] = 0
    uso_atual: Optional[str] = ""
    benfeitorias: Optional[str] = ""
    topografia: Optional[str] = ""
    solo_vegetacao: Optional[str] = ""
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

    # Campos graos/safra
    cultura: Optional[str] = ""
    quantidade_toneladas: Optional[float] = 0
    sacas: Optional[float] = 0
    produtividade_sc_ha: Optional[float] = 0
    local_armazenagem: Optional[str] = ""
    safra_referencia: Optional[str] = ""

    # Campos bovinos
    raca_tipo: Optional[str] = ""
    quantidade_cabecas: Optional[int] = 0
    categoria: Optional[str] = ""
    peso_medio_kg: Optional[float] = 0
    aptidao: Optional[str] = ""
    local_rebanho: Optional[str] = ""

    # Campos equipamentos/veículos
    marca: Optional[str] = ""
    modelo: Optional[str] = ""
    ano_fabricacao: Optional[int] = 0
    numero_serie: Optional[str] = ""
    potencia: Optional[str] = ""
    horimetro_hodometro: Optional[str] = ""

    # Avaliação
    estado_conservacao: Optional[str] = "bom"
    valor_unitario: Optional[float] = 0
    valor_total: Optional[float] = 0
    data_avaliacao: Optional[str] = ""
    data_validade: Optional[str] = ""
    metodologia: Optional[str] = ""
    fundamentacao_legal: Optional[str] = "NBR 14.653"
    mercado_referencia: Optional[str] = ""
    fatores_depreciacao: Optional[str] = ""
    grau_fundamentacao: Optional[str] = ""

    # Resultado
    resultado_intervalo_inf: Optional[float] = 0
    resultado_intervalo_sup: Optional[float] = 0
    resultado_em_extenso: Optional[str] = ""

    # Conclusão
    consideracoes: Optional[str] = ""
    ressalvas: Optional[str] = ""

    # Responsável Técnico
    responsavel: GarantiaResponsavel = Field(default_factory=GarantiaResponsavel)

    # Fotos / Documentos
    fotos: List[str] = Field(default_factory=list)
    observacoes: Optional[str] = ""

    # D4Sign — Assinatura Digital com Validade Juridica (Lei 14.063/2020 + MP 2.200-2/2001)
    d4sign_document_uuid: Optional[str] = None
    d4sign_status: Optional[str] = None   # pendente|aguardando|assinado|cancelado
    d4sign_enviado_em: Optional[datetime] = None
    d4sign_assinado_em: Optional[datetime] = None
    d4sign_signatarios: Optional[List[dict]] = []
    d4sign_pdf_assinado_url: Optional[str] = None

    # Meta
    status: str = "rascunho"


class Garantia(GarantiaBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
