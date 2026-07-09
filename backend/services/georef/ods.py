# @module services.georef.ods — Planilha ODS do SIGEF: leitura, conferência e conversão em PDF.
#
# Parseia o content.xml do .ods DIRETO (zip + ElementTree) — evita o odfpy (que quebra a
# validação de gramática em .ods reais do LibreOffice) e não exige dependência nova.
# Motor de conferência conforme os padrões do SIGEF/INCRA + condições do Ofício Circular
# nº 814/2026 (aba de perímetro única, SIRGAS 2000, área conferida, vértices/coordenadas).
from __future__ import annotations

import io
import math
import re
import zipfile
import xml.etree.ElementTree as ET

_NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
}


def _T(tag: str) -> str:
    pre, local = tag.split(":")
    return "{%s}%s" % (_NS[pre], local)


def _cellval(cell) -> str:
    ps = cell.findall(_T("text:p"))
    if ps:
        return " ".join("".join(p.itertext()) for p in ps).strip()
    v = cell.get(_T("office:value"))
    return (v or "").strip()


def ler_abas(ods_bytes: bytes) -> dict:
    """{nome_aba: [[célula, ...], ...]} — expande repetições de coluna (com teto)."""
    with zipfile.ZipFile(io.BytesIO(ods_bytes)) as z:
        xml = z.read("content.xml")
    root = ET.fromstring(xml)
    out = {}
    for t in root.iter(_T("table:table")):
        name = t.get(_T("table:name")) or f"aba_{len(out)}"
        rows = []
        for r in t.findall(_T("table:table-row")):
            row = []
            for c in r.findall(_T("table:table-cell")):
                rep = int(c.get(_T("table:number-columns-repeated") or "1") or 1)
                rep = min(rep, 40)
                val = _cellval(c)
                row.extend([val] * rep)
            while row and row[-1] == "":
                row.pop()
            rows.append(row)
        out[name] = rows
    return out


def _dms_to_dec(s):
    """'47 28 34,060 W' / '04°58\\'20,939\"S' / '-47.476' → grau decimal (S/W/O = negativo)."""
    if s is None:
        return None
    s = str(s).strip().upper()
    if not s:
        return None
    hemi = None
    for h in ("N", "S", "E", "W", "L", "O"):
        if s.endswith(h) or s.startswith(h):
            hemi = h
            break
    nums = re.findall(r"\d+(?:[.,]\d+)?", s)
    if not nums:
        return None
    nums = [float(n.replace(",", ".")) for n in nums]
    if len(nums) >= 3:
        dec = nums[0] + nums[1] / 60.0 + nums[2] / 3600.0
    elif len(nums) == 2:
        dec = nums[0] + nums[1] / 60.0
    else:
        dec = nums[0]
    if hemi in ("S", "W", "O"):
        dec = -abs(dec)
    elif hemi in ("N", "E", "L"):
        dec = abs(dec)
    elif s.lstrip().startswith("-"):
        dec = -dec
    return dec


def _num(s):
    if s in (None, ""):
        return None
    try:
        return float(str(s).replace(".", "").replace(",", ".")) if "," in str(s) else float(str(s))
    except Exception:
        return None


_PERIM_RE = re.compile(r"^perimetro[_\s]*\d+$", re.IGNORECASE)
_VERT_COD_RE = re.compile(r"^[A-Z]{2,5}-[A-Z]-\d{1,7}$", re.IGNORECASE)


def _linha_valor(rows, rotulo):
    """Valor à direita de um rótulo (ex.: 'Matrícula:') em qualquer linha da aba."""
    alvo = rotulo.lower().rstrip(":")
    for row in rows:
        for i, cel in enumerate(row):
            if str(cel).lower().rstrip(":").strip() == alvo and i + 1 < len(row):
                v = str(row[i + 1]).strip()
                if v:
                    return v
    return ""


def _extrair_vertices(perim_rows):
    """Lê a tabela de perímetro: acha o cabeçalho 'Vértice' e coleta os vértices abaixo."""
    hdr_idx = None
    for i, row in enumerate(perim_rows):
        if row and str(row[0]).strip().lower() == "vértice":
            hdr_idx = i
            break
    if hdr_idx is None:
        return []
    verts = []
    for row in perim_rows[hdr_idx + 1:]:
        cod = str(row[0]).strip() if row else ""
        if not cod:
            break
        verts.append({
            "codigo": cod,
            "long": row[1] if len(row) > 1 else "",
            "lat": row[3] if len(row) > 3 else "",
            "sigma_long": row[2] if len(row) > 2 else "",
            "sigma_lat": row[4] if len(row) > 4 else "",
            "metodo": row[7] if len(row) > 7 else "",
            "tipo_limite": row[8] if len(row) > 8 else "",
            "matricula": row[10] if len(row) > 10 else "",
            "confrontante": row[11] if len(row) > 11 else "",
            "_lon": _dms_to_dec(row[1] if len(row) > 1 else ""),
            "_lat": _dms_to_dec(row[3] if len(row) > 3 else ""),
        })
    return verts


