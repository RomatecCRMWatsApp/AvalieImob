"""Benchmark do motor de inferência contra o fixture SINTÉTICO do kit
"Análise Estatística Avançada" (inference_reference.py, 15/11/2026).

Valores esperados obtidos rodando o núcleo de referência (QR/SVD, sem statsmodels)
sobre os mesmos dados. Dados ARTIFICIAIS — não são avaliação imobiliária.
Também cobre os bloqueios matemáticos (§5 do kit) e os diagnósticos de influência.
"""
import numpy as np
import pandas as pd
import pytest

from services.inferencia.motor import Especificacao, Regressor, estimar
from services.inferencia.transformacoes import ErroInferencia

X = [[-3, -1], [-3, 1], [-1, -1], [-1, 1], [1, -1], [1, 1], [3, -1], [3, 1]]
Y = [85, 85, 91, 99, 105, 105, 111, 119]
TOL = 1e-9


def _amostra(xs=X, ys=Y):
    return pd.DataFrame([{"dado_id": f"D{i+1:02d}", "vu": y, "x1": a, "x2": b}
                         for i, ((a, b), y) in enumerate(zip(xs, ys))])


def _esp():
    return Especificacao(dependente="vu",
                         regressores=[Regressor("x1"), Regressor("x2")])


def _rodar(df=None, aval=None):
    # O fixture tem n=8 e k=2 (< 3(k+1)=9): o piso da norma é contornado só no
    # teste, chamando com fator 1 via params — o objetivo é a matemática, não o grau.
    import services.inferencia.motor as M
    orig = M.carregar_params

    def p(norma):
        d = dict(orig(norma))
        d["micronumerosidade_fator"] = 1
        return d
    M.carregar_params = p
    try:
        return estimar(df if df is not None else _amostra(), _esp(),
                       aval or {"x1": 0, "x2": 0})
    finally:
        M.carregar_params = orig


def test_coeficientes_e_estatisticas_batem_com_a_referencia():
    r = _rodar()
    coef = [x["coeficiente"] for x in r["regressores"]]
    assert np.allclose(coef, [100.0, 5.0, 2.0], atol=TOL)
    ep = [x["erro_padrao"] for x in r["regressores"]]
    assert np.allclose(ep, [0.8944271909999157, 0.4, 0.8944271909999159], atol=TOL)
    t = [x["t"] for x in r["regressores"]]
    assert np.allclose(t, [111.80339887498947, 12.5, 2.236067977499799], atol=1e-7)
    p = [x["significancia"] for x in r["regressores"]]
    assert np.allclose(p, [1.0855670402089337e-09, 5.8133366502196986e-05,
                           0.07558681842161154], rtol=1e-6)
    assert r["r2"] == pytest.approx(0.9699248120300752, abs=TOL)
    assert r["r2_ajustado"] == pytest.approx(0.9578947368421052, abs=TOL)
    assert r["erro_padrao_estimativa"] == pytest.approx(2.5298221281347035, abs=TOL)
    assert r["f"] == pytest.approx(80.625, abs=1e-7)
    assert r["signif_f"] == pytest.approx(0.00015686312976862364, rel=1e-6)
    assert r["graus_liberdade"] == 5


def test_ic_da_media_e_ip_80_separados_e_iguais_a_referencia():
    pr = _rodar()["predicao"]
    assert pr["valor_central"] == pytest.approx(100.0, abs=TOL)
    assert pr["ic80"]["inferior"] == pytest.approx(98.67992917596831, abs=1e-8)
    assert pr["ic80"]["superior"] == pytest.approx(101.32007082403163, abs=1e-8)
    assert pr["ip80"]["inferior"] == pytest.approx(96.03978752790498, abs=1e-8)
    assert pr["ip80"]["superior"] == pytest.approx(103.96021247209497, abs=1e-8)
    # O IP de nova observação é sempre mais largo que o IC da média, no mesmo nível.
    assert (pr["ip80"]["superior"] - pr["ip80"]["inferior"]) > \
           (pr["ic80"]["superior"] - pr["ic80"]["inferior"])


def test_influencia_alavancagem_e_cook_batem_com_a_referencia():
    inf = _rodar()["diagnostico"]["influencia"]
    assert np.allclose([i["alavancagem"] for i in inf],
                       [0.475, 0.475, 0.275, 0.275, 0.275, 0.275, 0.475, 0.475], atol=TOL)
    assert np.allclose([i["cook"] for i in inf],
                       [0.35903250188966523, 0.3590325018896347, 0.10899722552516379,
                        0.10899722552516991, 0.10899722552517305, 0.10899722552516689,
                        0.3590325018896344, 0.35903250188964514], atol=1e-9)
    assert np.allclose([i["residuo_studentizado"] for i in inf],
                       [1.091089451179993, -1.0910894511799465, -0.9284766908852395,
                        0.9284766908852657, 0.928476690885279, -0.9284766908852528,
                        -1.0910894511799463, 1.0910894511799623], atol=1e-9)


def test_permutar_linhas_nao_muda_coeficientes():
    idx = [5, 2, 7, 0, 3, 6, 1, 4]
    r = _rodar(_amostra([X[i] for i in idx], [Y[i] for i in idx]))
    assert np.allclose([x["coeficiente"] for x in r["regressores"]],
                       [100.0, 5.0, 2.0], atol=TOL)


def test_mudar_unidade_reverte_o_coeficiente():
    r = _rodar(_amostra([[a * 1000, b] for a, b in X]), aval={"x1": 0, "x2": 0})
    assert r["regressores"][1]["coeficiente"] == pytest.approx(5.0 / 1000, rel=1e-9)
    assert r["predicao"]["valor_central"] == pytest.approx(100.0, abs=1e-8)


def test_matriz_sem_posto_completo_e_bloqueada():
    df = _amostra()
    df["x3"] = df["x1"] * 2  # redundante
    esp = Especificacao(dependente="vu", regressores=[Regressor("x1"), Regressor("x2"),
                                                     Regressor("x3")])
    df = pd.concat([df] * 2, ignore_index=True)
    with pytest.raises(ErroInferencia, match="posto completo"):
        estimar(df, esp, {"x1": 0, "x2": 0, "x3": 0})


def test_valor_ausente_e_bloqueado_e_nao_vira_zero():
    df = pd.concat([_amostra()] * 2, ignore_index=True)
    df.loc[3, "x2"] = np.nan
    with pytest.raises(ErroInferencia, match="ausente"):
        estimar(df, _esp(), {"x1": 0, "x2": 0})


def test_dependente_constante_e_bloqueada():
    df = pd.concat([_amostra(ys=[100] * 8)] * 2, ignore_index=True)
    with pytest.raises(ErroInferencia, match="constante"):
        estimar(df, _esp(), {"x1": 0, "x2": 0})


def test_enquadramento_sinaliza_parametros_nao_conferidos():
    enq = _rodar()["enquadramento"]
    assert "parametros_conferidos" in enq
