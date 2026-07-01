# @module services.geo_urbano.extractor — extração dos documentos urbanos (J&G real).
#
# Parsers calibrados nos PDFs REAIS do caso J&G (pdfplumber):
#   • BCI (Boletim de Cadastro Imobiliário) — layout rótulo/valor em 2 linhas
#   • IPTU (DAM) e CND (Certidão Negativa) — regularidade fiscal por imóvel
#   • Mapa de Remembramento — planilha de vértices + quadro de áreas + CMI/matrículas
#   • Matrícula (certidão de inteiro teor) — TEXTO (via OCR; certidões são imagem)
# Todos best-effort: retornam o que acharem, None no que faltar. A reconciliação
# e a conferência manual cobrem o resto.
from __future__ import annotations

import io
import re
import uuid
from typing import List, Optional

_LOC = r"\d{2}\.\d{2}\.\d{3}\.\d{4}\.\d{5}"


def _texto(pdf_bytes: bytes) -> str:
    """Texto de um PDF (pdfplumber; fallback PyMuPDF)."""
    txt = ""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            txt = "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:  # noqa: BLE001
        txt = ""
    if len(txt.strip()) < 40:
        try:
            import fitz
            d = fitz.open("pdf", pdf_bytes)
            txt = "\n".join(d[i].get_text() for i in range(d.page_count))
        except Exception:  # noqa: BLE001
            pass
    return txt


