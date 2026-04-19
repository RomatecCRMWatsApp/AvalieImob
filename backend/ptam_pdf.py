"""PDF generator for PTAM documents — RomaTec branding.

Uses reportlab to produce a professional, print-ready PDF with:
  - Cover page with logo, title, PTAM number and city/date
  - 7 content sections matching the PTAM model
  - Tables for impact-area samples and consolidation
  - Green (#1B4D1B) header band on every page + gold (#D4A830) section titles
  - Footer: 'RomaTec Consultoria Total — NBR 14.653' on every page
  - Signature block at the end (evaluator name, CNAI/CRECI)
"""
from __future__ import annotations

import io
import urllib.request
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── brand colours ────────────────────────────────────────────────────────────
GREEN = colors.HexColor("#1B4D1B")
GOLD = colors.HexColor("#D4A830")
WHITE = colors.white
LIGHT_GREEN = colors.HexColor("#E8F5E9")
DARK = colors.HexColor("#1A1A1A")

LOGO_URL = (
    "https://customer-assets.emergentagent.com"
    "/job_review-simples/artifacts/0n08eo2p_02_icone_512.png"
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt_currency(v: Any) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _fmt_area(v: Any) -> str:
    try:
        return f"{float(v):,.4f} m²".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,0000 m²"


def _fetch_logo() -> bytes | None:
    try:
        with urllib.request.urlopen(LOGO_URL, timeout=5) as resp:
            return resp.read()
    except Exception:
        return None


# ── styles ────────────────────────────────────────────────────────────────────

def _make_styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=26,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "section_title": ParagraphStyle(
            "section_title",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=18,
            textColor=GOLD,
            alignment=TA_CENTER,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "subsection_title": ParagraphStyle(
            "subsection_title",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=GREEN,
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=DARK,
            spaceAfter=2,
        ),
        "value": ParagraphStyle(
            "value",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=DARK,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=DARK,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "conclusion_value": ParagraphStyle(
            "conclusion_value",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=20,
            textColor=GREEN,
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "conclusion_words": ParagraphStyle(
            "conclusion_words",
            fontName="Helvetica-Oblique",
            fontSize=10,
            leading=14,
            textColor=DARK,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "sig_line": ParagraphStyle(
            "sig_line",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=DARK,
            alignment=TA_CENTER,
        ),
    }


# ── page template (header band + footer) ─────────────────────────────────────

class _RomaTecDoc(BaseDocTemplate):
    """Custom doc template that draws header and footer on every page."""

    def __init__(self, buf: io.BytesIO):
        self.styles = _make_styles()
        margin_lr = 2.0 * cm
        margin_tb = 2.5 * cm
        header_h = 1.6 * cm
        footer_h = 1.0 * cm

        super().__init__(
            buf,
            pagesize=A4,
            leftMargin=margin_lr,
            rightMargin=margin_lr,
            topMargin=margin_tb + header_h,
            bottomMargin=margin_tb + footer_h,
        )

        page_w, page_h = A4
        content_w = page_w - 2 * margin_lr
        content_h = page_h - (margin_tb + header_h) - (margin_tb + footer_h)

        frame = Frame(
            margin_lr,
            margin_tb + footer_h,
            content_w,
            content_h,
            id="content",
        )
        template = PageTemplate(id="main", frames=[frame], onPage=self._on_page)
        self.addPageTemplates([template])

    # called by reportlab for every page
    def _on_page(self, canvas, doc):
        canvas.saveState()
        page_w, page_h = A4
        header_h = 1.6 * cm
        footer_h = 0.9 * cm
        margin = 2.0 * cm

        # ── header band ────────────────────────────────────────────────────
        canvas.setFillColor(GREEN)
        canvas.rect(0, page_h - header_h, page_w, header_h, fill=1, stroke=0)

        # logo in header (tiny, if available)
        if hasattr(doc, "_logo_bytes") and doc._logo_bytes:
            try:
                logo_buf = io.BytesIO(doc._logo_bytes)
                canvas.drawImage(
                    logo_buf,
                    margin,
                    page_h - header_h + 0.15 * cm,
                    width=1.2 * cm,
                    height=1.2 * cm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        # company name in header
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(WHITE)
        canvas.drawString(margin + 1.5 * cm, page_h - header_h + 0.5 * cm, "RomaTec Consultoria Total")

        # PTAM number (right side)
        ptam_num = getattr(doc, "_ptam_number", "")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(GOLD)
        canvas.drawRightString(page_w - margin, page_h - header_h + 0.5 * cm, f"PTAM nº {ptam_num}")

        # gold underline
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(0, page_h - header_h, page_w, page_h - header_h)

        # ── footer band ────────────────────────────────────────────────────
        canvas.setFillColor(GREEN)
        canvas.rect(0, 0, page_w, footer_h, fill=1, stroke=0)

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(WHITE)
        canvas.drawCentredString(
            page_w / 2,
            (footer_h - 0.3 * cm),
            "RomaTec Consultoria Total  —  NBR 14.653",
        )

        # page number (right)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GOLD)
        canvas.drawRightString(page_w - margin, (footer_h - 0.3 * cm), f"Pág. {doc.page}")

        canvas.restoreState()


# ── builder helpers ───────────────────────────────────────────────────────────

def _lv(styles, label: str, value: Any) -> list:
    """Return a label+value pair as a list of Paragraphs."""
    if value is None or str(value).strip() in ("", "0", "0.0", "0.00"):
        return []
    return [
        Paragraph(f"<b>{label}:</b> {value}", styles["value"]),
    ]


def _section(styles, text: str) -> list:
    return [
        Spacer(1, 0.3 * cm),
        Paragraph(text.upper(), styles["section_title"]),
        Spacer(1, 0.2 * cm),
    ]


def _subsection(styles, text: str) -> list:
    return [Paragraph(text, styles["subsection_title"])]


def _body(styles, text: str) -> list:
    if not text or not text.strip():
        return []
    return [Paragraph(text.replace("\n", "<br/>"), styles["body"])]


def _spacer(h: float = 0.4) -> Spacer:
    return Spacer(1, h * cm)


# ── samples table ─────────────────────────────────────────────────────────────

def _samples_table(samples: list) -> list:
    if not samples:
        return []
    headers = ["Nº", "Bairro/Local", "Área Total (m²)", "Valor (R$)", "R$/m²"]
    data = [headers]
    for idx, s in enumerate(samples, start=1):
        vps = s.get("value_per_sqm") or (
            (s.get("value") or 0) / (s.get("area_total") or 1) if s.get("area_total") else 0
        )
        data.append([
            str(s.get("number") or idx),
            s.get("neighborhood", "") or "",
            _fmt_area(s.get("area_total", 0)).replace(" m²", ""),
            _fmt_currency(s.get("value", 0)).replace("R$ ", ""),
            f"{float(vps):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        ])

    col_widths = [1.2 * cm, 5.5 * cm, 3.5 * cm, 3.5 * cm, 3.0 * cm]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREEN]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C0C0C0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    return [tbl, _spacer(0.3)]


# ── consolidation table ───────────────────────────────────────────────────────

def _consolidation_table(impact_areas: list) -> tuple[list, float]:
    if not impact_areas:
        return [], 0.0

    headers = ["Área de Impacto", "Classificação", "Metragem", "Valor Unitário", "Indenização"]
    data = [headers]
    grand_total = 0.0

    for a in impact_areas:
        total_value = a.get("total_value") or (a.get("area_sqm", 0) * a.get("unit_value", 0))
        grand_total += float(total_value or 0)
        data.append([
            a.get("name", ""),
            a.get("classification", ""),
            _fmt_area(a.get("area_sqm", 0)),
            _fmt_currency(a.get("unit_value", 0)) + "/m²",
            _fmt_currency(total_value),
        ])

    # totals row
    data.append(["TOTAL GERAL DA INDENIZAÇÃO", "", "", "", _fmt_currency(grand_total)])

    col_widths = [4.5 * cm, 2.5 * cm, 3.0 * cm, 3.0 * cm, 3.7 * cm]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    last = len(data) - 1
    tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, last - 1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, last - 1), [WHITE, LIGHT_GREEN]),
            ("BACKGROUND", (0, last), (-1, last), LIGHT_GREEN),
            ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
            ("SPAN", (0, last), (3, last)),
            ("ALIGN", (0, last), (3, last), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C0C0C0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    return [tbl, _spacer(0.3)], grand_total


# ── cover page ────────────────────────────────────────────────────────────────

def _build_cover(ptam: dict, logo_bytes: bytes | None, styles: dict) -> list:
    story = []

    # large logo centred
    if logo_bytes:
        try:
            logo_buf = io.BytesIO(logo_bytes)
            img = Image(logo_buf, width=5 * cm, height=5 * cm)
            img.hAlign = "CENTER"
            story.append(img)
            story.append(_spacer(0.6))
        except Exception:
            pass

    # green banner with title
    title_data = [[
        Paragraph("PARECER TÉCNICO DE AVALIAÇÃO MERCADOLÓGICA", styles["cover_title"]),
    ]]
    banner = Table(title_data, colWidths=[16.5 * cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(banner)
    story.append(_spacer(0.8))

    # PTAM number
    story.append(Paragraph(
        f"<b>PTAM nº {ptam.get('number', '—')}</b>",
        ParagraphStyle("ctr_bold", fontName="Helvetica-Bold", fontSize=16, alignment=TA_CENTER,
                       textColor=GREEN, spaceAfter=4),
    ))

    # property label
    if ptam.get("property_label") or ptam.get("property_address"):
        story.append(Paragraph(
            ptam.get("property_label") or ptam.get("property_address", ""),
            ParagraphStyle("ctr_prop", fontName="Helvetica", fontSize=13, alignment=TA_CENTER,
                           textColor=DARK, spaceAfter=6),
        ))

    story.append(_spacer(0.5))

    # meta table (solicitante, cidade, data)
    meta_rows = []
    if ptam.get("solicitante"):
        meta_rows.append(["Solicitante:", ptam["solicitante"]])
    city = ptam.get("conclusion_city") or ptam.get("property_city") or ""
    date_str = ptam.get("conclusion_date") or datetime.utcnow().strftime("%d/%m/%Y")
    if city:
        meta_rows.append(["Cidade:", city])
    meta_rows.append(["Data:", date_str])

    if meta_rows:
        meta_tbl = Table(meta_rows, colWidths=[4 * cm, 12 * cm])
        meta_tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ]))
        story.append(meta_tbl)

    story.append(_spacer(1.0))

    # gold rule
    rule_data = [[""]]
    rule = Table(rule_data, colWidths=[16.5 * cm], rowHeights=[0.2 * cm])
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOLD)]))
    story.append(rule)
    story.append(_spacer(0.4))

    story.append(Paragraph(
        "RomaTec Consultoria Total  —  NBR 14.653",
        ParagraphStyle("ctr_nbr", fontName="Helvetica-Bold", fontSize=10, alignment=TA_CENTER,
                       textColor=GOLD),
    ))

    story.append(PageBreak())
    return story


