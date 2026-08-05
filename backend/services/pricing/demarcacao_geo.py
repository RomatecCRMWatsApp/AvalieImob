# @module services.pricing.demarcacao_geo — Núcleo geométrico da Demarcação (Pontos & Croqui).
#
# Funções PURAS e testáveis (SPEC-Demarcacao §3). Coordenadas em UTM (metros):
#   distancia_plana / azimute / area_gauss (Shoelace) / perimetro_plano / calcular_lados.
# normalizar_pontos aceita o shape da spec ({vertice, utm_e, utm_n}) E o do geo_urbano
# ({de, coord_e, coord_n}); converte lat/lng → UTM (SIRGAS 2000) via geodesia quando só
# vierem coordenadas geográficas. area/perímetro planos (UTM conforme) batem com o
# memorial em escala de propriedade; a área geodésica (GRS80) fica disponível à parte.
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from services.geo_urbano import geodesia as GEO

_RES_ESTE = ("coord_e", "utm_e", "e", "E", "este", "leste")
_RES_NORTE = ("coord_n", "utm_n", "n", "N", "norte")
_RES_ROTULO = ("de", "vertice", "rotulo", "label", "ponto", "nome")
_RES_LAT = ("lat", "latitude")
_RES_LNG = ("lng", "lon", "long", "longitude")


def _f(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", ".")) if isinstance(v, str) else float(v)
    except (TypeError, ValueError):
        return None


def _first(d: dict, keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _pt(p) -> Tuple[float, float]:
    """(este, norte) de um dict normalizado OU de uma tupla (e, n)."""
    if isinstance(p, dict):
        return (float(p["coord_e"]), float(p["coord_n"]))
    return (float(p[0]), float(p[1]))


# ──────────────────────────────────────────────────────────────────────────────
# Normalização dos pontos
# ──────────────────────────────────────────────────────────────────────────────
def normalizar_pontos(pontos) -> List[dict]:
    """Canoniza os pontos p/ {ordem, de, coord_e, coord_n, latitude, longitude},
    ordenados por `ordem` e reindexados 1..n. Converte lat/lng → UTM se preciso."""
    raw = []
    for i, p in enumerate(pontos or []):
        if not isinstance(p, dict):
            continue
        de = _first(p, _RES_ROTULO) or f"P{i + 1}"
        este = _f(_first(p, _RES_ESTE))
        norte = _f(_first(p, _RES_NORTE))
        lat = GEO.dms_to_dec(_first(p, _RES_LAT))
        lng = GEO.dms_to_dec(_first(p, _RES_LNG))
        try:
            ordem = int(p.get("ordem"))
        except (TypeError, ValueError):
            ordem = i + 1
        if (este is None or norte is None) and lat is not None and lng is not None:
            este, norte, _fu, _he = GEO.geo_para_utm(lng, lat)
        raw.append({"ordem": ordem, "de": str(de), "coord_e": este, "coord_n": norte,
                    "latitude": lat, "longitude": lng})
    raw.sort(key=lambda x: x["ordem"])
    for idx, p in enumerate(raw):
        p["ordem"] = idx + 1
    return raw


def _validos(pontos) -> List[dict]:
    return [p for p in (pontos or [])
            if p.get("coord_e") is not None and p.get("coord_n") is not None]


# ──────────────────────────────────────────────────────────────────────────────
# Geometria plana (UTM)
# ──────────────────────────────────────────────────────────────────────────────
def distancia_plana(a, b) -> float:
    (ax, ay), (bx, by) = _pt(a), _pt(b)
    return math.hypot(bx - ax, by - ay)


def azimute(a, b) -> float:
    """Azimute (graus, [0,360)) — atan2(Δeste, Δnorte). Norte=0, Leste=90."""
    (ax, ay), (bx, by) = _pt(a), _pt(b)
    return math.degrees(math.atan2(bx - ax, by - ay)) % 360.0


def area_gauss(pontos) -> float:
    """Área (m²) por Shoelace (fecha no 1º vértice)."""
    pts = [_pt(p) for p in _validos(pontos)]
    n = len(pts)
    if n < 3:
        return 0.0
    s = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    return abs(s) / 2.0


def perimetro_plano(pontos) -> float:
    pts = _validos(pontos)
    n = len(pts)
    if n < 2:
        return 0.0
    return sum(distancia_plana(pts[i], pts[(i + 1) % n]) for i in range(n))


def calcular_lados(pontos) -> List[dict]:
    """Lados da poligonal (fecha no 1º) com distância e azimute."""
    pts = _validos(pontos)
    n = len(pts)
    lados = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        lados.append({
            "ordem": i + 1, "i_idx": i, "f_idx": (i + 1) % n,
            "vertice_de": a.get("de", f"P{i + 1}"),
            "vertice_para": b.get("de", f"P{(i + 1) % n + 1}"),
            "distancia_m": round(distancia_plana(a, b), 2),
            "azimute": round(azimute(a, b), 2),
        })
    return lados


def extensao_alinhamento(pontos, lados_ordem) -> float:
    """Soma (m) das distâncias dos lados selecionados (ordem 1-based)."""
    sel = {int(o) for o in (lados_ordem or [])}
    if not sel:
        return 0.0
    lados = calcular_lados(normalizar_pontos(pontos))
    return round(sum(l["distancia_m"] for l in lados if l["ordem"] in sel), 2)


def projeto_croqui(pontos, confrontantes=None) -> dict:
    """Monta {"vertices": [...]} pronto p/ croqui_drawing: cada vértice recebe
    `distancia_m` (lado que começa nele) e, se houver, `confrontante_lado`.
    `confrontantes` mapeia ordem (1-based) OU rótulo do vértice → texto."""
    pts = normalizar_pontos(pontos)
    lados = calcular_lados(pts)
    dist_por_idx = {l["i_idx"]: l["distancia_m"] for l in lados}
    conf = confrontantes or {}
    verts = []
    for i, p in enumerate(pts):
        v = dict(p)
        v["distancia_m"] = dist_por_idx.get(i)
        c = conf.get(i + 1) or conf.get(str(i + 1)) or conf.get(p.get("de"))
        if c:
            v["confrontante_lado"] = c
        verts.append(v)
    return {"vertices": verts}


def croqui_svg(pontos, destacar_lados=None, titulo_destaque=None,
               width: float = 520, height: float = 360, confrontantes=None) -> str:
    """SVG (string) da poligonal p/ o preview ao vivo do frontend. '' se <3 vértices."""
    from services.geo_urbano.generators.croqui import croqui_drawing
    proj = projeto_croqui(pontos, confrontantes)
    d = croqui_drawing(proj, width=width, height=height,
                       destacar_lados=destacar_lados, titulo_destaque=titulo_destaque)
    if d is None:
        return ""
    from reportlab.graphics import renderSVG
    return renderSVG.drawToString(d)


def resumo_geometria(pontos) -> dict:
    """Resumo p/ a UI/preview: nº vértices, área (m²/ha), perímetro (m), lados."""
    pts = normalizar_pontos(pontos)
    vs = _validos(pts)
    area = area_gauss(vs)
    return {
        "num_vertices": len(vs),
        "area_m2": round(area, 2),
        "area_ha": round(area / 10000.0, 4),
        "perimetro_m": round(perimetro_plano(vs), 2),
        "lados": calcular_lados(vs),
    }
