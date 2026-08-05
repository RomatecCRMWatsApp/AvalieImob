# @module services.geo_urbano.generators.croqui — croqui (desenho da poligonal).
#
# Desenho VETORIAL (ReportLab graphics) da poligonal resultante — vértices,
# medidas e confrontantes — embutido no Requerimento E no Memorial. Vetorial p/
# não depender de fontes externas no container (usa Helvetica embutida).
from __future__ import annotations

import math

from reportlab.graphics.shapes import Drawing, Polygon, Circle, String, Line, Group
from reportlab.lib.colors import HexColor, black, white

from services.geo_urbano.generators import textos as TX

_GREEN = HexColor("#0C3320")
_FILL = HexColor("#E8F0E8")
_RED = HexColor("#B23B2E")
_GRAY = HexColor("#555555")
_GOLD = HexColor("#C9A84C")       # destaque de alinhamento de cerca
_BASEGRAY = HexColor("#6e7681")   # poligonal base rebaixada quando há destaque


def _verts(projeto):
    vs = [v for v in (projeto.get("vertices") or [])
          if v.get("coord_e") is not None and v.get("coord_n") is not None]
    return sorted(vs, key=lambda v: v.get("ordem", 0))


def croqui_drawing(projeto: dict, width: float = 460, height: float = 340,
                   destacar_lados=None, titulo_destaque=None):
    """Drawing (Flowable) da poligonal; None se faltarem vértices.

    destacar_lados: lista de lados (ORDEM 1-based) a destacar como cerca a alinhar —
    tracejado dourado, cota "(ALINHAR)", poligonal base rebaixada a cinza + legenda.
    Sem destacar_lados a saída é IDÊNTICA ao croqui normal (não quebra o laudo)."""
    verts = _verts(projeto)
    if len(verts) < 3:
        return None
    destac = {int(o) for o in (destacar_lados or [])}
    xs = [float(v["coord_e"]) for v in verts]
    ys = [float(v["coord_n"]) for v in verts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    pad = 48
    s = min((width - 2 * pad) / ((maxx - minx) or 1), (height - 2 * pad) / ((maxy - miny) or 1))
    ox = (width - (maxx - minx) * s) / 2
    oy = (height - (maxy - miny) * s) / 2

    def T(x, y):
        return (ox + (x - minx) * s, oy + (y - miny) * s)  # ReportLab: y para cima

    pts = [T(float(v["coord_e"]), float(v["coord_n"])) for v in verts]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)

    d = Drawing(width, height)
    d.hAlign = "CENTER"
    d.add(Polygon(points=[c for p in pts for c in p], fillColor=_FILL,
                  strokeColor=(_BASEGRAY if destac else _GREEN), strokeWidth=1.2))

    # orientação do polígono (shoelace) p/ achar o lado EXTERNO de cada aresta mesmo
    # em poligonal CÔNCAVA ("L") — o offset por centroide jogava rótulos para dentro.
    area2 = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                for i in range(len(pts)))
    ccw = area2 > 0
    # medidas + confrontante por aresta — rótulo no MEIO da aresta, deslocado pela
    # NORMAL EXTERNA E ROTACIONADO para acompanhar a direção do segmento (azimute).
    total_alinhar = 0.0
    for i, v in enumerate(verts):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        destacado = (i + 1) in destac
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ex, ey = b[0] - a[0], b[1] - a[1]
        eln = (ex * ex + ey * ey) ** 0.5 or 1
        nx, ny = (ey / eln, -ex / eln) if ccw else (-ey / eln, ex / eln)   # normal EXTERNA
        lx, ly = mx + nx * 14, my + ny * 14
        ang = math.degrees(math.atan2(ey, ex))
        if ang > 90 or ang < -90:                    # mantém o texto "para cima"
            ang += 180
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        g = Group(transform=(ca, sa, -sa, ca, lx, ly))   # rotaciona em torno do ponto
        if v.get("distancia_m") is not None:
            if destacado:
                g.add(String(0, 2.0, f"{TX._n_br(v.get('distancia_m'))} m (ALINHAR)",
                             fontSize=7.0, fillColor=_GOLD, fontName="Helvetica-Bold",
                             textAnchor="middle"))
            else:
                g.add(String(0, 2.0, f"{TX._n_br(v.get('distancia_m'))} m",
                             fontSize=6.6, fillColor=black, textAnchor="middle"))
        conf = v.get("confrontante_lado")
        if conf:
            g.add(String(0, -6.5, conf[:26],
                         fontSize=5.6, fillColor=_GRAY, textAnchor="middle"))
        d.add(g)
        if destacado:
            d.add(Line(a[0], a[1], b[0], b[1], strokeColor=_GOLD, strokeWidth=4,
                       strokeDashArray=[8, 4]))
            total_alinhar += float(v.get("distancia_m") or 0)

    # vértices + rótulo FIEL (código INCRA completo, igual à tabela e ao Memorial) p/ fora
    for p, v in zip(pts, verts):
        d.add(Circle(p[0], p[1], 2.6, fillColor=_RED, strokeColor=white, strokeWidth=0.6))
        dx, dy = p[0] - cx, p[1] - cy
        ln = (dx * dx + dy * dy) ** 0.5 or 1
        nome = v.get("de") or ""
        d.add(String(p[0] + dx / ln * 15, p[1] + dy / ln * 15 - 3, nome,
                     fontSize=6.2, fillColor=_GREEN, textAnchor="middle"))

    # rosa dos ventos (N) no canto superior direito
    d.add(Line(width - 22, height - 14, width - 22, height - 34, strokeColor=black, strokeWidth=1.2))
    d.add(Polygon(points=[width - 22, height - 10, width - 25, height - 17, width - 19, height - 17],
                  fillColor=black, strokeColor=black))
    d.add(String(width - 22, height - 45, "N", fontSize=7, fillColor=black, textAnchor="middle"))

    # destaque de alinhamento: título (topo) + legenda com a extensão total (rodapé)
    if destac:
        if titulo_destaque:
            d.add(String(6, height - 12, str(titulo_destaque)[:48], fontSize=8,
                         fillColor=_GOLD, fontName="Helvetica-Bold", textAnchor="start"))
        d.add(String(6, 8, f"Cerca a ser alinhada — total: {TX._n_br(round(total_alinhar, 2))} m",
                     fontSize=7, fillColor=_GOLD, textAnchor="start"))
    return d
