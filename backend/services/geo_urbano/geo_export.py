# @module services.geo_urbano.geo_export — Shapefile SIG-RI + KML + GeoJSON (urbano).
#
# Provimento CNJ 195/2025: o SIG-RI é OBRIGATÓRIO para alimentar a malha fundiária
# do Registro de Imóveis em TODOS os procedimentos (inclusive urbanos). Geramos o
# pacote shapefile (SHP/SHX/DBF/PRJ + CPG + LEIAME.txt) em SIRGAS 2000/EPSG:4674,
# com o esquema de atributos URBANO (schema_onr) e ÁREA/PERÍMETRO GEODÉSICOS
# (GRS80, via services.geo_urbano.geodesia) — nunca planos.
from __future__ import annotations

import hashlib
import io
import os
import re
import tempfile
import zipfile

from services.georef.geo import SIRGAS2000_PRJ
from services.geo_urbano import geodesia as GEO
from services.geo_urbano import schema_onr as SCH
from services.geo_urbano.generators import textos as TX


# ──────────────────────────────────────────────────────────────────────────────
# Feições (rotulo, vértices) — 1 por lote (desdobro) ou o polígono único
# ──────────────────────────────────────────────────────────────────────────────
def _feature_vertices(projeto):
    lotes = projeto.get("lotes_resultantes") or []
    if projeto.get("tipo_servico") == "desdobro" and lotes:
        out = []
        for lt in sorted(lotes, key=lambda x: x.get("ordem", 0)):
            out.append((lt.get("denominacao") or "", lt.get("vertices") or []))
        return out
    return [(projeto.get("denominacao_imovel") or "", projeto.get("vertices") or [])]


def _feature_aneis(projeto):
    """[(rotulo, anel_horario, n_vertices, fuso, hemisferio)] com anéis válidos (≥4 pts)."""
    out = []
    for rotulo, verts in _feature_vertices(projeto):
        ring, fuso, hemis = GEO.resolver_anel(verts)
        ring = GEO.orientar_horario(ring)
        if len(ring) >= 4:
            out.append((rotulo, ring, len(ring) - 1, fuso, hemis))
    return out


def _matriculas_str(projeto):
    return "/".join(m.get("matricula") for m in (projeto.get("matriculas") or []) if m.get("matricula"))


def _requerente(projeto):
    for p in projeto.get("partes") or []:
        if p.get("papel") == "requerente":
            return (p.get("razao_social") or p.get("nome") or "", p.get("cnpj") or p.get("cpf") or "")
    return ("", "")


# ──────────────────────────────────────────────────────────────────────────────
# GeoJSON / KML (SIRGAS 2000 / EPSG:4674)
# ──────────────────────────────────────────────────────────────────────────────
def gerar_geojson(projeto: dict) -> dict:
    feats = []
    nome_prop, _doc = _requerente(projeto)
    for rotulo, anel, _n, _f, _h in _feature_aneis(projeto):
        feats.append({"type": "Feature",
                      "properties": {"denominacao": rotulo, "matricula": _matriculas_str(projeto),
                                     "cmi": TX.cim_completo(projeto), "proprietario": nome_prop},
                      "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in anel]]}})
    return {"type": "FeatureCollection", "crs": {"type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::4674"}}, "features": feats}


def gerar_kml(projeto: dict) -> str:
    placemarks = []
    for rotulo, anel, _n, _f, _h in _feature_aneis(projeto):
        coords = " ".join(f"{lon:.8f},{lat:.8f},0" for (lon, lat) in anel)
        placemarks.append(
            f"<Placemark><name>{(rotulo or 'Imóvel')}</name><Polygon><outerBoundaryIs><LinearRing>"
            f"<coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>")
    nome = projeto.get("denominacao_imovel") or "Geo Urbano"
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f"<name>{nome}</name>{''.join(placemarks)}</Document></kml>")


