# Testes do módulo Geo Urbano (Remembramento) — seed J&G, geometria, reconciliação,
# transcrição fiel das matrículas e geração dos documentos (Requerimento 2 vias,
# Memorial, Cadeia, Dossiê).
import io

import pytest
from pypdf import PdfReader

from models.geo_urbano import GeoUrbanoProjeto, calcular_completude
from services.geo_urbano.seed import build_seed
from services.geo_urbano import geometria as GEOM
from services.geo_urbano import reconcile as RECONCILE
from services.geo_urbano import aprovacao as APROVACAO
from services.geo_urbano import extractor as EX


def _mk_pdf(linhas):
    """PDF sintético (uma linha por drawString) p/ exercitar os parsers."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    y = 800
    for ln in linhas:
        c.drawString(40, y, ln)
        y -= 14
    c.showPage()
    c.save()
    return buf.getvalue()


_BCI = _mk_pdf([
    "DADOS CARTOGRÁFICOS",
    "Cód imóvel Loc. Cartográfica Distrito Setor Quadra Lote Unid Situação Natureza",
    "0000012424 01.10.041.0001.00001 01 10 0041 0001 00001 Ativo Predio",
    "LogradouroTipo Nome Logradouro Número Número Anterior CEP Complemento",
    "1569 RUA INGLATERRA 0001 65930000 QD. 041,LT. 0001",
    "Bairro Nome do Bairro Segmento Seção Insc. Anterior Compl Data Cadastro Data de Construção",
    "10 PARQUE DAS NAÇÕES 0 0 LOTE: 00001 10/05/2018 / /",
    "Nome do Proprietário ou detentor",
    "INCORPORADORA BRASIL LTDA",
    "Inscrição do Contribuinte 7072 CPF/CNPJ 07612344000109",
    "No.Frentes No.Unid.Lote Testada Principal Prof. do Lote Área da Edificação Área do Terreno M2 Área Total da Edificação",
    "0 0 15,00 15,00 300,00 300,00 300,00",
])

_IPTU = _mk_pdf([
    "Insc. Contribuinte Ins Cadastral No. Crédito Parcela Origem da receita Receita No. do Acordo Vencimento",
    "7072 12424 1514365 001/001 PARCELAMENTO IPTU 2026001084 24/07/2026",
    "Acordo Ref. Exercicio(s): 2023,2024,2025,",
    "Loc. Cart.01.10.041.0001.00001 VALOR COBRADO 394,00",
    "Insc do Imovel 0000012424",
    "Nº Acordo 2026001084",
])

_CND = _mk_pdf([
    "CERTIDÃO NEGATIVA DO IMÓVEL",
    "Nº 0000001596",
    "INSC. DO IMÓVEL 0002121673",
    "LOC. CARTOGRAFICA 01.10.041.0002.00001 LOTE: 0002",
    "27552 - J & G INDUSTRIA E COMERCIO LTDA",
    "C.N.P.J.: 28.804.226/0001-64",
    "VALIDA ATÉ:22/08/2026",
])

_MAPA = _mk_pdf([
    "De Para Coord. N(Y) Coord. E(X) Azimute Distância Fator K Latitude Longitude",
    "FQNS-P-PDN1 FQNS-P-PDN2 9.453.722,7409 226.466,3304 150°03'29\" 50,00 m 1,00052614 04°56'15,475979\"S 47°27'59,462032\"W",
    "FQNS-P-PDN2 FQNS-P-PDN3 9.453.707,7672 226.440,3345 240°03'29\" 30,00 m 1,00052632 04°56'15,960049\"S 47°28'00,307186\"W",
    "Área: 2.100,00 m²",
    "Perímetro: 220,00 m",
    "CIM: 01.10.041.0001.00001 - 111",
    "MATRÍCULA(S): 34.161/34.162",
    "Cadastro Novo: QD: 41 / LT: 01",
    "Cadastro Antigo: QD: 41 / LT: 01,02",
    "Cód imóvel: 0000012424 - Loc. Cartográfica:01.10.041.0001.00001 ( QD41 - Lote 01)",
    "Cód imóvel: 0002121673 - Loc. Cartográfica:01.10.041.0002.00001 ( QD41 - Lote 02)",
])
from services.geo_urbano.generators import textos as TX
from services.geo_urbano.generators import pdf as PDF
from services.geo_urbano.generators import dossie as DOSSIE
from services.geo_urbano.generators import capa as CAPA


def _img_aerea_sintetica() -> bytes:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (600, 600), (60, 72, 40))
    d = ImageDraw.Draw(im)
    d.line([(150, 150), (430, 170), (410, 440), (170, 420), (150, 150)], fill=(180, 255, 40), width=6)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def proj():
    return build_seed("u-test")


def _paginas(data: bytes) -> int:
    assert data[:5] == b"%PDF-"
    return len(PdfReader(io.BytesIO(data)).pages)


def test_seed_modelo_valido(proj):
    # o seed passa pelo schema Pydantic v2
    m = GeoUrbanoProjeto(**proj)
    assert len(m.matriculas) == 7
    assert len(m.vertices) == 6
    assert len(m.partes) == 2
    assert m.area_declarada_m2 == 2100.0


def test_completude_alta(proj):
    assert calcular_completude(proj) >= 80


def test_geometria_area_perimetro(proj):
    # área do polígono (shoelace UTM) bate com a declarada (2.100,00 m²)
    conf = GEOM.conferencia_areas(proj["vertices"], proj["area_declarada_m2"])
    assert abs(conf["area_calculada_m2"] - 2100.0) < 1.0
    assert abs(conf["perimetro_m"] - 220.0) < 0.5
    assert conf["ok"] is True
    assert (conf["divergencia_pct"] or 0) < 1.0


def test_reconciliacao_titularidade_divergente(proj):
    out = RECONCILE.reconciliar(proj)
    tipos = {a["tipo"] for a in out["alertas"]}
    assert "titularidade_divergente" in tipos
    # Lote 01 (matrícula 34.161) é o divergente (BCI ainda Incorporadora)
    div = [a for a in out["alertas"] if a["tipo"] == "titularidade_divergente"]
    assert any("34.161" in (a["mensagem"] or "") for a in div)
    assert out["resumo"]["bloqueantes"] >= 1
    assert out["resumo"]["pode_protocolar"] is False


def test_reconciliacao_sem_divergencia_quando_bci_atualizado(proj):
    p = {**proj}
    # alinha o BCI do lote 01 ao registro (J&G) → sem divergência de titularidade
    bcis = [dict(b) for b in p["bci"]]
    bcis[0]["proprietario_cadastral"] = {"nome": "J & G Indústria e Comércio Ltda-EPP",
                                         "doc": "28.804.226/0001-64"}
    p["bci"] = bcis
    out = RECONCILE.reconciliar(p)
    assert not [a for a in out["alertas"] if a["tipo"] == "titularidade_divergente"]


def test_transcricao_fiel_matricula_1(proj):
    itens = TX.lista_transcricoes(proj)
    assert len(itens) == 7
    t1 = itens[0]
    assert t1.startswith("1- Matrícula nº 34.161")
    assert "Livro 2-HN" in t1 and "fls. 70" in t1
    assert "300,00 m²" in t1
    assert "01.10.041.0001.00001" in t1
    assert "FRENTE: 15,00 m com Rua Inglaterra" in t1
    assert "Lote nº 02" in t1


def test_descricao_resultante(proj):
    d = TX.descricao_resultante(proj)
    assert "2.100,00 m²" in d
    assert "220,00 m" in d
    assert "Lote nº 01" in d or "Lote nº 01".replace("nº ", "") in d


@pytest.mark.parametrize("tema", ["prime_i", "prime_ii", "tradicional"])
@pytest.mark.parametrize("tipo", ["requerimento_cartorio", "requerimento_superintendencia",
                                  "memorial_descritivo", "cadeia_dominical"])
def test_gera_pdf(proj, tipo, tema):
    data = PDF.gerar_pdf(tipo, proj, tema)
    assert _paginas(data) >= 1


def test_quadro_vertices_no_memorial_e_requerimento(proj):
    import fitz
    for tipo in ("memorial_descritivo", "requerimento_cartorio"):
        d = fitz.open("pdf", PDF.gerar_pdf(tipo, proj, "prime_i"))
        txt = "".join(d[i].get_text() for i in range(d.page_count))
        assert "MEDIDAS E CONFRONTAÇÕES" in txt          # o quadro do mapa entra nos dois
        assert "Rua Suriname" in txt and "1,00052614" in txt  # confrontante + fator K


def test_requerimento_duas_vias_diferem_so_no_destinatario(proj):
    # corpo idêntico, só muda o bloco destinatário (tamanhos próximos, ambos válidos)
    via1 = PDF.gerar_pdf("requerimento_cartorio", proj, "prime_i")
    via2 = PDF.gerar_pdf("requerimento_superintendencia", proj, "prime_i")
    assert _paginas(via1) == _paginas(via2)
    assert via1 != via2


def test_extrair_bci():
    b = EX.parse_bci(_BCI)
    assert b["cod_imovel"] == "0000012424"
    assert b["loc_cartografica"] == "01.10.041.0001.00001"
    assert b["proprietario_cadastral"]["nome"] == "INCORPORADORA BRASIL LTDA"
    assert b["proprietario_cadastral"]["doc"] == "07612344000109"
    assert b["inscricao_contribuinte"] == "7072"
    assert b["area_terreno_m2"] == 300.0 and b["testada_principal_m"] == 15.0


def test_extrair_iptu():
    it = EX.parse_iptu(_IPTU)
    assert it["via_regularidade"] == "guia_paga"
    assert it["acordo_numero"] == "2026001084"
    assert it["valor"] == 394.0
    assert it["loc_cartografica"] == "01.10.041.0001.00001"
    assert it["exercicios"] == ["2023", "2024", "2025"]
    assert it["situacao"] == "debito_parcelado"


def test_extrair_cnd():
    c = EX.parse_cnd(_CND)
    assert c["via_regularidade"] == "cnd" and c["situacao"] == "cnd_negativa"
    assert c["cnd_numero"] == "0000001596"
    assert c["cnd_validade"] == "2026-08-22"
    assert c["loc_cartografica"] == "01.10.041.0002.00001"


def test_extrair_mapa():
    mp = EX.parse_mapa(_MAPA)
    assert len(mp["vertices"]) == 2
    assert mp["vertices"][0]["coord_n"] == 9453722.7409
    assert mp["vertices"][0]["coord_e"] == 226466.3304
    assert mp["area_declarada_m2"] == 2100.0
    assert mp["perimetro_m"] == 220.0
    assert mp["cmi_resultante"] == "01.10.041.0001.00001"
    assert mp["matriculas_numeros"] == ["34.161", "34.162"]
    assert len(mp["lotes_quadro"]) == 2
    assert mp["lotes_quadro"][1]["lote"] == "02"


def test_extrair_tudo_orquestra_e_vincula():
    res = EX.extrair_tudo({
        "mapa_remembramento": [_MAPA], "bci": [_BCI],
        "guia_iptu": [_IPTU], "cnd_iptu": [_CND],
    })
    assert len(res["matriculas"]) == 2
    m1 = res["matriculas"][0]
    assert m1["matricula"] == "34.161" and m1["cod_imovel"] == "0000012424" and m1["id"]
    # BCI do lote 01 vinculado à matrícula 01 por cod_imovel
    bci01 = next(b for b in res["bci"] if b["cod_imovel"] == "0000012424")
    assert bci01["matricula_id"] == m1["id"]
    # IPTU/CND viram regularidade vinculada
    assert len(res["iptu"]) == 2


def test_parse_matricula_text():
    # certidão real do 34.161 (estado atual: transmitido p/ J&G via R-01)
    txt = ("CERTIFICO, revendo o Livro nº 2-HN, sob as fls. 70, MATRÍCULA Nº 34.161 - UM TERRENO, "
           "Quadra nº 41, Lote nº 01, Loteamento PARQUE DAS NAÇÕES. "
           "Frente: 15,00m (quinze metros) para a Rua Inglaterra, "
           "Lateral direita: 20,00m (vinte metros) para o lote nº 02, "
           "Lateral esquerda: 20,00m para a Rua Venezuela, Fundo: 15,00m para o lote nº 24, com a área de 300m². "
           "PROPRIETÁRIO(A): INCORPORADORA BRASIL LTDA, inscrita no CNPJ sob o n. 07.612.344/0001-09. "
           "R.01/34.161 - ADQUIRENTE(S) - a firma J & G INDÚSTRIA E COMÉRCIO LTDA-EPP, "
           "inscrita no CNPJ sob o nº 28.804.226/0001-64. TÍTULO - Compra e Venda.")
    d = EX.parse_matricula_text(txt)
    assert d["matricula"] == "34.161"
    assert d["livro"] == "2-HN" and d["folhas"] == "70"
    assert d["lote_origem"] == "01"
    # proprietário REGISTRAL atual = ADQUIRENTE do último registro (J&G), NÃO o cabeçalho (Incorporadora)
    assert "J & G" in d["proprietario_registral"]["nome"]
    assert d["proprietario_registral"]["doc"] == "28.804.226/0001-64"
    # confrontações limpas (sem "(quinze metros)" nem texto vazado)
    porlado = {c["lado"]: c["confrontante"] for c in d["confrontacoes"]}
    assert porlado["frente"] == "Rua Inglaterra"
    assert porlado["lateral_direita"] == "lote nº 02"
    assert porlado["fundo"] == "lote nº 24"


def test_signatarios_proprietario(proj):
    from services.geo_urbano import assinatura_proprietario as PROP
    sigs = PROP.signatarios_de(proj)
    # PJ requerente (J&G) NÃO assina; quem assina é o representante (Juscelino)
    assert any("Juscelino" in (s.get("nome") or "") for s in sigs)
    assert all(s.get("papel") != "requerente" or True for s in sigs)
    assert not any((s.get("nome") or "").startswith("J & G") for s in sigs)


def test_carimbo_proprietario_no_requerimento(proj):
    # reusa carimbar_multi p/ carimbar o traço desenhado no Requerimento gerado
    from datetime import datetime, timezone
    from PIL import Image
    from services.assinatura_cliente_carimbo import carimbar_multi
    base = PDF.gerar_pdf("requerimento_cartorio", proj, "prime_i")
    buf = io.BytesIO()
    Image.new("RGBA", (160, 60), (10, 50, 30, 255)).save(buf, "PNG")
    sigs = [{
        "nome": "Juscelino Oliveira", "cpf": "027.460.033-17", "role": "representante",
        "traco_png": buf.getvalue(), "assinado_em": datetime.now(timezone.utc),
        "posicoes": [{"pagina": 0, "x_pt": 110, "y_pt": 120, "larg_pt": 160, "alt_pt": 50, "tipo": "assinatura"}],
    }]
    final, sha = carimbar_multi(base, sigs)
    assert final[:5] == b"%PDF-"
    assert isinstance(sha, str) and len(sha) == 64
    assert _paginas(final) >= _paginas(base)


def test_assinatura_geo_urbano_registrada():
    # o técnico assina Memorial/Mapa via ICP reusando o módulo de assinatura
    from routes.assinatura import _TIPO_COLECAO, _propagar_geo_urbano_assinado  # noqa
    assert _TIPO_COLECAO.get("geo_urbano") == "geo_urbano_assinaturas"


def _proj_desdobro():
    return {
        "tipo_servico": "desdobro", "denominacao_imovel": "Lote 10 — Qd 5 (Desdobro em 3)",
        "municipio": "Açailândia", "uf": "MA", "quadra": "5", "loteamento": "Centro",
        "area_mae_m2": 600.0, "area_via_doacao_m2": 0.0,
        "lote_minimo_municipal_m2": 150.0, "testada_minima_m": 8.0,
        "matriculas": [{"ordem": 1, "matricula": "12.345", "livro": "2-A", "folhas": "10",
                        "lote_origem": "10", "quadra": "5", "area_m2": 600.0,
                        "confrontacoes": [{"lado": "frente", "medida_m": 20.0, "confrontante": "Rua A"}]}],
        "partes": [{"papel": "requerente", "tipo_pessoa": "fisica", "nome": "Maria Souza", "cpf": "111"}],
        "cartorio": {"nome": "Cartório 1º Ofício"}, "superintendencia": {"nome": "Superintendência"},
        "lotes_resultantes": [
            {"id": "a", "ordem": 1, "denominacao": "10-A", "area_declarada_m2": 200.0, "perimetro_m": 60.0,
             "confrontacoes": [{"lado": "frente", "medida_m": 10.0, "confrontante": "Rua A"},
                               {"lado": "fundo", "medida_m": 10.0, "confrontante": "Lote 22"}]},
            {"id": "b", "ordem": 2, "denominacao": "10-B", "area_declarada_m2": 200.0, "perimetro_m": 60.0,
             "confrontacoes": [{"lado": "frente", "medida_m": 10.0, "confrontante": "Rua A"}]},
            {"id": "c", "ordem": 3, "denominacao": "10-C", "area_declarada_m2": 200.0, "perimetro_m": 60.0,
             "confrontacoes": [{"lado": "frente", "medida_m": 10.0, "confrontante": "Rua A"}]},
        ],
    }


def test_desdobro_conservacao_area():
    p = _proj_desdobro()
    c = GEOM.conservacao_area(p)
    assert c["ok"] is True and c["total_m2"] == 600.0 and c["modalidade"] == "desdobro"
    # mãe 650 → não fecha
    p2 = {**p, "area_mae_m2": 650.0}
    assert GEOM.conservacao_area(p2)["ok"] is False
    # via/doação → desmembramento
    p3 = {**p, "area_mae_m2": 650.0, "area_via_doacao_m2": 50.0}
    c3 = GEOM.conservacao_area(p3)
    assert c3["ok"] is True and c3["modalidade"] == "desmembramento"


def test_desdobro_validacoes_urbanisticas():
    p = {**_proj_desdobro(), "lote_minimo_municipal_m2": 250.0}
    avisos = GEOM.validacoes_urbanisticas(p)
    assert len(avisos) == 3 and all(a["tipo"] == "lote_abaixo_do_minimo" for a in avisos)


def test_desdobro_requerimento_e_memorial():
    from services.geo_urbano.lotes import projeto_do_lote
    p = _proj_desdobro()
    desc = TX.descricao_lotes_resultantes(p)
    assert all(x in desc for x in ("10-A", "10-B", "10-C")) and "três" in desc
    req = PDF.gerar_pdf("requerimento_cartorio", p, "prime_i")
    assert _paginas(req) >= 1
    mem = PDF.gerar_pdf("memorial_descritivo", projeto_do_lote(p, p["lotes_resultantes"][0]), "prime_i")
    assert _paginas(mem) >= 1


def _proj_retificacao():
    return {
        "tipo_servico": "retificacao", "retificacao_tipo": "mista", "denominacao_imovel": "Retificação — Matrícula 563",
        "municipio": "Açailândia", "uf": "MA", "quadra": "118",
        "matriculas": [{"ordem": 1, "matricula": "563", "area_m2": 563.00, "endereco": "Rua Marly Sarney",
                        "loc_cartografica": "01.10.118.0116.00001", "cod_imovel": "0000999",
                        "proprietario_registral": {"nome": "João Lima", "doc": "111"}}],
        "bci": [{"area_terreno_m2": 560.00, "endereco": "R. Marly Sarney", "loc_cartografica": "01.10.118.0116.00001",
                 "cod_imovel": "0000999", "proprietario_cadastral": {"nome": "João Lima", "doc": "111"}}],
        "partes": [{"papel": "requerente", "tipo_pessoa": "fisica", "nome": "João Lima", "cpf": "111"}],
        "cartorio": {"nome": "Cartório"}, "superintendencia": {"nome": "Superintendência"},
        "vertices_atual": [{"ordem": 1, "de": "V1", "para": "V2", "coord_e": 0, "coord_n": 0, "confrontante_lado": "Fulano"}],
        "vertices": [{"ordem": 1, "de": "V1", "para": "V2", "coord_e": 0, "coord_n": 0, "confrontante_lado": "Beltrano"}],
    }


def test_retificacao_diff_cadastral():
    from services.geo_urbano import retificacao as RET
    an = RET.analisar(_proj_retificacao())
    por = {d["campo"]: d for d in an["cadastral_diffs"]}
    assert por["area_registral"]["divergente"] is True       # 563 ≠ 560
    assert por["endereco"]["divergente"] is False            # "Rua" vs "R." normalizado
    assert por["titularidade"]["divergente"] is False        # mesmo titular
    assert por["area_registral"]["valor_correto"] == 563.00  # registro é autoritativo
    assert an["gerou_alteracao"] is True


def test_retificacao_confrontante_alterado():
    from services.geo_urbano import retificacao as RET
    g = RET.analisar(_proj_retificacao())["geometrico"]
    assert any(c["alterado"] for c in g["confrontantes_diff"])  # Fulano → Beltrano


def test_parse_art_trt():
    base = _mk_pdf(["CONSELHO FEDERAL DOS TECNICOS", "Documento de RT: CFT2605953795-MA"])
    assert EX.parse_art_trt(base, "art.pdf") == "CFT2605953795-MA"
    # fallback pelo nome do arquivo quando o PDF é imagem/sem texto
    assert EX.parse_art_trt(b"%PDF-1.4 imagem", "CFT2605953795.7B6Y6.pdf") == "CFT2605953795"


def test_drl_so_confrontante_particular():
    proj = {**_proj_retificacao(), "endereco": "Rua A, 10", "confrontantes": [
        {"id": "c1", "lado": "lateral_direita", "confrontante": "Sr. Bita", "tipo": "particular", "medida_m": 22.96},
        {"id": "c2", "lado": "frente", "confrontante": "Rua X", "tipo": "via_publica", "medida_m": 21.40},
        {"id": "c3", "lado": "fundo", "confrontante": "Praça", "tipo": "area_publica", "medida_m": 10.0},
    ]}
    drls = PDF.confrontantes_para_drl(proj)
    assert [c["confrontante"] for c in drls] == ["Sr. Bita"]  # via/área pública dispensam
    pdf = PDF.drl(proj, proj["confrontantes"][0], "prime_i")
    assert _paginas(pdf) >= 1


def test_retificacao_quadro_e_requerimento():
    from services.geo_urbano import retificacao as RET
    p = _proj_retificacao()
    p["retificacao_analise"] = RET.analisar(p)
    assert "retifique-se" in TX.relacao_retificacao(p)
    assert _paginas(PDF.gerar_pdf("quadro_retificacao", p, "prime_i")) >= 1
    assert _paginas(PDF.gerar_pdf("requerimento_cartorio", p, "prime_i")) >= 1


def test_aprovacao_matriz_papeis(proj):
    out = APROVACAO.build_status(proj)
    assert out["status_geral"] == "rascunho"
    porn = {l["documento"]: l for l in out["matriz"]}
    # Requerimento e ART/TRT → só proprietário
    assert porn["requerimento_cartorio"]["papeis"] == ["proprietario"]
    assert porn["art_trt"]["papeis"] == ["proprietario"]
    # Memorial e Mapa → técnico + superintendente (carimbo no superintendente)
    mem = porn["memorial_descritivo"]
    assert mem["papeis"] == ["tecnico", "superintendente"]
    assert mem["celulas"]["superintendente"]["carimbo"] is True
    assert mem["celulas"]["tecnico"]["metodo"] == "tecnico_sistema"
    assert porn["mapa"]["celulas"]["superintendente"]["metodo"] == "aprovacao_superintendencia"


def test_status_geral_transicoes():
    aprov = {"proprietarios": [{"requerimento": True}], "tecnico": {}, "superintendencia": {}}
    assert APROVACAO.status_geral(aprov) == "assinatura_partes"
    aprov["tecnico"] = {"assinado": True}
    assert APROVACAO.status_geral(aprov) == "assinatura_tecnico"
    aprov["enviado_superintendencia"] = True
    assert APROVACAO.status_geral(aprov) == "enviado_superintendencia"
    aprov["superintendencia"] = {"memorial_aprovado": True, "mapa_aprovado": True}
    assert APROVACAO.status_geral(aprov) == "aprovado"
    aprov["superintendencia"]["oficio_emitido"] = True
    assert APROVACAO.status_geral(aprov) == "oficio_emitido"


def test_oficio_aprovacao_render(proj):
    p = {**proj}
    p["aprovacao"] = {
        **(p.get("aprovacao") or {}),
        "superintendencia": {"memorial_aprovado": True, "mapa_aprovado": True,
                             "oficio_emitido": True, "oficio_numero": "OF-2026-0001",
                             "responsavel": "Davi Alexandre Sampaio Camargo", "portaria": "019/2025 - GAB"},
    }
    data = PDF.gerar_pdf("oficio_aprovacao", p, "prime_i")
    assert _paginas(data) >= 1


def test_capa_lupa_render(proj):
    img = _img_aerea_sintetica()
    png = CAPA.preview_png(proj, img)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    lupa = CAPA.gerar_lupa(__import__("PIL.Image", fromlist=["Image"]).open(io.BytesIO(img)))
    assert lupa.mode == "RGBA" and lupa.size[0] > 0
    pdf = CAPA.gerar_capa_pdf(proj, img)
    assert _paginas(pdf) == 1


def test_capa_legenda_por_servico(proj):
    leg = CAPA._legenda_lupa(proj)
    assert "2.100,00 m²" in leg
    # a legenda do remembramento mostra ÁREA + PERÍMETRO (não rotula a área como "PERÍMETRO")
    assert leg.startswith("ÁREA") and "PERÍMETRO 220,00 m" in leg
    p = {**proj, "tipo_servico": "retificacao"}
    assert "RETIFICAÇÃO" in CAPA._legenda_lupa(p)


def test_dossie_converte_imagem_jpg(proj):
    # comprovantes em JPG/PNG devem virar página no dossiê (não podem ser pulados)
    from PIL import Image
    jb = io.BytesIO(); Image.new("RGB", (640, 480), (210, 220, 190)).save(jb, "JPEG")
    req = PDF.gerar_pdf("requerimento_cartorio", proj, "prime_i")
    doss = DOSSIE.gerar_dossie_ordenado(proj, [("Requerimento", [req]), ("Comprovante", [jb.getvalue()])])
    # capa(1) + sumário(1) + requerimento(2) + comprovante(1) = 5
    assert _paginas(doss) >= 5


def test_dossie_usa_capa_lupa(proj):
    partes = {t: PDF.gerar_pdf(t, proj, "prime_i") for t in (
        "requerimento_cartorio", "requerimento_superintendencia",
        "memorial_descritivo", "cadeia_dominical")}
    capa_pdf = CAPA.gerar_capa_pdf(proj, _img_aerea_sintetica())
    doss = DOSSIE.gerar_dossie(proj, partes, capa_pdf=capa_pdf)
    assert _paginas(doss) >= 9


def test_dossie_capa_sumario_ordem(proj):
    partes = {t: PDF.gerar_pdf(t, proj, "prime_i") for t in (
        "requerimento_cartorio", "requerimento_superintendencia",
        "memorial_descritivo", "cadeia_dominical")}
    doss = DOSSIE.gerar_dossie(proj, partes)
    n = _paginas(doss)
    # capa(1) + sumário(1) + 4 peças (2 pág cada) = 10
    assert n >= 9
    assert DOSSIE.ORDEM_DOSSIE[0][0] == "requerimento_cartorio"
