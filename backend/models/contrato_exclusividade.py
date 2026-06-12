# @module models.contrato_exclusividade — Contrato de Exclusividade com aceite eletrônico via WhatsApp
"""
Fluxo leve de Exclusividade de Corretagem com ACEITE ELETRÔNICO via link/WhatsApp
(token por signatário), distinto do módulo genérico `contratos` (assinatura
ICP-Brasil/D4Sign). Collection própria: `contratos_exclusividade`.

Fundamentos: MP 2.200-2/2001 art. 10 §2º; Lei 14.063/2020; CC art. 726;
Lei 6.530/1978 + Resolução COFECI 458/1995.
"""
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class EstadoCivil(str, Enum):
    SOLTEIRO = "solteiro"
    CASADO = "casado"
    UNIAO_ESTAVEL = "uniao_estavel"
    DIVORCIADO = "divorciado"
    VIUVO = "viuvo"


class RegimeBens(str, Enum):
    COMUNHAO_PARCIAL = "comunhao_parcial"
    COMUNHAO_UNIVERSAL = "comunhao_universal"
    SEPARACAO_TOTAL = "separacao_total"
    PARTICIPACAO_FINAL = "participacao_final_aquestos"


class StatusContrato(str, Enum):
    RASCUNHO = "rascunho"
    ENVIADO = "enviado"
    PARCIALMENTE_ASSINADO = "parcialmente_assinado"
    ASSINADO = "assinado"
    EXPIRADO = "expirado"
    CANCELADO = "cancelado"


class StatusSignatario(str, Enum):
    PENDENTE = "pendente"
    ACEITO = "aceito"


# Estados civis + regime que EXIGEM cônjuge/companheiro(a) como 2º signatário.
# Casado/União estável exigem, SALVO separação total de bens.
def exige_conjuge(estado_civil, regime_bens) -> bool:
    ec = estado_civil.value if isinstance(estado_civil, EstadoCivil) else estado_civil
    rb = regime_bens.value if isinstance(regime_bens, RegimeBens) else regime_bens
    return ec in (EstadoCivil.CASADO.value, EstadoCivil.UNIAO_ESTAVEL.value) \
        and rb != RegimeBens.SEPARACAO_TOTAL.value


def _so_digitos(v: str) -> str:
    return "".join(filter(str.isdigit, v or ""))


def cpf_valido(cpf: str) -> bool:
    """Valida CPF por dígito verificador."""
    cpf = _so_digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(cpf[n]) * ((i + 1) - n) for n in range(i))
        dig = (soma * 10) % 11
        dig = 0 if dig == 10 else dig
        if dig != int(cpf[i]):
            return False
    return True


class PessoaInput(BaseModel):
    nome: str
    cpf: str
    rg: Optional[str] = None
    rg_orgao: Optional[str] = None
    cnh: Optional[str] = None
    nacionalidade: str = "brasileiro(a)"
    naturalidade_cidade: Optional[str] = None
    naturalidade_uf: Optional[str] = None
    profissao: Optional[str] = None
    whatsapp: str  # E.164 sem '+', ex.: 5599999999999
    email: Optional[str] = None
    endereco_completo: Optional[str] = None

    @field_validator("cpf")
    @classmethod
    def valida_cpf(cls, v: str) -> str:
        digitos = _so_digitos(v)
        if len(digitos) != 11:
            raise ValueError("CPF deve conter 11 dígitos")
        if not cpf_valido(digitos):
            raise ValueError("CPF inválido (dígito verificador)")
        return digitos

    @field_validator("whatsapp")
    @classmethod
    def valida_whatsapp(cls, v: str) -> str:
        digitos = _so_digitos(v)
        if len(digitos) < 12 or len(digitos) > 13:
            raise ValueError("WhatsApp deve estar no formato 55DDDNUMERO")
        return digitos