# ──────────────────────────────────────────────────────────────────────────────
# Pacote shapefile SIG-RI (SHP/SHX/DBF/PRJ + CPG + LEIAME.txt)
# ──────────────────────────────────────────────────────────────────────────────
def _slug(rotulo: str, idx: int) -> str:
    t = re.sub(r"[^0-9A-Za-z]+", "", (rotulo or "")) or f"Lote{idx + 1}"
    return t[:24]


def _pacote_shapefile(projeto: dict, feat, idx: int, multi: bool):
    """(basename, zip_bytes) de UM pacote shapefile (1 polígono):
    SHP/SHX/DBF/PRJ/CPG + LEIAME.txt, SIRGAS 2000/EPSG:4674, área geodésica."""
    import shapefile  # pyshp

    rotulo, ring, n_vert, fuso, hemis = feat
    area_m2, perim_m = GEO.area_perimetro_geodesico(ring)
    num = str(projeto.get("numero") or "sn").replace("/", "_")
    slug = _slug(rotulo, idx)
    tmp = tempfile.mkdtemp(prefix="sigri_urb_")
    base = os.path.join(tmp, f"SIGRI_URB_{num}_{slug}")
    nome_base = os.path.basename(base)

    w = shapefile.Writer(base, shapeType=shapefile.POLYGON)
    for f, t, sz, dec in SCH.ONR_URBANO_FIELDS:
        w.field(f, t, sz, dec)
    rec = SCH.montar_registro(projeto, rotulo=rotulo, area_m2=area_m2, perimetro_m=perim_m,
                              n_vertices=n_vert, fuso=fuso, hemisferio=hemis,
                              id_imovel=f"{projeto.get('id') or num}-{slug}",
                              lote_label=(rotulo if multi else None))
    w.poly([[list(p) for p in ring]])
    w.record(**rec)
    w.close()

    with open(base + ".prj", "w", encoding="utf-8") as fh:
        fh.write(SIRGAS2000_PRJ)
    with open(base + ".cpg", "w", encoding="utf-8") as fh:
        fh.write("UTF-8")

    partes = {}
    for ext in ("shp", "shx", "dbf", "prj", "cpg"):
        caminho = base + f".{ext}"
        if os.path.exists(caminho):
            with open(caminho, "rb") as fh:
                partes[ext] = fh.read()
    h = hashlib.sha256()
    for ext in ("shp", "shx", "dbf", "prj"):   # SHA-256 dos arquivos-núcleo
        if ext in partes:
            h.update(partes[ext])
    leiame = SCH.montar_leiame(projeto, sha256=h.hexdigest(), rotulo=rotulo, area_m2=area_m2,
                               perimetro_m=perim_m, n_vertices=n_vert, fuso=fuso, hemisferio=hemis)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for ext in ("shp", "shx", "dbf", "prj", "cpg"):
            if ext in partes:
                z.writestr(f"{nome_base}.{ext}", partes[ext])
        z.writestr("LEIAME.txt", leiame.encode("utf-8"))
    return nome_base, buf.getvalue()


def gerar_shapefile_bytes(projeto: dict) -> bytes:
    """Pacote SIG-RI SIRGAS 2000/EPSG:4674 (esquema URBANO, área geodésica).

    §8.1: UM polígono por pacote. Imóvel único/remembramento → um pacote
    (SHP/SHX/DBF/PRJ/CPG + LEIAME). Desdobro com N lotes → N pacotes (cada lote
    vira matrícula própria) empacotados num ZIP-mãe.
    """
    feats = _feature_aneis(projeto)
    if not feats:
        raise ValueError(
            "Poligonal insuficiente para o SIG-RI: informe os vértices com Latitude/Longitude "
            "ou coordenadas UTM (Este/Norte).")

    multi = len(feats) > 1
    pacotes = [_pacote_shapefile(projeto, f, i, multi) for i, f in enumerate(feats)]
    if len(pacotes) == 1:
        return pacotes[0][1]

    # ZIP-mãe (loteamento/desdobro): um pacote shapefile por lote
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome_base, pkg in pacotes:
            z.writestr(f"{nome_base}.zip", pkg)
    return buf.getvalue()
