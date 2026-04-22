"""PDF generator for Avaliação de Locação — RomaTec branding.

Uses reportlab to produce a professional, print-ready PDF with:
  - Cover page with logo, title, laudo number and address
  - 10 content sections (NBR 14653 + Lei 8.245/1991)
  - Table for rental market comparatives (address, area, aluguel, R$/m²)
  - Statistical calculations (média, desvio padrão, CV%, fator locação)
  - Highlighted result section (valor estimado mensal in full)
  - Guarantee and conditions section
  - Legal basis (Lei 8.245/1991, Código Civil 565-578, NBR 14653)
  - Photo grid with captions
  - Technical responsible signature block
  - Green (#1B4D1B) header + gold (#D4A830) section titles on every page
  - Footer with legal basis on every page

Normative references:
  ABNT NBR 14653-1, -2 | Lei 8.245/1991 (Lei do Inquilinato)
  Código Civil art. 565–578 | Res. COFECI 957/2006
"""
from __future__ import annotations

import io
import math
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
HIGHLIGHT_BG = colors.HexColor("#FFF8E1")  # subtle gold background for result

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
        return f"{float(v):,.2f} m²".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 m²"


def _fetch_logo() -> bytes | None:
    try:
        with urllib.request.urlopen(LOGO_URL, timeout=5) as resp:
            return resp.read()
    except Exception:
        return None


# ── styles ────────────────────────────────────────────────────────────────────

def _make_styles() -> dict:
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
        "result_value": ParagraphStyle(
            "result_value",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=22,
            textColor=GREEN,
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "result_words": ParagraphStyle(
            "result_words",
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

class _LocacaoDoc(BaseDocTemplate):
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

    def _on_page(self, canvas, doc):
        canvas.saveState()
        page_w, page_h = A4
        header_h = 1.6 * cm
        footer_h = 0.9 * cm
        margin = 2.0 * cm

        # ── header band ────────────────────────────────────────────────────
        canvas.setFillColor(GREEN)
        canvas.rect(0, page_h - header_h, page_w, header_h, fill=1, stroke=0)

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

        header_company = getattr(doc, "_company_name", "") or "Romatec Consultoria"
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(WHITE)
        canvas.drawString(margin + 1.5 * cm, page_h - header_h + 0.5 * cm, header_company)

        laudo_num = getattr(doc, "_laudo_number", "")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(GOLD)
        canvas.drawRightString(page_w - margin, page_h - header_h + 0.5 * cm, f"Laudo nº {laudo_num}")

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
            "Romatec Consultoria  —  Elaborado conforme NBR 14653 e Lei 8.245/1991 (Lei do Inquilinato)",
        )

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GOLD)
        canvas.drawRightString(page_w - margin, (footer_h - 0.3 * cm), f"Pág. {doc.page}")

        canvas.restoreState()


# ── builder helpers ───────────────────────────────────────────────────────────

def _lv(styles: dict, label: str, value: Any) -> list:
    if value is None or str(value).strip() in ("", "0", "0.0", "0.00"):
        return []
    return [Paragraph(f"<b>{label}:</b> {value}", styles["value"])]


def _section(styles: dict, text: str) -> list:
    return [
        Spacer(1, 0.3 * cm),
        Paragraph(text.upper(), styles["section_title"]),
        Spacer(1, 0.2 * cm),
    ]


def _subsection(styles: dict, text: str) -> list:
    return [Paragraph(text, styles["subsection_title"])]


def _body(styles: dict, text: str) -> list:
    if not text or not text.strip():
        return []
    return [Paragraph(text.replace("\n", "<br/>"), styles["body"])]


def _spacer(h: float = 0.4) -> Spacer:
    return Spacer(1, h * cm)


# ── cover page ────────────────────────────────────────────────────────────────