class ImovelInput(BaseModel):
    # Compatível com o fluxo atual (descrição/endereço/valor obrigatórios no create cheio)
    descricao: str
    endereco: str
    bairro: str
    cidade: str = "Açailândia"
    uf: str = "MA"
    matricula: Optional[str] = None
    cartorio: Optional[str] = "1º Ofício Extrajudicial de Açailândia/MA"
    area_total: Optional[str] = None
    valor_anunciado: float
    # ---- v2: detalhamento registral / cadastral / áreas / ônus (todos opcionais) ----
    tipo: Literal["urbano", "rural"] = "urbano"
    livro: Optional[str] = None
    folha: Optional[str] = None
    cartorio_cns: Optional[str] = "03.018-9"
    # cadastrais urbano (BCI)
    inscricao_cadastral: Optional[str] = None
    quadra: Optional[str] = None
    lote: Optional[str] = None
    loteamento_bairro: Optional[str] = None
    # cadastrais rural
    ccir: Optional[str] = None
    nirf: Optional[str] = None
    codigo_sigef: Optional[str] = None
    denominacao: Optional[str] = None
    # áreas
    area_terreno: Optional[float] = None
    area_unidade: Literal["m2", "ha"] = "m2"
    area_construida: Optional[float] = None
    construcao_averbada: Literal["sim", "nao", "nao_se_aplica"] = "nao_se_aplica"
    numero_averbacao: Optional[str] = None
    # ônus
    alienacao_fiduciaria: bool = False
    credor_fiduciario: Optional[str] = None
    saldo_devedor_aprox: Optional[float] = None
    outros_onus: Optional[str] = None
    iptu_itr_situacao: Optional[Literal["quitado", "parcelado", "em_debito", "isento"]] = None
    ptam_referencia_id: Optional[str] = None


class MultaRescisoria(BaseModel):
    """
    Penalidade por rescisão imotivada pelo proprietário antes do fim do prazo de
    exclusividade. Exatamente UM dos dois modos:
      - percentual sobre a comissão estimada (calculada sobre o valor anunciado), ou
      - valor fixo em reais.
    """
    modo: Literal["percentual_comissao", "valor_fixo"]
    percentual: Optional[float] = Field(default=None, ge=1, le=100)
    valor_fixo: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def valida_modo(self):
        if self.modo == "percentual_comissao" and self.percentual is None:
            raise ValueError("Informe o percentual da multa sobre a comissão estimada")
        if self.modo == "valor_fixo" and self.valor_fixo is None:
            raise ValueError("Informe o valor fixo da multa rescisória")
        return self


# ===========================================================================
# v2 (multiproprietários + ficha de imóvel no padrão PTAM)
# ===========================================================================


def cnpj_valido(cnpj: str) -> bool:
    c = _so_digitos(cnpj)
    if len(c) != 14 or c == c[0] * 14:
        return False
    def dv(base):
        pesos = list(range(len(base) + 1 - 8, 1, -1)) + list(range(9, 1, -1))
        pesos = pesos[-len(base):]
        s = sum(int(d) * p for d, p in zip(base, pesos))
        r = s % 11
        return "0" if r < 2 else str(11 - r)
    d1 = dv(c[:12])
    d2 = dv(c[:12] + d1)
    return c[12:] == d1 + d2


class ProprietarioInput(PessoaInput):
    """Um condômino do imóvel. CPF (11) ou CNPJ (14); fração e estado civil próprios."""
    cpf: Optional[str] = None  # neutraliza o cpf herdado de PessoaInput
    cpf_cnpj: str
    fracao_percentual: float = Field(gt=0, le=100)
    estado_civil: EstadoCivil = EstadoCivil.SOLTEIRO
    regime_bens: Optional[RegimeBens] = None
    conjuge: Optional[PessoaInput] = None

    @field_validator("cpf")
    @classmethod
    def _cpf_opcional(cls, v):
        # Condômino é identificado por cpf_cnpj; sobrescreve o validador estrito herdado.
        return v

    @field_validator("cpf_cnpj")
    @classmethod
    def valida_cpf_cnpj(cls, v: str) -> str:
        d = _so_digitos(v)
        if len(d) == 11:
            if not cpf_valido(d):
                raise ValueError("CPF inválido (dígito verificador)")
        elif len(d) == 14:
            if not cnpj_valido(d):
                raise ValueError("CNPJ inválido (dígito verificador)")
        else:
            raise ValueError("Informe CPF (11 dígitos) ou CNPJ (14 dígitos)")
        return d

    @model_validator(mode="after")
    def valida_conjuge_proprietario(self):
        # PJ (CNPJ) não tem cônjuge
        exige = (len(self.cpf_cnpj) == 11
                 and exige_conjuge(self.estado_civil, self.regime_bens))
        if exige and self.conjuge is None:
            raise ValueError(
                f"Cônjuge obrigatório para o proprietário {self.nome} "
                "(casado/união estável sem separação total de bens)")
        return self