def ocr_pdf(pdf_bytes: bytes, max_paginas: int = 6, dpi: int = 220) -> str:
    """OCR de um PDF escaneado (matrículas/CNH são imagem). '' se tesseract ausente."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except Exception:  # noqa: BLE001
        return ""
    out = []
    try:
        d = fitz.open("pdf", pdf_bytes)
        for i in range(min(max_paginas, d.page_count)):
            pix = d[i].get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            out.append(pytesseract.image_to_string(img, lang="por"))
    except Exception:  # noqa: BLE001
        return ""
    return "\n".join(out)


def _num(s) -> Optional[float]:
    if s is None:
        return None
    s = str(s).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _so_digitos(s) -> str:
    return re.sub(r"\D", "", s or "")


def _busca(rx, txt, grupo=1, flags=re.IGNORECASE):
    m = re.search(rx, txt, flags)
    return m.group(grupo).strip() if m else None


# ──────────────────────────────────────────────────────────────────────────────
# BCI — Boletim de Cadastro Imobiliário
# ──────────────────────────────────────────────────────────────────────────────
def parse_bci(pdf_bytes: bytes) -> dict:
    t = _texto(pdf_bytes)
    out = {}
    m = re.search(rf"(\d{{10}})\s+({_LOC})\s+\d+\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)\s+(\w+)\s+(\w+)", t)
    if m:
        out["cod_imovel"] = m.group(1)
        out["loc_cartografica"] = m.group(2)
        out["situacao"] = m.group(6)
        out["natureza"] = m.group(7)
    out["inscricao_contribuinte"] = _busca(r"Inscri[çc][ãa]o do Contribuinte\s+(\d+)", t)
    cnpj = _busca(r"CPF/CNPJ\s+(\d+)", t)
    # proprietário = linha após "Nome do Proprietário ou detentor"
    mp = re.search(r"Nome do Propriet[áa]rio ou detentor\s*\n\s*(.+)", t, re.IGNORECASE)
    nome = mp.group(1).strip() if mp else None
    out["proprietario_cadastral"] = {"nome": nome, "doc": cnpj}
    # logradouro (endereço)
    out["endereco"] = _busca(r"\n\s*\d+\s+((?:RUA|AV|AVENIDA|TRAVESSA|ROD|ALAMEDA)\b.+?)\s+\d{3,4}\s+\d{8}", t)
    # bairro + data de cadastro
    mb = re.search(r"\n\s*\d+\s+(.+?)\s+\d+\s+\d+\s+LOTE:\s*\d+\s+(\d{2}/\d{2}/\d{4})", t)
    if mb:
        out["bairro"] = mb.group(1).strip()
        out["data_cadastro"] = mb.group(2)
    # medidas (testada, prof, área edif, área terreno, área total)
    mm = re.search(r"[ÁA]rea Total da Edifica[çc][ãa]o\s*\n\s*\d+\s+\d+\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)", t)
    if mm:
        out["testada_principal_m"] = _num(mm.group(1))
        out["profundidade_m"] = _num(mm.group(2))
        out["area_edificada_m2"] = _num(mm.group(3))
        out["area_terreno_m2"] = _num(mm.group(4))
    return {k: v for k, v in out.items() if v not in (None, "")}


# ──────────────────────────────────────────────────────────────────────────────
# IPTU (DAM) — regularidade fiscal (parcelamento)
# ──────────────────────────────────────────────────────────────────────────────
def parse_iptu(pdf_bytes: bytes) -> dict:
    t = _texto(pdf_bytes)
    out = {"via_regularidade": "guia_paga"}
    m = re.search(r"(\d+)\s+\d+\s+\d+\s+\d{3}/\d{3}\s+PARCELAMENTO\s+IPTU\s+(\d+)\s+(\d{2}/\d{2}/\d{4})", t)
    if m:
        out["acordo_numero"] = m.group(2)
        out["vencimento"] = m.group(3)
        out["situacao"] = "debito_parcelado"
    out["acordo_numero"] = out.get("acordo_numero") or _busca(r"N[ºo]\s*Acordo\s*(\d+)", t) or _busca(r"Acordo No\.?\s*(\d+)", t)
    out["valor"] = _num(_busca(r"VALOR COBRADO\s*([\d.,]+)", t))
    out["loc_cartografica"] = _busca(rf"Loc\.?\s*Cart\.?\s*({_LOC})", t)
    out["cod_imovel"] = _busca(r"Insc do Im[óo]vel\s*(\d+)", t)
    ex = _busca(r"Exercicio\(s\):\s*([\d,\s]+)", t)
    if ex:
        out["exercicios"] = [e for e in re.split(r"[,\s]+", ex.strip()) if e.isdigit()]
    if not out.get("situacao"):
        out["situacao"] = "debito_parcelado" if re.search(r"PARCELAMENTO", t, re.I) else "debito_aberto"
    return {k: v for k, v in out.items() if v not in (None, "", [])}


# ──────────────────────────────────────────────────────────────────────────────
# CND — Certidão Negativa do Imóvel
# ──────────────────────────────────────────────────────────────────────────────
def parse_cnd(pdf_bytes: bytes) -> dict:
    t = _texto(pdf_bytes)
    out = {"via_regularidade": "cnd", "situacao": "cnd_negativa"}
    out["cnd_numero"] = _busca(r"CERTID[ÃA]O NEGATIVA[^\n]*\n\s*N[ºo]\s*(\d+)", t) or _busca(r"\bN[ºo]\s*(\d{6,})", t)
    val = _busca(r"VALIDA AT[ÉE]:?\s*(\d{2}/\d{2}/\d{4})", t)
    if val:
        d, mth, y = val.split("/")
        out["cnd_validade"] = f"{y}-{mth}-{d}"
    out["loc_cartografica"] = _busca(rf"LOC\.?\s*CARTOGRAFICA\s*({_LOC})", t)
    out["cod_imovel"] = _busca(r"INSC\.?\s*DO\s*IM[ÓO]VEL\s*(\d+)", t)
    return {k: v for k, v in out.items() if v not in (None, "")}


# ──────────────────────────────────────────────────────────────────────────────
# Mapa de Remembramento — planilha de vértices + quadro de áreas + CMI/matrículas
# ──────────────────────────────────────────────────────────────────────────────
_VERTICE_RE = re.compile(
    r"([A-Z]+-P-\w+)\s+([A-Z]+-P-\w+)\s+([\d.]+,\d+)\s+([\d.]+,\d+)\s+"
    r"(\d+°\d+'\d+\")\s+([\d.,]+)\s*m?\s+([\d,]+)\s+([\d°'\",.]+\"?[SN])\s+([\d°'\",.]+\"?[WE])")


def _f_num(x):
    """float tolerante (aceita BR '226.466,3304' / '50,00' ou número)."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def alinhar_coords_aos_vertices(vertices: list) -> list:
    """Algumas planilhas de mapa listam, em cada linha 'De→Para', a COORDENADA do
    vértice PARA (destino), não do De — então as posições ficam deslocadas em 1 e o
    desenho/Memorial não batem com as medidas. Detecta o offset comparando a
    distância entre coords consecutivas com a distância tabelada e, se for o caso,
    desloca coord_n/coord_e/latitude/longitude um vértice para trás (cada vértice
    passa a carregar a SUA posição). Azimute/distância/fator_k ficam no vértice De.
    Idempotente e seguro: só desloca quando a evidência é clara."""
    import math
    vs = sorted(vertices or [], key=lambda v: v.get("ordem", 0))
    n = len(vs)
    if n < 3:
        return vertices
    e0, n0 = _f_num(vs[0].get("coord_e")), _f_num(vs[0].get("coord_n"))
    e1, n1 = _f_num(vs[1].get("coord_e")), _f_num(vs[1].get("coord_n"))
    d0, d1 = _f_num(vs[0].get("distancia_m")), _f_num(vs[1].get("distancia_m"))
    if None in (e0, n0, e1, n1, d0, d1):
        return vertices
    dcalc = math.hypot(e1 - e0, n1 - n0)
    # coord=De → dcalc≈d0 ; coord=Para (deslocado) → dcalc≈d1
    if abs(dcalc - d1) + 0.5 < abs(dcalc - d0):
        pos = [(v.get("coord_n"), v.get("coord_e"), v.get("latitude"), v.get("longitude")) for v in vs]
        for i, v in enumerate(vs):
            cn, ce, lat, lon = pos[(i - 1) % n]
            v["coord_n"], v["coord_e"], v["latitude"], v["longitude"] = cn, ce, lat, lon
    return vertices


