"""DOCX generator for PTAM documents replicating the reference layout."""
from io import BytesIO
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


BRAND_GREEN = RGBColor(0x0D, 0x4F, 0x3C)
DARK = RGBColor(0x1A, 0x1A, 0x1A)


def _set_cell_bg(cell, color_hex: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tc_pr.append(shd)


def _add_heading(doc, text: str, size: int = 14, center: bool = True):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    r.font.color.rgb = BRAND_GREEN
    r.font.name = "Calibri"
    return p


def _add_section_title(doc, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text.upper())
    r.bold = True
    r.font.size = Pt(14)
    r.font.color.rgb = BRAND_GREEN
    doc.add_paragraph("_" * 80).alignment = WD_ALIGN_PARAGRAPH.CENTER


def _add_para(doc, text: str, bold: bool = False, size: int = 11, justify: bool = True):
    if not text:
        return
    p = doc.add_paragraph()
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for line in text.split("\n"):
        if line.strip() == "":
            p.add_run("\n")
            continue
        r = p.add_run(line + "\n")
        r.bold = bold
        r.font.size = Pt(size)
        r.font.name = "Calibri"


def _add_label_value(doc, label: str, value: str):
    if not value:
        return
    p = doc.add_paragraph()
    r1 = p.add_run(f"{label}: ")
    r1.bold = True
    r1.font.size = Pt(11)
    r2 = p.add_run(str(value))
    r2.font.size = Pt(11)


def _format_currency(v: float) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _format_area(v: float) -> str:
    try:
        return f"{float(v):,.2f} m²".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 m²"


def _samples_table(doc, samples: list):
    if not samples:
        return
    headers = ["Nº", "Bairro/Local", "Área Total (m²)", "Valor (R$)", "R$/m²"]
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 1"
    hdr_row = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        _set_cell_bg(cell, "0D4F3C")
    for idx, s in enumerate(samples, start=1):
        row = table.add_row()
        row.cells[0].text = str(s.get("number") or idx)
        row.cells[1].text = s.get("neighborhood", "") or ""
        row.cells[2].text = _format_area(s.get("area_total", 0)).replace(" m²", "")
        row.cells[3].text = _format_currency(s.get("value", 0)).replace("R$ ", "")
        vps = s.get("value_per_sqm") or (
            (s.get("value") or 0) / (s.get("area_total") or 1) if s.get("area_total") else 0
        )
        row.cells[4].text = f"{float(vps):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    doc.add_paragraph()


def _consolidation_table(doc, impact_areas: list):
    if not impact_areas:
        return
    headers = ["Área", "Metragem", "Valor Unitário", "Indenização"]
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 1"
    hdr_row = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        _set_cell_bg(cell, "0D4F3C")
    total = 0.0
    for a in impact_areas:
        row = table.add_row()
        row.cells[0].text = f"{a.get('name', '')} ({a.get('classification', '')})"
        row.cells[1].text = _format_area(a.get("area_sqm", 0))
        row.cells[2].text = _format_currency(a.get("unit_value", 0)) + "/m²"
        total_value = a.get("total_value") or (a.get("area_sqm", 0) * a.get("unit_value", 0))
        total += float(total_value or 0)
        row.cells[3].text = _format_currency(total_value)
    # Totals row
    tr = table.add_row()
    tr.cells[0].merge(tr.cells[2])
    tc = tr.cells[0]
    tc.text = ""
    p = tc.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run("TOTAL GERAL DA INDENIZAÇÃO")
    r.bold = True
    _set_cell_bg(tc, "E8F4EF")
    tr.cells[3].text = ""
    rp = tr.cells[3].paragraphs[0]
    rv = rp.add_run(_format_currency(total))
    rv.bold = True
    _set_cell_bg(tr.cells[3], "E8F4EF")
    doc.add_paragraph()
    return total


def generate_ptam_docx(ptam: dict, user: dict) -> bytes:
    """Generate a DOCX file from PTAM data. Returns bytes."""
    doc = Document()

    # Margins
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # --- COVER ---
    _add_heading(doc, "LAUDO DE PARECER TÉCNICO DE AVALIAÇÃO MERCADOLÓGICA", size=16)
    _add_heading(doc, f"PTAM nº {ptam.get('number', '---')}", size=14)
    doc.add_paragraph()

    _add_section_title(doc, "Imóvel Avaliado")
    _add_para(doc, ptam.get("property_label") or ptam.get("property_address", ""), bold=True)
    doc.add_paragraph()

    _add_label_value(doc, "Solicitante", ptam.get("solicitante", ""))
    _add_label_value(doc, "Processo", ptam.get("judicial_process", ""))
    _add_label_value(doc, "Ação", ptam.get("judicial_action", ""))
    _add_label_value(doc, "Fórum", ptam.get("forum", ""))
    _add_label_value(doc, "Requerente", ptam.get("requerente", ""))
    _add_label_value(doc, "Requerido", ptam.get("requerido", ""))
    _add_label_value(doc, "Juiz", ptam.get("judge", ""))
    doc.add_page_break()

    # --- FINALIDADE ---
    _add_section_title(doc, "Finalidade")
    _add_para(doc, ptam.get("purpose", ""))
    doc.add_paragraph()

    # --- IMÓVEL AVALIANDO ---
    _add_section_title(doc, "Imóvel Avaliando")
    _add_label_value(doc, "Endereço", ptam.get("property_address", ""))
    _add_label_value(doc, "Cidade/UF", ptam.get("property_city", ""))
    _add_label_value(doc, "Matrícula", ptam.get("property_matricula", ""))
    _add_label_value(doc, "Proprietário", ptam.get("property_owner", ""))
    area_ha = ptam.get("property_area_ha", 0)
    area_sqm = ptam.get("property_area_sqm", 0)
    if area_ha:
        _add_label_value(doc, "Área", f"{area_ha} hectares")
    if area_sqm:
        _add_label_value(doc, "Equivalente a", _format_area(area_sqm))
    _add_label_value(doc, "Confrontações", ptam.get("property_confrontations", ""))
    _add_para(doc, ptam.get("property_description", ""))
    doc.add_paragraph()

    # --- VISTORIA ---
    _add_section_title(doc, "Vistoria")
    _add_label_value(doc, "Data da Vistoria", ptam.get("vistoria_date", ""))
    _add_heading(doc, "1. Objetivo da Vistoria", size=12, center=False)
    _add_para(doc, ptam.get("vistoria_objective", ""))
    _add_heading(doc, "2. Metodologia Adotada", size=12, center=False)
    _add_para(doc, ptam.get("vistoria_methodology", ""))
    _add_heading(doc, "3. Caracterização Física", size=12, center=False)
    _add_label_value(doc, "3.1 Topografia", ptam.get("topography", ""))
    _add_label_value(doc, "3.2 Solo e Cobertura Vegetal", ptam.get("soil_vegetation", ""))
    _add_heading(doc, "4. Benfeitorias Existentes", size=12, center=False)
    _add_para(doc, ptam.get("benfeitorias", ""))
    _add_heading(doc, "5. Acessibilidade e Infraestrutura", size=12, center=False)
    _add_para(doc, ptam.get("accessibility", ""))
    _add_heading(doc, "6. Contexto Urbano e Mercadológico", size=12, center=False)
    _add_para(doc, ptam.get("urban_context", ""))
    _add_heading(doc, "7. Estado Geral de Conservação", size=12, center=False)
    _add_para(doc, ptam.get("conservation_state", ""))
    _add_heading(doc, "8. Síntese Conclusiva da Vistoria", size=12, center=False)
    _add_para(doc, ptam.get("vistoria_synthesis", ""))
    doc.add_page_break()

    # --- ANÁLISE MERCADOLÓGICA ---
    if ptam.get("market_analysis"):
        _add_section_title(doc, "Análise Mercadológica")
        _add_para(doc, ptam.get("market_analysis", ""))
        doc.add_paragraph()

    # --- METODOLOGIA ---
    _add_section_title(doc, "Metodologia Utilizada")
    _add_para(doc, ptam.get("methodology", ""), bold=True)
    _add_para(doc, ptam.get("methodology_justification", ""))
    doc.add_paragraph()

    # --- ÁREAS DE IMPACTO ---
    impact_areas = ptam.get("impact_areas", []) or []
    for idx, area in enumerate(impact_areas, start=1):
        _add_section_title(doc, f"Avaliação — {area.get('name', f'Área de Impacto {idx:02d}')}")
        _add_label_value(doc, "Classificação", area.get("classification", ""))
        _add_label_value(doc, "Área Impactada", _format_area(area.get("area_sqm", 0)))
        _add_label_value(doc, "Valor Unitário Adotado", _format_currency(area.get("unit_value", 0)) + "/m²")
        total_v = area.get("total_value") or (area.get("area_sqm", 0) * area.get("unit_value", 0))
        _add_label_value(doc, "Valor Indenizatório", _format_currency(total_v))
        if area.get("majoration_note"):
            _add_label_value(doc, "Majoração Aplicada", area.get("majoration_note", ""))
        if area.get("notes"):
            _add_para(doc, area.get("notes", ""))
        if area.get("samples"):
            _add_heading(doc, "Amostragem", size=12, center=False)
            _samples_table(doc, area.get("samples", []))
        doc.add_paragraph()

    # --- CONSOLIDAÇÃO ---
    if impact_areas:
        _add_section_title(doc, "Consolidação das Indenizações")
        total_calc = _consolidation_table(doc, impact_areas)
        if not ptam.get("total_indemnity"):
            ptam["total_indemnity"] = total_calc

    # --- CONCLUSÃO ---
    doc.add_page_break()
    _add_section_title(doc, "Conclusão")
    _add_para(doc, ptam.get("conclusion_text", ""))
    if ptam.get("total_indemnity"):
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(f"Valor Total da Indenização: {_format_currency(ptam.get('total_indemnity', 0))}")
        r.bold = True
        r.font.size = Pt(13)
        r.font.color.rgb = BRAND_GREEN
        if ptam.get("total_indemnity_words"):
            p2 = doc.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r2 = p2.add_run(f"({ptam.get('total_indemnity_words')})")
            r2.italic = True
            r2.font.size = Pt(11)

    doc.add_paragraph()
    doc.add_paragraph()
    city = ptam.get("conclusion_city", "Açailândia/MA")
    date_str = ptam.get("conclusion_date", datetime.utcnow().strftime("%d/%m/%Y"))
    loc = doc.add_paragraph(f"{city}, {date_str}.")
    loc.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # Signature block
    doc.add_paragraph()
    doc.add_paragraph()
    sig = doc.add_paragraph("_" * 50)
    sig.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_run = sp.add_run(user.get("name", "—"))
    name_run.bold = True
    role_p = doc.add_paragraph()
    role_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    role_p.add_run(user.get("role", ""))
    if user.get("crea"):
        crea_p = doc.add_paragraph()
        crea_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        crea_p.add_run(user.get("crea"))

    # Save to bytes
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
