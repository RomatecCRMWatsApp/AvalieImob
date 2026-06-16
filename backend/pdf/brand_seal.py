"""Selo da marca AvalieImob (monograma 'A') para os laudos PTAM.

O 'A' é 100% poligonal (sem curvas) → desenha direto com Path + preenchimento
even-odd (o contra-forma vira furo). A origem do ReportLab é o canto inferior-
esquerdo e Y cresce para cima — a função converte do espaço SVG (1024, Y p/ baixo).
"""
from reportlab.pdfgen.canvas import Canvas, FILL_EVEN_ODD

_GREEN = (12 / 255, 51 / 255, 32 / 255)    # #0C3320
_GOLD = (184 / 255, 134 / 255, 11 / 255)   # #B8860B
_A_OUTER = [(512, 222), (805, 802), (654, 802), (512, 498), (370, 802), (219, 802)]
_A_COUNTER = [(512, 372), (575, 478), (449, 478)]
# Atenção: no ReportLab FILL_EVEN_ODD == 0 e FILL_NON_ZERO == 1 (invertido do que
# parece). Sempre usar a constante importada, nunca o literal.


def draw_brand_seal(c: Canvas, x: float, y: float, size: float, ring: bool = True) -> None:
    """Desenha o selo 'A' com canto inferior-esquerdo em (x, y) e lado `size` (pt).

    ring=True envolve o 'A' num anel dourado (selo de autenticidade no rodapé/capa).
    """
    def to_page(sx, sy):
        return (x + (sx / 1024.0) * size, y + (1.0 - sy / 1024.0) * size)

    scale = 0.78 if ring else 1.0

    def scaled(sx, sy):
        return (512 + (sx - 512) * scale, 512 + (sy - 512) * scale)

    c.saveState()

    if ring:
        cx, cy = to_page(512, 512)
        c.setStrokeColorRGB(*_GOLD)
        c.setLineWidth(size * 0.028)
        c.circle(cx, cy, size * 0.485, stroke=1, fill=0)

    path = c.beginPath()
    outer = [to_page(*scaled(*p)) for p in _A_OUTER]
    path.moveTo(*outer[0])
    for px, py in outer[1:]:
        path.lineTo(px, py)
    path.close()

    counter = [to_page(*scaled(*p)) for p in _A_COUNTER]
    path.moveTo(*counter[0])
    for px, py in counter[1:]:
        path.lineTo(px, py)
    path.close()

    c.setFillColorRGB(*_GREEN)
    c.drawPath(path, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)
    c.restoreState()