def parse_mapa(pdf_bytes: bytes) -> dict:
    t = _texto(pdf_bytes)
    out = {}
    vertices = []
    for i, m in enumerate(_VERTICE_RE.finditer(t)):
        vertices.append({
            "ordem": i + 1, "de": m.group(1), "para": m.group(2),
            "coord_n": _num(m.group(3)), "coord_e": _num(m.group(4)),
            "azimute": m.group(5), "distancia_m": _num(m.group(6)), "fator_k": _num(m.group(7)),
            "latitude": m.group(8), "longitude": m.group(9),
        })
    if vertices:
        out["vertices"] = alinhar_coords_aos_vertices(vertices)
    out["area_declarada_m2"] = _num(_busca(r"[ÁA]rea:\s*([\d.,]+)\s*m", t))
    out["perimetro_m"] = _num(_busca(r"Per[íi]metro:\s*([\d.,]+)\s*m", t))
    out["cmi_resultante"] = _busca(rf"CIM:\s*({_LOC})", t)
    cad_novo = _busca(r"Cadastro Novo:\s*\n?\s*(QD[^\n]+)", t)
    cad_ant = _busca(r"Cadastro Antigo:\s*\n?\s*(QD[^\n]+)", t)
    out["cadastro_novo"] = cad_novo
    out["cadastro_antigo"] = cad_ant
    mats = _busca(r"MATR[ÍI]CULA\(S\):\s*\n?\s*([\d./]+)", t)
    if mats:
        out["matriculas_numeros"] = [x for x in mats.split("/") if x.strip()]
    # quadro de áreas: cod_imovel + loc por lote. O lote vem do 4º segmento da
    # localização cartográfica (DD.SS.QQQQ.LLLL.UUUUU) — robusto ao texto do mapa
    # que às vezes corrompe o sufixo "( QD41 - Lote NN )".
    lotes, vistos = [], set()
    for m in re.finditer(rf"C[óo]d im[óo]vel:\s*(\d+)\s*-\s*Loc\.\s*Cartogr[áa]fica:\s*({_LOC})", t):
        cod, loc = m.group(1), m.group(2)
        if loc in vistos:
            continue
        vistos.add(loc)
        seg = loc.split(".")
        lote = (seg[3].lstrip("0") or "0").zfill(2) if len(seg) >= 4 else None
        lotes.append({"cod_imovel": cod, "loc_cartografica": loc, "lote": lote})
    if lotes:
        out["lotes_quadro"] = sorted(lotes, key=lambda x: x.get("lote") or "")
    return {k: v for k, v in out.items() if v not in (None, "", [])}


