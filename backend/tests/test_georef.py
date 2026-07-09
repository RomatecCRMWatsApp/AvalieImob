# Testes do módulo Topografia & Geo — extração SIGEF/CCIR, geometria, shapefile, geradores.
import io
import zipfile

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

from models.georef import GeorefProjeto, calcular_completude
from services.georef import extractor as EX
from services.georef import geo as GEO
from services.georef.generators import textos as TX
from services.georef.generators import pdf as PDF
from services.georef.generators import docx as DOCX
from services.georef.generators import dossie as DOSSIE


# ──────────────────────────────────────────────────────────────────────────────
# PDFs sintéticos (espelham o layout SIGEF/INCRA real, em texto)
# ──────────────────────────────────────────────────────────────────────────────
_MEMORIAL_LINHAS = [
    "MEMORIAL DESCRITIVO",
    "Denominação: Fazenda Santa Maria",
    "Proprietário(a): José Romário Pinto Bezerra",
    "CPF: 012.091.853-69",
    "Matrícula do imóvel: 1234",
    "Natureza da Área: Particular",
    "Código INCRA/SNCR: 9510990828483",
    "Responsável Técnico(a): José Romário Pinto Bezerra",
    "Formação: Técnico Industrial em Agrimensura",
    "Código de credenciamento: FQNS",
    "Conselho Profissional: CFT/MA",
    "Documento de RT: CFT2605953795-MA",
    "Sistema Geodésico de referência: SIRGAS 2000",
    "Área (Sistema Geodésico Local): 30,8600 ha",
    "Perímetro (m): 2221,00",
    "Município/UF: São Francisco do Maranhão - MA",
    "Cartório (CNS): (03.169-0) São Francisco do Maranhão - MA",
    "CERTIFICAÇÃO: ABC123XYZ",
    "DESCRIÇÃO DA PARCELA",
    "Código Longitude Latitude Altitude Vante Azimute Dist Confrontações",
    "FQNS-M-A016 -47°15'36,000\" -5°11'24,000\" 280,50 FQNS-M-A017 90°00' 554,40 "
    "Mat.338 | Nome: João da Silva CPF: 111.111.111-11",
    "FQNS-M-A017 -47°15'18,000\" -5°11'24,000\" 281,00 FQNS-M-A018 0°00' 556,60 "
    "Mat.11434 | Nome: Fazenda Santa Maria Parcela 02",
    "FQNS-M-A018 -47°15'18,000\" -5°11'06,000\" 281,50 FQNS-M-A019 270°00' 554,40 "
    "Mat.0 | ESTRADA VICINAL",
    "FQNS-M-A019 -47°15'36,000\" -5°11'06,000\" 282,00 FQNS-M-A016 180°00' 556,60 "
    "Mat.504 | Nome: Sirvaldo Silva Machado CPF: 222.222.222-22",
]

_CCIR_LINHAS = [
    "CERTIFICADO DE CADASTRO DE IMÓVEL RURAL - CCIR",
    "123.456.789.012-3",
    "DENOMINAÇÃO DO IMÓVEL RURAL",
    "Fazenda Santa Maria",
    "ÁREA TOTAL (ha) 96,8180",
    "CLASSIFICAÇÃO FUNDIÁRIA Pequena Propriedade DATA 01/01/2026",
    "MÓDULO FISCAL (ha) 70,00",
    "FRAÇÃO MÍNIMA DE PARCELAMENTO (ha) 2,00",
    "MUNICÍPIO SEDE DO IMÓVEL RURAL",
    "São Francisco do Maranhão UF MA",
]


def _pdf_de_linhas(linhas) -> bytes:
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 60
    for ln in linhas:
        c.setFont("Helvetica", 8)
        c.drawString(40, y, ln)
        y -= 16
        if y < 60:
            c.showPage()
            y = h - 60
    c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture(scope="module")
def memorial_pdf():
    return _pdf_de_linhas(_MEMORIAL_LINHAS)


@pytest.fixture(scope="module")
def ccir_pdf():
    return _pdf_de_linhas(_CCIR_LINHAS)


