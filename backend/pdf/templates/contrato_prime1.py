# @module pdf.templates.contrato_prime1 — Renderer PRIME I (editorial preto × verde).
# Assinatura: render(doc, uid, empresa) -> bytes. Capa split diagonal, filete dourado,
# seções com rótulo "SEÇÃO 0N" (sem ghost), banda verde de total, footer faixa preta.
import io
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Flowable, PageBreak, KeepTogether, NextPageTemplate,
)

from pdf.themes import prime1 as P1
from pdf.themes import prime2_theme as T
from pdf.templates.contrato_prime2 import (
    _parte_nome, _parte_doc, _parte_endereco, _endereco_full, _money, _extenso,
    _quebra_titulo, _bloco_assinaturas,
)

logger = logging.getLogger("romatec")
PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm


def _styles():
    f = T.fonts()
    return {
        "corpo": ParagraphStyle("p1_corpo", fontName=f["sans"], fontSize=10, leading=15,
                                alignment=TA_JUSTIFY, textColor=T.C_CINZA_TEXTO, spaceAfter=6),
        "clausula_tit": ParagraphStyle("p1_ctit", fontName=f["sans_bold"], fontSize=11, leading=14,
                                       textColor=P1.C_PRETO, spaceBefore=10, spaceAfter=3),
        "sec_label": ParagraphStyle("p1_seclbl", fontName=f["sans_bold"], fontSize=8, leading=12,
                                    textColor=T.C_DOURADO),
        "sec_titulo": ParagraphStyle("p1_sec", fontName=f["serif_bold"], fontSize=22, leading=24,
                                     textColor=P1.C_PRETO),
        "item": ParagraphStyle("p1_item", fontName=f["sans"], fontSize=9.5, leading=13,
                               textColor=T.C_CINZA_TEXTO),
        "assina_nome": ParagraphStyle("p1_anome", fontName=f["sans_bold"], fontSize=10, leading=13,
                                      alignment=TA_LEFT, textColor=P1.C_PRETO),
        "assina_cred": ParagraphStyle("p1_acred", fontName=f["sans"], fontSize=8, leading=11,
                                      textColor=T.C_CINZA_TEXTO),
    }


class SecaoHeaderP1(Flowable):
    """Rótulo 'S E Ç Ã O  0N' dourado caps + título serif preto (sem numeral ghost)."""
    def __init__(self, numero, titulo, width=None):
        super().__init__()
        self.numero = numero
        self.titulo = titulo
        self._w = width

    def wrap(self, availWidth, availHeight):
        self.width = self._w or availWidth
        self.height = 1.4 * cm
        return self.width, self.height

    def draw(self):
        c = self.canv
        f = T.fonts()
        c.setFillColor(T.C_DOURADO)
        c.setFont(f["sans_bold"], 8)
        c.drawString(0, 1.0 * cm, T.tracking(f"SEÇÃO {self.numero}"))
        c.setFillColor(P1.C_PRETO)
        c.setFont(f["serif_bold"], 22)
        c.drawString(0, 0.2 * cm, self.titulo)


class BandaVerde(Flowable):
    """Faixa verde full-width: microlabel dourado + valor serif branco + extenso itálico."""
    def __init__(self, label, valor, extenso, width=None):
        super().__init__()
        self.label = label
        self.valor = valor
        self.extenso = extenso
        self._w = width

    def wrap(self, availWidth, availHeight):
        self.width = self._w or availWidth
        self.height = 2.4 * cm
        return self.width, self.height

    def draw(self):
        c = self.canv
        f = T.fonts()
        c.setFillColor(T.C_VERDE_ESCURO)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(T.C_DOURADO)
        c.setFont(f["sans"], 8)
        c.drawString(0.7 * cm, self.height - 0.7 * cm, T.tracking(self.label))
        c.setFillColor(T.C_BRANCO)
        c.setFont(f["serif_bold"], 26)
        c.drawString(0.7 * cm, 0.75 * cm, self.valor)
        if self.extenso:
            c.setFillColor(T.C_CINZA_GHOST)
            c.setFont(f["serif_italic"], 9)
            c.drawString(0.7 * cm, 0.32 * cm, self.extenso)