# ──────────────────────────────────────────────────────────────────────────────
# Memorial Descritivo URBANO em PROSA (usucapião georreferenciada, N/E UTM).
# Formato: "Inicia-se a descrição ... no vértice X, de coordenadas N ... e E ...;
# ... segue confrontando com NOME ... : AZ e DIST m até o vértice Y, de coordenadas
# ...". Distinto do parse_mapa (planilha tabular). Calibrado no Memorial da Lindaura.
# ──────────────────────────────────────────────────────────────────────────────
# Azimute tolerante a variações de extração (° pode vir como º/o; aspas '/′/"/″; espaços).
_AZ = r"[0-9][0-9°ºoO'′`´\"″:\s.,\-]*?"


def _parse_memorial_texto(t: str) -> dict:
    """Roda os regexes sobre UM texto já normalizado (whitespace colapsado)."""
    out: dict = {}
    coords = {}
    for m in re.finditer(r"v[ée]rtice\s*([\w.\-]+)[,\s]*de\s*coordenadas?\s*N\s*([\d.,]+)\s*m?\s*e\s*E\s*([\d.,]+)", t):
        coords[m.group(1)] = (_num(m.group(2)), _num(m.group(3)))
    ini = re.search(r"\bno\s*v[ée]rtice\s*([\w.\-]+)", t)
    de = ini.group(1) if ini else None
    pat = re.compile(
        r"confrontando\s*com\s*(?P<conf>.+?)(?:,?\s*inscrito|,?\s*com\s*os\s*seguintes)"
        r"|(?P<az>" + _AZ + r")\s*e\s*(?P<dist>[\d.,]+)\s*m\s*at[ée]\s*o\s*v[ée]rtice\s*(?P<para>[\w.\-]+)")
    cur, ordem, verts = None, 0, []
    for m in pat.finditer(t):
        if m.group("conf"):
            cur = re.sub(r"\s+", " ", m.group("conf")).strip(" .,")
        elif de:
            ordem += 1
            cn, ce = coords.get(de, (None, None))
            verts.append({
                "ordem": ordem, "de": de, "para": m.group("para"),
                "coord_n": cn, "coord_e": ce, "azimute": (m.group("az") or "").strip(),
                "distancia_m": _num(m.group("dist")), "confrontante_lado": cur,
            })
            de = m.group("para")
    if verts:
        out["vertices"] = verts
    am = re.search(r"[ÁA]rea\s*\(?\s*m.{0,4}\)?\s*:?\s*([\d.,]+)", t)
    pm = re.search(r"[Pp]er[íi]metro\s*\(?\s*m\)?\s*:?\s*([\d.,]+)", t)
    if am:
        out["area_declarada_m2"] = _num(am.group(1))
    if pm:
        out["perimetro_m"] = _num(pm.group(1))
    den = re.search(r"Im[óo]vel:\s*(.+?)\s*(?:Propriet|CPF|$)", t)
    if den:
        out["denominacao"] = den.group(1).strip(" .,")
    loc = re.search(_LOC, t)
    if loc:
        out["cmi_resultante"] = loc.group(0)
        ctrl = re.search(_LOC + r"\s*-\s*(\d{1,3})", t)
        if ctrl:
            out["cmi_controle"] = ctrl.group(1)
    return {k: v for k, v in out.items() if v not in (None, "", [])}


def _textos_candidatos(pdf_bytes: bytes) -> list:
    """Várias extrações de texto (pdfplumber + PyMuPDF + OCR) — o layout/versão da lib
    muda o espaçamento; tentamos todas e escolhemos a que rende mais vértices."""
    cands = []
    t1 = _texto(pdf_bytes) or ""
    if t1.strip():
        cands.append(t1)
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        t2 = "\n".join(p.get_text("text") for p in doc)
        if t2.strip():
            cands.append(t2)
    except Exception:  # noqa: BLE001
        pass
    if not cands:
        try:
            cands.append(ocr_pdf(pdf_bytes))
        except Exception:  # noqa: BLE001
            pass
    return cands


def parse_memorial_usucapiao(pdf_bytes: bytes) -> dict:
    """Memorial Descritivo em PROSA: tenta cada motor de texto e fica com o melhor."""
    melhor = {}
    for raw in _textos_candidatos(pdf_bytes):
        t = re.sub(r"\s+", " ", raw)
        r = _parse_memorial_texto(t)
        if len(r.get("vertices") or []) > len(melhor.get("vertices") or []):
            melhor = r
        elif not melhor:
            melhor = r
    return melhor


