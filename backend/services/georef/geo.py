# @module services.georef.geo — Geometria: anel da poligonal, Shapefile SIG-RI, GeoJSON, KML.
#
# Provimento CNJ 195/2025: o arquivo geoespacial enviado ao SIG-RI / Mapa do ONR
# (mapa.onr.org.br) é um Shapefile em SIRGAS 2000 (EPSG:4674). Gera-se também
# GeoJSON (preview no front) e KML (Google Earth) a partir do mesmo anel.
import math
import os
import re
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
# Esquema de atributos DBF do SIG-RI (Prov. CNJ 195/2025 / ONR-EGI). Nomes ≤10 chars
# (limite do formato DBF). Preenchidos com o ACERVO COMPLETO do imóvel/parcela.
_FIELDS = [
    ("MATRICULA", "C", 20, 0),   # matrícula do imóvel de origem
    ("PARCELA", "C", 30, 0),     # rótulo da parcela resultante (Parte I / Parte II)
    ("TIPO_ATO", "C", 24, 0),    # desmembramento / remembramento / georreferenciamento
    ("DENOM", "C", 120, 0),      # denominação da parcela/imóvel
    ("COD_INCRA", "C", 20, 0),   # código INCRA/SNCR
    ("CCIR", "C", 30, 0),        # nº do CCIR
    ("NIRF", "C", 20, 0),        # NIRF / ITR
    ("CAR", "C", 80, 0),         # registro no CAR
    ("PROPRIET", "C", 120, 0),   # proprietário
    ("CPF_CNPJ", "C", 20, 0),
    ("CNS", "C", 20, 0),         # CNS da serventia
    ("CARTORIO", "C", 120, 0),   # serventia / cartório
    ("COMARCA", "C", 60, 0),     # comarca/município do cartório
    ("AREA_HA", "N", 18, 4),     # área em hectares
    ("AREA_M2", "N", 18, 2),     # área em m²
    ("PERIM_M", "N", 18, 2),     # perímetro em metros
    ("SGEODESIC", "C", 24, 0),   # sistema geodésico de referência (SRC)
    ("CERT_SIGEF", "C", 50, 0),  # código de certificação SIGEF/INCRA
    ("DT_CERT", "C", 12, 0),     # data da certificação
    ("NATUREZA", "C", 60, 0),    # natureza da área
    ("MUNICIPIO", "C", 60, 0),   # município do imóvel
    ("UF", "C", 2, 0),
    ("RT_NOME", "C", 120, 0),    # responsável técnico
    ("RT_INCRA", "C", 20, 0),    # cód. credenciamento INCRA do RT
    ("ART_TRT", "C", 40, 0),     # ART/TRT/RRT
]

# Rótulos legíveis p/ a tela de CONFERÊNCIA dos atributos.
_FIELD_LABELS = {
    "MATRICULA": "Matrícula (origem)", "PARCELA": "Parcela resultante",
    "TIPO_ATO": "Tipo de ato", "DENOM": "Denominação", "COD_INCRA": "Código INCRA/SNCR",
    "CCIR": "CCIR", "NIRF": "NIRF / ITR", "CAR": "CAR (ambiental)",
    "PROPRIET": "Proprietário", "CPF_CNPJ": "CPF/CNPJ", "CNS": "CNS da serventia",
    "CARTORIO": "Cartório (serventia)", "COMARCA": "Comarca do cartório",
    "AREA_HA": "Área (ha)", "AREA_M2": "Área (m²)", "PERIM_M": "Perímetro (m)",
    "SGEODESIC": "Sistema geodésico (SRC)", "CERT_SIGEF": "Certificação SIGEF",
    "DT_CERT": "Data da certificação", "NATUREZA": "Natureza da área",
    "MUNICIPIO": "Município do imóvel", "UF": "UF", "RT_NOME": "Responsável Técnico",
    "RT_INCRA": "Cód. INCRA do RT", "ART_TRT": "ART / TRT",
}


def _to_num(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^0-9,.\-]", "", str(v))
    if not s:
        return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _coerce(name: str, ftype: str, size: int, value) -> object:
    if ftype == "N":
        return round(_to_num(value), 4 if name == "AREA_HA" else 2)
    return str(value if value is not None else "")[:size]


