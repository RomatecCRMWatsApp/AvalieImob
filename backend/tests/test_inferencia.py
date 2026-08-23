# @module tests.test_inferencia — suíte de aceite do motor de inferência (MCDDM).
#
# Portada da suíte de referência (test_engine_inferencia.py) para pytest. É
# CRITÉRIO DE MERGE: confere o motor contra o cálculo manual (equações normais,
# R², IP 80% com t de Student) e contra as regras da NBR 14653-2.
import numpy as np
import pytest
from scipy import stats as st

from services.inferencia import (Especificacao, ErroInferencia, Regressor,
                                 TRANSFORMACOES, estimar, serializavel)
from tests.fixtures.amostra_inferencia import AVALIANDO, gerar_amostra


def esp_padrao() -> Especificacao:
    return Especificacao(
        dependente="vu", transf_dependente="ln",
        regressores=[
            Regressor("area", "ln", "quantitativa", "AREA"),
            Regressor("dist_centro", "ln", "quantitativa", "DIST"),
            Regressor("pavimentacao", "identidade", "dicotomica", "PAV"),
            Regressor("esquina", "identidade", "dicotomica", "ESQ"),
        ])


@pytest.fixture(scope="module")
def resultado():
    return estimar(gerar_amostra(), esp_padrao(), AVALIANDO)


# ── 1. Transformações ────────────────────────────────────────────────────────
@pytest.mark.parametrize("nome", list(TRANSFORMACOES))
def test_inversa_de_cada_transformacao(nome):
    t = TRANSFORMACOES[nome]
    x = np.array([2.0, 7.5, 13.25])
    volta = t["inv"](t["f"](x))
    assert np.allclose(x, volta, rtol=1e-12), f"máx erro {np.max(np.abs(x - volta)):.2e}"


# ── 2. OLS conferido contra as equações normais ──────────────────────────────
def test_coeficientes_conferem_com_equacoes_normais(resultado):
    X = resultado["_X"].to_numpy(float)
    y = np.asarray(resultado["_y"], dtype=float)
    beta_manual = np.linalg.solve(X.T @ X, X.T @ y)
    beta_motor = np.array([g["coeficiente"] for g in resultado["regressores"]])
    assert np.allclose(beta_manual, beta_motor, atol=1e-9), \
        f"máx dif {np.max(np.abs(beta_manual - beta_motor)):.3e}"


# ── 3. R² conferido contra 1 - SQres/SQtot ───────────────────────────────────
def test_r2_confere_com_soma_de_quadrados(resultado):
    X = resultado["_X"].to_numpy(float)
    y = np.asarray(resultado["_y"], dtype=float)
    beta = np.linalg.solve(X.T @ X, X.T @ y)
    res = y - X @ beta
    r2_manual = 1 - (res @ res) / ((y - y.mean()) @ (y - y.mean()))
    assert abs(r2_manual - resultado["r2"]) < 1e-12


# ── 4. IP 80% conferido contra o t de Student, na mão ────────────────────────
def test_ip80_confere_com_calculo_manual(resultado):
    X = resultado["_X"].to_numpy(float)
    y = np.asarray(resultado["_y"], dtype=float)
    beta = np.linalg.solve(X.T @ X, X.T @ y)
    res = y - X @ beta
    gl = resultado["graus_liberdade"]
    s2 = (res @ res) / gl
    x0 = np.array([1.0, np.log(AVALIANDO["area"]), np.log(AVALIANDO["dist_centro"]),
                   AVALIANDO["pavimentacao"], AVALIANDO["esquina"]])
    se_pred = np.sqrt(s2 * (1 + x0 @ np.linalg.inv(X.T @ X) @ x0))
    t80 = st.t.ppf(0.90, gl)                      # IP de 80% ⇒ 10% em cada cauda
    centro_t = x0 @ beta
    lo, hi = np.exp(centro_t - t80 * se_pred), np.exp(centro_t + t80 * se_pred)
    assert abs(lo - resultado["predicao"]["ip80"]["inferior"]) < 1e-8
    assert abs(hi - resultado["predicao"]["ip80"]["superior"]) < 1e-8


