# Teste de REGRESSÃO criptográfica (OBRIGATÓRIO — seção 2.1 do spec):
# a assinatura da TESTEMUNHA (carimbo incremental + PAdES adicional) NÃO pode quebrar
# a assinatura das PARTES. Valida o PDF ANTES e DEPOIS — a assinatura da parte tem de
# continuar ÍNTEGRA/VÁLIDA, e a da testemunha também.
import datetime
import io

import pytest


def _gerar_pfx():
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Teste Romatec")])
    now = datetime.datetime.utcnow()
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=365))
            .sign(key, hashes.SHA256()))
    pfx = pkcs12.serialize_key_and_certificates(
        b"romatec", key, cert, None, serialization.BestAvailableEncryption(b"123"))
    return pfx, "123"


def _pdf_simples():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rc
    b = io.BytesIO()
    c = rc.Canvas(b, pagesize=A4)
    c.drawString(72, 700, "Contrato de teste — assinado pelas partes")
    c.showPage()
    c.save()
    return b.getvalue()


def _png():
    from PIL import Image
    im = Image.new("RGBA", (220, 80), (0, 0, 0, 0))
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("pyhanko") is None,
    reason="pyhanko ausente (roda no Railway)")
def test_testemunha_preserva_assinatura_das_partes():
    from services.pades_service import _assinar_pades
    from services.testemunha_signing import (
        carimbar_incremental, assinar_pades_incremental, status_assinaturas)

    pfx, pwd = _gerar_pfx()
    pdf = _pdf_simples()

    # 1) PARTE assina (campo RomatecICP) — base já assinada
    assinado_partes = _assinar_pades(pdf, pfx, pwd)
    st1 = status_assinaturas(assinado_partes)
    assert len(st1) == 1, f"esperava 1 assinatura, veio {st1}"
    assert st1[0][1] is True, "assinatura da parte deveria estar íntegra"

    # 2) TESTEMUNHA: carimbo INCREMENTAL + assinatura PAdES adicional INCREMENTAL
    com_carimbo = carimbar_incremental(
        assinado_partes, 0, (72, 120, 292, 180), _png(), "Testemunha do COMPRADOR (A MURTA): Fulano")
    com_testemunha = assinar_pades_incremental(com_carimbo, pfx, pwd, "RomatecTestemunha_1")

    # 3) AS DUAS ASSINATURAS CONTINUAM ÍNTEGRAS (a da parte NÃO pode ter quebrado)
    st2 = {n: (intact, valid) for (n, intact, valid) in status_assinaturas(com_testemunha)}
    assert "RomatecICP" in st2, f"assinatura da parte sumiu: {st2}"
    assert st2["RomatecICP"][0] is True, "REGRESSÃO: a assinatura da PARTE quebrou após a testemunha!"
    assert "RomatecTestemunha_1" in st2, "assinatura da testemunha não foi anexada"
    assert st2["RomatecTestemunha_1"][0] is True, "assinatura da testemunha não ficou íntegra"


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("pyhanko") is None,
    reason="pyhanko ausente (roda no Railway)")
def test_resave_nao_incremental_quebra_a_parte():
    """Garante que o teste DETECTA o jeito errado: uma reescrita NÃO-incremental
    (fitz save sem incremental) quebra a assinatura da parte (intact=False)."""
    import fitz
    from services.pades_service import _assinar_pades
    from services.testemunha_signing import status_assinaturas

    pfx, pwd = _gerar_pfx()
    assinado = _assinar_pades(_pdf_simples(), pfx, pwd)
    assert status_assinaturas(assinado)[0][1] is True
    d = fitz.open(stream=assinado, filetype="pdf")
    out = io.BytesIO()
    d.save(out)   # NÃO-incremental → reescreve o xref → quebra os byte-ranges
    d.close()
    st = {n: intact for (n, intact, _v) in status_assinaturas(out.getvalue())}
    assert st.get("RomatecICP") is False, "re-save não-incremental DEVERIA quebrar a assinatura"
