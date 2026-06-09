"""
Injeção de marca (white-label) nos PDFs do AvalieImob via ReportLab.

Expõe `make_branded_page_callbacks(...)` que devolve um onPage compatível com
SimpleDocTemplate/BaseDocTemplate, desenhando cabeçalho (logo + linha primária)
e rodapé (dados do tenant + paginação) em TODAS as páginas.

O logo pode vir de:
  - caminho local (logo padrão AvalieImob embarcado), ou
  - URL pública/R2 — baixado e cacheado em memória uma vez por geração.

Fallback é transparente: se o tenant usa o padrão, entra o logo/cores AvalieImob
sem quebrar PTAMs existentes.

Instalar: pip install reportlab requests
"""
from __future__ import annotations

import io
import os
import urllib.request
from functools import lru_cache
from typing import Callable, Optional

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from models.tenant_branding import ResolvedBranding, TenantBranding

PAGE_WIDTH, PAGE_HEIGHT = A4

# Geometria do cabeçalho/rodapé
_LOGO_W = 5.0 * cm
_LOGO_H = 1.8 * cm
_MARGIN_X = 2.0 * cm
_HEADER_LINE_Y = PAGE_HEIGHT - 3.8 * cm
_FOOTER_H = 1.9 * cm


@lru_cache(maxsize=64)
def _fetch_logo_reader(logo_ref: str) -> Optional[ImageReader]:
    """
    Carrega o logo como ImageReader. Aceita caminho local ou URL http(s).
    Cacheado por referência. Retorna None se não conseguir carregar (fallback
    silencioso para não quebrar a geração do documento).
    """
    try:
        if logo_ref.startswith("http://") or logo_ref.startswith("https://"):
            with urllib.request.urlopen(logo_ref, timeout=8) as resp:
                return ImageReader(io.BytesIO(resp.read()))
        if os.path.exists(logo_ref):
            return ImageReader(logo_ref)
    except Exception:
        return None
    return None


def _draw_header(c: Canvas, brand: ResolvedBranding) -> None:
    reader = _fetch_logo_reader(brand.logo_url)
    if reader is not None:
        try:
            iw, ih = reader.getSize()
            ratio = min(_LOGO_W / iw, _LOGO_H / ih)
            draw_w, draw_h = iw * ratio, ih * ratio
            c.drawImage(
                reader,
                _MARGIN_X,
                PAGE_HEIGHT - 3.5 * cm,
                width=draw_w,
                height=draw_h,
                preserveAspectRatio=True,
                mask="auto",  # respeita transparência do PNG
            )
        except Exception:
            pass  # nunca interromper a geração por causa do logo

    # Linha divisória na cor primária do tenant
    c.setStrokeColor(HexColor(brand.color_primary))
    c.setLineWidth(1.5)
    c.line(_MARGIN_X, _HEADER_LINE_Y, PAGE_WIDTH - _MARGIN_X, _HEADER_LINE_Y)


def _draw_footer(c: Canvas, page_num: int, brand: ResolvedBranding) -> None:
    # Faixa de fundo
    c.setFillColor(HexColor(brand.color_footer_bg))
    c.rect(0, 0, PAGE_WIDTH, _FOOTER_H, fill=1, stroke=0)

    # Fonte do rodapé: tenta a do tenant; cai para Helvetica se não registrada
    footer_font = _safe_font(brand.font_body)

    c.setFillColor(HexColor(brand.color_footer_text))
    c.setFont(footer_font, 7)
    cx = PAGE_WIDTH / 2
    if brand.footer_line1:
        c.drawCentredString(cx, 1.30 * cm, brand.footer_line1)
    if brand.footer_line2:
        c.drawCentredString(cx, 0.85 * cm, brand.footer_line2)
    if brand.footer_line3:
        c.drawCentredString(cx, 0.40 * cm, brand.footer_line3)

    # Paginação (lado direito)
    c.setFont(footer_font, 7)
    c.drawRightString(PAGE_WIDTH - _MARGIN_X, 0.40 * cm, f"Pág. {page_num}")


def _safe_font(name: Optional[str]) -> str:
    """
    Fontes custom (Montserrat, Inter...) precisam ser registradas via
    pdfmetrics.registerFont antes do uso. Aqui garantimos um fallback seguro.
    Registre suas TTFs no startup se quiser fidelidade tipográfica total.
    """
    from reportlab.pdfbase.pdfmetrics import getRegisteredFontNames

    if name and name in getRegisteredFontNames():
        return name
    return "Helvetica"


def make_branded_page_callbacks(
    branding: TenantBranding,
) -> Callable[[Canvas, object], None]:
    """
    Recebe o TenantBranding (do tenant logado) e devolve um onPage(canvas, doc)
    pronto para SimpleDocTemplate(..., onFirstPage=cb, onLaterPages=cb).

    Uso no gerador do PTAM:

        from backend.services import branding_repository as repo
        from backend.services.pdf_branding import make_branded_page_callbacks

        branding = await repo.get_branding(db, tenant_id)
        on_page = make_branded_page_callbacks(branding)
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    """
    brand = branding.resolved()

    def on_page(c: Canvas, doc: object) -> None:  # doc fornece page count corrente
        page_num = getattr(doc, "page", c.getPageNumber())
        c.saveState()
        _draw_header(c, brand)
        _draw_footer(c, page_num, brand)
        c.restoreState()

    return on_page


def render_preview_png(branding: TenantBranding, width: int = 900) -> bytes:
    """
    Gera um PNG de preview (cabeçalho + faixa + rodapé) para o endpoint
    GET /branding/preview e para a aba Preview do BrandingWizard.

    Renderiza uma página A4 em branco apenas com as marcas e rasteriza com
    pdf2image (poppler) ou, na ausência, devolve o PDF como bytes.
    """
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=A4)
    brand = branding.resolved()
    c.setFillColor(HexColor(brand.color_background))
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    _draw_header(c, brand)

    # Bloco-amostra de título no corpo, na cor de texto/primária do tenant
    c.setFillColor(HexColor(brand.color_primary))
    c.setFont(_safe_font(brand.font_title), 16)
    c.drawString(_MARGIN_X, PAGE_HEIGHT - 5.0 * cm,
                 "LAUDO DE AVALIAÇÃO (PTAM) — Amostra")
    c.setFillColor(HexColor(brand.color_text))
    c.setFont(_safe_font(brand.font_body), 10)
    c.drawString(_MARGIN_X, PAGE_HEIGHT - 5.8 * cm,
                 f"Responsável técnico: {brand.stamp_name}")
    c.drawString(_MARGIN_X, PAGE_HEIGHT - 6.3 * cm, brand.stamp_credentials)

    _draw_footer(c, 1, brand)
    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()

    try:
        from pdf2image import convert_from_bytes  # requer poppler-utils
        images = convert_from_bytes(pdf_bytes, dpi=120, fmt="png")
        out = io.BytesIO()
        img = images[0]
        # redimensiona para a largura pedida mantendo proporção
        h = int(img.height * (width / img.width))
        img = img.resize((width, h))
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        # Sem poppler: devolve o PDF (o frontend trata content-type).
        return pdf_bytes
