# @module services.inss_obra.params — Parâmetros da aferição indireta de obra predial (SERO).
#
# FONTE: Manual do SERO v3.0 (08/2024), Receita Federal — SHA-256 do PDF
# 916208b79c04c1fe9fcf78312c6c467298723cc1befe4d1b9a7c75c071110f99.
#
# Cada parâmetro carrega `fonte` (página do Manual) e `status`:
#   - "texto"   : o número está escrito no texto do Manual;
#   - "exemplo" : o número foi confirmado reproduzindo um exemplo numérico do Manual;
#   - "conferir": o número está numa FIGURA do Manual (sem texto extraível) e veio da
#                 IN RFB 2.021/2021 — conferir no PDF antes de tratar como definitivo.
# O motor marca a simulação com os parâmetros "conferir" que usou. NUNCA trocar um
# número aqui sem atualizar `fonte`/`status`.
from decimal import Decimal as D

VERSAO_MANUAL = "Manual do SERO v3.0 (08/2024)"

DESTINACOES = {
    "residencial_unifamiliar": "Residencial unifamiliar",
    "residencial_multifamiliar": "Residencial multifamiliar",
    "comercial_salas_lojas": "Comercial salas e lojas",
    "edificio_garagens": "Edifício de garagens",
    "galpao_industrial": "Galpão industrial",
    "casa_popular": "Casa popular",
    "conjunto_habitacional_popular": "Conjunto habitacional popular",
}
CATEGORIAS = {"obra_nova": "Obra nova", "acrescimo": "Acréscimo",
              "reforma": "Reforma", "demolicao": "Demolição"}
TIPOS = {"alvenaria": "Alvenaria", "mista": "Mista", "madeira": "Madeira"}
CLASSES_AREA = {"principal": "Principal",
                "complementar_coberta": "Compl. coberta",
                "complementar_descoberta": "Compl. descoberta"}

# 17.1 — Percentual de equivalência sobre as ÁREAS PRINCIPAIS, pela soma das áreas
# principais da destinação no projeto. (limite_m2, até_o_limite, acima_do_limite)
EQUIVALENCIA = {
    "residencial_unifamiliar": {"limite": D("1000"), "ate": D("0.89"), "acima": D("0.85"),
                                "status": "texto", "fonte": "Manual p.74 (exemplos 1 e 2)"},
    "residencial_multifamiliar": {"limite": D("1000"), "ate": D("0.90"), "acima": D("0.86"),
                                  "status": "texto", "fonte": "Manual p.73 (quadro conferido no PDF)"},
    "comercial_salas_lojas": {"limite": D("3000"), "ate": D("0.86"), "acima": D("0.83"),
                              "status": "texto", "fonte": "Manual p.73 (quadro conferido no PDF)"},
    "edificio_garagens": {"limite": D("3000"), "ate": D("0.86"), "acima": D("0.83"),
                          "status": "texto", "fonte": "Manual p.73 (quadro conferido no PDF)"},
    "galpao_industrial": {"limite": None, "ate": D("0.95"), "acima": D("0.95"),
                          "status": "texto", "fonte": "Manual p.73 (quadro conferido no PDF)"},
    "casa_popular": {"limite": None, "ate": D("0.98"), "acima": D("0.98"),
                     "status": "texto", "fonte": "Manual p.73 (quadro conferido no PDF)"},
    "conjunto_habitacional_popular": {"limite": None, "ate": D("0.98"), "acima": D("0.98"),
                                      "status": "texto", "fonte": "Manual p.73 (quadro conferido no PDF)"},
}

# 17.2 — Redução das áreas complementares (multiplicador da área)
COMPLEMENTAR = {"complementar_coberta": D("0.50"), "complementar_descoberta": D("0.25"),
                "status": "exemplo", "fonte": "Manual p.75 e p.80"}

# 19.1 — Percentual de mão de obra sobre o custo, por tipo (madeira e mista iguais)
_POPULARES = {"casa_popular", "conjunto_habitacional_popular"}
MAO_DE_OBRA = {
    "normal": {"alvenaria": D("0.20"), "mista": D("0.15"), "madeira": D("0.15")},
    "popular": {"alvenaria": D("0.12"), "mista": D("0.07"), "madeira": D("0.07")},
    "status": "exemplo", "fonte": "Manual p.80 (quadro) e p.81 (exemplo alvenaria/mista)",
}

# 19.2 — Percentual de cálculo por categoria
CATEGORIA_PCT = {"obra_nova": D("1"), "acrescimo": D("1"), "reforma": D("0.35"),
                 "demolicao": D("0.10"), "status": "texto", "fonte": "Manual p.82"}

# 19.3 — Percentual de cálculo por destinação (edifício de garagens: redução de 20%)
DESTINACAO_PCT = {"edificio_garagens": D("0.80"), "status": "texto", "fonte": "Manual p.84"}

# 19.4 — Fator social (só pessoa física), pela área total da CATEGORIA no projeto
# (principal + complementar, sem área existente). (área máxima inclusiva, índice)
FATOR_SOCIAL = {
    "faixas": [(D("100"), D("0.20")), (D("200"), D("0.40")), (D("300"), D("0.55")),
               (D("400"), D("0.70")), (None, D("0.90"))],
    "status": "texto", "fonte": "Manual p.85",
}

# 21.5 — Crédito por concreto/argamassa usinada ou massa asfáltica
USINADO_FATOR = D("0.05")
USINADO_CATEGORIA = {"obra_nova": D("1"), "acrescimo": D("1"), "reforma": D("0.35"),
                     "demolicao": D("0")}
