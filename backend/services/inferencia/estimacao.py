# @module services.inferencia.estimacao — OLS, coeficientes, testes t e F.
#
# PROIBIDO implementar regressão à mão: toda estimação passa por statsmodels.OLS,
# para reprodutibilidade e auditoria contra o software de referência do setor.
import numpy as np
import statsmodels.api as sm

from services.inferencia.transformacoes import ErroInferencia, rotular


# Limite de condicionamento da matriz PADRONIZADA (colunas centradas/escaladas):
# mudar a unidade de uma variável não fabrica falha; colinearidade real, sim.
LIMITE_CONDICIONAMENTO = 1e8


def validar_entrada(y, X) -> dict:
    """Bloqueios matemáticos ANTES de ajustar (kit Análise Avançada §5).

    O statsmodels resolve por pseudo-inversa: com matriz sem posto completo ele
    devolve coeficientes "quaisquer" em silêncio. Aqui isso vira erro explicado.
    Não altera nenhum resultado de entrada válida.
    """
    yv = np.asarray(y, dtype=float)
    Xv = np.asarray(X, dtype=float)
    if not np.all(np.isfinite(yv)):
        raise ErroInferencia("Variável dependente com valor ausente ou não numérico.")
    if not np.all(np.isfinite(Xv)):
        cols = [str(c) for c, ok in zip(getattr(X, "columns", range(Xv.shape[1])),
                                        np.all(np.isfinite(Xv), axis=0)) if not ok]
        raise ErroInferencia("Regressor com valor ausente ou não numérico: " + ", ".join(cols))
    n, p = Xv.shape
    if n <= p:
        raise ErroInferencia(f"Observações insuficientes: {n} dados para {p} parâmetros.")
    if float(np.ptp(yv)) == 0.0:
        raise ErroInferencia("Variável dependente constante — não há o que explicar.")
    # Padroniza as colunas não constantes (a constante é o intercepto).
    Z = Xv.copy()
    for j in range(p):
        col = Z[:, j]
        dp = float(np.sqrt(np.mean((col - col.mean()) ** 2)))
        if dp > 0:
            Z[:, j] = (col - col.mean()) / dp
        elif np.any(col != 0):
            Z[:, j] = col / abs(col[0])
    sv = np.linalg.svd(Z, compute_uv=False)
    corte = sv.max() * max(n, p) * np.finfo(float).eps
    posto = int(np.count_nonzero(sv > corte))
    nomes = [str(c) for c in getattr(X, "columns", range(p))]
    if posto < p:
        raise ErroInferencia(
            f"Matriz sem posto completo ({posto} de {p}): há variáveis redundantes "
            f"(uma é combinação das outras) ou constantes. Revise: {', '.join(nomes)}.")
    cond = float(sv.max() / sv.min())
    if cond > LIMITE_CONDICIONAMENTO:
        raise ErroInferencia(
            f"Matriz numericamente mal condicionada (número de condição {cond:.3g}). "
            "Variáveis quase redundantes — reveja a especificação.")
    return {"posto": posto, "numero_condicao": cond}


def ajustar(y, X):
    """OLS puro. Devolve o RegressionResults do statsmodels."""
    modelo = sm.OLS(np.asarray(y, dtype=float), X).fit()
    if not np.isfinite(modelo.mse_resid) or float(modelo.mse_resid) <= 0:
        raise ErroInferencia("Ajuste perfeito (variância residual nula) — estatísticas "
                             "t, F e intervalos não são identificáveis.")
    return modelo


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
        "metodo_ajuste": "OLS (statsmodels) com verificação prévia de posto e condicionamento",
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