def _draw_capa(c, meta):
    f = T.fonts()
    c.saveState()
    # painel direito verde (fundo todo) + filete dourado no topo
    c.setFillColor(T.C_VERDE_ESCURO)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(T.C_DOURADO)
    c.rect(0, PAGE_H - 0.18 * cm, PAGE_W, 0.18 * cm, fill=1, stroke=0)
    # painel esquerdo PRETO com corte diagonal (~56%)
    split = 0.56 * PAGE_W
    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(split - 1.4 * cm, 0)
    p.lineTo(split + 1.4 * cm, PAGE_H)
    p.lineTo(0, PAGE_H)
    p.close()
    c.setFillColor(P1.C_PRETO)
    c.drawPath(p, fill=1, stroke=0)

    # ── painel esquerdo (preto): marca + título ──
    try:
        from pdf.brand_seal import draw_header_lockup
        draw_header_lockup(c, MARGIN, PAGE_H - 2.2 * cm, mark=1.0 * cm, light=True,
                           tagline="Romatec Consultoria Total")
    except Exception:
        c.setFillColor(T.C_BRANCO)
        c.setFont(f["serif_bold"], 15)
        c.drawString(MARGIN, PAGE_H - 2.4 * cm, "Romatec Consultoria Total")
    c.setFillColor(T.C_DOURADO)
    c.setFont(f["sans_bold"], 8)
    c.drawString(MARGIN, PAGE_H - 7.0 * cm, T.tracking("INSTRUMENTO PARTICULAR"))
    c.setFillColor(T.C_BRANCO)
    c.setFont(f["serif_bold"], 30)
    y = PAGE_H - 8.2 * cm
    for linha in meta["titulo_linhas"]:
        c.drawString(MARGIN, y, linha)
        y -= 1.05 * cm
    if meta.get("subtitulo"):
        c.setFillColor(T.C_CINZA_GHOST)
        c.setFont(f["sans"], 9)
        c.drawString(MARGIN, y - 0.2 * cm, meta["subtitulo"])
    # rodapé esquerdo: emissão
    c.setFillColor(T.C_CINZA_GHOST)
    c.setFont(f["sans"], 8)
    c.drawString(MARGIN, 2.0 * cm, meta.get("emissao", ""))

    # ── painel direito (verde): código + contratante ──
    rx = split + 2.0 * cm
    c.setFillColor(T.C_DOURADO)
    c.setFont(f["sans_bold"], 8)
    c.drawString(rx, PAGE_H - 6.5 * cm, T.tracking("CONTRATO N."))
    c.setFillColor(T.C_DOURADO)
    c.setFont(f["serif_bold"], 30)
    for i, parte in enumerate(meta["codigo_linhas"]):
        c.drawString(rx, PAGE_H - 7.6 * cm - i * 1.0 * cm, parte)
    # card contratante (translúcido = verde mais claro)
    cy = 7.5 * cm
    c.setFillColor(P1.C_VERDE_GRAD_TOP)
    c.roundRect(rx, cy - 2.6 * cm, PAGE_W - MARGIN - rx, 3.0 * cm, 6, fill=1, stroke=0)
    c.setFillColor(T.C_DOURADO)
    c.setFont(f["sans"], 7)
    c.drawString(rx + 0.4 * cm, cy + 0.1 * cm, T.tracking("CONTRATANTE"))
    c.setFillColor(T.C_BRANCO)
    c.setFont(f["sans_bold"], 12)
    c.drawString(rx + 0.4 * cm, cy - 0.5 * cm, (meta["contratante_nome"] or "—")[:28])
    c.setFont(f["sans"], 8)
    if meta.get("contratante_doc"):
        c.drawString(rx + 0.4 * cm, cy - 1.05 * cm, f"CPF/CNPJ: {meta['contratante_doc']}")
    if meta.get("contratante_end"):
        c.drawString(rx + 0.4 * cm, cy - 1.5 * cm, meta["contratante_end"][:34])
    c.restoreState()


def _draw_footer(c, meta):
    f = T.fonts()
    c.saveState()
    c.setFillColor(P1.C_PRETO)
    c.rect(0, 0, PAGE_W, 1.15 * cm, fill=1, stroke=0)
    c.setFillColor(T.C_CINZA_GHOST)
    c.setFont(f["sans"], 7)
    c.drawString(MARGIN, 0.42 * cm, meta.get("email", "romateccrm@gmail.com"))
    c.setFillColor(T.C_DOURADO)
    c.setFont(f["mono"], 7)
    c.drawRightString(PAGE_W - MARGIN, 0.42 * cm, meta["codigo"])
    c.setFillColor(T.C_CINZA_GHOST)
    c.setFont(f["sans"], 7)
    c.drawCentredString(PAGE_W / 2, 0.42 * cm, f"Pág. {c.getPageNumber()}")
    c.restoreState()


