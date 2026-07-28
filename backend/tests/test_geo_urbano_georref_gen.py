# Testes da Fase 6 (Inc 2 — geradores): peças (memoriais/quadro/mapa/planta/ART/
# apresentação), capa configurável e dossiê montado pela composição.
import io

import pytest
from pypdf import PdfReader

from services.geo_urbano import georref_urbano as GU6
from services.geo_urbano.generators import georref_urbano_gen as GEN


def _proj():
    """Modelo REAL de referência: QD04 LT20 — Residencial Ouro Verde, Açailândia/MA."""
    return {
        "id": "p1", "user_id": "u", "numero": "URB-2026-0009",
        "denominacao_imovel": "Lote nº 20 da Quadra nº 04 — Residencial Ouro Verde",
        "tipo_servico": "georref_urbano", "tema": "prime_i",
        "finalidade": "regularizacao_municipal",
        "municipio": "Açailândia", "uf": "MA", "bairro": "Residencial Ouro Verde",
        "loteamento": "Residencial Ouro Verde", "quadra": "04", "lote_resultante": "20",
        "endereco": "Rua Fernando Pessoa",
        "cmi_resultante": "046.0004.0020.0001", "cmi_controle": "201",
        "area_calculada_m2": 300.0, "perimetro_m": 74.0,
        "memoriais_selecionados": ["MD-PER", "MD-SIT", "MD-SUC", "MD-CON"],
        "possui_benfeitoria": True,
        "areas_construidas": [{"descricao": "Térreo", "area": 90.0}, {"descricao": "Superior", "area": 70.0}],
        "art_trt": {"tipo": "TRT", "numero": "CFT2606068376", "data": "28/07/2026", "valor": 1000.0,
                    "observacao": "Levantamento cadastral / memorial descritivo."},
        "quadra_dados": {"modo_planta": "gerada", "formato": "retangular",
                         "vias": [{"nome": "Rua Fernando Pessoa", "posicao": "S"},
                                  {"nome": "Avenida Contorno", "posicao": "O"},
                                  {"nome": "Avenida Rafael de Almeida", "posicao": "N"},
                                  {"nome": "Avenida Adelino Andrade", "posicao": "L"}],
                         "esquina": {"is_esquina": False, "distancia_m": 48.0, "logradouro": "Avenida Contorno"}},
        "responsavel_tecnico": {"nome": "José Romário Pinto Bezerra", "formacao": "Técnico em Agrimensura",
                                "conselho": "CFT/MA 01209185369", "credenciamento_incra": "FQNS"},
        "partes": [{"papel": "requerente", "tipo_pessoa": "juridica",
                    "razao_social": "AJM CONSTRUTORA E INCORPORADORA DE EMPREENDIMENTOS IMOBILIÁRIOS LTDA",
                    "cnpj": "10.742.243/0001-59"}],
        "levantamento": {"equipamento": "GNSS RTK", "metodo": "PPP",
                         "sistema": "SIRGAS 2000 / UTM 23S", "meridiano_central": "45°00'", "fuso": "-23",
                         "data_levantamento": "2025-07-28"},
        "vertices": [
            {"ordem": 1, "de": "P1", "coord_n": 9450853.30, "coord_e": 224062.78, "feicao": "Muro",
             "confrontante_lado": "Lote nº 19", "azimute": "122°56'38\"", "distancia_m": 25.0},
            {"ordem": 2, "de": "P2", "coord_n": 9450839.70, "coord_e": 224083.76, "feicao": "Muro",
             "confrontante_lado": "RUA FERNANDO PESSOA", "azimute": "212°56'38\"", "distancia_m": 12.0},
            {"ordem": 3, "de": "P3", "coord_n": 9450829.63, "coord_e": 224077.23, "feicao": "Muro",
             "confrontante_lado": "Lote nº 21", "azimute": "302°56'38\"", "distancia_m": 25.0},
            {"ordem": 4, "de": "P4", "coord_n": 9450843.23, "coord_e": 224056.25, "feicao": "Muro",
             "confrontante_lado": "Lote nº 05", "azimute": "32°56'31\"", "distancia_m": 12.0},
        ],
        "composicao": GU6.composicao_default("financiamento_bancario"),
    }


def _pages(pdf_bytes):
    assert pdf_bytes[:5] == b"%PDF-"
    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)


def _text(pdf_bytes):
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf_bytes)).pages)


@pytest.mark.parametrize("tipo", [
    "apresentacao", "memorial_perimetrico", "memorial_situacao", "memorial_sucinto",
    "memorial_area_construida", "quadro_vertices", "mapa_lote", "planta_quadra", "art_trt",
])
def test_cada_peca_gera_pdf_valido(tipo):
    data = GEN.gerar_peca(tipo, _proj(), "prime_i")
    assert _pages(data) >= 1


@pytest.mark.parametrize("tema", ["prime_i", "prime_ii", "tradicional"])
def test_memorial_perimetrico_nos_3_temas(tema):
    assert _pages(GEN.memorial_perimetrico(_proj(), tema)) >= 1


def test_peca_desconhecida_levanta():
    with pytest.raises(ValueError):
        GEN.gerar_peca("inexistente", _proj(), "prime_i")


