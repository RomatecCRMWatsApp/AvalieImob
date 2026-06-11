# @module services.pricing.tjma — Emolumentos cartorários TJMA 2026 (port fiel da ZAYRA).
# Resolução GP 143/2025 TJMA — valores TOTAL (emolumentos+FERC+FADEP+FEMP+FERRFIS).
from __future__ import annotations

import math
from datetime import datetime, timezone

INF = math.inf

# Tabela 16.3 — Registro de atos com valor declarado.
TABELA_16_3 = [
    (5917.36, 111.11), (7692.57, 140.01), (9615.72, 158.55), (12019.65, 196.77),
    (15024.56, 244.66), (18780.69, 306.77), (23475.86, 384.85), (29344.81, 481.65),
    (36681.02, 599.84), (45851.29, 750.69), (57314.07, 939.28), (71642.58, 1173.09),
    (89553.26, 1466.33), (111941.56, 1832.33), (139926.94, 2289.78), (174908.66, 2862.74),
    (218635.83, 3578.55), (273294.81, 4474.29), (341618.50, 5590.81), (427023.14, 6989.72),
    (533778.91, 8736.26), (667223.64, 10920.44), (834029.56, 13651.34), (1042536.94, 16209.99),
    (1303171.21, 17299.63), (1563805.44, 17818.55), (1876566.51, 18353.16), (2251879.82, 18903.80),
    (2702255.82, 19470.93), (3242706.98, 20055.05), (3891248.37, 20656.61), (4669498.05, 21276.39),
    (5603397.67, 21914.57), (6724077.19, 22572.09), (8068892.63, 23249.22), (INF, 23946.65),
]

# Tabela 16.9 — Registros torrens com valor declarado (base p/ averbação com valor).
TABELA_16_9 = [
    (5917.36, 55.79), (7692.57, 69.61), (9615.72, 79.21), (12019.65, 97.91),
    (15024.56, 122.40), (18780.69, 153.07), (23475.86, 192.35), (29344.81, 240.90),
    (36681.02, 300.16), (45851.29, 375.12), (57314.07, 469.55), (71642.58, 586.80),
    (89553.26, 733.25), (111941.56, 916.01), (139926.94, 1144.81), (174908.66, 1431.60),
    (218635.83, 1789.11), (273294.81, 2237.14), (341618.50, 2795.50), (427023.14, 3494.94),
    (533778.91, 4367.74), (667223.64, 5460.36), (834029.56, 6826.00), (1042536.94, 8254.14),
    (1303171.21, 8652.66), (1563805.44, 8912.43), (1876566.51, 9179.87), (2251879.82, 9455.21),
    (2702255.82, 9738.85), (3242706.98, 10030.99), (3891248.37, 10331.76), (4669498.05, 10641.97),
    (5603397.67, 10961.14), (6724077.19, 11289.88), (8068892.63, 11628.53), (INF, 11977.56),
]

VALOR_AVERBACAO_SEM_VALOR_DECLARADO = 134.43   # 16.22.2
VALOR_AVERBACAO_GEORREF_SIGEF = 557.94          # 16.22.4
VALOR_DESDOBRO_UNIFICACAO = 161.54              # 16.22.6
VALOR_REGISTRO_LOTE_DESM_INCORP = 161.54        # 16.5 / 16.6 (por unidade)
VALOR_PRENOTACAO = 43.37                         # 16.1
VALOR_MATRICULA = 102.15                         # 16.2


def _buscar_faixa(tabela, valor_declarado: float) -> float:
    for ate, valor in tabela:
        if valor_declarado <= ate:
            return valor
    return tabela[-1][1]


def calcular_emolumentos(ato: str, valor_declarado: float = 0) -> dict:
    """Espelha calcularEmolumentos(ato, valorDeclarado) da ZAYRA."""
    consultado_em = datetime.now(timezone.utc).isoformat()
    if ato == "averbacao_construcao":
        return {"valor": _buscar_faixa(TABELA_16_9, valor_declarado), "fonte": "fallback",
                "consultadoEm": consultado_em,
                "base_calculo": "Tabela TJMA 16.9 — registros torrens (averbacao com valor)",
                "observacao": f"Valor venal: R$ {valor_declarado:.2f}"}
    if ato == "averbacao_sem_valor":
        return {"valor": VALOR_AVERBACAO_SEM_VALOR_DECLARADO, "fonte": "fallback",
                "consultadoEm": consultado_em,
                "base_calculo": "Tabela TJMA 16.22.2 — averbacao sem valor declarado"}
    if ato == "registro_propriedade":
        return {"valor": _buscar_faixa(TABELA_16_3, valor_declarado), "fonte": "fallback",
                "consultadoEm": consultado_em,
                "base_calculo": "Tabela TJMA 16.3 — registro com valor declarado"}
    if ato == "retificacao":
        return {"valor": _buscar_faixa(TABELA_16_9, valor_declarado) * 0.5, "fonte": "fallback",
                "consultadoEm": consultado_em,
                "base_calculo": "Tabela TJMA 16.22.8.1 — retificacao (16.9 com 50%)"}
    if ato == "desmembramento":
        return {"valor": _buscar_faixa(TABELA_16_3, valor_declarado), "fonte": "fallback",
                "consultadoEm": consultado_em,
                "base_calculo": "Tabela TJMA 16.3 — registro de desmembramento (acrescentar 16.5 por lote)"}
    if ato == "georreferenciamento":
        return {"valor": VALOR_AVERBACAO_GEORREF_SIGEF, "fonte": "fallback",
                "consultadoEm": consultado_em,
                "base_calculo": "Tabela TJMA 16.22.4 — averbacao certificacao SIGEF/INCRA"}
    if ato == "desdobro_unificacao":
        return {"valor": VALOR_DESDOBRO_UNIFICACAO, "fonte": "fallback",
                "consultadoEm": consultado_em,
                "base_calculo": "Tabela TJMA 16.22.6 — desdobro/unificacao"}
    raise ValueError(f"Ato TJMA desconhecido: {ato}")


def valor_por_lote_adicional() -> float:
    return VALOR_REGISTRO_LOTE_DESM_INCORP
