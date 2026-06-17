"""Marca AvalieImob (monograma 'A') para os laudos PTAM — ReportLab.

3 brasões derivados do mesmo "A" (furo even-odd):
  - draw_brand_badge / draw_cover_lockup  → CAPA (badge + AvalieImob + tagline)
  - draw_header_monogram                  → CABEÇALHO (monograma-letra)
  - draw_brand_seal / draw_avaliador_seal → RODAPÉ / assinatura (selo de avaliador)

Atenção: no ReportLab FILL_EVEN_ODD == 0 e FILL_NON_ZERO == 1 (invertido do que
parece). Sempre usar a constante importada, nunca o literal.
"""
from reportlab.pdfgen.canvas import Canvas, FILL_EVEN_ODD
from reportlab.lib.units import mm

_GREEN = (12 / 255, 51 / 255, 32 / 255)    # #0C3320
_GOLD = (184 / 255, 134 / 255, 11 / 255)   # #B8860B
_GRAY = (0.42, 0.42, 0.40)
_A_OUTER = [(512, 222), (805, 802), (654, 802), (512, 498), (370, 802), (219, 802)]
_A_COUNTER = [(512, 372), (575, 478), (449, 478)]


def _draw_A(c, x, y, size, scale=1.0, color=_GREEN):
    """Desenha o 'A' (furo even-odd) no quadro (x,y)-(x+size,y+size)."""
    def P(sx, sy):
        return (x + (sx / 1024.0) * size, y + (1.0 - sy / 1024.0) * size)

    def S(sx, sy):
        return (512 + (sx - 512) * scale, 512 + (sy - 512) * scale)

    p = c.beginPath()
    outer = [P(*S(*pt)) for pt in _A_OUTER]
    p.moveTo(*outer[0])
    for px, py in outer[1:]:
        p.lineTo(px, py)
    p.close()
    ctr = [P(*S(*pt)) for pt in _A_COUNTER]
    p.moveTo(*ctr[0])
    for px, py in ctr[1:]:
        p.lineTo(px, py)
    p.close()
    c.setFillColorRGB(*color)
    c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)


def draw_brand_seal(c, x, y, size, ring=True):
    """Selo 'A' (anel dourado + A verde). Canto inferior-esquerdo em (x, y)."""
    c.saveState()
    if ring:
        cx, cy = x + size / 2, y + size / 2
        c.setStrokeColorRGB(*_GOLD)
        c.setLineWidth(size * 0.028)
        c.circle(cx, cy, size * 0.485, stroke=1, fill=0)
        _draw_A(c, x, y, size, scale=0.78)
    else:
        _draw_A(c, x, y, size, scale=1.0)
    c.restoreState()


def draw_brand_badge(c, x, y, size):
    """Badge: quadrado dourado arredondado + 'A' verde (igual ao ícone do app)."""
    c.saveState()
    c.setFillColorRGB(*_GOLD)
    c.roundRect(x, y, size, size, size * 0.22, stroke=0, fill=1)
    _draw_A(c, x, y, size, scale=1.0)   # furo do A revela o dourado do badge
    c.restoreState()


def draw_cover_lockup(c, center_x, top_y, badge=16 * mm,
                      word_font="Helvetica-Bold", tag_font="Helvetica"):
    """CAPA: badge centralizado + 'AvalieImob' + tagline."""
    c.saveState()
    bx = center_x - badge / 2
    draw_brand_badge(c, bx, top_y - badge, badge)
    c.setFillColorRGB(*_GREEN)
    c.setFont(word_font, 19)
    c.drawCentredString(center_x, top_y - badge - 8 * mm, "AvalieImob")
    c.setFillColorRGB(*_GRAY)
    c.setFont(tag_font, 8)
    c.drawCentredString(center_x, top_y - badge - 12.5 * mm,
                        "ROMATEC  ·  PTAM  ·  LAUDOS")
    c.restoreState()


def draw_header_monogram(c, x, y_base, fs=13,
                         word_font="Helvetica-Bold", tag_font="Helvetica"):
    """CABEÇALHO: monograma como letra ('A' glyph + 'valieImob')."""
    c.saveState()
    s = fs * 1.24
    gy = y_base - 0.217 * s
    _draw_A(c, x, gy, s, scale=1.0, color=_GREEN)
    tx = x + s * 0.80
    c.setFillColorRGB(*_GREEN)
    c.setFont(word_font, fs)
    c.drawString(tx, y_base, "valieImob")
    c.setFillColorRGB(*_GRAY)
    c.setFont(tag_font, 6.5)
    c.drawString(x, y_base - 4.2 * mm, "Avaliação imobiliária · NBR 14.653")
    c.restoreState()


def draw_header_lockup(c, x, y_center, mark=11 * mm, light=False,
                       tagline="PTAM · LAUDOS",
                       word_font="Helvetica-Bold", tag_font="Helvetica"):
    """Brasão pequeno horizontal: badge + nome. light=True p/ faixa escura/verde."""
    c.saveState()
    draw_brand_badge(c, x, y_center - mark / 2, mark)
    tx = x + mark + 3 * mm
    word_c = (1, 1, 1) if light else _GREEN
    tag_c = (0.86, 0.86, 0.84) if light else _GRAY
    c.setFillColorRGB(*word_c)
    c.setFont(word_font, 12)
    c.drawString(tx, y_center + 0.6 * mm, "AvalieImob")
    c.setFillColorRGB(*tag_c)
    c.setFont(tag_font, 6.5)
    c.drawString(tx, y_center - 3.2 * mm, tagline)
    c.restoreState()


def draw_avaliador_seal(c, x, y_center, seal=14 * mm, rule_w=62 * mm,
                        word_font="Helvetica-Bold", tag_font="Helvetica",
                        credenciais="CNAI 031161 · NBR 14.653 · ICP-Brasil"):
    """RODAPÉ: selo de avaliador (selo + nome + régua + credenciais)."""
    c.saveState()
    draw_brand_seal(c, x, y_center - seal / 2, seal, ring=True)
    tx = x + seal + 3.5 * mm
    c.setFillColorRGB(*_GREEN)
    c.setFont(word_font, 11)
    c.drawString(tx, y_center + 1.6 * mm, "AvalieImob")
    c.setStrokeColorRGB(*_GOLD)
    c.setLineWidth(0.7)
    c.line(tx, y_center - 0.4 * mm, tx + rule_w, y_center - 0.4 * mm)
    c.setFillColorRGB(*_GRAY)
    c.setFont(tag_font, 7)
    c.drawString(tx, y_center - 4.2 * mm, credenciais)
    c.restoreState()