def _build_cover(loc: dict, logo_bytes: bytes | None, styles: dict) -> list:
    story = []

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
    story.append(_spacer(0.5))

    # subtitle
    story.append(Paragraph(
        "AVALIAÇÃO PARA FINS DE LOCAÇÃO",
        ParagraphStyle("ctr_sub", fontName="Helvetica-Bold", fontSize=14, alignment=TA_CENTER,
                       textColor=GOLD, spaceAfter=6),
    ))

    # laudo number
    numero = loc.get("numero_locacao") or "—"
    story.append(Paragraph(
        f"<b>Laudo nº {numero}</b>",
        ParagraphStyle("ctr_bold", fontName="Helvetica-Bold", fontSize=16, alignment=TA_CENTER,
                       textColor=GREEN, spaceAfter=4),
    ))

    # address
    endereco = loc.get("imovel_endereco") or ""
    bairro = loc.get("imovel_bairro") or ""
    cidade = loc.get("imovel_cidade") or ""
    estado = loc.get("imovel_estado") or ""
    full_address_parts = [p for p in [endereco, bairro, cidade, estado] if p]
    full_address = " — ".join(full_address_parts)
    if full_address:
        story.append(Paragraph(
            full_address,
            ParagraphStyle("ctr_addr", fontName="Helvetica", fontSize=12, alignment=TA_CENTER,
                           textColor=DARK, spaceAfter=6),
        ))

    story.append(_spacer(0.5))

    # meta table
    meta_rows = []
    solicitante = loc.get("solicitante_nome") or ""
    if solicitante:
        meta_rows.append(["Solicitante:", solicitante])
    if cidade:
        meta_rows.append(["Cidade:", f"{cidade}/{estado}" if estado else cidade])
    date_str = loc.get("conclusion_date") or datetime.utcnow().strftime("%d/%m/%Y")
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
        "Romatec Consultoria  —  NBR 14.653  |  Lei 8.245/1991",
        ParagraphStyle("ctr_nbr", fontName="Helvetica-Bold", fontSize=10, alignment=TA_CENTER,
                       textColor=GOLD),
    ))

    story.append(PageBreak())
    return story


# ── Section 1: Identificação ──────────────────────────────────────────────────

def _build_identificacao(loc: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "1. Identificação")

    objetivo_map = {
        "fixacao": "Fixação de Aluguel",
        "revisao": "Revisão de Aluguel (Lei 8.245/91 art. 19)",
        "renovatoria": "Ação Renovatória (Lei 8.245/91 art. 51)",
        "outros": "Outros",
    }
    objetivo = loc.get("objetivo") or ""
    objetivo_str = objetivo_map.get(objetivo, objetivo)
    if loc.get("objetivo_outros"):
        objetivo_str = loc["objetivo_outros"]

    tipo_map = {
        "residencial": "Residencial",
        "comercial": "Comercial",
        "galpao": "Galpão / Industrial",
        "ponto_comercial": "Ponto Comercial",
        "misto": "Uso Misto",
    }
    tipo = loc.get("tipo_locacao") or ""

    for label, val in [
        ("Número do Laudo", loc.get("numero_locacao")),
        ("Solicitante", loc.get("solicitante_nome")),
        ("CPF/CNPJ", loc.get("solicitante_cpf")),
        ("Telefone", loc.get("solicitante_telefone")),
        ("E-mail", loc.get("solicitante_email")),
        ("Endereço do Solicitante", loc.get("solicitante_endereco")),
        ("Objetivo da Avaliação", objetivo_str or None),
        ("Tipo de Locação", tipo_map.get(tipo, tipo) or None),
        ("Data de Vistoria", loc.get("conclusion_date")),
    ]:
        story += _lv(styles, label, val)

    return story


# ── Section 2: Imóvel Avaliado ────────────────────────────────────────────────

