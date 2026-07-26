# Módulo ONR (SIG-RI) standalone: extração do memorial (prosa) → validação →
# pacote shapefile. O motor (geodesia/schema_onr/geo_export/validacao_onr) é
# reutilizado sem alteração.
import io
import textwrap
import zipfile

from services.onr_sigri import extractor_onr as OX
from services.geo_urbano import geo_export as GX, validacao_onr as V

_MEMORIAL = """MEMORIAL DESCRITIVO
Imóvel: LOTE TESTE ONR
Proprietário(a): FULANO DE TAL / CPF nº: 111.444.777-35
Local: Bairro Centro, Açailândia-MA
Área (ha): 0,0360 ha / 360,00 m²
Perímetro (m): 84,00 m
DESCRIÇÃO DO PERÍMETRO
Inicia-se a descrição deste perímetro no vértice P-01, de coordenadas N 9.458.000,00m e E 223.000,00m; deste, segue confrontando com RUA A, com os seguintes azimutes e distâncias: 90°00'00" e 12,00 m até o vértice P-02, de coordenadas N 9.458.000,00m e E 223.012,00m; deste, segue confrontando com LOTE 02, com os seguintes azimutes e distâncias: 0°00'00" e 30,00 m até o vértice P-03, de coordenadas N 9.458.030,00m e E 223.012,00m; deste, segue confrontando com RUA B, com os seguintes azimutes e distâncias: 270°00'00" e 12,00 m até o vértice P-04, de coordenadas N 9.458.030,00m e E 223.000,00m; deste, segue confrontando com LOTE 04, com os seguintes azimutes e distâncias: 180°00'00" e 30,00 m até o vértice P-01, ponto inicial.
Matrícula nº 9809, CNS: 03.018-9, Folha nº 97, Livro nº 2-BL, da comarca de Açailândia, estado de MA.
45°00', fuso -23, tendo como datum o SIRGAS2000.
"""


def _mk_memorial_pdf(texto):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for para in texto.strip().split("\n"):
        for line in (textwrap.wrap(para, 95) or [""]):
            c.drawString(40, y, line)
            y -= 12
            if y < 40:
                c.showPage()
                y = 800
    c.showPage()
    c.save()
    return buf.getvalue()


def _extraido():
    return OX.parse_memorial_onr(_mk_memorial_pdf(_MEMORIAL))


def test_parse_memorial_onr():
    d = _extraido()
    assert d.get("denominacao_imovel") == "LOTE TESTE ONR"
    assert d.get("municipio") == "Açailândia" and d.get("uf") == "MA"
    assert abs(d.get("area_declarada_m2") - 360.0) < 0.01
    assert abs(d.get("perimetro_m") - 84.0) < 0.01
    assert d.get("fuso") == 23
    assert (d.get("proprietario") or {}).get("nome") == "FULANO DE TAL"
    assert (d.get("proprietario") or {}).get("doc") == "111.444.777-35"
    assert (d.get("matricula") or {}).get("matricula") == "9809"
    verts = d.get("vertices") or []
    assert len(verts) == 4
    # UTM convertido p/ geodésica (Açailândia)
    assert all(v.get("latitude") and v.get("longitude") for v in verts)
    assert -6 < verts[0]["latitude"] < -4 and -48 < verts[0]["longitude"] < -47


def _projeto():
    d = _extraido()
    prop = d.get("proprietario") or {}
    mat = d.get("matricula") or {}
    return {
        "numero": "ONR-2026-0001", "natureza": "georreferenciamento", "tipo_servico": "georreferenciamento",
        "denominacao_imovel": d.get("denominacao_imovel"), "municipio": d.get("municipio"), "uf": d.get("uf"),
        "codigo_ibge": "2100055", "area_declarada_m2": d.get("area_declarada_m2"), "perimetro_m": d.get("perimetro_m"),
        "vertices": d.get("vertices"),
        "matriculas": [{"matricula": mat.get("matricula"), "area_m2": d.get("area_declarada_m2")}],
        "partes": [{"papel": "requerente", "tipo_pessoa": "fisica", "nome": prop.get("nome"), "cpf": prop.get("doc")}],
        "cartorio": {"nome": "Registro de Imóveis de Açailândia", "cns": mat.get("cns")},
        "trt_numero": "TRT-2026-001", "precisao_posicional_m": 0.10,
        "responsavel_tecnico": {"nome": "José Romário", "formacao": "Técnico em Agrimensura", "conselho": "CFT/MA 01209185369"},
    }


def test_validacao_pode_gerar():
    res = V.validar(_projeto())
    assert res["erros"] == [] and res["pode_gerar"] is True
    assert abs(res["area_calculada_m2"] - 360.0) / 360.0 < 0.01   # área geodésica ~360 m²


def test_shapefile_do_memorial():
    data = GX.gerar_shapefile_bytes(_projeto())
    z = zipfile.ZipFile(io.BytesIO(data))
    nomes = z.namelist()
    assert {"cpg", "dbf", "prj", "shp", "shx"} <= {n.rsplit(".", 1)[-1] for n in nomes if "." in n}
    assert "LEIAME.txt" in nomes
    import shapefile
    rd = lambda e: io.BytesIO(z.read(next(n for n in nomes if n.endswith(e))))  # noqa: E731
    r = shapefile.Reader(shp=rd(".shp"), shx=rd(".shx"), dbf=rd(".dbf"))
    rec = dict(zip([f[0] for f in r.fields[1:]], r.record(0)))
    assert rec["TIPO_IMOV"] == "URBANO" and rec["NAT_ATO"] == "GEORREFERENCIAMENTO"
    assert rec["MATRICULA"] == "9809" and rec["PROV_195"] == "SIM"
    for proibido in ("SIGEF", "SNCI", "CCIR", "CAR"):
        assert proibido not in [f[0] for f in r.fields[1:]]
