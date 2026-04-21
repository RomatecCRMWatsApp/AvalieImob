# @module pdf.tvi_pdf — Geração de PDF para Termo de Vistoria de Imóvel (TVI)
"""PDF generator for TVI documents — RomaTec branding.

Uses reportlab to produce a professional, print-ready PDF with:
  - Header: logo Romatec + dados empresa à direita
  - Linha divisória verde (#1B4D1B)
  - Título: TERMO DE VISTORIA DE IMÓVEL — [TIPO DO MODELO]
  - Número: TVI-XXXX/AAAA
  - Corpo: todos os campos preenchidos organizados por seção
  - Galeria de fotos com legendas (2 por linha, redimensionadas)
  - Conclusão técnica
  - Rodapé: assinatura digital (base64) + ART/TRT + data + local
  - Watermark sutil: ROMATEC CONSULTORIA IMOBILIÁRIA
"""
from __future__ import annotations

import base64
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

# ── brand colours ─────────────────────────────────────────────────────────────
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


def _fetch_logo() -> bytes | None:
    try:
        with urllib.request.urlopen(LOGO_URL, timeout=5) as resp:
            return resp.read()
    except Exception:
        return None


def _spacer(h: float = 0.4) -> Spacer:
    return Spacer(1, h * cm)


# ── styles ────────────────────────────────────────────────────────────────────

def _make_styles() -> dict:
    return {
        "title": ParagraphStyle(
            "tvi_title", fontName="Helvetica-Bold", fontSize=15, leading=20,
            textColor=WHITE, alignment=TA_CENTER, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "tvi_subtitle", fontName="Helvetica", fontSize=12, leading=16,
            textColor=WHITE, alignment=TA_CENTER, spaceAfter=2,
        ),
        "section_title": ParagraphStyle(
            "tvi_section", fontName="Helvetica-Bold", fontSize=12, leading=16,
            textColor=GOLD, alignment=TA_CENTER, spaceBefore=12, spaceAfter=6,
        ),
        "label": ParagraphStyle(
            "tvi_label", fontName="Helvetica-Bold", fontSize=10, leading=14,
            textColor=DARK, spaceAfter=2,
        ),
        "value": ParagraphStyle(
            "tvi_value", fontName="Helvetica", fontSize=10, leading=14,
            textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "tvi_body", fontName="Helvetica", fontSize=10, leading=14,
            textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "tvi_footer", fontName="Helvetica", fontSize=8, leading=10,
            textColor=WHITE, alignment=TA_CENTER,
        ),
        "caption": ParagraphStyle(
            "tvi_caption", fontName="Helvetica-Oblique", fontSize=8, leading=10,
            textColor=DARK, alignment=TA_CENTER, spaceAfter=4,
        ),
        "sig_line": ParagraphStyle(
            "tvi_sig", fontName="Helvetica", fontSize=10, leading=14,
            textColor=DARK, alignment=TA_CENTER,
        ),
        "conclusion": ParagraphStyle(
            "tvi_conc", fontName="Helvetica-Bold", fontSize=12, leading=16,
            textColor=GREEN, alignment=TA_CENTER, spaceBefore=10, spaceAfter=4,
        ),
    }


# ── page template ─────────────────────────────────────────────────────────────