def test_ic_da_media_e_mais_estreito_que_o_ip(resultado):
    """O Grau de Precisão usa o IP (nova observação), que é sempre mais largo."""
    p = resultado["predicao"]
    assert p["ic80"]["inferior"] > p["ip80"]["inferior"]
    assert p["ic80"]["superior"] < p["ip80"]["superior"]


# ── 5. Micronumerosidade bloqueia ────────────────────────────────────────────
def test_micronumerosidade_bloqueia_a_estimacao():
    with pytest.raises(ErroInferencia) as e:
        estimar(gerar_amostra().head(12), esp_padrao(), AVALIANDO)
    assert "Micronumerosidade" in str(e.value)


# ── 6. Domínio da transformação ──────────────────────────────────────────────
def test_violacao_de_dominio_falha_apontando_o_dado():
    df = gerar_amostra()
    df.loc[df.index[0], "area"] = 0.0
    with pytest.raises(ErroInferencia) as e:
        estimar(df, esp_padrao(), AVALIANDO)
    msg = str(e.value)
    assert "area" in msg and "domínio" in msg
    assert "linha(s) 1" in msg          # aponta o dado, não descarta em silêncio


def test_dado_negativo_em_raiz_tambem_falha():
    df = gerar_amostra()
    df.loc[df.index[3], "area"] = -10.0
    esp = Especificacao("vu", "ln", [Regressor("area", "raiz", "quantitativa", "AREA"),
                                     Regressor("dist_centro", "ln", "quantitativa", "DIST")])
    with pytest.raises(ErroInferencia):
        estimar(df, esp, AVALIANDO)


# ── 7. Extrapolação ──────────────────────────────────────────────────────────
def test_extrapolacao_detectada_e_derruba_o_grau_iii():
    df = gerar_amostra()
    fora = dict(AVALIANDO, area=float(df["area"].max()) + 500)
    r = estimar(df, esp_padrao(), fora)
    assert len(r["extrapolacoes"]) == 1
    assert r["extrapolacoes"][0]["campo"] == "area"
    assert r["enquadramento"]["grau_fundamentacao"] != "III"
    assert any("Extrapolação" in b for b in r["enquadramento"]["bloqueios_grau_iii"])


# ── 8. Amostra suficiente atinge Grau III ────────────────────────────────────
def test_amostra_suficiente_atinge_grau_iii(resultado):
    enq = resultado["enquadramento"]
    assert enq["grau_fundamentacao"] == "III"
    assert enq["grau_precisao"] == "III"
    assert enq["amplitude_ip80"] <= 0.30
    assert resultado["n"] >= 6 * (resultado["k"] + 1)
    assert enq["bloqueios_grau_iii"] == []


# ── 9. Amostra reduzida derruba o grau ───────────────────────────────────────
def test_n_reduzido_cai_de_grau_por_quantidade_de_dados():
    r = estimar(gerar_amostra().head(21), esp_padrao(), AVALIANDO)
    assert r["enquadramento"]["grau_fundamentacao"] != "III"
    assert any("Quantidade mínima" in b for b in r["enquadramento"]["bloqueios_grau_iii"])


# ── 10. Pressupostos ─────────────────────────────────────────────────────────
def test_pressupostos_atendidos_na_amostra_demo(resultado):
    d = resultado["diagnostico"]
    assert d["normalidade_ks"]["atende"], d["normalidade_ks"]
    assert d["homocedasticidade_bp"]["atende"], d["homocedasticidade_bp"]
    assert d["durbin_watson"]["atende"], d["durbin_watson"]
    assert d["vif_ok"], d["vif"]
    assert max(v["vif"] for v in d["vif"]) < 1.5


