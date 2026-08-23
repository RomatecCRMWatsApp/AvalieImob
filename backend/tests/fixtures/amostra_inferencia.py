# @module tests.fixtures.amostra_inferencia — amostra-demo do motor de inferência.
#
# 32 dados de mercado (k = 4), materializados como LITERAIS para o teste não
# depender do gerador de números aleatórios do numpy (que muda entre versões).
# Reproduz a amostra da implementação de referência: Fundamentação III,
# Precisão III, IP 80% ≈ 15%, VIF máx ≈ 1,07, pressupostos todos atendidos.
import pandas as pd

# (dado_id, vu R$/m², área m², distância ao centro m, pavimentação 0/1, esquina 0/1)
DADOS = [
    ("D01", 19.72, 507, 2034, 0, 0),
    ("D02", 20.56, 752, 2386, 1, 1),
    ("D03", 27.89, 301, 2010, 1, 0),
    ("D04", 17.45, 751, 2710, 0, 1),
    ("D05", 28.70, 395, 691, 0, 0),
    ("D06", 22.01, 457, 1816, 0, 1),
    ("D07", 22.20, 684, 1656, 1, 0),
    ("D08", 32.17, 449, 743, 1, 1),
    ("D09", 22.87, 528, 2075, 1, 0),
    ("D10", 29.22, 235, 2561, 1, 0),
    ("D11", 19.47, 642, 1964, 1, 0),
    ("D12", 24.91, 521, 1198, 1, 1),
    ("D13", 23.49, 405, 2532, 1, 0),
    ("D14", 23.33, 662, 1772, 0, 1),
    ("D15", 22.96, 390, 1775, 0, 1),
    ("D16", 18.03, 474, 2332, 0, 0),
    ("D17", 32.59, 295, 940, 0, 1),
    ("D18", 21.22, 446, 2485, 1, 0),
    ("D19", 24.60, 334, 2172, 1, 0),
    ("D20", 20.32, 367, 2410, 0, 0),
    ("D21", 25.91, 640, 1041, 1, 0),
    ("D22", 23.01, 377, 2445, 1, 0),
    ("D23", 27.82, 492, 1040, 1, 0),
    ("D24", 22.13, 769, 788, 0, 0),
    ("D25", 15.42, 759, 2567, 0, 0),
    ("D26", 19.36, 626, 2581, 1, 0),
    ("D27", 17.19, 523, 2616, 0, 0),
    ("D28", 28.60, 375, 1685, 1, 1),
    ("D29", 28.61, 310, 1230, 1, 0),
    ("D30", 28.52, 763, 616, 1, 1),
    ("D31", 22.91, 509, 2085, 0, 1),
    ("D32", 28.69, 285, 2256, 1, 1),
]

AVALIANDO = {"area": 450, "dist_centro": 1200, "pavimentacao": 1, "esquina": 0}
AREA_TOTAL_AVALIANDO = 450.0


def gerar_amostra() -> pd.DataFrame:
    return pd.DataFrame(
        DADOS, columns=["dado_id", "vu", "area", "dist_centro", "pavimentacao", "esquina"])


def amostra_dicts() -> list:
    """Formato persistido em `modelos_inferencia.amostra`."""
    return [
        {"dado_id": d[0], "utilizado": True, "motivo_descarte": None,
         "variaveis": {"vu": d[1], "area": d[2], "dist_centro": d[3],
                       "pavimentacao": d[4], "esquina": d[5]}}
        for d in DADOS
    ]


ESPECIFICACAO = {
    "dependente": {"campo": "vu", "transformacao": "ln"},
    "regressores": [
        {"campo": "area", "transformacao": "ln", "tipo": "quantitativa", "rotulo": "AREA"},
        {"campo": "dist_centro", "transformacao": "ln", "tipo": "quantitativa", "rotulo": "DIST"},
        {"campo": "pavimentacao", "transformacao": "identidade", "tipo": "dicotomica", "rotulo": "PAV"},
        {"campo": "esquina", "transformacao": "identidade", "tipo": "dicotomica", "rotulo": "ESQ"},
    ],
    "intercepto": True,
}
