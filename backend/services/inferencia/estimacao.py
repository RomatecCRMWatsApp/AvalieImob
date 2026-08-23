# @module services.inferencia.estimacao — OLS, coeficientes, testes t e F.
#
# PROIBIDO implementar regressão à mão: toda estimação passa por statsmodels.OLS,
# para reprodutibilidade e auditoria contra o software de referência do setor.
import numpy as np
import statsmodels.api as sm

from services.inferencia.transformacoes import ErroInferencia, rotular


def ajustar(y, X):
    """OLS puro. Devolve o RegressionResults do statsmodels."""
    return sm.OLS(np.asarray(y, dtype=float), X).fit()


def tabela_regressores(modelo, X) -> list:
    """Coeficiente, erro-padrão, t e significância BICAUDAL por regressor.

    O statsmodels já devolve `pvalues` bicaudais — não converter (regra do MD).
    """
    saida = []
    for nome in X.columns:
        saida.append({
            "nome": "Intercepto" if nome == "const" else nome,
            "coeficiente": float(modelo.params[nome]),
            "erro_padrao": float(modelo.bse[nome]),
            "t": float(modelo.tvalues[nome]),
            "significancia": float(modelo.pvalues[nome]),
            "eh_intercepto": nome == "const",
        })
    return saida


def estatisticas_modelo(modelo, n: int, k: int) -> dict:
    return {
        "n": int(n),
        "k": int(k),
        "graus_liberdade": int(modelo.df_resid),
        "r2": float(modelo.rsquared),
        "r2_ajustado": float(modelo.rsquared_adj),
        "erro_padrao_estimativa": float(np.sqrt(modelo.mse_resid)),
        "f": float(modelo.fvalue),
        "signif_f": float(modelo.f_pvalue),
    }


def checar_suficiencia(n: int, k: int, fator_min: int = 3) -> None:
    """Micronumerosidade: n >= 3(k+1) é piso ABSOLUTO — abaixo disso, bloqueia."""
    if k == 0:
        raise ErroInferencia("Modelo sem regressores.")
    minimo = fator_min * (k + 1)
    if n < minimo:
        raise ErroInferencia(
            f"Micronumerosidade: {n} dados para {k} regressores. "
            f"Mínimo absoluto = {fator_min}(k+1) = {minimo}.")


def equacao(esp, regressores_out: list) -> str:
    """Equação estimada por extenso, para o laudo."""
    dep = rotular(esp.transf_dependente, esp.dependente.upper())
    partes = []
    for r in regressores_out:
        if r["eh_intercepto"]:
            partes.append(f"{r['coeficiente']:.6f}")
        else:
            sinal = "+" if r["coeficiente"] >= 0 else "-"
            partes.append(f"{sinal} {abs(r['coeficiente']):.6f} * {r['nome']}")
    if not partes:
        return f"{dep} = (sem termos)"
    # Sem intercepto o primeiro termo não deve começar com "+".
    corpo = " ".join(partes)
    if corpo.startswith("+ "):
        corpo = corpo[2:]
    return f"{dep} = {corpo}"