class _TVIDoc(BaseDocTemplate):
    """Custom doc with green header, watermark and footer on every page."""

    def __init__(self, buf: io.BytesIO, logo_bytes: bytes | None = None):
        self.styles = _make_styles()
        self._logo_bytes = logo_bytes
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

        frame = Frame(margin_lr, margin_tb + footer_h, content_w, content_h, id="content")
        template = PageTemplate(id="main", frames=[frame], onPage=self._on_page)
        self.addPageTemplates([template])

    def _on_page(self, canvas, doc):
        canvas.saveState()
        page_w, page_h = A4
        header_h = 1.6 * cm
        footer_h = 0.9 * cm
        margin = 2.0 * cm

        # ── watermark ──────────────────────────────────────────────────────
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 36)
        canvas.setFillColor(colors.HexColor("#1B4D1B"))
        canvas.setFillAlpha(0.04)
        canvas.translate(page_w / 2, page_h / 2)
        canvas.rotate(35)
        canvas.drawCentredString(0, 0, "ROMATEC CONSULTORIA IMOBILIÁRIA")
        canvas.restoreState()

        # ── header band ────────────────────────────────────────────────────
        canvas.setFillColor(GREEN)
        canvas.rect(0, page_h - header_h, page_w, header_h, fill=1, stroke=0)

        if self._logo_bytes:
            try:
                logo_buf = io.BytesIO(self._logo_bytes)
                canvas.drawImage(
                    logo_buf, margin, page_h - header_h + 0.15 * cm,
                    width=1.2 * cm, height=1.2 * cm,
                    preserveAspectRatio=True, mask="auto",
                )
            except Exception:
                pass

        company = getattr(doc, "_company_name", "") or "RomaTec Consultoria Imobiliária"
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(WHITE)
        canvas.drawString(margin + 1.5 * cm, page_h - header_h + 0.5 * cm, company)

        tvi_num = getattr(doc, "_tvi_number", "")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(GOLD)
        canvas.drawRightString(page_w - margin, page_h - header_h + 0.5 * cm, f"TVI nº {tvi_num}")

        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(0, page_h - header_h, page_w, page_h - header_h)

        # ── footer band ────────────────────────────────────────────────────
        canvas.setFillColor(GREEN)
        canvas.rect(0, 0, page_w, footer_h, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(WHITE)
        canvas.drawCentredString(
            page_w / 2, footer_h - 0.3 * cm,
            "RomaTec Consultoria Imobiliária  —  Termo de Vistoria de Imóvel  |  Documento técnico gerado automaticamente",
        )
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GOLD)
        canvas.drawRightString(page_w - margin, footer_h - 0.3 * cm, f"Pág. {doc.page}")
        canvas.restoreState()


# ── builder helpers ───────────────────────────────────────────────────────────

def _lv(styles: dict, label: str, value: Any) -> list:
    if value is None or str(value).strip() in ("", "0", "0.0"):
        return []
    return [Paragraph(f"<b>{label}:</b> {value}", styles["value"])]


def _section(styles: dict, text: str) -> list:
    return [
        _spacer(0.3),
        Paragraph(text.upper(), styles["section_title"]),
        _spacer(0.2),
    ]


def _body(styles: dict, text: str) -> list:
    if not text or not text.strip():
        return []
    return [Paragraph(text.replace("\n", "<br/>"), styles["body"])]


def _divider() -> Table:
    tbl = Table([[""]], colWidths=[16.5 * cm], rowHeights=[0.15 * cm])
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN)]))
    return tbl


# ── cover ─────────────────────────────────────────────────────────────────────

