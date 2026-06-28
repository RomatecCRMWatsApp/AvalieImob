# @module services.geo_urbano.geo_export — Shapefile SIG-RI + KML + GeoJSON (urbano).
#
# Provimento CNJ 195/2025: o SIG-RI é OBRIGATÓRIO para alimentar a malha fundiária
# do Registro de Imóveis em TODOS os procedimentos (inclusive urbanos). Geramos o
# shapefile (SHP/SHX/DBF/PRJ) em SIRGAS 2000 / EPSG:4674 (geográfico) a partir das
# coordenadas Latitude/Longitude (DMS) dos vértices — convertidas para decimal.
from __future__ import annotations

import io
import os
import re
import tempfile
import zipfile

from services.georef.geo import SIRGAS2000_PRJ, _orientar_horario

# Campos do DBF (atributos da feição na malha fundiária)
_FIELDS = [
    ("MATRICULA", "C", 80, 0), ("DENOM", "C", 100, 0), ("CMI", "C", 40, 0),
    ("PROPRIET", "C", 100, 0), ("DOC", "C", 20, 0),
    ("AREA_M2", "N", 18, 2), ("PERIM_M", "N", 14, 2),
    ("MUNICIPIO", "C", 60, 0), ("UF", "C", 2, 0), ("SGEODESIC", "C", 12, 0),
]


def _dms_to_dec(s):
    """'04°56'15,475979\"S' / '47°27'59,462032\"W' → decimal (S/W negativos)."""
    if not s:
        return None
    s = str(s).strip()
    neg = bool(re.search(r"[SWsw]\s*$", s)) or s.lstrip().startswith("-")
    nums = re.findall(r"\d+(?:[.,]\d+)?", s)
    if not nums:
        return None
    g = float(nums[0].replace(",", "."))
    m = float(nums[1].replace(",", ".")) if len(nums) > 1 else 0.0
    sec = float(nums[2].replace(",", ".")) if len(nums) > 2 else 0.0
    dec = g + m / 60.0 + sec / 3600.0
    return -dec if neg else dec


def _anel_latlon(vertices):
    """Anel (lon, lat) decimal, na ordem dos vértices; fecha o polígono."""
    verts = sorted((v for v in (vertices or []) if v.get("latitude") and v.get("longitude")),
                   key=lambda v: v.get("ordem", 0))
    ring = []
    for v in verts:
        lat, lon = _dms_to_dec(v.get("latitude")), _dms_to_dec(v.get("longitude"))
        if lat is not None and lon is not None:
            ring.append((lon, lat))
    if len(ring) >= 3 and ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def _features(projeto):
    """[(rotulo, anel)] — 1 por lote (desdobro) ou o polígono único."""
    lotes = projeto.get("lotes_resultantes") or []
    if projeto.get("tipo_servico") == "desdobro" and lotes:
        out = []
        for lt in sorted(lotes, key=lambda x: x.get("ordem", 0)):
            anel = _anel_latlon(lt.get("vertices") or [])
            if len(anel) >= 4:
                out.append((lt.get("denominacao") or "", anel))
        return out
    anel = _anel_latlon(projeto.get("vertices") or [])
    return [(projeto.get("denominacao_imovel") or "", anel)] if len(anel) >= 4 else []


def _matriculas_str(projeto):
    return "/".join(m.get("matricula") for m in (projeto.get("matriculas") or []) if m.get("matricula"))


def _requerente(projeto):
    for p in projeto.get("partes") or []:
        if p.get("papel") == "requerente":
            return (p.get("razao_social") or p.get("nome") or "", p.get("cnpj") or p.get("cpf") or "")
    return ("", "")


def gerar_geojson(projeto: dict) -> dict:
    feats = []
    nome_prop, _doc = _requerente(projeto)
    for rotulo, anel in _features(projeto):
        feats.append({"type": "Feature",
                      "properties": {"denominacao": rotulo, "matricula": _matriculas_str(projeto),
                                     "cmi": projeto.get("cmi_resultante"), "proprietario": nome_prop},
                      "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in anel]]}})
    return {"type": "FeatureCollection", "crs": {"type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::4674"}}, "features": feats}


def gerar_kml(projeto: dict) -> str:
    placemarks = []
    for rotulo, anel in _features(projeto):
        coords = " ".join(f"{lon:.8f},{lat:.8f},0" for (lon, lat) in anel)
        placemarks.append(
            f"<Placemark><name>{(rotulo or 'Imóvel')}</name><Polygon><outerBoundaryIs><LinearRing>"
            f"<coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>")
    nome = projeto.get("denominacao_imovel") or "Geo Urbano"
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f"<name>{nome}</name>{''.join(placemarks)}</Document></kml>")


def gerar_shapefile_bytes(projeto: dict) -> bytes:
    """Shapefile SIG-RI (.shp/.shx/.dbf/.prj) zipado — SIRGAS 2000 / EPSG:4674."""
    import shapefile  # pyshp
    feats = _features(projeto)
    feats = [(r, _orientar_horario(a)) for (r, a) in feats]
    feats = [(r, a) for (r, a) in feats if len(a) >= 4]
    if not feats:
        raise ValueError("Poligonal insuficiente (faltam Latitude/Longitude dos vértices) para o SIG-RI.")

    nome_prop, doc = _requerente(projeto)
    mats = _matriculas_str(projeto)
    tmp = tempfile.mkdtemp(prefix="sigri_urb_")
    base = os.path.join(tmp, f"SIGRI_URB_{(projeto.get('numero') or 'sn')}".replace("/", "_"))

    w = shapefile.Writer(base, shapeType=shapefile.POLYGON)
    for f, t, sz, dec in _FIELDS:
        w.field(f, t, sz, dec)
    for rotulo, ring in feats:
        # área/perímetro em metros (UTM) — usa coord_e/coord_n se houver, senão deixa 0
        w.poly([[list(p) for p in ring]])
        w.record(mats[:80], (rotulo or "")[:100], str(projeto.get("cmi_resultante") or "")[:40],
                 (nome_prop or "")[:100], str(doc or "")[:20],
                 float(projeto.get("area_declarada_m2") or 0), float(projeto.get("perimetro_m") or 0),
                 (projeto.get("municipio") or "")[:60], str(projeto.get("uf") or "")[:2], "SIRGAS2000")
    w.close()
    with open(base + ".prj", "w", encoding="utf-8") as fh:
        fh.write(SIRGAS2000_PRJ)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for ext in ("shp", "shx", "dbf", "prj"):
            caminho = base + f".{ext}"
            if os.path.exists(caminho):
                z.write(caminho, arcname=os.path.basename(base) + f".{ext}")
    return buf.getvalue()
