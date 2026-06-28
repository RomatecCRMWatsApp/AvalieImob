# @module services.geo_urbano.generators.croqui — croqui (desenho da poligonal).
#
# Desenho VETORIAL (ReportLab graphics) da poligonal resultante — vértices,
# medidas e confrontantes — embutido no Requerimento E no Memorial. Vetorial p/
# não depender de fontes externas no container (usa Helvetica embutida).
from __future__ import annotations

from reportlab.graphics.shapes import Drawing, Polygon, Circle, String, Line
from reportlab.lib.colors import HexColor, black, white

from services.geo_urbano.generators import textos as TX

_GREEN = HexColor("#0C3320")
_FILL = HexColor("#E8F0E8")
_RED = HexColor("#B23B2E")
_GRAY = HexColor("#555555")


def _verts(projeto):
    vs = [v for v in (projeto.get("vertices") or [])
          if v.get("coord_e") is not None and v.get("coord_n") is not None]
    return sorted(vs, key=lambda v: v.get("ordem", 0))


def croqui_drawing(projeto: dict, width: float = 460, height: float = 340):
    """Drawing (Flowable) da poligonal; None se faltarem vértices."""
    verts = _verts(projeto)
    if len(verts) < 3:
        return None
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
                  strokeColor=_GREEN, strokeWidth=1.2))

    # medidas + confrontante por aresta — rótulo no MEIO da aresta, deslocado pela
    # NORMAL da própria aresta (para fora), de modo que cada cota fique sobre o seu
    # segmento (corrige o desalinhamento do offset por centroide na poligonal em "L").
    for i, v in enumerate(verts):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ex, ey = b[0] - a[0], b[1] - a[1]
        eln = (ex * ex + ey * ey) ** 0.5 or 1
        nx, ny = -ey / eln, ex / eln                 # normal à aresta
        if nx * (mx - cx) + ny * (my - cy) < 0:      # garante apontar p/ FORA
            nx, ny = -nx, -ny
        lx, ly = mx + nx * 12, my + ny * 12
        if v.get("distancia_m") is not None:
            d.add(String(lx, ly, f"{TX._n_br(v.get('distancia_m'))} m",
                         fontSize=6.6, fillColor=black, textAnchor="middle"))
        conf = v.get("confrontante_lado")
        if conf:
            d.add(String(lx, ly - 8, conf[:26],
                         fontSize=5.6, fillColor=_GRAY, textAnchor="middle"))

    # vértices + rótulo (PDN1..) para fora
    for p, v in zip(pts, verts):
        d.add(Circle(p[0], p[1], 2.6, fillColor=_RED, strokeColor=white, strokeWidth=0.6))
        dx, dy = p[0] - cx, p[1] - cy
        ln = (dx * dx + dy * dy) ** 0.5 or 1
        nome = (v.get("de") or "").split("-")[-1]
        d.add(String(p[0] + dx / ln * 13, p[1] + dy / ln * 13 - 3, nome,
                     fontSize=7, fillColor=_GREEN, textAnchor="middle"))

    # rosa dos ventos (N) no canto superior direito
    d.add(Line(width - 22, height - 14, width - 22, height - 34, strokeColor=black, strokeWidth=1.2))
    d.add(Polygon(points=[width - 22, height - 10, width - 25, height - 17, width - 19, height - 17],
                  fillColor=black, strokeColor=black))
    d.add(String(width - 22, height - 45, "N", fontSize=7, fillColor=black, textAnchor="middle"))
    return d
