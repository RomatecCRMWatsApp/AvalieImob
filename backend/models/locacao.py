# @module models.locacao — Modelos Pydantic para Avaliação de Locação
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.common import _id, _now


class LocacaoAmostra(BaseModel):
    address: Optional[str] = ""
    neighborhood: Optional[str] = ""
    area: Optional[float] = 0
    valor_aluguel: Optional[float] = 0
    valor_por_m2: Optional[float] = 0
    source: Optional[str] = ""
    collection_date: Optional[str] = ""
    contact_phone: Optional[str] = ""
    notes: Optional[str] = ""
    foto: Optional[str] = None
    tipo_amostra: Optional[str] = "oferta"


class LocacaoBase(BaseModel):
    # Seção 1 — Identificação
    numero_locacao: Optional[str] = None
    solicitante_nome: Optional[str] = ""
    solicitante_cpf: Optional[str] = ""
    solicitante_telefone: Optional[str] = ""
    solicitante_email: Optional[str] = ""
    solicitante_endereco: Optional[str] = ""

    # Seção 2 — Objetivo
    objetivo: Optional[str] = ""
    objetivo_outros: Optional[str] = ""
    tipo_locacao: Optional[str] = "residencial"
    base_legal_locacao: Optional[str] = "Lei 8.245/1991 (Lei do Inquilinato) — Art. 565 a 578 do Código Civil"

    # Seção 3 — Identificação do Imóvel
    imovel_endereco: Optional[str] = ""
    imovel_bairro: Optional[str] = ""
    imovel_cidade: Optional[str] = ""
    imovel_estado: Optional[str] = ""
    imovel_cep: Optional[str] = ""
    imovel_matricula: Optional[str] = ""
    imovel_cartorio: Optional[str] = ""
    imovel_tipo: Optional[str] = ""
    imovel_area_terreno: Optional[float] = 0
    imovel_area_construida: Optional[float] = 0
    imovel_idade: Optional[int] = 0
    imovel_estado_conservacao: Optional[str] = ""
    imovel_padrao_acabamento: Optional[str] = ""
    imovel_num_quartos: Optional[int] = 0
    imovel_num_banheiros: Optional[int] = 0
    imovel_num_vagas: Optional[int] = 0
    imovel_piscina: Optional[bool] = False
    imovel_caracteristicas: Optional[str] = ""

    # Seção 4 — Caracterização da Região
    regiao_infraestrutura: Optional[str] = ""
    regiao_servicos_publicos: Optional[str] = ""
    regiao_uso_predominante: Optional[str] = ""
    regiao_padrao_construtivo: Optional[str] = ""
    regiao_tendencia_mercado: Optional[str] = ""
    regiao_observacoes: Optional[str] = ""
    zoneamento: Optional[str] = ""

    # Seção 5 — Pesquisa de Mercado
    market_samples: List[LocacaoAmostra] = Field(default_factory=list)
    market_analysis: Optional[str] = ""

    # Seção 6 — Cálculos
    methodology: Optional[str] = "Método Comparativo Direto de Dados de Mercado"
    methodology_justification: Optional[str] = ""
    calc_media: Optional[float] = 0
    calc_mediana: Optional[float] = 0
    calc_desvio_padrao: Optional[float] = 0
    calc_coef_variacao: Optional[float] = 0
    calc_grau_fundamentacao: Optional[str] = ""
    calc_fatores_homogeneizacao: Optional[str] = ""
    calc_observacoes: Optional[str] = ""

    # Seção 7 — Garantia
    prazo_locacao: Optional[str] = ""
    garantia_locacao: Optional[str] = ""
    fator_locacao: Optional[float] = None
    grau_precisao: Optional[str] = "I"
    campo_arbitrio_min: Optional[float] = 0
    campo_arbitrio_max: Optional[float] = 0

    # Seção 8 — Responsável Técnico
    responsavel_nome: Optional[str] = ""
    responsavel_creci: Optional[str] = ""
    responsavel_cnai: Optional[str] = ""
    registro_profissional: Optional[str] = ""
    tipo_profissional: Optional[str] = "corretor"
    art_rrt_numero: Optional[str] = ""
    prazo_validade_meses: Optional[int] = 6
    conclusion_city: Optional[str] = ""
    conclusion_date: Optional[str] = ""

    # Seção 9 — Fotos
    fotos_imovel: List[str] = Field(default_factory=list)
    fotos_documentos: List[str] = Field(default_factory=list)
    documentos_analisados: List[str] = Field(default_factory=list)

    # Seção 10 — Resultado
    valor_locacao_estimado: Optional[float] = None
    valor_locacao_minimo: Optional[float] = None
    valor_locacao_maximo: Optional[float] = None
    valor_locacao_por_extenso: Optional[str] = ""
    resultado_data_referencia: Optional[str] = ""
    resultado_prazo_validade: Optional[str] = ""
    consideracoes_ressalvas: Optional[str] = ""
    consideracoes_pressupostos: Optional[str] = ""
    consideracoes_limitacoes: Optional[str] = ""
    conclusion_text: Optional[str] = ""

    # Meta
    status: str = "Rascunho"


class Locacao(LocacaoBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