def _area_perimetro_ha(verts):
    """Área (ha) e perímetro (m) por projeção equirretangular local (bom p/ parcela pequena)."""
    pts = [(v["_lon"], v["_lat"]) for v in verts if v["_lon"] is not None and v["_lat"] is not None]
    if len(pts) < 3:
        return None, None
    lat0 = sum(p[1] for p in pts) / len(pts)
    lat0r = math.radians(lat0)
    m_lat = 111132.92 - 559.82 * math.cos(2 * lat0r) + 1.175 * math.cos(4 * lat0r)
    m_lon = 111412.84 * math.cos(lat0r) - 93.5 * math.cos(3 * lat0r)
    xy = [((lon) * m_lon, (lat) * m_lat) for lon, lat in pts]
    # shoelace
    n = len(xy)
    area2 = 0.0
    perim = 0.0
    for i in range(n):
        x1, y1 = xy[i]
        x2, y2 = xy[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
        perim += math.hypot(x2 - x1, y2 - y1)
    return abs(area2) / 2.0 / 10000.0, perim


def analisar(ods_bytes: bytes) -> dict:
    """Extrai a estrutura da ODS: abas, identificação, aba(s) de perímetro, vértices e área."""
    abas = ler_abas(ods_bytes)
    nomes = list(abas.keys())
    perim_nomes = [n for n in nomes if _PERIM_RE.match(n or "")]
    ident_rows = abas.get("identificacao", [])
    ident = {
        "denominacao": _linha_valor(ident_rows, "Denominação"),
        "situacao": _linha_valor(ident_rows, "Situação"),
        "natureza": _linha_valor(ident_rows, "Natureza da área"),
        "cod_incra": _linha_valor(ident_rows, "Código do Imóvel(SNCR/INCRA)")
                     or _linha_valor(ident_rows, "Código do Imóvel"),
        "cns": _linha_valor(ident_rows, "Código do cartório (CNS)") or _linha_valor(ident_rows, "CNS"),
        "matricula": _linha_valor(ident_rows, "Matrícula"),
        "detentor": _linha_valor(ident_rows, "Nome"),
        "cpf_cnpj": _linha_valor(ident_rows, "CPF") or _linha_valor(ident_rows, "CNPJ"),
        "natureza_servico": _linha_valor(ident_rows, "Natureza do serviço"),
    }
    perim_rows = abas.get(perim_nomes[0], []) if perim_nomes else []
    # Sistema de referência: captura a célula "Sistema de referência ..." (mesmo se não SIRGAS,
    # p/ o validador poder acusar SRC inválido) — fallback p/ qualquer célula com "SIRGAS".
    sistema = ""
    for row in perim_rows:
        for cel in row:
            cl = str(cel).strip()
            low = cl.lower()
            if low.startswith("sistema de refer") or "SIRGAS" in cl.upper():
                sistema = cl
                break
        if sistema:
            break
    verts = _extrair_vertices(perim_rows)
    area_ha, perim_m = _area_perimetro_ha(verts)
    return {
        "abas": nomes,
        "abas_perimetro": perim_nomes,
        "identificacao": ident,
        "sistema_referencia": sistema,
        "vertices": verts,
        "n_vertices": len(verts),
        "area_ha": area_ha,
        "perimetro_m": perim_m,
    }


def validar(ods_bytes: bytes, area_parcela_ha=None) -> dict:
    """Motor de conferência da ODS conforme padrões do SIGEF + Ofício Circular 814/2026.
    Devolve erros (impeditivos), alertas (análise INCRA) e infos, no espírito do item 2.5."""
    try:
        a = analisar(ods_bytes)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "lido": False,
                "erros": [{"codigo": "ODS_ILEGIVEL", "msg": f"Não foi possível ler a Planilha ODS: {e}"}],
                "alertas": [], "info": []}

    erros, alertas, info = [], [], []
    perim = a["abas_perimetro"]
    if not perim:
        erros.append({"codigo": "SEM_PERIMETRO",
                      "msg": "A planilha não possui aba de perímetro (perimetro_1)."})
    elif len(perim) > 1:
        alertas.append({"codigo": "MULTI_PERIMETRO",
                        "msg": f"A planilha possui {len(perim)} abas de perímetro. O item 1 (iv) do "
                               "Ofício 814/2026 exige uma ÚNICA aba de perímetro para deferimento automático."})
    else:
        info.append({"codigo": "PERIMETRO_UNICO", "msg": "Uma única aba de perímetro (condição iv atendida)."})

    sistema = (a["sistema_referencia"] or "").upper().replace(" ", "")
    if not sistema:
        alertas.append({"codigo": "SEM_SRC", "msg": "Sistema de referência não identificado na planilha."})
    elif "SIRGAS2000" not in sistema:
        erros.append({"codigo": "SRC_INVALIDO",
                      "msg": f"Sistema de referência '{a['sistema_referencia']}' — o SIGEF exige SIRGAS 2000."})
    else:
        info.append({"codigo": "SRC_OK", "msg": "Sistema geodésico SIRGAS 2000."})

    n = a["n_vertices"]
    if n < 3:
        erros.append({"codigo": "POUCOS_VERTICES",
                      "msg": f"A poligonal tem {n} vértice(s) — o mínimo para um polígono é 3."})
    else:
        info.append({"codigo": "VERTICES", "msg": f"{n} vértices na poligonal."})

    sem_cod = [v for v in a["vertices"] if not v["codigo"]]
    fora_padrao = [v for v in a["vertices"] if v["codigo"] and not _VERT_COD_RE.match(v["codigo"])]
    sem_coord = [v for v in a["vertices"] if v["_lon"] is None or v["_lat"] is None]
    if sem_cod:
        erros.append({"codigo": "VERTICE_SEM_CODIGO", "msg": f"{len(sem_cod)} vértice(s) sem código."})
    if sem_coord:
        erros.append({"codigo": "COORD_INVALIDA",
                      "msg": f"{len(sem_coord)} vértice(s) com coordenada ilegível/ausente."})
    if fora_padrao:
        alertas.append({"codigo": "CODIGO_FORA_PADRAO",
                        "msg": f"{len(fora_padrao)} código(s) de vértice fora do padrão SIGEF "
                               "(ex.: FQNS-M-4028): " + ", ".join(v["codigo"] for v in fora_padrao[:4])})

    if a["area_ha"] is not None:
        info.append({"codigo": "AREA_CALC",
                     "msg": f"Área calculada da poligonal: {a['area_ha']:.4f} ha".replace(".", ",")
                            + (f" · perímetro {a['perimetro_m']:.2f} m".replace(".", ",") if a["perimetro_m"] else "")})
        pa = _num(area_parcela_ha)
        if pa and pa > 0:
            d_abs = abs(a["area_ha"] - pa)
            d_pct = d_abs / pa * 100.0
            if d_pct >= 10.0:
                alertas.append({"codigo": "AREA_DIFF_10",
                                "msg": f"Área da ODS difere {d_pct:.2f}% da área da parcela "
                                       "(≥ 10% — condição v não atendida).".replace(".", ",")})
            if d_abs >= 25.0:
                alertas.append({"codigo": "AREA_DIFF_25",
                                "msg": f"Área da ODS difere {d_abs:.4f} ha da parcela "
                                       "(≥ 25 ha — condição vi não atendida).".replace(".", ",")})
            if d_pct < 10.0 and d_abs < 25.0:
                info.append({"codigo": "AREA_OK",
                             "msg": f"Área confere com a parcela (diferença {d_pct:.2f}%).".replace(".", ",")})

    return {
        "ok": len(erros) == 0,
        "lido": True,
        "resumo": a,
        "erros": erros,
        "alertas": alertas,
        "info": info,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Conversão em PDF (planilha → PDF legível para anexar ao processo)
# ──────────────────────────────────────────────────────────────────────────────
def para_pdf(ods_bytes: bytes, tema: str = "prime_i", logo_bytes: bytes = None) -> bytes:
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from services.georef.generators import pdf as PDF

    a = analisar(ods_bytes)
    cfg = PDF._cfg(tema)
    st = PDF._styles(cfg)
    lar = PDF._largura()
    e = []
    e += PDF._titulo("PLANILHA ODS — SIGEF (conversão para PDF)", cfg, st, lar)

    ident = a["identificacao"]
    pares = [
        ("Denominação", ident.get("denominacao")),
        ("Detentor", ident.get("detentor")),
        ("CPF/CNPJ", ident.get("cpf_cnpj")),
        ("Matrícula", ident.get("matricula")),
        ("Código INCRA/SNCR", ident.get("cod_incra")),
        ("CNS do cartório", ident.get("cns")),
        ("Natureza da área", ident.get("natureza")),
        ("Situação", ident.get("situacao")),
        ("Sistema de referência", a.get("sistema_referencia")),
        ("Nº de vértices", str(a.get("n_vertices") or "")),
        ("Área calculada (ha)", (f"{a['area_ha']:.4f}".replace(".", ",") if a.get("area_ha") else "")),
        ("Perímetro (m)", (f"{a['perimetro_m']:.2f}".replace(".", ",") if a.get("perimetro_m") else "")),
    ]
    e += PDF._secao("IDENTIFICAÇÃO", cfg, st, lar)
    e.append(PDF._kv_table([(k, v) for k, v in pares if v], cfg, st, lar))

    verts = a["vertices"]
    if verts:
        e += PDF._secao("TABELA DE PERÍMETRO", cfg, st, lar)
        header = ["Vértice", "E/Long", "N/Lat", "Método", "Tipo", "Matríc.", "Confrontante"]
        rows = [[v["codigo"], str(v["long"]), str(v["lat"]), str(v["metodo"]),
                 str(v["tipo_limite"]), str(v["matricula"]), str(v["confrontante"])[:44]]
                for v in verts]
        e.append(PDF._data_table(header, rows, cfg, st, lar))

    return PDF._build(e, cfg, "Planilha ODS — SIGEF", logo_bytes)
