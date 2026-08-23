# @module services.inferencia.transformacoes — catálogo de transformações e inversas.
#
# Portado da implementação de referência (engine_inferencia_referencia.py), que já
# passou nas 21 verificações de aceite. Não reescrever a matemática: qualquer
# mudança aqui invalida a conferência contra software de referência do setor.
#
# Domínio violado por QUALQUER dado ⇒ falha indicando o dado e a variável.
# Nunca substituir por zero nem descartar em silêncio (regra da NBR e do MD).
from typing import Any

import numpy as np


class ErroInferencia(Exception):
    """Falha de domínio, de especificação ou de suficiência amostral."""


TRANSFORMACOES: dict[str, dict[str, Any]] = {
    "identidade": {
        "rotulo": "x",
        "f": lambda x: x,
        "inv": lambda y: y,
        "dominio": lambda x: True,
    },
    "ln": {
        "rotulo": "ln(x)",
        "f": np.log,
        "inv": np.exp,
        "dominio": lambda x: np.all(x > 0),
    },
    "inverso": {
        "rotulo": "1/x",
        "f": lambda x: 1.0 / x,
        "inv": lambda y: 1.0 / y,
        "dominio": lambda x: np.all(x != 0),
    },
    "quadrado": {
        "rotulo": "x^2",
        "f": lambda x: x ** 2,
        "inv": lambda y: np.sqrt(y),
        "dominio": lambda x: True,
    },
    "raiz": {
        "rotulo": "sqrt(x)",
        "f": np.sqrt,
        "inv": lambda y: y ** 2,
        "dominio": lambda x: np.all(x >= 0),
    },
}

# Rótulos legíveis para a tela e para o laudo.
ROTULO_HUMANO = {
    "identidade": "sem transformação (x)",
    "ln": "logaritmo natural — ln(x)",
    "inverso": "inverso — 1/x",
    "quadrado": "quadrado — x²",
    "raiz": "raiz quadrada — √x",
}


def aplicar(transf: str, valores: np.ndarray, nome_campo: str) -> np.ndarray:
    """Aplica a transformação validando o domínio. Levanta ErroInferencia."""
    if transf not in TRANSFORMACOES:
        raise ErroInferencia(f"Transformação desconhecida: {transf}")
    t = TRANSFORMACOES[transf]
    valores = np.asarray(valores, dtype=float)
    if not t["dominio"](valores):
        fora = _indices_fora(transf, valores)
        raise ErroInferencia(
            f"Transformação '{transf}' inválida para a variável '{nome_campo}': "
            f"há dado fora do domínio da função"
            + (f" (linha(s) {', '.join(str(i + 1) for i in fora)})." if fora else ".")
        )
    return np.asarray(t["f"](valores), dtype=float)


def _indices_fora(transf: str, valores: np.ndarray) -> list:
    """Quais linhas violam o domínio — a mensagem tem de apontar o dado."""
    if transf == "ln":
        return list(np.where(valores <= 0)[0])
    if transf == "inverso":
        return list(np.where(valores == 0)[0])
    if transf == "raiz":
        return list(np.where(valores < 0)[0])
    return []


def inversa(transf: str):
    """Função inversa da transformação (para destransformar LIMITES, nunca amplitudes)."""
    if transf not in TRANSFORMACOES:
        raise ErroInferencia(f"Transformação desconhecida: {transf}")
    return TRANSFORMACOES[transf]["inv"]


def rotular(transf: str, nome: str) -> str:
    """AREA + ln → 'ln(AREA)'."""
    if transf == "identidade":
        return nome
    return TRANSFORMACOES[transf]["rotulo"].replace("x", nome)


# Compat com a implementação de referência (nome privado usado no motor).
_aplicar = aplicar
