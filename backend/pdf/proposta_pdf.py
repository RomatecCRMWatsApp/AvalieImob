# @module pdf.proposta_pdf — PDF da Proposta de Consultoria (layout AvalieImob).
# Genérico: renderiza o `custos_calculados` (seções 1-5 + condições + checklist + avisos)
# de QUALQUER subtipo. Marca "A" via pdf.brand_seal (não copia o layout do ZAYRA).
from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)

VERDE = colors.HexColor("#0C3320")
VERDE_CLR = colors.HexColor("#EAF2EC")
DOURADO = colors.HexColor("#B8860B")
CINZA = colors.HexColor("#5B7466")
PRETO = colors.HexColor("#1A1A1A")
PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
UTIL_W = PAGE_W - 2 * MARGIN


def _brl(v) -> str:
    try:
        s = f"{float(v):,.2f}"
    except Exception:
        s = "0,00"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _esc(s) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles():
    return {
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, textColor=VERDE, spaceAfter=2),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, textColor=CINZA, spaceAfter=8),
        "sec": ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=11, textColor=VERDE,
                              spaceBefore=12, spaceAfter=5),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9, textColor=PRETO,
                               alignment=TA_JUSTIFY, leading=13),
        "li": ParagraphStyle("li", fontName="Helvetica", fontSize=9, textColor=PRETO, leading=13,
                             leftIndent=10, bulletIndent=2),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, textColor=PRETO, leading=11),
        "cellr": ParagraphStyle("cellr", fontName="Helvetica-Bold", fontSize=8.5, textColor=PRETO,
                                alignment=TA_RIGHT),
        "obs": ParagraphStyle("obs", fontName="Helvetica-Oblique", fontSize=7, textColor=CINZA, leading=9),
        "aviso": ParagraphStyle("aviso", fontName="Helvetica", fontSize=7.5, textColor=CINZA,
                                alignment=TA_JUSTIFY, leading=10, spaceAfter=3),
    }


