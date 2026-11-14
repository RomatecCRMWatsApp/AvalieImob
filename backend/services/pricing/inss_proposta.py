# @module services.pricing.inss_proposta — INSS da obra nas propostas (averbação, projeto executivo).
#
# Usa o MESMO motor do módulo INSS de Obra (services.inss_obra), conferido com o Manual do
# SERO v3.0. Origens:
#   1) `_inss_obra_sim` (injetado pela rota quando a proposta é vinculada a uma obra do módulo)
#      → usa a última simulação daquela obra, sem recalcular;
#   2) PJ com contabilidade → 0 (apura pela escrituração);
#   3) senão, simula com os campos da proposta; sem VAU, estima pelo CUB-MA e avisa.
from __future__ import annotations

from datetime import date

from services.inss_obra import ErroSimulacao, simular as simular_inss
from services.pricing.params import cub_por_padrao


# ── INSS da obra (motor do módulo INSS de Obra) ─────────────────────────────
_DEST_POR_MODALIDADE = {"residencial": "residencial_unifamiliar", "comercial": "comercial_salas_lojas"}


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _br(v) -> str:
    s = f"{float(v):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _m2(v) -> str:
    return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v) -> str:
    return (f"{float(v) * 100:.2f}".rstrip("0").rstrip(".")).replace(".", ",") + "%"


def _base_calculo(res: dict) -> list:
    """Memória de cálculo do motor no formato {rotulo, formula, valor_resultado} da proposta."""
    out = []
    for l in res["linhas"]:
        nome = (l.get("descricao") or "").strip() or {
            "principal": "Área principal", "complementar_coberta": "Área complementar coberta",
            "complementar_descoberta": "Área complementar descoberta"}[l["classe"]]
        out.append({
            "rotulo": f"Custo da obra — {nome}",
            "formula": (f"{_m2(l['area_m2'])} m² × {_pct(l['reducao_area'])} = "
                        f"{_m2(l['area_calculo'])} m² × VAU {_br(l['vau'])}/m²"),
            "valor_resultado": float(l["cod"]),
        })
        fatores = f"{_pct(l['pct_mao_de_obra'])} mão de obra"
        pc = float(l["pct_categoria"]) * float(l["pct_destinacao"])
        if pc != 1:
            fatores += f" × {_pct(pc)} categoria/destinação"
        if float(l["fator_social"]) != 1:
            fatores += f" × {_pct(l['fator_social'])} fator social"
        out.append({"rotulo": f"RMT — {nome}", "formula": f"{_br(l['cod'])} × {fatores}",
                    "valor_resultado": float(l["rmt"])})
    dec = res["decadencia"]
    if dec["meses_decadentes"]:
        out.append({"rotulo": "RMT não decadente",
                    "formula": (f"{_br(res['rmt_total'])} × {dec['meses_nao_decadentes']}/{dec['meses_total']} "
                                f"meses não decadentes"),
                    "valor_resultado": float(res["rmt_nao_decadente"])})
    if res["usinado"]["aplicado"] and float(res["usinado"]["credito"]) > 0:
        out.append({"rotulo": "(−) Crédito concreto/argamassa usinada", "formula": "COD × % UF × 5%",
                    "valor_resultado": float(res["usinado"]["credito"])})
    for d in res["debitos"]:
        out.append({"rotulo": f"{d.get('codigo_receita') or d['codigo']} — {d['nome']}",
                    "formula": f"{_br(res['base_calculo'])} × {_pct(d['aliquota'])}",
                    "valor_resultado": float(d["valor"])})
    out.append({"rotulo": "TOTAL INSS DA OBRA (SERO)", "formula": "36,8% sobre a RMT não decadente",
                "valor_resultado": float(res["total"])})
    return out