class FotoImovel(BaseModel):
    """Alinhado ao padrão de reuso (FotosLaudo/uploadAPI): id do upload + legenda."""
    image_id: str
    legenda: str = ""
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None


class DocumentoImovel(BaseModel):
    image_id: str
    nome_arquivo: str = ""
    tipo: str = "outro"  # matricula | iptu | escritura | outro


class ChecklistDocumentacao(BaseModel):
    """Documentação analisada — mesmos itens da ficha PTAM (NBR 14653-1)."""
    matricula_do_imovel: bool = False
    carne_iptu: bool = False
    planta_projeto_aprovado: bool = False
    escritura_contrato: bool = False
    fotografias_do_imovel: bool = False
    habite_se_auto_conclusao: bool = False
    georreferenciamento_sigef_incra: bool = False
    ccir_cadastro_imovel_rural: bool = False
    itr_imposto_territorial_rural: bool = False
    car_cadastro_ambiental_rural: bool = False
    nirf_cib_receita_federal: bool = False
    certidoes_negativas: bool = False
    certidao_de_onus_reais: bool = False
    bci_boletim_cadastro_imobiliario: bool = False
    memorial_descritivo: bool = False
    metragem_das_construcoes: bool = False
    certidao_de_valor_venal: bool = False
    licenca_ambiental: bool = False
    art_trt: bool = False
    outros_documentos: bool = False
    etapa_concluida: bool = False


class ImovelContratoInput(BaseModel):
    """Objeto do contrato — espelho da ficha de imóvel do PTAM."""
    endereco: str
    bairro: str
    cidade: str = "Açailândia"
    uf: str = "MA"
    cep: Optional[str] = None
    matricula: Optional[str] = None
    cartorio: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_total_m2: Optional[float] = Field(default=None, ge=0)
    area_hectares: Optional[float] = Field(default=None, ge=0)
    confrontacoes: Optional[str] = None
    descricao_geral: str
    valor_anunciado: float = Field(gt=0)
    # ---- Cadastro Imobiliário Municipal (BCI) — Identificação Cadastral ----
    cti: Optional[str] = None                     # Código do Imóvel (CTI)
    inscricao_cadastral: Optional[str] = None     # Loc. cartográfica
    setor: Optional[str] = None
    quadra: Optional[str] = None
    lote: Optional[str] = None
    unidade: Optional[str] = None
    situacao_cadastral: Optional[str] = None
    natureza: Optional[str] = None
    data_cadastro: Optional[str] = None
    data_construcao: Optional[str] = None
    # ---- Proprietário/Detentor (BCI) ----
    proprietario_bci_nome: Optional[str] = None
    proprietario_bci_doc: Optional[str] = None    # CPF/CNPJ conforme BCI
    # ---- Medidas do Imóvel (BCI) ----
    testada_principal: Optional[float] = None
    profundidade_lote: Optional[float] = None
    area_terreno: Optional[float] = None
    area_edificacao: Optional[float] = None
    area_total_edificacao: Optional[float] = None
    # ---- IPTU ----
    iptu_inscricao_contribuinte: Optional[str] = None
    iptu_exercicio: Optional[str] = None
    iptu_valor_anual: Optional[float] = None
    iptu_situacao: Optional[str] = None
    iptu_vencimento: Optional[str] = None
    iptu_debito_total: Optional[float] = None
    iptu_desconto: Optional[float] = None
    iptu_valor_cobrado: Optional[float] = None
    # ---- Anexos ----
    fotos: list[FotoImovel] = Field(default_factory=list)
    documentos: list[DocumentoImovel] = Field(default_factory=list)
    checklist_documentacao: ChecklistDocumentacao = Field(default_factory=ChecklistDocumentacao)

    @field_validator("area_hectares")
    @classmethod
    def precisao_hectares(cls, v):
        return round(v, 4) if v is not None else v


