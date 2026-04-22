# @module ptam_docx — Geração de DOCX para PTAM (Parecer Técnico de Avaliação Mercadológica)
"""DOCX generator for PTAM — mesmo padrão visual do locacao_docx.py.

Layout:
- Capa com logo, título, subtítulo, número, endereço, solicitante, data
- Seções numeradas com header verde (tabela 1×1, fundo #1B4D1B, texto branco)
- Tabelas formatadas com cabeçalho verde
- Fotos do imóvel com legenda
- Responsável técnico com assinatura
- Cores: Verde (#1B4D1B) e Dourado (#D4A830)
"""
from io import BytesIO
from datetime import datetime

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io


# ── Cores Romatec ─────────────────────────────────────────────────────────────
GREEN = RGBColor(27, 77, 27)       # #1B4D1B
GOLD = RGBColor(212, 168, 48)      # #D4A830
WHITE = RGBColor(255, 255, 255)
DARK = RGBColor(26, 26, 26)
LIGHT_GREEN = RGBColor(232, 245, 233)


# ── helpers de célula ─────────────────────────────────────────────────────────

def _set_cell_shading(cell, color_hex: str) -> None:
    """Aplica cor de fundo a uma célula (hex sem #)."""
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), color_hex)
    cell._tc.get_or_add_tcPr().append(shading)


def _set_cell_border(cell) -> None:
    """Define bordas verdes na célula."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        edge_el = OxmlElement(f"w:{edge}")
        edge_el.set(qn("w:val"), "single")
        edge_el.set(qn("w:sz"), "4")
        edge_el.set(qn("w:color"), "1B4D1B")
        tcBorders.append(edge_el)
    tcPr.append(tcBorders)


# ── helpers de parágrafo ──────────────────────────────────────────────────────

def _add_styled_paragraph(doc, text: str, bold: bool = False, italic: bool = False,
                           size: int = 11, color=RGBColor(51, 51, 51),
                           alignment=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(6)):
    """Adiciona parágrafo formatado."""
    p = doc.add_paragraph()
    p.alignment = alignment
    p.paragraph_format.space_after = space_after
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return p


def _add_section_heading(doc, text: str):
    """Título de seção: tabela 1×1 com fundo verde escuro, texto branco — igual locacao_docx."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = table.cell(0, 0)
    cell.text = text
    _set_cell_shading(cell, "1B4D1B")
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = cell.paragraphs[0].runs[0]
    run.font.color.rgb = WHITE
    run.font.bold = True
    run.font.size = Pt(12)
    doc.add_paragraph()
    return table


def _add_label_value(doc, label: str, value, bold_label: bool = True):
    """Adiciona linha label: valor."""
    text = _fmt_val(value)
    if not text or not text.strip():
        return
    p = doc.add_paragraph()
    r1 = p.add_run(f"{label}: ")
    r1.bold = bold_label
    r1.font.size = Pt(11)
    r2 = p.add_run(str(text))
    r2.font.size = Pt(11)


def _fmt_val(val) -> str:
    if val is None:
        return ""
    if isinstance(val, bool):
        return "Sim" if val else "Não"
    if isinstance(val, list):
        return ", ".join(str(i) for i in val if i is not None and str(i).strip())
    if isinstance(val, dict):
        return " | ".join(f"{k}: {v}" for k, v in val.items() if v is not None and str(v).strip())
    return str(val)


def _format_currency(value) -> str:
    try:
        v = float(value) if value else 0
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _format_area(value) -> str:
    try:
        return f"{float(value):,.2f} m²".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 m²"


# ── renderers de seção ────────────────────────────────────────────────────────