def inss_da_obra(dados: dict, modalidade: str, area_construida: float, padrao: str,
                 responsavel: str) -> dict:
    """Estima o INSS da obra para uma proposta. Devolve {total, origem, fonte, observacao,
    aviso, base_calculo[, vau, vau_estimado]}."""
    fonte = "Manual do SERO v3.0 (08/2024) — IN RFB 2.021/2021"
    aviso_base = ("INSS DA OBRA: valor ESTIMADO pela metodologia do Manual do SERO (afericao indireta). "
                  "O valor definitivo e o apurado no SERO/e-CAC na conclusao da afericao (DCTFWeb Afericao "
                  "de Obras).")

    # 1) Simulação vinculada do módulo INSS de Obra
    sim = dados.get("_inss_obra_sim")
    if isinstance(sim, dict) and sim.get("resultado"):
        res = sim["resultado"]
        num = sim.get("numero") or ""
        return {"total": float(res["total"]), "origem": "inss_obra", "fonte": fonte,
                "observacao": f"Conforme simulacao {num} do modulo INSS de Obra (memoria abaixo).",
                "aviso": aviso_base + f" Valor trazido da simulacao {num}.",
                "base_calculo": _base_calculo(res)}

    # PJ com contabilidade regular apura pela escrituração (Manual item 26.2)
    if responsavel == "PJ_com_contabilidade":
        return {"total": 0.0, "origem": "pj_contabilidade", "fonte": fonte,
                "observacao": ("Apurado via contabilidade regular da PJ (Manual do SERO item 26.2) — "
                               "nao se aplica afericao indireta."),
                "aviso": aviso_base, "base_calculo": []}

    if area_construida <= 0:
        return {"total": 0.0, "origem": "sem_area", "fonte": fonte,
                "observacao": "Informe a area construida para estimar o INSS da obra.",
                "aviso": aviso_base, "base_calculo": []}

    # 2) Simulação com os campos da proposta
    destinacao = dados.get("inss_destinacao") or _DEST_POR_MODALIDADE.get(modalidade, "residencial_unifamiliar")
    vau = _num(dados.get("vau_m2"))
    vau_estimado = vau <= 0
    if vau_estimado:
        vau = cub_por_padrao(padrao)
    areas = [{"descricao": "Area principal", "destinacao": destinacao,
              "categoria": dados.get("inss_categoria") or "obra_nova",
              "tipo": dados.get("inss_tipo") or "alvenaria", "classe": "principal",
              "area_m2": area_construida}]
    for classe, chave, rot in (("complementar_coberta", "area_complementar_coberta", "Area complementar coberta"),
                               ("complementar_descoberta", "area_complementar_descoberta",
                                "Area complementar descoberta")):
        a = _num(dados.get(chave))
        if a > 0:
            areas.append({**areas[0], "descricao": rot, "classe": classe, "area_m2": a})
    hoje = date.today().isoformat()
    entrada = {"responsavel": "PF" if responsavel == "PF" else "PJ", "uf": dados.get("uf") or "MA",
               "vau": {destinacao: vau}, "areas": areas, "usinado": bool(dados.get("usinado")),
               "data_inicio": dados.get("data_inicio_obra") or hoje,
               "data_fim": dados.get("data_fim_obra") or dados.get("data_inicio_obra") or hoje,
               "data_afericao": hoje}
    try:
        res = simular_inss(entrada)
    except ErroSimulacao as e:
        return {"total": 0.0, "origem": "erro", "fonte": fonte,
                "observacao": f"Nao foi possivel estimar o INSS: {e}", "aviso": aviso_base,
                "base_calculo": []}
    aviso = aviso_base
    if vau_estimado:
        aviso += (f" VAU ESTIMADO pelo CUB-MA do padrao {padrao} ({_br(vau)}/m²): informe o VAU "
                  f"do SERO (e-CAC > SERO > Consultar Tabela VAU) para um valor mais preciso.")
    obs = (f"RMT {_br(res['rmt_nao_decadente'])} × 36,8% — VAU {_br(vau)}/m² "
           f"({'estimado pelo CUB' if vau_estimado else 'informado do SERO'})")
    return {"total": float(res["total"]), "origem": "proposta", "fonte": fonte, "observacao": obs,
            "aviso": aviso, "base_calculo": _base_calculo(res), "vau": vau, "vau_estimado": vau_estimado}