@pytest.fixture(scope="module")
def projeto(memorial_pdf):
    res = EX.parse_memorial(memorial_pdf)
    conf = EX.agrupar_confrontantes(res["vertices"], matricula_imovel="1234")
    return {
        "id": "t1", "user_id": "u1", "nome_projeto": "Fazenda Santa Maria",
        "tipo_servico": "georreferenciamento", "tema_pdf": "prime_i",
        "imovel": res["imovel"],
        "responsavel_tecnico": {**GeorefProjeto().responsavel_tecnico.model_dump(),
                                **res["responsavel_tecnico"]},
        "vertices": res["vertices"], "confrontantes": conf,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Conversão de coordenadas
# ──────────────────────────────────────────────────────────────────────────────
def test_dms_to_decimal():
    assert EX.dms_to_decimal("-47°15'36,000\"") == pytest.approx(-47.26, abs=1e-4)
    assert EX.dms_to_decimal("-5°11'24,000\"") == pytest.approx(-5.19, abs=1e-4)
    assert EX.dms_to_decimal("") == 0.0


def test_num_br():
    assert EX._num("4.095,92") == pytest.approx(4095.92)
    assert EX._num("96,8180") == pytest.approx(96.818)
    assert EX._num("") is None


# ──────────────────────────────────────────────────────────────────────────────
# Parser do Memorial
# ──────────────────────────────────────────────────────────────────────────────
def test_parse_memorial_cabecalho(projeto):
    im = projeto["imovel"]
    assert im["denominacao"] == "Fazenda Santa Maria"
    assert im["proprietario_cpf_cnpj"] == "012.091.853-69"
    assert im["matricula"] == "1234"
    assert im["cod_incra"] == "9510990828483"
    assert im["municipio"] == "São Francisco do Maranhão"
    assert im["uf"] == "MA"
    assert im["cartorio_cns"] == "03.169-0"
    assert im["area_ha"] == pytest.approx(30.86, abs=0.01)
    assert im["perimetro_m"] == pytest.approx(2221.0, abs=0.01)
    assert im["certificacao_sigef"] == "ABC123XYZ"


def test_parse_memorial_rt(projeto):
    rt = projeto["responsavel_tecnico"]
    assert rt["credenciamento_incra"] == "FQNS"
    assert rt["conselho"] == "CFT/MA"
    assert rt["art_trt"] == "CFT2605953795-MA"


def test_parse_memorial_vertices(projeto):
    v = projeto["vertices"]
    assert len(v) == 4
    a016 = v[0]
    assert a016["codigo"] == "FQNS-M-A016"
    assert a016["tipo"] == "M"
    assert a016["longitude"] == pytest.approx(-47.26, abs=1e-4)
    assert a016["latitude"] == pytest.approx(-5.19, abs=1e-4)
    assert a016["vante_codigo"] == "FQNS-M-A017"
    assert a016["distancia"] == pytest.approx(554.40)


# ──────────────────────────────────────────────────────────────────────────────
# Agrupamento de confrontantes (DRL)
# ──────────────────────────────────────────────────────────────────────────────
def test_agrupar_confrontantes(projeto):
    conf = projeto["confrontantes"]
    assert len(conf) == 4
    tipos = {c.get("tipo") for c in conf}
    assert "via_publica" in tipos       # ESTRADA VICINAL (Mat.0)
    assert "particular" in tipos
    via = next(c for c in conf if c["tipo"] == "via_publica")
    assert via["matricula"] == "0"
    joao = next(c for c in conf if (c.get("nome") or "").startswith("João"))
    assert joao["matricula"] == "338"
    assert joao["segmentos"] == ["FQNS-M-A016"]


def test_confrontante_fazenda_com_incra_e_particular():
    """Confrontante rural TITULADO (Fazenda com INCRA/SNCR) SEM matrícula NÃO é bem
    público — é PARTICULAR e EXIGE anuência (Prov. CNJ 195/2025 + Decreto 4.449/2002)."""
    raw = "FAZENDA TRÊS IRMÃOS - INCRA: 1100350355993|CNS: 14.951-8|Mat.0"
    conf = EX.agrupar_confrontantes([{"codigo": "V1", "confrontacao_raw": raw}],
                                    matricula_imovel="141")
    assert len(conf) == 1
    c = conf[0]
    assert c["tipo"] == "particular", c          # antes: via_publica (BUG)
    assert c["incra"] == "1100350355993"         # INCRA com ':' agora é extraído


def test_confrontante_estrada_continua_via_publica():
    """Bem público REAL (estrada/rio) segue dispensando anuência."""
    conf = EX.agrupar_confrontantes(
        [{"codigo": "V1", "confrontacao_raw": "ESTRADA VICINAL|Mat.0"}], matricula_imovel="141")
    assert conf[0]["tipo"] == "via_publica"


def test_drl_particular_gera_anuencia_do_confrontante():
    """DRL de confrontante particular traz o bloco de ANUÊNCIA (confrontante assina)."""
    raw = "FAZENDA TRÊS IRMÃOS - INCRA: 1100350355993|Mat.0"
    conf = EX.agrupar_confrontantes([{"codigo": "V1", "confrontacao_raw": raw}],
                                    matricula_imovel="141")[0]
    projeto = {"imovel": {"denominacao": "FAZENDA SANTA MARIA", "matricula": "141",
                          "municipio": "Senador La Rocque", "uf": "MA",
                          "proprietario_nome": "MARIA", "proprietario_cpf_cnpj": "343.406.103-72"},
               "responsavel_tecnico": {"nome": "JOSE ROMARIO", "conselho": "CFT/MA"},
               "vertices": [{"codigo": "V1"}], "confrontantes": [conf]}
    d = TX.render_drl(projeto, conf)
    assert d["via_publica"] is False
    # há uma linha de assinatura do CONFRONTANTE (anuência)
    assert any("Confrontante" in papel for _, papel in d["assinaturas"])
    assert "RECONHECE" in d["corpo"] and "Decreto" in d["corpo"]


def test_drl_unificada_desmembramento(projeto):
    """Desmembramento/remembramento: DRL UNIFICADA (RT + proprietário) reconhecendo os
    limites já certificados; sem DRL por confrontante (Prov. CNJ 195/2025)."""
    p = {**projeto, "tipo_servico": "desmembramento",
         "parcelas": [{"id": "p2", "rotulo": "Parte II", "denominacao": "STA MARIA II",
                       "area_ha": 6.14, "perimetro_m": 1372, "certificacao_sigef": "ABC123"}]}
    assert TX.requer_drl(p["tipo_servico"]) is False           # sem DRL por confrontante
    assert TX.requer_drl_unificada(p["tipo_servico"]) is True  # tem DRL unificada
    assert TX.confrontantes_para_drl(p) == []                  # nenhuma DRL por confrontante
    d = TX.render_drl_unificada(p)
    assert "UNIFICADA" in d["titulo"]
    # assina o PROPRIETÁRIO e o RESPONSÁVEL TÉCNICO (não confrontantes)
    papeis = " ".join(pp for _, pp in d["assinaturas"])
    assert "Proprietário" in papeis and "Responsável Técnico" in papeis
    assert "RATIFICAM" in d["corpo"] and "Decreto" in d["corpo"] and "AVERBADO" in d["corpo"]
    # lista as parcelas resultantes (Parte I + Parte II)
    assert len(d["parcelas"]) == 2
    # gera o PDF
    b = PDF.gerar_pdf("drl_unificada", p, "prime_i")
    assert b[:5] == b"%PDF-"


def test_georref_nao_usa_drl_unificada(projeto):
    """Georreferenciamento/retificação usam DRL por CONFRONTANTE, não a unificada."""
    assert TX.requer_drl_unificada("georreferenciamento") is False
    assert TX.requer_drl_unificada("retificacao") is False


def test_confrontantes_para_drl_exclui_proprio(projeto):
    # nenhuma matrícula igual a 1234 -> todas geram DRL
    assert len(TX.confrontantes_para_drl(projeto)) == 4


def test_requer_drl_por_tipo():
    for t in ("georreferenciamento", "retificacao", "certificacao", "desdobro"):
        assert TX.requer_drl(t) is True, t
    for t in ("desmembramento", "remembramento"):
        assert TX.requer_drl(t) is False, t


def test_drl_dispensada_desmembramento(projeto):
    p = {**projeto, "tipo_servico": "desmembramento"}
    # nenhuma DRL para desmembramento/remembramento
    assert TX.confrontantes_para_drl(p) == []
    # e o Requerimento NÃO lista a DRL como documento instrutório
    assert not any("DRL" in item for item in TX.render_requerimento(p)["documentos"])
    # já o georref lista a DRL
    assert any("DRL" in item for item in TX.render_requerimento(projeto)["documentos"])


# ──────────────────────────────────────────────────────────────────────────────
# CCIR
# ──────────────────────────────────────────────────────────────────────────────
def test_parse_ccir(ccir_pdf):
    out = EX.parse_ccir(ccir_pdf)
    assert out["ccir_codigo"] == "123.456.789.012-3"
    assert out["ccir_area_total"] == pytest.approx(96.818)
    assert out["ccir_modulo_fiscal"] == pytest.approx(70.0)
    assert out["ccir_fmp"] == pytest.approx(2.0)
    assert "Pequena Propriedade" in (out.get("ccir_classificacao") or "")


# ──────────────────────────────────────────────────────────────────────────────
# Geometria / shapefile / geojson
# ──────────────────────────────────────────────────────────────────────────────
def test_build_ring_fecha(projeto):
    ring = GEO.build_ring(projeto["vertices"])
    assert len(ring) == 5            # 4 vértices + fechamento
    assert ring[0] == ring[-1]


def test_validar_geometria(projeto):
    area_calc, _perim = GEO.area_perimetro(GEO.build_ring(projeto["vertices"]))
    val = GEO.validar_geometria(projeto["vertices"], area_ha_sigef=area_calc)
    assert val["fechado"] is True
    assert val["simples"] is True
    assert val["divergencia_pct"] == pytest.approx(0.0, abs=0.01)
    assert val["area_calc_ha"] == pytest.approx(30.8, abs=1.0)


def test_geojson(projeto):
    gj = GEO.gerar_geojson(projeto)
    coords = gj["features"][0]["geometry"]["coordinates"][0]
    assert coords[0] == coords[-1]
    assert gj["features"][0]["properties"]["matricula"] == "1234"


def test_shapefile_valido(projeto):
    import shapefile
    from shapely.geometry import shape

    zbytes = GEO.gerar_shapefile_bytes(projeto)
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    nomes = {n.split(".")[-1] for n in z.namelist()}
    assert {"shp", "shx", "dbf", "prj"} <= nomes
    # reabre via pyshp e valida com shapely
    membros = {n.split(".")[-1]: z.read(n) for n in z.namelist()}
    r = shapefile.Reader(
        shp=io.BytesIO(membros["shp"]), shx=io.BytesIO(membros["shx"]),
        dbf=io.BytesIO(membros["dbf"]),
    )
    assert r.shapeType == shapefile.POLYGON
    geom = shape(r.shape(0).__geo_interface__)
    assert geom.is_valid
    rec = r.record(0).as_dict()
    assert rec["MATRICULA"] == "1234"
    assert "SIRGAS" in rec["SGEODESIC"]
    # atributos SIG-RI completos (Prov. 195/2025): m² derivado do ha + campos do acervo
    assert rec["AREA_M2"] == pytest.approx(rec["AREA_HA"] * 10000, rel=1e-3)
    for campo in ("PARCELA", "TIPO_ATO", "COD_INCRA", "PROPRIET", "RT_NOME", "PERIM_M"):
        assert campo in rec
    # PRJ é SIRGAS 2000 / EPSG 4674
    assert b"4674" in membros["prj"]


def test_descricao_poligono_para_rgi(projeto_multi):
    """Cada parcela tem uma 'Descrição do polígono' pronta p/ colar no ONR/RGI."""
    atrs = GEO.atributos_sigri(projeto_multi)
    for a in atrs:
        d = a["descricao"]
        assert isinstance(d, str) and d.endswith(".")
        assert "matrícula" in d.lower() and "perímetro" in d.lower() and "ha" in d
        assert "desmembramento" in d.lower()          # tipo do ato refletido
    # a Parte I e a Parte II têm descrições DISTINTAS (área/denominação próprias)
    assert atrs[0]["descricao"] != atrs[1]["descricao"]


def test_atributos_sigri_completo(projeto_multi):
    """A conferência SIG-RI traz UM registro completo por parcela (Parte I + Parte II)."""
    atrs = GEO.atributos_sigri(projeto_multi)
    assert len(atrs) == 2
    campos = {c[0] for c in GEO.campos_sigri()}
    for a in atrs:
        assert set(a["record"].keys()) == campos          # todos os atributos presentes
        assert a["record"]["TIPO_ATO"] == "desmembramento"
    # a Parte II tem denominação/área próprias (parcela-aware)
    p2 = next(a for a in atrs if not a["principal"])
    assert "PARTE II" in (p2["record"]["DENOM"] or "").upper() or p2["record"]["PARCELA"]


# ──────────────────────────────────────────────────────────────────────────────
# Builders de conteúdo
# ──────────────────────────────────────────────────────────────────────────────
def test_requerimento_conteudo(projeto):
    d = TX.render_requerimento(projeto)
    assert "REQUERIMENTO DE GEORREFERENCIAMENTO" in d["titulo"]
    assert d["titulo"].lower().startswith("requerimento de georreferenciamento para fim")
    assert "195/2025" in d["corpo"]
    assert "10.267/2001" in d["corpo"]
    assert "Fazenda Santa Maria" in d["corpo"]


def test_drl_via_publica_sem_confrontante(projeto):
    via = next(c for c in projeto["confrontantes"] if c["tipo"] == "via_publica")
    d = TX.render_drl(projeto, via)
    assert d["via_publica"] is True
    papeis = [p for _n, p in d["assinaturas"]]
    assert not any("Confrontante" in p for p in papeis)   # via pública não assina
    particular = next(c for c in projeto["confrontantes"] if c["tipo"] == "particular")
    d2 = TX.render_drl(projeto, particular)
    assert any("Confrontante" in p for _n, p in d2["assinaturas"])
    assert len(d2["tabela"]) == len(particular["segmentos"])


def test_laudo_secoes(projeto):
    d = TX.render_laudo_tecnico(projeto)
    assert "LAUDO TÉCNICO DE AGRIMENSURA" in d["titulo"]
    assert "SIRGAS 2000" in d["metodologia"]
    assert "13133" in d["justificativa"]
    assert len(d["resultado_tabela"]) == 4
    # sem cadeia dominial -> nota de certidão anexa
    assert d["cadeia_tabela"] is None
    assert "anexa" in d["cadeia_nota"]


# ──────────────────────────────────────────────────────────────────────────────
# Regressão: layout REAL de 2 colunas do SIGEF (campos vizinhos na mesma linha)
# ──────────────────────────────────────────────────────────────────────────────
_MEMORIAL_2COL = [
    "MEMORIAL DESCRITIVO",
    "Denominação: FAZENDA SANTA MARIA - PARTE I Natureza da Área: Particular",
    "Proprietário(a): PAULO HENRIQUE DA LUZ OLIVEIRA CPF: 960.826.313-15",
    "Matrícula do imóvel:489 (1 de 2) Código INCRA/SNCR: 9510990828483",
    "Município/UF: São Francisco do Brejão-MA Cartório (CNS): (03.169-0) São Francisco do",
    "Responsável Técnico(a): JOSE ROMARIO PINTO BEZERRA Maranhão - MA",
    "Formação: Técnico(a) Industrial em Agrimensura",
    "Código de credenciamento: FQNS Conselho Profissional: 01209185369/MA",
    "Sistema Geodésico de referência: SIRGAS 2000 Documento de RT: CFT2605953795 - MA",
    "Área (Sistema Geodésico Local): 96,818 ha Coordenadas: Latitude, longitude e altitude",
    "Perímetro (m): 4.095,92 m Azimutes: Azimutes geodésicos",
    "FQNS-M-A016 -47°15'36,000\" -5°11'24,000\" 280,50 FQNS-M-017 90°00' 554,40 "
    "CNS: 03.169-0 | Mat. 338 | Nome: XXXXFRANCISCO XXXX CPF: ***.403.283**",
    "FQNS-M-017 -47°15'18,000\" -5°11'24,000\" 281,00 FQNS-M-018 0°00' 556,60 "
    "CNS: 03.169-0 | Mat. 338 | Joao Francisco da Silva",
]


def test_parse_memorial_layout_2colunas():
    """Garante o split correto quando o SIGEF junta 2 colunas na mesma linha."""
    r = EX.parse_memorial(_pdf_de_linhas(_MEMORIAL_2COL))
    im = r["imovel"]
    assert im["denominacao"] == "FAZENDA SANTA MARIA - PARTE I"        # sem "Natureza..."
    assert im["proprietario_nome"] == "PAULO HENRIQUE DA LUZ OLIVEIRA"  # sem "CPF..."
    assert im["proprietario_cpf_cnpj"] == "960.826.313-15"
    assert im["natureza_area"] == "Particular"
    assert im["sistema_geodesico"] == "SIRGAS 2000"                     # sem "Documento de RT..."
    assert im["municipio"] == "São Francisco do Brejão"
    assert im["uf"] == "MA"
    assert im["matricula"] == "489"
    assert im["area_ha"] == pytest.approx(96.818)
    assert im["perimetro_m"] == pytest.approx(4095.92)
    assert r["responsavel_tecnico"]["nome"] == "JOSE ROMARIO PINTO BEZERRA"  # sem wrap "Maranhão"
    # confrontante Mat.338 vira 1 grupo só, com o nome LIMPO (não o mascarado)
    conf = EX.agrupar_confrontantes(r["vertices"], im["matricula"])
    g338 = [c for c in conf if c.get("matricula") == "338"]
    assert len(g338) == 1
    assert g338[0]["nome"] == "Joao Francisco da Silva"
    assert len(g338[0]["segmentos"]) == 2


# ──────────────────────────────────────────────────────────────────────────────
# Renderers PDF / DOCX (nos 3 temas)
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("tema", ["tradicional", "prime_i", "prime_ii"])
@pytest.mark.parametrize("tipo", ["requerimento", "memorial", "laudo_tecnico"])
def test_pdf_gera(projeto, tipo, tema):
    out = PDF.gerar_pdf(tipo, projeto, tema)
    assert out[:5] == b"%PDF-"
    assert len(out) > 1500


@pytest.mark.parametrize("tema", ["tradicional", "prime_i", "prime_ii"])
def test_pdf_drl(projeto, tema):
    conf = projeto["confrontantes"][0]
    out = PDF.gerar_pdf("drl", projeto, tema, conf=conf)
    assert out[:5] == b"%PDF-"


@pytest.mark.parametrize("tipo", ["requerimento", "memorial", "laudo_tecnico"])
def test_docx_gera(projeto, tipo):
    out = DOCX.gerar_docx(tipo, projeto)
    assert out[:2] == b"PK"            # zip/docx
    assert len(out) > 1500


def test_docx_drl(projeto):
    conf = projeto["confrontantes"][0]
    out = DOCX.gerar_docx("drl", projeto, conf=conf)
    assert out[:2] == b"PK"


# ──────────────────────────────────────────────────────────────────────────────
# Dossiê consolidado
# ──────────────────────────────────────────────────────────────────────────────
def test_dossie_merge(projeto):
    from pypdf import PdfReader

    req = PDF.gerar_pdf("requerimento", projeto, "prime_i")
    laudo = PDF.gerar_pdf("laudo_tecnico", projeto, "prime_i")
    mem = PDF.gerar_pdf("memorial", projeto, "prime_i")
    drls = [PDF.gerar_pdf("drl", projeto, "prime_i", conf=c)
            for c in TX.confrontantes_para_drl(projeto)]
    out = DOSSIE.gerar_dossie(
        projeto, {"requerimento": req, "laudo_tecnico": laudo, "memorial": mem, "drl": drls},
        "prime_i",
    )
    assert out[:5] == b"%PDF-"
    # capa(1) + sumário(1) + req + laudo + memorial + 4 DRLs -> várias páginas
    assert len(PdfReader(io.BytesIO(out)).pages) >= 8


def test_dossie_sumario_com_links(projeto):
    """Dossiê: pág 2 é o SUMÁRIO com links clicáveis (ref de página) + bookmarks."""
    from pypdf import PdfReader
    from pypdf.generic import IndirectObject

    req = PDF.gerar_pdf("requerimento", projeto, "prime_i")
    laudo = PDF.gerar_pdf("laudo_tecnico", projeto, "prime_i")
    mem = PDF.gerar_pdf("memorial", projeto, "prime_i")
    out = DOSSIE.gerar_dossie(
        projeto, {"requerimento": req, "laudo_tecnico": laudo, "memorial": mem}, "prime_i")
    rd = PdfReader(io.BytesIO(out))
    assert "SUMÁRIO" in (rd.pages[1].extract_text() or "")        # pág 2 = sumário
    annots = rd.pages[1].get("/Annots") or []
    assert len(annots) == 3                                       # req, laudo, memorial
    pagemap = {p.indirect_reference.idnum: i for i, p in enumerate(rd.pages)}
    for a in annots:
        dest = a.get_object().get("/Dest")
        assert isinstance(dest[0], IndirectObject)                # ref de página (não inteiro)
        assert dest[0].idnum in pagemap
    # 1ª seção (requerimento) começa após capa(1)+sumário(1) → índice 2 (3ª página)
    alvos = [pagemap[a.get_object()["/Dest"][0].idnum] for a in annots]
    assert min(alvos) == 2
    assert len(rd.outline) >= 5                                   # Capa + Sumário + 3 seções


# ──────────────────────────────────────────────────────────────────────────────
# Modelo / completude
# ──────────────────────────────────────────────────────────────────────────────
def test_completude(projeto):
    assert calcular_completude(projeto) >= 90


def test_modelo_default():
    p = GeorefProjeto(user_id="u1", nome_projeto="Teste")
    assert p.status == "rascunho"
    assert p.tema_pdf == "prime_i"
    assert p.responsavel_tecnico.credenciamento_incra == "FQNS"


# ──────────────────────────────────────────────────────────────────────────────
# Multi-parcela (desmembramento)
# ──────────────────────────────────────────────────────────────────────────────
def _parcela_ii():
    """Parcela adicional com poligonal própria (retângulo deslocado)."""
    verts = [
        {"codigo": "FQNS-M-B001", "longitude": -47.250, "latitude": -5.200,
         "vante_codigo": "FQNS-M-B002", "azimute": "90°00'", "distancia": 500.0,
         "longitude_dms": "-47°15'00\"", "latitude_dms": "-5°12'00\"", "altitude": 280.0,
         "confrontacao_raw": "CNS: 03.169-0 | Mat. 489 | PAULO HENRIQUE"},
        {"codigo": "FQNS-M-B002", "longitude": -47.245, "latitude": -5.200,
         "vante_codigo": "FQNS-M-B003", "azimute": "0°00'", "distancia": 500.0,
         "longitude_dms": "-47°14'42\"", "latitude_dms": "-5°12'00\"", "altitude": 281.0,
         "confrontacao_raw": "CNS: 03.169-0 | Mat. 0 | ESTRADA VICINAL"},
        {"codigo": "FQNS-M-B003", "longitude": -47.245, "latitude": -5.195,
         "vante_codigo": "FQNS-M-B001", "azimute": "270°00'", "distancia": 500.0,
         "longitude_dms": "-47°14'42\"", "latitude_dms": "-5°11'42\"", "altitude": 282.0,
         "confrontacao_raw": "CNS: 03.169-0 | Mat. 0 | ESTRADA VICINAL"},
    ]
    return {"id": "parc2", "rotulo": "Parte II", "denominacao": "FAZENDA SANTA MARIA - PARTE II",
            "area_ha": 22.5, "perimetro_m": 1500.0, "certificacao_sigef": "CERT-II",
            "vertices": verts, "confrontantes": []}


@pytest.fixture
def projeto_multi(projeto):
    p = {**projeto, "tipo_servico": "desmembramento", "parcelas": [_parcela_ii()]}
    return p


def test_parcelas_do_projeto(projeto, projeto_multi):
    from services.georef import parcelas as P
    pv = P.parcelas_do_projeto(projeto_multi)
    assert len(pv) == 2
    assert pv[0]["principal"] is True and pv[0]["rotulo"] == "Parte I"
    assert pv[1]["principal"] is False and pv[1]["rotulo"] == "Parte II"
    assert pv[1]["denominacao"] == "FAZENDA SANTA MARIA - PARTE II"
    assert P.tem_multiparcela(projeto_multi) is True
    assert P.tem_multiparcela(projeto) is False


def test_projeto_da_parcela(projeto_multi):
    from services.georef import parcelas as P
    pv = P.parcelas_do_projeto(projeto_multi)[1]
    sub = P.projeto_da_parcela(projeto_multi, pv)
    # dados da parcela sobrepõem o imóvel; proprietário (compartilhado) preservado
    assert sub["imovel"]["denominacao"] == "FAZENDA SANTA MARIA - PARTE II"
    assert sub["imovel"]["area_ha"] == 22.5
    assert sub["imovel"]["proprietario_cpf_cnpj"] == projeto_multi["imovel"]["proprietario_cpf_cnpj"]
    assert len(sub["vertices"]) == 3


def test_shapefile_multipoligono(projeto_multi):
    """Desmembramento gera UM shapefile POR PARCELA no .zip (dois conjuntos shp/shx/dbf/prj)."""
    import shapefile
    zbytes = GEO.gerar_shapefile_bytes(projeto_multi)
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    # dois shapefiles distintos (dois .shp), cada um com 1 polígono
    shp_names = sorted(n for n in z.namelist() if n.endswith(".shp"))
    assert len(shp_names) == 2, f"esperava 2 shapefiles, veio: {z.namelist()}"
    denoms = set()
    for shp in shp_names:
        base = shp[:-4]
        r = shapefile.Reader(
            shp=io.BytesIO(z.read(base + ".shp")), shx=io.BytesIO(z.read(base + ".shx")),
            dbf=io.BytesIO(z.read(base + ".dbf")))
        assert len(r.shapes()) == 1      # cada arquivo = 1 parcela
        denoms.add(r.record(0).as_dict().get("DENOM"))
    assert any("PARTE II" in (d or "") for d in denoms)


def test_laudo_e_requerimento_listam_parcelas(projeto_multi):
    laudo = TX.render_laudo_tecnico(projeto_multi)
    assert laudo["parcelas_tabela"] is not None
    assert len(laudo["parcelas_tabela"]) == 2
    req = TX.render_requerimento(projeto_multi)
    assert req["parcelas"] is not None
    assert any("Parte II" in linha for linha in req["parcelas"])
    # ação do requerimento muda para DESMEMBRAMENTO
    assert "DESMEMBRAMENTO" in req["corpo"]


def test_pdf_memorial_por_parcela(projeto_multi):
    from services.georef import parcelas as P
    pv = P.parcelas_do_projeto(projeto_multi)[1]
    sub = P.projeto_da_parcela(projeto_multi, pv)
    out = PDF.gerar_pdf("memorial", sub, "prime_i")
    assert out[:5] == b"%PDF-"


# ──────────────────────────────────────────────────────────────────────────────
# Cartório por CNS (tabela oficial de serventias)
# ──────────────────────────────────────────────────────────────────────────────
def test_serventia_lookup_por_cns():
    from services.georef import serventias as S
    s = S.buscar_serventia("03.169-0")
    assert s is not None
    assert "SAO FRANCISCO DO MARANHAO" in s["denominacao"].upper()
    assert s["uf"] == "MA"
    assert S.buscar_serventia("031690") is not None     # aceita formato sem pontuação
    assert S.buscar_serventia("xxx") is None             # sem dígitos -> nada


def test_enriquecer_cartorio_pelo_cns():
    from services.georef import serventias as S
    im = {"cartorio_cns": "03.169-0", "cartorio_nome": "São Francisco do"}  # parser parcial
    S.enriquecer_cartorio(im, {})
    assert "SERVENTIA" in im["cartorio_nome"].upper()    # nome correto da serventia
    assert im["cartorio_municipio"]
    assert im["cartorio_uf"] == "MA"
    # respeita edição manual (não sobrescreve)
    im2 = {"cartorio_cns": "03.169-0", "cartorio_nome": "Meu cartório"}
    S.enriquecer_cartorio(im2, {"imovel.cartorio_nome": True})
    assert im2["cartorio_nome"] == "Meu cartório"


def test_requerimento_usa_comarca_do_cartorio(projeto):
    p = {**projeto, "imovel": {**projeto["imovel"],
                               "cartorio_municipio": "São Francisco do Maranhão", "cartorio_uf": "MA"}}
    d = TX.render_requerimento(p)
    assert "São Francisco do Maranhão/MA" in d["destinatario"]


# ──────────────────────────────────────────────────────────────────────────────
# Bug 1.1 — normalização de denominação (PARTA → PARTE)
# ──────────────────────────────────────────────────────────────────────────────
def test_normalizar_denominacao():
    from services.georef import parcelas as P
    base = {"imovel": {"denominacao": "FAZENDA X - FAZENDA X PARTA I"},
            "parcelas": [], "vertices": [], "confrontantes": []}
    assert "PARTA" in P.parcelas_do_projeto(base)[0]["denominacao"]   # desligado: preserva
    base["normalizar_denominacao"] = True
    assert P.parcelas_do_projeto(base)[0]["denominacao"].endswith("PARTE I")


# ──────────────────────────────────────────────────────────────────────────────
# Bug 1.2 — serventia/comarca da certidão prevalece sobre a cidade do CNS
# ──────────────────────────────────────────────────────────────────────────────
def test_parse_serventia_da_certidao():
    txt = ("CERTIDÃO DE INTEIRO TEOR\n"
           "OFÍCIO ÚNICO DE SÃO FRANCISCO DO BREJÃO (Tabeliã Melina Luna Dias), CNS 03.169-0\n"
           "Comarca de São Francisco do Brejão/MA.")
    s = EX.parse_serventia_text(txt)
    assert "BREJÃO" in s["cartorio_nome"].upper()
    assert "Brejão" in s["cartorio_municipio"]
    assert s["cartorio_uf"] == "MA"


def test_enriquecer_nao_sobrepoe_municipio_do_imovel():
    from services.georef import serventias as S
    # a cidade da tabela CNS (Maranhão) NÃO entra na comarca quando o imóvel já tem município
    im = {"cartorio_cns": "03.169-0", "municipio": "São Francisco do Brejão", "uf": "MA"}
    S.enriquecer_cartorio(im, {})
    assert im.get("cartorio_municipio") in (None, "São Francisco do Brejão")


def test_requerimento_comarca_do_municipio_sem_cartorio(projeto):
    p = {**projeto, "imovel": {**projeto["imovel"], "cartorio_municipio": None,
                               "municipio": "São Francisco do Brejão", "uf": "MA"}}
    d = TX.render_requerimento(p)
    assert "São Francisco do Brejão/MA" in d["destinatario"]


# ──────────────────────────────────────────────────────────────────────────────
# Laudo UNIFICADO — subseção de poligonal/confrontações por parcela
# ──────────────────────────────────────────────────────────────────────────────
def test_laudo_unificado_subsecoes_por_parcela(projeto_multi):
    d = TX.render_laudo_tecnico(projeto_multi)
    assert d["multiparcela"] is True
    assert d["resultado_parcelas"] and len(d["resultado_parcelas"]) == 2
    assert d["resultado_parcelas"][0]["rotulo"] == "Parte I"
    assert d["resultado_parcelas"][1]["rotulo"] == "Parte II"
    # cada subseção tem os vértices da SUA parcela (principal=4, parcela II=3)
    assert len(d["resultado_parcelas"][0]["tabela"]) == 4
    assert len(d["resultado_parcelas"][1]["tabela"]) == 3
    assert d["confrontacoes_parcelas"] and len(d["confrontacoes_parcelas"]) == 2
    # OBJETO lista TODOS os códigos SIGEF (não só o da Parte I)
    assert "ABC123XYZ" in d["objeto"] and "CERT-II" in d["objeto"]
    # CONCLUSÃO atesta as duas parcelas
    assert "Parte I" in d["conclusao"] and "Parte II" in d["conclusao"]


def test_laudo_unificado_pdf_secoes_por_parcela(projeto_multi):
    from pypdf import PdfReader
    out = PDF.gerar_pdf("laudo_tecnico", projeto_multi, "prime_i")
    txt = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(out)).pages)
    assert "POLIGONAL POR PARCELA" in txt
    assert "CONFRONTAÇÕES POR PARCELA" in txt