def test_descricao_perimetro_formato_modelo_real():
    txt = GEN.descricao_perimetro(_proj())
    assert txt.startswith("Inicia-se a descrição deste perímetro no vértice P1, de coordenadas "
                          "N 9.450.853,30m e E 224.062,78m;")
    assert "Muro;" in txt
    assert "segue confrontando com Lote nº 19, com os seguintes azimutes e distâncias: 122°56'38\" e 25,00 m até o vértice P2" in txt
    assert "ponto inicial da descrição deste perímetro." in txt
    assert "Meridiano Central nº 45°00', fuso -23, tendo como datum o SIRGAS2000" in txt
    assert "Posicionamento por Ponto Preciso (PPP)" in txt


def test_descricao_situacao_formato_modelo_real():
    txt = GEN.descricao_situacao(_proj())
    assert txt.startswith("Um TERRENO nesta cidade de Açailândia, Estado do Maranhão, "
                          "Frente para a RUA FERNANDO PESSOA")
    assert "denominado Lote nº 20 da Quadra nº 04 – RESIDENCIAL OURO VERDE" in txt
    assert "medindo de Frente 12,00 m (doze metros) com a RUA FERNANDO PESSOA" in txt
    assert "Formato do lote retangular." in txt
    assert ("Situado na quadra formada pelas seguintes confrontantes: Rua Fernando Pessoa, "
            "Avenida Contorno, Avenida Rafael de Almeida e Avenida Adelino Andrade.") in txt
    assert "Distante da esquina com a Avenida Contorno, medindo 48,00 m (quarenta e oito metros)." in txt


def test_md_sit_leva_superintendencia_so_em_municipal():
    # regularização municipal → linha da Superintendência presente
    assert "SUPERINTEND" in _text(GEN.memorial_situacao(_proj(), "prime_i")).upper()
    proj = _proj(); proj["finalidade"] = "financiamento_bancario"
    assert "SUPERINTEND" not in _text(GEN.memorial_situacao(proj, "prime_i")).upper()


def test_capa_png_e_pdf():
    proj = _proj()
    png = GEN.capa_georref_png(proj, None, None, "prime_i")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert _pages(GEN.capa_georref_pdf(proj, None, None, "tradicional")) == 1


def test_dossie_banco_tem_capa_e_sumario():
    # preset BANCO liga capa+sumario → dossiê traz capa (pág 1) + sumário + seções
    proj = _proj()
    data = GEN.gerar_dossie(proj, {}, "prime_i")
    n = _pages(data)
    # capa(1) + sumário(≥1) + mapa_lote + quadro + MD-PER + MD-SIT + ART ⇒ várias páginas
    assert n >= 6


def test_dossie_simplificado_sem_capa_menos_paginas():
    proj = _proj()
    proj["composicao"] = {
        "preset": "SIMPLIFICADO", "pecas": GU6.preset_pecas("SIMPLIFICADO"),
        "ordem": list(GU6.PECAS), "definicao_capa": "Para fins de localização e situação",
    }
    pecas = GU6.pecas_no_dossie(proj)
    assert "capa" not in pecas and "sumario" not in pecas
    assert set(pecas) <= {"mapa_lote", "memorial_perimetrico", "art_trt"}
    simplificado = GEN.gerar_dossie(proj, {}, "prime_i")
    assert simplificado[:5] == b"%PDF-"
    banco = GEN.gerar_dossie(_proj(), {}, "prime_i")
    # SIMPLIFICADO não tem capa+sumário → menos páginas que o BANCO
    assert _pages(simplificado) < _pages(banco)


def test_timbre_renderiza_no_cabecalho_quando_ativo():
    proj = _proj()
    # sem timbre injetado → cabeçalho não traz o contato
    assert "consultoriaromatec" not in _text(GEN.memorial_perimetrico(proj, "prime_i")).lower()
    proj["_timbre"] = {
        "empresa": "ROMATEC CONSULTORIA TOTAL", "telefone": "(99) 9 9181-1246",
        "email": "romatec.cad@hotmail.com", "site": "www.consultoriaromatec.com.br",
        "endereco": "Rua São Paulo, 161 - Centro Açailândia - MA CEP 65930-000",
        "rt_nome": "José Romário Pinto Bezerra", "rt_titulo": "Técnico em Agrimensura",
        "rt_conselho": "CFT/MA 01209185369", "rt_incra": "FQNS",
    }
    txt = _text(GEN.memorial_perimetrico(proj, "prime_i"))
    assert "ROMATEC CONSULTORIA TOTAL" in txt
    assert "consultoriaromatec" in txt.lower()
    assert "Rua São Paulo, 161" in txt


def test_qualificacao_requerente_completa():
    proj = _proj()
    proj["proprietario_natureza"] = "pj"
    proj["partes"] = [{"papel": "requerente", "tipo_pessoa": "juridica",
                       "razao_social": "AJM CONSTRUTORA LTDA", "cnpj": "10.742.243/0001-59",
                       "endereco": "RUA SÃO RAIMUNDO, nº 527, CENTRO, AÇAILÂNDIA - MA, CEP 65930000",
                       "telefone": "(99) 9125-4865"}]
    q = GEN.qualificacao_requerente(proj)
    assert "AJM CONSTRUTORA LTDA" in q
    assert "CNPJ sob o nº 10.742.243/0001-59" in q
    assert "com sede na RUA SÃO RAIMUNDO" in q
    assert "telefone (99) 9125-4865" in q
    # a apresentação usa a qualificação (pypdf quebra a linha → normaliza e checa tokens)
    import re as _re
    apr = _re.sub(r"\s+", " ", _text(GEN.apresentacao(proj, "prime_i")))
    assert "RAIMUNDO" in apr and "CNPJ" in apr
