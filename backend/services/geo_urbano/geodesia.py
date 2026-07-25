# @module services.geo_urbano.geodesia — Motor geodésico do SIG-RI/ONR (urbano).
#
# Provimento CNJ 195/2025 + ABNT NBR 17047:2022. Sistema geodésico de referência
# FIXO: SIRGAS 2000 (geográfico EPSG:4674). Este módulo:
#   • deriva fuso/MC/hemisfério da poligonal;
#   • converte UTM SIRGAS 2000 ↔ geodésica (pyproj);
#   • calcula ÁREA e PERÍMETRO GEODÉSICOS (elipsoide GRS80) — nunca planos,
#     evitando a divergência com o memorial (tolerância 0,5%);
#   • monta o anel (lon, lat) de um conjunto de vértices, aceitando Latitude/
#     Longitude (DMS) OU coordenadas UTM (coord_e/coord_n) quando o lat/long
#     não vem na planta.
#
# pyproj traz o PROJ empacotado nos wheels (sem dependência de sistema).
from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple

# Reusa o orientador horário (praxe ESRI/SIGEF) já validado no georef rural.
from services.georef.geo import _orientar_horario

# EPSG geográfico do SGR brasileiro (Resolução PR/IBGE 1/2015).
EPSG_SIRGAS2000_GEO = 4674

_GRS80 = None          # Geod lazy (GRS80 = elipsoide do SIRGAS 2000)
_TRANSFORMERS: dict = {}


def _geod():
    global _GRS80
    if _GRS80 is None:
        from pyproj import Geod
        _GRS80 = Geod(ellps="GRS80")
    return _GRS80


def _transformer(epsg_src: int, epsg_dst: int):
    chave = (epsg_src, epsg_dst)
    t = _TRANSFORMERS.get(chave)
    if t is None:
        from pyproj import Transformer
        # always_xy=True → ordem (x=lon/este, y=lat/norte)
        t = Transformer.from_crs(epsg_src, epsg_dst, always_xy=True)
        _TRANSFORMERS[chave] = t
    return t


# ──────────────────────────────────────────────────────────────────────────────
# Fuso / Meridiano Central / EPSG UTM SIRGAS 2000
# ──────────────────────────────────────────────────────────────────────────────
def fuso_de_longitude(lon: float) -> int:
    """Fuso UTM (1–60) a partir da longitude (graus decimais)."""
    return int(math.floor((float(lon) + 180.0) / 6.0)) + 1


def mc_de_fuso(fuso: int) -> int:
    """Meridiano central do fuso (ex.: fuso 23 → -45)."""
    return -183 + 6 * int(fuso)


def epsg_utm(fuso: int, hemisferio: str) -> int:
    """EPSG do UTM SIRGAS 2000. Sul 17S–25S → 31977–31985; Norte 18N–22N → 31972–31976."""
    fuso = int(fuso)
    h = (hemisferio or "S").strip().upper()[:1]
    if h == "N":
        return 31972 + (fuso - 18)   # 18N=31972 … 22N=31976
    return 31977 + (fuso - 17)       # 17S=31977 … 25S=31985


# ──────────────────────────────────────────────────────────────────────────────
# Conversões UTM ↔ geodésica
# ──────────────────────────────────────────────────────────────────────────────
def utm_para_geo(este: float, norte: float, fuso: int, hemisferio: str) -> Tuple[float, float]:
    """(Este X, Norte Y) UTM SIRGAS 2000 → (lon, lat) EPSG:4674."""
    lon, lat = _transformer(epsg_utm(fuso, hemisferio), EPSG_SIRGAS2000_GEO).transform(
        float(este), float(norte))
    return lon, lat


def geo_para_utm(lon: float, lat: float, fuso: Optional[int] = None,
                 hemisferio: Optional[str] = None) -> Tuple[float, float, int, str]:
    """(lon, lat) → (Este, Norte, fuso, hemisfério). Deriva fuso/hemisfério se ausentes."""
    if fuso is None:
        fuso = fuso_de_longitude(lon)
    if hemisferio is None:
        hemisferio = "S" if float(lat) < 0 else "N"
    este, norte = _transformer(EPSG_SIRGAS2000_GEO, epsg_utm(fuso, hemisferio)).transform(
        float(lon), float(lat))
    return este, norte, int(fuso), hemisferio