def _render_cover(doc: Document, ptam: dict, user: dict) -> None:
    """Capa: logo, título, subtítulo, número, endereço, solicitante, data."""
    # Logo da empresa
    company_logo = user.get("_company_logo_bytes")
    if company_logo:
        try:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(io.BytesIO(company_logo), width=Inches(1.5))
        except Exception:
            pass

    # Título principal
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("PARECER TÉCNICO DE AVALIAÇÃO MERCADOLÓGICA")
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = GREEN

    # Subtítulo
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Avaliação de Imóvel Urbano — NBR 14653")
    run.font.size = Pt(14)
    run.font.italic = True
    run.font.color.rgb = DARK

    doc.add_paragraph()

    # Número do laudo
    numero = ptam.get("number") or ptam.get("numero") or "PTAM-0000/0000"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"Laudo nº {numero}")
    run.font.size = Pt(16)
    run.font.bold = True
    run.font.color.rgb = DARK

    doc.add_paragraph()

    # Endereço do imóvel
    endereco = ptam.get("property_address") or ""
    city_uf = ptam.get("property_city") or ""
    if endereco:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{endereco}\n{city_uf}" if city_uf else endereco)
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = DARK

    doc.add_paragraph()

    # Solicitante / data
    _add_styled_paragraph(doc, f"Solicitante: {ptam.get('solicitante', 'Não informado')}",
                          bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    _add_styled_paragraph(doc, f"Cidade: {city_uf or 'Não informado'}",
                          alignment=WD_ALIGN_PARAGRAPH.CENTER)
    data_ref = ptam.get("vistoria_date") or ptam.get("conclusion_date") or datetime.now().strftime("%d/%m/%Y")
    _add_styled_paragraph(doc, f"Data: {data_ref}", alignment=WD_ALIGN_PARAGRAPH.CENTER)

    doc.add_page_break()


def _render_identificacao(doc: Document, ptam: dict) -> None:
    """Seção 1 — Identificação."""
    _add_section_heading(doc, "1. IDENTIFICAÇÃO")

    numero = ptam.get("number") or ptam.get("numero") or "PTAM-0000/0000"
    _add_styled_paragraph(doc, f"Número do Laudo: {numero}", bold=True)
    _add_label_value(doc, "Solicitante", ptam.get("solicitante"))
    _add_label_value(doc, "Processo Judicial", ptam.get("judicial_process"))
    _add_label_value(doc, "Ação", ptam.get("judicial_action"))
    _add_label_value(doc, "Fórum", ptam.get("forum"))
    _add_label_value(doc, "Requerente", ptam.get("requerente"))
    _add_label_value(doc, "Requerido", ptam.get("requerido"))
    _add_label_value(doc, "Juiz", ptam.get("judge"))
    _add_label_value(doc, "Data de Referência", ptam.get("vistoria_date"))


def _render_imovel(doc: Document, ptam: dict) -> None:
    """Seção 2 — Imóvel Avaliado."""
    _add_section_heading(doc, "2. IMÓVEL AVALIADO")

    _add_label_value(doc, "Endereço", ptam.get("property_address"))
    _add_label_value(doc, "Cidade / UF", ptam.get("property_city"))
    _add_label_value(doc, "Matrícula", ptam.get("property_matricula"))
    _add_label_value(doc, "Proprietário", ptam.get("property_owner"))
    if ptam.get("property_area_ha"):
        _add_label_value(doc, "Área", f"{ptam.get('property_area_ha')} hectares")
    if ptam.get("property_area_sqm"):
        _add_label_value(doc, "Área equivalente", _format_area(ptam.get("property_area_sqm")))
    _add_label_value(doc, "Confrontações", ptam.get("property_confrontations"))
    if ptam.get("property_description"):
        _add_styled_paragraph(doc, ptam["property_description"],
                               alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)


def _render_finalidade(doc: Document, ptam: dict) -> None:
    """Seção 3 — Finalidade."""
    _add_section_heading(doc, "3. FINALIDADE")
    if ptam.get("purpose"):
        _add_styled_paragraph(doc, ptam["purpose"], alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)


def _render_vistoria(doc: Document, ptam: dict) -> None:
    """Seção 4 — Vistoria."""
    _add_section_heading(doc, "4. VISTORIA")

    _add_label_value(doc, "Data da Vistoria", ptam.get("vistoria_date"))
    _add_label_value(doc, "Objetivo", ptam.get("vistoria_objective"))
    _add_label_value(doc, "Metodologia", ptam.get("vistoria_methodology"))
    _add_label_value(doc, "Topografia", ptam.get("topography"))
    _add_label_value(doc, "Solo e Cobertura Vegetal", ptam.get("soil_vegetation"))
    _add_label_value(doc, "Benfeitorias", ptam.get("benfeitorias"))
    _add_label_value(doc, "Acessibilidade e Infraestrutura", ptam.get("accessibility"))
    _add_label_value(doc, "Contexto Urbano e Mercadológico", ptam.get("urban_context"))
    _add_label_value(doc, "Estado Geral de Conservação", ptam.get("conservation_state"))
    if ptam.get("vistoria_synthesis"):
        _add_styled_paragraph(doc, ptam["vistoria_synthesis"],
                               alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)


def _render_metodologia(doc: Document, ptam: dict) -> None:
    """Seção 5 — Metodologia."""
    _add_section_heading(doc, "5. METODOLOGIA")

    if ptam.get("methodology"):
        _add_styled_paragraph(doc, ptam["methodology"], bold=True,
                               alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)
    if ptam.get("methodology_justification"):
        _add_styled_paragraph(doc, ptam["methodology_justification"],
                               alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)
    if ptam.get("market_analysis"):
        _add_styled_paragraph(doc, ptam["market_analysis"],
                               alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)


def _render_amostras_table(doc, samples: list) -> None:
    """Tabela de amostras de mercado com cabeçalho verde."""
    if not samples:
        return
    headers = ["Nº", "Bairro / Local", "Área Total (m²)", "Valor (R$)", "R$/m²"]
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        _set_cell_shading(hdr_cells[i], "1B4D1B")
        hdr_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in hdr_cells[i].paragraphs[0].runs:
            run.font.color.rgb = WHITE
            run.font.bold = True
            run.font.size = Pt(10)

    for idx, s in enumerate(samples, start=1):
        row_cells = table.add_row().cells
        row_cells[0].text = str(s.get("number") or idx)
        row_cells[1].text = s.get("neighborhood") or ""
        area = s.get("area_total", 0) or 0
        row_cells[2].text = _format_area(area).replace(" m²", "")
        valor = s.get("value", 0) or 0
        row_cells[3].text = _format_currency(valor).replace("R$ ", "")
        vps = s.get("value_per_sqm") or (float(valor) / float(area) if float(area) > 0 else 0)
        row_cells[4].text = f"{float(vps):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        for cell in row_cells:
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()


def _render_areas_impacto(doc: Document, impact_areas: list) -> None:
    """Seção 6 — Avaliação por Área de Impacto."""
    if not impact_areas:
        return
    _add_section_heading(doc, "6. AVALIAÇÃO DAS ÁREAS DE IMPACTO")

    for idx, area in enumerate(impact_areas, start=1):
        # Sub-heading por área
        p = doc.add_paragraph()
        run = p.add_run(f"Área {idx}: {area.get('name', f'Área {idx}')}")
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = GREEN

        _add_label_value(doc, "Classificação", area.get("classification"))
        _add_label_value(doc, "Área Impactada", _format_area(area.get("area_sqm", 0)))
        _add_label_value(doc, "Valor Unitário Adotado",
                          _format_currency(area.get("unit_value", 0)) + "/m²")
        total_v = area.get("total_value") or (
            (area.get("area_sqm") or 0) * (area.get("unit_value") or 0)
        )
        _add_label_value(doc, "Valor Indenizatório", _format_currency(total_v))
        if area.get("majoration_note"):
            _add_label_value(doc, "Majoração Aplicada", area.get("majoration_note"))
        if area.get("notes"):
            _add_styled_paragraph(doc, area["notes"], alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)
        if area.get("samples"):
            _add_styled_paragraph(doc, "Amostragem:", bold=True)
            _render_amostras_table(doc, area["samples"])
        doc.add_paragraph()


def _render_consolidacao_table(doc, impact_areas: list):
    """Tabela de consolidação das indenizações com cabeçalho verde."""
    if not impact_areas:
        return 0.0
    headers = ["Área", "Metragem", "Valor Unitário", "Indenização"]
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        _set_cell_shading(hdr_cells[i], "1B4D1B")
        hdr_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in hdr_cells[i].paragraphs[0].runs:
            run.font.color.rgb = WHITE
            run.font.bold = True

    total = 0.0
    for a in impact_areas:
        row = table.add_row()
        row.cells[0].text = f"{a.get('name', '')} ({a.get('classification', '')})"
        row.cells[1].text = _format_area(a.get("area_sqm", 0))
        row.cells[2].text = _format_currency(a.get("unit_value", 0)) + "/m²"
        total_value = a.get("total_value") or (
            (a.get("area_sqm") or 0) * (a.get("unit_value") or 0)
        )
        total += float(total_value or 0)
        row.cells[3].text = _format_currency(total_value)
        for cell in row.cells:
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Linha de total
    tr = table.add_row()
    tr.cells[0].merge(tr.cells[2])
    tc = tr.cells[0]
    tc.text = ""
    p = tc.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run("TOTAL GERAL DA INDENIZAÇÃO")
    r.bold = True
    _set_cell_shading(tc, "E8F5E9")
    tr.cells[3].text = ""
    rp = tr.cells[3].paragraphs[0]
    rv = rp.add_run(_format_currency(total))
    rv.bold = True
    _set_cell_shading(tr.cells[3], "E8F5E9")
    doc.add_paragraph()
    return total


def _render_consolidacao(doc: Document, ptam: dict, impact_areas: list) -> float:
    """Seção 7 — Consolidação das Indenizações."""
    if not impact_areas:
        return 0.0
    _add_section_heading(doc, "7. CONSOLIDAÇÃO DAS INDENIZAÇÕES")
    total = _render_consolidacao_table(doc, impact_areas)
    return total


def _render_conclusao(doc: Document, ptam: dict, total_indemnity: float) -> None:
    """Seção 8 — Conclusão."""
    _add_section_heading(doc, "8. CONCLUSÃO")

    if ptam.get("conclusion_text"):
        _add_styled_paragraph(doc, ptam["conclusion_text"],
                               alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)

    total = ptam.get("total_indemnity") or total_indemnity
    if total:
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run("Valor Total da Indenização: ")
        run.font.bold = True
        run.font.size = Pt(12)
        run2 = p.add_run(_format_currency(total))
        run2.font.bold = True
        run2.font.size = Pt(14)
        run2.font.color.rgb = GREEN

        if ptam.get("total_indemnity_words"):
            _add_styled_paragraph(doc, f"({ptam['total_indemnity_words']})",
                                   italic=True, alignment=WD_ALIGN_PARAGRAPH.CENTER)

        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p2.add_run(
            "Este Parecer Técnico tem validade de 6 meses a contar da data de emissão, "
            "conforme ABNT NBR 14653-1. Após esse período, nova avaliação deverá ser realizada."
        ).font.size = Pt(10)


def _render_base_legal(doc: Document) -> None:
    """Seção 9 — Base Legal e Normativa."""
    _add_section_heading(doc, "9. BASE LEGAL E NORMATIVA")

    _add_styled_paragraph(doc, "Esta avaliação foi elaborada com base nas seguintes normas:",
                           alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)
    normas = [
        "ABNT NBR 14653-1: Procedimentos gerais de avaliação de bens.",
        "ABNT NBR 14653-2: Avaliação de imóveis urbanos — Método Comparativo Direto.",
        "ABNT NBR 14653-3: Avaliação de imóveis rurais.",
        "Resolução COFECI 957/2006: Habilita o Corretor de Imóveis para elaboração de PTAM.",
        "Lei 8.245/1991 — Lei do Inquilinato (quando aplicável).",
        "Código Civil — arts. 1.196 a 1.368 (direito de propriedade).",
    ]
    for item in normas:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item).font.size = Pt(10)