def _registro_parcela(im: dict, rt: dict, tipo: str, p: dict) -> dict:
    """Monta o registro DBF (atributos SIG-RI) de UMA parcela — fonte ÚNICA."""
    area_ha = _to_num(p.get("area_ha"))
    bruto = {
        "MATRICULA": im.get("matricula"),
        "PARCELA": p.get("rotulo") or ("Parte I" if p.get("principal") else ""),
        "TIPO_ATO": tipo,
        "DENOM": p.get("denominacao") or im.get("denominacao"),
        "COD_INCRA": im.get("cod_incra"),
        "CCIR": im.get("ccir_codigo"),
        "NIRF": im.get("nirf"),
        "CAR": im.get("car"),
        "PROPRIET": im.get("proprietario_nome"),
        "CPF_CNPJ": im.get("proprietario_cpf_cnpj"),
        "CNS": im.get("cartorio_cns"),
        "CARTORIO": im.get("cartorio_nome"),
        "COMARCA": im.get("cartorio_municipio"),
        "AREA_HA": area_ha,
        "AREA_M2": area_ha * 10000.0,
        "PERIM_M": _to_num(p.get("perimetro_m")),
        "SGEODESIC": im.get("sistema_geodesico") or "SIRGAS 2000",
        "CERT_SIGEF": p.get("certificacao_sigef") or im.get("certificacao_sigef"),
        "DT_CERT": im.get("data_certificacao"),
        "NATUREZA": im.get("natureza_area"),
        "MUNICIPIO": im.get("municipio"),
        "UF": im.get("uf"),
        "RT_NOME": rt.get("nome"),
        "RT_INCRA": rt.get("credenciamento_incra"),
        "ART_TRT": rt.get("art_trt") or im.get("certificacao_sigef"),
    }
    return {n: _coerce(n, t, sz, bruto.get(n)) for (n, t, sz, _dec) in _FIELDS}


def atributos_sigri(projeto: dict) -> list:
    """Atributos DBF do SIG-RI (Prov. 195/2025) POR PARCELA — p/ a CONFERÊNCIA e o shapefile.
    Retorna [{rotulo, principal, id, record{FIELD: valor}}, ...]."""
    from services.georef.parcelas import parcelas_do_projeto
    im = projeto.get("imovel") or {}
    rt = projeto.get("responsavel_tecnico") or {}
    tipo = (projeto.get("tipo_servico") or "").strip()
    return [{"rotulo": p.get("rotulo") or "Parcela", "principal": bool(p.get("principal")),
             "id": p.get("id"), "record": _registro_parcela(im, rt, tipo, p)}
            for p in parcelas_do_projeto(projeto)]


def campos_sigri() -> list:
    """[(campo, label, tipo)] na ordem do DBF — p/ a tela de conferência."""
    return [(n, _FIELD_LABELS.get(n, n), t) for (n, t, _sz, _dec) in _FIELDS]


def _slug_parcela(parc: dict, idx: int) -> str:
    rot = parc.get("rotulo") or ("ParteI" if parc.get("principal") else f"Parte{idx + 1}")
    slug = "".join(ch for ch in str(rot) if ch.isalnum())
    return slug or f"P{idx + 1}"


def _escrever_shapefile(base: str, record: dict, ring) -> None:
    """Escreve um conjunto shp/shx/dbf/prj (1 polígono + atributos) em `base` (sem extensão)."""
    import shapefile  # pyshp
    w = shapefile.Writer(base, shapeType=shapefile.POLYGON)
    for f, t, sz, dec in _FIELDS:
        w.field(f, t, sz, dec)
    w.poly([[list(p) for p in ring]])
    w.record(*[record[n] for (n, *_rest) in _FIELDS])
    w.close()
    with open(base + ".prj", "w", encoding="utf-8") as fh:
        fh.write(SIRGAS2000_PRJ)


def gerar_shapefile_bytes(projeto: dict) -> bytes:
    """Gera o(s) Shapefile(s) SIG-RI (.shp/.shx/.dbf/.prj) zipados, SIRGAS 2000/EPSG:4674,
    com o ACERVO COMPLETO de atributos (Prov. 195/2025) preenchido no DBF.

    DESMEMBRAMENTO (2+ parcelas resultantes): UM shapefile POR PARCELA no .zip
    (cada parcela vira uma matrícula própria no RI). Imóvel único/remembramento
    (unificação): um único shapefile.
    """
    from services.georef.parcelas import parcelas_do_projeto

    im = projeto.get("imovel") or {}
    rt = projeto.get("responsavel_tecnico") or {}
    tipo = (projeto.get("tipo_servico") or "").strip()
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
        _escrever_shapefile(base, _registro_parcela(im, rt, tipo, parc), ring)
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
