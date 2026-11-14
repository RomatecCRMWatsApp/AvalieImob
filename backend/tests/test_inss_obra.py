# Golden tests contra os exemplos numéricos do Manual do SERO v3.0.
from datetime import date
from decimal import Decimal as D

import pytest

from services.inss_obra import ErroSimulacao, simular
from services.inss_obra import params as P
from services.inss_obra import prazos
from services.inss_obra.motor import competencias, decadencia


def _base(**kw):
    e = {"responsavel": "PF", "uf": "MA", "data_inicio": "2025-01-10",
         "data_fim": "2025-12-10", "data_afericao": "2026-11-14", "usinado": False}
    e.update(kw)
    return e


def test_equivalencia_unifamiliar_p74():
    assert P.equivalencia("residencial_unifamiliar", D(1000)) * 1000 == D(890)
    assert P.equivalencia("residencial_unifamiliar", D(1001)) == D("0.85")
    assert P.equivalencia("comercial_salas_lojas", D(3001)) == D("0.83")


def test_complementares_p80():
    r = simular(_base(responsavel="PJ", vau={"residencial_unifamiliar": "4139.62"}, areas=[
        {"destinacao": "residencial_unifamiliar", "categoria": "obra_nova", "classe": "complementar_descoberta", "area_m2": 40},
        {"destinacao": "residencial_unifamiliar", "categoria": "obra_nova", "classe": "complementar_coberta", "area_m2": 40},
    ]))
    assert D(r["cod_total"]) == D("124188.60")


def test_exemplo_fator_social_p86_87():
    # Demolição de 40 m² + obra nova multifamiliar 100 m² + piscina coberta 50 m².
    vau = "3478.46"  # devolve os COD do Manual: 313.061,40 / 125.224,56 / 86.961,50
    r = simular(_base(vau={"residencial_multifamiliar": vau}, areas=[
        {"destinacao": "residencial_multifamiliar", "categoria": "obra_nova", "classe": "principal", "area_m2": 100},
        {"destinacao": "residencial_multifamiliar", "categoria": "demolicao", "classe": "principal", "area_m2": 40},
        {"destinacao": "residencial_multifamiliar", "categoria": "obra_nova", "classe": "complementar_coberta", "area_m2": 50},
    ]))
    cods = [D(l["cod"]) for l in r["linhas"]]
    assert cods == [D("313061.40"), D("125224.56"), D("86961.50")]
    rmts = [D(l["rmt"]) for l in r["linhas"]]
    assert rmts == [D("25044.91"), D("500.90"), D("6956.92")]
    assert D(r["rmt_total"]) == D("32502.73")
    assert [l["fator_social"] for l in r["linhas"]] == ["0.40", "0.20", "0.40"]


def test_edificio_garagens_p84():
    # RMT = 2.689.908,00 × 20% × 80% = 430.385,28 (PJ, sem fator social)
    r = simular(_base(responsavel="PJ", vau={"edificio_garagens": "2689908"}, areas=[
        {"destinacao": "edificio_garagens", "categoria": "obra_nova", "classe": "complementar_coberta", "area_m2": 2},
    ]))
    assert D(r["linhas"][0]["cod"]) == D("2689908.00")
    assert D(r["rmt_total"]) == D("430385.28")


def test_decadencia_p96():
    d = decadencia(date(2012, 1, 1), date(2016, 12, 31), date(2020, 8, 15))
    assert (d["meses_total"], d["meses_decadentes"], d["meses_nao_decadentes"]) == (60, 36, 24)
    assert d["percentual_nao_decadente"] == D("0.4")


def test_meses_p97():
    assert len(competencias(date(2015, 12, 31), date(2016, 1, 10))) == 2


def test_debito_36_8_p149_e_p97():
    for rmt, total in [("48879.32", "17987.59"), ("292174.40", "107520.18")]:
        base = D(rmt)
        soma = sum((v * base).quantize(D("0.01"), rounding="ROUND_HALF_UP") for _, _, _, v in P.ALIQUOTAS)
        assert soma == D(total)


def test_usinado_p139():
    r = simular(_base(responsavel="PJ", uf="TO", usinado=True,
                      vau={"residencial_multifamiliar": "626122.80"}, areas=[
        {"destinacao": "residencial_multifamiliar", "categoria": "obra_nova", "classe": "complementar_coberta", "area_m2": 2},
    ]))
    assert D(r["usinado"]["credito"]) == D("2241.52")


def test_obra_decadente_zera():
    r = simular(_base(data_inicio="2010-01-01", data_fim="2011-06-30",
                      vau={"residencial_unifamiliar": "2500"}, areas=[
        {"destinacao": "residencial_unifamiliar", "categoria": "obra_nova", "classe": "principal", "area_m2": 120}]))
    assert D(r["total"]) == 0 and r["alertas"]


def test_marca_parametros_a_conferir():
    r = simular(_base(vau={"galpao_industrial": "2000"}, areas=[
        {"destinacao": "galpao_industrial", "categoria": "obra_nova", "classe": "principal", "area_m2": 300}]))
    # p.73 e p.149 conferidos no PDF: nada mais em conferência sem o usinado
    assert r["parametros_a_conferir"] == []
    r2 = simular(_base(usinado=True, vau={"galpao_industrial": "2000"}, areas=[
        {"destinacao": "galpao_industrial", "categoria": "obra_nova", "classe": "principal", "area_m2": 300}]))
    assert r2["parametros_a_conferir"] == []
    from decimal import Decimal as _D
    assert P.USINADO_UF["MG"]["residencial_unifamiliar"] == _D("0.0468")
    assert P.USINADO_UF["PE"]["edificio_garagens"] == _D("0.0947")
    assert [d["codigo_receita"] for d in r["debitos"]][:3] == ["1138-31", "1082-31", "1646-31"]


def test_erros_claros():
    with pytest.raises(ErroSimulacao, match="VAU"):
        simular(_base(vau={}, areas=[{"destinacao": "residencial_unifamiliar", "categoria": "obra_nova",
                                       "classe": "principal", "area_m2": 100}]))
    with pytest.raises(ErroSimulacao, match="anterior"):
        simular(_base(data_inicio="2025-05-01", data_fim="2025-01-01", vau={"residencial_unifamiliar": "1"},
                      areas=[{"destinacao": "residencial_unifamiliar", "categoria": "obra_nova",
                              "classe": "principal", "area_m2": 100}]))


def test_prazos():
    assert prazos.prazo_cno(date(2026, 3, 1)) == date(2026, 3, 31)
    # aferição em 11/2026 → DARF 20/12/2026 é domingo → antecipa p/ sexta 18/12
    assert prazos.vencimento_darf(date(2026, 11, 14)) == date(2026, 12, 18)
