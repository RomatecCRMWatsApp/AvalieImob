# @module pdf.templates.anexos_imovel — Anexos (fotos + documentos) do imóvel para o
# PDF do contrato. Compartilhado pelos 3 renderers (tradicional/prime1/prime2) + módulo
# de exclusividade. Os BYTES já vêm pré-carregados (db.images → data_b64) e injetados em
# objeto["_fotos_bytes"] / objeto["_documentos_bytes"]; aqui só montamos flowables.
# Defensivo: qualquer imagem inválida é ignorada, nunca quebra o PDF.
import io
import logging

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle,
)

logger = logging.getLogger("romatec")

_VERDE = colors.HexColor("#1a4731")
_DOURADO = colors.HexColor("#B8860B")

_TIT = ParagraphStyle(
    "anexo_tit", fontName="Helvetica-Bold", fontSize=12, textColor=_VERDE,
    spaceBefore=4, spaceAfter=8, leading=15,
)
_LEG = ParagraphStyle(
    "anexo_leg", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#444444"),
    alignment=TA_CENTER, spaceBefore=2, spaceAfter=4, leading=10,
)


def _img_flowable(raw: bytes, max_w: float, max_h: float):
    """Cria um Image escalado preservando proporção, cabendo em (max_w, max_h). None se inválido.
    Normaliza via PIL para PNG RGB — garante que o ReportLab consiga DESENHAR (evita falha
    de build com WebP, CMYK, paletas ou modos exóticos vindos do upload)."""
    try:
        from PIL import Image as _PILImage
        im = _PILImage.open(io.BytesIO(raw))
        im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        iw, ih = im.size
        if not iw or not ih:
            return None
        out = io.BytesIO()
        im.save(out, format="PNG")
        out.seek(0)
        escala = min(max_w / iw, max_h / ih)
        return Image(out, width=iw * escala, height=ih * escala)
    except Exception:
        logger.warning("Anexo: imagem inválida ignorada.", exc_info=True)
        return None


def anexos_imovel_flowables(objeto: dict) -> list:
    """Retorna a lista de flowables dos anexos (fotos + documentos) ou [] se não houver.

    Espera objeto["_fotos_bytes"]: list[bytes] e objeto["_documentos_bytes"]: list[bytes]
    (PDFs já convertidos em páginas-imagem no upload)."""
    if not isinstance(objeto, dict):
        return []
    fotos = [b for b in (objeto.get("_fotos_bytes") or []) if b]
    docs = [b for b in (objeto.get("_documentos_bytes") or []) if b]
    if not fotos and not docs:
        return []

    page_w = A4[0] - 5 * cm  # margens ~2,5cm de cada lado
    elems: list = []

    # ── ANEXO I — RELATÓRIO FOTOGRÁFICO ───────────────────────────────────────
    if fotos:
        elems.append(PageBreak())
        elems.append(Paragraph("ANEXO I — RELATÓRIO FOTOGRÁFICO DO IMÓVEL", _TIT))
        elems.append(HRFlowable(width="100%", thickness=1, color=_DOURADO, spaceAfter=10))
        cel_w = (page_w - 0.6 * cm) / 2.0  # 2 colunas
        cel_h = 6.2 * cm
        linha = []
        linhas = []
        for i, raw in enumerate(fotos, 1):
            img = _img_flowable(raw, cel_w, cel_h)
            # NÃO usar KeepTogether dentro de célula de Table: o ReportLab calcula a
            # altura da linha como um valor gigante (2^24), a tabela vira "too large" e
            # o template resiliente PULA a tabela inteira — fotos sumiam (só o cabeçalho
            # do Anexo I aparecia). A célula [img, legenda] já fica junta na própria linha.
            cel = [img, Paragraph(f"Foto {i}", _LEG)] if img else [Paragraph(f"Foto {i} (indisponível)", _LEG)]
            linha.append(cel)
            if len(linha) == 2:
                linhas.append(linha)
                linha = []
        if linha:
            linha.append("")  # completa a 2ª coluna
            linhas.append(linha)
        tbl = Table(linhas, colWidths=[cel_w + 0.3 * cm, cel_w + 0.3 * cm])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        elems.append(tbl)

    # ── ANEXO II — DOCUMENTAÇÃO DO IMÓVEL ─────────────────────────────────────
    if docs:
        elems.append(PageBreak())
        elems.append(Paragraph("ANEXO II — DOCUMENTAÇÃO DO IMÓVEL", _TIT))
        elems.append(HRFlowable(width="100%", thickness=1, color=_DOURADO, spaceAfter=10))
        doc_h = A4[1] - 9 * cm  # folga p/ legenda/rodapé; evita "flowable too large"
        for i, raw in enumerate(docs, 1):
            img = _img_flowable(raw, page_w, doc_h)
            if img:
                if i > 1:
                    elems.append(PageBreak())  # 1 documento por página
                elems.append(img)
                elems.append(Paragraph(f"Documento {i}", _LEG))
            else:
                elems.append(Paragraph(f"Documento {i} (indisponível)", _LEG))

    return elems
