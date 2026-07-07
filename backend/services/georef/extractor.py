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
# NOTA: o Memorial SIGEF tem layout de 2 COLUNAS — a extração de texto mistura
# campos vizinhos na mesma linha (ex.: "Denominação: X ... Natureza da Área: Y").
# Por isso vários padrões usam lookahead p/ PARAR no início do campo seguinte.
# As buscas rodam com re.MULTILINE → `$` = fim de LINHA (não do documento).
HEADER_PATTERNS = {
    "denominacao":        r"Denomina[çc][ãa]o:\s*(.+?)(?=\s+Natureza da [ÁA]rea:|\s*$)",
    "proprietario_nome":  r"Propriet[áa]rio\(a\):\s*(.+?)(?=\s+CPF:|\s*$)",
    "proprietario_cpf_cnpj": r"CPF:\s*([\d.\-/]+)",
    "matricula":          r"Matr[íi]cula do im[óo]vel:\s*([\d./-]+)",
    "natureza_area":      r"Natureza da [ÁA]rea:\s*(.+?)(?=\s+Cart[óo]rio|\s*$)",
    "cod_incra":          r"C[óo]digo INCRA/SNCR:\s*([\d]+)",
    "rt_nome":            r"Respons[áa]vel T[ée]cnico\(a\):\s*([A-ZÀ-Ÿ]+(?![a-zà-ÿ])(?:\s+[A-ZÀ-Ÿ]+(?![a-zà-ÿ]))*)",
    "rt_formacao":        r"Forma[çc][ãa]o:\s*(.+?)(?=\s+C[óo]digo de|\s*$)",
    "rt_credenciamento":  r"C[óo]digo de credenciamento:\s*(\w+)",
    "rt_conselho":        r"Conselho Profissional:\s*([\w/]+)",
    "rt_art":             r"Documento de RT:\s*([\w\-]+)",
    "sistema_geodesico":  r"Sistema Geod[ée]sico de refer[êe]ncia:\s*(.+?)(?=\s+Documento de RT|\s*$)",
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
        m = re.search(pat, full, re.MULTILINE)
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
# Rótulos numéricos do CCIR: (campo, substring do rótulo p/ a célula, regex p/ linha simples)
_CCIR_NUM = [
    ("ccir_area_total",    "ÁREA TOTAL",                    r"[ÁA]REA TOTAL\s*\(ha\)"),
    ("ccir_modulo_fiscal", "MÓDULO FISCAL",                 r"M[ÓO]DULO FISCAL\s*\(ha\)"),
    ("ccir_fmp",           "FRAÇÃO MÍNIMA DE PARCELAMENTO", r"FRA[ÇC][ÃA]O M[ÍI]NIMA DE PARCELAMENTO\s*\(ha\)"),
]


def parse_ccir(src: PdfSource) -> dict:
    """Extrai do CCIR: código, área total, classificação, módulo fiscal e FMP.

    O CCIR é um FORMULÁRIO posicional (rótulo numa linha, valor na linha de baixo).
    Lê via extract_tables (célula 'RÓTULO\\nVALOR') e cai p/ regex de linha simples.
    NÃO retorna denominação/município — o Memorial é a fonte autoritativa desses.
    """
    full = ""
    tables = []
    with _open(src) as pdf:
        for page in pdf.pages:
            full += (page.extract_text() or "") + "\n"
            tables.extend(page.extract_tables() or [])

    out = {}
    m = re.search(r"(\d{3}\.\d{3}\.\d{3}\.\d{3}-\d)", full)
    if m:
        out["ccir_codigo"] = m.group(1)

    # 1) Formulário real: célula "RÓTULO (ha)\n102,9640" (tables = lista de TABELAS)
    for table in tables:
        for row in (table or []):
            for cell in (row or []):
                texto = str(cell) if cell else ""
                if "\n" not in texto:
                    continue
                label, _, valor = texto.partition("\n")
                label_u = label.upper()
                for campo, chave, _rx in _CCIR_NUM:
                    if campo not in out and chave in label_u:
                        mv = re.search(r"\d[\d.,]*", valor)
                        if mv:
                            out[campo] = _num(mv.group(0))

    # 2) Layout simples: "RÓTULO (ha) 96,8180" na MESMA linha (só espaços/tabs, não cruza \n)
    for campo, _chave, rx in _CCIR_NUM:
        if campo in out:
            continue
        mm = re.search(rx + r"[ \t]*(\d[\d.,]*)", full)
        if mm:
            out[campo] = _num(mm.group(1))

    # Classificação fundiária: linha simples OU linha-abaixo-do-rótulo
    mc = re.search(r"CLASSIFICA[ÇC][ÃA]O FUND[IÍ][ÁA]RIA\s+(.+?)\s+(?:DATA|\d{2}/\d{2}/\d{4})", full)
    if mc:
        out["ccir_classificacao"] = _clean(mc.group(1))
    else:
        linhas = full.splitlines()
        for i, l in enumerate(linhas):
            if "CLASSIFICAÇÃO FUNDIÁRIA" in l.upper() and i + 1 < len(linhas):
                mv = re.search(r"^[\d.,]+\s+(.+?)\s+\d{2}/\d{2}/\d{4}", linhas[i + 1])
                if mv:
                    out["ccir_classificacao"] = _clean(mv.group(1))
                break
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Parser da CERTIDÃO DE MATRÍCULA (imóvel de ORIGEM — o que será desmembrado)
# ──────────────────────────────────────────────────────────────────────────────
# A certidão de inteiro teor traz a área/perímetro REGISTRAL do imóvel inteiro
# (ex.: 102,9640 ha) — distinta da parcela SIGEF (Parte I). É texto livre, então
# os padrões são tolerantes (melhor-esforço; o usuário pode corrigir na tela).
def parse_matricula_text(full: str) -> dict:
    out = {}

    def grab(pat):
        m = re.search(pat, full, re.IGNORECASE)
        return _clean(m.group(1)) if m else None

    mat = grab(r"Matr[íi]cula\s*N?[ºo°.]?\s*([\d.]+)")
    if mat:
        out["matricula"] = mat.strip(".")
    livro = grab(r"\blivro\s*0*(\d+)")
    if livro:
        out["livro"] = livro
    den = grab(r"denominad[ao]\s*[\"'“”']?\s*([A-ZÀ-Ÿ0-9][^\"'“”'\n,;]+)")
    if den:
        out["denominacao_matricula"] = den.strip(" .,-")
    out["area_matricula"] = _num(grab(r"[áa]rea\s+de\s*([\d.]+,\d+|\d+)\s*ha"))
    out["perimetro_matricula"] = _num(grab(r"Per[íi]metro:?\s*([\d.]+,\d+|\d+)\s*m\b"))
    mun = grab(r"cidade\s+de\s+([A-ZÀ-Ÿ][^,\n]+?)(?:,|\s+Estado|\s+Munic[íi]pio)")
    if mun:
        out["municipio_matricula"] = mun
    nirf = grab(r"NIRF:?\s*([\d.\-]+)")
    if nirf:
        out["nirf"] = nirf.rstrip(".")
    incra = grab(r"INCRA:?\s*([\d.\-]{8,})")
    if incra:
        out["incra_matricula"] = incra
    # Serventia + comarca da CERTIDÃO (fonte registral autoritativa — prioritária
    # sobre o CNS, cuja tabela pode trazer a cidade desatualizada). Best-effort.
    out.update(parse_serventia_text(full))
    return {k: v for k, v in out.items() if v not in (None, "")}


# Cabeçalho da certidão de inteiro teor: serventia (cartório) + comarca/UF.
# Ex.: "OFÍCIO ÚNICO DE SÃO FRANCISCO DO BREJÃO ... CNS 03.169-0 ... no município
# de São Francisco do Brejão/MA". O layout varia por cartório — captura tolerante.
_SERVENTIA_NOME_RE = re.compile(
    r"((?:OF[ÍI]CIO\s+[ÚU]NICO|OF[ÍI]CIO\s+DE\s+REGISTRO|CART[ÓO]RIO|SERVENTIA"
    r"|TABELIONATO|REGISTRO\s+DE\s+IM[ÓO]VEIS)[A-ZÀ-Ÿ0-9ºª°/.\-\s]*?DE\s+"
    r"[A-ZÀ-Ÿ][A-ZÀ-Ÿ\s]+?)(?=\s*[\(,;]|\s+CNS|\s+Tabeli|\s*\n|\s*$)",
    re.IGNORECASE,
)
_COMARCA_RE = re.compile(
    r"COMARCA\s+DE\s+([A-ZÀ-Ÿ][A-Za-zÀ-ÿ'´`\s]+?)(?:\s*[/\-]\s*([A-Z]{2}))?"
    r"(?=\s*[,;.\n]|\s+Estado|\s*$)",
    re.IGNORECASE,
)
_MUN_UF_RE = re.compile(
    r"munic[íi]pio\s+de\s+([A-ZÀ-Ÿ][A-Za-zÀ-ÿ'´`\s]+?)\s*[/\-]\s*([A-Z]{2})\b",
    re.IGNORECASE,
)


def parse_serventia_text(full: str) -> dict:
    """Extrai serventia (cartório), comarca/município e UF do texto da certidão."""
    out = {}
    mn = _SERVENTIA_NOME_RE.search(full)
    if mn:
        nome = _clean(mn.group(1)).rstrip(" ,.;-")
        # descarta capturas degeneradas (curtas demais p/ ser uma serventia)
        if len(nome) >= 10:
            out["cartorio_nome"] = nome
    mc = _COMARCA_RE.search(full)
    if mc:
        out["cartorio_municipio"] = _clean(mc.group(1)).rstrip(" ,.;-")
        if mc.group(2):
            out["cartorio_uf"] = mc.group(2).upper()
    if "cartorio_municipio" not in out:
        mm = _MUN_UF_RE.search(full)
        if mm:
            out["cartorio_municipio"] = _clean(mm.group(1)).rstrip(" ,.;-")
            out["cartorio_uf"] = mm.group(2).upper()
    return {k: v for k, v in out.items() if v}


def parse_matricula(src: PdfSource) -> dict:
    """Lê a certidão de inteiro teor (PDF) e extrai os dados REGISTRAIS do imóvel
    de origem: matrícula, livro, denominação, ÁREA e PERÍMETRO da matrícula, NIRF."""
    full = ""
    with _open(src) as pdf:
        for page in pdf.pages:
            full += (page.extract_text() or "") + "\n"
    return parse_matricula_text(full)


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
            # INCRA/SNCR: aceita "INCRA: 1100...", "INCRA/SNCR 1100...", "INCRA 1100..."
            mi = re.search(r"INCRA(?:/SNCR)?[^\d]{0,4}(\d{6,})", p)
            if mi:
                out["incra"] = mi.group(1)
    desc = out["descricao"] or ""
    mat = (out["matricula"] or "").strip()
    # Agrupa por MATRÍCULA (mesma matrícula = mesmo confrontante → 1 DRL).
    # Matrícula "0"/vazia (via pública etc.) agrupa pela descrição.
    out["key"] = mat if (mat and mat != "0") else f"0|{desc[:40]}"
    return out


def _eh_limpo(s: str) -> bool:
    """Nome/descrição utilizável (não mascarado pelo SIGEF com X.../***/...)."""
    s = (s or "").strip()
    return bool(s) and "XXX" not in s.upper() and "*" not in s and "..." not in s


def classificar_confrontante(g: dict, matricula_imovel: str = None) -> str:
    """Classifica o confrontante em proprio/via_publica/particular e RECUPERA o
    código INCRA/SNCR da descrição quando faltar (self-heal de dados já extraídos).

    BEM PÚBLICO (dispensa anuência) SÓ quando a divisa é realmente pública
    (estrada/rio/servidão/via) OU não há QUALQUER identificação do confrontante.
    Um imóvel rural TITULADO/CERTIFICADO (Fazenda com INCRA/SNCR, CNS ou nome),
    mesmo SEM matrícula, é PARTICULAR e EXIGE anuência (Prov. CNJ 195/2025 +
    Lei 10.267/2001 + Decreto 4.449/2002, art. 9º).
    """
    desc = g.get("descricao") or g.get("imovel") or ""
    if not g.get("incra"):
        mi = re.search(r"INCRA(?:/SNCR)?[^\d]{0,4}(\d{6,})", desc)
        if mi:
            g["incra"] = mi.group(1)
    mat = (g.get("matricula") or "").strip()
    incra = (g.get("incra") or "").strip()
    cpf = (g.get("cpf_cnpj") or "").strip()
    cns = (g.get("cns") or "").strip()
    eh_publica = bool(_VIA_PUBLICA_RE.search(desc))
    sem_id = not (desc.strip() or _eh_limpo(g.get("nome"))
                  or (mat and mat != "0") or incra or cpf or cns)
    if matricula_imovel and mat and mat == str(matricula_imovel).strip():
        return "proprio"
    if eh_publica or sem_id:
        return "via_publica"
    return "particular"


def agrupar_confrontantes(vertices: List[dict], matricula_imovel: str = None) -> List[dict]:
    """Agrupa os segmentos por confrontante. Marca tipo via_publica/proprio/particular."""
    grupos = {}
    for v in vertices:
        info = parse_confrontacao(v.get("confrontacao_raw", ""))
        k = info["key"]
        if k not in grupos:
            grupos[k] = {**info, "imovel": info.get("descricao"), "segmentos": []}
        else:
            g = grupos[k]
            # mescla: prefere o segmento com nome/descrição LIMPOS (não mascarados)
            if _eh_limpo(info.get("nome")) and not _eh_limpo(g.get("nome")):
                g["nome"] = info["nome"]
            if _eh_limpo(info.get("descricao")) and not _eh_limpo(g.get("descricao")):
                g["descricao"] = info["descricao"]
                g["imovel"] = info["descricao"]
            for campo in ("cpf_cnpj", "incra", "cns", "certificacao"):
                if not g.get(campo) and info.get(campo):
                    g[campo] = info[campo]
        grupos[k]["segmentos"].append(v.get("codigo"))

    saida = []
    for g in grupos.values():
        g["tipo"] = classificar_confrontante(g, matricula_imovel)
        # nome mascarado (XXX/***) → usa a descrição limpa, senão zera (cai p/ matrícula)
        nome = g.get("nome")
        if nome and not _eh_limpo(nome):
            g["nome"] = g["descricao"] if _eh_limpo(g.get("descricao")) else None
        saida.append(g)
    return saida