# ── section builders ─────────────────────────────────────────────────────────

def _build_identification(ptam: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "1. Identificação")
    for label, key in [
        ("Finalidade", "purpose"),
        ("Solicitante", "solicitante"),
        ("Processo Judicial", "judicial_process"),
        ("Ação Judicial", "judicial_action"),
        ("Fórum", "forum"),
        ("Requerente", "requerente"),
        ("Requerido", "requerido"),
        ("Juiz", "judge"),
    ]:
        story += _lv(styles, label, ptam.get(key))
    return story


def _build_property(ptam: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "2. Imóvel Avaliando")
    for label, key in [
        ("Endereço", "property_address"),
        ("Cidade/UF", "property_city"),
        ("Matrícula", "property_matricula"),
        ("Proprietário", "property_owner"),
        ("Confrontações", "property_confrontations"),
    ]:
        story += _lv(styles, label, ptam.get(key))
    if ptam.get("property_area_ha"):
        story += _lv(styles, "Área (ha)", ptam["property_area_ha"])
    if ptam.get("property_area_sqm"):
        story += _lv(styles, "Área (m²)", _fmt_area(ptam["property_area_sqm"]))
    story += _body(styles, ptam.get("property_description", ""))
    return story


def _build_vistoria(ptam: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "3. Vistoria")
    story += _lv(styles, "Data da Vistoria", ptam.get("vistoria_date"))

    for sub_title, key in [
        ("1. Objetivo da Vistoria", "vistoria_objective"),
        ("2. Metodologia Adotada", "vistoria_methodology"),
    ]:
        story += _subsection(styles, sub_title)
        story += _body(styles, ptam.get(key, ""))

    story += _subsection(styles, "3. Caracterização Física")
    story += _lv(styles, "3.1 Topografia", ptam.get("topography"))
    story += _lv(styles, "3.2 Solo e Cobertura Vegetal", ptam.get("soil_vegetation"))

    for sub_title, key in [
        ("4. Benfeitorias Existentes", "benfeitorias"),
        ("5. Acessibilidade e Infraestrutura", "accessibility"),
        ("6. Contexto Urbano e Mercadológico", "urban_context"),
        ("7. Estado Geral de Conservação", "conservation_state"),
        ("8. Síntese Conclusiva da Vistoria", "vistoria_synthesis"),
    ]:
        story += _subsection(styles, sub_title)
        story += _body(styles, ptam.get(key, ""))

    return story