class ContratoExclusividadeCreate(BaseModel):
    proprietarios: list[ProprietarioInput] = Field(min_length=1)
    imovel: ImovelContratoInput
    comissao_percentual: float = Field(ge=0.5, le=10.0)
    prazo_meses: int = Field(ge=1, le=24, default=6)
    multa_rescisoria: Optional[MultaRescisoria] = None
    reembolso_despesas: bool = False
    observacoes: Optional[str] = None
    # assinatura / foro / textos rich (opcionais)
    assinatura_cidade: Optional[str] = None
    assinatura_data: Optional[str] = None
    foro_comarca: str = "Açailândia/MA"
    observacoes_html: Optional[str] = None
    condicoes_especiais_html: Optional[str] = None
    # Guarda: arras NÃO se aplicam à exclusividade de corretagem
    arras: Optional[Any] = None

    @model_validator(mode="after")
    def valida_fracoes_e_duplicados(self):
        soma = round(sum(p.fracao_percentual for p in self.proprietarios), 2)
        if abs(soma - 100.0) > 0.05:  # tolerância p/ dízimas (33,33 × 3 = 99,99)
            raise ValueError(
                f"A soma das frações dos proprietários deve totalizar 100% (atual: {soma}%)")
        docs = [p.cpf_cnpj for p in self.proprietarios]
        if len(docs) != len(set(docs)):
            raise ValueError("Proprietário duplicado (mesmo CPF/CNPJ)")
        return self

    @field_validator("arras")
    @classmethod
    def rejeita_arras(cls, v):
        if v is not None:
            raise ValueError(
                "Arras não se aplicam a contrato de exclusividade de corretagem "
                "(instituto dos arts. 417-420 CC é próprio de compra e venda)")
        return v


class AceiteInput(BaseModel):
    concordo: bool
    nome_digitado: str  # reforço de manifestação de vontade


# ---------------------------------------------------------------------------
# v2 — Update parcial (autosave do wizard) e etapas de auditoria
# ---------------------------------------------------------------------------

from pydantic import ConfigDict  # noqa: E402


class ContratoExclusividadeUpdate(BaseModel):
    """
    Update PARCIAL do rascunho (autosave do wizard). TUDO opcional — no router usar
    model_dump(exclude_unset=True) + $set com merge profundo. Coração do fix 5-B:
    todos os campos novos estão declarados, então o validator não os descarta.
    Sub-objetos chegam como dict (merge por dot-notation no router) para permitir
    preenchimento progressivo campo a campo sem exigir o objeto inteiro.
    """
    model_config = ConfigDict(extra="ignore")

    proprietarios: Optional[list] = None   # lista inteira de condôminos (substitui a cada save)
    imovel: Optional[dict] = None          # ficha — merge profundo por campo
    comissao_percentual: Optional[float] = None
    prazo_meses: Optional[int] = None
    observacoes: Optional[str] = None
    multa_rescisoria: Optional[MultaRescisoria] = None
    reembolso_despesas: Optional[bool] = None
    # Campos da etapa 1 que precisam persistir (5-B)
    assinatura_cidade: Optional[str] = None
    assinatura_data: Optional[str] = None
    foro_comarca: Optional[str] = None
    observacoes_html: Optional[str] = None
    condicoes_especiais_html: Optional[str] = None
    colaborador_relatorio: Optional[str] = None


# Etapas do wizard (10) — usado para inicializar etapas[] e calcular andamento (%)
ETAPAS_PADRAO = [
    (1, "Proprietários"),
    (2, "Imóvel"),
    (3, "Fotos & Documentos"),
    (4, "Condições"),
    (5, "Revisão e Envio"),
]


def etapas_iniciais() -> list:
    return [
        {"etapa_numero": n, "etapa_nome": nome, "concluida": False,
         "concluida_em": None, "concluida_por": None}
        for n, nome in ETAPAS_PADRAO
    ]


def andamento_pct(etapas: list) -> int:
    total = len(etapas) or len(ETAPAS_PADRAO)
    feitas = sum(1 for e in (etapas or []) if e.get("concluida"))
    return round((feitas / total) * 100) if total else 0