def test_aderencia_dos_residuos_traz_observado_e_teorico(resultado):
    faixas = resultado["diagnostico"]["aderencia_residuos"]
    assert set(faixas) == {"1.00", "1.64", "1.96"}
    assert faixas["1.96"]["teorico"] == 0.95
    assert 0.0 <= faixas["1.96"]["observado"] <= 1.0


def test_outliers_listados_por_identificador_do_dado():
    df = gerar_amostra()
    df.loc[df.index[5], "vu"] = df["vu"].max() * 2.2      # discrepante forçado
    r = estimar(df, esp_padrao(), AVALIANDO)
    ids = [o["id"] for o in r["diagnostico"]["outliers"]]
    assert "D06" in ids


# ── 11. Descarte de dados ────────────────────────────────────────────────────
def test_descarte_de_dados_reflete_em_n(resultado):
    df = gerar_amostra()
    df.loc[df.index[:3], "utilizado"] = False
    r = estimar(df, esp_padrao(), AVALIANDO)
    assert r["n"] == resultado["n"] - 3


# ── Extras da portagem ───────────────────────────────────────────────────────
def test_significancia_e_bicaudal(resultado):
    """statsmodels devolve p bicaudal — o motor não pode reconverter."""
    from scipy import stats
    gl = resultado["graus_liberdade"]
    for r in resultado["regressores"]:
        esperado = 2 * (1 - stats.t.cdf(abs(r["t"]), gl))
        assert abs(esperado - r["significancia"]) < 1e-9


def test_equacao_por_extenso(resultado):
    eq = resultado["equacao"]
    assert eq.startswith("ln(VU) = ")
    for nome in ("ln(AREA)", "ln(DIST)", "PAV", "ESQ"):
        assert nome in eq


def test_nota_de_destransformacao_quando_dependente_e_log(resultado):
    assert resultado["predicao"]["dependente_transformada"] is True
    assert "mediana" in resultado["predicao"]["observacao_destransformacao"]


def test_dependente_sem_transformacao_nao_traz_nota():
    esp = Especificacao("vu", "identidade", esp_padrao().regressores)
    r = estimar(gerar_amostra(), esp, AVALIANDO)
    assert r["predicao"]["observacao_destransformacao"] is None


def test_valor_total_multiplica_os_limites(resultado):
    r = estimar(gerar_amostra(), esp_padrao(), AVALIANDO, quantidade_total=450)
    tot = r["predicao"]["total"]
    assert abs(tot["valor_central"] - r["predicao"]["valor_central"] * 450) < 1e-6
    assert abs(tot["ip80"]["inferior"] - r["predicao"]["ip80"]["inferior"] * 450) < 1e-6


def test_campo_de_arbitrio_e_15_por_cento(resultado):
    p = resultado["predicao"]
    assert abs(p["campo_arbitrio"]["inferior"] - p["valor_central"] * 0.85) < 1e-9
    assert abs(p["campo_arbitrio"]["superior"] - p["valor_central"] * 1.15) < 1e-9


def test_resultado_serializavel_nao_leva_objetos_internos(resultado):
    limpo = serializavel(resultado)
    assert not any(k.startswith("_") for k in limpo)
    import json
    json.dumps(limpo)          # tem de serializar sem custom encoder


def test_variavel_ausente_na_amostra_falha_claro():
    esp = Especificacao("vu", "ln", [Regressor("nao_existe", "ln", "quantitativa", "X"),
                                     Regressor("area", "ln", "quantitativa", "AREA")])
    with pytest.raises(ErroInferencia) as e:
        estimar(gerar_amostra(), esp, {**AVALIANDO, "nao_existe": 1})
    assert "nao_existe" in str(e.value)


def test_caracteristica_do_avaliando_ausente_falha_claro():
    with pytest.raises(ErroInferencia) as e:
        estimar(gerar_amostra(), esp_padrao(), {"area": 450})
    assert "avaliando" in str(e.value).lower()