# ──────────────────────────────────────────────────────────────────────────────
# Laudo SEPARADO — 1 PDF por parcela
# ──────────────────────────────────────────────────────────────────────────────
def test_pdf_laudos_separados(projeto_multi):
    from pypdf import PdfReader
    seps = PDF.pdf_laudos_separados(projeto_multi, "prime_i")
    assert len(seps) == 2
    assert all(s["bytes"][:5] == b"%PDF-" for s in seps)
    assert seps[0]["rotulo"] == "Parte I" and seps[1]["rotulo"] == "Parte II"
    t1 = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(seps[1]["bytes"])).pages)
    assert "Parte II" in t1                       # descreve só a parcela
    assert "489" in t1 or "1234" in t1            # cita a matriz de origem


def test_dossie_laudo_separado_um_sumario_por_parcela(projeto_multi):
    from pypdf import PdfReader
    laudos = PDF.pdf_laudos_separados(projeto_multi, "prime_i")
    laudo_secao = [{"titulo": f"Laudo Técnico de Agrimensura — {lp['rotulo']}",
                    "bytes": lp["bytes"]} for lp in laudos]
    req = PDF.gerar_pdf("requerimento", projeto_multi, "prime_i")
    out = DOSSIE.gerar_dossie(
        projeto_multi, {"requerimento": req, "laudo_tecnico": laudo_secao}, "prime_i")
    sumario = PdfReader(io.BytesIO(out)).pages[1].extract_text() or ""
    assert sumario.count("Laudo Técnico") >= 2
    assert "Parte I" in sumario and "Parte II" in sumario


