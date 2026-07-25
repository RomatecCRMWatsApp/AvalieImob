# Testes do SIG-RI/ONR urbano (Prov. CNJ 195/2025 · NBR 17047:2022):
# motor geodésico (área/perímetro GRS80, fuso/MC/UTM↔geo) e pacote shapefile
# com esquema URBANO (schema_onr) + .cpg + LEIAME.txt.
import io
import zipfile

import pytest

from services.geo_urbano import geodesia as GEO
from services.geo_urbano import geo_export as GX
from services.geo_urbano import schema_onr as SCH


def _quadra_utm(largura=12.0, profundidade=30.0, e0=223000.0, n0=9458000.0):
    """Retângulo largura×profundidade (m) em UTM 23S SIRGAS2000 (Açailândia/MA)."""
    cantos = [(e0, n0), (e0 + largura, n0), (e0 + largura, n0 + profundidade), (e0, n0 + profundidade)]
    return [{"ordem": i, "de": f"P-{i+1:02d}", "coord_e": e, "coord_n": n}
            for i, (e, n) in enumerate(cantos)]


def _projeto_onr(**over):
    p = {
        "id": "urb-onr-1", "numero": "URB-2026-0009", "tipo_servico": "remembramento",
        "denominacao_imovel": "Lote 09, Quadra 06 — Jardim Glória",
        "municipio": "Açailândia", "uf": "MA", "codigo_ibge": "2100055",
        "bairro": "Jardim Glória", "loteamento": "Jardim Glória", "quadra": "06",
        "lote_resultante": "09", "endereco": "Rua das Palmeiras", "cib": "1.234.567-8",
        "inscricao_municipal": "01.02.041.0009", "precisao_posicional_m": 0.10,
        "cartorio": {"nome": "Ofício Único da Comarca de Açailândia – MA", "cns": "12.345-6"},
        "matriculas": [{"matricula": "34.161"}, {"matricula": "34.162"}],
        "partes": [{"papel": "requerente", "tipo_pessoa": "juridica",
                    "razao_social": "J & G Empreendimentos Ltda", "cnpj": "28.804.226/0001-64"}],
        "vertices": _quadra_utm(),
        "responsavel_tecnico": {"nome": "José Romário Pinto Bezerra",
                                "formacao": "Técnico em Agrimensura", "conselho": "CFT/MA 01209185369"},
        "trt_numero": "TRT-2026-000123",
    }
    p.update(over)
    return p


# ── Motor geodésico ───────────────────────────────────────────────────────────
def test_fuso_mc_epsg():
    assert GEO.fuso_de_longitude(-47.46) == 23
    assert GEO.mc_de_fuso(23) == -45
    assert GEO.epsg_utm(23, "S") == 31983     # SIRGAS 2000 / UTM 23S
    assert GEO.epsg_utm(22, "N") == 31976


def test_utm_ida_e_volta():
    lon, lat = GEO.utm_para_geo(223000.0, 9458000.0, 23, "S")
    assert -48 < lon < -47 and -6 < lat < -4      # Açailândia/MA
    e, n, fuso, hemis = GEO.geo_para_utm(lon, lat)
    assert fuso == 23 and hemis == "S"
    assert abs(e - 223000.0) < 0.01 and abs(n - 9458000.0) < 0.01


def test_area_perimetro_geodesico_quadra_12x30():
    ring, fuso, hemis = GEO.resolver_anel(_quadra_utm(), fuso=23, hemisferio="S")
    assert fuso == 23 and hemis == "S" and len(ring) >= 4
    area, perim = GEO.area_perimetro_geodesico(ring)
    # 12×30 = 360 m² e perímetro 2×(12+30)=84 m — geodésico difere <1% do grid
    assert abs(area - 360.0) / 360.0 < 0.01
    assert abs(perim - 84.0) / 84.0 < 0.01


def test_resolver_anel_de_lat_long_dms():
    verts = [
        {"ordem": 0, "latitude": "04°56'15,000\"S", "longitude": "47°27'59,000\"W"},
        {"ordem": 1, "latitude": "04°56'15,000\"S", "longitude": "47°27'58,600\"W"},
        {"ordem": 2, "latitude": "04°56'14,600\"S", "longitude": "47°27'58,600\"W"},
    ]
    ring, fuso, hemis = GEO.resolver_anel(verts)
    assert fuso == 23 and hemis == "S"        # inferido do centroide
    assert ring[0] == ring[-1] and len(ring) == 4


