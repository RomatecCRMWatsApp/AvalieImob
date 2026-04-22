"""PDF generator for PTAM documents — RomaTec branding.

Uses reportlab to produce a professional, print-ready PDF with:
  - Cover page with logo, title, PTAM number and city/date
  - 11 content sections matching the PTAM model (ABNT NBR 14653)
  - Tables for market samples and consolidation
  - Green (#1B4D1B) header band on every page + gold (#D4A830) section titles
  - Footer with full legal basis on every page
  - Signature block at the end (evaluator name, CRECI/CREA/CAU, ART/RRT)

Normative references:
  ABNT NBR 14653-1, -2, -3 | Res. COFECI 957/2006
  Lei 5.194/1966 | Lei 6.530/1978 | Res. CONFEA 345/90
  Lei 13.786/2018 | CPC art. 156
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

    def __init__(self, buf: io.BytesIO, company_logo_bytes: bytes | None = None):
        self.styles = _make_styles()
        self._company_logo_bytes = company_logo_bytes
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

        # logo in header: prefer company logo, fall back to system logo
        logo_bytes_to_use = self._company_logo_bytes or (doc._logo_bytes if hasattr(doc, "_logo_bytes") else None)
        if logo_bytes_to_use:
            try:
                logo_buf = io.BytesIO(logo_bytes_to_use)
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
        elif hasattr(doc, "_logo_bytes") and doc._logo_bytes:
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

        # company name in header (prefer user company name, fall back to default)
        header_company = getattr(doc, "_company_name", "") or "RomaTec Consultoria Total"
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(WHITE)
        canvas.drawString(margin + 1.5 * cm, page_h - header_h + 0.5 * cm, header_company)

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

        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(WHITE)
        canvas.drawCentredString(
            page_w / 2,
            (footer_h - 0.3 * cm),
            "RomaTec Consultoria Total  —  ABNT NBR 14653-1/-2/-3  |  Res. COFECI 957/2006  |  Lei 5.194/66  |  Lei 6.530/78  |  Res. CONFEA 345/90  |  Lei 13.786/2018  |  CPC art. 156",
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
    ptam_display_num = ptam.get("numero_ptam") or ptam.get("number") or "—"
    story.append(Paragraph(
        f"<b>PTAM nº {ptam_display_num}</b>",
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

    # normative reference block
    story.append(_spacer(0.3))
    norm_text = (
        "<b>Base normativa:</b> ABNT NBR 14653-1 (Procedimentos Gerais) | NBR 14653-2 (Imóveis Urbanos) | "
        "NBR 14653-3 (Imóveis Rurais) | Res. COFECI 957/2006 | Lei 5.194/1966 | Lei 6.530/1978 | "
        "Res. CONFEA 345/90 | Lei 13.786/2018 | CPC art. 156"
    )
    story.append(Paragraph(norm_text, ParagraphStyle(
        "norm_ref", fontName="Helvetica", fontSize=8, alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"), spaceAfter=4,
    )))

    story.append(PageBreak())
    return story


# ── section builders ─────────────────────────────────────────────────────────

def _build_identification(ptam: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "1. Identificação e Objetivo")

    # Número do PTAM
    num_ptam = ptam.get("numero_ptam") or ptam.get("number") or ""
    if num_ptam:
        story += _lv(styles, "Número do PTAM", num_ptam)

    # Tipo de avaliação / finalidade
    finalidade_map = {
        # Compra e Venda
        "cv_alienacao": "Compra e Venda — Alienação",
        "cv_aquisicao": "Compra e Venda — Aquisição",
        "cv_oferta": "Compra e Venda — Oferta Pública",
        "cv_dacao": "Compra e Venda — Dação em Pagamento",
        # Garantia Bancária
        "gar_sfh": "Garantia Bancária — Financiamento SFH",
        "gar_sfi": "Garantia Bancária — Financiamento SFI",
        "gar_credito_rural": "Garantia Bancária — Crédito Rural (Penhor Rural)",
        "gar_refinanciamento": "Garantia Bancária — Refinanciamento",
        "gar_lci_cri": "Garantia Bancária — LCI / CRI",
        "gar_ccb": "Garantia Bancária — CCB Imobiliária",
        # Judicial / Pericial
        "judicial_partilha": "Judicial — Partilha de Bens (Inventário / Divórcio)",
        "judicial_desapropriacao": "Judicial — Desapropriação",
        "judicial_indenizacao": "Judicial — Ação de Indenização",
        "judicial_execucao": "Judicial — Execução de Sentença",
        "judicial_usucapiao": "Judicial — Usucapião",
        "judicial_pericia": "Perícia Judicial (CPC art. 156)",
        # Locação
        "loc_fixacao": "Locação — Fixação de Aluguel",
        "loc_revisao": "Locação — Revisão de Aluguel (Lei 8.245/91)",
        "loc_renovatoria": "Locação — Ação Renovatória",
        # Seguros
        "seg_reposicao": "Seguros — Valor de Reposição",
        "seg_sinistro": "Seguros — Sinistro",
        "seg_risco": "Seguros — Valor em Risco",
        # Tributário / Fiscal
        "trib_itbi": "Tributário — Base de Cálculo ITBI",
        "trib_itcmd": "Tributário — Base de Cálculo ITCMD (Herança / Doação)",
        "trib_ir": "Tributário — Imposto de Renda (Ganho de Capital)",
        "trib_iptu_itr": "Tributário — IPTU / ITR Progressivo",
        # Incorporação e Registro
        "inc_registro": "Incorporação — Registro (Lei 4.591/64)",
        "inc_afetacao": "Incorporação — Patrimônio de Afetação (Lei 13.786/2018)",
        "inc_permuta": "Incorporação — Permuta",
        # Execução de Garantia
        "exec_fid_1": "Execução de Garantia — Alienação Fiduciária 1º Leilão (Lei 9.514/97 art. 27)",
        "exec_fid_2": "Execução de Garantia — Alienação Fiduciária 2º Leilão",
        "exec_hipoteca": "Execução de Garantia — Execução Hipotecária",
        "exec_consolidacao": "Execução de Garantia — Consolidação da Propriedade",
        # Desapropriação
        "desap_utilidade": "Desapropriação por Utilidade Pública (Dec.-Lei 3.365/41)",
        "desap_interesse_social": "Desapropriação por Interesse Social (Lei 4.132/62)",
        "desap_reforma_agraria": "Desapropriação — Reforma Agrária (LC 76/93)",
        # Regularização Fundiária
        "reurb_s_e": "Regularização Fundiária — REURB-S / REURB-E (Lei 13.465/2017)",
        "reurb_demarcacao": "Regularização Fundiária — Demarcação Urbanística",
        # Outros
        "outros_contab": "Contabilidade / Balanço Patrimonial (CPC 28 / IFRS 13)",
        "outros_fii": "Fundo de Investimento Imobiliário (FII)",
        "outros_ma": "Fusão e Aquisição (M&A)",
        "outros_bts": "Locação Built to Suit",
        "outros_diligencia": "Due Diligence Imobiliária",
        # Legacy values
        "compra_venda": "Compra e Venda",
        "financiamento": "Financiamento / Garantia Bancária",
        "judicial": "Uso Judicial / Inventário",
        "inventario": "Inventário / Partilha",
        "locacao": "Locação",
        "garantia": "Garantia de Crédito",
        "permuta": "Permuta",
        "outros": "Outros",
    }
    finalidade_val = ptam.get("finalidade", "")
    finalidade_str = finalidade_map.get(finalidade_val, finalidade_val) or ptam.get("purpose", "")
    if finalidade_str:
        story += _lv(styles, "Finalidade", finalidade_str)
    if ptam.get("finalidade_outros"):
        story += _lv(styles, "Especificação", ptam["finalidade_outros"])

    for label, key in [
        ("Solicitante", "solicitante_nome"),
        ("CPF/CNPJ", "solicitante_cpf_cnpj"),
        ("Endereço do Solicitante", "solicitante_endereco"),
        ("Telefone", "solicitante_telefone"),
        ("E-mail", "solicitante_email"),
        ("Processo Judicial", "judicial_process"),
        ("Ação Judicial", "judicial_action"),
        ("Fórum", "forum"),
        ("Requerente", "requerente"),
        ("Requerido", "requerido"),
        ("Juiz", "judge"),
    ]:
        story += _lv(styles, label, ptam.get(key))
    # Legacy fallback
    if not ptam.get("solicitante_nome") and ptam.get("solicitante"):
        story += _lv(styles, "Solicitante", ptam["solicitante"])
    return story


def _build_documentos_analisados(ptam: dict, styles: dict) -> list:
    """Seção 2: Documentação Analisada — NBR 14653."""
    docs = ptam.get("documentos_analisados") or []
    docs_label = {
        "matricula": "Matrícula do imóvel",
        "IPTU": "Carnê de IPTU",
        "planta": "Planta / Projeto aprovado",
        "escritura": "Escritura / Contrato",
        "fotos": "Fotografias do imóvel",
        "habite_se": "Habite-se / Auto de conclusão",
        "geo_rural": "Georreferenciamento (rural)",
        "outros_docs": "Outros documentos",
    }
    # também conta fotos_imovel e fotos_documentos
    fotos_count = len(ptam.get("fotos_imovel") or [])
    doc_count = len(ptam.get("fotos_documentos") or [])

    story = []
    story += _section(styles, "2. Documentação Analisada")
    if docs:
        items_text = " | ".join(docs_label.get(d, d) for d in docs)
        story.append(Paragraph(items_text, styles["value"]))
    if fotos_count > 0:
        story += _lv(styles, "Fotos do imóvel", f"{fotos_count} foto(s) anexada(s)")
    if doc_count > 0:
        story += _lv(styles, "Documentos digitalizados", f"{doc_count} arquivo(s) anexado(s)")
    if not docs and fotos_count == 0 and doc_count == 0:
        story.append(Paragraph("Documentação não especificada.", styles["body"]))
    return story


RURAL_PROPERTY_TYPES = {"rural", "fazenda", "sitio", "chacara", "terreno_rural"}


def _is_rural(ptam: dict) -> bool:
    return str(ptam.get("property_type", "")).lower() in RURAL_PROPERTY_TYPES


def _fmt_area_ha(v: Any) -> str:
    try:
        return f"{float(v):,.4f} ha".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,0000 ha"


def _build_property(ptam: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "3. Identificação do Imóvel")
    rural = _is_rural(ptam)

    for label, key in [
        ("Tipo", "property_type"),
        ("Endereço", "property_address"),
        ("Bairro", "property_neighborhood"),
        ("Cidade/UF", "property_city"),
        ("CEP", "property_cep"),
        ("Matrícula", "property_matricula"),
        ("Cartório", "property_cartorio"),
        ("Proprietário", "property_owner"),
        ("Confrontações", "property_confrontations"),
    ]:
        story += _lv(styles, label, ptam.get(key))

    # Proprietários detalhados (lista dinâmica)
    proprietarios = ptam.get("proprietarios") or []
    proprietarios_validos = [p for p in proprietarios if isinstance(p, dict) and p.get("nome")]
    if proprietarios_validos:
        story += _subsection(styles, "Proprietário(s) do Imóvel")
        prop_headers = ["Nome / Razão Social", "CPF / CNPJ", "Fração / Percentual"]
        prop_data = [prop_headers] + [
            [
                p.get("nome", ""),
                p.get("cpf_cnpj", ""),
                p.get("percentual", ""),
            ]
            for p in proprietarios_validos
        ]
        prop_col_widths = [7.0 * cm, 5.0 * cm, 4.5 * cm]
        prop_tbl = Table(prop_data, colWidths=prop_col_widths, repeatRows=1)
        prop_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREEN]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C0C0C0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(prop_tbl)
        story.append(_spacer(0.3))

    # Área: rural → ha (prioritário), urbano → m²
    if rural:
        if ptam.get("property_area_ha"):
            story += _lv(styles, "Área total", _fmt_area_ha(ptam["property_area_ha"]))
        if ptam.get("property_area_sqm"):
            story += _lv(styles, "Área construída / benfeitorias (m²)", _fmt_area(ptam["property_area_sqm"]))
        if ptam.get("perimetro_m"):
            story += _lv(styles, "Perímetro", f"{float(ptam['perimetro_m']):,.2f} m".replace(",", "X").replace(".", ",").replace("X", "."))
    else:
        if ptam.get("property_area_sqm"):
            story += _lv(styles, "Área (m²)", _fmt_area(ptam["property_area_sqm"]))
        if ptam.get("property_area_ha"):
            story += _lv(styles, "Área (ha)", _fmt_area_ha(ptam["property_area_ha"]))

    if ptam.get("property_gps_lat") and ptam.get("property_gps_lng"):
        story += _lv(styles, "Coordenadas GPS", f"{ptam['property_gps_lat']}, {ptam['property_gps_lng']}")
    story += _body(styles, ptam.get("property_description", ""))

    # Seção de Registros Rurais — apenas para imóvel rural
    if rural:
        rural_docs = [
            ("SIGEF — Sistema de Gestão Fundiária", "certificacao_sigef"),
            ("INCRA — Cadastro no INCRA", "cadastro_incra"),
            ("CCIR — Certificado de Cadastro de Imóvel Rural", "ccir"),
            ("NIRF / CIB — Receita Federal / Cadastro Imobiliário Brasileiro", "nirf_cib"),
            ("CAR — Cadastro Ambiental Rural", "car"),
        ]
        rural_items = [(lbl, ptam.get(key)) for lbl, key in rural_docs if ptam.get(key)]
        if rural_items:
            story += _subsection(styles, "Registros Rurais")
            for lbl, val in rural_items:
                story += _lv(styles, lbl, val)

    return story


def _build_vistoria(ptam: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "4. Vistoria Técnica")
    story += _lv(styles, "Data da Vistoria", ptam.get("vistoria_date"))
    if ptam.get("vistoria_responsavel"):
        story += _lv(styles, "Responsável pela Vistoria", ptam["vistoria_responsavel"])
    if ptam.get("vistoria_condicoes"):
        story += _lv(styles, "Condições de Acesso", ptam["vistoria_condicoes"])

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


def _build_regiao(ptam: dict, styles: dict) -> list:
    """Seção 5: Análise da Região — infraestrutura, zoneamento, liquidez."""
    story = []
    story += _section(styles, "5. Análise da Região")

    # Zoneamento conforme Plano Diretor
    if ptam.get("zoneamento"):
        story += _lv(styles, "Zoneamento (Plano Diretor)", ptam["zoneamento"])

    for label, key in [
        ("Infraestrutura Urbana", "regiao_infraestrutura"),
        ("Serviços Públicos", "regiao_servicos_publicos"),
        ("Uso Predominante do Solo", "regiao_uso_predominante"),
        ("Padrão Construtivo da Região", "regiao_padrao_construtivo"),
        ("Tendência de Mercado", "regiao_tendencia_mercado"),
        ("Observações Complementares", "regiao_observacoes"),
    ]:
        if ptam.get(key):
            story += _subsection(styles, label)
            story += _body(styles, ptam[key])

    # legacy fields
    for label, key in [
        ("Contexto Urbano", "urban_context"),
    ]:
        if ptam.get(key) and not ptam.get("regiao_infraestrutura"):
            story += _lv(styles, label, ptam.get(key))

    return story if len(story) > 3 else []


def _market_samples_table(samples: list) -> list:
    """Table of market_samples (new PTAM model) — Seção 6."""
    if not samples:
        return []
    headers = ["Nº", "Endereço / Bairro", "Área (m²)", "Valor (R$)", "R$/m²", "Tipo", "Fonte", "Data Coleta"]
    data = [headers]
    for idx, s in enumerate(samples, start=1):
        vps = float(s.get("value_per_sqm") or 0)
        tipo_raw = s.get("tipo_amostra") or "oferta"
        tipo_label = "Consolidada" if tipo_raw == "consolidada" else "Oferta"
        data.append([
            str(idx),
            f"{s.get('address', '')} / {s.get('neighborhood', '')}".strip(" /"),
            f"{float(s.get('area') or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            _fmt_currency(s.get("value", 0)).replace("R$ ", ""),
            f"{vps:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            tipo_label,
            s.get("source", "") or "",
            s.get("collection_date", "") or "",
        ])
    col_widths = [0.8 * cm, 4.5 * cm, 2.0 * cm, 2.3 * cm, 1.8 * cm, 2.0 * cm, 2.2 * cm, 1.6 * cm]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREEN]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C0C0C0")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ALIGN", (6, 1), (6, -1), "LEFT"),
    ]))
    return [tbl, _spacer(0.3)]


def _build_market_analysis(ptam: dict, styles: dict) -> list:
    market_samples = ptam.get("market_samples") or []
    market_analysis = ptam.get("market_analysis", "") or ""
    if not market_samples and not market_analysis:
        return []
    story = []
    story += _section(styles, "6. Homogeneização e Amostras de Mercado")
    story += _body(styles, market_analysis)
    if market_samples:
        story += _subsection(styles, "Elementos de Comparação Coletados (NBR 14653-2 item 8.2)")
        story += _market_samples_table(market_samples)
        # Stats summary
        values = [float(s.get("value_per_sqm") or 0) for s in market_samples if s.get("value_per_sqm")]
        if values:
            n = len(values)
            avg = sum(values) / n
            sorted_v = sorted(values)
            median = (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2 if n % 2 == 0 else sorted_v[n // 2]
            variance = sum((v - avg) ** 2 for v in values) / n
            std = variance ** 0.5
            cv = (std / avg * 100) if avg > 0 else 0
            stats_text = (
                f"<b>Estatísticas:</b> n={n} | Média: R$ {avg:,.2f}/m² | Mediana: R$ {median:,.2f}/m² | "
                f"Desvio Padrão: R$ {std:,.2f} | CV: {cv:.2f}%"
            ).replace(",", "X").replace(".", ",").replace("X", ".")
            story.append(Paragraph(stats_text, styles["value"]))
    return story


def _build_ponderancia(ptam: dict, styles: dict) -> list:
    """Seção 8b: Cálculo de Ponderância — filtragem 50%/150% da média."""
    media = ptam.get("ponderancia_media")
    lim_inf = ptam.get("ponderancia_limite_inf")
    lim_sup = ptam.get("ponderancia_limite_sup")
    eliminadas = ptam.get("ponderancia_eliminadas") or []
    valor_final = ptam.get("ponderancia_valor_final")
    market_samples = ptam.get("market_samples") or []

    # Only render if there was a calculation or samples exist
    if not media and not market_samples:
        return []

    story = []
    story += _section(styles, "8b. Cálculo de Ponderância")
    story.append(Paragraph(
        "Método comparativo com filtragem de amostras fora da faixa de 50% a 150% da média simples (Norma ABNT NBR 14653-2).",
        styles["body"],
    ))
    story.append(_spacer(0.2))

    # Amostras table with status
    valid_samples = [s for s in market_samples if float(s.get("area") or 0) > 0 and float(s.get("value") or 0) > 0]
    if valid_samples:
        story += _subsection(styles, "Quadro de Amostras com Classificação")
        headers = ["Nº", "Bairro / Local", "Área (m²)", "Valor (R$)", "R$/m²", "Situação"]
        data = [headers]
        RED_LIGHT = colors.HexColor("#FFEBEE")
        GREEN_LIGHT = colors.HexColor("#E8F5E9")
        row_styles = []
        for idx, s in enumerate(valid_samples, start=0):
            vpm = float(s.get("value_per_sqm") or 0)
            if vpm == 0 and float(s.get("area") or 0) > 0:
                vpm = float(s.get("value") or 0) / float(s.get("area") or 1)
            eliminada = idx in eliminadas
            situacao = "ELIMINADA" if eliminada else "OK"
            row_color = RED_LIGHT if eliminada else (GREEN_LIGHT if media else WHITE)
            row_styles.append(("BACKGROUND", (0, idx + 1), (-1, idx + 1), row_color))
            if eliminada:
                row_styles.append(("TEXTCOLOR", (0, idx + 1), (-1, idx + 1), colors.HexColor("#C62828")))
            data.append([
                str(idx + 1),
                f"{s.get('address', '')} / {s.get('neighborhood', '')}".strip(" /") or "—",
                f"{float(s.get('area') or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                _fmt_currency(s.get("value", 0)).replace("R$ ", ""),
                f"{vpm:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                situacao,
            ])

        col_widths = [0.8 * cm, 5.0 * cm, 2.2 * cm, 2.5 * cm, 2.0 * cm, 2.2 * cm]
        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        base_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C0C0C0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ]
        tbl.setStyle(TableStyle(base_styles + row_styles))
        story.append(tbl)
        story.append(_spacer(0.3))

    # Results summary
    if media:
        story += _subsection(styles, "Resultado do Cálculo de Ponderância")
        restantes = len(valid_samples) - len(eliminadas)
        rows = []
        if lim_inf is not None:
            rows.append(["Limite Inferior (50% da média):", _fmt_currency(lim_inf) + "/m²"])
        if lim_sup is not None:
            rows.append(["Limite Superior (150% da média):", _fmt_currency(lim_sup) + "/m²"])
        rows.append(["Amostras eliminadas:", str(len(eliminadas))])
        rows.append(["Amostras restantes (válidas):", str(restantes)])
        rows.append(["Fórmula:", f"Σ R$/m² das amostras restantes / {restantes}"])
        summary_tbl = Table(rows, colWidths=[8.0 * cm, 7.7 * cm])
        summary_tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GREEN]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
        ]))
        story.append(summary_tbl)
        story.append(_spacer(0.3))

        # Média ponderada final em destaque
        story.append(Paragraph(
            f"Média Ponderada Final: <b>{_fmt_currency(media)}/m²</b>",
            ParagraphStyle("pond_media", fontName="Helvetica-Bold", fontSize=12,
                           alignment=TA_CENTER, textColor=GREEN, spaceBefore=6, spaceAfter=4),
        ))

    # Valor final do imóvel
    if valor_final:
        story.append(_spacer(0.2))
        story.append(Paragraph(
            f"Valor do Imóvel Avaliando: <b>{_fmt_currency(valor_final)}</b>",
            ParagraphStyle("pond_valor", fontName="Helvetica-Bold", fontSize=13,
                           alignment=TA_CENTER, textColor=GOLD, spaceBefore=4, spaceAfter=6),
        ))

    return story


def _fmt_brl(value) -> str:
    """Formata valor em reais no padrão pt-BR: R$ 1.234,56"""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    int_part = int(v)
    dec_part = round((v - int_part) * 100)
    formatted = f"{int_part:,}".replace(",", ".")
    return f"R$ {formatted},{dec_part:02d}"


_METODO_LABELS = {
    "ross_heidecke":   "Método Ross-Heidecke (Depreciação)",
    "linha_reta":      "Método da Linha Reta (Depreciação)",
    "fatores_terreno": "Método dos Fatores de Terreno Urbano",
    "nbr_rural":       "Método NBR 14653-3 — Rural / VTN / INCRA",
    "renda":           "Método da Renda (Capitalização)",
}


def _build_metodo_avaliacao(ptam: dict, styles: dict) -> list:
    """Seção 8c: Método de Avaliação — Depreciação e Valorização."""
    metodo = ptam.get("metodo_avaliacao")
    valor_total = ptam.get("valor_total_metodo")

    if not metodo or valor_total is None:
        return []

    story = []
    story += _section(styles, "8c. Método de Avaliação — Depreciação e Valorização")
    label = _METODO_LABELS.get(metodo, metodo)
    story.append(Paragraph(f"<b>Método utilizado:</b> {label}", styles["body"]))
    story.append(_spacer(0.2))

    params = ptam.get("metodo_params") or {}

    # ── Parâmetros por método ──────────────────────────────────────────────────
    if metodo == "ross_heidecke":
        dep_pct  = ptam.get("depreciacao_percentual") or 0
        val_dep  = ptam.get("valor_depreciacao") or 0
        val_novo = params.get("valor_novo") or 0
        estado   = params.get("estado", "—")
        vida_util = params.get("vida_util", 60)
        idade    = params.get("idade_atual", 0)
        rows = [
            ["Parâmetro", "Valor"],
            ["Valor de Novo", _fmt_brl(val_novo)],
            ["Idade Atual", f"{idade} anos"],
            ["Vida Útil", f"{vida_util} anos"],
            ["Estado de Conservação", estado],
            ["Coeficiente de Depreciação (Kd)", f"{dep_pct:.2f}%"],
            ["Valor da Depreciação", _fmt_brl(val_dep)],
        ]
    elif metodo == "linha_reta":
        dep_pct  = ptam.get("depreciacao_percentual") or 0
        val_dep  = ptam.get("valor_depreciacao") or 0
        val_novo = params.get("valor_novo") or 0
        rows = [
            ["Parâmetro", "Valor"],
            ["Valor de Novo", _fmt_brl(val_novo)],
            ["Valor Residual (%)", f"{params.get('residual_pct', 20):.1f}%"],
            ["Vida Útil", f"{params.get('vida_util', 40)} anos"],
            ["Idade Atual", f"{params.get('idade_atual', 0)} anos"],
            ["Depreciação Acumulada", _fmt_brl(val_dep)],
        ]
    elif metodo == "fatores_terreno":
        rows = [
            ["Parâmetro", "Valor"],
            ["Valor Unitário de Referência (R$/m²)", _fmt_brl(params.get("valor_unitario", 0))],
            ["Área do Terreno (m²)", f"{params.get('area_terreno', 0):,.2f} m²".replace(",", ".")],
            ["Fator Localização", str(params.get("f_loc", "1.00"))],
            ["Fator Topografia", str(params.get("f_topo", "1.00"))],
            ["Testada (m)", f"{params.get('testada_m', 0)} m"],
            ["Fator Infraestrutura", str(params.get("f_infra", "1.00"))],
        ]
    elif metodo == "nbr_rural":
        val_terra = ptam.get("valor_terreno_calc") or 0
        rows = [
            ["Parâmetro", "Valor"],
            ["Área Total (ha)", f"{params.get('area_ha', 0):,.4f} ha".replace(",", ".")],
            ["VTN — Valor por Hectare", _fmt_brl(params.get("vtn_hectare", 0))],
            ["Classe de Uso / CUF", str(params.get("classe_uso", "1.00"))],
            ["Valor da Terra Nua", _fmt_brl(val_terra)],
            ["Benfeitorias Rurais", _fmt_brl(params.get("benfeitorias_rurais", 0))],
            ["Cultura Permanente", _fmt_brl(params.get("cultura_permanente", 0))],
            ["Cultura Temporária", _fmt_brl(params.get("cultura_temporaria", 0))],
        ]
    elif metodo == "renda":
        rows = [
            ["Parâmetro", "Valor"],
            ["Renda Mensal", _fmt_brl(params.get("renda_mensal", 0))],
            ["Renda Anual", _fmt_brl(float(params.get("renda_mensal", 0)) * 12)],
            ["Taxa de Capitalização", f"{params.get('taxa_cap', 8):.2f}% a.a."],
            ["Tipo de Cálculo", "Perpetuidade" if params.get("tipo", "perpetuidade") == "perpetuidade" else f"Prazo de {params.get('prazo_anos', 0)} anos"],
        ]
    else:
        rows = [["Parâmetro", "Valor"]]

    if len(rows) > 1:
        story += _subsection(styles, "Parâmetros Utilizados")
        tbl = Table(rows, colWidths=[220, 220])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4332")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0FAF4")]),
            ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#C8E6C9")),
            ("ALIGN",      (1, 1), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",  (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        story.append(_spacer(0.3))

    # ── Resultado consolidado ──────────────────────────────────────────────────
    story += _subsection(styles, "Resultado Consolidado")
    result_rows = [["Componente", "Valor"]]
    val_terreno = ptam.get("valor_terreno_calc")
    val_benf    = ptam.get("valor_benfeitoria")
    dep_pct_v   = ptam.get("depreciacao_percentual")
    val_dep_v   = ptam.get("valor_depreciacao")

    if val_terreno:
        result_rows.append(["Valor do Terreno / Terra Nua", _fmt_brl(val_terreno)])
    if val_benf:
        result_rows.append(["Benfeitorias (depreciado)", _fmt_brl(val_benf)])
    if dep_pct_v:
        result_rows.append([f"Depreciação ({dep_pct_v:.2f}%)", _fmt_brl(val_dep_v)])
    result_rows.append(["VALOR TOTAL (Terreno + Benfeitorias)", _fmt_brl(valor_total)])

    tbl2 = Table(result_rows, colWidths=[280, 160])
    tbl2.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#1B4332")),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F0FAF4")]),
        ("BACKGROUND",  (0, -1), (-1, -1), colors.HexColor("#FFF9C4")),
        ("FONTNAME",    (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, -1), (-1, -1), colors.HexColor("#7B4F00")),
        ("FONTSIZE",    (0, -1), (-1, -1), 10),
        ("GRID",        (0, 0),  (-1, -1), 0.4, colors.HexColor("#C8E6C9")),
        ("ALIGN",       (1, 1),  (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0),  (-1, -1), 6),
        ("RIGHTPADDING",(0, 0),  (-1, -1), 6),
        ("TOPPADDING",  (0, 0),  (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    story.append(tbl2)

    return story


def _build_methodology(ptam: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "7. Metodologia")
    story += _lv(styles, "Método Utilizado", ptam.get("methodology"))
    story += _body(styles, ptam.get("methodology_justification", ""))
    # fatores de homogeneizacao e estatisticas
    if ptam.get("calc_fatores_homogeneizacao"):
        story += _subsection(styles, "Fatores de Homogeneização Aplicados")
        story += _body(styles, ptam["calc_fatores_homogeneizacao"])
    if ptam.get("calc_grau_fundamentacao"):
        story += _lv(styles, "Grau de Fundamentação (NBR 14653-2)", ptam["calc_grau_fundamentacao"])
    if ptam.get("calc_observacoes"):
        story += _lv(styles, "Observações sobre os Cálculos", ptam["calc_observacoes"])
    return story


def _build_impact_areas(ptam: dict, styles: dict) -> list:
    areas = ptam.get("impact_areas", []) or []
    if not areas:
        return []

    story = []
    story += _section(styles, "8. Áreas de Impacto e Amostras")

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
    story += _section(styles, "9. Valor de Avaliação e Resultado")
    story += _body(styles, ptam.get("conclusion_text", ""))

    # ── Valor principal ────────────────────────────────────────────────────────
    valor_total = ptam.get("resultado_valor_total") or ptam.get("total_indemnity") or 0
    valor_unitario = ptam.get("resultado_valor_unitario") or 0
    if valor_total:
        story.append(_spacer(0.4))
        story.append(Paragraph(
            f"Valor de Mercado Avaliado: {_fmt_currency(valor_total)}",
            styles["conclusion_value"],
        ))
        if ptam.get("total_indemnity_words"):
            story.append(Paragraph(
                f"({ptam['total_indemnity_words']})",
                styles["conclusion_words"],
            ))
        if valor_unitario:
            story += _lv(styles, "Valor Unitário R$/m²", _fmt_currency(valor_unitario))

    # ── Intervalo de confiança ─────────────────────────────────────────────────
    inf_val = ptam.get("resultado_intervalo_inf") or 0
    sup_val = ptam.get("resultado_intervalo_sup") or 0
    if inf_val and sup_val:
        story += _lv(styles, "Intervalo de Confiança", f"{_fmt_currency(inf_val)} a {_fmt_currency(sup_val)}")

    # ── Grau de Precisão — NBR 14653-1 item 9 ─────────────────────────────────
    grau_precisao = ptam.get("grau_precisao") or ""
    if grau_precisao:
        grau_desc = {"I": "Grau I — Amplitude ≤ 30%", "II": "Grau II — Amplitude ≤ 20%", "III": "Grau III — Amplitude ≤ 10%"}
        story += _lv(styles, "Grau de Precisão (NBR 14653-1 item 9)", grau_desc.get(grau_precisao, grau_precisao))

    # ── Campo de Arbítrio — NBR 14653-1 item 9.2.4 ───────────────────────────
    arb_min = ptam.get("campo_arbitrio_min") or 0
    arb_max = ptam.get("campo_arbitrio_max") or 0
    if arb_min or arb_max:
        story += _lv(
            styles, "Campo de Arbítrio (NBR 14653-1 item 9.2.4)",
            f"{_fmt_currency(arb_min)} a {_fmt_currency(arb_max)}  (variação máx. ±15%)"
        )

    # ── Data de referência ─────────────────────────────────────────────────────
    if ptam.get("resultado_data_referencia"):
        story += _lv(styles, "Data de Referência da Avaliação", ptam["resultado_data_referencia"])

    # ── Prazo de Validade ─────────────────────────────────────────────────────
    story += _section(styles, "10. Prazo de Validade do Laudo")
    prazo_meses = ptam.get("prazo_validade_meses") or 6
    prazo_str = ptam.get("resultado_prazo_validade") or f"{prazo_meses} meses"
    story.append(Paragraph(
        f"Este Parecer Técnico tem validade de <b>{prazo_str}</b> a contar da data de emissão, "
        "conforme preconiza a ABNT NBR 14653-1. Após esse período, nova avaliação deverá ser realizada.",
        styles["body"],
    ))

    # ── Considerações, Ressalvas e Pressupostos ───────────────────────────────
    if ptam.get("consideracoes_ressalvas") or ptam.get("consideracoes_pressupostos") or ptam.get("consideracoes_limitacoes"):
        story += _section(styles, "10.1 Ressalvas, Pressupostos e Limitações")
        if ptam.get("consideracoes_ressalvas"):
            story += _subsection(styles, "Ressalvas")
            story += _body(styles, ptam["consideracoes_ressalvas"])
        if ptam.get("consideracoes_pressupostos"):
            story += _subsection(styles, "Pressupostos")
            story += _body(styles, ptam["consideracoes_pressupostos"])
        if ptam.get("consideracoes_limitacoes"):
            story += _subsection(styles, "Limitações")
            story += _body(styles, ptam["consideracoes_limitacoes"])

    # ── Declaração de Responsabilidade Técnica ────────────────────────────────
    story += _section(styles, "11. Declaração de Responsabilidade Técnica")

    tipo_prof = ptam.get("tipo_profissional") or user.get("role", "")
    tipo_map = {
        "corretor": "Corretor de Imóveis habilitado nos termos da Resolução COFECI 957/2006",
        "engenheiro": "Engenheiro com Anotação de Responsabilidade Técnica (ART) conforme Resolução CONFEA 345/90",
        "arquiteto": "Arquiteto e Urbanista com Registro de Responsabilidade Técnica (RRT)",
        "perito_judicial": "Perito Judicial cadastrado no Tribunal, habilitado nos termos do CPC art. 156",
    }
    tipo_desc = tipo_map.get(tipo_prof, tipo_prof)
    if tipo_desc:
        story.append(Paragraph(
            f"O(A) profissional signatário(a) deste Parecer Técnico de Avaliação Mercadológica é "
            f"<b>{tipo_desc}</b>, responsabilizando-se técnica e legalmente pelo conteúdo e pelos "
            "valores aqui expressos, conforme as normas regulamentadoras vigentes.",
            styles["body"],
        ))

    art_rrt = ptam.get("art_rrt_numero") or ""
    if art_rrt:
        story += _lv(styles, "Nº ART / RRT (Res. CONFEA 345/90)", art_rrt)

    # ── Location and date ──────────────────────────────────────────────────────
    city = ptam.get("conclusion_city", "")
    date_str = ptam.get("conclusion_date", datetime.utcnow().strftime("%d/%m/%Y"))
    if city or date_str:
        story.append(_spacer(0.6))
        loc_text = f"{city}, {date_str}." if city else date_str
        story.append(Paragraph(loc_text, ParagraphStyle(
            "loc", fontName="Helvetica", fontSize=10, alignment=TA_RIGHT, textColor=DARK,
        )))

    # ── Signature block ────────────────────────────────────────────────────────
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

    # nome preferencial: do PTAM ou do user
    name = ptam.get("responsavel_nome") or user.get("name", "")
    role = user.get("role", "")
    # registros: CRECI, CNAI, CREA/CAU
    creci = ptam.get("responsavel_creci") or user.get("crea", "")
    cnai = ptam.get("responsavel_cnai") or ""
    registro = ptam.get("registro_profissional") or ""

    if name:
        story.append(Paragraph(f"<b>{name}</b>", styles["sig_line"]))
    if role:
        story.append(Paragraph(role, styles["sig_line"]))
    if creci:
        story.append(Paragraph(creci, styles["sig_line"]))
    if cnai:
        story.append(Paragraph(cnai, styles["sig_line"]))
    if registro:
        story.append(Paragraph(registro, styles["sig_line"]))
    if art_rrt:
        story.append(Paragraph(f"ART/RRT nº {art_rrt}", styles["sig_line"]))

    return story


# ── CND: Certidões das Partes ─────────────────────────────────────────────────

_PROVIDER_LABELS = {
    "receita":      "Receita Federal",
    "pgfn":         "PGFN - Dívida Ativa",
    "tst":          "TST - Certidão Trabalhista",
    "trf1":         "TRF1 - Justiça Federal",
    "tjma":         "TJMA - Justiça Estadual",
    "cnib":         "CNIB - Indisponibilidade",
    "rfb_cadastro": "Situação Cadastral CPF/CNPJ",
}

_RESULTADO_LABELS = {
    "negativa":     "Negativa",
    "positiva":     "Positiva",
    "indisponivel": "Indisponível",
    "erro":         "Erro",
}


def _build_certidoes_partes(styles: dict, consultas_data: list) -> list:
    """Seção 'CERTIDÕES DAS PARTES' — apenas se houver consultas vinculadas."""
    if not consultas_data:
        return []

    story = []
    story += _section(styles, "Certidões das Partes")
    story.append(Paragraph(
        "Certidões Negativas de Débito (CND) consultadas junto aos órgãos oficiais para as partes envolvidas nesta avaliação.",
        styles["body"],
    ))
    story.append(_spacer(0.3))

    for item in consultas_data:
        consulta = item.get("consulta", {})
        certidoes = item.get("certidoes", [])

        nome = consulta.get("nome_parte", "—")
        cpf_cnpj = consulta.get("cpf_cnpj", "—")
        tipo = consulta.get("tipo_parte", "")
        data_consulta = ""
        if consulta.get("created_at"):
            try:
                from datetime import datetime as _dt
                d = consulta["created_at"]
                if isinstance(d, str):
                    d = _dt.fromisoformat(d.replace("Z", "+00:00"))
                data_consulta = d.strftime("%d/%m/%Y")
            except Exception:
                pass

        story += _subsection(styles, f"{nome} — {tipo}" if tipo else nome)
        story += _lv(styles, "CPF/CNPJ", cpf_cnpj)
        if data_consulta:
            story += _lv(styles, "Data da Consulta", data_consulta)

        if certidoes:
            headers = ["Órgão / Certidão", "Resultado"]
            data = [headers]
            for c in certidoes:
                provider_label = _PROVIDER_LABELS.get(c.get("provider", ""), c.get("provider", "—"))
                resultado_raw = c.get("resultado") or c.get("status", "indisponivel")
                resultado_label = _RESULTADO_LABELS.get(resultado_raw, resultado_raw.capitalize())
                data.append([provider_label, resultado_label])

            col_widths = [11.0 * cm, 5.7 * cm]
            tbl = Table(data, colWidths=col_widths, repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREEN]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C0C0C0")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(tbl)
            story.append(_spacer(0.3))
        else:
            story.append(Paragraph("Nenhuma certidão retornada para esta parte.", styles["body"]))
            story.append(_spacer(0.2))

    return story


# ── main entry point ──────────────────────────────────────────────────────────

def generate_ptam_pdf(ptam: dict, user: dict, cnd_consultas: list | None = None) -> bytes:
    """Generate a PDF from PTAM data. Returns bytes.

    Sections (ABNT NBR 14653):
      1. Identificação e Objetivo
      2. Documentação Analisada
      3. Identificação do Imóvel
      4. Vistoria Técnica
      5. Análise da Região
      6. Homogeneização e Amostras de Mercado
      7. Metodologia
      8. Áreas de Impacto (legacy — desapropriação)
      9. Valor de Avaliação e Resultado
     10. Prazo de Validade / Ressalvas / Pressupostos
     11. Declaração de Responsabilidade Técnica + Assinatura
     12. Certidões das Partes (CND) — somente se cnd_consultas fornecido
    """
    buf = io.BytesIO()
    system_logo_bytes = _fetch_logo()
    company_logo_bytes: bytes | None = user.get("_company_logo_bytes")

    doc = _RomaTecDoc(buf, company_logo_bytes=company_logo_bytes)
    doc._logo_bytes = system_logo_bytes
    doc._ptam_number = ptam.get("numero_ptam") or ptam.get("number", "")
    doc._company_name = user.get("company", "") or ""

    styles = _make_styles()

    story: list = []

    # ── cover ────────────────────────────────────────────────────────────
    # For cover page: prefer company logo, else system logo
    cover_logo_bytes = company_logo_bytes or system_logo_bytes
    story += _build_cover(ptam, cover_logo_bytes, styles)

    # ── Seção 1: Identificação e Objetivo ────────────────────────────────
    story += _build_identification(ptam, styles)
    story.append(_spacer(0.5))

    # ── Seção 2: Documentação Analisada ──────────────────────────────────
    story += _build_documentos_analisados(ptam, styles)
    story.append(_spacer(0.5))

    # ── Seção 3: Identificação do Imóvel ─────────────────────────────────
    story += _build_property(ptam, styles)
    story.append(_spacer(0.5))

    # ── Seção 4: Vistoria Técnica ─────────────────────────────────────────
    story += _build_vistoria(ptam, styles)
    story.append(PageBreak())

    # ── Seção 5: Análise da Região ────────────────────────────────────────
    regiao = _build_regiao(ptam, styles)
    if regiao:
        story += regiao
        story.append(_spacer(0.5))

    # ── Seção 6: Amostras de Mercado / Homogeneização ────────────────────
    story += _build_market_analysis(ptam, styles)
    if ptam.get("market_analysis") or ptam.get("market_samples"):
        story.append(_spacer(0.5))

    # ── Seção 7: Metodologia ──────────────────────────────────────────────
    story += _build_methodology(ptam, styles)
    story.append(_spacer(0.5))

    # ── Seção 8b: Cálculo de Ponderância ─────────────────────────────────
    ponderancia = _build_ponderancia(ptam, styles)
    if ponderancia:
        story += ponderancia
        story.append(_spacer(0.5))

    # ── Seção 8c: Método de Avaliação — Depreciação e Valorização ─────────
    metodo_aval = _build_metodo_avaliacao(ptam, styles)
    if metodo_aval:
        story += metodo_aval
        story.append(_spacer(0.5))

    # ── Seção 8: Áreas de Impacto (legacy) ───────────────────────────────
    story += _build_impact_areas(ptam, styles)
    if ptam.get("impact_areas"):
        story.append(_spacer(0.5))

    # ── Seções 9-11: Resultado, Prazo, Responsabilidade Técnica ──────────
    story += _build_conclusion(ptam, user, styles)

    # ── Seção CND: Certidões das Partes (opcional) ────────────────────────
    certidoes_section = _build_certidoes_partes(styles, cnd_consultas or [])
    if certidoes_section:
        story.append(PageBreak())
        story += certidoes_section

    doc.build(story)
    return buf.getvalue()
