# Testes do destaque de ALINHAMENTO DE CERCA no croqui (SPEC-Demarcacao §5/§10).
# Lados destacados: dourado #C9A84C, tracejado, cota "(ALINHAR)", base cinza #6e7681,
# título + legenda com a extensão (BR). Sem destacar_lados → saída IDÊNTICA (regressão).
from reportlab.graphics.shapes import Line, Polygon, String, Group

from services.geo_urbano.generators.croqui import croqui_drawing

_GOLD = "c9a84c"
_GRAY = "6e7681"
_GREEN = "0c3320"


def _projeto_retangulo():
    # P1(0,0) P2(9,0) P3(9,22) P4(0,22); distancia_m = lado que começa no vértice
    return {"vertices": [
        {"ordem": 1, "de": "P1", "coord_e": 0.0, "coord_n": 0.0, "distancia_m": 9.0},
        {"ordem": 2, "de": "P2", "coord_e": 9.0, "coord_n": 0.0, "distancia_m": 22.0},
        {"ordem": 3, "de": "P3", "coord_e": 9.0, "coord_n": 22.0, "distancia_m": 9.0},
        {"ordem": 4, "de": "P4", "coord_e": 0.0, "coord_n": 22.0, "distancia_m": 22.0},
    ]}


def _walk(drawing):
    out = []
    def rec(node):
        for c in getattr(node, "contents", []) or []:
            out.append(c)
            if isinstance(c, Group):
                rec(c)
    rec(drawing)
    return out


def _hex(color):
    if color is None:
        return None
    try:
        return color.hexval()[2:].lower()
    except Exception:
        return None


def test_croqui_sem_destaque_regressao():
    d = croqui_drawing(_projeto_retangulo())
    assert d is not None
    shapes = _walk(d)
    # base verde (#0C3320) e NENHUM traço dourado quando não há destaque
    polys = [s for s in shapes if isinstance(s, Polygon)]
    base = polys[0]
    assert _hex(base.strokeColor) == _GREEN
    assert all(_hex(getattr(s, "strokeColor", None)) != _GOLD for s in shapes)
    assert all("(ALINHAR)" not in getattr(s, "text", "") for s in shapes if isinstance(s, String))


def test_croqui_com_destaque_alinhamento():
    d = croqui_drawing(_projeto_retangulo(), destacar_lados=[2],
                       titulo_destaque="Cerca a ser alinhada")
    assert d is not None
    shapes = _walk(d)
    # base rebaixada para cinza
    base = [s for s in shapes if isinstance(s, Polygon)][0]
    assert _hex(base.strokeColor) == _GRAY
    # existe uma linha dourada tracejada (o lado destacado)
    linhas_gold = [s for s in shapes if isinstance(s, Line) and _hex(s.strokeColor) == _GOLD]
    assert linhas_gold, "esperava >=1 lado destacado em dourado"
    assert any(getattr(l, "strokeDashArray", None) for l in linhas_gold)
    assert any(round(getattr(l, "strokeWidth", 0)) >= 3 for l in linhas_gold)
    # cota "(ALINHAR)" e legenda/título com a extensão em BR (22,00 m)
    textos = [s.text for s in shapes if isinstance(s, String)]
    assert any("(ALINHAR)" in t for t in textos)
    assert any("Cerca a ser alinhada" in t for t in textos)
    assert any("22,00" in t for t in textos)