# ── Esquema / pacote SIG-RI urbano ────────────────────────────────────────────
def test_montar_registro_campos_urbanos():
    rec = SCH.montar_registro(_projeto_onr(), rotulo="09", area_m2=360.0,
                              perimetro_m=84.0, n_vertices=4, fuso=23, hemisferio="S")
    assert rec["TIPO_IMOV"] == "URBANO"
    assert rec["NAT_ATO"] == "REMEMBRAMENTO"
    assert rec["MATRICULA"] == "34.161;34.162"
    assert rec["COD_IBGE"] == "2100055"
    assert rec["MC"] == -45 and rec["FUSO"] == 23 and rec["HEMISF"] == "S"
    assert rec["CONSELHO"] == "CFT" and "01209185369" in rec["REG_PROF"]
    assert rec["COMARCA"] == "Açailândia"
    assert rec["PROV_195"] == "SIM" and rec["NORMA_TEC"] == "ABNT NBR 17047:2022"
    assert abs(rec["AREA_HA"] - 0.036) < 1e-6


def test_nat_ato_reurb_modalidade():
    assert SCH.montar_registro(_projeto_onr(tipo_servico="reurb", reurb_modalidade="reurb_s"),
                               fuso=23)["NAT_ATO"] == "REURB-S"
    assert SCH.montar_registro(_projeto_onr(tipo_servico="reurb", reurb_modalidade="reurb_e"),
                               fuso=23)["NAT_ATO"] == "REURB-E"


def test_pacote_shapefile_onr_reabre_e_valida():
    import shapefile  # pyshp
    data = GX.gerar_shapefile_bytes(_projeto_onr())
    z = zipfile.ZipFile(io.BytesIO(data))
    nomes = z.namelist()

    # .cpg = UTF-8, .prj = SIRGAS 2000, LEIAME presente e coerente
    cpg = z.read(next(n for n in nomes if n.endswith(".cpg"))).decode().strip()
    assert cpg.upper() == "UTF-8"
    prj = z.read(next(n for n in nomes if n.endswith(".prj"))).decode()
    assert "SIRGAS" in prj.upper()
    leiame = z.read("LEIAME.txt").decode("utf-8")
    assert "URBANO" in leiame and "SIRGAS 2000" in leiame and "17047" in leiame
    assert "SIGEF" in leiame  # a nota que diz que NÃO se aplicam campos rurais

    # reabre o shapefile (pyshp) a partir dos bytes
    shp = io.BytesIO(z.read(next(n for n in nomes if n.endswith(".shp"))))
    shx = io.BytesIO(z.read(next(n for n in nomes if n.endswith(".shx"))))
    dbf = io.BytesIO(z.read(next(n for n in nomes if n.endswith(".dbf"))))
    r = shapefile.Reader(shp=shp, shx=shx, dbf=dbf)
    campos = [f[0] for f in r.fields[1:]]  # pula o DeletionFlag

    for obrig in ("ID_IMOVEL", "TIPO_IMOV", "NAT_ATO", "COD_IBGE", "AREA_M2", "AREA_HA",
                  "PERIMETRO", "N_VERTICES", "RESP_TEC", "ART_TRT", "PROV_195"):
        assert obrig in campos, f"campo {obrig} ausente"
    # imóvel URBANO: NÃO existem campos rurais
    for proibido in ("COD_SIGEF", "SIGEF", "SNCI", "CCIR", "NIRF", "CAR", "MOD_FISCAL"):
        assert proibido not in campos, f"campo rural {proibido} não deveria existir no DBF urbano"

    assert r.numRecords == 1
    d = dict(zip(campos, r.record(0)))
    assert d["TIPO_IMOV"] == "URBANO"
    assert d["NAT_ATO"] == "REMEMBRAMENTO"
    assert d["PROV_195"] == "SIM"
    assert abs(float(d["AREA_M2"]) - 360.0) / 360.0 < 0.01   # área GEODÉSICA


def test_shapefile_sem_vertices_falha():
    with pytest.raises(ValueError):
        GX.gerar_shapefile_bytes(_projeto_onr(vertices=[]))
