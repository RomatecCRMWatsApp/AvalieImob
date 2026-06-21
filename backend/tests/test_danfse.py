# Testes do DANFSe — content builder (cálculos) + cada renderer + registry.
import fitz  # PyMuPDF
import pytest

from pdf.templates.danfse_base import (
    calcular, montar, documento_exemplo_59, num, br, mascara_doc,
)
from pdf.templates.registry import (
    gerar_danfse, get_danfse_renderer, DANFSE_TEMPLATES_DISPONIVEIS,
)

TEMAS = ["prime1", "prime2", "tradicional"]
SECOES_ESPERADAS = ["PRESTADOR", "TOMADOR", "DISCRIMINAÇÃO", "TRIBUTOS FEDERAIS",
                    "CÁLCULO DO ISS", "IBS", "CONSTRUÇÃO CIVIL"]


# ── Helpers de formatação ────────────────────────────────────────────────────
def test_num_aceita_br_e_numero():
    assert num("17.500,00") == 17500.0
    assert num("350,00") == 350.0
    assert num(17500) == 17500.0
    assert num("") == 0.0


def test_br_formata_pt_br():
    assert br(17500) == "17.500,00"
    assert br(350) == "350,00"
    assert br(1234567.8) == "1.234.567,80"


def test_mascara_doc():
    assert mascara_doc("17261987000109") == "17.261.987/0001-09"
    assert mascara_doc("12345678901") == "123.456.789-01"


# ── Cálculos fiscais (caso real NFS-e 59) ────────────────────────────────────
def test_calculo_nfse_59():
    c = calcular(documento_exemplo_59())
    assert round(c["base"], 2) == 17500.00
    assert round(c["valor_iss"], 2) == 350.00      # 17.500 × 2%
    assert round(c["valor_liquido"], 2) == 17500.00
    assert c["aliquota_pct"] == 2.0


def test_calculo_com_deducao_desconto_e_retencao():
    doc = {"valor_servico": 10000, "deducao": 1000, "desc_incond": 500,
           "desc_cond": 200, "ret_fed": 300, "iss_retido_v": 0, "aliquota_iss": "5,00"}
    c = calcular(doc)
    assert c["base"] == 8500.0                    # 10000 - 1000 - 500
    assert c["valor_iss"] == 425.0                # 8500 × 5%
    assert c["valor_liquido"] == 9000.0           # 10000 - 500 - 200 - 300


def test_aliquota_aceita_fracao_ou_percentual():
    assert calcular({"valor_servico": 1000, "aliquota_iss": 0.02})["valor_iss"] == 20.0
    assert calcular({"valor_servico": 1000, "aliquota_iss": "2,0000"})["valor_iss"] == 20.0


# ── Montagem neutra ──────────────────────────────────────────────────────────
def test_montar_tem_7_secoes_na_ordem():
    conteudo = montar(documento_exemplo_59())
    ns = [s["n"] for s in conteudo["secoes"]]
    assert ns == ["01", "02", "03", "04", "05", "06", "07"]
    assert conteudo["secoes"][4]["tipo"] == "tricol"   # seção 05 é tri-coluna


# ── Renderers (cada tema) ────────────────────────────────────────────────────
@pytest.mark.parametrize("tema", TEMAS)
def test_renderer_gera_pdf_uma_pagina_com_7_secoes(tema):
    pdf = gerar_danfse(documento_exemplo_59(), tema)
    assert pdf[:5] == b"%PDF-", "saída deve ser um PDF"
    d = fitz.open(stream=pdf, filetype="pdf")
    assert d.page_count == 1, "DANFSe deve caber em 1 página"
    txt = "".join(d[i].get_text() for i in range(d.page_count)).upper()
    for sec in SECOES_ESPERADAS:
        assert sec in txt, f"seção ausente no tema {tema}: {sec}"
    assert "350,00" in txt and "17.500,00" in txt, "valores calculados ausentes"


def test_registry_temas_e_fallback():
    assert set(DANFSE_TEMPLATES_DISPONIVEIS) == {"prime1", "prime2", "tradicional"}
    # tema inválido cai no padrão (prime1) sem quebrar
    assert get_danfse_renderer("inexistente") is get_danfse_renderer("prime1")
    pdf = gerar_danfse(documento_exemplo_59(), "inexistente")
    assert pdf[:5] == b"%PDF-"