def _build_market_analysis(ptam: dict, styles: dict) -> list:
    if not ptam.get("market_analysis"):
        return []
    story = []
    story += _section(styles, "4. Análise Mercadológica")
    story += _body(styles, ptam.get("market_analysis", ""))
    return story


def _build_methodology(ptam: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "5. Metodologia")
    story += _lv(styles, "Método Utilizado", ptam.get("methodology"))
    story += _body(styles, ptam.get("methodology_justification", ""))
    return story


def _build_impact_areas(ptam: dict, styles: dict) -> list:
    areas = ptam.get("impact_areas", []) or []
    if not areas:
        return []

    story = []
    story += _section(styles, "6. Áreas de Impacto e Amostras")

    for idx, area in enumerate(areas, start=1):
        name = area.get("name") or f"Área de Impacto {idx:02d}"
        story += _subsection(styles, f"{name} — {area.get('classification', '')}")
        story += _lv(styles, "Área Impactada", _fmt_area(area.get("area_sqm", 0)))
        story += _lv(styles, "Valor Unitário Adotado", _fmt_currency(area.get("unit_value", 0)) + "/m²")
        total_v = area.get("total_value") or (area.get("area_sqm", 0) * area.get("unit_value", 0))
        story += _lv(styles, "Valor Indenizatório", _fmt_currency(total_v))
        if area.get("majoration_note"):
            story += _lv(styles, "Majoração Aplicada", area.get("majoration_note"))
        story += _body(styles, area.get("notes", ""))

        samples = area.get("samples", []) or []
        if samples:
            story += _subsection(styles, "Amostragem")
            story += _samples_table(samples)

        story.append(_spacer(0.4))

    # consolidation table
    story += _subsection(styles, "Consolidação das Indenizações")
    tbl_elements, grand_total = _consolidation_table(areas)
    story += tbl_elements

    return story


