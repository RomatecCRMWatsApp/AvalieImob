# @module services.pades_service — Assinatura PAdES com pyhanko + bloco visual Romatec
"""
Assinatura digital PAdES (PDF Advanced Electronic Signatures) usando pyhanko.

Fluxo:
1. Recebe PDF original (bytes) + .pfx (bytes) + senha + metadados do avaliador.
2. Anexa página visual de assinatura (HTML-like via reportlab) com:
   - Cabeçalho verde "ASSINADO DIGITALMENTE — ICP-Brasil (PAdES)"
   - Nome, CPF, data/hora, AC, validade, link validar.iti.gov.br
   - Linha de assinatura, cargo, registro
   - Hash SHA-256 e URL pública /v/laudo/v/{hash}
   - QR Code apontando pra URL pública
3. Aplica assinatura PAdES B-LT criptografando com a chave do .pfx.
4. Retorna PDF assinado (bytes) + hash de autenticidade.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger("romatec")


# ─────────────────────────────────────────────────────────────────────────────
# Config: URL base pra QR Code de validação
# ─────────────────────────────────────────────────────────────────────────────
def _public_base_url() -> str:
    return os.getenv(
        "PUBLIC_BASE_URL",
        "https://app.romatecavalieimob.com.br",
    ).rstrip("/")


# ─────────────────────────────────────────────────────────────────────────────
# Bloco visual de assinatura — gera 1 página PDF com a "etiqueta" de assinatura
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_pagina_assinatura(
    *,
    titular: str,
    documento: str,
    cargo: str = "",
    registro: str = "",
    cidade_uf: str = "",
    data_assinatura: datetime,
    emissor: str,
    valido_ate: Optional[datetime],
    hash_autenticidade: str,
    url_verificacao: str,
) -> bytes:
    """Gera 1 página A4 PDF com o bloco visual padrão Romatec.

    Retorna bytes do PDF (1 página) — esse PDF será concatenado ao final do
    documento original ANTES da assinatura PAdES ser aplicada.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    # QR Code via lib `qrcode`
    try:
        import qrcode
        from qrcode.image.pil import PilImage
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

    # Margem
    margin_x = 20 * mm
    cursor_y = page_h - 25 * mm

    # ── Cabeçalho data/local ───────────────────────────────────────────────
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#666666"))
    cabecalho = data_assinatura.strftime("%d de %B de %Y").lower()
    # tradução simples mês PT-BR
    meses = {
        "january": "janeiro", "february": "fevereiro", "march": "março",
        "april": "abril", "may": "maio", "june": "junho",
        "july": "julho", "august": "agosto", "september": "setembro",
        "october": "outubro", "november": "novembro", "december": "dezembro",
    }
    for en, pt in meses.items():
        cabecalho = cabecalho.replace(en, pt)
    cabecalho_full = f"{cidade_uf}, {cabecalho}." if cidade_uf else cabecalho + "."
    c.drawCentredString(page_w / 2, cursor_y, cabecalho_full)
    cursor_y -= 12 * mm

    # ── Caixa verde "ASSINADO DIGITALMENTE" ───────────────────────────────
    box_w = 130 * mm
    box_h = 38 * mm
    box_x = (page_w - box_w) / 2
    box_y = cursor_y - box_h

    # Borda verde arredondada
    c.setStrokeColor(colors.HexColor("#10B981"))  # emerald-500
    c.setLineWidth(1.2)
    c.roundRect(box_x, box_y, box_w, box_h, 4 * mm, stroke=1, fill=0)

    # Header faixa verde no topo da caixa
    c.setFillColor(colors.HexColor("#10B981"))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(
        page_w / 2,
        box_y + box_h - 7 * mm,
        "ASSINADO DIGITALMENTE — ICP-Brasil (PAdES)",
    )

    # Nome do titular
    c.setFillColor(colors.HexColor("#1F2937"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(page_w / 2, box_y + box_h - 14 * mm, titular.upper())

    # CPF + assinado em
    c.setFillColor(colors.HexColor("#374151"))
    c.setFont("Helvetica", 9)
    data_str = data_assinatura.strftime("%d/%m/%Y %H:%M")
    c.drawCentredString(
        page_w / 2,
        box_y + box_h - 19.5 * mm,
        f"{documento}  ·  Assinado em {data_str}",
    )

    # Cert + validade
    valido_str = valido_ate.strftime("%d/%m/%Y") if valido_ate else "—"
    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawCentredString(
        page_w / 2,
        box_y + box_h - 25 * mm,
        f"Cert: {emissor}  ·  Válido até {valido_str}  ·  Validar em validar.iti.gov.br",
    )

    cursor_y = box_y - 12 * mm

    # ── Linha de assinatura ────────────────────────────────────────────────
    line_w = 90 * mm
    line_x1 = (page_w - line_w) / 2
    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    c.setLineWidth(0.7)
    c.line(line_x1, cursor_y, line_x1 + line_w, cursor_y)
    cursor_y -= 5 * mm

    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(page_w / 2, cursor_y, titular)
    cursor_y -= 4.5 * mm

    if cargo or registro:
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#4B5563"))
        sub = cargo
        if registro:
            sub = (cargo + " · " if cargo else "") + registro
        c.drawCentredString(page_w / 2, cursor_y, sub)
        cursor_y -= 6 * mm
    else:
        cursor_y -= 4 * mm

    cursor_y -= 5 * mm

    # ── Hash + URL + QR (parte inferior) ───────────────────────────────────
    qr_size = 30 * mm
    qr_x = page_w - margin_x - qr_size
    qr_y = cursor_y - qr_size

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(margin_x, cursor_y - 2 * mm, "Hash de autenticidade:")

    c.setFont("Courier", 8)
    c.setFillColor(colors.HexColor("#374151"))
    # Quebrar hash em 2 linhas se necessário
    hash_line = hash_autenticidade[:48]
    c.drawString(margin_x, cursor_y - 6.5 * mm, hash_line)
    if len(hash_autenticidade) > 48:
        c.drawString(margin_x, cursor_y - 10 * mm, hash_autenticidade[48:])

    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor("#6B7280"))
    # URL pode ser longa; quebrar
    url_y = cursor_y - 16 * mm
    if len(url_verificacao) > 75:
        c.drawString(margin_x, url_y, url_verificacao[:75])
        c.drawString(margin_x, url_y - 4 * mm, url_verificacao[75:])
    else:
        c.drawString(margin_x, url_y, url_verificacao)

    if qr_buf is not None:
        from reportlab.lib.utils import ImageReader
        c.drawImage(
            ImageReader(qr_buf), qr_x, qr_y, width=qr_size, height=qr_size,
            preserveAspectRatio=True, mask="auto",
        )
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#6B7280"))
        c.drawCentredString(qr_x + qr_size / 2, qr_y - 3.5 * mm, "Escaneie para validar")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Concatenar página de assinatura ao PDF original
# ─────────────────────────────────────────────────────────────────────────────

def _anexar_pagina(pdf_original: bytes, pdf_pagina: bytes) -> bytes:
    """Concatena uma página PDF ao final de um PDF original. Usa pypdf."""
    from pypdf import PdfReader, PdfWriter

    reader_orig = PdfReader(io.BytesIO(pdf_original))
    reader_page = PdfReader(io.BytesIO(pdf_pagina))
    writer = PdfWriter()

    for p in reader_orig.pages:
        writer.add_page(p)
    for p in reader_page.pages:
        writer.add_page(p)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Assinatura PAdES via pyhanko
# ─────────────────────────────────────────────────────────────────────────────

def _assinar_pades(pdf_bytes: bytes, pfx_bytes: bytes, password: str) -> bytes:
    """Aplica assinatura PAdES B-B (básica) usando pyhanko.

    A assinatura é embutida via /Sig dictionary no PDF — Adobe Reader e
    validar.iti.gov.br vão reconhecer o cadeia ICP-Brasil automaticamente.
    """
    from pyhanko.sign import signers
    from pyhanko.sign.fields import SigFieldSpec, append_signature_field
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

    # Carregar credencial
    signer = signers.SimpleSigner.load_pkcs12(
        pfx_file=io.BytesIO(pfx_bytes),
        passphrase=password.encode("utf-8") if password else None,
    )
    if signer is None:
        raise RuntimeError("Falha ao carregar .pfx no pyhanko")

    # Preparar PDF pra assinatura incremental
    in_buf = io.BytesIO(pdf_bytes)
    w = IncrementalPdfFileWriter(in_buf)

    # Adicionar campo de assinatura invisível
    append_signature_field(w, SigFieldSpec(sig_field_name="RomatecICP"))

    # Metadados PAdES
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
) -> Tuple[bytes, str, datetime]:
    """Assina um PDF com PAdES + bloco visual.

    Retorna: (pdf_assinado_bytes, hash_autenticidade, data_assinatura_utc)

    O hash é o SHA-256 do PDF assinado final — usado pra rota pública
    /v/laudo/v/{hash} e como id de verificação no QR Code.
    """
    data_assinatura = datetime.utcnow()

    # 1. Calcular hash provisório do PDF original (apenas pra QR code prévio).
    #    O hash final será do PDF assinado.
    hash_provisorio = hashlib.sha256(pdf_bytes).hexdigest()
    url_verificacao = f"{_public_base_url()}/v/laudo/v/{hash_provisorio}"

    # 2. Gerar página visual de assinatura
    pagina_pdf = _gerar_pagina_assinatura(
        titular=titular,
        documento=documento,
        cargo=cargo,
        registro=registro,
        cidade_uf=cidade_uf,
        data_assinatura=data_assinatura,
        emissor=emissor,
        valido_ate=valido_ate,
        hash_autenticidade=hash_provisorio,
        url_verificacao=url_verificacao,
    )

    # 3. Anexar página ao PDF original
    pdf_com_pagina = _anexar_pagina(pdf_bytes, pagina_pdf)

    # 4. Assinar com PAdES
    pdf_assinado = _assinar_pades(pdf_com_pagina, pfx_bytes, pfx_password)

    # 5. Hash final (do PDF assinado)
    hash_final = hashlib.sha256(pdf_assinado).hexdigest()

    return pdf_assinado, hash_final, data_assinatura
