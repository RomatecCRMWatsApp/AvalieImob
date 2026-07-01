# Testes do núcleo da assinatura DIGITADA (CPF + fontes manuscritas → PNG).
import io
from PIL import Image
from utils.cpf import validar_cpf, limpar_cpf, formatar_cpf, mascarar_cpf
from services import fontes_assinatura as FA


def test_validar_cpf():
    assert validar_cpf("529.982.247-25")          # válido conhecido
    assert validar_cpf("52998224725")
    assert not validar_cpf("111.111.111-11")       # repetidos
    assert not validar_cpf("123.456.789-00")       # DV errado
    assert not validar_cpf("123")                  # tamanho
    assert formatar_cpf("52998224725") == "529.982.247-25"
    assert mascarar_cpf("52998224725") == "***.982.247-**"
    assert limpar_cpf("529.982.247-25") == "52998224725"


def test_fontes_disponiveis():
    fs = FA.fontes_disponiveis()
    ids = {f["id"] for f in fs}
    assert {"DancingScript", "GreatVibes", "Sacramento", "Allura", "HomemadeApple", "Pacifico"} <= ids
    for f in fs:
        assert f["label"]                          # rótulo legível


def test_render_assinatura_png_todas_as_fontes():
    for f in FA.fontes_disponiveis():
        png = FA.render_assinatura_png("José Romário Pinto", f["id"])
        assert png[:8] == b"\x89PNG\r\n\x1a\n"     # é PNG
        im = Image.open(io.BytesIO(png))
        assert im.mode == "RGBA" and im.width > 40 and im.height > 20
        # tem pixels desenhados (alpha não-zero)
        assert im.getextrema()[3][1] > 0


def test_fonte_invalida():
    import pytest
    with pytest.raises(ValueError):
        FA.caminho_fonte("FonteInexistente")