# ──────────────────────────────────────────────────────────────────────────────
# Matrícula (certidão) — parser de TEXTO (vem do OCR; certidões são imagem)
# ──────────────────────────────────────────────────────────────────────────────
_DOC_RE = r"(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|\d{3}\.?\d{3}\.?\d{3}-?\d{2})"


def _limpa_nome(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip(" -–.,")).strip()


def _titular_atual(t: str) -> dict:
    """Proprietário REGISTRAL atual = ADQUIRENTE do ÚLTIMO registro; se não houver
    transmissão, o PROPRIETÁRIO(A) do cabeçalho (Registro Geral)."""
    pre = (r"(?:a\s+firma\s+|a\s+empresa\s+|a\s+sociedade\s+|o[as]?\s+s[rn][ao]?\.?\s+)?")
    nome_rx = r"([A-Z0-9À-Ÿ&][A-Z0-9À-Ÿ&.\s/'\"-]{3,90}?)\s*(?:,|\.|\bpessoa\b|\bbrasileir|\binscrit|\bportador|\bCNPJ|\bCPF)"
    cand = list(re.finditer(r"ADQUIRENTE\(?S?\)?\s*[-–:]+\s*" + pre + nome_rx, t, re.IGNORECASE))
    if not cand:
        cand = list(re.finditer(r"PROPRIET[ÁA]RIO\(?A?\)?\s*:?\s*" + pre + nome_rx, t, re.IGNORECASE))
    if not cand:
        return {}
    m = cand[-1]
    trecho = t[m.end(): m.end() + 320]
    doc = re.search(_DOC_RE, trecho)
    return {"nome": _limpa_nome(m.group(1)), "doc": doc.group(1) if doc else None}


def parse_art_trt(pdf_bytes: bytes, filename: str = "") -> Optional[str]:
    """Número da ART/TRT/RRT a partir do upload (texto → OCR → nome do arquivo)."""
    t = _texto(pdf_bytes) or ""
    if len(t.strip()) < 40:
        t = ocr_pdf(pdf_bytes, max_paginas=2) or t
    # 1) código CFT (Conselho Federal dos Técnicos): CFT + dígitos (+ -UF)
    m = re.search(r"\bCFT\s?\d{8,}(?:[-/]?[A-Z]{2})?", t)
    if m:
        return re.sub(r"\s+", "", m.group(0))
    # 2) ART/TRT/RRT nº …
    m = re.search(r"\b(ART|TRT|RRT)\b\D{0,25}(\d[\d./-]{5,})", t, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()} nº {m.group(2)}"
    # 3) fallback: nome do arquivo (ex.: CFT2605953795.7B6Y6.pdf)
    fn = re.search(r"CFT\s?\d{8,}", filename or "", re.IGNORECASE)
    if fn:
        return re.sub(r"\s+", "", fn.group(0)).upper()
    return None


