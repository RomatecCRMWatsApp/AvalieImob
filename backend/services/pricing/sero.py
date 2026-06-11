# @module services.pricing.sero — SERO/INSS de obra (aferição indireta IN RFB 2021/2021).
# Port fiel de sero-calculator.ts. Custo Global = CUB × área; RMT = Custo × %mão de obra;
# INSS = RMT×20%; Sistema S = RMT×8%; TOTAL = INSS + Sistema S (0 se PJ com contabilidade).
from __future__ import annotations

from services.pricing.params import SERO_INSS, cub_por_padrao


def calcular_sero(*, area_construida: float, padrao_construtivo: str, modalidade: str,
                  responsavel: str, com_premoldados: bool = False) -> dict:
    cub = cub_por_padrao(padrao_construtivo)
    custo_global = area_construida * cub

    pmo_tab = SERO_INSS["percentual_mao_obra"]
    if modalidade == "residencial":
        pmo = pmo_tab["residencial_alvenaria_com_premoldado"] if com_premoldados \
            else pmo_tab["residencial_alvenaria_sem_premoldado"]
    else:
        pmo = pmo_tab["comercial_medio"]

    rmt = custo_global * pmo
    inss = rmt * SERO_INSS["aliquota_inss"]
    sistema_s = rmt * SERO_INSS["aliquota_sistema_s"]

    aplica_sero = responsavel != "PJ_com_contabilidade"
    total = (inss + sistema_s) if aplica_sero else 0.0

    return {
        "custo_global": custo_global,
        "rmt": rmt,
        "inss": inss,
        "sistema_s": sistema_s,
        "total": total,
        "cub_usado": cub,
        "percentual_mao_obra": pmo,
        "fonte": SERO_INSS["fonte"],
        "aviso": SERO_INSS["aviso_pdf"],
        "observacao_pj": (None if aplica_sero else
                          "Apurado via contabilidade regular da PJ (nao se aplica SERO afericao indireta)."),
    }
