# @module services.ptam_pdf_v2 — Gerador de PDF do PTAM (spec 1.0, NBR 14653 + COFECI 1.066/2007)
# Implementacao literal ao prompt master. Acesso defensivo (.get) em todos os campos:
# campo ausente -> placeholder, nunca lanca excecao. Imagens que falham -> placeholder.
# Usado por rota paralela /ptam/{id}/pdf-v2 (nao substitui o gerador atual ate validacao).
from io import BytesIO
import logging
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Flowable, HRFlowable,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.utils import ImageReader

logger = logging.getLogger("romatec")

# ── Cores ─────────────────────────────────────────────────────────────────────
VERDE = HexColor('#0B6E4F')
VERDE_CLARO = HexColor('#E8F5F0')
DOURADO = HexColor('#B8860B')
CINZA = HexColor('#666666')
CINZA_CLARO = HexColor('#EEEEEE')
CINZA_BRD = HexColor('#CCCCCC')
PRETO = HexColor('#1A1A1A')
BRANCO = colors.white

# ── Pagina / margens ──────────────────────────────────────────────────────────
MARGIN_L = 2.5 * cm
MARGIN_R = 2.0 * cm
MARGIN_T = 3.2 * cm
MARGIN_B = 2.8 * cm
UTIL_W = A4[0] - MARGIN_L - MARGIN_R   # ~13.5cm
UTIL_H = A4[1] - MARGIN_T - MARGIN_B   # ~23.0cm

EMPRESA_NOME = "ROMATEC CONSULTORIA TOTAL"
EMPRESA_ENDERECO = "Acailandia/MA"
EMPRESA_CONTATO = ""


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  HELPERS DE FORMATACAO                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def _g(d, *path, default=None):
    """Acesso aninhado defensivo: _g(ptam, 'imovel', 'endereco')."""
    cur = d
    for k in path:
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return default
    return cur if cur is not None else default


def fmt_moeda(valor) -> str:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "R$ 0,00"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_area(valor) -> str:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "—"
    return f"{v:,.2f} m²".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_data(data) -> str:
    if not data:
        return "—"
    if isinstance(data, datetime):
        return data.strftime("%d/%m/%Y")
    s = str(data)
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(s[:len(fmt) + 6], fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return s[:10]


def _txt(v, default="—"):
    if v is None:
        return default
    s = str(v).strip()
    return s if s else default


def _load_image_reader(src):
    """Retorna ImageReader de path/URL/bytes/BytesIO. Nunca lanca; None em falha."""
    if not src:
        return None
    try:
        if isinstance(src, (bytes, bytearray)):
            return ImageReader(BytesIO(bytes(src)))
        if isinstance(src, BytesIO):
            return ImageReader(src)
        return ImageReader(src)  # path local ou URL http(s)
    except Exception:
        logger.warning("ptam_pdf_v2: falha ao carregar imagem (placeholder usado)")
        return None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  FLOWABLE: CARD DE AMOSTRA                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝
CARD_H = 5.2 * cm
FOTO_R = 1.85 * cm


class AmostraCard(Flowable):
    def __init__(self, numero: int, amostra: dict):
        super().__init__()
        self.numero = numero
        self.a = amostra or {}
        self.width = UTIL_W
        self.height = CARD_H

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def _campo(self, c, x, y, label, valor):
        c.setFillColor(CINZA)
        c.setFont("Helvetica", 6.2)
        c.drawString(x, y, str(label).upper()[:34])
        c.setFillColor(PRETO)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(x, y - 0.32 * cm, _txt(valor)[:42])

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        a = self.a

        # 1. Sombra
        c.setFillColor(CINZA_BRD)
        c.roundRect(0.08 * cm, -0.08 * cm, w, h, 0.25 * cm, stroke=0, fill=1)
        # 2. Fundo do card
        c.setFillColor(BRANCO)
        c.setStrokeColor(HexColor('#DDDDDD'))
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 0.25 * cm, stroke=1, fill=1)
        # 3. Barra lateral verde
        c.setFillColor(VERDE)
        c.roundRect(0, 0, 0.28 * cm, h, 0.12 * cm, stroke=0, fill=1)

        # 4. Badge numero
        bx, by, bw, bh = 0.5 * cm, h - 1.0 * cm, 2.1 * cm, 0.55 * cm
        c.setFillColor(VERDE)
        c.roundRect(bx, by, bw, bh, 0.1 * cm, stroke=0, fill=1)
        c.setFillColor(BRANCO)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(bx + bw / 2, by + 0.16 * cm, f"AMOSTRA {self.numero}")

        # 5. Circulo da foto
        cx = 0.55 * cm + FOTO_R
        cy = h / 2 - 0.55 * cm
        c.setStrokeColor(DOURADO)
        c.setLineWidth(2)
        c.circle(cx, cy, FOTO_R + 0.06 * cm, stroke=1, fill=0)
        c.setFillColor(VERDE_CLARO)
        c.setStrokeColor(VERDE)
        c.setLineWidth(1)
        c.circle(cx, cy, FOTO_R, stroke=1, fill=1)
        img = _load_image_reader(a.get("foto_url") or a.get("foto"))
        if img is not None:
            try:
                c.saveState()
                p = c.beginPath()
                p.circle(cx, cy, FOTO_R)
                c.clipPath(p, stroke=0, fill=0)
                d = FOTO_R * 2
                c.drawImage(img, cx - FOTO_R, cy - FOTO_R, d, d,
                            preserveAspectRatio=True, anchor='c', mask='auto')
                c.restoreState()
            except Exception:
                pass
        else:
            c.setFillColor(VERDE)
            c.setFont("Helvetica", 11)
            c.drawCentredString(cx, cy + 0.15 * cm, "[FOTO]")
            c.setFillColor(CINZA)
            c.setFont("Helvetica", 5.5)
            c.drawCentredString(cx, cy - 0.45 * cm, "Foto da Amostra")

        # 6. Separador vertical
        sep_x = 0.6 * cm + FOTO_R * 2 + 0.55 * cm
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.4)
        c.line(sep_x, 0.3 * cm, sep_x, h - 0.3 * cm)

        # 7. Grid de dados (2 colunas)
        col1_x = sep_x + 0.35 * cm
        col2_x = sep_x + (w - sep_x) / 2 + 0.35 * cm
        top_y = h - 0.85 * cm
        dy = 1.0 * cm
        area_t = a.get("area_terreno")
        area_c = a.get("area_construida")
        area_str = " / ".join([s for s in [
            fmt_area(area_t) if area_t else None,
            fmt_area(area_c) if area_c else None,
        ] if s]) or "—"
        esquerda = [
            ("Endereco", a.get("endereco")),
            ("Tipo", a.get("tipo")),
            ("Area T / C", area_str),
            ("Fonte / Data", f"{_txt(a.get('fonte'), '')} {fmt_data(a.get('data_coleta'))}".strip()),
        ]
        direita = [
            ("Valor Ofertado", fmt_moeda(a.get("valor_ofertado"))),
            ("V.U. Tratado", fmt_moeda(a.get("valor_unitario_tratado"))),
            ("Fator Oferta", _txt(a.get("fator_oferta"))),
        ]
        for i, (lb, vl) in enumerate(esquerda):
            self._campo(c, col1_x, top_y - i * dy, lb, vl)
        for i, (lb, vl) in enumerate(direita):
            self._campo(c, col2_x, top_y - i * dy, lb, vl)

        # 8. Tag tipo (canto sup direito)
        tag = _txt(a.get("tipo_tag"), "")
        if tag:
            c.setFont("Helvetica-Bold", 6.5)
            tw = c.stringWidth(tag, "Helvetica-Bold", 6.5) + 0.4 * cm
            tx = w - tw - 0.35 * cm
            ty = h - 0.85 * cm
            c.setFillColor(VERDE_CLARO)
            c.setStrokeColor(VERDE)
            c.setLineWidth(0.6)
            c.roundRect(tx, ty, tw, 0.45 * cm, 0.1 * cm, stroke=1, fill=1)
            c.setFillColor(VERDE)
            c.drawCentredString(tx + tw / 2, ty + 0.13 * cm, tag)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  FLOWABLE: FOTO GRANDE (2 por pagina)                                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝
GAP = 0.5 * cm
FOTO_W = UTIL_W
FOTO_H = (UTIL_H - GAP) / 2


class FotoGrande(Flowable):
    def __init__(self, numero: int, legenda: str, total: int, url=None):
        super().__init__()
        self.numero = numero
        self.legenda = legenda or ""
        self.total = total
        self.url = url
        self.width = FOTO_W
        self.height = FOTO_H

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height

        # 1. Sombra
        c.setFillColor(HexColor('#BBBBBB'))
        c.roundRect(0.1 * cm, -0.1 * cm, w, h, 0.28 * cm, stroke=0, fill=1)
        # 2. Fundo
        c.setFillColor(CINZA_CLARO)
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.7)
        c.roundRect(0, 0, w, h, 0.28 * cm, stroke=1, fill=1)

        # 3. Imagem real ou placeholder
        faixa_h = 1.1 * cm
        img = _load_image_reader(self.url)
        if img is not None:
            try:
                c.saveState()
                p = c.beginPath()
                p.roundRect(0.1 * cm, faixa_h, w - 0.2 * cm, h - faixa_h - 0.1 * cm, 0.2 * cm)
                c.clipPath(p, stroke=0, fill=0)
                c.drawImage(img, 0.1 * cm, faixa_h, w - 0.2 * cm, h - faixa_h - 0.1 * cm,
                            preserveAspectRatio=True, anchor='c', mask='auto')
                c.restoreState()
            except Exception:
                self._placeholder(c, w, h)
        else:
            self._placeholder(c, w, h)

        # 4. Badge "FOTO NN"
        bx, by, bw, bh = 0.35 * cm, h - 0.95 * cm, 1.9 * cm, 0.6 * cm
        c.setFillColor(VERDE)
        c.roundRect(bx, by, bw, bh, 0.1 * cm, stroke=0, fill=1)
        c.setFillColor(BRANCO)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(bx + bw / 2, by + 0.18 * cm, f"FOTO {self.numero:02d}")

        # 5. Faixa legenda na base
        c.setFillColor(VERDE)
        c.roundRect(0, 0, w, faixa_h, 0.28 * cm, stroke=0, fill=1)
        c.setFillColor(VERDE)
        c.rect(0, faixa_h - 0.3 * cm, w, 0.3 * cm, stroke=0, fill=1)
        c.setFillColor(DOURADO)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.4 * cm, faixa_h / 2 - 0.12 * cm, "•")
        c.setFillColor(BRANCO)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(0.85 * cm, faixa_h / 2 - 0.12 * cm, str(self.legenda)[:95])

    def _placeholder(self, c, w, h):
        c.setFillColor(CINZA)
        c.setFont("Helvetica", 22)
        c.drawCentredString(w / 2, h / 2 + 0.2 * cm, "[ ]")
        c.setFont("Helvetica", 9)
        c.drawCentredString(w / 2, h / 2 - 0.6 * cm, f"Foto {self.numero} de {self.total}")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  DOC TEMPLATE com sumario (multiBuild)                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝
class _PtamDocTemplate(BaseDocTemplate):
    def __init__(self, filename, ptam, **kw):
        super().__init__(filename, **kw)
        self._ptam = ptam
        frame = Frame(MARGIN_L, MARGIN_B, UTIL_W, UTIL_H, id='corpo',
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id='capa', frames=[frame], onPage=self._capa_bg),
            PageTemplate(id='corpo', frames=[frame], onPage=self._header_footer),
        ])

    def _capa_bg(self, canvas, doc):
        pass  # a capa e composta por flowables; fundo verde desenhado abaixo

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        secao = getattr(doc, '_secao_atual', 'PARECER TECNICO')
        # Cabecalho
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(VERDE)
        canvas.drawString(MARGIN_L, A4[1] - 1.6 * cm, EMPRESA_NOME)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(CINZA)
        canvas.drawRightString(A4[0] - MARGIN_R, A4[1] - 1.6 * cm, f"PTAM — {secao}"[:70])
        canvas.setStrokeColor(DOURADO)
        canvas.setLineWidth(0.8)
        canvas.line(MARGIN_L, A4[1] - 1.8 * cm, A4[0] - MARGIN_R, A4[1] - 1.8 * cm)
        # Rodape
        canvas.setStrokeColor(DOURADO)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_L, MARGIN_B - 0.5 * cm, A4[0] - MARGIN_R, MARGIN_B - 0.5 * cm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(CINZA)
        canvas.drawString(MARGIN_L, MARGIN_B - 0.95 * cm,
                          "NBR 14653-2:2011 | Res. COFECI 1.066/2007")
        canvas.drawRightString(A4[0] - MARGIN_R, MARGIN_B - 0.95 * cm, f"Pagina {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style = flowable.style.name
            if style == 'SecTitle':
                self.notify('TOCEntry', (0, flowable.getPlainText(), self.page))
            elif style == 'SubTitle':
                self.notify('TOCEntry', (1, flowable.getPlainText(), self.page))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  GERADOR                                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝
STYLE_TABELA = TableStyle([
    ('BACKGROUND', (0, 0), (0, -1), VERDE),
    ('TEXTCOLOR', (0, 0), (0, -1), BRANCO),
    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ('BACKGROUND', (1, 0), (1, -1), HexColor('#F5F5F5')),
    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('GRID', (0, 0), (-1, -1), 0.4, CINZA_BRD),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
])

FINALIDADE_TEXTO = {
    'compra_venda': "determinar o Valor de Mercado para subsidiar negociacao de compra e venda do imovel.",
    'garantia_bancaria': "subsidiar operacao de credito imobiliario com garantia real sobre o imovel.",
    'inventario': "subsidiar processo de inventario / partilha entre herdeiros.",
    'judicial': "atender determinacao judicial, subsidiando decisao no processo em epigrafe.",
    'locacao': "determinar o Valor de Locacao do imovel.",
    'desapropriacao': "subsidiar processo de desapropriacao conforme a legislacao vigente.",
}


class PtamPDFGenerator:
    def __init__(self, ptam: dict):
        self.p = ptam or {}
        self._styles()

    # ── estilos ────────────────────────────────────────────────────────────
    def _styles(self):
        self.st_sec = ParagraphStyle('SecTitle', fontName='Helvetica-Bold',
                                      fontSize=13, textColor=VERDE, spaceAfter=2)
        self.st_sub = ParagraphStyle('SubTitle', fontName='Helvetica-Bold',
                                      fontSize=10, textColor=PRETO, leftIndent=4,
                                      spaceBefore=8, spaceAfter=4)
        self.st_nota = ParagraphStyle('Nota', fontName='Helvetica-Oblique',
                                      fontSize=8, textColor=CINZA, spaceAfter=6)
        self.st_corpo = ParagraphStyle('Corpo', fontName='Helvetica', fontSize=9,
                                       textColor=PRETO, leading=14, alignment=TA_JUSTIFY,
                                       spaceAfter=6)
        self.st_center = ParagraphStyle('Center', parent=self.st_corpo, alignment=TA_CENTER)
        self.st_cell = ParagraphStyle('Cell', fontName='Helvetica', fontSize=9,
                                      textColor=PRETO, leading=12)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _titulo_secao(self, texto, nota=''):
        out = [Paragraph(texto, self.st_sec),
               HRFlowable(width='100%', thickness=1.5, color=DOURADO,
                          spaceBefore=2, spaceAfter=6)]
        if nota:
            out.append(Paragraph(nota, self.st_nota))
        return out

    def _subtitulo(self, texto):
        return [Paragraph(texto, self.st_sub)]

    def _hr_fina(self):
        return HRFlowable(width='100%', thickness=0.4, color=DOURADO,
                          spaceBefore=6, spaceAfter=6)

    def _hr_grossa(self):
        return HRFlowable(width='100%', thickness=1, color=DOURADO,
                          spaceBefore=8, spaceAfter=8)

    def _tabela_descritiva(self, dados, col_w=None):
        col_w = col_w or [5.5 * cm, 8.0 * cm]
        linhas = []
        for lb, vl in dados:
            linhas.append([lb, Paragraph(_txt(vl), self.st_cell)])
        if not linhas:
            linhas = [["—", Paragraph("—", self.st_cell)]]
        t = Table(linhas, colWidths=col_w)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), VERDE),
            ('TEXTCOLOR', (0, 0), (0, -1), BRANCO),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.4, CINZA_BRD),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        for i in range(len(linhas)):
            if i % 2 == 1:
                style.add('BACKGROUND', (1, i), (1, i), VERDE_CLARO)
            else:
                style.add('BACKGROUND', (1, i), (1, i), BRANCO)
        t.setStyle(style)
        return t

    def _tabela_header_verde(self, header, linhas, col_w):
        data = [header] + (linhas or [["—"] * len(header)])
        t = Table(data, colWidths=col_w, repeatRows=1)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERDE),
            ('TEXTCOLOR', (0, 0), (-1, 0), BRANCO),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.4, CINZA_BRD),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BRANCO, VERDE_CLARO]),
            ('LINEBELOW', (0, -1), (-1, -1), 1.2, DOURADO),
        ])
        t.setStyle(style)
        return t

    def _caixa_valor_destaque(self, valor, extenso, metodo, data):
        body = [
            [Paragraph("VALOR DE MERCADO ADOTADO",
                       ParagraphStyle('cx1', fontName='Helvetica-Bold', fontSize=13,
                                      textColor=BRANCO, alignment=TA_CENTER))],
            [Paragraph(_txt(valor),
                       ParagraphStyle('cx2', fontName='Helvetica-Bold', fontSize=18,
                                      textColor=DOURADO, alignment=TA_CENTER, spaceBefore=4))],
            [Paragraph(f"({_txt(extenso, '')})",
                       ParagraphStyle('cx3', fontName='Helvetica-Oblique', fontSize=10,
                                      textColor=BRANCO, alignment=TA_CENTER))],
            [Paragraph(f"Metodo: {_txt(metodo, '')} | Data-Base: {_txt(data, '')}",
                       ParagraphStyle('cx4', fontName='Helvetica', fontSize=9,
                                      textColor=CINZA_BRD, alignment=TA_CENTER))],
        ]
        t = Table(body, colWidths=[UTIL_W])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), VERDE),
            ('BOX', (0, 0), (-1, -1), 1.5, DOURADO),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        return t

    def _quadro_resumo_amostras(self, amostras):
        header = ["Nº", "Endereco", "Area (m²)", "V.U. Oferta", "F. Oferta", "V.U. Tratado"]
        linhas = []
        for i, a in enumerate(amostras, 1):
            area = a.get("area_terreno") or a.get("area_construida")
            linhas.append([
                str(i), _txt(a.get("endereco"))[:46],
                fmt_area(area).replace(" m²", ""),
                fmt_moeda(a.get("valor_unitario_oferta")),
                _txt(a.get("fator_oferta")),
                fmt_moeda(a.get("valor_unitario_tratado")),
            ])
        return self._tabela_header_verde(
            header, linhas,
            [0.8 * cm, 5.8 * cm, 1.8 * cm, 3.0 * cm, 1.5 * cm, 3.1 * cm])

    # ── CAPA ─────────────────────────────────────────────────────────────────
    def _build_capa(self):
        p = self.p
        out = []
        # bloco verde topo (simulado com tabela)
        topo = Table([[Paragraph(EMPRESA_NOME,
                       ParagraphStyle('cap', fontName='Helvetica-Bold', fontSize=22,
                                      textColor=BRANCO, alignment=TA_CENTER))],
                      [Paragraph(EMPRESA_ENDERECO,
                       ParagraphStyle('cap2', fontName='Helvetica', fontSize=10,
                                      textColor=BRANCO, alignment=TA_CENTER))]],
                     colWidths=[UTIL_W], rowHeights=[4.0 * cm, 1.2 * cm])
        topo.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), VERDE),
                                  ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        out.append(topo)
        out.append(HRFlowable(width='100%', thickness=2, color=DOURADO, spaceBefore=6, spaceAfter=14))
        out.append(Paragraph("PTAM", ParagraphStyle('t', fontName='Helvetica-Bold',
                   fontSize=20, textColor=VERDE, alignment=TA_CENTER, spaceAfter=6)))
        out.append(Paragraph("PARECER TECNICO DE AVALIACAO MERCADOLOGICA",
                   ParagraphStyle('st', fontName='Helvetica-Bold', fontSize=14,
                                  textColor=PRETO, alignment=TA_CENTER, spaceAfter=6)))
        out.append(Paragraph("Resolucao COFECI nº 1.066/2007 | NBR 14653-2:2011 (ABNT)",
                   ParagraphStyle('ref', fontName='Helvetica', fontSize=10,
                                  textColor=CINZA, alignment=TA_CENTER, spaceAfter=10)))
        out.append(HRFlowable(width='100%', thickness=1, color=DOURADO, spaceBefore=4, spaceAfter=14))
        ano = (fmt_data(_g(p, 'data_laudo')) or '')[-4:]
        ident = [
            ("Tipo do Documento", "PTAM — Parecer Tecnico de Avaliacao Mercadologica"),
            ("Finalidade", _g(p, 'finalidade')),
            ("Solicitante", _g(p, 'solicitante', 'nome')),
            ("Imovel Avaliando", _g(p, 'imovel', 'endereco')),
            ("Data do Parecer", fmt_data(_g(p, 'data_laudo'))),
            ("Referencia", f"PTAM-{_txt(_g(p, 'id_curto') or _g(p, 'id'), '')}/{ano}"),
        ]
        out.append(self._tabela_descritiva(ident))
        out.append(HRFlowable(width='100%', thickness=1, color=DOURADO, spaceBefore=14, spaceAfter=8))
        out.append(Paragraph(
            f"{_txt(_g(p, 'avaliador', 'nome'), '')} — CNAI {_txt(_g(p, 'avaliador', 'cnai'), '')} | "
            f"CRECI/MA {_txt(_g(p, 'avaliador', 'creci'), '')}",
            ParagraphStyle('av', fontName='Helvetica', fontSize=9, textColor=CINZA, alignment=TA_CENTER)))
        return out

    # ── secoes ────────────────────────────────────────────────────────────────
    def _sec(self, titulo, nota=''):
        return self._titulo_secao(titulo, nota)

    def _build_secao_01_tipo(self):
        p = self.p
        ano = (fmt_data(_g(p, 'data_laudo')) or '')[-4:]
        out = self._sec("1. TIPO DO DOCUMENTO: LAUDO OU PTAM?",
                        "Res. COFECI 1.066/2007 | NBR 14653")
        out.append(self._tabela_descritiva([
            ("Tipo do Documento", "PTAM — Parecer Tecnico de Avaliacao Mercadologica"),
            ("Norma de Referencia", "NBR 14653-1:2019 e NBR 14653-2:2011 (ABNT)"),
            ("Resolucao COFECI", "Resolucao nº 1.066/2007"),
            ("Grau de Fundamentacao", _g(p, 'grau_fundamentacao')),
            ("Grau de Precisao", _g(p, 'grau_precisao')),
            ("Referencia", f"PTAM-{_txt(_g(p, 'id_curto') or _g(p, 'id'), '')}/{ano}"),
            ("Data de Emissao", fmt_data(_g(p, 'data_laudo'))),
            ("Validade", "180 (cento e oitenta) dias"),
        ]))
        out.append(Spacer(1, 8))
        out.append(Paragraph(
            "O PTAM (Parecer Tecnico de Avaliacao Mercadologica) e o documento de avaliacao "
            "emitido pelo Corretor de Imoveis habilitado (CNAI/COFECI), distinto do Laudo de "
            "Avaliacao de competencia do Engenheiro (CREA). Ambos seguem a NBR 14653, diferindo "
            "quanto a habilitacao profissional do responsavel tecnico.", self.st_corpo))
        return out

    def _build_secao_02_finalidade(self):
        p = self.p
        fin = _g(p, 'finalidade')
        texto = FINALIDADE_TEXTO.get(fin) or _g(p, 'finalidade_texto') or "—"
        out = self._sec("2. FINALIDADE DO PARECER", "Res. COFECI 1.066/2007, Art. 3º")
        out.append(self._tabela_descritiva([
            ("Finalidade", fin),
            ("Texto de Finalidade", texto),
            ("Destinatario", _g(p, 'solicitante', 'nome')),
            ("Data-Base", fmt_data(_g(p, 'data_vistoria'))),
        ]))
        out.append(Spacer(1, 6))
        out.append(Paragraph("Norma de referencia: NBR 14653-1:2019 e NBR 14653-2:2011 (ABNT).",
                             self.st_nota))
        return out

    def _build_secao_03_solicitante(self):
        p = self.p
        out = self._sec("3. DADOS DO SOLICITANTE")
        out.append(self._tabela_descritiva([
            ("Nome / Razao Social", _g(p, 'solicitante', 'nome')),
            ("CPF / CNPJ", _g(p, 'solicitante', 'cpf_cnpj')),
            ("Endereco", _g(p, 'solicitante', 'endereco')),
            ("Telefone", _g(p, 'solicitante', 'telefone')),
            ("E-mail", _g(p, 'solicitante', 'email')),
            ("Qualidade", _g(p, 'solicitante', 'qualidade')),
            ("Documento de Identidade", _g(p, 'solicitante', 'documento')),
        ]))
        return out

    def _build_sumario(self, toc):
        out = [Paragraph("SUMARIO", self.st_sec),
               HRFlowable(width='100%', thickness=1.5, color=DOURADO, spaceBefore=2, spaceAfter=10)]
        toc.levelStyles = [
            ParagraphStyle('toc1', fontName='Helvetica-Bold', fontSize=10, leading=16),
            ParagraphStyle('toc2', fontName='Helvetica', fontSize=9, leading=14, leftIndent=1 * cm),
        ]
        out.append(toc)
        return out

    def _build_secao_05_objetivo(self):
        p = self.p
        out = self._sec("5. OBJETIVO DA AVALIACAO")
        out.append(self._tabela_descritiva([
            ("Objeto", f"{_txt(_g(p, 'imovel', 'endereco'), '')} - {_txt(_g(p, 'imovel', 'tipo'), '')}"),
            ("Finalidade Tecnica", FINALIDADE_TEXTO.get(_g(p, 'finalidade')) or _g(p, 'finalidade')),
            ("Metodo Principal", _g(p, 'metodologia', 'metodo_principal')),
            ("Norma Aplicavel", "NBR 14653-1:2019 | NBR 14653-2:2011"),
            ("Grau de Fundamentacao", _g(p, 'grau_fundamentacao')),
            ("Data-Base", fmt_data(_g(p, 'data_vistoria'))),
        ]))
        return out

    def _build_secao_06_imovel(self):
        p = self.p
        out = self._sec("6. IDENTIFICACAO DO IMOVEL AVALIANDO", "NBR 14653-2, item 8.1")
        out.append(self._tabela_descritiva([
            ("Endereco Completo", _g(p, 'imovel', 'endereco')),
            ("Bairro", _g(p, 'imovel', 'bairro')),
            ("Municipio / UF", f"{_txt(_g(p, 'imovel', 'municipio'), '')}/{_txt(_g(p, 'imovel', 'uf'), '')}"),
            ("CEP", _g(p, 'imovel', 'cep')),
            ("Matricula / Transcricao", _g(p, 'imovel', 'matricula')),
            ("Cartorio", _g(p, 'imovel', 'cartorio')),
            ("Tipo", _g(p, 'imovel', 'tipo')),
            ("Uso", _g(p, 'imovel', 'uso')),
            ("Area do Terreno", fmt_area(_g(p, 'imovel', 'area_terreno'))),
            ("Area Construida", fmt_area(_g(p, 'imovel', 'area_construida'))),
            ("Area Total Avaliada", fmt_area(_g(p, 'imovel', 'area_total'))),
            ("IPTU / ITR nº", _g(p, 'imovel', 'iptu_itr')),
        ]))
        return out

    def _check(self, v):
        return "Sim" if v else "Nao"

    def _build_secao_07_regiao(self):
        p = self.p
        out = self._sec("7. REGIAO E CONTEXTO URBANO/RURAL", "NBR 14653-2, item 8.2")
        out += self._subtitulo("7.1 Localizacao e Entorno")
        out.append(self._tabela_descritiva([
            ("Descricao da Localizacao", _g(p, 'regiao', 'descricao_localizacao')),
            ("Equipamentos Urbanos", _g(p, 'regiao', 'equipamentos_urbanos')),
            ("Perfil Socioeconomico", _g(p, 'regiao', 'perfil_socioeconomico')),
            ("Tendencia", _g(p, 'regiao', 'tendencia')),
        ]))
        out += self._subtitulo("7.2 Infraestrutura Disponivel")
        infra = _g(p, 'regiao', 'infra', default={}) or {}
        out.append(self._tabela_descritiva([
            ("Agua", self._check(infra.get('agua'))),
            ("Energia", self._check(infra.get('energia'))),
            ("Esgoto", self._check(infra.get('esgoto'))),
            ("Pavimentacao", self._check(infra.get('pavimentacao'))),
            ("Calcada", self._check(infra.get('calcada'))),
            ("Iluminacao", self._check(infra.get('iluminacao'))),
            ("Coleta de Lixo", self._check(infra.get('coleta_lixo'))),
            ("Internet", self._check(infra.get('internet'))),
        ]))
        out += self._subtitulo("7.3 Analise Mercadologica da Regiao")
        out.append(self._tabela_descritiva([
            ("Oferta", _g(p, 'regiao', 'oferta')),
            ("Demanda", _g(p, 'regiao', 'demanda')),
            ("Liquidez", _g(p, 'regiao', 'liquidez')),
            ("Analise Mercadologica", _g(p, 'regiao', 'analise_mercadologica')),
        ]))
        return out

    def _build_secao_08_caracterizacao(self):
        p = self.p
        out = self._sec("8. CARACTERIZACAO DO IMOVEL", "NBR 14653-2, itens 8.3 e 8.4")
        ter = _g(p, 'imovel', 'terreno', default={}) or {}
        out += self._subtitulo("8.1 Caracteristicas do Terreno")
        out.append(self._tabela_descritiva([
            ("Formato", ter.get('formato')),
            ("Topografia", ter.get('topografia')),
            ("Pedologia", ter.get('pedologia')),
            ("Testada", ter.get('testada')),
            ("Fundo", ter.get('fundo')),
            ("Lados", ter.get('lados')),
            ("Area", fmt_area(ter.get('area') or _g(p, 'imovel', 'area_terreno'))),
        ]))
        try:
            area_c = float(_g(p, 'imovel', 'area_construida') or 0)
        except (TypeError, ValueError):
            area_c = 0
        if area_c > 0:
            con = _g(p, 'imovel', 'construcao', default={}) or {}
            out += self._subtitulo("8.2 Caracteristicas da Construcao")
            out.append(self._tabela_descritiva([
                ("Padrao Construtivo", con.get('padrao')),
                ("Estrutura", con.get('estrutura')),
                ("Cobertura", con.get('cobertura')),
                ("Revestimentos", con.get('revestimentos') or con.get('revestimento')),
                ("Piso", con.get('piso')),
                ("Estado de Conservacao", con.get('estado_conservacao')),
                ("Idade Aparente", con.get('idade_aparente')),
                ("Vida Util", con.get('vida_util')),
                ("Nº de Comodos", con.get('comodos') or con.get('num_comodos')),
            ]))
        out += self._subtitulo("8.3 Benfeitorias e Equipamentos")
        benf = _g(p, 'imovel', 'benfeitorias', default=[]) or []
        if benf:
            for b in benf:
                out.append(Paragraph(f"• {_txt(b)}", self.st_corpo))
        else:
            out.append(Paragraph("Nenhuma benfeitoria relevante registrada.", self.st_corpo))
        return out

    def _build_secao_09_amostras(self):
        p = self.p
        amostras = _g(p, 'amostras', default=[]) or []
        nota = "Minimo 3 amostras (Grau I) | 5 amostras (Grau II) — NBR 14653-2, item 8.5"
        out = self._sec("9. AMOSTRAS DE MERCADO — PESQUISA", nota)
        if not amostras:
            out.append(Paragraph("Nenhuma amostra de mercado cadastrada.", self.st_corpo))
            return out
        for i, a in enumerate(amostras, 1):
            out.append(AmostraCard(i, a))
            out.append(Spacer(1, 0.35 * cm))
        out += self._subtitulo("9.N Quadro Resumo das Amostras")
        out.append(self._quadro_resumo_amostras(amostras))
        return out

    def _build_secao_10_metodologia(self):
        p = self.p
        out = self._sec("10. METODOLOGIA ADOTADA",
                        "NBR 14653-1:2019, item 8 | NBR 14653-2:2011, item 8.6")
        fatores = _g(p, 'metodologia', 'fatores', default=[]) or []
        out.append(self._tabela_descritiva([
            ("Metodo Principal", _g(p, 'metodologia', 'metodo_principal')),
            ("Justificativa", _g(p, 'metodologia', 'justificativa')),
            ("Tratamento", _g(p, 'metodologia', 'tratamento')),
            ("Fatores Utilizados", ", ".join(str(f) for f in fatores) if fatores else "—"),
            ("Campo de Arbitrio", "± 15% sobre valor unitario saneado"),
            ("Criterio de Saneamento", _g(p, 'metodologia', 'criterio_saneamento')),
            ("Metodo Complementar", _g(p, 'metodologia', 'metodo_complementar')),
            ("Grau de Fundamentacao", _g(p, 'grau_fundamentacao')),
            ("Grau de Precisao", _g(p, 'grau_precisao')),
        ]))
        out += self._subtitulo("10.1 Depreciacao — Metodo Adotado")
        out.append(self._tabela_descritiva([
            ("Metodo", _g(p, 'depreciacao', 'metodo')),
            ("Parametros", "Idade real, vida util, estado de conservacao"),
            ("Referencia", "NBR 14653-2, item 8.4 | Tabela Ross-Heidecke"),
        ]))
        return out

    def _build_secao_11_calculos(self):
        p = self.p
        out = self._sec("11. CALCULOS E TRATAMENTO DOS VALORES", "NBR 14653-2, item 8.6")
        out += self._subtitulo("11.1 Fatores de Homogeneizacao")
        fatores = _g(p, 'calculos', 'fatores', default=[]) or []
        linhas = []
        for f in fatores:
            linhas.append([
                _txt(f.get('amostra') if isinstance(f, dict) else f),
                _txt(f.get('f_localizacao') if isinstance(f, dict) else ''),
                _txt(f.get('f_padrao') if isinstance(f, dict) else ''),
                _txt(f.get('f_area') if isinstance(f, dict) else ''),
                _txt(f.get('f_oferta') if isinstance(f, dict) else ''),
                _txt(f.get('fh_total') if isinstance(f, dict) else ''),
                fmt_moeda(f.get('vu_homog')) if isinstance(f, dict) else '—',
            ])
        out.append(self._tabela_header_verde(
            ["Amostra", "F.Localiz.", "F.Padrao", "F.Area", "F.Oferta", "FH Total", "V.U. Homog."],
            linhas, [1.5 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 3.0 * cm]))
        est = _g(p, 'calculos', 'estatisticas', default={}) or {}
        out += self._subtitulo("11.2 Estatisticas da Amostragem")
        out.append(self._tabela_descritiva([
            ("Minimo", fmt_moeda(est.get('minimo'))),
            ("Maximo", fmt_moeda(est.get('maximo'))),
            ("Media", fmt_moeda(est.get('media'))),
            ("Desvio Padrao", _txt(est.get('desvio_padrao'))),
            ("CV %", _txt(est.get('cv'))),
            ("Valor Saneado", fmt_moeda(est.get('valor_saneado'))),
        ]))
        arb = _g(p, 'calculos', 'campo_arbitrio', default={}) or {}
        out += self._subtitulo("11.3 Campo de Arbitrio (± 15%)")
        out.append(self._tabela_descritiva([
            ("Limite Inferior", fmt_moeda(arb.get('limite_inferior'))),
            ("Valor Adotado", fmt_moeda(arb.get('valor_adotado'))),
            ("Limite Superior", fmt_moeda(arb.get('limite_superior'))),
        ]))
        out += self._subtitulo("11.4 Calculo do Valor Final")
        out.append(self._tabela_descritiva([
            ("Valor Unitario Adotado", f"{fmt_moeda(_g(p, 'resultado', 'valor_unitario'))} /m²"),
            ("Area Avaliada", fmt_area(_g(p, 'resultado', 'area'))),
            ("Valor Bruto", fmt_moeda(_g(p, 'calculos', 'valor_bruto'))),
            ("Depreciacao", fmt_moeda(_g(p, 'depreciacao', 'valor_depreciacao'))),
            ("Valorizacao", fmt_moeda(_g(p, 'valorizacao', 'valor'))),
            ("VALOR DE MERCADO", fmt_moeda(_g(p, 'resultado', 'valor_final'))),
        ]))
        return out

    def _build_secao_12_ponderancia(self):
        p = self.p
        out = self._sec("12. PONDERANCIA DOS RESULTADOS", "NBR 14653-2, item 8.7")
        res = _g(p, 'ponderacao', 'resultados', default=[]) or []
        if not res or len(res) <= 1:
            out.append(Paragraph("Nao aplicavel — metodo unico adotado.", self.st_corpo))
            return out
        linhas = [[
            _txt(r.get('metodo')), _txt(r.get('resultado')),
            _txt(r.get('peso')), fmt_moeda(r.get('valor_ponderado'))
        ] for r in res]
        out.append(self._tabela_header_verde(
            ["Metodo", "Resultado", "Peso (%)", "Valor Ponderado"],
            linhas, [4.0 * cm, 3.5 * cm, 2.5 * cm, 3.5 * cm]))
        return out

    def _build_secao_13_depreciacao(self):
        p = self.p
        out = self._sec("13. DEPRECIACAO / VALORIZACAO",
                        "NBR 14653-2, item 8.4 | Tabela Ross-Heidecke")
        d = _g(p, 'depreciacao', default={}) or {}
        out += self._subtitulo("13.1 Depreciacao da Construcao")
        out.append(self._tabela_descritiva([
            ("Metodo", d.get('metodo')),
            ("Idade Real", d.get('idade_real')),
            ("Vida Util", d.get('vida_util')),
            ("Estado de Conservacao", d.get('estado_conservacao')),
            ("Coeficiente K", d.get('coeficiente_k')),
            ("Fator Fd %", d.get('fator_fd')),
            ("Valor da Depreciacao", fmt_moeda(d.get('valor_depreciacao'))),
        ]))
        v = _g(p, 'valorizacao', default={}) or {}
        out += self._subtitulo("13.2 Valorizacao / Fatores Positivos")
        out.append(self._tabela_descritiva([
            ("Fatores", v.get('fatores')),
            ("Percentual", v.get('percentual')),
            ("Valor", fmt_moeda(v.get('valor'))),
            ("Justificativa", v.get('justificativa')),
        ]))
        return out

    def _build_secao_14_resultado(self):
        p = self.p
        out = self._sec("14. RESULTADO FINAL DA AVALIACAO")
        out.append(self._caixa_valor_destaque(
            fmt_moeda(_g(p, 'resultado', 'valor_final')),
            _g(p, 'resultado', 'valor_extenso'),
            _g(p, 'resultado', 'metodo'),
            fmt_data(_g(p, 'resultado', 'data_base') or _g(p, 'data_vistoria'))))
        out.append(Spacer(1, 10))
        out.append(self._tabela_descritiva([
            ("Metodo Adotado", _g(p, 'resultado', 'metodo')),
            ("Valor Unitario Adotado", f"{fmt_moeda(_g(p, 'resultado', 'valor_unitario'))} /m²"),
            ("Area Avaliada", fmt_area(_g(p, 'resultado', 'area'))),
            ("Valor Final (arredondado)", fmt_moeda(_g(p, 'resultado', 'valor_final'))),
            ("Valor por Extenso", _g(p, 'resultado', 'valor_extenso')),
            ("Justificativa", _g(p, 'resultado', 'justificativa')),
        ]))
        return out

    def _build_secao_15_conclusao(self):
        p = self.p
        out = self._sec("15. CONCLUSAO", "Res. COFECI 1.066/2007 | NBR 14653-1:2019, item 9")
        texto = _g(p, 'conclusao', 'texto')
        if not texto:
            texto = (
                f"Com base nos elementos coletados, nas pesquisas de mercado realizadas e na "
                f"metodologia descrita, o signatario conclui que o valor de mercado do imovel "
                f"situado em {_txt(_g(p, 'imovel', 'endereco'), '')}, na data-base de "
                f"{fmt_data(_g(p, 'data_vistoria'))}, e de {fmt_moeda(_g(p, 'resultado', 'valor_final'))} "
                f"({_txt(_g(p, 'resultado', 'valor_extenso'), '')}), conforme demonstrado neste Parecer.")
        out.append(self._tabela_descritiva([
            ("Texto de Conclusao", texto),
            ("Validade", "180 dias a contar da data de emissao"),
            ("Ressalvas", _g(p, 'conclusao', 'ressalvas')),
            ("Pressupostos", _g(p, 'conclusao', 'pressupostos')),
            ("Limitacoes", _g(p, 'conclusao', 'limitacoes')),
        ]))
        out.append(Spacer(1, 14))
        out += self._bloco_assinatura()
        return out

    def _bloco_assinatura(self):
        p = self.p
        out = [Paragraph(f"Acailandia/MA, {fmt_data(_g(p, 'data_laudo'))}", self.st_center),
               Spacer(1, 1.4 * cm),
               Paragraph("_____________________________________________", self.st_center),
               Paragraph(_txt(_g(p, 'avaliador', 'nome'), ''),
                         ParagraphStyle('asn', fontName='Helvetica-Bold', fontSize=11,
                                        textColor=PRETO, alignment=TA_CENTER)),
               Paragraph(f"Avaliador de Imoveis — CNAI {_txt(_g(p, 'avaliador', 'cnai'), '')}",
                         ParagraphStyle('asr', fontName='Helvetica', fontSize=9,
                                        textColor=CINZA, alignment=TA_CENTER)),
               Paragraph(f"CRECI/MA {_txt(_g(p, 'avaliador', 'creci'), '')} | "
                         f"CFT/MA {_txt(_g(p, 'avaliador', 'cft'), '')}",
                         ParagraphStyle('asr2', fontName='Helvetica', fontSize=9,
                                        textColor=CINZA, alignment=TA_CENTER))]
        proc = _g(p, 'processo_judicial', 'numero')
        if proc:
            out.append(Paragraph(f"Perito do Juizo — Processo nº {_txt(proc)}",
                       ParagraphStyle('asp', fontName='Helvetica', fontSize=9,
                                      textColor=CINZA, alignment=TA_CENTER)))
        return out

    def _build_secao_16_fotos_imovel(self):
        p = self.p
        fotos = _g(p, 'fotos_imovel', default=[]) or []
        fotos = sorted(fotos, key=lambda f: (f.get('ordem') if isinstance(f, dict) else 0) or 0)
        out = self._sec("16. RELATORIO FOTOGRAFICO DO IMOVEL AVALIANDO")
        if not fotos:
            out.append(Paragraph("Nenhuma foto do imovel cadastrada.", self.st_corpo))
            return out
        total = len(fotos)
        out.append(Paragraph("Registro fotografico do imovel avaliando, ordenado conforme vistoria.",
                             self.st_nota))
        for i in range(0, total, 2):
            if i > 0:
                out.append(PageBreak())
                n2 = min(i + 2, total)
                out.append(Paragraph(f"Fotografias {i + 1} e {n2} de {total}",
                           ParagraphStyle('cnt', fontName='Helvetica', fontSize=7.5,
                                          textColor=CINZA, alignment=TA_CENTER, spaceAfter=4)))
            f1 = fotos[i]
            out.append(FotoGrande(i + 1, _g(f1, 'legenda') if isinstance(f1, dict) else '',
                                  total, _g(f1, 'url') if isinstance(f1, dict) else f1))
            if i + 1 < total:
                out.append(Spacer(1, GAP))
                f2 = fotos[i + 1]
                out.append(FotoGrande(i + 2, _g(f2, 'legenda') if isinstance(f2, dict) else '',
                                      total, _g(f2, 'url') if isinstance(f2, dict) else f2))
            else:
                out.append(Spacer(1, GAP))
                out.append(Spacer(1, FOTO_H))
        return out

    def _build_secao_17_documentos(self):
        p = self.p
        out = self._sec("17. DOCUMENTOS DO IMOVEL")
        docs = _g(p, 'documentos', default=[]) or []
        linhas = []
        for i, d in enumerate(docs, 1):
            linhas.append([
                str(i), _txt(_g(d, 'tipo')), _txt(_g(d, 'descricao')),
                fmt_data(_g(d, 'data_emissao')), _txt(_g(d, 'observacao'), ''),
            ])
        out.append(self._tabela_header_verde(
            ["Nº", "Tipo do Documento", "Descricao", "Data", "Observacao"],
            linhas, [0.8 * cm, 3.5 * cm, 4.5 * cm, 2.5 * cm, 3.7 * cm]))
        out.append(Spacer(1, 8))
        out.append(Paragraph(
            f"Os documentos acima foram fornecidos pelo solicitante e/ou obtidos pelo avaliador "
            f"para instrucao deste parecer. Copias digitais arquivadas no AvalieImob sob "
            f"referencia PTAM-{_txt(_g(p, 'id_curto') or _g(p, 'id'), '')}.", self.st_corpo))
        return out

    def _build_secao_18_trt_art(self):
        p = self.p
        out = self._sec("18. TRT / ART / RRT", "Res. COFECI 1.066/2007 | CREA/COFECI")
        out.append(self._tabela_descritiva([
            ("Tipo de Registro", _g(p, 'art_trt', 'tipo')),
            ("Numero", _g(p, 'art_trt', 'numero')),
            ("Data de Emissao", fmt_data(_g(p, 'art_trt', 'data_emissao'))),
            ("Valor Recolhido", fmt_moeda(_g(p, 'art_trt', 'valor'))),
            ("Conselho", _g(p, 'art_trt', 'conselho')),
            ("Observacao", "Copia anexada ao final deste documento"),
        ]))
        out.append(Spacer(1, 6))
        out.append(Paragraph(
            "O PTAM assinado por Corretor de Imoveis deve ser acompanhado do TRT (COFECI). Quando o "
            "avaliador acumula habilitacao de Tecnico em Edificacoes (CREA), a ART pode ser emitida "
            "complementarmente.", self.st_nota))
        return out

    def _build_secao_19_texto_conclusao(self):
        p = self.p
        out = self._sec("19. TEXTO DE CONCLUSAO DO LAUDO",
                        "NBR 14653-1:2019, item 9.3 | Res. COFECI 1.066/2007, Art. 4º")
        # 19.1
        out += self._subtitulo("19.1 Texto Principal de Conclusao")
        texto = _g(p, 'conclusao', 'texto_conclusao')
        if not texto:
            out.append(Paragraph(
                f"Com base nos elementos coletados em vistoria realizada em "
                f"{fmt_data(_g(p, 'data_vistoria'))}, nas pesquisas de mercado efetuadas na regiao e "
                f"na metodologia tecnica descrita neste Parecer, o signatario conclui que o valor de "
                f"mercado do imovel situado em {_txt(_g(p, 'imovel', 'endereco'), '')}, "
                f"{_txt(_g(p, 'imovel', 'bairro'), '')}, {_txt(_g(p, 'imovel', 'municipio'), '')}/"
                f"{_txt(_g(p, 'imovel', 'uf'), '')}, na data-base de "
                f"{fmt_data(_g(p, 'data_vistoria'))}, e de:", self.st_corpo))
        else:
            out.append(Paragraph(_txt(texto), self.st_corpo))
        out.append(Paragraph(
            f"{fmt_moeda(_g(p, 'resultado', 'valor_final'))} "
            f"({_txt(_g(p, 'resultado', 'valor_extenso'), '')})",
            ParagraphStyle('v19', fontName='Helvetica-Bold', fontSize=13, textColor=VERDE,
                           alignment=TA_CENTER, spaceBefore=8, spaceAfter=8)))
        out.append(Paragraph(
            f"Valor determinado pelo {_txt(_g(p, 'resultado', 'metodo'), '')}, em conformidade com a "
            f"NBR 14653-2:2011 (ABNT) e a Resolucao COFECI nº 1.066/2007, com grau de fundamentacao "
            f"{_txt(_g(p, 'grau_fundamentacao'), '')} e grau de precisao "
            f"{_txt(_g(p, 'grau_precisao'), '')}.", self.st_corpo))
        # 19.2
        out.append(self._hr_fina())
        out += self._subtitulo("19.2 Validade do Parecer")
        out.append(Paragraph(
            "O presente Parecer Tecnico de Avaliacao Mercadologica possui validade estimada de 180 "
            "(cento e oitenta) dias a contar da data de sua emissao, podendo sofrer revisao caso "
            "ocorram alteracoes significativas nas condicoes de mercado, na legislacao aplicavel ou "
            "no estado de conservacao do imovel avaliando.", self.st_corpo))
        # 19.3
        out.append(self._hr_fina())
        out.append(Paragraph("Ressalvas:", self.st_sub))
        out.append(Paragraph(_g(p, 'conclusao', 'ressalva') or (
            "Este parecer foi elaborado com base nas informacoes e documentos fornecidos pelo "
            "solicitante e nas condicoes de mercado verificadas na data da vistoria. O signatario nao "
            "se responsabiliza por informacoes incorretas, omitidas ou adulteradas pelo contratante, "
            "nem por alteracoes ocorridas apos a data-base desta avaliacao."), self.st_corpo))
        # 19.4
        out.append(self._hr_fina())
        out.append(Paragraph("Pressupostos:", self.st_sub))
        out.append(Paragraph(_g(p, 'conclusao', 'pressuposto') or (
            "Presumiu-se que o imovel esta livre e desembaracado de quaisquer onus, dividas, "
            "hipotecas, penhoras ou restricoes judiciais, salvo as expressamente mencionadas neste "
            "documento. Presumiu-se ainda a regularidade da documentacao apresentada."), self.st_corpo))
        # 19.5
        out.append(self._hr_fina())
        out.append(Paragraph("Limitacoes:", self.st_sub))
        out.append(Paragraph(_g(p, 'conclusao', 'limitacoes') or (
            "A presente avaliacao baseou-se em vistoria e nas informacoes disponiveis na data-base "
            "indicada. Eventuais restricoes de acesso ao imovel, ausencia de documentacao ou "
            "limitacoes de mercado estao descritas no corpo deste Parecer."), self.st_corpo))
        # 19.6
        out.append(self._hr_grossa())
        out.append(Paragraph(f"Acailandia/MA, {fmt_data(_g(p, 'data_laudo'))}",
                   ParagraphStyle('d19', fontName='Helvetica-Oblique', fontSize=9,
                                  textColor=CINZA, alignment=TA_CENTER)))
        out.append(Spacer(1, 1.8 * cm))
        out += self._bloco_assinatura_completo()
        return out

    def _bloco_assinatura_completo(self):
        p = self.p
        av = _g(p, 'avaliador', default={}) or {}
        out = [
            Paragraph("_____________________________________________",
                      ParagraphStyle('ul', fontName='Helvetica', fontSize=10,
                                     textColor=VERDE, alignment=TA_CENTER)),
            Paragraph(_txt(av.get('nome'), ''),
                      ParagraphStyle('n', fontName='Helvetica-Bold', fontSize=11,
                                     textColor=PRETO, alignment=TA_CENTER)),
            Paragraph(f"Avaliador de Imoveis — CNAI {_txt(av.get('cnai'), '')}",
                      ParagraphStyle('r', fontName='Helvetica', fontSize=9,
                                     textColor=CINZA, alignment=TA_CENTER)),
            Paragraph(f"CRECI/MA {_txt(av.get('creci'), '')} | CFT/MA {_txt(av.get('cft'), '')}",
                      ParagraphStyle('r2', fontName='Helvetica', fontSize=9,
                                     textColor=CINZA, alignment=TA_CENTER)),
            Paragraph(_txt(av.get('empresa'), ''),
                      ParagraphStyle('e', fontName='Helvetica-Bold', fontSize=9,
                                     textColor=VERDE, alignment=TA_CENTER)),
            Paragraph(f"{_txt(av.get('telefone'), '')} | {_txt(av.get('email'), '')}",
                      ParagraphStyle('c', fontName='Helvetica', fontSize=8,
                                     textColor=CINZA, alignment=TA_CENTER)),
        ]
        proc = _g(p, 'processo_judicial', default={}) or {}
        if proc.get('numero'):
            out.append(Paragraph(f"Perito do Juizo — Processo nº {_txt(proc.get('numero'))}",
                       ParagraphStyle('pj', fontName='Helvetica', fontSize=9,
                                      textColor=CINZA, alignment=TA_CENTER)))
            out.append(Paragraph(f"Vara: {_txt(proc.get('vara'), '')}",
                       ParagraphStyle('pv', fontName='Helvetica', fontSize=9,
                                      textColor=CINZA, alignment=TA_CENTER)))
        return out

    def _build_secao_20_curriculo(self):
        p = self.p
        av = _g(p, 'avaliador', default={}) or {}
        out = self._sec("20. QUALIFICACAO TECNICA DO AVALIADOR",
                        "Res. COFECI 1.066/2007, Art. 5º — obrigatorio")
        out += self._subtitulo("20.1 Dados de Identificacao Profissional")
        dados = [
            ("Nome Completo", av.get('nome')),
            ("Formacao Academica", av.get('formacao')),
            ("Especializacao", av.get('especializacao')),
            ("CNAI (COFECI)", av.get('cnai')),
            ("CRECI", av.get('creci')),
        ]
        for chave, lbl in [('cft', 'CFT/MA'), ('crea', 'CREA/MA'), ('incra', 'INCRA')]:
            if av.get(chave):
                dados.append((lbl, av.get(chave)))
        dados.append(("Empresa / Escritorio", av.get('empresa')))
        if av.get('cnpj_empresa'):
            dados.append(("CNPJ da Empresa", av.get('cnpj_empresa')))
        dados += [
            ("Endereco Profissional", av.get('endereco')),
            ("CEP", av.get('cep')),
            ("Telefone / WhatsApp", av.get('telefone')),
            ("E-mail", av.get('email')),
        ]
        if av.get('site'):
            dados.append(("Site / Portfolio", av.get('site')))
        out.append(self._tabela_descritiva(dados))

        out.append(self._hr_fina())
        out += self._subtitulo("Experiencia e Atuacao Profissional")
        curric = av.get('curriculo')
        if isinstance(curric, dict):
            curric = (
                f"{_txt(av.get('nome'), '')} e {_txt(av.get('formacao'), '')}, com registro ativo no "
                f"COFECI (CNAI {_txt(av.get('cnai'), '')}) e CRECI/MA {_txt(av.get('creci'), '')}. "
                f"Atua na area de avaliacao imobiliaria, com especializacao em "
                f"{_txt(av.get('especializacao'), '')}. E responsavel tecnico da "
                f"{_txt(av.get('empresa'), '')}, prestando servicos de avaliacao de imoveis urbanos e "
                f"rurais, laudos tecnicos periciais, assessoria imobiliaria e consultoria em negocios "
                f"imobiliarios.")
        out.append(Paragraph(_txt(curric, "Curriculo nao informado."), self.st_corpo))

        out.append(self._hr_fina())
        out += self._subtitulo("20.3 Registros e Habilitacoes")
        regs = []
        for org, chave in [("COFECI — CNAI", 'cnai'), ("CRECI/MA", 'creci'),
                           ("CFT/MA", 'cft'), ("CREA/MA", 'crea'), ("INCRA", 'incra')]:
            if av.get(chave):
                regs.append([org, _txt(av.get(chave)), "Ativo"])
        out.append(self._tabela_header_verde(
            ["Conselho / Orgao", "Registro", "Situacao"], regs,
            [5.0 * cm, 5.0 * cm, 3.0 * cm]))

        out.append(self._hr_grossa())
        out.append(Paragraph(
            "Declaro que as informacoes prestadas neste Parecer Tecnico de Avaliacao Mercadologica "
            "sao verdadeiras, foram elaboradas com base na minha capacidade tecnica e experiencia "
            "profissional, em estrita conformidade com a Resolucao COFECI nº 1.066/2007, NBR 14653 "
            "(ABNT) e demais normas tecnicas aplicaveis. Declaro ainda que nao possuo qualquer "
            "interesse pessoal ou financeiro no imovel avaliando que possa comprometer a "
            "imparcialidade deste parecer.",
            ParagraphStyle('decl', fontName='Helvetica-Oblique', fontSize=9, textColor=CINZA,
                           alignment=TA_JUSTIFY, leading=14, spaceAfter=10)))

        # 20.5 bloco final
        bloco = [
            [Paragraph(_txt(av.get('nome'), ''),
                       ParagraphStyle('bf1', fontName='Helvetica-Bold', fontSize=11,
                                      textColor=VERDE, alignment=TA_CENTER))],
            [Paragraph(_txt(av.get('empresa'), ''),
                       ParagraphStyle('bf2', fontName='Helvetica-Bold', fontSize=9,
                                      textColor=PRETO, alignment=TA_CENTER))],
            [Paragraph(f"{_txt(av.get('endereco'), '')} | CEP {_txt(av.get('cep'), '')}",
                       ParagraphStyle('bf3', fontName='Helvetica', fontSize=8,
                                      textColor=CINZA, alignment=TA_CENTER))],
            [Paragraph(f"{_txt(av.get('telefone'), '')} | {_txt(av.get('email'), '')}",
                       ParagraphStyle('bf4', fontName='Helvetica', fontSize=8,
                                      textColor=CINZA, alignment=TA_CENTER))],
            [Paragraph(f"CNAI {_txt(av.get('cnai'), '')} | CRECI/MA {_txt(av.get('creci'), '')} | "
                       f"CFT/MA {_txt(av.get('cft'), '')} | CREA/MA {_txt(av.get('crea'), '')}",
                       ParagraphStyle('bf5', fontName='Helvetica-Bold', fontSize=8,
                                      textColor=VERDE, alignment=TA_CENTER))],
        ]
        tb = Table(bloco, colWidths=[UTIL_W])
        tb.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), VERDE_CLARO),
            ('BOX', (0, 0), (-1, -1), 0.8, VERDE),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        out.append(Spacer(1, 8))
        out.append(tb)
        return out

    # ── build ────────────────────────────────────────────────────────────────
    def build(self) -> bytes:
        buf = BytesIO()
        doc = _PtamDocTemplate(buf, self.p, pagesize=A4,
                               leftMargin=MARGIN_L, rightMargin=MARGIN_R,
                               topMargin=MARGIN_T, bottomMargin=MARGIN_B,
                               title="PTAM", author=_txt(_g(self.p, 'avaliador', 'nome'), 'Romatec'))
        toc = TableOfContents()

        story = []
        story += self._build_capa()
        story.append(PageBreak())

        secoes = [
            ("1. TIPO DO DOCUMENTO", self._build_secao_01_tipo),
            ("2. FINALIDADE", self._build_secao_02_finalidade),
            ("3. SOLICITANTE", self._build_secao_03_solicitante),
            ("SUMARIO", lambda: self._build_sumario(toc)),
            ("5. OBJETIVO", self._build_secao_05_objetivo),
            ("6. IMOVEL", self._build_secao_06_imovel),
            ("7. REGIAO", self._build_secao_07_regiao),
            ("8. CARACTERIZACAO", self._build_secao_08_caracterizacao),
            ("9. AMOSTRAS", self._build_secao_09_amostras),
            ("10. METODOLOGIA", self._build_secao_10_metodologia),
            ("11. CALCULOS", self._build_secao_11_calculos),
            ("12. PONDERANCIA", self._build_secao_12_ponderancia),
            ("13. DEPRECIACAO", self._build_secao_13_depreciacao),
            ("14. RESULTADO", self._build_secao_14_resultado),
            ("15. CONCLUSAO", self._build_secao_15_conclusao),
            ("16. FOTOS", self._build_secao_16_fotos_imovel),
            ("17. DOCUMENTOS", self._build_secao_17_documentos),
            ("18. TRT/ART", self._build_secao_18_trt_art),
            ("19. TEXTO CONCLUSAO", self._build_secao_19_texto_conclusao),
            ("20. CURRICULO", self._build_secao_20_curriculo),
        ]
        for i, (nome, fn) in enumerate(secoes):
            try:
                story += fn()
            except Exception:
                logger.exception("ptam_pdf_v2: falha na secao %s", nome)
                story.append(Paragraph(f"[Secao {nome} indisponivel neste documento]", self.st_nota))
            if i < len(secoes) - 1:
                story.append(PageBreak())

        # multiBuild para sumario com paginas reais
        try:
            doc.multiBuild(story)
        except Exception:
            logger.exception("ptam_pdf_v2: multiBuild falhou; tentando build simples")
            buf = BytesIO()
            doc = _PtamDocTemplate(buf, self.p, pagesize=A4,
                                   leftMargin=MARGIN_L, rightMargin=MARGIN_R,
                                   topMargin=MARGIN_T, bottomMargin=MARGIN_B)
            doc.build(story)
        return buf.getvalue()


def generate_ptam_pdf_v2(ptam: dict) -> bytes:
    """Ponto de entrada: gera o PDF do PTAM (spec 1.0) e retorna bytes."""
    return PtamPDFGenerator(ptam or {}).build()
