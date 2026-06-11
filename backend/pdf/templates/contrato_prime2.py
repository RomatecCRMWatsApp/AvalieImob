# @module pdf.templates.contrato_prime2 — Renderer PRIME II do contrato.
# Assinatura: render(doc: dict, uid: str, empresa: str) -> bytes (PDF síncrono).
# Capa verde integral, numerais ghost, banda dourada de valor, cards borda dourada,
# cláusulas justificadas, bloco de assinaturas e footer banda. Cores/fontes só via theme.
import io
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Flowable, PageBreak, KeepTogether, NextPageTemplate,
)

from pdf.themes import prime2_theme as T

logger = logging.getLogger("romatec")

PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm


# ── Helpers de dados ──────────────────────────────────────────────────────────
def _parte_nome(p: dict) -> str:
    if not isinstance(p, dict):
        return ""
    pf = p.get("pf") or {}
    pj = p.get("pj") or {}
    return (p.get("nome") or pf.get("nome") or pj.get("razao_social")
            or p.get("razao_social") or "").strip()


def _parte_doc(p: dict) -> str:
    pf = (p or {}).get("pf") or {}
    pj = (p or {}).get("pj") or {}
    return (p.get("cpf") or p.get("doc") or pf.get("cpf") or pj.get("cnpj") or "").strip()


def _parte_endereco(p: dict) -> str:
    pf = (p or {}).get("pf") or {}
    pj = (p or {}).get("pj") or {}
    return (p.get("endereco") or pf.get("endereco") or pj.get("endereco") or "").strip()


def _money(v) -> str:
    try:
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _extenso(v) -> str:
    try:
        from routes.contratos import _extenso as ext
        return ext(v)
    except Exception:
        return ""


# ── Estilos ───────────────────────────────────────────────────────────────────
def _styles():
    f = T.fonts()
    return {
        "corpo": ParagraphStyle(
            "p2_corpo", fontName=f["sans"], fontSize=10, leading=15,
            alignment=TA_JUSTIFY, textColor=T.C_TEXTO, spaceAfter=6),
        "clausula_tit": ParagraphStyle(
            "p2_ctit", fontName=f["sans_bold"], fontSize=11, leading=14,
            textColor=T.C_VERDE_ESCURO, spaceBefore=10, spaceAfter=3),
        "sec_titulo": ParagraphStyle(
            "p2_sec", fontName=f["serif_bold"], fontSize=22, leading=24,
            textColor=T.C_VERDE_ESCURO),
        "ghost": ParagraphStyle(
            "p2_ghost", fontName=f["serif_bold"], fontSize=58, leading=58,
            textColor=T.C_CINZA_GHOST, alignment=TA_RIGHT),
        "card_tit": ParagraphStyle(
            "p2_card_tit", fontName=f["mono"], fontSize=8, leading=12,
            textColor=T.C_DOURADO),
        "card_corpo": ParagraphStyle(
            "p2_card_corpo", fontName=f["sans"], fontSize=9.5, leading=13,
            textColor=T.C_BRANCO),
        "micro": ParagraphStyle(
            "p2_micro", fontName=f["sans"], fontSize=8, leading=11,
            textColor=T.C_CINZA_TEXTO),
        "assina_nome": ParagraphStyle(
            "p2_anome", fontName=f["sans_bold"], fontSize=10, leading=13,
            alignment=TA_LEFT, textColor=T.C_TEXTO),
        "assina_cred": ParagraphStyle(
            "p2_acred", fontName=f["sans"], fontSize=8, leading=11,
            textColor=T.C_CINZA_TEXTO),
    }


# ── Flowables custom ──────────────────────────────────────────────────────────
class SecaoHeader(Flowable):
    """Cabeçalho de seção: título serif + palavra itálica + numeral ghost à direita."""
    def __init__(self, numero, titulo, palavra_italica=None, width=None):
        super().__init__()
        self.numero = numero
        self.titulo = titulo
        self.palavra = palavra_italica
        self._w = width

    def wrap(self, availWidth, availHeight):
        self.width = self._w or availWidth
        self.height = 1.5 * cm
        return self.width, self.height

    def draw(self):
        c = self.canv
        f = T.fonts()
        # numeral ghost
        c.setFillColor(T.C_CINZA_GHOST)
        c.setFont(f["serif_bold"], 56)
        c.drawRightString(self.width, 0.15 * cm, str(self.numero))
        # título
        c.setFillColor(T.C_VERDE_ESCURO)
        c.setFont(f["serif_bold"], 22)
        c.drawString(0, 0.55 * cm, self.titulo)
        if self.palavra:
            larg = c.stringWidth(self.titulo + " ", f["serif_bold"], 22)
            c.setFillColor(T.C_VERDE_MEDIO)
            c.setFont(f["serif_italic"], 22)
            c.drawString(larg, 0.55 * cm, self.palavra)
        # filete dourado
        c.setStrokeColor(T.C_DOURADO)
        c.setLineWidth(1)
        c.line(0, 0.30 * cm, self.width, 0.30 * cm)


