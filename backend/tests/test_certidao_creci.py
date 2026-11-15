# @module tests.test_certidao_creci — leitura da validade da certidão do CRECI.
from services.certidao_creci import ler_texto

TEXTO = """CERTIDÃO DE REGULARIDADE PESSOA FÍSICA
CERTIDÃO EMITIDA EM: 15/11/2026 ÀS 13:57:54
CÓDIGO DE AUTENTICIDADE: FJTXPH
ESTA CERTIDÃO É VÁLIDA POR 30 DIAS -> ATÉ 15/12/2026
Certificamos ... JOSE ROMARIO PINTO BEZERRA, encontra-se devidamente inscrito(a) nesta Entidade sob o Nº 4705, desde 08/01/2014"""


def test_le_validade_emissao_codigo():
    r = ler_texto(TEXTO)
    assert r["validade"] == "2026-12-15"
    assert r["emitida_em"] == "2026-11-15"
    assert r["codigo"] == "FJTXPH"
    assert r["creci"] == "4705"


def test_sem_validade_usa_emissao_mais_30():
    r = ler_texto("CERTIDAO EMITIDA EM: 01/03/2026 AS 10:00")
    assert r["validade"] == "2026-03-31"


def test_validade_absurda_do_ocr_cai_para_emissao_mais_30():
    r = ler_texto("EMITIDA EM: 15/11/2026  VALIDA POR 30 DIAS -> ATE 15/12/2096")
    assert r["validade"] == "2026-12-15"


def test_texto_vazio():
    assert ler_texto("") == {}