def _build_conclusion(ptam: dict, user: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "7. Conclusão")
    story += _body(styles, ptam.get("conclusion_text", ""))

    if ptam.get("total_indemnity"):
        story.append(_spacer(0.4))
        story.append(Paragraph(
            f"Valor Total da Indenização: {_fmt_currency(ptam.get('total_indemnity', 0))}",
            styles["conclusion_value"],
        ))
        if ptam.get("total_indemnity_words"):
            story.append(Paragraph(
                f"({ptam['total_indemnity_words']})",
                styles["conclusion_words"],
            ))

    # location and date
    city = ptam.get("conclusion_city", "")
    date_str = ptam.get("conclusion_date", datetime.utcnow().strftime("%d/%m/%Y"))
    if city or date_str:
        story.append(_spacer(0.6))
        loc_text = f"{city}, {date_str}." if city else date_str
        story.append(Paragraph(loc_text, ParagraphStyle(
            "loc", fontName="Helvetica", fontSize=10, alignment=TA_RIGHT, textColor=DARK,
        )))

    # signature block
    story.append(_spacer(1.5))
    sig_line_data = [["_" * 45]]
    sig_line_tbl = Table(sig_line_data, colWidths=[10 * cm])
    sig_line_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    sig_line_tbl.hAlign = "CENTER"
    story.append(sig_line_tbl)

    name = user.get("name", "")
    role = user.get("role", "")
    crea = user.get("crea", "")

    if name:
        story.append(Paragraph(f"<b>{name}</b>", styles["sig_line"]))
    if role:
        story.append(Paragraph(role, styles["sig_line"]))
    if crea:
        story.append(Paragraph(crea, styles["sig_line"]))

    return story


# ── main entry point ──────────────────────────────────────────────────────────

def generate_ptam_pdf(ptam: dict, user: dict) -> bytes:
    """Generate a PDF from PTAM data. Returns bytes."""
    buf = io.BytesIO()
    logo_bytes = _fetch_logo()

    doc = _RomaTecDoc(buf)
    doc._logo_bytes = logo_bytes
    doc._ptam_number = ptam.get("number", "")

    styles = _make_styles()

    story: list = []

    # ── cover ────────────────────────────────────────────────────────────
    story += _build_cover(ptam, logo_bytes, styles)

    # ── sections ─────────────────────────────────────────────────────────
    story += _build_identification(ptam, styles)
    story.append(_spacer(0.5))

    story += _build_property(ptam, styles)
    story.append(_spacer(0.5))

    story += _build_vistoria(ptam, styles)
    story.append(PageBreak())

    story += _build_market_analysis(ptam, styles)
    if ptam.get("market_analysis"):
        story.append(_spacer(0.5))

    story += _build_methodology(ptam, styles)
    story.append(_spacer(0.5))

    story += _build_impact_areas(ptam, styles)
    story.append(_spacer(0.5))

    story += _build_conclusion(ptam, user, styles)

    doc.build(story)
    return buf.getvalue()
