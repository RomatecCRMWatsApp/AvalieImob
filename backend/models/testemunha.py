# @module models.testemunha — Testemunhas salvas do usuário (pessoas do escritório)
# Pré-cadastro reutilizável para autofill no passo Testemunhas do wizard de Contratos.
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


class TestemunhaBase(BaseModel):
    nome: str = ""
    cpf: Optional[str] = ""
    rg: Optional[str] = ""
    profissao: Optional[str] = ""
    endereco: Optional[str] = ""
    cidade: Optional[str] = ""
    uf: Optional[str] = ""

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v):
        if v and _digits(v) and not validar_cpf(v):
            raise ValueError("CPF inválido")
        return v


class Testemunha(TestemunhaBase):
    id: str = Field(default_factory=_id)
    user_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