def _build_imovel(loc: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "2. Imóvel Avaliado")

    conservacao_map = {
        "otimo": "Ótimo",
        "bom": "Bom",
        "regular": "Regular",
        "ruim": "Ruim",
        "pessimo": "Péssimo",
    }
    padrao_map = {
        "alto": "Alto",
        "medio": "Médio",
        "simples": "Simples",
        "minimo": "Mínimo",
    }
    tipo_imovel_map = {
        "casa": "Casa",
        "apartamento": "Apartamento",
        "sala_comercial": "Sala Comercial",
        "galpao": "Galpão",
        "loja": "Loja",
        "terreno": "Terreno",
    }

    endereco = loc.get("imovel_endereco") or ""
    bairro = loc.get("imovel_bairro") or ""
    cidade = loc.get("imovel_cidade") or ""
    estado = loc.get("imovel_estado") or ""
    cidade_uf = f"{cidade}/{estado}" if estado else cidade

    tipo_imovel = loc.get("imovel_tipo") or ""
    conservacao = loc.get("imovel_estado_conservacao") or ""
    padrao = loc.get("imovel_padrao_acabamento") or ""

    area_terreno = loc.get("imovel_area_terreno") or 0
    area_construida = loc.get("imovel_area_construida") or 0

    for label, val in [
        ("Tipo", tipo_imovel_map.get(tipo_imovel, tipo_imovel) or None),
        ("Endereço", endereco or None),
        ("Bairro", bairro or None),
        ("Cidade/UF", cidade_uf or None),
        ("CEP", loc.get("imovel_cep")),
        ("Matrícula", loc.get("imovel_matricula")),
        ("Cartório", loc.get("imovel_cartorio")),
    ]:
        story += _lv(styles, label, val)

    if area_terreno:
        story += _lv(styles, "Área do Terreno", _fmt_area(area_terreno))
    if area_construida:
        story += _lv(styles, "Área Construída", _fmt_area(area_construida))

    if loc.get("imovel_idade"):
        story += _lv(styles, "Idade do Imóvel", f"{loc['imovel_idade']} anos")
    if conservacao:
        story += _lv(styles, "Estado de Conservação", conservacao_map.get(conservacao, conservacao))
    if padrao:
        story += _lv(styles, "Padrão de Acabamento", padrao_map.get(padrao, padrao))
    if loc.get("imovel_num_quartos"):
        story += _lv(styles, "Dormitórios", str(loc["imovel_num_quartos"]))
    if loc.get("imovel_num_banheiros"):
        story += _lv(styles, "Banheiros", str(loc["imovel_num_banheiros"]))
    if loc.get("imovel_num_vagas"):
        story += _lv(styles, "Vagas de Garagem", str(loc["imovel_num_vagas"]))
    if loc.get("imovel_piscina"):
        story += _lv(styles, "Piscina", "Sim")
    story += _body(styles, loc.get("imovel_caracteristicas") or "")

    return story


# ── Section 3: Região e Entorno ───────────────────────────────────────────────

def _build_regiao(loc: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "3. Região e Entorno")

    if loc.get("zoneamento"):
        story += _lv(styles, "Zoneamento (Plano Diretor)", loc["zoneamento"])

    for label, key in [
        ("Infraestrutura", "regiao_infraestrutura"),
        ("Serviços Públicos", "regiao_servicos_publicos"),
        ("Uso Predominante do Solo", "regiao_uso_predominante"),
        ("Padrão Construtivo da Região", "regiao_padrao_construtivo"),
        ("Tendência de Mercado", "regiao_tendencia_mercado"),
        ("Observações", "regiao_observacoes"),
    ]:
        if loc.get(key):
            story += _subsection(styles, label)
            story += _body(styles, loc[key])

    return story if len(story) > 3 else []


# ── Section 4: Pesquisa de Mercado ────────────────────────────────────────────

def _build_mercado(loc: dict, styles: dict) -> list:
    samples = loc.get("market_samples") or []
    market_analysis = loc.get("market_analysis") or ""
    if not samples and not market_analysis:
        return []

    story = []
    story += _section(styles, "4. Pesquisa de Mercado")
    story += _body(styles, market_analysis)

    if samples:
        story += _subsection(styles, "Elementos Comparativos — Mercado de Locação")
        story += _rental_samples_table(samples)

    return story


