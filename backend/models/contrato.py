# @module models.contrato — Modelos Pydantic para o modulo de Contratos Imobiliarios
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from models.common import _id, _now


# ============================================================
# TIPOS DE CONTRATO (15 tipos suportados)
# ============================================================
TIPOS_CONTRATO = [
    "Compra e Venda de Imóvel Urbano",
    "Compra e Venda de Imóvel Rural",
    "Compra e Venda de Veículo",
    "Promessa de Compra e Venda",
    "Locação Residencial",
    "Locação Comercial",
    "Locação por Temporada",
    "Comodato de Imóvel",
    "Permuta de Imóveis",
    "Permuta de Veículos",
    "Cessão de Direitos",
    "Contrato de Corretagem",
    "Contrato de Administração de Imóvel",
    "Distrato de Compra e Venda",
    "Instrumento Particular de Hipoteca",
]


# ============================================================
# PARTES DO CONTRATO
# ============================================================

class PessoaFisica(BaseModel):
    nome: str = ""
    cpf: Optional[str] = ""
    rg: Optional[str] = ""
    rg_orgao: Optional[str] = ""
    rg_uf: Optional[str] = ""
    data_nascimento: Optional[str] = ""
    nacionalidade: Optional[str] = "brasileiro(a)"
    estado_civil: Optional[str] = ""
    profissao: Optional[str] = ""
    email: Optional[str] = ""
    telefone: Optional[str] = ""
    endereco: Optional[str] = ""
    cidade: Optional[str] = ""
    uf: Optional[str] = ""
    cep: Optional[str] = ""
    # Conjuge
    conjuge_nome: Optional[str] = ""
    conjuge_cpf: Optional[str] = ""
    conjuge_rg: Optional[str] = ""
    conjuge_profissao: Optional[str] = ""
    regime_bens: Optional[str] = ""
    # Procurador
    procurador_nome: Optional[str] = ""
    procurador_cpf: Optional[str] = ""
    procurador_instrumento: Optional[str] = ""


class PessoaJuridica(BaseModel):
    razao_social: str = ""
    cnpj: Optional[str] = ""
    inscricao_estadual: Optional[str] = ""
    endereco: Optional[str] = ""
    cidade: Optional[str] = ""
    uf: Optional[str] = ""
    cep: Optional[str] = ""
    email: Optional[str] = ""
    telefone: Optional[str] = ""
    representante_nome: Optional[str] = ""
    representante_cpf: Optional[str] = ""
    representante_cargo: Optional[str] = ""


class Parte(BaseModel):
    tipo: str = "pf"  # "pf" | "pj"
    qualificacao: str = ""  # ex: "Vendedor", "Comprador", "Locador", "Locatario"
    pf: Optional[PessoaFisica] = None
    pj: Optional[PessoaJuridica] = None


# ============================================================
# CORRETOR / IMOBILIARIA
# ============================================================

class Corretor(BaseModel):
    nome: str = ""
    creci: Optional[str] = ""
    cpf_cnpj: Optional[str] = ""
    email: Optional[str] = ""
    telefone: Optional[str] = ""
    imobiliaria: Optional[str] = ""
    imobiliaria_cnpj: Optional[str] = ""
    # Comissao
    comissao_percentual: Optional[float] = None
    comissao_valor: Optional[float] = None
    comissao_responsavel: Optional[str] = ""  # quem paga
    comissao_forma_pagamento: Optional[str] = ""
    # Exclusividade
    exclusividade: Optional[bool] = False
    exclusividade_prazo_dias: Optional[int] = None
    # Clausulas de protecao
    clausulas_protecao: Optional[List[str]] = []


# ============================================================
# OBJETO DO CONTRATO
# ============================================================

class ObjetoContrato(BaseModel):
    tipo: str = "imovel_urbano"  # imovel_urbano | imovel_rural | veiculo
    # Imovel Urbano/Rural
    endereco: Optional[str] = ""
    complemento: Optional[str] = ""
    bairro: Optional[str] = ""
    cidade: Optional[str] = ""
    uf: Optional[str] = ""
    cep: Optional[str] = ""
    matricula: Optional[str] = ""
    cartorio: Optional[str] = ""
    area_terreno: Optional[float] = None
    area_construida: Optional[float] = None
    area_total_ha: Optional[float] = None
    denominacao: Optional[str] = ""
    inscricao_iptu: Optional[str] = ""
    ccir: Optional[str] = ""
    nirf: Optional[str] = ""
    car: Optional[str] = ""
    # Situacao e onus
    situacao: Optional[str] = ""  # ex: "livre e desembaraçado"
    onus: Optional[str] = ""  # hipotecas, penhoras etc.
    ocupacao: Optional[str] = ""  # desocupado, ocupado pelo vendedor etc.
    # Veiculo
    veiculo_marca: Optional[str] = ""
    veiculo_modelo: Optional[str] = ""
    veiculo_ano_fabricacao: Optional[int] = None
    veiculo_ano_modelo: Optional[int] = None
    veiculo_cor: Optional[str] = ""
    veiculo_placa: Optional[str] = ""
    veiculo_renavam: Optional[str] = ""
    veiculo_chassi: Optional[str] = ""
    veiculo_km: Optional[int] = None
    descricao_adicional: Optional[str] = ""