def _build_cover(v: dict, model_nome: str, logo_bytes: bytes | None, styles: dict) -> list:
    story = []

    if logo_bytes:
        try:
            img = Image(io.BytesIO(logo_bytes), width=4 * cm, height=4 * cm)
            img.hAlign = "CENTER"
            story.append(img)
            story.append(_spacer(0.4))
        except Exception:
            pass

    banner_data = [[
        Paragraph("TERMO DE VISTORIA DE IMÓVEL", styles["title"]),
    ]]
    if model_nome:
        banner_data.append([Paragraph(model_nome.upper(), styles["subtitle"])])

    banner = Table(banner_data, colWidths=[16.5 * cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(banner)
    story.append(_spacer(0.6))

    numero = v.get("numero_tvi") or "TVI-0000/0000"
    story.append(Paragraph(
        f"<b>Nº {numero}</b>",
        ParagraphStyle("ctr_num", fontName="Helvetica-Bold", fontSize=15,
                       alignment=TA_CENTER, textColor=GREEN, spaceAfter=4),
    ))

    if v.get("imovel_endereco"):
        story.append(Paragraph(
            v["imovel_endereco"],
            ParagraphStyle("ctr_end", fontName="Helvetica", fontSize=12,
                           alignment=TA_CENTER, textColor=DARK, spaceAfter=6),
        ))

    story.append(_spacer(0.4))
    meta_rows = []
    if v.get("cliente_nome"):
        meta_rows.append(["Solicitante:", v["cliente_nome"]])
    city_uf = " / ".join(filter(None, [v.get("imovel_cidade"), v.get("imovel_uf")]))
    if city_uf:
        meta_rows.append(["Cidade/UF:", city_uf])
    data_vis = v.get("data_vistoria") or datetime.utcnow().strftime("%d/%m/%Y")
    meta_rows.append(["Data da Vistoria:", data_vis])
    if v.get("responsavel_nome"):
        meta_rows.append(["Responsável Técnico:", v["responsavel_nome"]])

    if meta_rows:
        meta_tbl = Table(meta_rows, colWidths=[5 * cm, 11 * cm])
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

    story.append(_spacer(0.8))
    story.append(_divider())
    story.append(_spacer(0.3))
    story.append(Paragraph(
        "RomaTec Consultoria Imobiliária  —  Termo de Vistoria de Imóvel",
        ParagraphStyle("ctr_brand", fontName="Helvetica-Bold", fontSize=9,
                       alignment=TA_CENTER, textColor=GOLD),
    ))
    story.append(PageBreak())
    return story


# ── sections ──────────────────────────────────────────────────────────────────

def _build_identificacao(v: dict, styles: dict) -> list:
    story = _section(styles, "1. Identificação")
    story += _lv(styles, "Número TVI", v.get("numero_tvi"))
    story += _lv(styles, "Cliente / Solicitante", v.get("cliente_nome"))
    story += _lv(styles, "CPF / CNPJ", v.get("cliente_cpf_cnpj"))
    story += _lv(styles, "Telefone", v.get("cliente_telefone"))
    story += _lv(styles, "E-mail", v.get("cliente_email"))
    return story


def _build_imovel(v: dict, styles: dict) -> list:
    story = _section(styles, "2. Dados do Imóvel")
    story += _lv(styles, "Tipo", v.get("imovel_tipo"))
    story += _lv(styles, "Endereço", v.get("imovel_endereco"))
    story += _lv(styles, "Bairro", v.get("imovel_bairro"))
    city_uf = " / ".join(filter(None, [v.get("imovel_cidade"), v.get("imovel_uf")]))
    story += _lv(styles, "Cidade / UF", city_uf)
    story += _lv(styles, "CEP", v.get("imovel_cep"))
    story += _lv(styles, "Matrícula", v.get("imovel_matricula"))
    return story


def _build_vistoria_info(v: dict, styles: dict) -> list:
    story = _section(styles, "3. Dados da Vistoria")
    story += _lv(styles, "Data", v.get("data_vistoria"))
    story += _lv(styles, "Hora", v.get("hora_vistoria"))
    story += _lv(styles, "Condições Climáticas", v.get("condicoes_climaticas"))
    story += _lv(styles, "Objetivo", v.get("objetivo"))
    story += _lv(styles, "Metodologia", v.get("metodologia"))
    return story


def _build_ambientes(v: dict, styles: dict) -> list:
    ambientes = v.get("ambientes") or []
    if not ambientes:
        return []
    story = _section(styles, "4. Ambientes Vistoriados")
    for amb in ambientes:
        if not (isinstance(amb, dict) and amb.get("nome")):
            continue
        story.append(Paragraph(
            f"<b>{amb['nome']}</b>",
            ParagraphStyle("amb_nome", fontName="Helvetica-Bold", fontSize=11,
                           leading=15, textColor=GREEN, spaceBefore=6, spaceAfter=2),
        ))
        story += _lv(styles, "Descrição", amb.get("descricao"))
        story += _lv(styles, "Estado de Conservação", amb.get("estado_conservacao"))
        story += _lv(styles, "Observações", amb.get("observacoes"))
    return story


def _build_campos_extras(v: dict, styles: dict) -> list:
    extras = v.get("campos_extras") or {}
    if not extras:
        return []
    story = _section(styles, "5. Informações Complementares")
    for key, val in extras.items():
        if val is not None and str(val).strip():
            label = key.replace("_", " ").title()
            story += _lv(styles, label, val)
    return story


def _build_fotos(photos: list, styles: dict) -> list:
    """Galeria de fotos — 2 por linha, com legenda abaixo de cada foto."""
    if not photos:
        return []
    story = _section(styles, "6. Registro Fotográfico")
    MAX_W = 8.0 * cm
    MAX_H = 6.0 * cm

    row_cells: list = []
    for photo in photos:
        url = photo.get("url", "") if isinstance(photo, dict) else ""
        legenda = photo.get("legenda", "") if isinstance(photo, dict) else ""
        ambiente = photo.get("ambiente", "") if isinstance(photo, dict) else ""
        caption_text = legenda or ambiente or ""

        img_elem = None
        if url:
            try:
                if url.startswith("data:"):
                    b64 = url.split(",", 1)[-1]
                    img_data = base64.b64decode(b64)
                    img_elem = Image(io.BytesIO(img_data), width=MAX_W, height=MAX_H)
                    img_elem.hAlign = "CENTER"
                else:
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        img_data = resp.read()
                    img_elem = Image(io.BytesIO(img_data), width=MAX_W, height=MAX_H)
                    img_elem.hAlign = "CENTER"
            except Exception:
                img_elem = None

        cell_content: list = []
        if img_elem:
            cell_content.append(img_elem)
        if caption_text:
            cell_content.append(Paragraph(caption_text, styles["caption"]))

        if cell_content:
            row_cells.append(cell_content)

        if len(row_cells) == 2:
            tbl = Table([row_cells], colWidths=[8.5 * cm, 8.5 * cm])
            tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(tbl)
            story.append(_spacer(0.2))
            row_cells = []

    if row_cells:
        # Pad to 2 columns
        while len(row_cells) < 2:
            row_cells.append([Spacer(1, MAX_H)])
        tbl = Table([row_cells], colWidths=[8.5 * cm, 8.5 * cm])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(tbl)
        story.append(_spacer(0.2))

    return story


def _build_conclusao(v: dict, styles: dict) -> list:
    story = _section(styles, "7. Conclusão Técnica")
    story += _body(styles, v.get("conclusao_tecnica", ""))
    return story


def _build_assinatura(v: dict, sigs: list, styles: dict) -> list:
    story = []
    story.append(_spacer(0.8))

    city = v.get("imovel_cidade", "")
    date_str = v.get("data_vistoria") or datetime.utcnow().strftime("%d/%m/%Y")
    loc_text = f"{city}, {date_str}." if city else date_str
    story.append(Paragraph(loc_text, ParagraphStyle(
        "loc_tvi", fontName="Helvetica", fontSize=10, alignment=TA_RIGHT, textColor=DARK,
    )))
    story.append(_spacer(1.2))

    # Signature image from sigs collection (first sig)
    first_sig = next((s for s in (sigs or []) if isinstance(s, dict) and s.get("data_b64")), None)
    if first_sig:
        try:
            sig_data = base64.b64decode(first_sig["data_b64"])
            sig_img = Image(io.BytesIO(sig_data), width=6 * cm, height=2.5 * cm)
            sig_img.hAlign = "CENTER"
            story.append(sig_img)
        except Exception:
            pass

    sig_line_tbl = Table([["_" * 45]], colWidths=[10 * cm])
    sig_line_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    sig_line_tbl.hAlign = "CENTER"
    story.append(sig_line_tbl)

    nome = v.get("responsavel_nome") or (first_sig or {}).get("signatario", "")
    if nome:
        story.append(Paragraph(f"<b>{nome}</b>", styles["sig_line"]))
    for field, label in [
        ("responsavel_crea", "CREA"),
        ("responsavel_cau", "CAU"),
        ("responsavel_cftma", "CFTMA"),
        ("art_trt_numero", "ART/TRT nº"),
    ]:
        val = v.get(field, "")
        if val:
            story.append(Paragraph(f"{label} {val}", styles["sig_line"]))

    if first_sig and first_sig.get("cargo"):
        story.append(Paragraph(first_sig["cargo"], styles["sig_line"]))

    return story


# ── main entry point ──────────────────────────────────────────────────────────

def generate_tvi_pdf(
    vistoria: dict,
    user: dict,
    photos: list | None = None,
    signatures: list | None = None,
    model_nome: str = "",
) -> bytes:
    """Generate TVI PDF. Returns bytes.

    Args:
        vistoria: Vistoria document dict (VistoriaBase fields).
        user: Logged-in user dict (name, company, role, crea, …).
        photos: List of VistoriaPhoto dicts [{url, ambiente, legenda}, …].
        signatures: List of VistoriaSignature dicts [{data_b64, signatario, cargo}, …].
        model_nome: Human-readable model name, e.g. "Locação — Entrada".
    """
    buf = io.BytesIO()
    system_logo = _fetch_logo()
    logo = system_logo

    doc = _TVIDoc(buf, logo_bytes=logo)
    doc._tvi_number = vistoria.get("numero_tvi") or ""
    doc._company_name = user.get("company", "") or "RomaTec Consultoria Imobiliária"

    styles = _make_styles()
    story: list = []

    story += _build_cover(vistoria, model_nome, logo, styles)
    story += _build_identificacao(vistoria, styles)
    story.append(_spacer(0.4))
    story += _build_imovel(vistoria, styles)
    story.append(_spacer(0.4))
    story += _build_vistoria_info(vistoria, styles)
    story.append(_spacer(0.4))
    story += _build_ambientes(vistoria, styles)
    story.append(_spacer(0.4))
    story += _build_campos_extras(vistoria, styles)
    story.append(_spacer(0.4))
    story += _build_fotos(photos or [], styles)
    story.append(_spacer(0.4))
    story += _build_conclusao(vistoria, styles)
    story += _build_assinatura(vistoria, signatures or [], styles)

    doc.build(story)
    return buf.getvalue()