def _rental_samples_table(samples: list) -> list:
    """Table of rental market comparatives."""
    if not samples:
        return []
    headers = ["Nº", "Endereço / Bairro", "Área (m²)", "Aluguel (R$)", "R$/m²", "Tipo", "Fonte", "Data"]
    data = [headers]
    for idx, s in enumerate(samples, start=1):
        area = float(s.get("area") or 0)
        valor = float(s.get("valor_aluguel") or 0)
        vpm = float(s.get("valor_por_m2") or 0)
        if not vpm and area > 0 and valor > 0:
            vpm = valor / area
        addr_bairro = f"{s.get('address', '')} / {s.get('neighborhood', '')}".strip(" /")
        tipo_raw = s.get("tipo_amostra") or "oferta"
        tipo_label = "Consolidada" if tipo_raw == "consolidada" else "Oferta"
        data.append([
            str(idx),
            addr_bairro,
            f"{area:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"{vpm:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            tipo_label,
            s.get("source", "") or "",
            s.get("collection_date", "") or "",
        ])
    col_widths = [0.8 * cm, 4.0 * cm, 1.8 * cm, 2.0 * cm, 1.6 * cm, 1.8 * cm, 2.8 * cm, 2.2 * cm]
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
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ALIGN", (6, 1), (6, -1), "LEFT"),
        ("ALIGN", (7, 1), (7, -1), "CENTER"),
    ]))
    return [tbl, _spacer(0.3)]


# ── Section 5: Cálculos ───────────────────────────────────────────────────────

