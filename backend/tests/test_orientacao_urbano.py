# Testes da orientação de lote urbano (frente/laterais/fundo) + descrição por extenso.
from utils.extenso import area_extenso, distancia_extenso, _inteiro_extenso as ie
from services.geo_urbano.orientacao import classificar_lados, aplicar_lados
from services.geo_urbano.generators import textos as TX


def _retangulo(confr_frente="Rua A"):
    """Lote 20×10: V1(0,0) V2(20,0) V3(20,10) V4(0,10); frente = aresta sul (rua)."""
    return [
        {"ordem": 1, "de": "V1", "para": "V2", "coord_e": 0.0, "coord_n": 0.0,
         "distancia_m": 20.0, "azimute": "90°00'00\"", "confrontante_lado": confr_frente},
        {"ordem": 2, "de": "V2", "para": "V3", "coord_e": 20.0, "coord_n": 0.0,
         "distancia_m": 10.0, "azimute": "0°00'00\"", "confrontante_lado": "Vizinho B"},
        {"ordem": 3, "de": "V3", "para": "V4", "coord_e": 20.0, "coord_n": 10.0,
         "distancia_m": 20.0, "azimute": "270°00'00\"", "confrontante_lado": "Vizinho C"},
        {"ordem": 4, "de": "V4", "para": "V1", "coord_e": 0.0, "coord_n": 10.0,
         "distancia_m": 10.0, "azimute": "180°00'00\"", "confrontante_lado": "Vizinho D"},
    ]


def test_extenso_area_distancia():
    assert ie(1106) == "mil cento e seis"
    assert area_extenso(1106.00) == "mil cento e seis metros quadrados"
    assert area_extenso(1.00) == "um metro quadrado"
    assert distancia_extenso(22.89) == "vinte e dois metros e oitenta e nove centímetros"
    assert distancia_extenso(143.20) == "cento e quarenta e três metros e vinte centímetros"
    assert distancia_extenso(100.00) == "cem metros"


def test_classifica_com_rua_na_frente():
    out = classificar_lados(_retangulo())
    assert out["frente_indefinida"] is False
    assert out["lados"] == ["frente", "lateral_esquerda", "fundo", "lateral_direita"]


def test_frente_indefinida_sem_rua():
    verts = _retangulo(confr_frente="Vizinho A")  # nenhum confrontante é logradouro
    out = classificar_lados(verts)
    assert out["frente_indefinida"] is True
    assert all(l is None for l in out["lados"])


def test_frente_idx_forcado():
    verts = _retangulo(confr_frente="Vizinho A")
    out = classificar_lados(verts, frente_idx=0)  # marca a aresta sul como frente
    assert out["frente_indefinida"] is False
    assert out["lados"][0] == "frente"
    assert "fundo" in out["lados"]
    assert "lateral_direita" in out["lados"] and "lateral_esquerda" in out["lados"]


def test_override_manual_tem_prioridade():
    verts = _retangulo()
    verts[1]["lado_manual"] = "fundo"      # força a aresta leste como fundo
    out = classificar_lados(verts)
    assert out["lados"][1] == "fundo"


def test_rodovia_conta_como_frente():
    # Caso Lindaura: confrontantes vizinhos + "ROD BR-010" na frente.
    verts = _retangulo(confr_frente="ROD BR-010 KM 1418 — Sr. Ilzom")
    out = classificar_lados(verts)
    assert out["lados"][0] == "frente"
    assert out["frente_indefinida"] is False


def test_descricao_perimetrica_com_lado_e_extenso():
    proj = {"vertices": _retangulo()}
    txt = TX.descricao_perimetrica(proj)
    assert "Inicia-se a descrição no vértice V1" in txt
    assert "segue pela FRENTE" in txt
    assert "pelos FUNDOS" in txt
    assert "(vinte metros)" in txt         # distância de 20,00 m por extenso
    assert "fechando o polígono." in txt


def test_descricao_sem_frente_nao_inventa_lado():
    proj = {"vertices": _retangulo(confr_frente="Vizinho A")}
    txt = TX.descricao_perimetrica(proj)
    assert "segue pela" not in txt and "pelos FUNDOS" not in txt
    assert "deste, segue, com azimute" in txt   # sem rótulo de lado
    assert "(vinte metros)" in txt              # extenso continua


def test_aplicar_lados_escreve_no_vertice():
    proj = {"vertices": _retangulo()}
    cls = aplicar_lados(proj)
    assert cls["frente_indefinida"] is False
    lados = [v["lado"] for v in sorted(proj["vertices"], key=lambda v: v["ordem"])]
    assert lados == ["frente", "lateral_esquerda", "fundo", "lateral_direita"]


def test_m2_ext_metros_ext():
    assert TX.m2_ext(1106.0) == "1.106,00 m² (mil cento e seis metros quadrados)"
    assert TX.metros_ext(143.20) == "143,20 m (cento e quarenta e três metros e vinte centímetros)"
