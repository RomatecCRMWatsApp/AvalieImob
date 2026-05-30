# @module services.pades_service — Assinatura PAdES com pyhanko + carimbo visual Romatec
"""
Assinatura digital PAdES (PDF Advanced Electronic Signatures) usando pyhanko.

Fluxo:
1. Recebe PDF original (bytes) + .pfx (bytes) + senha + metadados do avaliador.
2. Gera um CARIMBO visual compacto (caixa verde) com:
   - "ASSINADO DIGITALMENTE — ICP-Brasil (PAdES)"
   - Nome, registros (CRECI/CNAI), endereco, fone, e-mail, site
   - AC, validade, hash SHA-256 e QR Code (URL publica /v/laudo/v/{hash})
3. Sobrepoe o carimbo na PAGINA DE CONCLUSAO do documento (detectada por texto).
   Se nao encontrar, anexa o carimbo como pagina propria (fallback).
4. Aplica assinatura PAdES criptografando com a chave do .pfx.
5. Retorna PDF assinado (bytes) + hash de autenticidade.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
from datetime import datetime
from typing import Optional, Tuple, List

logger = logging.getLogger("romatec")


def _public_base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "https://app.romatecavalieimob.com.br").rstrip("/")


# ─────────────────────────────────────────────────────────────────────────────
# Carimbo visual compacto — desenhado no rodape de uma pagina A4 transparente,
# para ser sobreposto na pagina de conclusao do documento.
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_carimbo_assinatura(
    *,
    titular: str,
    documento: str,
    registro_full: str = "",
    endereco: str = "",
    contato: str = "",
    data_assinatura: datetime,
    emissor: str,
    valido_ate: Optional[datetime],
    hash_autenticidade: str,
    url_verificacao: str,
) -> bytes:
    """Gera 1 pagina A4 (fundo transparente) com o carimbo no rodape."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    try:
        import qrcode
        qr_img = qrcode.make(url_verificacao, box_size=8, border=1)
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format="PNG")
        qr_buf.seek(0)
    except Exception as e:
        logger.warning("Falha ao gerar QR Code: %s", e)
        qr_buf = None

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4

    # Caixa no rodape
    box_x = 18 * mm
    box_y = 16 * mm
    box_w = page_w - 2 * box_x
    box_h = 60 * mm

    # Fundo branco semi-translucido + borda verde (cobre eventual conteudo atras)
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#10B981"))
    c.setLineWidth(1.2)
    c.roundRect(box_x, box_y, box_w, box_h, 4 * mm, stroke=1, fill=1)

    # Faixa-titulo
    c.setFillColor(colors.HexColor("#10B981"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(box_x + 6 * mm, box_y + box_h - 8 * mm, "ASSINADO DIGITALMENTE — ICP-Brasil (PAdES)")

    # QR (lado direito)
    qr_size = 30 * mm
    qr_x = box_x + box_w - qr_size - 6 * mm
    qr_y = box_y + (box_h - qr_size) / 2 - 3 * mm
    if qr_buf is not None:
        from reportlab.lib.utils import ImageReader
        c.drawImage(ImageReader(qr_buf), qr_x, qr_y, width=qr_size, height=qr_size,
                    preserveAspectRatio=True, mask="auto")
        c.setFont("Helvetica", 6.5)
        c.setFillColor(colors.HexColor("#6B7280"))
        c.drawCentredString(qr_x + qr_size / 2, qr_y - 3.5 * mm, "Escaneie para validar")

    # Coluna de texto (esquerda)
    tx = box_x + 6 * mm
    text_w = qr_x - tx - 4 * mm
    ty = box_y + box_h - 16 * mm

    # Linha de assinatura
    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    c.setLineWidth(0.7)
    c.line(tx, ty, tx + min(text_w, 80 * mm), ty)
    ty -= 5 * mm

    c.setFillColor(colors.HexColor("#111827"))
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(tx, ty, (titular or "").upper())
    ty -= 4.6 * mm

    c.setFillColor(colors.HexColor("#374151"))
    c.setFont("Helvetica", 8.5)
    for linha in [registro_full, endereco, contato]:
        if linha:
            c.drawString(tx, ty, linha[:95])
            ty -= 4.2 * mm

    ty -= 1.5 * mm
    data_str = data_assinatura.strftime("%d/%m/%Y %H:%M")
    valido_str = valido_ate.strftime("%d/%m/%Y") if valido_ate else "—"
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(tx, ty, f"{documento}  ·  Assinado em {data_str}  ·  Cert: {emissor}  ·  Validade {valido_str}")
    ty -= 3.8 * mm
    c.drawString(tx, ty, "Validade juridica ICP-Brasil — confira em validar.iti.gov.br")
    ty -= 4.2 * mm

    c.setFont("Courier", 6.8)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawString(tx, ty, f"SHA-256: {hash_autenticidade[:56]}")
    if len(hash_autenticidade) > 56:
        ty -= 3.2 * mm
        c.drawString(tx, ty, hash_autenticidade[56:])

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Sobreposicao na pagina de conclusao (com fallback de anexar pagina)
# ─────────────────────────────────────────────────────────────────────────────

def _indice_pagina_conclusao(reader) -> Optional[int]:
    """Acha a pagina da secao de conclusao. Prioriza 'RESPONSABILIDADE'
    (so aparece na secao), depois 'CONCLUS'. Ignora a pagina de sumario."""
    def _norm(s: str) -> str:
        return (s or "").upper()

    alvo = None
    for i, p in enumerate(reader.pages):
        try:
            txt = _norm(p.extract_text())
        except Exception:
            txt = ""
        if "RESPONSABILIDADE" in txt and ("CONCLUS" in txt or "TECNICA" in txt or "TÉCNICA" in txt):
            return i
    for i, p in enumerate(reader.pages):
        try:
            txt = _norm(p.extract_text())
        except Exception:
            txt = ""
        if "CONCLUS" in txt and "SUMARIO" not in txt and "SUMÁRIO" not in txt:
            alvo = i
    return alvo


def _aplicar_carimbo(pdf_bytes: bytes, carimbo_pdf: bytes) -> bytes:
    """Sobrepoe o carimbo na pagina de conclusao; se nao achar, anexa ao final."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    idx = _indice_pagina_conclusao(reader)

    if idx is not None:
        overlay_page = PdfReader(io.BytesIO(carimbo_pdf)).pages[0]
        for i, p in enumerate(reader.pages):
            if i == idx:
                try:
                    p.merge_page(overlay_page)
                except Exception as e:
                    logger.warning("Falha ao sobrepor carimbo na conclusao: %s", e)
            writer.add_page(p)
    else:
        for p in reader.pages:
            writer.add_page(p)
        for op in PdfReader(io.BytesIO(carimbo_pdf)).pages:
            writer.add_page(op)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Assinatura PAdES via pyhanko
# ─────────────────────────────────────────────────────────────────────────────

def _carregar_signer(pfx_bytes: bytes, password: str):
    """Carrega um SimpleSigner do pyhanko a partir dos bytes do .pfx.

    O pyhanko (load_pkcs12) espera um CAMINHO de arquivo, nao um BytesIO.
    Tentamos primeiro montar direto dos bytes via `cryptography`; se a versao
    do pyhanko nao tiver helper, gravamos um arquivo temporario e usamos o path.
    """
    from pyhanko.sign import signers

    pwd = password.encode("utf-8") if password else None

    # Caminho 1 (preferido): montar a partir dos bytes com cryptography
    try:
        from cryptography.hazmat.primitives.serialization import pkcs12 as _pkcs12
        from asn1crypto import x509 as _asn1_x509, keys as _asn1_keys
        from cryptography.hazmat.primitives import serialization as _ser
        from pyhanko_certvalidator.registry import SimpleCertificateStore

        key, cert, extra = _pkcs12.load_key_and_certificates(pfx_bytes, pwd)
        if key is None or cert is None:
            raise RuntimeError("PKCS12 sem chave/certificado")
        signing_cert = _asn1_x509.Certificate.load(cert.public_bytes(_ser.Encoding.DER))
        key_der = key.private_bytes(
            _ser.Encoding.DER, _ser.PrivateFormat.PKCS8, _ser.NoEncryption()
        )
        signing_key = _asn1_keys.PrivateKeyInfo.load(key_der)
        registry = SimpleCertificateStore()
        if extra:
            registry.register_multiple(
                _asn1_x509.Certificate.load(c.public_bytes(_ser.Encoding.DER)) for c in extra
            )
        return signers.SimpleSigner(
            signing_cert=signing_cert,
            signing_key=signing_key,
            cert_registry=registry,
        )
    except Exception as e:
        logger.warning("Montagem direta do signer falhou (%s); usando arquivo temporario", e)

    # Caminho 2 (fallback): gravar .pfx temporario e usar o path
    import tempfile
    tf_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pfx", delete=False) as tf:
            tf.write(pfx_bytes)
            tf_path = tf.name
        return signers.SimpleSigner.load_pkcs12(pfx_file=tf_path, passphrase=pwd)
    finally:
        if tf_path:
            try:
                os.unlink(tf_path)
            except OSError:
                pass


def _assinar_pades(pdf_bytes: bytes, pfx_bytes: bytes, password: str) -> bytes:
    """Aplica assinatura PAdES usando pyhanko (campo invisivel)."""
    from pyhanko.sign import signers
    from pyhanko.sign.fields import SigFieldSpec, append_signature_field
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

    signer = _carregar_signer(pfx_bytes, password)
    if signer is None:
        raise RuntimeError("Falha ao carregar .pfx no pyhanko")

    in_buf = io.BytesIO(pdf_bytes)
    w = IncrementalPdfFileWriter(in_buf)
    append_signature_field(w, SigFieldSpec(sig_field_name="RomatecICP"))
    meta = signers.PdfSignatureMetadata(
        field_name="RomatecICP",
        reason="Assinatura digital ICP-Brasil — Romatec AvalieImob",
        location="Brasil",
    )
    out_buf = io.BytesIO()
    signers.sign_pdf(w, meta, signer=signer, output=out_buf)
    return out_buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Função pública — orquestra tudo
# ─────────────────────────────────────────────────────────────────────────────

def assinar_pdf_icp(
    *,
    pdf_bytes: bytes,
    pfx_bytes: bytes,
    pfx_password: str,
    titular: str,
    documento: str,
    cargo: str = "",
    registro: str = "",
    cidade_uf: str = "",
    emissor: str,
    valido_ate: Optional[datetime] = None,
    registro_full: str = "",
    endereco: str = "",
    contato: str = "",
) -> Tuple[bytes, str, datetime]:
    """Assina um PDF com PAdES + carimbo visual na pagina de conclusao.

    Retorna: (pdf_assinado_bytes, hash_autenticidade, data_assinatura_utc)
    """
    data_assinatura = datetime.utcnow()

    # registro_full default a partir de 'registro' (compat.)
    if not registro_full:
        registro_full = ("Avaliador " + registro).strip() if registro else ""

    hash_provisorio = hashlib.sha256(pdf_bytes).hexdigest()
    url_verificacao = f"{_public_base_url()}/v/laudo/v/{hash_provisorio}"

    carimbo_pdf = _gerar_carimbo_assinatura(
        titular=titular,
        documento=documento,
        registro_full=registro_full,
        endereco=endereco,
        contato=contato,
        data_assinatura=data_assinatura,
        emissor=emissor,
        valido_ate=valido_ate,
        hash_autenticidade=hash_provisorio,
        url_verificacao=url_verificacao,
    )

    pdf_com_carimbo = _aplicar_carimbo(pdf_bytes, carimbo_pdf)
    pdf_assinado = _assinar_pades(pdf_com_carimbo, pfx_bytes, pfx_password)
    hash_final = hashlib.sha256(pdf_assinado).hexdigest()

    return pdf_assinado, hash_final, data_assinatura
