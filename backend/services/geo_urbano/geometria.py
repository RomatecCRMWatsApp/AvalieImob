# @module services.geo_urbano.geometria — área/perímetro e polígono (UTM N/E).
#
# A planilha do mapa de remembramento traz vértices em UTM (SIRGAS 2000 / fuso 23S):
# Coord. N (Y) e Coord. E (X) em metros. Em coordenadas projetadas o cálculo de
# área (shoelace) e perímetro é DIRETO (metros), sem aproximação geográfica.
from __future__ import annotations

from typing import List, Tuple

# Tolerância (1%) entre a área calculada do polígono e a área declarada (soma
# registral). Acima disso → aviso de divergência (não bloqueia).
TOLERANCIA_AREA = 0.01


def _anel(vertices: List[dict]) -> List[Tuple[float, float]]:
    """Sequência (E, N) dos vértices ordenados; fecha o anel."""
    ordenados = sorted(
        (v for v in (vertices or []) if v.get("coord_e") is not None and v.get("coord_n") is not None),
        key=lambda v: v.get("ordem", 0),
    )
    anel = [(float(v["coord_e"]), float(v["coord_n"])) for v in ordenados]
    if len(anel) >= 3 and anel[0] != anel[-1]:
        anel.append(anel[0])
    return anel


def area_m2(vertices: List[dict]) -> float:
    """Área do polígono (shoelace, UTM) em m². 0 se < 3 vértices."""
    anel = _anel(vertices)
    if len(anel) < 4:
        return 0.0
    soma = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:]):
        soma += x1 * y2 - x2 * y1
    return abs(soma) / 2.0


def perimetro_m(vertices: List[dict]) -> float:
    """Perímetro: soma das distâncias da planilha (fallback: dist. euclidiana)."""
    dists = [float(v["distancia_m"]) for v in (vertices or []) if v.get("distancia_m")]
    if dists:
        return round(sum(dists), 2)
    anel = _anel(vertices)
    total = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:]):
        total += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    return round(total, 2)


def conferencia_areas(vertices: List[dict], area_declarada: float | None) -> dict:
    """Compara área calculada × declarada. Retorna {area_calc, divergencia_pct, ok, aviso}."""
    calc = area_m2(vertices)
    out = {"area_calculada_m2": round(calc, 2), "perimetro_m": perimetro_m(vertices),
           "divergencia_pct": None, "ok": True, "aviso": None}
    if area_declarada and calc:
        div = abs(calc - float(area_declarada)) / float(area_declarada)
        out["divergencia_pct"] = round(div * 100, 3)
        if div > TOLERANCIA_AREA:
            out["ok"] = False
            out["aviso"] = (
                f"Área calculada ({calc:.2f} m²) diverge da declarada "
                f"({float(area_declarada):.2f} m²) em {div*100:.2f}% — conferir a poligonal."
            )
    return out


def conservacao_area(projeto: dict) -> dict:
    """Desdobro: Σ(lotes resultantes) + via/doação deve fechar com a área-mãe (tol. 0,5 m²)."""
    lotes = projeto.get("lotes_resultantes") or []
    soma = sum(float(l.get("area_declarada_m2") or 0) for l in lotes)
    via = float(projeto.get("area_via_doacao_m2") or 0)
    mae = float(projeto.get("area_mae_m2") or 0)
    total = soma + via
    out = {"soma_resultantes_m2": round(soma, 2), "via_doacao_m2": round(via, 2),
           "total_m2": round(total, 2), "area_mae_m2": round(mae, 2),
           "qtd_lotes": len(lotes), "ok": True, "divergencia_m2": None, "aviso": None,
           "modalidade": "desmembramento" if via > 0 else "desdobro"}
    if mae and lotes:
        div = abs(total - mae)
        out["divergencia_m2"] = round(div, 2)
        if div > 0.5:
            out["ok"] = False
            out["aviso"] = (f"A soma das áreas ({total:.2f} m²) não fecha com a matrícula-mãe "
                            f"({mae:.2f} m²) — diferença de {div:.2f} m².")
    return out


def validacoes_urbanisticas(projeto: dict) -> list:
    """Avisos (não bloqueiam): lote abaixo do mínimo municipal / testada mínima."""
    avisos = []
    minA = projeto.get("lote_minimo_municipal_m2")
    minT = projeto.get("testada_minima_m")
    for l in projeto.get("lotes_resultantes") or []:
        nome = l.get("denominacao") or f"Lote {l.get('ordem')}"
        a = l.get("area_declarada_m2")
        if minA and a and float(a) < float(minA):
            avisos.append({"tipo": "lote_abaixo_do_minimo", "severidade": "alerta", "lote": nome,
                           "mensagem": f"{nome}: área {a:.2f} m² abaixo do mínimo municipal ({float(minA):.2f} m²)."})
        frente = next((c.get("medida_m") for c in (l.get("confrontacoes") or [])
                       if (c.get("lado") or "").lower() == "frente"), None)
        if minT and frente and float(frente) < float(minT):
            avisos.append({"tipo": "testada_abaixo_do_minimo", "severidade": "alerta", "lote": nome,
                           "mensagem": f"{nome}: testada {frente:.2f} m abaixo do mínimo ({float(minT):.2f} m)."})
    return avisos


def poligono_geojson(projeto: dict) -> dict:
    """GeoJSON do polígono resultante (UTM como coordenadas — para preview SVG)."""
    anel = _anel(projeto.get("vertices") or [])
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "denominacao": projeto.get("denominacao_imovel"),
                "area_m2": area_m2(projeto.get("vertices") or []),
                "perimetro_m": perimetro_m(projeto.get("vertices") or []),
                "cmi": projeto.get("cmi_resultante"),
            },
            "geometry": {"type": "Polygon", "coordinates": [anel]} if len(anel) >= 4 else None,
        }],
    }
