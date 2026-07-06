# @module services.georef.geo — Geometria: anel da poligonal, Shapefile SIG-RI, GeoJSON, KML.
#
# Provimento CNJ 195/2025: o arquivo geoespacial enviado ao SIG-RI / Mapa do ONR
# (mapa.onr.org.br) é um Shapefile em SIRGAS 2000 (EPSG:4674). Gera-se também
# GeoJSON (preview no front) e KML (Google Earth) a partir do mesmo anel.
import math
import os
import tempfile
import zipfile
from typing import List, Tuple

SIRGAS2000_PRJ = (
    'GEOGCS["SIRGAS 2000",DATUM["Sistema_de_Referencia_Geocentrico_para_as_'
    'Americas_2000",SPHEROID["GRS 1980",6378137,298.257222101]],PRIMEM["Greenwich",0],'
    'UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4674"]]'
)

_R = 6378137.0  # raio equatorial WGS84/GRS80 (m) — projeção local p/ aferir área


# ──────────────────────────────────────────────────────────────────────────────
# Anel da poligonal
# ──────────────────────────────────────────────────────────────────────────────
def build_ring(vertices: List[dict]) -> List[Tuple[float, float]]:
    """Segue a cadeia 'vante' a partir do 1º vértice e fecha o anel.

    Fallback: se a cadeia quebrar (vante ausente/órfão), usa a ordem da lista.
    """
    pts = [v for v in vertices if v.get("longitude") is not None and v.get("latitude") is not None]
    if not pts:
        return []
    vidx = {v.get("codigo"): v for v in pts}

    ring: List[Tuple[float, float]] = []
    cur = pts[0].get("codigo")
    seen = set()
    while cur and cur in vidx and cur not in seen:
        seen.add(cur)
        v = vidx[cur]
        ring.append((float(v["longitude"]), float(v["latitude"])))
        cur = v.get("vante_codigo")

    # se a cadeia não percorreu todos, cai para a ordem natural
    if len(ring) < len(pts):
        ring = [(float(v["longitude"]), float(v["latitude"])) for v in pts]

    if len(ring) >= 1 and ring[0] != ring[-1]:
        ring.append(ring[0])  # fecha
    return ring


