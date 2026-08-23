# @module services.inferencia.motor — orquestra estimação, diagnóstico, predição e enquadramento.
#
# Portado de engine_inferencia_referencia.py, preservando a ASSINATURA
# `estimar(amostra, esp, avaliando, norma)` e as chaves de saída — a suíte de
# aceite (tests/test_inferencia.py) compara contra o cálculo manual.
#
# Não depende de FastAPI nem de MongoDB: entra DataFrame/dataclass, sai dict.
from typing import Optional

import pandas as pd

from services.inferencia import diagnostico as DIAG
from services.inferencia import estimacao as EST
from services.inferencia import predicao as PRED
from services.inferencia.design_matrix import (Especificacao, Regressor,  # noqa: F401
                                               filtrar_utilizados, linha_avaliando,
                                               montar, validar_avaliando)
from services.inferencia.enquadramento import carregar_params, enquadrar
from services.inferencia.transformacoes import (TRANSFORMACOES,  # noqa: F401
                                                ErroInferencia)


def estimar(amostra: pd.DataFrame, esp: Especificacao, avaliando: dict,
            norma: str = "14653-2", quantidade_total: Optional[float] = None) -> dict:
    """Estima o modelo, roda o diagnóstico, prediz o ponto e enquadra na norma.

    `quantidade_total` (opcional): área do avaliando, para o valor TOTAL além do unitário.
    """
    params = carregar_params(norma)

    df = filtrar_utilizados(amostra)
    n, k = len(df), len(esp.regressores)
    EST.checar_suficiencia(n, k, int(params.get("micronumerosidade_fator", 3)))
    validar_avaliando(esp, avaliando)   # falha cedo, antes de estimar

    y, X, X_sem_const = montar(df, esp)
    modelo = EST.ajustar(y, X)

    regressores_out = EST.tabela_regressores(modelo, X)
    diag = DIAG.rodar(modelo, X_sem_const, df, params)
    extrap = DIAG.extrapolacoes(esp, df, avaliando)

    Xp = linha_avaliando(esp, avaliando, X.columns)
    predicao = PRED.predizer(modelo, Xp, esp, params)
    if quantidade_total:
        predicao["total"] = PRED.totalizar(predicao, quantidade_total)

    enq = enquadrar(n, k, modelo.f_pvalue, regressores_out,
                    predicao["amplitude_ip80"], extrap, params)

    return {
        **EST.estatisticas_modelo(modelo, n, k),
        "norma": norma,
        "regressores": regressores_out,
        "diagnostico": diag,
        "extrapolacoes": extrap,
        "predicao": predicao,
        "enquadramento": enq,
        "equacao": EST.equacao(esp, regressores_out),
        "especificacao": esp.to_dict(),
        "avaliando": dict(avaliando or {}),
        # Objetos internos — usados pelos gráficos; NÃO serializar no Mongo.
        "_modelo": modelo,
        "_resid_pad": diag["residuos_padronizados"],
        "_fitted": modelo.fittedvalues,
        "_y": y,
        "_X": X,
        "_df": df,
    }


def serializavel(resultado: dict) -> dict:
    """Remove os objetos internos (statsmodels/pandas) antes de gravar no Mongo."""
    return {k: v for k, v in (resultado or {}).items() if not k.startswith("_")}
