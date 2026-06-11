# @module models.perfil_corretor — Perfis de Corretor/Intermediador do usuário
# Fonte de dados do autofill "Usar meus dados" no wizard de Contratos/Propostas/Recibos.
# Um usuário pode ter vários perfis (PF e PJ), um marcado como `padrao`.
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from models.common import _id, _now


def _digits(s) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelos dígitos verificadores."""
    n = _digits(cpf)
    if len(n) != 11 or n == n[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(n[j]) * ((i + 1) - j) for j in range(i))
        dv = (soma * 10) % 11
        dv = 0 if dv == 10 else dv
        if dv != int(n[i]):
            return False
    return True


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ pelos dígitos verificadores."""
    n = _digits(cnpj)
    if len(n) != 14 or n == n[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    for pesos, pos in ((pesos1, 12), (pesos2, 13)):
        soma = sum(int(n[i]) * pesos[i] for i in range(pos))
        dv = soma % 11
        dv = 0 if dv < 2 else 11 - dv
        if dv != int(n[pos]):
            return False
    return True


class ConjugeDados(BaseModel):
    nome: str = ""
    cpf: Optional[str] = ""
    rg: Optional[str] = ""
    orgao_emissor: Optional[str] = ""
    data_nascimento: Optional[str] = ""
    profissao: Optional[str] = ""
    nacionalidade: Optional[str] = "brasileiro(a)"

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v):
        if v and _digits(v) and not validar_cpf(v):
            raise ValueError("CPF do cônjuge inválido")
        return v


class PerfilCorretorBase(BaseModel):
    tipo_pessoa: str = "fisica"  # fisica | juridica
    apelido: str = ""            # ex.: "José Romário (PF)", "Romatec (PJ)"
    padrao: bool = False
    # Pessoa Física
    nome: str = ""
    cpf: Optional[str] = ""
    rg: Optional[str] = ""
    orgao_emissor: Optional[str] = ""
    data_nascimento: Optional[str] = ""
    estado_civil: Optional[str] = ""
    profissao: Optional[str] = ""
    nacionalidade: Optional[str] = "brasileiro(a)"
    # Pessoa Jurídica
    razao_social: Optional[str] = ""
    cnpj: Optional[str] = ""
    representante: Optional[str] = ""
    # Credenciais profissionais
    creci: Optional[str] = ""
    cnai: Optional[str] = ""
    cft: Optional[str] = ""
    crea: Optional[str] = ""
    # Contato / endereço
    email: Optional[str] = ""
    telefone: Optional[str] = ""
    endereco: Optional[str] = ""
    cidade: Optional[str] = ""
    uf: Optional[str] = ""
    cep: Optional[str] = ""
    # Regime de bens + cônjuge (outorga conjugal — CC art. 1.647)
    regime_bens: Optional[str] = ""
    conjuge: Optional[ConjugeDados] = None

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v):
        if v and _digits(v) and not validar_cpf(v):
            raise ValueError("CPF inválido")
        return v

    @field_validator("cnpj")
    @classmethod
    def _check_cnpj(cls, v):
        if v and _digits(v) and not validar_cnpj(v):
            raise ValueError("CNPJ inválido")
        return v


class PerfilCorretor(PerfilCorretorBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
