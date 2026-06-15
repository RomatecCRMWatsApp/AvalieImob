"""Anexo — Cartão de Regularidade Profissional (CRECI).

Renderiza, como ANEXO ao fim do contrato/laudo, o cartão de regularidade do corretor
(imagem enviada pelo usuário em Configurações) + o link de verificação. Best-effort:
devolve [] em qualquer falha (nunca quebra a geração do PDF).
"""
from __future__ import annotations

import base64
import io
import logging

logger = logging.getLogger("romatec")


def _b64_to_bytes(b64: str) -> bytes:
    if not b64:
        return b""
    s = b64.split(",", 1)[1] if b64.startswith("data:") else b64
    try:
        return base64.b64decode(s)
    except Exception:
        return b""


def is_pdf_b64(b64: str) -> bool:
    """True se o base64 (com ou sem data-uri) for um PDF."""
    if not b64:
        return False
    if b64.startswith("data:application/pdf"):
        return True
    return _b64_to_bytes(b64)[:5] == b"%PDF-"


def pdf_b64_to_paginas_png_b64(pdf_b64: str, max_paginas: int = 4, dpi: int = 150) -> list:
    """Converte cada página do PDF do cartão em PNG (data-uri base64). [] em falha.
    Usa PyMuPDF (fitz) — sem dependência de sistema (poppler)."""
    raw = _b64_to_bytes(pdf_b64)
    if raw[:5] != b"%PDF-":
        return []
    out = []
    try:
        import fitz  # PyMuPDF
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        with fitz.open(stream=raw, filetype="pdf") as doc:
            for i, page in enumerate(doc):
                if i >= max_paginas:
                    break
                pix = page.get_pixmap(matrix=mat, alpha=False)
                png = pix.tobytes("png")
                out.append("data:image/png;base64," + base64.b64encode(png).decode("ascii"))
    except Exception:
        logger.warning("Falha ao converter o PDF do cartão em imagens.", exc_info=True)
        return []
    return out


def _img_flowable(raw: bytes, largura_pt: float, max_h: float = 640.0):
    """RLImage normalizada (PIL→PNG) escalada à largura, com teto de altura. None em falha."""
    if not raw:
        return None
    try:
        from reportlab.platypus import Image as RLImage
        from reportlab.lib.utils import ImageReader
        try:
            from PIL import Image as _PIL
            im = _PIL.open(io.BytesIO(raw))
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")
            im.thumbnail((1600, 2200))
            out = io.BytesIO()
            im.save(out, format="PNG", optimize=True)
            raw = out.getvalue()
        except Exception:
            pass
        ir = ImageReader(io.BytesIO(raw))
        iw, ih = ir.getSize()
        w = float(largura_pt)
        h = w * (ih / float(iw)) if iw else w
        if h > max_h:
            h = max_h
            w = h * (iw / float(ih)) if ih else w
        return RLImage(io.BytesIO(raw), width=w, height=h)
    except Exception:
        return None


def cartao_regularidade_flowables(b64: str = None, link: str = "", largura_pt: float = 440.0,
                                  titulo: str = "ANEXO — CARTÃO DE REGULARIDADE PROFISSIONAL (CRECI)",
                                  paginas: list = None) -> list:
    """Flowables do anexo do cartão (PageBreak + título + imagem(ns) + link).
    Aceita uma imagem única (b64) OU uma lista de páginas-imagem (PDF convertido). [] se vazio."""
    imgs = []
    if paginas:
        imgs = [_b64_to_bytes(p) for p in paginas if p]
    elif b64:
        imgs = [_b64_to_bytes(b64)]
    imgs = [r for r in imgs if r]
    if not imgs:
        return []
    try:
        from reportlab.platypus import Paragraph, PageBreak
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib import colors

        st_tit = ParagraphStyle("cart_tit", fontName="Helvetica-Bold", fontSize=11,
                                textColor=colors.HexColor("#0C3320"), alignment=TA_CENTER, spaceAfter=10)
        st_cap = ParagraphStyle("cart_cap", fontName="Helvetica", fontSize=8,
                                textColor=colors.HexColor("#5B7466"), alignment=TA_CENTER, spaceBefore=8)
        legenda = ("Documento emitido pelo Sistema COFECI-CRECI, comprobatório da regularidade "
                   "e habilitação profissional do corretor de imóveis.")
        if link:
            legenda += f"<br/>Verificação on-line: {link}"

        flow = []
        multi = len(imgs) > 1
        for idx, raw in enumerate(imgs):
            img = _img_flowable(raw, largura_pt)
            if img is None:
                continue
            flow.append(PageBreak())
            if idx == 0:
                flow.append(Paragraph(titulo, st_tit))
            elif multi:
                flow.append(Paragraph(f"{titulo} (cont. — pág. {idx + 1})", st_tit))
            flow.append(img)
            # legenda só na última página do cartão
            if idx == len(imgs) - 1:
                flow.append(Paragraph(legenda, st_cap))
        return flow
    except Exception:
        logger.warning("Falha ao montar o anexo do cartão de regularidade.", exc_info=True)
        return []


def anexos_regularidade_flowables(av: dict, largura_pt: float = 440.0,
                                  titulo_cartao: str = "ANEXO — CARTÃO DE REGULARIDADE PROFISSIONAL (CRECI)",
                                  titulo_certidao: str = "ANEXO — CERTIDÃO DE REGULARIDADE PROFISSIONAL (CRECI)") -> list:
    """Flowables dos anexos de regularidade (cartão + certidão) a partir do dict do avaliador.
    Cada um só entra se tiver imagem/páginas e o respectivo toggle 'anexar' estiver ligado."""
    av = av or {}
    out = []
    if av.get("cartao_regularidade_anexar", True):
        out += cartao_regularidade_flowables(
            av.get("cartao_regularidade_b64"), av.get("cartao_regularidade_link"), largura_pt,
            titulo=titulo_cartao, paginas=av.get("cartao_regularidade_paginas_b64") or [])
    if av.get("certidao_regularidade_anexar", True):
        out += cartao_regularidade_flowables(
            av.get("certidao_regularidade_b64"), av.get("certidao_regularidade_link"), largura_pt,
            titulo=titulo_certidao, paginas=av.get("certidao_regularidade_paginas_b64") or [])
    return out
