# Testes da Retificação de Área alinhada ao spec §7:
# emolumento FIXO 134,43 (16.22.2), Anotação Técnica selecionável, área-a-apurar,
# e Diligências itemizadas (Secretaria/Cartório/Anuência) como despesa à parte.
import pytest
from services.pricing.retificacao import calcular_retificacao


def _base(**extra):
    d = {"tipo_retificacao": "administrativa", "area_atual_matricula": 1000,
         "area_real_levantada": 1010, "valor_venal": 100000}
    d.update(extra)
    return d


def test_emolumento_fixo_independe_do_valor_venal():
    r1 = calcular_retificacao(_base(valor_venal=100000))["custos"]
    r2 = calcular_retificacao(_base(valor_venal=5_000_000))["custos"]
    emol1 = [i for i in r1["secao_2_taxas"] if "molument" in i["descricao"].lower()][0]
    emol2 = [i for i in r2["secao_2_taxas"] if "molument" in i["descricao"].lower()][0]
    assert emol1["valor"] == 134.43
    assert emol2["valor"] == 134.43
    # total idêntico: o emolumento não escala com o valor venal
    assert r1["secao_5_total"] == r2["secao_5_total"]


def test_anotacao_tecnica_selecionavel():
    # o seletor é honrado: o rótulo da anotação muda conforme o conselho escolhido
    padrao = calcular_retificacao(_base())["custos"]
    trt = calcular_retificacao(_base(anotacao_tecnica="trt_cft"))["custos"]
    rrt = calcular_retificacao(_base(anotacao_tecnica="rrt_cau"))["custos"]
    assert "ART CREA" in padrao["secao_2_taxas"][0]["descricao"]   # default
    assert "TRT CFT" in trt["secao_2_taxas"][0]["descricao"]
    assert "RRT CAU" in rrt["secao_2_taxas"][0]["descricao"]


def test_area_real_a_apurar_nao_exige_area_real():
    # sem levantamento ainda: não deve levantar erro nem exigir area_real
    d = {"tipo_retificacao": "administrativa", "area_atual_matricula": 1000,
         "area_real_a_apurar": True}
    r = calcular_retificacao(d)["custos"]
    assert r["secao_5_total"] > 0
    assert any("apurar" in a.lower() for a in r["avisos"])


def test_area_real_obrigatoria_quando_nao_a_apurar():
    with pytest.raises(ValueError):
        calcular_retificacao({"tipo_retificacao": "administrativa",
                              "area_atual_matricula": 1000, "area_real_levantada": 0})


def test_diligencias_itemizadas_como_despesa_a_parte():
    r = calcular_retificacao(_base(
        dil_secretaria_incluir=True, dil_cartorio_incluir=True, dil_anuencia_incluir=True))["custos"]
    da = r.get("despesas_administrativas")
    assert da is not None
    assert da["valor"] == 600.0                # 150 + 150 + 300 (defaults)
    assert len(da["itens"]) == 3
    # despesa é à parte — NÃO entra no total
    sem = calcular_retificacao(_base())["custos"]
    assert r["secao_5_total"] == sem["secao_5_total"]


def test_diligencias_valores_editaveis():
    r = calcular_retificacao(_base(
        dil_secretaria_incluir=True, dil_secretaria_valor=200,
        dil_anuencia_incluir=True, dil_anuencia_valor=350))["custos"]
    assert r["despesas_administrativas"]["valor"] == 550.0  # 200 + 350 (cartório off)


def test_sem_diligencias_nao_gera_despesa():
    assert "despesas_administrativas" not in calcular_retificacao(_base())["custos"]
