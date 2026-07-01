# @module utils.cpf — validação/formatação de CPF (assinatura eletrônica avançada).
from __future__ import annotations


def limpar_cpf(cpf: str) -> str:
    return "".join(c for c in (cpf or "") if c.isdigit())


def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelos dígitos verificadores (rejeita repetidos como 111.111.111-11)."""
    cpf = limpar_cpf(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def _dv(parcial: str, peso_inicial: int) -> int:
        soma = sum(int(d) * p for d, p in zip(parcial, range(peso_inicial, 1, -1)))
        resto = (soma * 10) % 11
        return 0 if resto == 10 else resto

    return _dv(cpf[:9], 10) == int(cpf[9]) and _dv(cpf[:10], 11) == int(cpf[10])


def formatar_cpf(cpf: str) -> str:
    cpf = limpar_cpf(cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf


def mascarar_cpf(cpf: str) -> str:
    """CPF mascarado p/ exibição pública (verificador): ***.456.789-**."""
    cpf = limpar_cpf(cpf)
    return f"***.{cpf[3:6]}.{cpf[6:9]}-**" if len(cpf) == 11 else "***"