def parse_matricula_text(t: str) -> dict:
    out = {}
    out["matricula"] = _busca(r"MATR[ÍI]CULA\s*n?[ºo°.]?\s*([\d.]+)", t)
    out["livro"] = _busca(r"Livro\s*n?[ºo°.]*\s*(\d+\s*-?\s*[A-Z]{0,4})", t)
    if out.get("livro"):
        out["livro"] = re.sub(r"\s+", "", out["livro"])
    out["folhas"] = _busca(r"\bf[lo]?s?\.?\s*(\d+)", t)
    out["lote_origem"] = _busca(r"Lote\s*n?[ºo°.]?\s*(\d+)", t)
    out["quadra"] = _busca(r"Quadra\s*n?[ºo°.]?\s*(\d+)", t)
    out["area_m2"] = _num(_busca(r"[ÁA]rea\s*(?:de)?\s*([\d.,]+)\s*m", t))
    tit = _titular_atual(t)
    if tit.get("nome"):
        out["proprietario_registral"] = tit
    # confrontações: "Frente: 15,00m (quinze metros) para a Rua Inglaterra, Lateral
    # direita: 20,00m para o lote nº 02, ...". O confrontante para no PRÓXIMO lado /
    # "com a área" / fim — não engole o resto da frase.
    _STOP = r"(?=\s*(?:Lateral\s+(?:direita|esquerda)|Frente|Fundos?|com\s+a\s+[áa]rea|N[ºo°.]\s*DO\s*REGISTRO|;|$))"
    confs = []
    for lado, chave in (("FRENTE", "frente"), ("LATERAL\\s+DIREITA", "lateral_direita"),
                        ("LATERAL\\s+ESQUERDA", "lateral_esquerda"), ("FUNDOS?", "fundo")):
        mm = re.search(
            rf"{lado}\s*[:\-]?\s*([\d.,]+)\s*m\s*(?:\([^)]*\)\s*)?(.+?){_STOP}",
            t, re.IGNORECASE | re.DOTALL)
        if mm:
            conf = re.sub(r"\([^)]*\)", "", mm.group(2))                       # tira "(quinze metros)"
            conf = re.sub(r"^(?:com|para)\s+(?:o[as]?|a[s]?)?\s*", "", conf.strip(), flags=re.IGNORECASE)
            conf = re.sub(r"\s+", " ", conf).strip(" ,.;-")
            confs.append({"lado": chave, "medida_m": _num(mm.group(1)), "confrontante": conf or None})
    if confs:
        out["confrontacoes"] = confs
    return {k: v for k, v in out.items() if v not in (None, "")}


