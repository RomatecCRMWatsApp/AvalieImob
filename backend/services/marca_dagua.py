"""Marca d'água (MINUTA / RASCUNHO) carimbada em TODAS as páginas de um PDF.

Usada para enviar ao cliente a MINUTA (rascunho) do contrato/procuração junto com o
link de assinatura, para leitura prévia. Mesma mecânica do carimbo (reportlab overlay
+ pypdf merge_page). Best-effort: devolve o PDF ORIGINAL em qualquer falha.
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger("marca_dagua")


def aplicar_marca_dagua(pdf_bytes: bytes, texto: str = "MINUTA",
                        subtitulo: str = "PARA LEITURA — AGUARDANDO ASSINATURA") -> bytes:
    """Carimba a marca d'água diagonal semitransparente em cada página. Fallback = original."""
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
        return pdf_bytes
    try:
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas as _canvas
        from reportlab.lib.colors import Color

        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        for page in reader.pages:
            mb = page.mediabox
            w, h = float(mb.width), float(mb.height)
            buf = io.BytesIO()
            c = _canvas.Canvas(buf, pagesize=(w, h))
            c.saveState()
            c.translate(w / 2.0, h / 2.0)
            c.rotate(45)
            base = min(w, h)
            c.setFont("Helvetica-Bold", base * 0.16)
            c.setFillColor(Color(0.78, 0.10, 0.10, alpha=0.16))
            c.drawCentredString(0, 0, texto)
            if subtitulo:
                c.setFont("Helvetica-Bold", base * 0.034)
                c.setFillColor(Color(0.78, 0.10, 0.10, alpha=0.22))
                c.drawCentredString(0, -base * 0.11, subtitulo)
            c.restoreState()
            c.save()
            buf.seek(0)
            overlay = PdfReader(buf).pages[0]
            page.merge_page(overlay)
            writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        data = out.getvalue()
        return data if data.startswith(b"%PDF-") else pdf_bytes
    except Exception:
        logger.warning("Falha ao aplicar marca d'água — enviando PDF original.", exc_info=True)
        return pdf_bytes
