# Testes do parser dos MEMORIAIS georref urbano (extração → auto-preenchimento).
# Calibrado no modelo real QD04 LT20 ROV (verificado com os PDFs reais na sessão).
import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

from services.geo_urbano import extractor_georref as EX


def _mk_pdf(linhas):
    """PDF sintético: uma linha por drawString (pdfplumber lê linha a linha)."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    y = 800
    for ln in linhas:
        c.drawString(40, y, ln)
        y -= 16
    c.showPage()
    c.save()
    return buf.getvalue()


_COORD = [
    "MEMORIAL DESCRITIVO",
    "(X) Imóvel Urbano.",
    "Bairro: Rua: Quadra: Lote:",
    "Residencial Ouro Verde Rua Fernando Pessoa 04 20",
    "Área: 300,00m² Município: Açailândia Estado: MA",
    "CIM: 046.0004.0020.0001-201 TRT:",
    "DESCRIÇÃO DO PERÍMETRO",
    "Inicia-se a descrição deste perímetro no vértice P1, de coordenadas N 9.450.853,30m e E 224.062,78m; Muro;",
    "deste, segue confrontando com Lote nº 19, com os seguintes azimutes e distâncias: 122°56'38\" e 25,00 m",
    "até o vértice P2, de coordenadas N 9.450.839,70m e E 224.083,76m; Muro;",
    "deste, segue confrontando com RUA FERNANDO PESSOA, com os seguintes azimutes e distâncias: 212°56'38\" e 12,00 m",
    "até o vértice P3, de coordenadas N 9.450.829,63m e E 224.077,23m; Muro;",
    "deste, segue confrontando com Lote nº 21, com os seguintes azimutes e distâncias: 302°56'38\" e 25,00 m",
    "até o vértice P4, de coordenadas N 9.450.843,23m e E 224.056,25m; Muro;",
    "deste, segue confrontando com Lote nº 05, com os seguintes azimutes e distâncias: 32°56'31\" e 12,00 m",
    "até o vértice P1, ponto inicial da descrição deste perímetro.",
    "Meridiano Central nº 45°00', fuso -23, tendo como datum o SIRGAS2000.",
]

_SIT = [
    "MEMORIAL DESCRITIVO",
    "Um TERRENO nesta cidade de Açailândia, Estado do Maranhão, Frente para a Rua Fernando Pessoa,",
    "denominado Lote nº 20 da Quadra nº 04 – RESIDENCIAL OURO VERDE, com área de 300,00m². Formato do lote retangular.",
    "Situado na quadra formada pelas seguintes confrontantes: Rua Fernando Pessoa, Avenida Contorno,",
    "Avenida Rafael de Almeida e Avenida Adelino Andrade. Distante da esquina com a Avenida Contorno, medindo 48,00m.",
]


def test_split_ident():
    assert EX._split_ident("Residencial Ouro Verde Rua Fernando Pessoa 04 20") == \
        ("Residencial Ouro Verde", "Rua Fernando Pessoa", "04", "20")
    assert EX._split_ident("Centro Avenida Brasil 10 5") == ("Centro", "Avenida Brasil", "10", "5")


def test_parse_coordenadas_identificacao():
    d = EX.parse_memorial_coordenadas(_mk_pdf(_COORD))
    assert d["bairro"] == "Residencial Ouro Verde"
    assert d["rua"] == "Rua Fernando Pessoa"
    assert d["quadra"] == "04" and d["lote"] == "20"
    assert d["area"] == 300.0
    assert d["municipio"] == "Açailândia" and d["uf"] == "MA"
    assert d["cim_base"] == "046.0004.0020.0001" and d["cim_controle"] == "201"
    assert d["fuso"] == "-23"


def test_parse_coordenadas_vertices():
    d = EX.parse_memorial_coordenadas(_mk_pdf(_COORD))
    vs = d["vertices"]
    assert len(vs) == 4
    assert vs[0]["de"] == "P1" and vs[0]["coord_n"] == 9450853.30 and vs[0]["coord_e"] == 224062.78
    assert vs[0]["confrontante_lado"] == "Lote nº 19" and vs[0]["distancia_m"] == 25.0
    assert vs[0]["feicao"] == "Muro"
    assert vs[1]["confrontante_lado"] == "RUA FERNANDO PESSOA" and vs[1]["distancia_m"] == 12.0
    assert vs[3]["de"] == "P4" and vs[3]["confrontante_lado"] == "Lote nº 05"


def test_parse_situacao():
    d = EX.parse_memorial_situacao(_mk_pdf(_SIT))
    assert d["formato"] == "retangular"
    nomes = [v["nome"] for v in d["vias"]]
    assert nomes == ["Rua Fernando Pessoa", "Avenida Contorno", "Avenida Rafael de Almeida", "Avenida Adelino Andrade"]
    assert d["esquina"]["logradouro"] == "Avenida Contorno" and d["esquina"]["distancia_m"] == 48.0


_ART = [
    "Termo de Responsabilidade Técnica - TRT",
    "Nº CFT2606068376",
    "2. Contratante",
    "Contratante: AJM CONSTRUTORA E INCORPORADORA DE EMPREENDIMENTOS IMOBILIARIOS CPF/CNPJ: 10.742.243/0001-59",
    "LTDA",
    "Logradouro:RUA SÃO RAIMNUNDO Nº: 527",
    "Complemento: Bairro: CENTRO",
    "Cidade:AÇAILÂNDIA UF:MA CEP:65930000",
    "Telefone:(99) 9125-4865 Email:",
    "3. Dados da Obra/Serviço",
    "Proprietário(a): AJM CONSTRUTORA E INCORPORADORA DE EMPREENDIMENTOS CPF/CNPJ: 10.742.243/0001-59",
    "IMOBILIARIOS LTDA",
    "5. Observações",
    "TRT de Geo Urbano do imóvel objeto da MATRÍCULA N.º 8.716 (Mat. originaria do loteamento).",
]


def test_parse_art_trt():
    d = EX.parse_art_trt(_mk_pdf(_ART))
    assert d["trt_numero"] == "CFT2606068376"
    assert d["proprietario_nome"] == "AJM CONSTRUTORA E INCORPORADORA DE EMPREENDIMENTOS IMOBILIARIOS LTDA"
    assert d["proprietario_doc"] == "10.742.243/0001-59"
    assert d["matricula"] == "8.716"
    assert d["proprietario_telefone"] == "(99) 9125-4865"
    assert d["proprietario_endereco"] == "RUA SÃO RAIMNUNDO, nº 527, CENTRO, AÇAILÂNDIA - MA, CEP 65930000"


def test_extrair_georref_orquestra():
    out = EX.extrair_georref(_mk_pdf(_COORD), _mk_pdf(_SIT), _mk_pdf(_ART))
    assert out["bairro"] == "Residencial Ouro Verde"
    assert len(out["vertices"]) == 4
    assert out["quadra_dados"]["formato"] == "retangular"
    assert len(out["quadra_dados"]["vias"]) == 4
    assert out["art"]["proprietario_doc"] == "10.742.243/0001-59"
    assert out["art"]["trt_numero"] == "CFT2606068376"
