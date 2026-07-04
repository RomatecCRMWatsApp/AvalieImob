# Testa a importação de uma NFS-e já expedida (PDF SpeedGov/Açailândia) → doc FLAT + re-tematização.
import os

import pytest

from services.nfse.danfse_import import parse_nfse_pdf, ImportacaoNFSeError

_FIX = os.path.join(os.path.dirname(__file__), "fixtures", "nfse_speedgov_62.pdf")


def _fixture_bytes():
    with open(_FIX, "rb") as f:
        return f.read()


@pytest.mark.skipif(not os.path.exists(_FIX), reason="fixture do PDF ausente")
def test_parse_nfse_62_campos_principais():
    r = parse_nfse_pdf(_fixture_bytes())
    d = r["doc"]
    assert d["numero_nfse"] == "0000000062"
    assert d["serie"] == "ELETRÔNICA"
    assert d["data_geracao"] == "04/07/2026"
    assert d["competencia"] == "JUL/2026"
    assert d["numero_rps"] == "0"
    assert d["dps_substituida"] == "0"
    assert d["local_prestacao"] == "AÇAILÂNDIA-MA"
    assert d["optante_simples"] == "NÃO"
    assert d["chave_acesso"] == "21000551217261987000109000000000006226077434050989"


@pytest.mark.skipif(not os.path.exists(_FIX), reason="fixture do PDF ausente")
def test_parse_nfse_62_prestador_tomador():
    d = parse_nfse_pdf(_fixture_bytes())["doc"]
    assert d["prest_razao"] == "J R P BEZERRA LTDA"
    assert d["prest_fantasia"] == "ROMATEC CONSULTORIA TOTAL"
    assert d["prest_cnpj"] == "17261987000109"
    assert d["prest_im"] == "26800"
    assert d["prest_uf"] == "MA"
    assert d["prest_cidade"] == "Açailândia"
    assert d["prest_cep"] == "65930000"
    assert d["prest_fone"] == "9991811246"
    assert "QUADRA 104" in d["prest_endereco"]
    assert d["tom_razao"] == "CEARÁ DISTRIBUIDORA DE ALIMENTOS LTDA"
    assert d["tom_email"] == "contabilidade@cearaalimentos.com"
    assert d["tom_cnpj"] == "07133563000105"
    assert "BR 010" in d["tom_endereco"]


@pytest.mark.skipif(not os.path.exists(_FIX), reason="fixture do PDF ausente")
def test_parse_nfse_62_valores_e_discriminacao():
    d = parse_nfse_pdf(_fixture_bytes())["doc"]
    assert d["valor_servico"] == "8.500,00"
    assert d["aliquota_iss"] == "2,0000"
    assert d["deducao"] == "0,00"
    assert d["iss_retido_v"] == "0,00"
    assert d["iss_a_reter"] == "Não"
    assert d["cod_validacao"] == "74uklt59y2vc3wmrdnxbpaghjzo"
    assert d["link_consulta"] == "https://servicos2.speedgov.com.br/acailandia/"
    assert d["cod_atividade"].startswith("1701 / 0 / 821130001")
    assert "revestimento de piso sobreposto" in d["discriminacao"]
    assert "128,90 m" in d["discriminacao"]
    assert d["impressa_em"] == "04/07/26 12:40"
    assert d["hora_emissao"] == "12:40:29"


@pytest.mark.skipif(not os.path.exists(_FIX), reason="fixture do PDF ausente")
def test_calculo_recalcula_iss_do_doc_importado():
    from pdf.templates.danfse_base import calcular
    d = parse_nfse_pdf(_fixture_bytes())["doc"]
    c = calcular(d)
    assert c["base"] == 8500.0
    assert round(c["valor_iss"], 2) == 170.0
    assert round(c["valor_liquido"], 2) == 8500.0


@pytest.mark.skipif(not os.path.exists(_FIX), reason="fixture do PDF ausente")
def test_doc_importado_gera_danfse_nos_3_temas():
    from pdf.templates.registry import gerar_danfse
    d = parse_nfse_pdf(_fixture_bytes())["doc"]
    for tema in ("prime1", "prime2", "tradicional"):
        pdf = gerar_danfse(d, tema)
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 3000


@pytest.mark.skipif(not os.path.exists(_FIX), reason="fixture do PDF ausente")
def test_secao05_textos_nao_sobrepoem_no_render():
    """Regressão: a col. do meio (Natureza/Código/Link/ISS a Reter) saía sobreposta ao rótulo.
    Agora rótulo e valor ficam em linhas separadas e os textos longos não são truncados."""
    import io
    import pdfplumber
    from pdf.templates.registry import gerar_danfse
    d = parse_nfse_pdf(_fixture_bytes())["doc"]
    for tema in ("prime1", "prime2", "tradicional"):
        pdf = gerar_danfse(d, tema)
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            texto = "\n".join((pg.extract_text() or "") for pg in p.pages)
        # valores por extenso/URL/código chegam INTEIROS (não truncados pela sobreposição)
        assert "https://servicos2.speedgov.com.br/acailandia/" in texto, tema
        assert "74uklt59y2vc3wmrdnxbpaghjzo" in texto, tema
        assert "Tributada no Município" in texto, tema


def test_pdf_ilegivel_levanta_erro():
    with pytest.raises(ImportacaoNFSeError):
        parse_nfse_pdf(b"%PDF-1.4 not really a nfse tiny stub")
