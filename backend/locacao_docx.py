# @module locacao_docx — Geração de DOCX para Avaliação de Locação
"""DOCX generator for Avaliação de Locação — Lei 8.245/91."""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
from datetime import datetime


def _set_cell_shading(cell, color: str):
    """Aplica cor de fundo a uma célula (hex sem #)."""
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color)
    cell._tc.get_or_add_tcPr().append(shading)


def _add_heading(doc, text: str, level: int = 1):
    """Adiciona título formatado."""
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in p.runs:
        run.font.color.rgb = RGBColor(0, 102, 51)  # Verde Romatec
        run.font.bold = True
    return p


def _add_paragraph(doc, text: str, bold: bool = False, size: int = 11):
    """Adiciona parágrafo formatado."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(51, 51, 51)
    return p


def _format_currency(value) -> str:
    """Formata valor como moeda brasileira."""
    try:
        v = float(value) if value else 0
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


def generate_locacao_docx(loc: dict, user: dict | None = None) -> bytes:
    """Generate DOCX for Avaliação de Locação. Returns bytes."""
    doc = Document()
    
    # Configura margens
    sections = doc.sections[0]
    sections.top_margin = Cm(2)
    sections.bottom_margin = Cm(2)
    sections.left_margin = Cm(2.5)
    sections.right_margin = Cm(2.5)
    
    # ── Cabeçalho ───────────────────────────────────────────────────────────
    header = doc.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run("AVALIAÇÃO DE LOCAÇÃO")
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 102, 51)
    
    # Número do laudo
    numero = loc.get("numero_locacao") or "LOC-0000/0000"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"Laudo nº {numero}")
    run.font.size = Pt(12)
    run.font.bold = True
    
    doc.add_paragraph()  # Espaço
    
    # ── 1. Identificação ────────────────────────────────────────────────────
    _add_heading(doc, "1. IDENTIFICAÇÃO", level=2)
    
    solicitante = loc.get("solicitante", {})
    _add_paragraph(doc, f"Solicitante: {solicitante.get('nome', 'Não informado')}")
    _add_paragraph(doc, f"CPF/CNPJ: {solicitante.get('cpf_cnpj', 'Não informado')}")
    _add_paragraph(doc, f"Objetivo: {loc.get('objetivo', 'Avaliação de aluguel conforme Lei 8.245/91')}")
    
    data_vistoria = loc.get("data_vistoria", "")
    if data_vistoria:
        try:
            dt = datetime.fromisoformat(data_vistoria.replace('Z', '+00:00'))
            data_str = dt.strftime("%d/%m/%Y")
        except:
            data_str = data_vistoria
        _add_paragraph(doc, f"Data da Vistoria: {data_str}")
    
    doc.add_paragraph()
    
    # ── 2. Imóvel Avaliado ──────────────────────────────────────────────────
    _add_heading(doc, "2. IMÓVEL AVALIADO", level=2)
    
    endereco = loc.get("endereco", {})
    endereco_str = f"{endereco.get('logradouro', '')}, {endereco.get('numero', '')}"
    if endereco.get('complemento'):
        endereco_str += f" - {endereco['complemento']}"
    endereco_str += f"\n{endereco.get('bairro', '')}, {endereco.get('cidade', '')} - {endereco.get('uf', '')}"
    endereco_str += f"\nCEP: {endereco.get('cep', 'Não informado')}"
    
    _add_paragraph(doc, f"Endereço: {endereco_str}")
    _add_paragraph(doc, f"Tipo: {loc.get('tipo_imovel', 'Não informado')}")
    
    # Características
    caracteristicas = loc.get("caracteristicas", {})
    if caracteristicas:
        _add_paragraph(doc, "Características:", bold=True)
        if caracteristicas.get('area_util'):
            _add_paragraph(doc, f"  • Área útil: {caracteristicas['area_util']} m²")
        if caracteristicas.get('area_total'):
            _add_paragraph(doc, f"  • Área total: {caracteristicas['area_total']} m²")
        if caracteristicas.get('quartos'):
            _add_paragraph(doc, f"  • Quartos: {caracteristicas['quartos']}")
        if caracteristicas.get('banheiros'):
            _add_paragraph(doc, f"  • Banheiros: {caracteristicas['banheiros']}")
        if caracteristicas.get('vagas'):
            _add_paragraph(doc, f"  • Vagas: {caracteristicas['vagas']}")
        if caracteristicas.get('conservacao'):
            _add_paragraph(doc, f"  • Estado de conservação: {caracteristicas['conservacao']}")
    
    doc.add_paragraph()
    
    # ── 3. Região e Entorno ─────────────────────────────────────────────────
    _add_heading(doc, "3. REGIÃO E ENTORNO", level=2)
    
    regiao = loc.get("regiao_entorno", {})
    if regiao:
        _add_paragraph(doc, f"Infraestrutura: {regiao.get('infraestrutura', 'Não avaliada')}")
        _add_paragraph(doc, f"Acessos: {regiao.get('acessos', 'Não avaliados')}")
        _add_paragraph(doc, f"Serviços próximos: {regiao.get('servicos', 'Não informado')}")
    else:
        _add_paragraph(doc, "Região não detalhada no cadastro.")
    
    doc.add_paragraph()
    
    # ── 4. Pesquisa de Mercado ───────────────────────────────────────────────
    _add_heading(doc, "4. PESQUISA DE MERCADO", level=2)
    
    comparativos = loc.get("comparativos", [])
    if comparativos:
        # Tabela de comparativos
        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        
        # Cabeçalho
        hdr_cells = table.rows[0].cells
        headers = ["Endereço", "Área (m²)", "Aluguel (R$)", "R$/m²", "Fonte"]
        for i, h in enumerate(headers):
            hdr_cells[i].text = h
            _set_cell_shading(hdr_cells[i], "006633")
            for paragraph in hdr_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.font.bold = True
        
        # Dados
        valores_m2 = []
        for comp in comparativos:
            row_cells = table.add_row().cells
            row_cells[0].text = comp.get("endereco", "Não informado")
            row_cells[1].text = str(comp.get("area", "-"))
            row_cells[2].text = _format_currency(comp.get("aluguel"))
            
            area = float(comp.get("area", 1) or 1)
            aluguel = float(comp.get("aluguel", 0) or 0)
            valor_m2 = aluguel / area if area > 0 else 0
            valores_m2.append(valor_m2)
            row_cells[3].text = f"R$ {valor_m2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            row_cells[4].text = comp.get("fonte", "Pesquisa de mercado")
        
        doc.add_paragraph()
        
        # Estatísticas
        if valores_m2:
            import statistics
            media = statistics.mean(valores_m2)
            _add_paragraph(doc, f"Média do mercado: R$ {media:,.2f}/m²".replace(",", "X").replace(".", ",").replace("X", "."), bold=True)
    else:
        _add_paragraph(doc, "Nenhum comparativo cadastrado.")
    
    doc.add_paragraph()
    
    # ── 5. Resultado da Avaliação ────────────────────────────────────────────
    _add_heading(doc, "5. RESULTADO DA AVALIAÇÃO", level=2)
    
    resultado = loc.get("resultado", {})
    if resultado:
        valor_estimado = resultado.get("valor_mensal_estimado", 0)
        intervalo_min = resultado.get("intervalo_min", 0)
        intervalo_max = resultado.get("intervalo_max", 0)
        
        p = doc.add_paragraph()
        run = p.add_run("VALOR MENSAL ESTIMADO: ")
        run.font.bold = True
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0, 102, 51)
        
        run = p.add_run(_format_currency(valor_estimado))
        run.font.bold = True
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(0, 102, 51)
        
        if intervalo_min and intervalo_max:
            _add_paragraph(doc, f"Intervalo de mercado: {_format_currency(intervalo_min)} a {_format_currency(intervalo_max)}")
        
        if resultado.get("fator_locacao"):
            _add_paragraph(doc, f"Fator de locação aplicado: {resultado['fator_locacao']}")
        
        if resultado.get("metodo"):
            _add_paragraph(doc, f"Método: {resultado['metodo']}")
    else:
        _add_paragraph(doc, "Resultado não calculado.", bold=True)
    
    doc.add_paragraph()
    
    # ── 6. Garantia e Condições ──────────────────────────────────────────────
    _add_heading(doc, "6. GARANTIA E CONDIÇÕES", level=2)
    
    garantia = loc.get("garantia", {})
    if garantia:
        _add_paragraph(doc, f"Tipo de garantia: {garantia.get('tipo', 'Não informado')}")
        _add_paragraph(doc, f"Prazo de locação: {garantia.get('prazo', 'Não informado')}")
        if garantia.get('observacoes'):
            _add_paragraph(doc, f"Observações: {garantia['observacoes']}")
    else:
        _add_paragraph(doc, "Condições não especificadas.")
    
    doc.add_paragraph()
    
    # ── 7. Base Legal ────────────────────────────────────────────────────────
    _add_heading(doc, "7. BASE LEGAL", level=2)
    
    _add_paragraph(doc, "• Lei nº 8.245/1991 — Lei do Inquilinato")
    _add_paragraph(doc, "• Código Civil Brasileiro — Arts. 1.047 a 1.215")
    _add_paragraph(doc, "• NBR 14.653 — Norma Brasileira de Avaliação de Imóveis")
    
    doc.add_paragraph()
    
    # ── 8. Responsável Técnico ───────────────────────────────────────────────
    _add_heading(doc, "8. RESPONSÁVEL TÉCNICO", level=2)
    
    if user:
        _add_paragraph(doc, f"Nome: {user.get('nome', user.get('name', 'Não informado'))}")
        if user.get('creci'):
            _add_paragraph(doc, f"CRECI: {user['creci']}")
        if user.get('cna'):
            _add_paragraph(doc, f"CNAI: {user['cna']}")
        if user.get('company'):
            _add_paragraph(doc, f"Empresa: {user['company']}")
    else:
        _add_paragraph(doc, "Responsável técnico não identificado.")
    
    # Data do laudo
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    data_atual = datetime.now().strftime("%d/%m/%Y")
    run = p.add_run(f"Mirador, MA, {data_atual}")
    run.font.italic = True
    
    # ── Salvar em bytes ──────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
