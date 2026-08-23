# @module services.inferencia.enquadramento — Graus de Fundamentação e Precisão (NBR 14653).
#
# Limiares vêm de params/nbr14653_*.json — NUNCA hard-coded (MD §8).
# Saída: grau por item, grau final e a lista OBJETIVA do que impede o Grau III.
import json
from functools import lru_cache
from pathlib import Path

_DIR_PARAMS = Path(__file__).resolve().parent / "params"
_ARQUIVO = {"14653-2": "nbr14653_2.json", "14653-3": "nbr14653_3.json",
            "urbano": "nbr14653_2.json", "rural": "nbr14653_3.json"}

ORDEM = {"III": 3, "II": 2, "I": 1, "fora": 0}


@lru_cache(maxsize=8)
def carregar_params(norma: str = "14653-2") -> dict:
    nome = _ARQUIVO.get(str(norma), _ARQUIVO["14653-2"])
    with open(_DIR_PARAMS / nome, encoding="utf-8") as fh:
        return json.load(fh)


def _grau_por_limite(valor: float, limites: dict) -> str:
    """Menor é melhor: devolve o melhor grau cujo limite o valor respeita."""
    for g in ("III", "II", "I"):
        if valor <= limites[g]:
            return g
    return "fora"


def _fmt_pct(v: float, casas: int = 2) -> str:
    return ("< 0,0001%" if v * 100 < 1e-4 else f"{v * 100:.{casas}f}%").replace(".", ",")


def enquadrar(n, k, signif_f, regressores_out, amplitude_ip, extrapolacoes,
              params: dict) -> dict:
    itens = []

    # 1. Quantidade mínima de dados efetivamente utilizados
    minimos = {g: f * (k + 1) for g, f in params["dados_min_fator"].items()}
    g_dados = "fora"
    for g in ("III", "II", "I"):
        if n >= minimos[g]:
            g_dados = g
            break
    itens.append({
        "item": "Quantidade mínima de dados efetivamente utilizados",
        "grau": g_dados,
        "detalhe": (f"n = {n}; exigido {minimos['III']} (III), {minimos['II']} (II), "
                    f"{minimos['I']} (I) para k = {k}"),
        "automatico": True,
    })

    # 2. Significância por regressor (t bicaudal) — pior caso
    nao_intercepto = [r for r in regressores_out if not r["eh_intercepto"]]
    pior = max((r["significancia"] for r in nao_intercepto), default=1.0)
    nome_pior = max(nao_intercepto, key=lambda r: r["significancia"])["nome"] \
        if nao_intercepto else "—"
    g_t = _grau_por_limite(pior, params["signif_regressor_max"])
    lim_t = params["signif_regressor_max"]
    itens.append({
        "item": "Nível de significância máximo por regressor (teste t bicaudal)",
        "grau": g_t,
        "detalhe": (f"pior caso: {nome_pior} com {_fmt_pct(pior)}; limites "
                    f"{_fmt_pct(lim_t['III'], 0)} (III), {_fmt_pct(lim_t['II'], 0)} (II), "
                    f"{_fmt_pct(lim_t['I'], 0)} (I)"),
        "automatico": True,
    })

    # 3. Significância do modelo (teste F)
    g_f = _grau_por_limite(float(signif_f), params["signif_modelo_max"])
    lim_f = params["signif_modelo_max"]
    itens.append({
        "item": "Nível de significância máximo do modelo (teste F)",
        "grau": g_f,
        "detalhe": (f"significância de F = {_fmt_pct(float(signif_f), 4)}; limites "
                    f"{_fmt_pct(lim_f['III'], 0)} (III), {_fmt_pct(lim_f['II'], 0)} (II), "
                    f"{_fmt_pct(lim_f['I'], 0)} (I)"),
        "automatico": True,
    })

    # 4. Extrapolação — não admitida no Grau III
    g_ex = "III" if not extrapolacoes else ("II" if len(extrapolacoes) == 1 else "fora")
    itens.append({
        "item": "Extrapolação das características do avaliando",
        "grau": g_ex,
        "detalhe": ("sem extrapolação" if not extrapolacoes else
                    "extrapola: " + ", ".join(e["campo"] for e in extrapolacoes)),
        "automatico": True,
    })

    grau_fund = {3: "III", 2: "II", 1: "I", 0: "fora"}[min(ORDEM[i["grau"]] for i in itens)]

    # Grau de PRECISÃO — amplitude do IP 80%
    g_prec = _grau_por_limite(float(amplitude_ip), params["amplitude_ip80_max"])

    bloqueios = [f"{i['item']}: {i['detalhe']}" for i in itens if ORDEM[i["grau"]] < 3]
    if g_prec != "III":
        bloqueios.append(
            f"Grau de Precisão: amplitude do IP 80% = {_fmt_pct(float(amplitude_ip))} "
            f"(limite {_fmt_pct(params['amplitude_ip80_max']['III'], 0)} para Grau III)")

    return {
        "itens": itens,
        "grau_fundamentacao": grau_fund,
        "grau_precisao": g_prec,
        "amplitude_ip80": float(amplitude_ip),
        "bloqueios_grau_iii": bloqueios,
        "checklist_manual": list(params.get("checklist_manual") or []),
        "norma": params.get("_norma"),
    }