def test_dossie_laudo_unificado_uma_secao(projeto_multi):
    """Modo unificado: o laudo continua sendo UMA seção (regressão)."""
    from pypdf import PdfReader
    laudo = PDF.gerar_pdf("laudo_tecnico", projeto_multi, "prime_i")
    out = DOSSIE.gerar_dossie(projeto_multi, {"laudo_tecnico": laudo}, "prime_i")
    sumario = PdfReader(io.BytesIO(out)).pages[1].extract_text() or ""
    assert sumario.count("Laudo Técnico") == 1


# ──────────────────────────────────────────────────────────────────────────────
# Requerimento de Cancelamento de parcela SIGEF (Ofício Circular 814/2026/INCRA)
# ──────────────────────────────────────────────────────────────────────────────
def _projeto_cancelamento(**canc):
    base = {
        "tipo_servico": "cancelamento", "tema_pdf": "prime_i",
        "imovel": {"proprietario_nome": "ANTONIO DA SILVA",
                   "proprietario_cpf_cnpj": "123.456.789-00", "denominacao": "Fazenda Santa Maria",
                   "matricula": "489", "cod_incra": "1100350355993", "municipio": "Açailândia",
                   "uf": "MA", "area_ha": 102.964, "perimetro_m": 5080.40,
                   "certificacao_sigef": "ABC12345"},
        "responsavel_tecnico": {"nome": "JOSE ROMARIO", "conselho": "CFT/MA",
                                "credenciamento_incra": "FQNS"},
        "cancelamento": {"justificativa": "alteracao_rt", "codigo_parcela_sigef": "PARC-001",
                         "natureza": "particular", "registro_confirmado": False,
                         "ods_uma_aba": True, "area_parcela_ha": 102.964, "area_ods_ha": 102.5,
                         "requerente_e_rt": True},
    }
    base["cancelamento"].update(canc)
    return base


