# @module services.assinatura_cliente_carimbo — carimba o TRAÇO desenhado (PNG) do
# cliente nos rects posicionados pelo corretor, e anexa a folha de autoria.
#
# Reusa o MESMO padrão do pades_service (overlay numa página transparente do tamanho
# da página alvo + pypdf merge_page → alinhamento exato). Diferença: desenha a IMAGEM
# do traço (não o texto "ASSINADO DIGITALMENTE"). NÃO assina ICP — isso roda DEPOIS,
# por último (pyHanko), pra não invalidar o PAdES.
#
# Coordenadas: pontos PDF, origem inferior-esquerda (igual ao "Posicionar"/pades_service).
import io
import hashlib
import logging
from datetime import datetime
from typing import List, Optional, Tuple

logger = logging.getLogger("romatec")

_VERDE_HEX = "#0B6E4F"
_DOURADO_HEX = "#B8860B"


def _png_size(raw: bytes) -> Tuple[int, int]:
    """Largura/altura do PNG (via PIL; fallback 1x1)."""
    try:
        from PIL import Image as _PILImage
        im = _PILImage.open(io.BytesIO(raw))
        return int(im.width or 1), int(im.height or 1)
    except Exception:
        return 1, 1


def _overlay_traco(page_w: float, page_h: float, rect: Tuple[float, float, float, float],
                   traco_png: bytes, legenda: str = "") -> bytes:
    """Página transparente (tamanho da página alvo) com o traço centralizado no rect,
    proporção preservada, margem interna de 4pt. Opcional: micro-legenda dourada abaixo."""
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as _canvas
    from reportlab.lib.utils import ImageReader

    x0, y0, x1, y1 = rect
    box_w = max(1.0, (x1 - x0) - 8)
    box_h = max(1.0, (y1 - y0) - 8)
    iw, ih = _png_size(traco_png)
    escala = min(box_w / iw, box_h / ih)
    w, h = iw * escala, ih * escala

    buf = io.BytesIO()
    c = _canvas.Canvas(buf, pagesize=(page_w, page_h))
    c.saveState()
    try:
        c.drawImage(ImageReader(io.BytesIO(traco_png)),
                    x0 + ((x1 - x0) - w) / 2, y0 + ((y1 - y0) - h) / 2,
                    width=w, height=h, mask="auto")
    except Exception:
        logger.warning("Traço inválido ignorado no carimbo.", exc_info=True)
    if legenda:
        c.setFont("Helvetica", 5.0)
        c.setFillColor(colors.HexColor(_DOURADO_HEX))
        c.drawString(x0, max(2.0, y0 - 6), legenda[:120])
    c.restoreState()
    c.showPage()
    c.save()
    return buf.getvalue()


def carimbar_traco_em_pagina(pdf_bytes: bytes, pagina_idx: int,
                             rect: Tuple[float, float, float, float],
                             traco_png: bytes, legenda: str = "") -> bytes:
    """Carimba UM traço (PNG) no rect (pontos, origem inf-esq) da página `pagina_idx`
    (0-based). Levanta erro 422-like se a página for inválida."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_bytes))
    total = len(reader.pages)
    if pagina_idx < 0 or pagina_idx >= total:
        raise ValueError(f"Página de âncora inválida: {pagina_idx} (0..{total - 1})")
    mb = reader.pages[pagina_idx].mediabox
    overlay = _overlay_traco(float(mb.width), float(mb.height), rect, traco_png, legenda)
    overlay_page = PdfReader(io.BytesIO(overlay)).pages[0]
    writer = PdfWriter()
    for i, p in enumerate(reader.pages):
        if i == pagina_idx:
            try:
                p.merge_page(overlay_page)
            except Exception as e:
                logger.warning("Overlay do traço falhou na página %s (%s)", i, e)
        writer.add_page(p)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _folha_autoria(assinaturas: List[dict], doc_hash_placeholder: str = "") -> bytes:
    """Página A4 'Manifestação de Vontade e Autoria' com base legal + evidências por signatário."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as _canvas

    VERDE = colors.HexColor(_VERDE_HEX)
    DOURADO = colors.HexColor(_DOURADO_HEX)
    W, H = A4
    buf = io.BytesIO()
    c = _canvas.Canvas(buf, pagesize=A4)
    y = H - 56
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(VERDE)
    c.drawString(50, y, "MANIFESTAÇÃO DE VONTADE E AUTORIA — ASSINATURA ELETRÔNICA")
    y -= 8
    c.setFillColor(DOURADO)
    c.rect(50, y - 2, 495, 1.5, stroke=0, fill=1)
    y -= 22
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(50, y, "Lei nº 14.063/2020 (assinatura avançada) · MP 2.200-2/2001 · CC arts. 219, 221 e 1.647 · CPC art. 411")
    y -= 22
    for sig in assinaturas:
        try:
            h_traco = hashlib.sha256(sig.get("traco_png") or b"").hexdigest()
        except Exception:
            h_traco = "-"
        ass_em = sig.get("assinado_em")
        ass_em = ass_em.isoformat() if isinstance(ass_em, datetime) else str(ass_em or "-")
        linhas = [
            f"Signatário: {sig.get('nome', '-')}"
            + (f"  ·  CPF {sig.get('cpf')}" if sig.get("cpf") else "")
            + f"  ·  Papel: {sig.get('role', '-')}",
            f"Data/hora: {ass_em}  ·  IP: {sig.get('ip') or '-'}",
            f"Geolocalização: {sig.get('geo_lat') if sig.get('geo_lat') is not None else '-'}, "
            f"{sig.get('geo_lng') if sig.get('geo_lng') is not None else '-'}  ·  "
            f"Dispositivo: {(sig.get('user_agent') or '-')[:90]}",
            f"Hash do traço (SHA-256): {h_traco}",
        ]
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#1A1A1A"))
        for l in linhas:
            if y < 60:
                break
            c.drawString(50, y, l)
            y -= 13
        y -= 8
    c.showPage()
    c.save()
    return buf.getvalue()


def _append_pagina(pdf_bytes: bytes, pagina_pdf: bytes) -> bytes:
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    for p in PdfReader(io.BytesIO(pdf_bytes)).pages:
        writer.add_page(p)
    for p in PdfReader(io.BytesIO(pagina_pdf)).pages:
        writer.add_page(p)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def carimbar_documento(pdf_bytes: bytes, ancoras: List[dict],
                       assinaturas: List[dict]) -> Tuple[bytes, str]:
    """Carimba todos os traços nos rects das âncoras e anexa a folha de autoria.
    `ancoras`: [{role, pagina, x_pt, y_pt, larg_pt, alt_pt}]. `assinaturas`: [{role, nome,
    cpf, traco_png, ip, geo_lat, geo_lng, user_agent, assinado_em}].
    Retorna (pdf_bytes_carimbado, sha256)."""
    out = pdf_bytes
    by_role = {a.get("role"): a for a in (ancoras or [])}
    for sig in assinaturas:
        a = by_role.get(sig.get("role"))
        traco = sig.get("traco_png")
        if not a or not traco:
            continue
        x = float(a.get("x_pt", 0)); y = float(a.get("y_pt", 0))
        w = float(a.get("larg_pt", 0)); h = float(a.get("alt_pt", 0))
        rect = (x, y, x + w, y + h)
        legenda = f"Assinado eletronicamente · {sig.get('nome', '')}"
        out = carimbar_traco_em_pagina(out, int(a.get("pagina", 0)), rect, traco, legenda)
    out = _append_pagina(out, _folha_autoria(assinaturas))
    doc_hash = hashlib.sha256(out).hexdigest()
    return out, doc_hash