# ============================================================
# CONDICOES DE PAGAMENTO
# ============================================================

class ParcelaPagamento(BaseModel):
    numero: int = 1
    valor: float = 0
    vencimento: Optional[str] = ""
    forma_pagamento: Optional[str] = ""  # dinheiro, pix, transferencia, cheque, financiamento
    banco: Optional[str] = ""
    descricao: Optional[str] = ""
    pago: Optional[bool] = False
    data_pagamento: Optional[str] = ""


class CondicoesPagamento(BaseModel):
    valor_total: float = 0
    valor_total_extenso: Optional[str] = ""
    moeda: Optional[str] = "BRL"
    forma_principal: Optional[str] = ""  # a-vista | parcelado | financiamento | permuta
    # Sinal/arras
    sinal_valor: Optional[float] = None
    sinal_data: Optional[str] = ""
    sinal_arras_tipo: Optional[str] = ""  # confirmatórias | penitenciais
    # Parcelas
    parcelas: List[ParcelaPagamento] = Field(default_factory=list)
    # Financiamento
    financiamento_banco: Optional[str] = ""
    financiamento_valor: Optional[float] = None
    financiamento_prazo_meses: Optional[int] = None
    # Clausulas de inadimplemento
    multa_inadimplemento: Optional[float] = None  # percentual
    juros_mora: Optional[float] = None  # percentual ao mes
    correcao_monetaria: Optional[str] = ""
    observacoes: Optional[str] = ""


# ============================================================
# TESTEMUNHAS
# ============================================================

class Testemunha(BaseModel):
    nome: str = ""
    cpf: Optional[str] = ""
    rg: Optional[str] = ""
    email: Optional[str] = ""
    telefone: Optional[str] = ""
    endereco: Optional[str] = ""


# ============================================================
# CLAUSULAS
# ============================================================

class Clausula(BaseModel):
    numero: int = 1
    titulo: str = ""
    conteudo: str = ""
    tipo: str = "padrao"  # padrao | especial | obrigatoria | negociada
    base_legal: Optional[str] = ""


# ============================================================
# ALERTAS JURIDICOS
# ============================================================

class AlertaJuridico(BaseModel):
    nivel: str = "info"  # info | aviso | critico
    campo: Optional[str] = ""
    mensagem: str = ""
    sugestao: Optional[str] = ""
    resolvido: Optional[bool] = False


# ============================================================
# VERSAO DO CONTRATO
# ============================================================

class ContratoVersionDiff(BaseModel):
    campo: str
    valor_anterior: Optional[Any] = None
    valor_novo: Optional[Any] = None


class ContratoVersion(BaseModel):
    id: str = Field(default_factory=_id)
    contrato_id: str
    user_id: str
    numero_versao: int
    hash_sha256: str
    diffs: List[ContratoVersionDiff] = Field(default_factory=list)
    snapshot: Optional[dict] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    observacao: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


# ============================================================
# CONTRATO BASE E CONTRATO COMPLETO
# ============================================================

class ContratoBase(BaseModel):
    # Identificacao
    tipo_contrato: str = ""  # um dos TIPOS_CONTRATO
    numero_contrato: Optional[str] = None
    titulo: Optional[str] = ""
    # Partes
    partes: List[Parte] = Field(default_factory=list)
    # Corretor
    corretor: Optional[Corretor] = None
    # Objeto
    objeto: Optional[ObjetoContrato] = None
    # Condicoes financeiras
    condicoes_pagamento: Optional[CondicoesPagamento] = None
    # Clausulas
    clausulas: List[Clausula] = Field(default_factory=list)
    # Testemunhas
    testemunhas: List[Testemunha] = Field(default_factory=list)
    # Dados do contrato
    data_assinatura: Optional[str] = ""
    cidade_assinatura: Optional[str] = ""
    uf_assinatura: Optional[str] = ""
    prazo_vigencia_dias: Optional[int] = None
    data_vigencia_inicio: Optional[str] = ""
    data_vigencia_fim: Optional[str] = ""
    # Alertas juridicos
    alertas_juridicos: List[AlertaJuridico] = Field(default_factory=list)
    # Status e controle
    status: str = "rascunho"  # rascunho | em_revisao | assinado | arquivado | cancelado
    observacoes: Optional[str] = ""
    # Versionamento
    lacrado: Optional[bool] = False
    versao_lacrada: Optional[str] = None
    hash_lacrado: Optional[str] = None
    # Link publico
    link_publico_token: Optional[str] = None
    link_publico_ativo: Optional[bool] = False
    link_publico_criado_em: Optional[datetime] = None
    # D4Sign — Assinatura Digital (Lei 14.063/2020 + MP 2.200-2/2001)
    d4sign_document_uuid: Optional[str] = None
    d4sign_status: Optional[str] = None  # pendente | aguardando | assinado | cancelado
    d4sign_enviado_em: Optional[datetime] = None
    d4sign_assinado_em: Optional[datetime] = None
    d4sign_signatarios: Optional[List[dict]] = Field(default_factory=list)
    d4sign_pdf_assinado_url: Optional[str] = None


class Contrato(ContratoBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
