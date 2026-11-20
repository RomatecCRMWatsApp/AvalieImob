import io
import logging

from services import log_redact as LR


def test_redige_dados_pessoais_e_segredos():
    t = LR.redigir(
        "Falha ao enviar p/ 5599991811246 e (99) 98515-7964, joao.silva@gmail.com, "
        "CPF 123.456.789-09, Bearer abcdefghijklmnop, "
        "GET /api/publico/assinatura-cliente/AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_- HTTP/1.1"
    )
    assert "5599991811246" not in t and "***1246" in t
    assert "98515-7964" not in t and "***7964" in t
    assert "joao.silva@" not in t and "j***@gmail.com" in t
    assert "123.456.789" not in t and "***.***.***-09" in t
    assert "abcdefghijklmnop" not in t
    assert "/assinatura-cliente/[token]" in t


def test_preserva_uuid_numeros_e_valores():
    t = LR.redigir("PTAM 3f2b8c1e-1d2a-4b3c-9e8f-0a1b2c3d4e5f valor R$ 272.666,02 área 2100.5 m² ano 2026")
    assert "3f2b8c1e-1d2a-4b3c-9e8f-0a1b2c3d4e5f" in t
    assert "272.666,02" in t and "2026" in t


def test_filtro_aplica_em_args_sem_quebrar_formatacao():
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.addFilter(LR.FiltroRedacao())
    lg = logging.getLogger("teste_redacao")
    lg.addHandler(h)
    lg.propagate = False
    lg.warning("Falha ao enviar WhatsApp p/ %s: %s", "5599991811246", "timeout")
    assert buf.getvalue().strip() == "Falha ao enviar WhatsApp p/ ***1246: timeout"