def test_cancelamento_catalogo_dez_justificativas():
    from services.georef import cancelamento as C
    assert len(C.JUSTIFICATIVAS) == 10
    nums = [j["num"] for j in C.JUSTIFICATIVAS]
    assert nums == ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    # distrato e impedimento de registro dispensam a Planilha ODS (item 2.2)
    assert C.justificativa("distrato")["exige_ods"] is False
    assert C.justificativa("impedimento_registro")["exige_ods"] is False
    assert C.justificativa("alteracao_rt")["exige_ods"] is True


def test_cancelamento_deferimento_automatico_todas_condicoes():
    from services.georef import cancelamento as C
    proj = _projeto_cancelamento()
    ck = C.checklist(proj)
    assert ck["justificativa"]["id"] == "alteracao_rt"
    assert ck["deferimento_automatico"] is True
    assert all(c["ok"] is True for c in ck["condicoes_auto"])
    # ODS entra no checklist de documentos qdo exigida
    assert any("Planilha ODS" in d["label"] for d in ck["documentos"])


def test_cancelamento_area_ods_divergente_barra_deferimento():
    from services.georef import cancelamento as C
    # diferença de 40 ha (> 25 ha e > 10%) → condições v e vi falham
    proj = _projeto_cancelamento(area_parcela_ha=100.0, area_ods_ha=60.0)
    ck = C.checklist(proj)
    assert ck["deferimento_automatico"] is False
    assert not C.exige_ods(proj) or True  # ODS segue exigida p/ alteracao_rt
    assert C.exige_ods(proj) is True