class BandaTotal(Flowable):
    """Retângulo dourado arredondado: microlabel + valor serif branco + extenso."""
    def __init__(self, label, valor, extenso, width=None):
        super().__init__()
        self.label = label
        self.valor = valor
        self.extenso = extenso
        self._w = width

    def wrap(self, availWidth, availHeight):
        self.width = self._w or availWidth
        self.height = 2.6 * cm
        return self.width, self.height

    def draw(self):
        c = self.canv
        f = T.fonts()
        c.setFillColor(T.C_DOURADO)
        c.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=0)
        c.setFillColor(T.C_BRANCO)
        c.setFont(f["sans"], 8)
        c.drawString(0.7 * cm, self.height - 0.75 * cm, T.tracking(self.label))
        c.setFont(f["serif_bold"], 28)
        c.drawString(0.7 * cm, 0.85 * cm, self.valor)
        if self.extenso:
            c.setFont(f["serif_italic"], 9)
            c.drawString(0.7 * cm, 0.35 * cm, self.extenso)


def _card_borda_dourada(titulo, linhas, styles, largura):
    """Card fundo verde-escuro, borda dourada, título mono dourado, corpo branco."""
    corpo = "<br/>".join(linhas)
    inner = [
        [Paragraph(T.tracking(titulo), styles["card_tit"])],
        [Paragraph(corpo, styles["card_corpo"])],
    ]
    t = Table(inner, colWidths=[largura])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), T.C_VERDE_ESCURO),
        ("BOX", (0, 0), (-1, -1), 1, T.C_DOURADO),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


# ── Capa e footer (canvas) ────────────────────────────────────────────────────
def _draw_capa(c, meta):
    f = T.fonts()
    c.saveState()
    # fundo verde integral
    c.setFillColor(T.C_VERDE_ESCURO)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # marca topo-esquerda
    c.setFillColor(T.C_BRANCO)
    c.setFont(f["serif_bold"], 16)
    c.drawString(MARGIN, PAGE_H - 2.2 * cm, "Romatec")
    c.setFillColor(T.C_DOURADO)
    c.setFont(f["serif_italic"], 16)
    c.drawString(MARGIN + c.stringWidth("Romatec ", f["serif_bold"], 16),
                 PAGE_H - 2.2 * cm, "Consultoria Total")
    # pill dourada com código
    codigo = meta["codigo"]
    c.setFont(f["mono"], 9)
    pill_w = c.stringWidth(codigo, f["mono"], 9) + 0.9 * cm
    c.setFillColor(T.C_DOURADO)
    c.roundRect(MARGIN, PAGE_H - 3.6 * cm, pill_w, 0.7 * cm, 6, fill=1, stroke=0)
    c.setFillColor(T.C_VERDE_ESCURO)
    c.drawString(MARGIN + 0.45 * cm, PAGE_H - 3.4 * cm, codigo)
    # título do documento (serif branca, 2 linhas)
    c.setFillColor(T.C_BRANCO)
    c.setFont(f["serif_bold"], 32)
    y = PAGE_H - 8.0 * cm
    for linha in meta["titulo_linhas"]:
        c.drawString(MARGIN, y, linha)
        y -= 1.15 * cm
    # subtítulo / base legal
    if meta.get("subtitulo"):
        c.setFillColor(T.C_DOURADO)
        c.setFont(f["sans"], 9)
        c.drawString(MARGIN, y - 0.3 * cm, meta["subtitulo"])
    # bloco contratante
    cy = 6.5 * cm
    c.setFillColor(T.C_DOURADO)
    c.setFont(f["sans"], 8)
    c.drawString(MARGIN, cy, T.tracking("CONTRATANTE"))
    c.setFillColor(T.C_BRANCO)
    c.setFont(f["sans_bold"], 13)
    c.drawString(MARGIN, cy - 0.65 * cm, meta["contratante_nome"] or "—")
    c.setFont(f["sans"], 9)
    if meta.get("contratante_doc"):
        c.drawString(MARGIN, cy - 1.15 * cm, f"CPF/CNPJ: {meta['contratante_doc']}")
    if meta.get("contratante_end"):
        c.drawString(MARGIN, cy - 1.6 * cm, meta["contratante_end"][:90])
    # rodapé capa: emissão / validade
    c.setStrokeColor(T.C_DOURADO)
    c.setLineWidth(0.5)
    c.line(MARGIN, 2.6 * cm, PAGE_W - MARGIN, 2.6 * cm)
    c.setFillColor(T.C_CINZA_GHOST)
    c.setFont(f["sans"], 8)
    c.drawString(MARGIN, 2.1 * cm, meta.get("emissao", ""))
    if meta.get("validade"):
        c.drawRightString(PAGE_W - MARGIN, 2.1 * cm, meta["validade"])
    c.restoreState()


