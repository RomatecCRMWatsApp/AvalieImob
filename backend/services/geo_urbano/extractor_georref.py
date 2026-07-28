# @module services.geo_urbano.extractor_georref — Fase 6: extração dos MEMORIAIS.
#
# Lê os PDFs que o usuário JÁ tem (Memorial Descritivo de Coordenadas [MD-PER] +
# Memorial de Localização e Situação [MD-SIT]) e AUTO-PREENCHE o projeto:
# identificação (bairro/rua/quadra/lote/área/município/UF/CIM), vértices (coords
# N/E + azimute + distância + confrontante + feição) e a quadra (formato/vias/
# esquina). CALIBRADO no modelo real do usuário (QD04 LT20 · Residencial Ouro
# Verde/Açailândia). Os campos ficam EDITÁVEIS depois (autosave do wizard).
import io
import re
from typing import Optional


def _texto(pdf_bytes: bytes) -> str:
    """Texto do PDF — pdfplumber (memorial é texto vetorial), fitz de reserva."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:  # noqa: BLE001
        pass
    try:
        import fitz
        d = fitz.open(stream=pdf_bytes, filetype="pdf")
        return "\n".join(d[i].get_text() for i in range(d.page_count))
    except Exception:  # noqa: BLE001
        return ""


def _num(s) -> Optional[float]:
    """Número BR '9.450.853,30' → 9450853.30 / '25,00' → 25.0."""
    if s is None:
        return None
    t = str(s).strip()
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


# Vértice: "vértice P2, de coordenadas N 9.450.839,70m e E 224.083,76m; Muro;"
_RX_VERT = re.compile(
    r"v[ée]rtice\s+([\w\-.]+),?\s+de coordenadas\s+N\s+([\d.,]+)\s*m\s+e\s+E\s+([\d.,]+)\s*m;\s*([^;]*?);",
    re.IGNORECASE)
# Segmento: "confrontando com Lote nº 19, com os seguintes azimutes e distâncias: 122°56'38" e 25,00 m até o vértice P2"
_RX_SEG = re.compile(
    r"confrontando com\s+(.+?),?\s+com os seguintes azimutes e dist[âa]ncias:\s*([0-9°'\"´’”\s]+?)\s+e\s+([\d.,]+)\s*m\s+at[ée] o v[ée]rtice\s+([\w\-.]+)",
    re.IGNORECASE)


_VIAS_KW = {"rua", "avenida", "av", "travessa", "alameda", "rodovia", "estrada",
            "via", "viela", "praça", "praca", "r", "tv", "al", "rod"}


def _split_ident(valores: str):
    """'Residencial Ouro Verde Rua Fernando Pessoa 04 20' → (bairro, rua, quadra, lote).
    Quadra/Lote são os 2 últimos tokens; a rua começa no 1º logradouro; o resto é o bairro."""
    toks = valores.split()
    if len(toks) < 4:
        return None
    lote, quadra, resto = toks[-1], toks[-2], toks[:-2]
    idx = next((i for i, tk in enumerate(resto) if tk.lower().strip(".") in _VIAS_KW), None)
    if idx is not None:
        bairro, rua = " ".join(resto[:idx]).strip(), " ".join(resto[idx:]).strip()
    else:
        bairro, rua = " ".join(resto).strip(), ""
    return bairro, rua, quadra, lote


def parse_memorial_coordenadas(pdf_bytes: bytes) -> dict:
    """MD-PER — identificação + vértices (coords/azimute/dist/confrontante/feição)."""
    txt = _texto(pdf_bytes)
    if not txt:
        return {}
    dados: dict = {}
    # ── identificação inline ──
    m = re.search(r"[ÁA]rea:\s*([\d.,]+)", txt)
    if m:
        dados["area"] = _num(m.group(1))
    m = re.search(r"Munic[íi]pio:\s*(.+?)(?:\s+Estado:|\s*$)", txt)
    if m:
        dados["municipio"] = m.group(1).strip()
    m = re.search(r"Estado:\s*([A-Za-z]{2})", txt)
    if m:
        dados["uf"] = m.group(1).upper()
    m = re.search(r"CIM:\s*([\d.]+)\s*-\s*(\d+)", txt)
    if m:
        dados["cim_base"], dados["cim_controle"] = m.group(1).strip(), m.group(2).strip()
    else:
        m = re.search(r"CIM:\s*([\d.]+)", txt)
        if m:
            dados["cim_base"] = m.group(1).strip()
    # ── bairro/rua/quadra/lote ──
    linhas = [ln.rstrip() for ln in txt.splitlines()]
    ident = None
    # (a) layout pdfplumber: "Bairro: Rua: Quadra: Lote:" + valores na próxima linha
    for i, ln in enumerate(linhas):
        if re.search(r"Bairro:", ln) and re.search(r"Lote:", ln):
            for vln in linhas[i + 1:]:
                if vln.strip():
                    ident = _split_ident(vln.strip())
                    break
            break
    # (b) layout fitz: rótulos empilhados → 4 valores empilhados após "Lote:"
    if not ident:
        try:
            i_lote = next(i for i, ln in enumerate(linhas)
                          if re.match(r"^\s*Lote:?\s*$", ln, re.IGNORECASE))
            vals = []
            for ln in linhas[i_lote + 1:]:
                s = ln.strip()
                if not s:
                    continue
                if ":" in s:
                    break
                vals.append(s)
                if len(vals) >= 4:
                    break
            if len(vals) >= 4:
                ident = (vals[0], vals[1], vals[2], vals[3])
        except StopIteration:
            pass
    if ident:
        dados["bairro"], dados["rua"], dados["quadra"], dados["lote"] = ident
    # ── vértices (prosa) + sistema geodésico (texto normalizado) ──
    t = re.sub(r"\s+", " ", txt)
    m = re.search(r"Meridiano Central n[ºo]\s*([\d°'´’]+)", t)
    if m:
        dados["meridiano_central"] = m.group(1).strip()
    m = re.search(r"fuso\s*(-?\d+)", t, re.IGNORECASE)
    if m:
        dados["fuso"] = m.group(1)
    pos = []
    for mm in _RX_VERT.finditer(t):
        pos.append({"de": mm.group(1), "coord_n": _num(mm.group(2)),
                    "coord_e": _num(mm.group(3)), "feicao": (mm.group(4) or "").strip() or None})
    segs = []
    for mm in _RX_SEG.finditer(t):
        segs.append({"conf": mm.group(1).strip(),
                     "az": re.sub(r"\s+", "", mm.group(2)).strip(),
                     "dist": _num(mm.group(3))})
    verts = []
    for i, p in enumerate(pos):
        v = {"ordem": i + 1, **p}
        if i < len(segs):
            v["confrontante_lado"] = segs[i]["conf"]
            v["azimute"] = segs[i]["az"]
            v["distancia_m"] = segs[i]["dist"]
        verts.append(v)
    dados["vertices"] = verts
    return dados


def parse_memorial_situacao(pdf_bytes: bytes) -> dict:
    """MD-SIT — formato do lote, vias que formam a quadra, esquina."""
    txt = _texto(pdf_bytes)
    if not txt:
        return {}
    t = re.sub(r"\s+", " ", txt)
    dados: dict = {}
    m = re.search(r"Formato do lote\s+([\wçãáéí]+)", t, re.IGNORECASE)
    if m:
        formato = m.group(1).strip().lower()
        dados["formato"] = "retangular" if formato.startswith("retang") else formato
    m = re.search(r"Situado na quadra formada pelas seguintes confrontantes:\s*(.+?)\.", t, re.IGNORECASE)
    if m:
        bruto = m.group(1)
        partes = re.split(r",\s*|\s+e\s+", bruto)
        dados["vias"] = [{"nome": p.strip()} for p in partes if p.strip()]
    m = re.search(r"Distante da esquina com a\s+(.+?),\s*medindo\s*([\d.,]+)", t, re.IGNORECASE)
    if m:
        dados["esquina"] = {"logradouro": m.group(1).strip(), "distancia_m": _num(m.group(2))}
    return dados


# Rótulos de campo do formulário do CFT (p/ saber onde o nome do contratante termina)
_ART_LABEL = re.compile(
    r"^(Logradouro|Complemento|Cidade|Pa[íi]s|Telefone|Contrato|Valor|A[çc][ãa]o|CPF|CNPJ|"
    r"Tipo|Bairro|UF|CEP|N[ºo°]:|T[íi]tulo|Registro|Data|Finalidade|Coordenadas|\d\.)",
    re.IGNORECASE)


def _art_proprietario(linhas):
    """Nome + CPF/CNPJ do proprietário/contratante do CFT. O nome pode continuar na
    linha seguinte (o pdfplumber quebra 'AJM ... EMPREENDIMENTOS' / 'IMOBILIARIOS LTDA')."""
    for chave in ("Proprietário(a):", "Proprietario(a):", "Contratante:"):
        for i, ln in enumerate(linhas):
            if not ln.startswith(chave):
                continue
            resto = ln.split(":", 1)[1].strip() if ":" in ln else ln
            m = re.search(r"(.+?)\s+CPF/CNPJ:\s*([\d./-]+)", resto)
            if m:
                nome, doc = m.group(1).strip(), m.group(2).strip()
            else:
                nome = resto.strip()
                m2 = re.search(r"CPF/CNPJ:\s*([\d./-]+)", " ".join(linhas[i:i + 3]))
                doc = m2.group(1) if m2 else None
            if i + 1 < len(linhas) and not _ART_LABEL.match(linhas[i + 1]) and len(linhas[i + 1]) < 60:
                nome = f"{nome} {linhas[i + 1].strip()}".strip()
            return nome, doc
    return None, None


def _secao_art(linhas, ini, fim):
    """Linhas entre a que começa com `ini` e a próxima que começa com `fim`."""
    a = next((i for i, ln in enumerate(linhas) if ln.startswith(ini)), None)
    if a is None:
        return linhas
    b = next((i for i in range(a + 1, len(linhas)) if linhas[i].startswith(fim)), len(linhas))
    return linhas[a:b]


def _art_endereco(linhas) -> Optional[str]:
    """Compõe o endereço do contratante da seção 2 do CFT."""
    t = " ".join(linhas)
    partes = []
    m = re.search(r"Logradouro:\s*(.+?)\s+N[ºo°]:\s*(\S+)", t)
    if m:
        partes.append(f"{m.group(1).strip()}, nº {m.group(2).strip()}")
    m = re.search(r"Bairro:\s*(.+?)(?:\s+Cidade:|\s*$)", t)
    if m and m.group(1).strip():
        partes.append(m.group(1).strip())
    m = re.search(r"Cidade:\s*(.+?)\s+UF:\s*(\w{2})\s+CEP:\s*(\d+)", t)
    if m:
        partes.append(f"{m.group(1).strip()} - {m.group(2)}, CEP {m.group(3)}")
    return ", ".join(partes) if partes else None


def parse_art_trt(pdf_bytes: bytes) -> dict:
    """ART/TRT (CFT) — proprietário/contratante (nome+CPF/CNPJ+endereço+telefone+e-mail)
    + nº da TRT + matrícula, para a qualificação completa do requerente."""
    txt = _texto(pdf_bytes)
    if not txt:
        return {}
    dados: dict = {}
    m = re.search(r"N[ºo°]\s*(CFT\d+)", txt)
    if m:
        dados["trt_numero"] = m.group(1).strip()
    m = re.search(r"MATR[ÍI]CULA\s*N[.ºo°]*\s*([\d.]+)", txt, re.IGNORECASE)
    if m:
        dados["matricula"] = m.group(1).strip()
    linhas = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    nome, doc = _art_proprietario(linhas)
    if nome:
        dados["proprietario_nome"] = nome
    if doc:
        dados["proprietario_doc"] = doc
    # endereço + contato: da SEÇÃO 2 (Contratante), não da seção 3 (Obra)
    sec2 = _secao_art(linhas, "2. Contratante", "3.")
    end = _art_endereco(sec2)
    if end:
        dados["proprietario_endereco"] = end
    m = re.search(r"Telefone:\s*(\(\d{2}\)[\d\s-]+\d)", " ".join(sec2))
    if m:
        dados["proprietario_telefone"] = m.group(1).strip()
    m = re.search(r"Email:\s*([^\s]+@[^\s]+)", " ".join(sec2))
    if m:
        dados["proprietario_email"] = m.group(1).strip()
    return dados


def extrair_georref(memorial_coord: Optional[bytes], memorial_sit: Optional[bytes],
                    art: Optional[bytes] = None) -> dict:
    """Orquestra a extração: memorial de coordenadas + situação + ART/TRT."""
    out: dict = {}
    if memorial_coord:
        out.update(parse_memorial_coordenadas(memorial_coord))
    if memorial_sit:
        sit = parse_memorial_situacao(memorial_sit)
        if sit:
            out["quadra_dados"] = sit
    if art:
        out["art"] = parse_art_trt(art)
    return out
