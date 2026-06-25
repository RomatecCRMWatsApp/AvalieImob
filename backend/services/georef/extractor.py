# @module services.georef.extractor — Pipeline de extração SIGEF/INCRA.
#
# Lê o Memorial Descritivo e o CCIR (PDFs do SIGEF/INCRA) via pdfplumber e popula
# o cabeçalho do imóvel, a lista de vértices (com vante/azimute/distância/
# confrontação) e os confrontantes agrupados (1 grupo por divisa, para a DRL).
#
# Conversão de coordenadas validada com dados reais (Fazenda Santa Maria):
#   -47°15'52,043"  ->  -47.264456  (vírgula decimal BR)
import io
import logging
import re
from typing import List, Union

import pdfplumber

logger = logging.getLogger("romatec")

PdfSource = Union[str, bytes, bytearray, io.IOBase]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _open(src: PdfSource):
    """pdfplumber.open aceitando path (str) OU bytes/file-like."""
    if isinstance(src, (bytes, bytearray)):
        return pdfplumber.open(io.BytesIO(bytes(src)))
    return pdfplumber.open(src)


def dms_to_decimal(dms: str) -> float:
    """-47°15'52,043"  ->  -47.264456  (vírgula decimal BR; sinal pelo prefixo)."""
    s = (dms or "").strip()
    if not s:
        return 0.0
    sign = -1 if s.lstrip().startswith("-") else 1
    nums = re.findall(r"\d+(?:,\d+)?", s)
    if len(nums) < 3:
        return 0.0
    deg, minu, sec = (float(n.replace(",", ".")) for n in nums[:3])
    return sign * (deg + minu / 60 + sec / 3600)