def render(doc: dict, uid: str, empresa: str) -> bytes:
    T.registrar_fontes()
    st = _styles()

    from pdf.templates.contrato_base import codigo_contrato, _norm_matricula
    codigo = codigo_contrato(doc)   # exclusividade → CONT_EXCLUSIV-AAAA-NNNN; demais → CONT-...
    tipo = (doc.get("tipo_contrato") or "Contrato").replace("_", " ").title()

    vendedores = doc.get("vendedores") or []
    compradores = doc.get("compradores") or []
    contratante = vendedores[0] if vendedores else (compradores[0] if compradores else {})
    objeto = doc.get("objeto") or {}
    pagamento = doc.get("pagamento") or {}
    corretor = doc.get("corretor") or {}
    clausulas = doc.get("clausulas") or []

    # código quebrado em linhas (ex.: 'CONT-2026', '0007-R1')
    cod_partes = codigo.split("-")
    codigo_linhas = ["-".join(cod_partes[:2])] if len(cod_partes) >= 2 else [codigo]
    if len(cod_partes) > 2:
        codigo_linhas.append("-".join(cod_partes[2:]))

    meta = {
        "codigo": codigo,
        "codigo_linhas": codigo_linhas,
        "titulo_linhas": _quebra_titulo(tipo),
        "subtitulo": "Lei 6.530/78 · CC arts. 722-729" if "exclusiv" in (doc.get("tipo_contrato") or "").lower() else "",
        "contratante_nome": _parte_nome(contratante),
        "contratante_doc": _parte_doc(contratante),
        "contratante_end": _parte_endereco(contratante),
        "emissao": f"Emitido em {(doc.get('data_assinatura') or '').strip() or '___/___/______'}",
        "email": "romateccrm@gmail.com",
    }

    buf = io.BytesIO()
    from pdf.templates.resilient import ResilientBaseDocTemplate
    pdf = ResilientBaseDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                                   topMargin=2.4 * cm, bottomMargin=1.9 * cm, title=f"Contrato {codigo}")
    frame = Frame(MARGIN, 1.9 * cm, PAGE_W - 2 * MARGIN, PAGE_H - 4.3 * cm, id="corpo")
    pdf.addPageTemplates([
        PageTemplate(id="capa", frames=[frame], onPage=lambda c, d: _draw_capa(c, meta)),
        PageTemplate(id="interna", frames=[frame], onPage=lambda c, d: _draw_footer(c, meta)),
    ])

    cw = PAGE_W - 2 * MARGIN
    story = [NextPageTemplate("interna"), PageBreak()]

    # Preâmbulo (qualificação das partes) — somente exclusividade
    if "exclusiv" in (doc.get("tipo_contrato") or "").lower():
        from pdf.templates.contrato_base import preambulo_exclusividade
        for par in preambulo_exclusividade(doc):
            story.append(Paragraph(par, st["corpo"]))
        story.append(Spacer(1, 8))

    # 01 Objeto
    story.append(SecaoHeaderP1("01", "Objeto & Imóvel", width=cw))
    story.append(Spacer(1, 4))
    end_imovel = _endereco_full(objeto) or objeto.get("endereco") or "—"
    desc = end_imovel if end_imovel != "—" else (objeto.get("descricao") or "Imóvel a especificar.")
    serventia = objeto.get("registro_imovel") or objeto.get("cartorio") or objeto.get("serventia") or "—"
    cns = objeto.get("cns") or objeto.get("cartorio_cns") or objeto.get("serventia_cns") or ""
    story.append(Paragraph(f"◆ Endereço: {end_imovel}", st["item"]))
    story.append(Paragraph(f"◆ Matrícula: {_norm_matricula(objeto.get('matricula')) or '—'} · Município/UF: {objeto.get('cidade','—') or '—'}/{objeto.get('uf','—') or '—'}", st["item"]))
    story.append(Paragraph(f"◆ Serventia / Cartório: {serventia}" + (f" · CNS {cns}" if cns else ""), st["item"]))
    lat, lon = objeto.get("latitude"), objeto.get("longitude")
    if lat not in (None, "") and lon not in (None, ""):
        story.append(Paragraph(f"◆ Coordenadas (SIRGAS 2000): {lat}, {lon}", st["item"]))
    from pdf.templates.contrato_prime2 import _mapa_flowable
    _mapa = _mapa_flowable(lat, lon, cw)
    if _mapa is not None:
        story.append(Spacer(1, 6))
        story.append(_mapa)
    story.append(Spacer(1, 12))

    # 02 Condições
    story.append(SecaoHeaderP1("02", "Condições Comerciais", width=cw))
    story.append(Spacer(1, 4))
    valor_total = pagamento.get("valor_total") or 0
    story.append(BandaVerde("Preço anunciado do imóvel", _money(valor_total), _extenso(valor_total), width=cw))
    story.append(Spacer(1, 12))

    # 03 Cláusulas (conteúdo neutro do contrato_base — canônico p/ exclusividade)
    from pdf.templates.contrato_base import montar_clausulas, fecho_exclusividade
    story.append(SecaoHeaderP1("03", "Cláusulas Contratuais", width=cw))
    story.append(Spacer(1, 4))
    cls = montar_clausulas(doc)
    if cls:
        for cl in cls:
            story.append(Paragraph(cl.titulo.upper(), st["clausula_tit"]))
            for item in cl.itens:
                story.append(Paragraph(item, st["corpo"]))
    else:
        story.append(Paragraph("As cláusulas serão geradas na etapa de cláusulas do contrato.", st["corpo"]))
    story.append(Spacer(1, 12))

    # 04 Comissão
    pct = corretor.get("comissao_percentual")
    if pct:
        try:
            comissao_val = float(valor_total) * float(pct) / 100.0
        except Exception:
            comissao_val = 0
        story.append(SecaoHeaderP1("04", "Comissão", width=cw))
        story.append(Spacer(1, 4))
        story.append(BandaVerde(f"Comissão estimada ({pct}%)", _money(comissao_val), _extenso(comissao_val), width=cw))
        story.append(Spacer(1, 12))

    # 05 Prazo
    story.append(SecaoHeaderP1("05", "Prazo & Vigência", width=cw))
    story.append(Spacer(1, 4))
    prazo = corretor.get("prazo_exclusividade") or doc.get("prazo_vigencia_dias")
    txt_prazo = f"{prazo}" if prazo else "INDETERMINADO (com aviso prévio conforme cláusula própria)"
    story.append(Paragraph(f"Prazo de exclusividade/vigência: <b>{txt_prazo}</b>.", st["corpo"]))
    story.append(Spacer(1, 12))

    # Fecho (exclusividade)
    if "exclusiv" in (doc.get("tipo_contrato") or "").lower():
        story.append(Paragraph(fecho_exclusividade(doc), st["corpo"]))
        story.append(Spacer(1, 8))

    # 06 Assinaturas + 07 Testemunhas — mantidos JUNTOS na MESMA página
    # (KeepTogether no nível do story; se não couber, o bloco inteiro desce junto).
    from pdf.templates.contrato_base import testemunhas_de, testemunha_linha
    bloco_fim = [
        SecaoHeaderP1("06", "Assinaturas", width=cw),
        Spacer(1, 16),
        *_bloco_assinaturas(contratante, st, cw),
    ]
    _tests = testemunhas_de(doc)
    if _tests:
        bloco_fim += [Spacer(1, 14), SecaoHeaderP1("07", "Testemunhas", width=cw), Spacer(1, 6)]
        for _t in _tests:
            bloco_fim.append(Paragraph(testemunha_linha(_t), st["corpo"]))
            bloco_fim.append(Spacer(1, 4))
    story.append(KeepTogether(bloco_fim))

    # Anexos do imóvel (fotos + documentos) — exclusividade
    try:
        from pdf.templates.anexos_imovel import anexos_imovel_flowables
        story.extend(anexos_imovel_flowables(objeto))
    except Exception:
        pass

    # Anexos do CORRETOR — Cartão + Certidão de Regularidade (CRECI), bloco separado
    # dos documentos do imóvel/cliente (que são ANEXO III/IV).
    try:
        from services.cartao_regularidade import anexos_regularidade_flowables
        story.extend(anexos_regularidade_flowables(
            doc.get("_avaliador") or {}, cw,
            titulo_cartao="ANEXO V — CARTÃO DE REGULARIDADE DO CORRETOR (CRECI)",
            titulo_certidao="ANEXO VI — CERTIDÃO DE REGULARIDADE DO CORRETOR (CRECI)"))
    except Exception:
        pass

    pdf.build(story)
    return buf.getvalue()