def _draw_footer(c, meta):
    f = T.fonts()
    c.saveState()
    c.setFillColor(T.C_VERDE_ESCURO)
    c.rect(0, 0, PAGE_W, 1.2 * cm, fill=1, stroke=0)
    c.setFillColor(T.C_BRANCO)
    c.setFont(f["serif_bold"], 9)
    c.drawString(MARGIN, 0.45 * cm, "Romatec")
    c.setFillColor(T.C_DOURADO)
    c.setFont(f["serif_italic"], 9)
    c.drawString(MARGIN + c.stringWidth("Romatec ", f["serif_bold"], 9),
                 0.45 * cm, "Consultoria Total")
    c.setFillColor(T.C_CINZA_GHOST)
    c.setFont(f["mono"], 7)
    c.drawRightString(PAGE_W - MARGIN, 0.45 * cm, meta["codigo"])
    c.setFont(f["sans"], 7)
    c.drawCentredString(PAGE_W / 2, 0.45 * cm, f"Pág. {c.getPageNumber()}")
    c.restoreState()


# ── Render principal ──────────────────────────────────────────────────────────
def render(doc: dict, uid: str, empresa: str) -> bytes:
    T.registrar_fontes()
    st = _styles()

    numero = (doc.get("numero_contrato") or doc.get("numero") or "").strip()
    codigo = numero.replace("CV-", "CONT-") if numero else "CONT-2026"
    tipo = (doc.get("tipo_contrato") or "Contrato").replace("_", " ").title()

    vendedores = doc.get("vendedores") or []
    compradores = doc.get("compradores") or []
    contratante = vendedores[0] if vendedores else (compradores[0] if compradores else {})
    objeto = doc.get("objeto") or {}
    pagamento = doc.get("pagamento") or {}
    corretor = doc.get("corretor") or {}
    clausulas = doc.get("clausulas") or []

    meta = {
        "codigo": codigo,
        "titulo_linhas": _quebra_titulo(tipo),
        "subtitulo": "Lei 6.530/78 · CC arts. 722-729 (corretagem)" if "exclusiv" in (doc.get("tipo_contrato") or "").lower() else "",
        "contratante_nome": _parte_nome(contratante),
        "contratante_doc": _parte_doc(contratante),
        "contratante_end": _parte_endereco(contratante),
        "emissao": f"Emitido em {(doc.get('data_assinatura') or '').strip() or '___/___/______'} · {(doc.get('cidade_assinatura') or 'Açailândia/MA')}",
        "validade": "",
    }

    buf = io.BytesIO()
    pdf = BaseDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.4 * cm, bottomMargin=2.0 * cm, title=f"Contrato {codigo}",
    )
    frame = Frame(MARGIN, 2.0 * cm, PAGE_W - 2 * MARGIN, PAGE_H - 4.4 * cm, id="corpo")
    pdf.addPageTemplates([
        PageTemplate(id="capa", frames=[frame], onPage=lambda c, d: _draw_capa(c, meta)),
        PageTemplate(id="interna", frames=[frame], onPage=lambda c, d: _draw_footer(c, meta)),
    ])

    # página 1 = capa (desenhada no onPage da template 'capa'); a partir da 2 usa 'interna'
    story = [NextPageTemplate("interna"), PageBreak()]

    cw = PAGE_W - 2 * MARGIN

    # Preâmbulo (qualificação das partes) — somente exclusividade
    if "exclusiv" in (doc.get("tipo_contrato") or "").lower():
        from pdf.templates.contrato_base import preambulo_exclusividade
        for par in preambulo_exclusividade(doc):
            story.append(Paragraph(par, st["corpo"]))
        story.append(Spacer(1, 10))

    # 01 Objeto & Imóvel
    story.append(SecaoHeader("01", "Objeto &", "Imóvel", width=cw))
    story.append(Spacer(1, 6))
    desc = objeto.get("endereco") or objeto.get("descricao") or "Imóvel a especificar."
    linhas_obj = [
        f"Endereço: {objeto.get('endereco','—')}",
        f"Matrícula: {objeto.get('matricula','—')} · Cartório: {objeto.get('cartorio','—')}",
        f"Município/UF: {objeto.get('cidade','—')}/{objeto.get('uf','—')}",
    ]
    story.append(Paragraph(f"O presente instrumento tem por objeto o imóvel adiante descrito: {desc}.", st["corpo"]))
    story.append(_card_borda_dourada("DADOS DO IMÓVEL", linhas_obj, st, cw))
    story.append(Spacer(1, 14))

    # 02 Condições Comerciais
    story.append(SecaoHeader("02", "Condições", "Comerciais", width=cw))
    story.append(Spacer(1, 6))
    valor_total = pagamento.get("valor_total") or 0
    story.append(BandaTotal("Preço anunciado do imóvel", _money(valor_total), _extenso(valor_total), width=cw))
    story.append(Spacer(1, 14))

    # 03 Cláusulas (conteúdo neutro vindo do contrato_base — canônico p/ exclusividade)
    from pdf.templates.contrato_base import montar_clausulas, fecho_exclusividade
    story.append(SecaoHeader("03", "Cláusulas", "Contratuais", width=cw))
    story.append(Spacer(1, 6))
    cls = montar_clausulas(doc)
    if cls:
        for cl in cls:
            story.append(Paragraph(cl.titulo.upper(), st["clausula_tit"]))
            for item in cl.itens:
                story.append(Paragraph(item, st["corpo"]))
    else:
        story.append(Paragraph("As cláusulas contratuais serão geradas na etapa de cláusulas do contrato.", st["corpo"]))
    story.append(Spacer(1, 14))

    # 04 Comissão
    pct = corretor.get("comissao_percentual")
    if pct:
        try:
            comissao_val = float(valor_total) * float(pct) / 100.0
        except Exception:
            comissao_val = 0
        story.append(SecaoHeader("04", "Comissão", None, width=cw))
        story.append(Spacer(1, 6))
        story.append(BandaTotal(f"Comissão estimada ({pct}%)", _money(comissao_val), _extenso(comissao_val), width=cw))
        story.append(Spacer(1, 14))

    # 05 Prazo & Vigência
    story.append(SecaoHeader("05", "Prazo &", "Vigência", width=cw))
    story.append(Spacer(1, 6))
    prazo = corretor.get("prazo_exclusividade") or doc.get("prazo_vigencia_dias")
    txt_prazo = f"{prazo}" if prazo else "INDETERMINADO (com aviso prévio conforme cláusula própria)"
    story.append(Paragraph(f"Prazo de exclusividade/vigência: <b>{txt_prazo}</b>.", st["corpo"]))
    story.append(Spacer(1, 14))

    # Fecho (exclusividade)
    if "exclusiv" in (doc.get("tipo_contrato") or "").lower():
        story.append(Paragraph(fecho_exclusividade(doc), st["corpo"]))
        story.append(Spacer(1, 10))

    # 06 Assinaturas
    story.append(SecaoHeader("06", "Assinaturas", None, width=cw))
    story.append(Spacer(1, 18))
    story.append(KeepTogether(_bloco_assinaturas(contratante, st, cw)))

    # BaseDocTemplate desenha via onPage das PageTemplates (não aceita onFirstPage)
    pdf.build(story)
    return buf.getvalue()


def _quebra_titulo(tipo: str):
    palavras = tipo.split()
    if len(palavras) <= 2:
        return [tipo]
    meio = len(palavras) // 2
    return [" ".join(palavras[:meio]), " ".join(palavras[meio:])]


def _bloco_assinaturas(contratante, st, cw):
    col = (cw - 0.8 * cm) / 2
    linha = "_" * 34
    cred_romatec = ("Romatec Consultoria Total<br/>"
                    "Técnico em Agrimensura · Avaliador CNAI 031161<br/>"
                    "CRECI/MA 4.705 · CFT/MA 01209185369 (INCRA: FQNS)")
    esq = [
        Paragraph(linha, st["assina_nome"]),
        Paragraph(_parte_nome(contratante) or "Contratante", st["assina_nome"]),
        Paragraph("Contratante", st["assina_cred"]),
    ]
    dir_ = [
        Paragraph(linha, st["assina_nome"]),
        Paragraph("José Romário", st["assina_nome"]),
        Paragraph(cred_romatec, st["assina_cred"]),
    ]
    t = Table([[esq, dir_]], colWidths=[col, col])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("LINEBEFORE", (1, 0), (1, 0), 0.5, T.C_DOURADO),
    ]))
    return [t]