def test_cancelamento_distrato_dispensa_ods():
    from services.georef import cancelamento as C
    proj = _projeto_cancelamento(justificativa="distrato")
    assert C.exige_ods(proj) is False
    labels = [d["label"] for d in C.documentos_checklist(proj)]
    assert not any("Planilha ODS" in x for x in labels)


def test_cancelamento_pdf_gera_com_justificativa_e_referencia():
    proj = _projeto_cancelamento()
    pdf = PDF.gerar_pdf("requerimento_cancelamento", proj, "prime_i")
    assert pdf[:5] == b"%PDF-" and len(pdf) > 2000
    d = TX.render_requerimento_cancelamento(proj)
    assert "CANCELAMENTO" in d["titulo"]
    assert "Alteração de Responsável Técnico" in d["justificativa_titulo"]
    assert "814/2026" in d["corpo"]
    assert d["deferimento_automatico"] is True
    # detentor + RT assinam
    papeis = [p[1] for p in d["assinaturas"]]
    assert any("Detentor" in x for x in papeis) and any("Responsável Técnico" in x for x in papeis)


# ──────────────────────────────────────────────────────────────────────────────
# Motor de conferência da Planilha ODS (SIGEF) — services/georef/ods.py
# ──────────────────────────────────────────────────────────────────────────────
def _ods_cell(txt):
    return f"<table:table-cell><text:p>{txt}</text:p></table:table-cell>"