def _tabela_itens(itens, st):
    rows = []
    for it in itens or []:
        desc = _esc(it.get("descricao", ""))
        obs = it.get("observacao")
        cell = [Paragraph(desc, st["cell"])]
        if obs:
            cell.append(Paragraph(_esc(obs), st["obs"]))
        valor = "—" if it.get("pendente") else _brl(it.get("valor", 0))
        rows.append([cell, Paragraph(valor, st["cellr"])])
    if not rows:
        return None
    t = Table(rows, colWidths=[UTIL_W - 3.2 * cm, 3.2 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDE5E0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _anexo_flowables(anexos_bytes, st):
    """Anexos (imagens) ao fim da proposta — 1 por página, escalada à largura."""
    from reportlab.platypus import PageBreak, Image as RLImage
    from reportlab.lib.utils import ImageReader
    out = []
    n = 0
    for raw in (anexos_bytes or []):
        if not raw:
            continue
        try:
            ir = ImageReader(io.BytesIO(raw))
            iw, ih = ir.getSize()
            w = UTIL_W
            h = w * (ih / float(iw)) if iw else w
            max_h = PAGE_H - 6 * cm
            if h > max_h:
                h = max_h
                w = h * (iw / float(ih)) if ih else w
            n += 1
            out.append(PageBreak())
            if n == 1:
                out.append(Paragraph("Anexos da Proposta", st["sec"]))
            img = RLImage(io.BytesIO(raw), width=w, height=h)
            img.hAlign = "CENTER"
            out.append(img)
            out.append(Paragraph(f"Anexo {n}", st["obs"]))
        except Exception:
            continue
    return out


def _croqui_flowables(proposta, st):
    """Croqui do imóvel (§9 4.6) + croqui de alinhamento de cerca (§9 4.7) quando a
    proposta de demarcação tem pontos em dados_imovel. [] se <3 vértices válidos."""
    dados = proposta.get("dados_imovel") or {}
    pontos = dados.get("pontos") or []
    try:
        from services.pricing.demarcacao_geo import (
            projeto_croqui, normalizar_pontos, extensao_alinhamento)
        from services.geo_urbano.generators.croqui import croqui_drawing
    except Exception:
        return []
    validos = [p for p in normalizar_pontos(pontos) if p.get("coord_e") is not None]
    if len(validos) < 3:
        return []
    proj = projeto_croqui(pontos, dados.get("confrontantes"))
    d = croqui_drawing(proj, width=UTIL_W, height=9.5 * cm)
    if d is None:
        return []
    out = [Spacer(1, 6), Paragraph("4.6. Croqui do Imóvel", st["sec"]), d,
           Paragraph("Poligonal georreferenciada — SIRGAS 2000 / UTM.", st["obs"])]
    alinhar = dados.get("alinhamento_lados") or []
    if alinhar:
        da = croqui_drawing(proj, width=UTIL_W, height=9.5 * cm,
                            destacar_lados=alinhar, titulo_destaque="Cerca a ser alinhada")
        if da is not None:
            out += [Spacer(1, 6), Paragraph("4.7. Croqui de Alinhamento de Cerca", st["sec"]), da]
            try:
                ext = extensao_alinhamento(pontos, alinhar)
            except Exception:
                ext = 0
            if ext:
                metros = ("%.2f" % ext).replace(".", ",")
                out.append(Paragraph(
                    f"Extensão total de cerca a alinhar: {metros} m.", st["obs"]))
    return out


def gerar_proposta_pdf(proposta: dict, perfil: dict = None, user: dict = None, anexos_bytes=None) -> bytes:
    st = _styles()
    custos = proposta.get("custos_calculados") or {}
    numero = proposta.get("numero", "—")
    subtipo_label = proposta.get("subtipo_label") or proposta.get("subtipo", "")

    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=2.6 * cm, bottomMargin=1.9 * cm, title=f"Proposta {numero}")
    frame = Frame(MARGIN, 1.9 * cm, UTIL_W, PAGE_H - 4.5 * cm, id="corpo")

    def _header_footer(c, d):
        c.saveState()
        # topo: barra + lockup
        c.setFillColor(VERDE); c.rect(0, PAGE_H - 0.16 * cm, PAGE_W, 0.16 * cm, stroke=0, fill=1)
        c.setFillColor(DOURADO); c.rect(0, PAGE_H - 0.24 * cm, PAGE_W, 0.08 * cm, stroke=0, fill=1)
        try:
            from pdf.brand_seal import draw_header_monogram
            draw_header_monogram(c, MARGIN, PAGE_H - 1.7 * cm, fs=12)
        except Exception:
            c.setFillColor(VERDE); c.setFont("Helvetica-Bold", 13)
            c.drawString(MARGIN, PAGE_H - 1.6 * cm, "AvalieImob")
        c.setFillColor(VERDE); c.setFont("Helvetica-Bold", 9)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.35 * cm, f"PROPOSTA Nº {numero}")
        c.setFillColor(CINZA); c.setFont("Helvetica", 7.5)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.7 * cm, _esc(subtipo_label))
        # rodapé: lockup + página
        c.setFillColor(VERDE); c.rect(0, 0, PAGE_W, 1.0 * cm, stroke=0, fill=1)
        try:
            from pdf.brand_seal import draw_header_lockup
            draw_header_lockup(c, MARGIN, 0.5 * cm, mark=0.8 * cm, light=True,
                               tagline="Romatec Consultoria Total")
        except Exception:
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 8)
            c.drawString(MARGIN, 0.38 * cm, "AvalieImob")
        c.setFillColor(colors.HexColor("#CFE0D5")); c.setFont("Helvetica", 7)
        c.drawCentredString(PAGE_W / 2, 0.38 * cm, f"Pág. {c.getPageNumber()}")
        c.drawRightString(PAGE_W - MARGIN, 0.38 * cm, _esc(numero))
        c.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_header_footer)])

    el = []
    el.append(Paragraph("Proposta de Consultoria", st["h1"]))
    el.append(Paragraph(_esc(subtipo_label), st["sub"]))

    # Cliente
    cli = [
        ("Cliente", proposta.get("cliente_nome")),
        ("CPF/CNPJ", proposta.get("cliente_cpf_cnpj")),
        ("Telefone", proposta.get("cliente_telefone")),
        ("Imóvel/Obra", proposta.get("endereco_imovel")),
    ]
    cli_rows = [[Paragraph(f"<b>{k}:</b>", st["cell"]), Paragraph(_esc(v or "—"), st["cell"])] for k, v in cli]
    tcli = Table(cli_rows, colWidths=[3.0 * cm, UTIL_W - 3.0 * cm])
    tcli.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    el.append(tcli)

    # 1 — Objeto / Escopo
    s1 = custos.get("secao_1_projetos") or []
    prog = (proposta.get("programa_necessidades")
            or (proposta.get("dados_imovel") or {}).get("programa_necessidades") or [])
    if s1 or prog:
        el.append(Paragraph("1. Objeto e Escopo dos Serviços", st["sec"]))
        for item in s1:
            el.append(Paragraph(f"• {_esc(item)}", st["li"]))
        if prog:
            prog = sorted(prog, key=lambda p: p.get("ordem_pdf", 999))
            partes = []
            for p in prog:
                q = int(p.get("quantidade") or 1)
                nome = p.get("nome_plural") if q > 1 else p.get("nome")
                partes.append(f"{q} {_esc(nome)}")
            el.append(Spacer(1, 4))
            el.append(Paragraph("<b>Programa de Necessidades</b> (cômodos da edificação): "
                                + "; ".join(partes) + ".", st["body"]))

    # 2 — Taxas de terceiros
    t2 = _tabela_itens(custos.get("secao_2_taxas"), st)
    if t2 is not None:
        el.append(Paragraph("2. Taxas e Emolumentos de Terceiros", st["sec"]))
        el.append(t2)

    # 3 — Honorários
    t3 = _tabela_itens(custos.get("secao_3_honorarios"), st)
    if t3 is not None:
        el.append(Paragraph("3. Honorários Técnicos (Romatec)", st["sec"]))
        el.append(t3)

    # Croqui do imóvel + alinhamento de cerca (demarcação com pontos) — §9 4.6/4.7
    el += _croqui_flowables(proposta, st)

    # Total
    total = custos.get("secao_5_total", 0)
    el.append(Spacer(1, 8))
    tot = Table([[Paragraph("<b>INVESTIMENTO TOTAL</b>", ParagraphStyle("tt", parent=st["cell"], textColor=colors.white, fontSize=11)),
                  Paragraph(f"<b>{_brl(total)}</b>", ParagraphStyle("tv", parent=st["cellr"], textColor=colors.white, fontSize=13))]],
                 colWidths=[UTIL_W - 5 * cm, 5 * cm])
    tot.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), VERDE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                             ("LEFTPADDING", (0, 0), (0, 0), 12), ("RIGHTPADDING", (-1, 0), (-1, 0), 12)]))
    el.append(tot)

    # Condições de pagamento
    cond = custos.get("condicoes_pagamento") or []
    if cond:
        el.append(Paragraph("4. Condições de Pagamento", st["sec"]))
        rows = [[Paragraph(_esc(p.get("rotulo", "")), st["cell"]),
                 Paragraph(_esc(p.get("descricao", "")), st["obs"]),
                 Paragraph(_brl(p.get("valor", 0)), st["cellr"])] for p in cond]
        tc = Table(rows, colWidths=[5.5 * cm, UTIL_W - 9.0 * cm, 3.5 * cm])
        tc.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDE5E0")),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        el.append(tc)

    # Serviços opcionais (georref) — informativos, à parte do total
    opc = (custos.get("secao_opcionais_georref") or {}).get("itens") or []
    opc = [o for o in opc if o.get("contratado")]
    if opc:
        el.append(Paragraph("Serviços Opcionais (à parte — não inclusos no total)", st["sec"]))
        rows = [[Paragraph(_esc(o.get("rotulo", "")), st["cell"]),
                 Paragraph(_brl(o.get("subtotal") or o.get("valor") or 0), st["cellr"])] for o in opc]
        to = Table(rows, colWidths=[UTIL_W - 3.2 * cm, 3.2 * cm])
        to.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDE5E0")),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        el.append(to)

    # Serviços opcionais (demarcação) — informativos, à parte do total
    opcd = (custos.get("secao_opcionais_demarcacao") or {}).get("linhas") or []
    opcd = [o for o in opcd if o.get("contratado")]
    if opcd:
        el.append(Paragraph("Serviços Opcionais (à parte — não inclusos no total)", st["sec"]))
        rows = [[Paragraph(_esc(o.get("rotulo", "")), st["cell"]),
                 Paragraph("Sob orçamento" if o.get("valor") == "sob_orcamento" else _brl(o.get("valor") or 0), st["cellr"])]
                for o in opcd]
        td = Table(rows, colWidths=[UTIL_W - 3.2 * cm, 3.2 * cm])
        td.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDE5E0")),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        el.append(td)

    # Despesas administrativas (desmembramento/remembramento) — à parte do total
    dadm = custos.get("despesas_administrativas")
    if dadm and (dadm.get("valor") or dadm.get("descritivo")):
        el.append(Paragraph("Despesas Administrativas (à parte — não inclusas no total)", st["sec"]))
        td = Table([[Paragraph(_esc(dadm.get("descritivo") or "Despesas administrativas"), st["cell"]),
                     Paragraph(_brl(dadm.get("valor") or 0), st["cellr"])]],
                   colWidths=[UTIL_W - 3.2 * cm, 3.2 * cm])
        td.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDE5E0")),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        el.append(td)

    # 5 — Documentação (checklist)
    chk = custos.get("secao_4_checklist") or []
    if chk:
        el.append(Paragraph("5. Documentação Necessária", st["sec"]))
        for it in chk:
            marca = "◆" if it.get("imprescindivel") else ("•" if it.get("obrigatorio") else "○")
            el.append(Paragraph(f"{marca} {_esc(it.get('texto', ''))}", st["li"]))

    # Observações do usuário (prazos / condições especiais)
    obs_user = str(proposta.get("observacoes") or "").strip()
    if obs_user:
        el.append(Paragraph("Observações", st["sec"]))
        for linha in obs_user.split("\n"):
            if linha.strip():
                el.append(Paragraph(_esc(linha), st["aviso"]))

    # Avisos
    avisos = custos.get("avisos") or []
    if avisos:
        el.append(Paragraph("Base Legal e Avisos", st["sec"]))
        for a in avisos:
            el.append(Paragraph(_esc(a), st["aviso"]))

    # Validade
    el.append(Spacer(1, 8))
    el.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDE5E0")))
    el.append(Paragraph(
        f"Proposta válida por {proposta.get('validade_dias', 15)} dias a partir da emissão. "
        f"Valores sujeitos a confirmação após vistoria/análise documental.", st["aviso"]))

    el += _anexo_flowables(anexos_bytes, st)

    doc.build(el)
    return buf.getvalue()