def _orientar_horario(ring: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """ESRI: anel externo no sentido HORÁRIO (shoelace > 0 = horário em x,y geográfico)."""
    if len(ring) < 4:
        return ring
    soma = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        soma += (x2 - x1) * (y2 + y1)
    # soma > 0 => horário; queremos horário
    return ring if soma > 0 else list(reversed(ring))


# ──────────────────────────────────────────────────────────────────────────────
# Área aferida (projeção equiretangular local — sanity check vs SIGEF)
# ──────────────────────────────────────────────────────────────────────────────
def area_perimetro(ring: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Retorna (area_ha, perimetro_m) aproximados via projeção local."""
    if len(ring) < 4:
        return 0.0, 0.0
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    cos0 = math.cos(lat0)

    def proj(p):
        x = math.radians(p[0]) * _R * cos0
        y = math.radians(p[1]) * _R
        return x, y

    xy = [proj(p) for p in ring]
    # shoelace
    area2 = 0.0
    perim = 0.0
    for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
        area2 += x1 * y2 - x2 * y1
        perim += math.hypot(x2 - x1, y2 - y1)
    area_m2 = abs(area2) / 2.0
    return area_m2 / 10000.0, perim


# ──────────────────────────────────────────────────────────────────────────────
# Validação geométrica (shapely)
# ──────────────────────────────────────────────────────────────────────────────
def validar_geometria(vertices: List[dict], area_ha_sigef: float = None,
                      tolerancia: float = 0.01) -> dict:
    """Anel fechado, sem auto-interseção, e área aferida vs SIGEF (tolerância 1%)."""
    avisos: List[str] = []
    ring = build_ring(vertices)
    if len(ring) < 4:
        return {"ok": False, "fechado": False, "simples": False,
                "area_calc_ha": 0.0, "divergencia_pct": None,
                "avisos": ["Vértices insuficientes para formar uma poligonal (mínimo 3)."]}

    fechado = ring[0] == ring[-1]
    if not fechado:
        avisos.append("Poligonal não fechada (primeiro ≠ último vértice).")

    simples = True
    try:
        from shapely.geometry import Polygon
        poly = Polygon(ring)
        simples = bool(poly.is_valid)
        if not simples:
            avisos.append("Poligonal inválida (auto-interseção detectada).")
    except Exception as e:  # noqa: BLE001
        avisos.append(f"Não foi possível validar a geometria via shapely ({e}).")

    area_calc, _perim = area_perimetro(ring)
    divergencia = None
    if area_ha_sigef:
        try:
            divergencia = abs(area_calc - float(area_ha_sigef)) / float(area_ha_sigef)
            if divergencia > tolerancia:
                avisos.append(
                    f"Área aferida ({area_calc:.4f} ha) diverge {divergencia * 100:.2f}% "
                    f"da área do SIGEF ({float(area_ha_sigef):.4f} ha)."
                )
        except (ValueError, ZeroDivisionError):
            divergencia = None

    ok = fechado and simples and (divergencia is None or divergencia <= tolerancia)
    return {
        "ok": ok, "fechado": fechado, "simples": simples,
        "area_calc_ha": round(area_calc, 4),
        "divergencia_pct": round(divergencia * 100, 4) if divergencia is not None else None,
        "avisos": avisos,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GeoJSON (preview no mapa do front)
# ──────────────────────────────────────────────────────────────────────────────
def gerar_geojson(projeto: dict) -> dict:
    im = projeto.get("imovel") or {}
    ring = build_ring(projeto.get("vertices") or [])
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "denominacao": im.get("denominacao"),
                "matricula": im.get("matricula"),
                "cod_incra": im.get("cod_incra"),
                "area_ha": im.get("area_ha"),
                "proprietario": im.get("proprietario_nome"),
            },
            "geometry": {"type": "Polygon", "coordinates": [[[x, y] for (x, y) in ring]]},
        }],
    }


def gerar_kml(projeto: dict) -> str:
    im = projeto.get("imovel") or {}
    ring = build_ring(projeto.get("vertices") or [])
    coords = " ".join(f"{x},{y},0" for (x, y) in ring)
    nome = (im.get("denominacao") or "Imóvel").replace("&", "e")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n'
        f"<Placemark><name>{nome}</name><Polygon><outerBoundaryIs><LinearRing>\n"
        f"<coordinates>{coords}</coordinates>\n"
        "</LinearRing></outerBoundaryIs></Polygon></Placemark>\n"
        "</Document></kml>\n"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Shapefile SIG-RI / ONR (Provimento 195/2025) — .zip SIRGAS 2000
# ──────────────────────────────────────────────────────────────────────────────
_FIELDS = [
    ("MATRICULA", "C", 20, 0), ("DENOM", "C", 100, 0), ("PROPRIET", "C", 100, 0),
    ("CPF_CNPJ", "C", 20, 0), ("COD_INCRA", "C", 20, 0), ("CNS", "C", 20, 0),
    ("AREA_HA", "N", 18, 4), ("PERIM_M", "N", 18, 2), ("SGEODESIC", "C", 20, 0),
    ("CERT_SIGEF", "C", 50, 0), ("MUNICIPIO", "C", 60, 0), ("UF", "C", 2, 0),
]


def _slug_parcela(parc: dict, idx: int) -> str:
    rot = parc.get("rotulo") or ("ParteI" if parc.get("principal") else f"Parte{idx + 1}")
    slug = "".join(ch for ch in str(rot) if ch.isalnum())
    return slug or f"P{idx + 1}"


def _escrever_shapefile(base: str, im: dict, parc: dict, ring) -> None:
    """Escreve um conjunto shp/shx/dbf/prj (1 polígono) em `base` (sem extensão)."""
    import shapefile  # pyshp
    w = shapefile.Writer(base, shapeType=shapefile.POLYGON)
    for f, t, sz, dec in _FIELDS:
        w.field(f, t, sz, dec)
    w.poly([[list(p) for p in ring]])
    w.record(
        str(im.get("matricula") or ""), (parc.get("denominacao") or "")[:100],
        (im.get("proprietario_nome") or "")[:100], str(im.get("proprietario_cpf_cnpj") or ""),
        str(im.get("cod_incra") or ""), str(im.get("cartorio_cns") or ""),
        float(parc.get("area_ha") or 0), float(parc.get("perimetro_m") or 0),
        "SIRGAS2000", str(parc.get("certificacao_sigef") or ""),
        (im.get("municipio") or "")[:60], str(im.get("uf") or "")[:2],
    )
    w.close()
    with open(base + ".prj", "w", encoding="utf-8") as fh:
        fh.write(SIRGAS2000_PRJ)


def gerar_shapefile_bytes(projeto: dict) -> bytes:
    """Gera o(s) Shapefile(s) SIG-RI (.shp/.shx/.dbf/.prj) zipados, SIRGAS 2000/EPSG:4674.

    DESMEMBRAMENTO (2+ parcelas resultantes): UM shapefile POR PARCELA no .zip
    (cada parcela vira uma matrícula própria no RI). Imóvel único/remembramento
    (unificação): um único shapefile.
    """
    from services.georef.parcelas import parcelas_do_projeto

    im = projeto.get("imovel") or {}
    parcelas = parcelas_do_projeto(projeto)
    aneis = [(p, _orientar_horario(build_ring(p.get("vertices") or []))) for p in parcelas]
    aneis = [(p, r) for (p, r) in aneis if len(r) >= 4]
    if not aneis:
        raise ValueError("Poligonal insuficiente para gerar shapefile (mínimo 3 vértices).")

    tmp = tempfile.mkdtemp(prefix="sigri_")
    matbase = f"SIGRI_{(im.get('matricula') or 'sn')}".replace("/", "_")
    multi = len(aneis) > 1                     # desmembramento → 1 shapefile por parcela
    bases = []
    for idx, (parc, ring) in enumerate(aneis):
        nome = f"{matbase}_{_slug_parcela(parc, idx)}" if multi else matbase
        base = os.path.join(tmp, nome)
        _escrever_shapefile(base, im, parc, ring)
        bases.append(base)

    import io as _io
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for base in bases:
            for ext in ("shp", "shx", "dbf", "prj"):
                caminho = base + f".{ext}"
                if os.path.exists(caminho):
                    z.write(caminho, arcname=os.path.basename(base) + f".{ext}")
    return buf.getvalue()