_USINADO_COLS = ["casa_popular", "comercial_salas_lojas", "conjunto_habitacional_popular",
                 "edificio_garagens", "galpao_industrial", "residencial_multifamiliar",
                 "residencial_unifamiliar"]
_USINADO_TXT = """
AC 4,69 13,33 4,69 13,33 4,52 9,61 7,43
AL 3,98 11,35 3,98 11,35 3,82 8,12 6,11
AM 4,69 13,33 4,69 13,33 4,52 9,61 7,43
AP 4,88 12,93 4,88 12,93 4,38 9,41 7,48
BA 3,73 10,31 3,73 10,31 3,62 7,46 5,53
CE 3,70 10,69 3,70 10,69 3,44 7,69 5,72
DF 3,53 9,62 3,53 9,62 3,43 7,06 5,24
ES 3,33 9,45 3,33 9,45 3,26 6,85 5,15
GO 3,88 10,27 3,88 10,27 3,60 7,62 5,79
MA 4,18 12,06 4,18 12,06 4,07 8,73 6,94
MG 3,15 8,66 3,15 8,66 3,05 6,22 4,68
MS 4,34 12,20 4,34 12,20 4,28 8,74 6,74
MT 4,02 10,96 4,02 10,96 3,89 8,01 6,22
PA 4,91 13,48 4,91 13,48 4,45 9,77 7,58
PB 4,12 11,81 4,12 11,81 3,81 8,58 6,32
PE 3,51 9,74 3,51 9,47 3,42 6,89 5,12
PI 3,53 10,00 3,53 10,00 3,30 7,16 5,33
PR 3,18 8,78 3,18 8,78 3,08 6,50 4,91
RJ 3,20 9,02 3,20 9,02 3,08 6,52 4,94
RN 4,01 10,41 4,01 10,41 3,63 7,62 5,96
RO 4,02 10,96 4,02 10,96 3,89 8,01 6,22
RR 4,69 13,33 4,69 13,33 4,52 9,61 7,43
RS 3,25 8,77 3,25 8,77 3,23 6,54 5,01
SC 2,93 8,36 2,93 8,36 2,87 6,19 4,79
SE 4,34 12,50 4,34 12,50 4,18 9,05 6,97
SP 3,15 8,69 3,15 8,69 2,96 6,35 4,90
TO 3,53 10,00 3,53 10,00 3,30 7,16 5,33
"""
USINADO_UF = {}
for _l in _USINADO_TXT.strip().splitlines():
    _p = _l.split()
    USINADO_UF[_p[0]] = {c: D(v.replace(",", ".")) / 100 for c, v in zip(_USINADO_COLS, _p[1:])}
# Conferido célula a célula no PDF (p.137). Mantido como está no Manual, inclusive
# PE: comercial 9,74% × edifício de garagens 9,47% (únicas colunas que diferem entre si).
USINADO_STATUS = {"status": "texto", "fonte": "Manual p.137 (quadro conferido no PDF)"}
UFS = sorted(USINADO_UF)

# 23 — Alíquotas sobre a RMT, por código de receita da DCTFWeb Aferição de Obras
# (quadro da p.149, conferido no PDF; soma 36,8% reproduz os exemplos p.97 e p.149).
# (sigla, código de receita, descrição, alíquota) — na ordem do quadro do Manual.
ALIQUOTAS = [
    ("PAT", "1138-31", "CP patronal — empregados", D("0.20")),
    ("SEG", "1082-31", "CP segurados — empregados", D("0.08")),
    ("GILRAT", "1646-31", "CP patronal — GILRAT", D("0.03")),
    ("FNDE", "1170-31", "Terceiros — salário-educação", D("0.025")),
    ("INCRA", "1176-31", "Terceiros — INCRA", D("0.002")),
    ("SEBRAE", "1200-31", "Terceiros — SEBRAE", D("0.006")),
    ("SESI", "1184-31", "Terceiros — SESI", D("0.015")),
    ("SENAI", "1181-31", "Terceiros — SENAI", D("0.01")),
]
ALIQUOTAS_STATUS = {"status": "texto", "fonte": "Manual p.149 (quadro conferido no PDF)"}


def percentual_mao_de_obra(destinacao: str, tipo: str) -> D:
    grupo = "popular" if destinacao in _POPULARES else "normal"
    return MAO_DE_OBRA[grupo][tipo]


def fator_social(area_categoria: D) -> D:
    for limite, indice in FATOR_SOCIAL["faixas"]:
        if limite is None or area_categoria <= limite:
            return indice
    return D("0.90")


def equivalencia(destinacao: str, area_principal_destinacao: D) -> D:
    e = EQUIVALENCIA[destinacao]
    if e["limite"] is None or area_principal_destinacao <= e["limite"]:
        return e["ate"]
    return e["acima"]


def opcoes() -> dict:
    """Catálogo para a tela."""
    return {
        "destinacoes": [{"valor": k, "rotulo": v} for k, v in DESTINACOES.items()],
        "categorias": [{"valor": k, "rotulo": v} for k, v in CATEGORIAS.items()],
        "tipos": [{"valor": k, "rotulo": v} for k, v in TIPOS.items()],
        "classes_area": [{"valor": k, "rotulo": v} for k, v in CLASSES_AREA.items()],
        "ufs": UFS,
        "versao_manual": VERSAO_MANUAL,
    }