def _render_fotos(doc: Document, fotos: list) -> None:
    """Seção 10 — Registro Fotográfico."""
    _add_section_heading(doc, "10. REGISTRO FOTOGRÁFICO")

    if not fotos:
        _add_styled_paragraph(doc, "Nenhuma foto anexada.")
        return

    _add_styled_paragraph(doc, "Fotografias do imóvel avaliado, obtidas na data da vistoria:")
    _add_styled_paragraph(doc, f"Total de {len(fotos)} foto(s) anexada(s) ao processo.")

    for i, foto in enumerate(fotos[:6]):
        img_bytes = None
        if isinstance(foto, dict):
            img_bytes = foto.get("_image_bytes")
            if not img_bytes:
                import base64, urllib.request
                url = foto.get("url", "")
                if url:
                    try:
                        if url.startswith("data:"):
                            img_bytes = base64.b64decode(url.split(",", 1)[-1])
                        else:
                            with urllib.request.urlopen(url, timeout=5) as resp:
                                img_bytes = resp.read()
                    except Exception:
                        img_bytes = None

        if img_bytes:
            try:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.add_picture(io.BytesIO(img_bytes), width=Inches(4))
                caption = (foto.get("caption") or foto.get("legenda") or f"Foto {i + 1}"
                           if isinstance(foto, dict) else f"Foto {i + 1}")
                _add_styled_paragraph(doc, caption, alignment=WD_ALIGN_PARAGRAPH.CENTER, size=10)
            except Exception:
                pass