def _build_calculos(loc: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "5. Cálculos e Tratamento Estatístico")

    # Auto-compute from samples if not stored
    samples = loc.get("market_samples") or []
    valores = [float(s.get("valor_por_m2") or 0) for s in samples if (s.get("valor_por_m2") or 0) > 0]
    # Also compute from valor_aluguel/area if valor_por_m2 missing
    for s in samples:
        if not (s.get("valor_por_m2") or 0):
            area = float(s.get("area") or 0)
            val = float(s.get("valor_aluguel") or 0)
            if area > 0 and val > 0:
                valores.append(val / area)

    media = float(loc.get("calc_media") or 0)
    mediana = float(loc.get("calc_mediana") or 0)
    desvio = float(loc.get("calc_desvio_padrao") or 0)
    cv = float(loc.get("calc_coef_variacao") or 0)

    if valores and not media:
        n = len(valores)
        media = sum(valores) / n
        sorted_v = sorted(valores)
        mediana = (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2 if n % 2 == 0 else sorted_v[n // 2]
        variance = sum((v - media) ** 2 for v in valores) / n
        desvio = math.sqrt(variance)
        cv = (desvio / media * 100) if media > 0 else 0

    if media:
        story += _lv(styles, "Número de Amostras", str(len(valores)) if valores else str(len(samples)))
        story += _lv(
            styles, "Média (R$/m²)",
            f"{media:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    if mediana:
        story += _lv(
            styles, "Mediana (R$/m²)",
            f"{mediana:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    if desvio:
        story += _lv(
            styles, "Desvio Padrão",
            f"{desvio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    if cv:
        story += _lv(
            styles, "Coeficiente de Variação (CV%)",
            f"{cv:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    fator_locacao = loc.get("fator_locacao")
    if fator_locacao:
        story += _lv(
            styles, "Fator de Locação Aplicado",
            f"{float(fator_locacao):.4f}%".replace(".", ",")
        )

    if loc.get("calc_grau_fundamentacao"):
        grau_desc = {
            "I": "Grau I — Mínimo (amostras insuficientes ou dados não verificados)",
            "II": "Grau II — Intermediário (amostras verificadas, dados consistentes)",
            "III": "Grau III — Máximo (amostras verificadas em campo, dados robustos)",
        }
        story += _lv(styles, "Grau de Fundamentação (NBR 14653-2)", grau_desc.get(loc["calc_grau_fundamentacao"], loc["calc_grau_fundamentacao"]))
        # Adicionar explicação do significado
        significado_fund = {
            "I": "Indica que a avaliação possui fundamentação mínima, com amostras não verificadas ou dados limitados.",
            "II": "Indica fundamentação intermediária, com amostras verificadas e dados consistentes.",
            "III": "Indica fundamentação máxima, com amostras verificadas em campo e dados robustos.",
        }
        if loc["calc_grau_fundamentacao"] in significado_fund:
            story += _body(styles, significado_fund[loc["calc_grau_fundamentacao"]])
            story.append(_spacer(0.2))

    grau_precisao = loc.get("grau_precisao") or ""
    if grau_precisao:
        grau_prec_desc = {
            "I": "Grau I — Amplitude ≤ 30% (precisão aceitável para laudos técnicos)",
            "II": "Grau II — Amplitude ≤ 20% (boa precisão)",
            "III": "Grau III — Amplitude ≤ 10% (excelente precisão)",
        }
        story += _lv(styles, "Grau de Precisão (NBR 14653-1 item 9)", grau_prec_desc.get(grau_precisao, grau_precisao))
        # Adicionar explicação do significado
        significado_prec = {
            "I": "O intervalo de confiança é amplo (até 30%), indicando precisão aceitável para fins de locação.",
            "II": "O intervalo de confiança é moderado (até 20%), indicando boa precisão.",
            "III": "O intervalo de confiança é estreito (até 10%), indicando excelente precisão.",
        }
        if grau_precisao in significado_prec:
            story += _body(styles, significado_prec[grau_precisao])
            story.append(_spacer(0.2))

    if loc.get("calc_fatores_homogeneizacao"):
        story += _subsection(styles, "Fatores de Homogeneização Aplicados")
        story += _body(styles, loc["calc_fatores_homogeneizacao"])

    if loc.get("calc_observacoes"):
        story += _lv(styles, "Observações sobre os Cálculos", loc["calc_observacoes"])

    return story


# ── Section 6: Resultado — DESTAQUE ──────────────────────────────────────────

def _build_resultado(loc: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "6. Resultado da Avaliação")

    story += _body(styles, loc.get("conclusion_text") or "")

    valor_estimado = loc.get("valor_locacao_estimado") or 0
    valor_min = loc.get("valor_locacao_minimo") or 0
    valor_max = loc.get("valor_locacao_maximo") or 0
    por_extenso = loc.get("valor_locacao_por_extenso") or ""

    if valor_estimado:
        story.append(_spacer(0.4))

        # highlighted result box
        result_data = [[
            Paragraph(
                f"Valor Estimado de Locação Mensal: {_fmt_currency(valor_estimado)}",
                styles["result_value"],
            )
        ]]
        result_box = Table(result_data, colWidths=[16.5 * cm])
        result_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HIGHLIGHT_BG),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("BOX", (0, 0), (-1, -1), 1.5, GOLD),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        story.append(result_box)
        story.append(_spacer(0.3))

        if por_extenso:
            story.append(Paragraph(f"({por_extenso})", styles["result_words"]))

    if valor_min and valor_max:
        story += _lv(
            styles, "Intervalo de Confiança (Mensal)",
            f"{_fmt_currency(valor_min)} a {_fmt_currency(valor_max)}"
        )

    fator_locacao = loc.get("fator_locacao")
    if fator_locacao:
        story += _lv(
            styles, "Fator de Locação Aplicado",
            f"{float(fator_locacao):.4f}%".replace(".", ",")
        )

    campo_arb_min = loc.get("campo_arbitrio_min") or 0
    campo_arb_max = loc.get("campo_arbitrio_max") or 0
    if campo_arb_min or campo_arb_max:
        story += _lv(
            styles, "Campo de Arbítrio (NBR 14653-1 item 9.2.4)",
            f"{_fmt_currency(campo_arb_min)} a {_fmt_currency(campo_arb_max)}  (variação máx. ±15%)"
        )

    if loc.get("resultado_data_referencia"):
        story += _lv(styles, "Data de Referência da Avaliação", loc["resultado_data_referencia"])

    prazo_meses = loc.get("prazo_validade_meses") or 6
    prazo_str = loc.get("resultado_prazo_validade") or f"{prazo_meses} meses"
    story.append(_spacer(0.3))
    story.append(Paragraph(
        f"Este Parecer Técnico tem validade de <b>{prazo_str}</b> a contar da data de emissão, "
        "conforme ABNT NBR 14653-1. Após esse período, nova avaliação deverá ser realizada.",
        styles["body"],
    ))

    return story


# ── Section 7: Garantia e Condições ──────────────────────────────────────────

def _build_garantia(loc: dict, styles: dict) -> list:
    garantia = loc.get("garantia_locacao") or ""
    prazo = loc.get("prazo_locacao") or ""
    if not garantia and not prazo:
        return []

    story = []
    story += _section(styles, "7. Garantia e Condições")

    garantia_map = {
        "caucao": "Caução (art. 37, I, Lei 8.245/91)",
        "fiador": "Fiança (art. 37, II, Lei 8.245/91)",
        "seguro_fianca": "Seguro de Fiança Locatícia (art. 37, III, Lei 8.245/91)",
        "titulo_capitalizacao": "Título de Capitalização (art. 37, IV, Lei 8.245/91)",
        "nenhuma": "Sem garantia",
    }

    if garantia:
        story += _lv(styles, "Tipo de Garantia Sugerida", garantia_map.get(garantia, garantia))
    if prazo:
        story += _lv(styles, "Prazo de Locação", prazo)

    return story


# ── Section 8: Base Legal ─────────────────────────────────────────────────────

def _build_base_legal(loc: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "8. Base Legal e Normativa")

    base_legal_text = loc.get("base_legal_locacao") or ""
    if base_legal_text:
        story += _body(styles, base_legal_text)

    story.append(Paragraph(
        "Esta avaliação foi elaborada com base nas seguintes normas e dispositivos legais:",
        styles["body"],
    ))
    story.append(_spacer(0.2))

    legal_items = [
        "<b>Lei 8.245/1991 — Lei do Inquilinato:</b> Dispõe sobre as locações dos imóveis urbanos e os procedimentos para determinação do valor de locação (arts. 19 a 21 — revisional; arts. 51 a 57 — renovatória).",
        "<b>Código Civil — art. 565 a 578:</b> Regula o contrato de locação de coisas, estabelecendo direitos e deveres das partes, reajuste e rescisão.",
        "<b>ABNT NBR 14653-1:</b> Procedimentos gerais de avaliação de bens — metodologia, graus de fundamentação e precisão.",
        "<b>ABNT NBR 14653-2:</b> Avaliação de imóveis urbanos — Método Comparativo Direto de Dados de Mercado (item 8.2), homogeneização e tratamento estatístico.",
        "<b>Resolução COFECI 957/2006:</b> Habilita o Corretor de Imóveis para elaboração de Parecer Técnico de Avaliação Mercadológica (PTAM).",
    ]
    for item in legal_items:
        story.append(Paragraph(f"• {item}", styles["value"]))
        story.append(_spacer(0.15))

    return story


# ── Section 9: Registro Fotográfico ──────────────────────────────────────────

def _build_fotos(loc: dict, styles: dict, user: dict) -> list:
    """Build photo section with images (bytes already loaded in foto['_image_bytes'])."""
    fotos = loc.get("fotos_imovel") or []
    docs = loc.get("fotos_documentos") or []
    
    if not fotos and not docs:
        return []

    story = []
    story += _section(styles, "9. Registro Fotográfico")
    story.append(Paragraph("Fotografias do imóvel avaliado, obtidas na data da vistoria:", styles["body"]))
    story.append(_spacer(0.3))

    # Processar fotos do imóvel (bytes já carregados pelo endpoint)
    image_rows = []
    current_row = []
    
    for i, foto in enumerate(fotos[:12]):  # Max 12 fotos
        if isinstance(foto, dict):
            caption = foto.get("caption") or foto.get("legenda") or f"Foto {i+1}"
            img_bytes = foto.get("_image_bytes")
        else:
            caption = f"Foto {i+1}"
            img_bytes = None
        
        if img_bytes:
            try:
                img = Image(io.BytesIO(img_bytes), width=6*cm, height=4.5*cm)
                img.hAlign = 'CENTER'
                current_row.append([
                    img,
                    Paragraph(caption, styles["caption"])
                ])
            except Exception:
                # Se imagem falhar, mostra texto
                current_row.append([
                    Paragraph(f"[Foto {i+1}]", styles["body"]),
                    Paragraph(caption, styles["caption"])
                ])
        else:
            current_row.append([
                Paragraph(f"[Foto {i+1}]", styles["body"]),
                Paragraph(caption, styles["caption"])
            ])
        
        # 3 fotos por linha
        if len(current_row) >= 3:
            image_rows.append(current_row)
            current_row = []
    
    if current_row:
        # Preenche linha incompleta
        while len(current_row) < 3:
            current_row.append(['', ''])
        image_rows.append(current_row)
    
    # Criar tabela de fotos
    if image_rows:
        for row in image_rows:
            # Extrair apenas as células de imagem (col 0 de cada par)
            img_cells = [cell[0] for cell in row]
            caption_cells = [cell[1] for cell in row]
            
            # Tabela de imagens
            img_table = Table([img_cells], colWidths=[6*cm, 6*cm, 6*cm])
            img_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(img_table)
            
            # Tabela de legendas
            cap_table = Table([caption_cells], colWidths=[6*cm, 6*cm, 6*cm])
            cap_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TEXTCOLOR', (0, 0), (-1, -1), DARK),
                ('PADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(cap_table)
            story.append(_spacer(0.3))
    
    # Documentos digitalizados
    if docs:
        story.append(Paragraph("Documentos Digitalizados:", styles["h3"]))
        for i, doc in enumerate(docs[:6]):
            if isinstance(doc, dict):
                doc_name = doc.get("name") or doc.get("nome") or f"Documento {i+1}"
            else:
                doc_name = f"Documento {i+1}"
            story.append(Paragraph(f"  • {doc_name}", styles["body"]))
    
    return story


# ── Section 10: Responsável Técnico ──────────────────────────────────────────

def _build_responsavel(loc: dict, user: dict, styles: dict) -> list:
    story = []
    story += _section(styles, "10. Responsável Técnico")

    tipo_prof = loc.get("tipo_profissional") or user.get("role", "")
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

    art_rrt = loc.get("art_rrt_numero") or ""
    if art_rrt:
        story += _lv(styles, "Nº ART / RRT", art_rrt)

    # Ressalvas / considerações
    if loc.get("consideracoes_ressalvas") or loc.get("consideracoes_pressupostos") or loc.get("consideracoes_limitacoes"):
        story += _subsection(styles, "Ressalvas, Pressupostos e Limitações")
        if loc.get("consideracoes_ressalvas"):
            story += _body(styles, loc["consideracoes_ressalvas"])
        if loc.get("consideracoes_pressupostos"):
            story += _body(styles, loc["consideracoes_pressupostos"])
        if loc.get("consideracoes_limitacoes"):
            story += _body(styles, loc["consideracoes_limitacoes"])

    # Location and date
    city = loc.get("conclusion_city") or ""
    date_str = loc.get("conclusion_date") or datetime.utcnow().strftime("%d/%m/%Y")
    story.append(_spacer(0.6))
    loc_text = f"{city}, {date_str}." if city else date_str
    story.append(Paragraph(loc_text, ParagraphStyle(
        "loc", fontName="Helvetica", fontSize=10, alignment=TA_RIGHT, textColor=DARK,
    )))

    # Signature block
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

    name = loc.get("responsavel_nome") or user.get("name", "")
    role = user.get("role", "")
    creci = loc.get("responsavel_creci") or user.get("crea", "")
    cnai = loc.get("responsavel_cnai") or ""
    registro = loc.get("registro_profissional") or ""

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


# ── main entry point ──────────────────────────────────────────────────────────

def generate_locacao_pdf(loc: dict, user: dict | None = None) -> bytes:
    """Generate a PDF for Avaliação de Locação. Returns bytes.

    Sections:
      Capa — Logo, título, subtítulo, número, data, endereço
      1. Identificação (solicitante, objetivo, data vistoria)
      2. Imóvel Avaliado (endereço, tipo, áreas, características, conservação)
      3. Região e Entorno (infraestrutura, acessos, serviços)
      4. Pesquisa de Mercado (tabela comparativos de aluguel)
      5. Cálculos (média, desvio padrão, CV%, fator locação, graus)
      6. Resultado — DESTAQUE (valor mensal estimado, intervalo, fator)
      7. Garantia e Condições (tipo, prazo)
      8. Base Legal (Lei 8.245/1991, Código Civil, NBR 14653)
      9. Registro Fotográfico (com imagens do banco)
     10. Responsável Técnico (nome, registro, assinatura)
    """
    if user is None:
        user = {}

    buf = io.BytesIO()
    system_logo_bytes = _fetch_logo()
    company_logo_bytes: bytes | None = user.get("_company_logo_bytes")

    doc = _LocacaoDoc(buf, company_logo_bytes=company_logo_bytes)
    doc._logo_bytes = system_logo_bytes
    doc._laudo_number = loc.get("numero_locacao") or ""
    doc._company_name = user.get("company", "") or "Romatec Consultoria"

    styles = _make_styles()
    story: list = []

    # ── Capa ─────────────────────────────────────────────────────────────
    cover_logo = company_logo_bytes or system_logo_bytes
    story += _build_cover(loc, cover_logo, styles)

    # ── Seção 1: Identificação ────────────────────────────────────────────
    story += _build_identificacao(loc, styles)
    story.append(_spacer(0.5))

    # ── Seção 2: Imóvel Avaliado ──────────────────────────────────────────
    story += _build_imovel(loc, styles)
    story.append(_spacer(0.5))

    # ── Seção 3: Região e Entorno ─────────────────────────────────────────
    regiao = _build_regiao(loc, styles)
    if regiao:
        story += regiao
        story.append(_spacer(0.5))

    # ── Seção 4: Pesquisa de Mercado ──────────────────────────────────────
    mercado = _build_mercado(loc, styles)
    if mercado:
        story += mercado
        story.append(PageBreak())

    # ── Seção 5: Cálculos ─────────────────────────────────────────────────
    story += _build_calculos(loc, styles)
    story.append(_spacer(0.8))

    # ── Seção 6: Resultado ────────────────────────────────────────────────
    story += _build_resultado(loc, styles)
    story.append(_spacer(0.8))

    # ── Seção 7: Garantia e Condições ─────────────────────────────────────
    garantia = _build_garantia(loc, styles)
    if garantia:
        story += garantia
        story.append(_spacer(0.5))

    # ── Seção 8: Base Legal ───────────────────────────────────────────────
    story += _build_base_legal(loc, styles)
    story.append(_spacer(0.5))

    # ── Seção 9: Registro Fotográfico ─────────────────────────────────────
    fotos = _build_fotos(loc, styles, user)
    if fotos:
        story += fotos
        story.append(_spacer(0.5))

    # ── Seção 10: Responsável Técnico ─────────────────────────────────────
    story += _build_responsavel(loc, user, styles)

    doc.build(story)
    return buf.getvalue()
