"""INSS da obra na proposta de averbação — mesmo motor do módulo INSS de Obra (Manual do SERO)."""
from decimal import Decimal

from services.inss_obra import simular
from services.pricing.averbacao import calcular_averbacao


def _inss(res):
    item = next(i for i in res["custos"]["secao_2_taxas"] if i["descricao"].startswith("INSS da obra"))
    return Decimal(str(item["valor"]))


BASE = {"modalidade": "residencial", "area_construida": 150, "valor_venal_imovel": 300000,
        "padrao_construtivo": "normal", "responsavel": "PF", "uf": "MA",
        "data_inicio_obra": "2026-01-10", "data_fim_obra": "2026-06-20"}


def test_vau_informado_bate_com_o_motor():
    dados = {**BASE, "vau_m2": 2500, "area_complementar_descoberta": 30}
    res = calcular_averbacao(dados)
    assert _inss(res) == Decimal("10377.60")
    # memória de cálculo acompanha a proposta
    base = res["custos"]["base_calculo"]
    assert base and "TOTAL" in base[-1]["rotulo"].upper()


def test_sem_vau_estima_pelo_cub_e_avisa():
    res = calcular_averbacao(dict(BASE))
    assert _inss(res) > 0
    assert "CUB" in " ".join(res["custos"].get("avisos") or []).upper() or res["fontes"].get("cub")


def test_pj_com_contabilidade_nao_cobra_inss():
    res = calcular_averbacao({**BASE, "responsavel": "PJ_com_contabilidade", "vau_m2": 2500})
    assert _inss(res) == 0


def test_usa_simulacao_vinculada_do_modulo():
    sim = simular({"responsavel": "PF", "uf": "MA", "vau": {"residencial_unifamiliar": "2000"},
                   "data_inicio": "2026-01-01", "data_fim": "2026-05-01", "data_afericao": "2026-06-01",
                   "areas": [{"destinacao": "residencial_unifamiliar", "categoria": "obra_nova",
                              "tipo": "alvenaria", "classe": "principal", "area_m2": "90"}]})
    res = calcular_averbacao({**BASE, "vau_m2": 2500,
                              "_inss_obra_sim": {"numero": "INSS-2026-0001", "resultado": sim}})
    assert _inss(res) == Decimal(sim["total"])
    assert res["fontes"]["sero"]["origem"] == "inss_obra"


# ── Projeto executivo: INSS como estimativa à parte (não soma no total) ──────
from services.pricing.projeto_executivo import calcular_projeto_executivo


def test_projeto_executivo_mostra_inss_fora_do_total():
    sem = calcular_projeto_executivo({"area_construir": 150, "inss_estimar": False})["custos"]
    com = calcular_projeto_executivo({"area_construir": 150, "vau_m2": 2500,
                                      "area_complementar_descoberta": 30})["custos"]
    assert sem["inss_obra_estimativa"] is None
    assert Decimal(str(com["inss_obra_estimativa"]["total"])) == Decimal("10377.60")
    assert com["secao_5_total"] == sem["secao_5_total"]  # INSS não entra no total
    assert com["inss_memoria"][-1]["rotulo"].startswith("TOTAL")


def test_projeto_executivo_usa_simulacao_vinculada():
    sim = simular({"responsavel": "PF", "uf": "MA", "vau": {"residencial_unifamiliar": "2000"},
                   "data_inicio": "2026-01-01", "data_fim": "2026-05-01", "data_afericao": "2026-06-01",
                   "areas": [{"destinacao": "residencial_unifamiliar", "categoria": "obra_nova",
                              "tipo": "alvenaria", "classe": "principal", "area_m2": "90"}]})
    c = calcular_projeto_executivo({"area_construir": 150,
                                    "_inss_obra_sim": {"numero": "INSS-2026-0001", "resultado": sim}})["custos"]
    assert Decimal(str(c["inss_obra_estimativa"]["total"])) == Decimal(sim["total"])
    assert c["inss_obra_estimativa"]["origem"] == "inss_obra"
