# Testes do suporte a GPX no parser de coletora (importar_coordenadas).
# GPX = XML com <wpt>/<rtept>/<trkpt> (atributos lat/lon). Açailândia/MA (fuso 23S).
from services.geo_urbano.georref_urbano import importar_coordenadas

_WPT = """<?xml version="1.0"?>
<gpx version="1.1" creator="Test">
  <wpt lat="-4.9711" lon="-47.4781"><name>P1</name></wpt>
  <wpt lat="-4.9712" lon="-47.4782"><name>P2</name></wpt>
  <wpt lat="-4.9713" lon="-47.4780"><name>P3</name></wpt>
</gpx>"""

_TRK = """<?xml version="1.0"?>
<gpx version="1.1"><trk><trkseg>
  <trkpt lat="-4.9711" lon="-47.4781"/>
  <trkpt lat="-4.9712" lon="-47.4782"/>
  <trkpt lat="-4.9713" lon="-47.4780"/>
</trkseg></trk></gpx>"""


def test_gpx_waypoints_com_nome():
    r = importar_coordenadas(_WPT.encode("utf-8"), "pontos.gpx")
    assert r["sistema"] == "geo"
    vs = r["vertices"]
    assert len(vs) == 3
    assert [v["de"] for v in vs] == ["P1", "P2", "P3"]
    for v in vs:
        assert 100_000 < v["coord_e"] < 1_000_000   # Este UTM plausível
        assert v["coord_n"] > 1_000_000             # Norte UTM (hemisfério S)


def test_gpx_trackpoints():
    r = importar_coordenadas(_TRK.encode("utf-8"), "trilha.gpx")
    assert len(r["vertices"]) == 3
    assert all(v.get("coord_e") is not None for v in r["vertices"])


def test_gpx_prioriza_waypoints_sobre_trackpoints():
    gpx = ("<gpx>"
           '<wpt lat="-4.9711" lon="-47.4781"><name>A</name></wpt>'
           '<wpt lat="-4.9712" lon="-47.4782"><name>B</name></wpt>'
           '<wpt lat="-4.9713" lon="-47.4780"><name>C</name></wpt>'
           "<trk><trkseg>"
           '<trkpt lat="-4.9700" lon="-47.4700"/>'
           '<trkpt lat="-4.9701" lon="-47.4701"/>'
           "</trkseg></trk></gpx>")
    vs = importar_coordenadas(gpx.encode("utf-8"), "x.gpx")["vertices"]
    assert len(vs) == 3
    assert [v["de"] for v in vs] == ["A", "B", "C"]


def test_gpx_fecha_anel_remove_duplicado():
    gpx = ("<gpx>"
           '<wpt lat="-4.9711" lon="-47.4781"><name>P1</name></wpt>'
           '<wpt lat="-4.9712" lon="-47.4782"><name>P2</name></wpt>'
           '<wpt lat="-4.9713" lon="-47.4780"><name>P3</name></wpt>'
           '<wpt lat="-4.9711" lon="-47.4781"><name>P1</name></wpt>'
           "</gpx>")
    assert len(importar_coordenadas(gpx.encode("utf-8"), "anel.gpx")["vertices"]) == 3


def test_gpx_detecta_por_conteudo_sem_extensao():
    # sem extensão .gpx → detecta pelo conteúdo (<gpx>/<trkpt>) e NÃO trata como CSV
    r = importar_coordenadas(_TRK.encode("utf-8"), "")
    assert len(r["vertices"]) == 3
    assert r["sistema"] == "geo"