def _render_responsavel(doc: Document, ptam: dict, user: dict) -> None:
    """Seção 11 — Responsável Técnico."""
    _add_section_heading(doc, "11. RESPONSÁVEL TÉCNICO")

    tipo_prof = ptam.get("tipo_profissional") or user.get("role", "")
    tipo_map = {
        "corretor": "Corretor de Imóveis habilitado nos termos da Resolução COFECI 957/2006",
        "engenheiro": "Engenheiro com Anotação de Responsabilidade Técnica (ART) conforme Resolução CONFEA 345/90",
        "arquiteto": "Arquiteto e Urbanista com Registro de Responsabilidade Técnica (RRT)",
        "perito_judicial": "Perito Judicial cadastrado no Tribunal, habilitado nos termos do CPC art. 156",
    }
    tipo_desc = tipo_map.get(tipo_prof, tipo_prof or "Profissional habilitado")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.add_run(
        f"O(A) profissional signatário(a) deste Parecer Técnico de Avaliação Mercadológica é "
        f"{tipo_desc}, responsabilizando-se técnica e legalmente pelo conteúdo e pelos valores "
        f"aqui expressos, conforme as normas regulamentadoras vigentes."
    ).font.size = Pt(11)

    doc.add_paragraph()
    doc.add_paragraph()

    # Local / data
    city = ptam.get("conclusion_city") or ptam.get("property_city") or "Mirador, MA"
    date_str = ptam.get("conclusion_date") or datetime.now().strftime("%d/%m/%Y")
    loc_p = doc.add_paragraph(f"{city}, {date_str}.")
    loc_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()
    doc.add_paragraph()

    # Assinatura
    sig_p = doc.add_paragraph("_" * 50)
    sig_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    nome = user.get("nome") or user.get("name") or ptam.get("conclusion_city", "Não informado")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(nome)
    run.font.bold = True
    run.font.size = Pt(12)

    for field, label in [
        ("creci", "CRECI"),
        ("cna", "CNAI"),
        ("crea", "CREA"),
        ("cau", "CAU"),
    ]:
        val = user.get(field) or ptam.get(field)
        if val:
            _add_styled_paragraph(doc, f"{label}: {val}",
                                   alignment=WD_ALIGN_PARAGRAPH.CENTER)


