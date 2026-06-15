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


def cartao_regularidade_flowables(b64: str, link: str = "", largura_pt: float = 440.0,
                                  titulo: str = "ANEXO — CARTÃO DE REGULARIDADE PROFISSIONAL (CRECI)") -> list:
    """Flowables do anexo do cartão (PageBreak + título + imagem + link). [] se sem imagem."""
    raw = _b64_to_bytes(b64)
    if not raw:
        return []
    try:
        from reportlab.platypus import Paragraph, Spacer, PageBreak, Image as RLImage
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib import colors
        from reportlab.lib.utils import ImageReader

        # normaliza via PIL → PNG RGB (garante render em qualquer formato; corrige CMYK/webp)
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
        # limita a altura p/ caber numa página (frame útil ~ 680pt)
        max_h = 660.0
        if h > max_h:
            h = max_h
            w = h * (iw / float(ih)) if ih else w

        st_tit = ParagraphStyle("cart_tit", fontName="Helvetica-Bold", fontSize=11,
                                textColor=colors.HexColor("#0C3320"), alignment=TA_CENTER, spaceAfter=10)
        st_cap = ParagraphStyle("cart_cap", fontName="Helvetica", fontSize=8,
                                textColor=colors.HexColor("#5B7466"), alignment=TA_CENTER, spaceBefore=8)
        flow = [
            PageBreak(),
            Paragraph(titulo, st_tit),
            RLImage(io.BytesIO(raw), width=w, height=h),
        ]
        legenda = ("Documento emitido pelo Sistema COFECI-CRECI, comprobatório da regularidade "
                   "e habilitação profissional do corretor de imóveis.")
        if link:
            legenda += f"<br/>Verificação on-line: {link}"
        flow.append(Paragraph(legenda, st_cap))
        return flow
    except Exception:
        logger.warning("Falha ao montar o anexo do cartão de regularidade.", exc_info=True)
        return []