def _ods_row(*cells):
    return "<table:table-row>" + "".join(_ods_cell(c) for c in cells) + "</table:table-row>"


def _build_ods(vertices, sistema="Sistema de referência SIRGAS2000", n_perim=1):
    perim_rows = [
        _ods_row(sistema),
        _ods_row("Vértice", "E/Long", "Sigma long", "N/Lat", "Sigma lat", "h", "Sigma h",
                 "Método Posicionamento", "Tipo Limite", "CNS", "Matrícula", "Descritivo"),
    ]
    for cod, lon, lat in vertices:
        perim_rows.append(_ods_row(cod, lon, "0,00", lat, "0,00", "100", "0,01",
                                   "PG1", "LA1", "03.018-9", "123", "Confrontante X"))
    perim = "".join(
        f'<table:table table:name="perimetro_{i}">' + "".join(perim_rows) + "</table:table>"
        for i in range(1, n_perim + 1))
    ident = ('<table:table table:name="identificacao">'
             + _ods_row("Denominação:", "FAZENDA TESTE")
             + _ods_row("Matrícula:", "489")
             + _ods_row("Código do Imóvel(SNCR/INCRA):", "1100350355993")
             + _ods_row("Natureza da área:", "Particular")
             + _ods_row("Código do cartório (CNS):", "03.018-9")
             + "</table:table>")
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-content '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
        "<office:body><office:spreadsheet>" + ident + perim
        + "</office:spreadsheet></office:body></office:document-content>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("content.xml", content)
    return buf.getvalue()


