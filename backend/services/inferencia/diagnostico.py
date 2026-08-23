# @module services.inferencia.diagnostico — verificação dos pressupostos do modelo.
#
# Normalidade (KS/Lilliefors + Jarque-Bera), aderência dos resíduos padronizados,
# homocedasticidade (Breusch-Pagan + White), autocorrelação (Durbin-Watson),
# multicolinearidade (correlação + VIF) e pontos discrepantes.
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan, het_white, lilliefors
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera

# Percentis teóricos da normal para a tabela de aderência dos resíduos.
FAIXAS_ADERENCIA = ((1.00, 0.68), (1.64, 0.90), (1.96, 0.95))


def residuos_padronizados(modelo) -> np.ndarray:
    resid = np.asarray(modelo.resid, dtype=float)
    return resid / np.std(resid, ddof=int(modelo.df_model) + 1)


def rodar(modelo, X_sem_const: pd.DataFrame, df: pd.DataFrame, params: dict) -> dict:
    """Bateria completa de pressupostos. Só leitura — não altera o modelo."""
    alfa = float(params.get("alfa_pressupostos", 0.05))
    vif_lim = float(params.get("vif_limite", 10.0))
    corr_lim = float(params.get("correlacao_limite", 0.80))
    sigma_out = float(params.get("outlier_sigma", 2.0))
    dw_lo, dw_hi = params.get("durbin_watson_faixa", [1.5, 2.5])

    resid = np.asarray(modelo.resid, dtype=float)
    resid_pad = residuos_padronizados(modelo)

    ks_stat, ks_p = lilliefors(resid, dist="norm")
    jb_stat, jb_p = jarque_bera(resid)[:2]
    bp_stat, bp_p = het_breuschpagan(resid, modelo.model.exog)[:2]
    try:
        wh_stat, wh_p = het_white(resid, modelo.model.exog)[:2]
    except Exception:  # noqa: BLE001 — White exige gl suficientes; sem eles, não trava
        wh_stat, wh_p = float("nan"), float("nan")
    dw = float(durbin_watson(resid))

    faixas = {}
    for sigma, teorico in FAIXAS_ADERENCIA:
        obs = float(np.mean(np.abs(resid_pad) <= sigma))
        faixas[f"{sigma:.2f}"] = {"observado": obs, "teorico": teorico,
                                  "diferenca": round(obs - teorico, 4)}

    vifs = []
    if X_sem_const.shape[1] > 1:
        Xv = sm.add_constant(X_sem_const, has_constant="add").to_numpy(float)
        for i, nome in enumerate(X_sem_const.columns, start=1):
            vifs.append({"nome": nome, "vif": float(variance_inflation_factor(Xv, i)),
                         "atende": bool(variance_inflation_factor(Xv, i) < vif_lim)})

    corr = X_sem_const.corr().round(4)
    pares_correlacionados = []
    nomes = list(X_sem_const.columns)
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            r = float(corr.loc[a, b]) if not pd.isna(corr.loc[a, b]) else 0.0
            if abs(r) >= corr_lim:
                pares_correlacionados.append({"a": a, "b": b, "r": r})

    outliers = []
    for pos, (idx, rp) in enumerate(zip(df.index, resid_pad)):
        if abs(float(rp)) > sigma_out:
            linha = df.loc[idx]
            outliers.append({
                "indice": int(pos),
                "residuo_padronizado": float(rp),
                "id": str(linha.get("dado_id", linha.get("id", idx))),
            })

    return {
        "normalidade_ks": {"estatistica": float(ks_stat), "p_valor": float(ks_p),
                           "atende": bool(ks_p > alfa)},
        "normalidade_jb": {"estatistica": float(jb_stat), "p_valor": float(jb_p),
                           "atende": bool(jb_p > alfa)},
        "homocedasticidade_bp": {"estatistica": float(bp_stat), "p_valor": float(bp_p),
                                 "atende": bool(bp_p > alfa)},
        "homocedasticidade_white": {
            "estatistica": float(wh_stat), "p_valor": float(wh_p),
            "atende": bool(wh_p > alfa) if wh_p == wh_p else None},  # NaN-safe
        "durbin_watson": {"estatistica": dw, "faixa": [dw_lo, dw_hi],
                          "atende": bool(dw_lo <= dw <= dw_hi)},
        "aderencia_residuos": faixas,
        "vif": vifs,
        "vif_ok": all(v["vif"] < vif_lim for v in vifs) if vifs else True,
        "correlacao": corr.to_dict(),
        "pares_correlacionados": pares_correlacionados,
        "outliers": outliers,
        "residuos_padronizados": [float(v) for v in resid_pad],
    }


def extrapolacoes(esp, df: pd.DataFrame, avaliando: dict) -> list:
    """Característica do avaliando fora do intervalo amostral descaracteriza o Grau III."""
    fora = []
    for r in esp.regressores:
        v = float(avaliando[r.campo])
        lo, hi = float(df[r.campo].min()), float(df[r.campo].max())
        if v < lo or v > hi:
            fora.append({"campo": r.campo, "rotulo": r.nome, "valor": v,
                         "min": lo, "max": hi})
    return fora