# ──────────────────────────────────────────────────────────────────────────────
# Orquestração: a partir dos uploads (bytes), monta os campos do projeto
# ──────────────────────────────────────────────────────────────────────────────
def extrair_tudo(uploads_bytes: dict) -> dict:
    """uploads_bytes = {tipo: [bytes,...]}. Retorna campos extraídos do projeto."""
    res: dict = {"avisos": []}

    # 1) Vértices/área/perímetro/CMI — do MEMORIAL (usucapião, prosa) OU do MAPA (planilha).
    #    O Memorial georreferenciado em prosa tem prioridade quando enviado (usucapião urbana).
    mem_raw = (uploads_bytes.get("memorial_usucapiao") or [None])[0]
    mapa_raw = (uploads_bytes.get("mapa_remembramento") or [None])[0]
    lotes_quadro = []
    mat_numeros = []
    if mem_raw:
        mp = parse_memorial_usucapiao(mem_raw)
        for k in ("vertices", "area_declarada_m2", "perimetro_m", "cmi_resultante",
                  "cmi_controle", "denominacao"):
            if mp.get(k) is not None:
                res[k] = mp[k]
        if not mp.get("vertices"):
            res["avisos"].append("Memorial enviado, mas não foi possível extrair os vértices — confira o layout/PDF.")
    elif mapa_raw:
        mp = parse_mapa(mapa_raw)
        for k in ("vertices", "area_declarada_m2", "perimetro_m", "cmi_resultante",
                  "cadastro_novo", "cadastro_antigo"):
            if mp.get(k) is not None:
                res[k] = mp[k]
        lotes_quadro = mp.get("lotes_quadro") or []
        mat_numeros = mp.get("matriculas_numeros") or []
    else:
        res["avisos"].append("Planta/Mapa (ou Memorial) não enviado — vértices/área não extraídos.")

    # 2) Matrículas: lista autoritativa = nºs do mapa (ordem do lote 01..N); anexa
    #    cod_imóvel/localização do quadro de áreas casando pelo nº do lote.
    matriculas = []
    quadro_por_lote = {lo.get("lote"): lo for lo in lotes_quadro}
    fonte = mat_numeros or [lo.get("lote") and None for lo in lotes_quadro]
    n = max(len(mat_numeros), len(lotes_quadro))
    for i in range(n):
        lote = str(i + 1).zfill(2)
        q = quadro_por_lote.get(lote, {})
        matriculas.append({
            "id": str(uuid.uuid4()),
            "ordem": i + 1, "lote_origem": lote, "quadra": "41",
            "cod_imovel": q.get("cod_imovel"), "loc_cartografica": q.get("loc_cartografica"),
            "matricula": mat_numeros[i] if i < len(mat_numeros) else None,
            "area_m2": 300.0, "loteamento": "Parque das Nações",
            "proprietario_registral": {}, "confrontacoes": [], "cadeia": [],
        })
    # OCR das certidões (se tesseract disponível) — enriquece a matrícula correspondente
    cert_list = uploads_bytes.get("certidao_inteiro_teor") or []
    # Sem planilha de mapa (usucapião / imóvel único) a CERTIDÃO é a fonte da matrícula.
    sem_mapa = not mat_numeros and not lotes_quadro
    ocr_ok = 0
    for raw in cert_list:
        texto = ocr_pdf(raw)
        if not texto:
            continue
        ocr_ok += 1
        dados = parse_matricula_text(texto)
        alvo = None
        if dados.get("matricula"):
            alvo = next((m for m in matriculas if (m.get("matricula") or "").replace(".", "") == dados["matricula"].replace(".", "")), None)
        if not alvo and dados.get("lote_origem"):
            alvo = next((m for m in matriculas if m.get("lote_origem") == dados["lote_origem"]), None)
        # Usucapião: cria o registro da matrícula a partir da certidão (senão a matrícula
        # lida pelo OCR seria descartada por não haver planilha de mapa).
        if not alvo and sem_mapa:
            alvo = {"id": str(uuid.uuid4()), "ordem": len(matriculas) + 1,
                    "proprietario_registral": {}, "confrontacoes": [], "cadeia": []}
            matriculas.append(alvo)
        if alvo:
            for k, v in dados.items():
                if v:
                    alvo[k] = v
    # Usucapião sem certidão legível: semeia UMA matrícula com os dados do Memorial
    # (denominação/CIM) para o imóvel usucapiendo ter registro a conferir/preencher.
    if sem_mapa and not matriculas and (res.get("denominacao") or res.get("cmi_resultante")):
        matriculas.append({
            "id": str(uuid.uuid4()), "ordem": 1,
            "denominacao": res.get("denominacao"),
            "loc_cartografica": res.get("cmi_resultante"),
            "proprietario_registral": {}, "confrontacoes": [], "cadeia": [],
        })
    if cert_list and ocr_ok == 0:
        res["avisos"].append("Certidões enviadas são imagem e o OCR não está disponível neste ambiente — "
                             "matrículas/confrontações precisam ser preenchidas/conferidas manualmente.")
    if matriculas:
        res["matriculas"] = matriculas

    # 3) BCI — um por arquivo; vincula à matrícula por cod_imovel
    bci = []
    for raw in (uploads_bytes.get("bci") or []):
        b = parse_bci(raw)
        if not b:
            continue
        cb = _so_digitos(b.get("cod_imovel"))
        alvo = next((m for m in matriculas if cb and _so_digitos(m.get("cod_imovel")) == cb), None)
        # Imóvel único (usucapião): 1 matrícula → o BCI é dela mesmo sem cod. na matrícula.
        if not alvo and len(matriculas) == 1:
            alvo = matriculas[0]
        if alvo:
            b["matricula_id"] = alvo.get("id")
            # enriquece a matrícula com os IDENTIFICADORES do BCI (preenche Cód./Loc. que o
            # OCR da certidão não pegou); NÃO copia área (mantém a checagem de divergência).
            if not alvo.get("cod_imovel") and b.get("cod_imovel"):
                alvo["cod_imovel"] = b["cod_imovel"]
            if not alvo.get("loc_cartografica") and b.get("loc_cartografica"):
                alvo["loc_cartografica"] = b["loc_cartografica"]
        bci.append(b)
    if bci:
        res["bci"] = bci

    # 4) IPTU/CND — regularidade fiscal por matrícula (vincula por loc/cod)
    iptu = []
    for tipo, parser in (("cnd_iptu", parse_cnd), ("guia_iptu", parse_iptu)):
        for raw in (uploads_bytes.get(tipo) or []):
            it = parser(raw)
            if not it:
                continue
            alvo = next((m for m in matriculas
                         if (it.get("loc_cartografica") and m.get("loc_cartografica") == it["loc_cartografica"])
                         or (it.get("cod_imovel") and _so_digitos(m.get("cod_imovel")) == _so_digitos(it.get("cod_imovel")))), None)
            if not alvo and len(matriculas) == 1:   # imóvel único → é desta matrícula
                alvo = matriculas[0]
            if alvo:
                it["matricula_id"] = alvo.get("id")
            iptu.append(it)
    if iptu:
        res["iptu"] = iptu

    return res