# ──────────────────────────────────────────────────────────────────────────────
# DMS → decimal (Latitude/Longitude das plantas: 04°56'15,475979"S)
# ──────────────────────────────────────────────────────────────────────────────
def dms_to_dec(s) -> Optional[float]:
    """'04°56'15,475979\"S' / '47°27'59,462032\"W/O' → decimal (S/W/O negativos)."""
    if s is None or s == "":
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    neg = bool(re.search(r"[SWOsw o]\s*$", s)) or s.lstrip().startswith("-")
    nums = re.findall(r"\d+(?:[.,]\d+)?", s)
    if not nums:
        return None
    g = float(nums[0].replace(",", "."))
    m = float(nums[1].replace(",", ".")) if len(nums) > 1 else 0.0
    sec = float(nums[2].replace(",", ".")) if len(nums) > 2 else 0.0
    dec = g + m / 60.0 + sec / 3600.0
    return -dec if neg else dec


# ──────────────────────────────────────────────────────────────────────────────
# Anel (lon, lat) a partir dos vértices — lat/long OU UTM
# ──────────────────────────────────────────────────────────────────────────────
def _fechar(ring: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    ring = [p for i, p in enumerate(ring) if i == 0 or p != ring[i - 1]]  # tira duplicados consecutivos
    if len(ring) >= 3 and ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def pontos_lonlat(vertices, fuso: Optional[int] = None, hemisferio: Optional[str] = None
                  ) -> Tuple[List[Tuple[float, float]], Optional[int], Optional[str]]:
    """Pontos (lon, lat) BRUTOS na ordem dos vértices (SEM dedup/fechamento) +
    (fuso, hemisfério). Prioriza Latitude/Longitude (DMS); se ausente, converte
    UTM (coord_e/coord_n) — caminho UTM usa fuso/hemisfério (default 23 Sul)."""
    verts = sorted((v for v in (vertices or []) if isinstance(v, dict)),
                   key=lambda v: v.get("ordem", 0))

    latlon = []
    for v in verts:
        lat, lon = dms_to_dec(v.get("latitude")), dms_to_dec(v.get("longitude"))
        if lat is not None and lon is not None:
            latlon.append((lon, lat))
    if len(latlon) >= 3:
        lon_c = sum(p[0] for p in latlon) / len(latlon)
        lat_c = sum(p[1] for p in latlon) / len(latlon)
        return latlon, fuso or fuso_de_longitude(lon_c), hemisferio or ("S" if lat_c < 0 else "N")

    utm = [(v.get("coord_e"), v.get("coord_n")) for v in verts
           if v.get("coord_e") not in (None, "") and v.get("coord_n") not in (None, "")]
    if len(utm) >= 3:
        f = int(fuso) if fuso else 23
        h = hemisferio or "S"
        return [utm_para_geo(float(e), float(n), f, h) for (e, n) in utm], f, h

    # insuficiente: devolve o que houver (o validador reporta E-VERT-MIN)
    return latlon, fuso, hemisferio


def resolver_anel(vertices, fuso: Optional[int] = None, hemisferio: Optional[str] = None
                  ) -> Tuple[List[Tuple[float, float]], Optional[int], Optional[str]]:
    """Anel (lon, lat) FECHADO (dedup de duplicados consecutivos) + (fuso, hemisfério)."""
    pts, f, h = pontos_lonlat(vertices, fuso, hemisferio)
    return _fechar(pts), f, h


def distancia_m(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Distância geodésica (m) entre dois pontos (lon, lat)."""
    _az1, _az2, dist = _geod().inv(float(p1[0]), float(p1[1]), float(p2[0]), float(p2[1]))
    return abs(dist)


def orientar_horario(ring: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Anel exterior no sentido horário (praxe ONR/SIGEF)."""
    return _orientar_horario(ring)


# ──────────────────────────────────────────────────────────────────────────────
# Área e perímetro GEODÉSICOS (GRS80)
# ──────────────────────────────────────────────────────────────────────────────
def area_perimetro_geodesico(ring_lonlat: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Área (m²) e perímetro (m) geodésicos do anel (lon, lat). Fechado ou não."""
    if not ring_lonlat or len(ring_lonlat) < 3:
        return 0.0, 0.0
    ring = list(ring_lonlat)
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    if len(ring) < 3:
        return 0.0, 0.0
    lons = [float(p[0]) for p in ring]
    lats = [float(p[1]) for p in ring]
    area, perim = _geod().polygon_area_perimeter(lons, lats)
    return abs(area), abs(perim)