# ── entry point ───────────────────────────────────────────────────────────────

def generate_ptam_docx(ptam: dict, user: dict) -> bytes:
    """Gera DOCX do PTAM com padrão visual locacao_docx. Retorna bytes."""
    if user is None:
        user = {}

    doc = Document()

    # Margens A4
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # ── Capa ──────────────────────────────────────────────────────────────────
    _render_cover(doc, ptam, user)

    # ── Corpo ─────────────────────────────────────────────────────────────────
    _render_identificacao(doc, ptam)
    doc.add_paragraph()

    _render_imovel(doc, ptam)
    doc.add_paragraph()

    _render_finalidade(doc, ptam)
    doc.add_paragraph()

    _render_vistoria(doc, ptam)
    doc.add_paragraph()

    _render_metodologia(doc, ptam)
    doc.add_paragraph()

    impact_areas = ptam.get("impact_areas") or []
    _render_areas_impacto(doc, impact_areas)

    total_calc = _render_consolidacao(doc, ptam, impact_areas)
    if not ptam.get("total_indemnity"):
        ptam["total_indemnity"] = total_calc
    doc.add_paragraph()

    doc.add_page_break()

    _render_conclusao(doc, ptam, total_calc)
    doc.add_paragraph()

    _render_base_legal(doc)
    doc.add_paragraph()

    fotos = ptam.get("fotos_imovel") or ptam.get("photos") or []
    _render_fotos(doc, fotos)
    doc.add_paragraph()

    doc.add_page_break()
    _render_responsavel(doc, ptam, user)

    # ── salvar ────────────────────────────────────────────────────────────────
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