_VERTS_OK = [
    ("FQNS-M-1", "47 28 34,000 W", "04 58 20,000 S"),
    ("FQNS-M-2", "47 28 20,000 W", "04 58 20,000 S"),
    ("FQNS-M-3", "47 28 20,000 W", "04 58 34,000 S"),
    ("FQNS-M-4", "47 28 34,000 W", "04 58 34,000 S"),
]


def test_ods_analisa_e_valida_sirgas():
    from services.georef import ods as ODS
    data = _build_ods(_VERTS_OK)
    a = ODS.analisar(data)
    assert a["abas_perimetro"] == ["perimetro_1"]
    assert "SIRGAS2000" in a["sistema_referencia"].upper().replace(" ", "")
    assert a["n_vertices"] == 4 and a["area_ha"] and a["area_ha"] > 0
    assert a["identificacao"]["matricula"] == "489"
    v = ODS.validar(data, area_parcela_ha=a["area_ha"])
    assert v["ok"] is True and not v["erros"]
    cods = [i["codigo"] for i in v["info"]]
    assert "PERIMETRO_UNICO" in cods and "SRC_OK" in cods and "AREA_OK" in cods


def test_ods_sistema_invalido_gera_erro():
    from services.georef import ods as ODS
    data = _build_ods(_VERTS_OK, sistema="Sistema de referência SAD69")
    v = ODS.validar(data)
    assert v["ok"] is False
    assert any(e["codigo"] == "SRC_INVALIDO" for e in v["erros"])


def test_ods_multi_perimetro_gera_alerta():
    from services.georef import ods as ODS
    data = _build_ods(_VERTS_OK, n_perim=2)
    a = ODS.analisar(data)
    assert len(a["abas_perimetro"]) == 2
    v = ODS.validar(data)
    assert any(x["codigo"] == "MULTI_PERIMETRO" for x in v["alertas"])


def test_ods_poucos_vertices_gera_erro():
    from services.georef import ods as ODS
    data = _build_ods(_VERTS_OK[:2])
    v = ODS.validar(data)
    assert any(e["codigo"] == "POUCOS_VERTICES" for e in v["erros"])


def test_ods_area_divergente_alerta():
    from services.georef import ods as ODS
    data = _build_ods(_VERTS_OK)
    v = ODS.validar(data, area_parcela_ha=999.0)  # muito maior que a real
    cods = [x["codigo"] for x in v["alertas"]]
    assert "AREA_DIFF_10" in cods and "AREA_DIFF_25" in cods


def test_ods_para_pdf():
    from services.georef import ods as ODS
    data = _build_ods(_VERTS_OK)
    pdf = ODS.para_pdf(data, "prime_i")
    assert pdf[:5] == b"%PDF-" and len(pdf) > 2000