def _num(s):
    """'4.095,92' -> 4095.92  | '96,8180' -> 96.818  | None/'' -> None."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _clean(c):
    return re.sub(r"\s+", " ", (c or "")).strip()


def _tipo_vertice(codigo: str):
    """Deriva o tipo (M/P/V/O) do código do vértice: FQNS-M-A016 -> 'M'."""
    m = re.match(r"^[A-Z0-9]+-([MPVO])-", (codigo or "").upper())
    return m.group(1) if m else None


# ──────────────────────────────────────────────────────────────────────────────
# Parser do Memorial Descritivo SIGEF
# ──────────────────────────────────────────────────────────────────────────────
HEADER_PATTERNS = {
    "denominacao":        r"Denomina[çc][ãa]o:\s*(.+)",
    "proprietario_nome":  r"Propriet[áa]rio\(a\):\s*(.+)",
    "proprietario_cpf_cnpj": r"CPF:\s*([\d.\-/]+)",
    "matricula":          r"Matr[íi]cula do im[óo]vel:\s*([\d./-]+)",
    "natureza_area":      r"Natureza da [ÁA]rea:\s*(.+)",
    "cod_incra":          r"C[óo]digo INCRA/SNCR:\s*([\d]+)",
    "rt_nome":            r"Respons[áa]vel T[ée]cnico\(a\):\s*(.+)",
    "rt_formacao":        r"Forma[çc][ãa]o:\s*(.+)",
    "rt_credenciamento":  r"C[óo]digo de credenciamento:\s*(\w+)",
    "rt_conselho":        r"Conselho Profissional:\s*([\w/]+)",
    "rt_art":             r"Documento de RT:\s*([\w\-]+)",
    "sistema_geodesico":  r"Sistema Geod[ée]sico de refer[êe]ncia:\s*(.+)",
    "area_ha":            r"[ÁA]rea \(Sistema Geod[ée]sico Local\):\s*([\d.,]+)\s*ha",
    "perimetro_m":        r"Per[íi]metro \(m\):\s*([\d.,]+)",
    "certificacao_sigef": r"CERTIFICA[ÇC][ÃA]O:\s*([\w\-./]+)",
}

EXTRA = {
    "municipio_uf":  r"Munic[íi]pio/UF:\s*(.+?)\s*-\s*([A-Z]{2})",
    "cartorio":      r"Cart[óo]rio \(CNS\):\s*\(([\d.\-]+)\)\s*(.+)",
}

# linha de vértice (tolerante a múltiplos espaços do extract_text)
VERTICE_RE = re.compile(
    r"(?P<cod>[A-Z0-9]+-[MPVO]-[\w]+)\s+"
    r"(?P<lon>-?\d+°\d+'[\d,]+\")\s+"
    r"(?P<lat>-?\d+°\d+'[\d,]+\")\s+"
    r"(?P<alt>[\d.,]+)\s+"
    r"(?P<vante>[A-Z0-9]+-[MPVO]-[\w]+)\s+"
    r"(?P<az>\d+°\d+')\s+"
    r"(?P<dist>[\d.,]+)\s+"
    r"(?P<conf>.+)"
)


def parse_memorial(src: PdfSource) -> dict:
    """Extrai cabeçalho (imovel + RT) e vértices do Memorial Descritivo SIGEF.

    Retorna {"imovel": {...}, "responsavel_tecnico": {...}, "vertices": [...]}.
    """
    full = ""
    rows: List[list] = []
    with _open(src) as pdf:
        for page in pdf.pages:
            full += (page.extract_text() or "") + "\n"
            for tbl in page.extract_tables() or []:
                rows.extend(tbl)

    head = {}
    for k, pat in HEADER_PATTERNS.items():
        m = re.search(pat, full)
        if m:
            head[k] = m.group(1).strip()

    mu = re.search(EXTRA["municipio_uf"], full)
    if mu:
        head["municipio"], head["uf"] = mu.group(1).strip(), mu.group(2)
    ca = re.search(EXTRA["cartorio"], full)
    if ca:
        head["cartorio_cns"], head["cartorio_nome"] = ca.group(1), ca.group(2).strip()

    head["area_ha"] = _num(head.get("area_ha"))
    head["perimetro_m"] = _num(head.get("perimetro_m"))

    # separa o que é do imóvel do que é do Responsável Técnico
    rt = {
        "nome": head.pop("rt_nome", None),
        "formacao": head.pop("rt_formacao", None),
        "credenciamento_incra": head.pop("rt_credenciamento", None),
        "conselho": head.pop("rt_conselho", None),
        "art_trt": head.pop("rt_art", None),
    }
    rt = {k: v for k, v in rt.items() if v}

    vertices = _parse_vertices_from_tables(rows) or _parse_vertices_from_text(full)
    return {"imovel": head, "responsavel_tecnico": rt, "vertices": vertices}


def _parse_vertices_from_text(full: str) -> List[dict]:
    out = []
    for line in full.splitlines():
        m = VERTICE_RE.search(line.strip())
        if not m:
            continue
        d = m.groupdict()
        out.append(_vertice_dict(
            d["cod"], d["lon"], d["lat"], d["alt"], d["vante"], d["az"], d["dist"], d["conf"]
        ))
    return out


def _parse_vertices_from_tables(rows) -> List[dict]:
    out = []
    for r in rows:
        cells = [(_clean(str(c)) if c else "") for c in r]
        if len(cells) < 7:
            continue
        if not re.match(r"[A-Z0-9]+-[MPVO]-", cells[0]):
            continue
        conf = " ".join(cells[7:]) if len(cells) > 7 else ""
        out.append(_vertice_dict(
            cells[0], cells[1], cells[2], cells[3], cells[4], cells[5], cells[6], conf
        ))
    return out


def _vertice_dict(cod, lon, lat, alt, vante, az, dist, conf) -> dict:
    return {
        "codigo": cod,
        "tipo": _tipo_vertice(cod),
        "longitude_dms": lon, "latitude_dms": lat,
        "longitude": dms_to_decimal(lon), "latitude": dms_to_decimal(lat),
        "altitude": _num(alt),
        "vante_codigo": vante, "azimute": az, "distancia": _num(dist),
        "confrontacao_raw": _clean(conf),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Parser do CCIR
# ──────────────────────────────────────────────────────────────────────────────
CCIR_PATTERNS = {
    "ccir_codigo":        r"(\d{3}\.\d{3}\.\d{3}\.\d{3}-\d)",
    "ccir_area_total":    r"[ÁA]REA TOTAL\s*\(ha\)\s*([\d.,]+)",
    "ccir_classificacao": r"CLASSIFICA[ÇC][ÃA]O FUND[IÍ][ÁA]RIA\s*([\w ]+?)\s*(?:DATA|M[ÓO]DULO)",
    "ccir_modulo_fiscal": r"M[ÓO]DULO FISCAL\s*\(ha\)\s*([\d.,]+)",
    "ccir_fmp":           r"FRA[ÇC][ÃA]O M[ÍI]NIMA DE PARCELAMENTO\s*\(ha\)\s*([\d.,]+)",
}
_CCIR_DENOM = r"DENOMINA[ÇC][ÃA]O DO IM[ÓO]VEL RURAL\s*\n?\s*(.+)"
_CCIR_MUN = r"MUNIC[ÍI]PIO SEDE DO IM[ÓO]VEL RURAL\s*\n?\s*(.+?)\s*(?:UF|\n)"


def parse_ccir(src: PdfSource) -> dict:
    """Extrai do CCIR: código, área total, classificação, módulo fiscal e FMP.

    O CCIR é PDF-tabela; combinamos extract_text (linha a linha) com a
    reconstrução por palavras (extract_words) para tolerar o layout.
    """
    full = ""
    words_text = ""
    with _open(src) as pdf:
        for page in pdf.pages:
            full += (page.extract_text() or "") + "\n"
            try:
                ws = page.extract_words() or []
                words_text += " ".join(w.get("text", "") for w in ws) + "\n"
            except Exception:  # noqa: BLE001
                pass

    blob = full + "\n" + words_text
    out = {}
    for k, pat in CCIR_PATTERNS.items():
        m = re.search(pat, blob, re.IGNORECASE)
        if m:
            out[k] = m.group(1).strip()

    md = re.search(_CCIR_DENOM, full, re.IGNORECASE)
    if md:
        out["denominacao"] = _clean(md.group(1))
    mm = re.search(_CCIR_MUN, full, re.IGNORECASE)
    if mm:
        out["municipio"] = _clean(mm.group(1))

    for k in ("ccir_area_total", "ccir_modulo_fiscal", "ccir_fmp"):
        if k in out:
            out[k] = _num(out[k])
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Agrupamento de confrontantes (para a DRL — uma por confrontante)
# ──────────────────────────────────────────────────────────────────────────────
_VIA_PUBLICA_RE = re.compile(
    r"ESTRADA|VICINAL|RODOVIA|VIA\s+P[ÚU]BLICA|C[ÓO]RREGO|RIO\b|RIACHO|SERVID[ÃA]O",
    re.IGNORECASE,
)


def parse_confrontacao(c: str) -> dict:
    """Quebra a célula de confrontação do SIGEF (separada por '|') em campos."""
    parts = [p.strip() for p in (c or "").split("|")]
    out = {
        "cns": None, "matricula": None, "descricao": None,
        "nome": None, "cpf_cnpj": None, "incra": None, "certificacao": None,
    }
    for p in parts:
        if not p:
            continue
        if p.startswith("CNS:"):
            out["cns"] = p.replace("CNS:", "").strip()
        elif p.startswith("Mat."):
            out["matricula"] = re.sub(r"\(.*?\)", "", p.replace("Mat.", "")).strip()
        else:
            out["descricao"] = p
            mn = re.search(r"Nome:\s*([^|]+?)(?:\s+CPF|$)", p)
            if mn:
                out["nome"] = mn.group(1).strip()
            mc = re.search(r"CPF:\s*([\d.\-*/]+)", p)
            if mc:
                out["cpf_cnpj"] = mc.group(1).strip()
            mi = re.search(r"INCRA\s*([\d]+)", p)
            if mi:
                out["incra"] = mi.group(1)
    desc = out["descricao"] or ""
    out["key"] = f'{out["matricula"]}|{desc[:30]}'
    return out


def agrupar_confrontantes(vertices: List[dict], matricula_imovel: str = None) -> List[dict]:
    """Agrupa os segmentos por confrontante. Marca tipo via_publica/proprio/particular."""
    grupos = {}
    for v in vertices:
        info = parse_confrontacao(v.get("confrontacao_raw", ""))
        k = info["key"]
        if k not in grupos:
            grupos[k] = {**info, "imovel": info.get("descricao"), "segmentos": []}
        grupos[k]["segmentos"].append(v.get("codigo"))

    saida = []
    for g in grupos.values():
        desc = g.get("descricao") or ""
        mat = (g.get("matricula") or "").strip()
        if matricula_imovel and mat and mat == str(matricula_imovel).strip():
            g["tipo"] = "proprio"
        elif mat in ("", "0", None) or _VIA_PUBLICA_RE.search(desc):
            g["tipo"] = "via_publica"
        else:
            g["tipo"] = "particular"
        saida.append(g)
    return saida
