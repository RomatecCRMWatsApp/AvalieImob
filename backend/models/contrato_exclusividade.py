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
    nacionalidade: str = "brasileiro(a)"
    profissao: Optional[str] = None
    whatsapp: str  # E.164 sem '+', ex.: 5599999999999
    email: Optional[str] = None

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
    descricao: str
    endereco: str
    bairro: str
    cidade: str = "Açailândia"
    uf: str = "MA"
    matricula: Optional[str] = None
    cartorio: Optional[str] = None
    area_total: Optional[str] = None
    valor_anunciado: float


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


class ContratoExclusividadeCreate(BaseModel):
    proprietario: PessoaInput
    estado_civil: EstadoCivil
    regime_bens: Optional[RegimeBens] = None
    conjuge: Optional[PessoaInput] = None
    imovel: ImovelInput
    comissao_percentual: float = Field(ge=0.5, le=10.0)
    prazo_meses: int = Field(ge=1, le=24, default=6)
    observacoes: Optional[str] = None
    # Penalidade por rescisão antecipada (opcional)
    multa_rescisoria: Optional[MultaRescisoria] = None
    reembolso_despesas: bool = False
    # Guarda de segurança: arras NÃO se aplicam à exclusividade de corretagem
    arras: Optional[Any] = None

    @field_validator("conjuge")
    @classmethod
    def valida_conjuge(cls, v, info):
        ec = info.data.get("estado_civil")
        rb = info.data.get("regime_bens")
        if exige_conjuge(ec, rb) and v is None:
            raise ValueError(
                "Cônjuge/companheiro(a) é obrigatório para casados ou união "
                "estável, salvo regime de separação total de bens"
            )
        return v

    @field_validator("arras")
    @classmethod
    def rejeita_arras(cls, v):
        if v is not None:
            raise ValueError(
                "Arras não se aplicam a contrato de exclusividade de corretagem "
                "(instituto dos arts. 417-420 CC é próprio de compra e venda)"
            )
        return v


class AceiteInput(BaseModel):
    concordo: bool
    nome_digitado: str  # reforço de manifestação de vontade
