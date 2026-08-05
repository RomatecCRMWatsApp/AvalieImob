# Testes do núcleo geométrico da Demarcação (Pontos & Croqui) — funções PURAS.
# Referências fixas da SPEC-Demarcacao §3/§5/§10:
#   retângulo 9×22 → lados [9,22,9,22], área 198 m² (0,0198 ha), perímetro 62 m.
from services.pricing import demarcacao_geo as G


def _retangulo_9x22():
    """V1(0,0) V2(9,0) V3(9,22) V4(0,22) — lados 9,22,9,22 (UTM metros)."""
    return [
        {"vertice": "P1", "utm_e": 0.0, "utm_n": 0.0},
        {"vertice": "P2", "utm_e": 9.0, "utm_n": 0.0},
        {"vertice": "P3", "utm_e": 9.0, "utm_n": 22.0},
        {"vertice": "P4", "utm_e": 0.0, "utm_n": 22.0},
    ]


def test_distancia_plana():
    assert abs(G.distancia_plana((0.0, 0.0), (9.0, 0.0)) - 9.0) < 1e-6
    assert abs(G.distancia_plana((0.0, 0.0), (3.0, 4.0)) - 5.0) < 1e-6


def test_azimute_normalizado_0_360():
    # atan2(Δe, Δn): Norte=0, Leste=90, Sul=180, Oeste=270
    assert abs(G.azimute((0, 0), (0, 10)) - 0.0) < 1e-6      # Norte
    assert abs(G.azimute((0, 0), (10, 0)) - 90.0) < 1e-6     # Leste
    assert abs(G.azimute((0, 0), (0, -10)) - 180.0) < 1e-6   # Sul
    assert abs(G.azimute((0, 0), (-10, 0)) - 270.0) < 1e-6   # Oeste
    az = G.azimute((0, 0), (-1, -1))
    assert 0.0 <= az < 360.0


def test_retangulo_lados():
    lados = G.calcular_lados(G.normalizar_pontos(_retangulo_9x22()))
    assert [round(l["distancia_m"], 2) for l in lados] == [9.0, 22.0, 9.0, 22.0]
    assert lados[0]["vertice_de"] == "P1" and lados[0]["vertice_para"] == "P2"
    assert lados[-1]["vertice_para"] == "P1"  # fecha no primeiro
    assert lados[0]["ordem"] == 1 and lados[-1]["ordem"] == 4


def test_retangulo_area_perimetro():
    pts = G.normalizar_pontos(_retangulo_9x22())
    assert abs(G.area_gauss(pts) - 198.0) < 0.01
    assert abs(G.perimetro_plano(pts) - 62.0) < 0.01


def test_resumo_geometria():
    r = G.resumo_geometria(_retangulo_9x22())
    assert r["num_vertices"] == 4
    assert abs(r["area_m2"] - 198.0) < 0.01
    assert abs(r["area_ha"] - 0.0198) < 1e-6
    assert abs(r["perimetro_m"] - 62.0) < 0.01


def test_extensao_alinhamento():
    pts = G.normalizar_pontos(_retangulo_9x22())
    # lados 2 e 4 são os de 22 m → extensão 44 m (ordem 1-based)
    assert abs(G.extensao_alinhamento(pts, [2, 4]) - 44.0) < 0.01
    assert abs(G.extensao_alinhamento(pts, [1]) - 9.0) < 0.01
    assert G.extensao_alinhamento(pts, []) == 0.0


def test_normalizar_pontos_aceita_shapes_e_ordena():
    # Aceita {vertice, utm_e, utm_n} (spec) e {de, coord_e, coord_n} (geo_urbano)
    entrada = [
        {"de": "A", "coord_e": 10.0, "coord_n": 20.0, "ordem": 2},
        {"vertice": "B", "utm_e": 30.0, "utm_n": 40.0, "ordem": 1},
    ]
    out = G.normalizar_pontos(entrada)
    assert out[0]["de"] == "B" and out[0]["ordem"] == 1        # ordenado por ordem
    assert out[1]["de"] == "A"
    for p in out:
        assert "coord_e" in p and "coord_n" in p and "de" in p and "ordem" in p


def test_croqui_svg_string():
    svg = G.croqui_svg(_retangulo_9x22())
    assert isinstance(svg, str)
    assert "<svg" in svg.lower()


def test_croqui_svg_vazio_sem_pontos():
    assert G.croqui_svg([{"utm_e": 0, "utm_n": 0}]) == ""


def test_croqui_svg_destaque():
    svg = G.croqui_svg(_retangulo_9x22(), destacar_lados=[2], titulo_destaque="Cerca a ser alinhada")
    assert "(ALINHAR)" in svg
    assert "Cerca a ser alinhada" in svg


def test_normalizar_pontos_latlng_converte_para_utm():
    # Açailândia/MA (fuso 23S) — só lat/lng → deve derivar coord_e/coord_n (UTM SIRGAS 2000)
    entrada = [
        {"vertice": "P1", "lat": -4.9711, "lng": -47.4781},
        {"vertice": "P2", "lat": -4.9712, "lng": -47.4782},
        {"vertice": "P3", "lat": -4.9713, "lng": -47.4780},
    ]
    out = G.normalizar_pontos(entrada)
    assert len(out) == 3
    for p in out:
        assert p["coord_e"] is not None and p["coord_n"] is not None
        assert 100_000 < p["coord_e"] < 1_000_000       # Este UTM plausível
        assert p["coord_n"] > 1_000_000                 # Norte UTM (hemisfério S) plausível
