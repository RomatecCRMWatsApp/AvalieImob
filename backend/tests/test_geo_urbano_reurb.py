# REURB (Lei 13.465/2017 · Decreto 9.310/2018) — geração do Requerimento de
# Regularização Fundiária Urbana + peças que o requerente assina.
import io

from pypdf import PdfReader

from services.geo_urbano.generators import pdf as PDF
from services.geo_urbano import assinatura_proprietario as PROP


def _projeto_reurb(**over):
    p = {
        "tipo_servico": "reurb", "reurb_modalidade": "reurb_s",
        "denominacao_imovel": "Lote 09 — Quadra 06", "municipio": "Açailândia", "uf": "MA",
        "endereco": "Rua das Palmeiras", "area_declarada_m2": 360.0, "perimetro_m": 84.0,
        "nucleo_informal_nome": "Vila Nova", "data_ocupacao_nucleo": "2005-01-01",
        "legitimacao_fundiaria": True, "processo_municipal_num": "123/2026",
        "superintendencia": {"nome": "Superintendência de Habitação e Reg. Fundiária",
                             "orgao": "Prefeitura Municipal de Açailândia/MA"},
        "partes": [{"papel": "requerente", "tipo_pessoa": "fisica", "nome": "Fulano de Tal",
                    "cpf": "111.444.777-35"}],
        "matriculas": [], "vertices": [],
    }
    p.update(over)
    return p


def _texto(data):
    return "".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages)


def test_requerimento_reurb_render_reurb_s():
    data = PDF.gerar_pdf("requerimento_reurb", _projeto_reurb(), "prime_i")
    assert data[:4] == b"%PDF"
    txt = _texto(data)
    assert "13.465" in txt and "9.310" in txt      # fundamentos legais
    assert "REURB" in txt.upper()
    assert "Vila Nova" in txt                        # núcleo informal


def test_requerimento_reurb_e_sem_justificativa_matricula():
    # Reurb-E: NÃO gera a justificativa de ausência de matrícula (essa é da Reurb-S)
    txt = _texto(PDF.gerar_pdf("requerimento_reurb", _projeto_reurb(reurb_modalidade="reurb_e"), "prime_i"))
    assert "Interesse Espec" in txt or "REURB" in txt.upper()
    assert "arts. 13 e 42" not in txt


def test_pecas_e_signatarios_reurb():
    proj = _projeto_reurb()
    pecas = [k for k, _ in PROP.pecas_proprietario(proj)]
    assert "requerimento_reurb" in pecas and "art_trt" in pecas
    sigs = PROP.signatarios_de(proj)
    assert sigs and "requerimento_reurb" in sigs[0]["pecas"]   # requerente assina o req. de Reurb
