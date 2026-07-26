# @module services.onr_sigri.extractor_onr — Extração do MEMORIAL para o ONR/SIG-RI.
#
# O memorial descritivo (prosa) é a fonte dos dados: vértices (UTM N/E +
# azimute + distância), área/perímetro, denominação, proprietário (nome/CPF),
# confrontantes por segmento, município/UF, matrícula, fuso/datum e RT. O MAPA
# vem como IMAGEM (anexo, não parseável) e a CERTIDÃO é escaneada (OCR opcional).
#
# Reutiliza (read-only) os extratores de texto e o motor geodésico existentes.
from __future__ import annotations

import re
from typing import Optional

from services.geo_urbano import extractor as EX
from services.geo_urbano import geodesia as GEO

_DOC = r"(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|\d{3}\.?\d{3}\.?\d{3}-?\d{2})"


def _confrontante_curto(txt: Optional[str]) -> Optional[str]:
    """Reduz o confrontante verboso do memorial ao nome do imóvel/pessoa."""
    if not txt:
        return None
    s = re.split(r",|\bna cidade\b|\bsituad|\bBairro\b|\bcom os seguintes\b|\bde propriedade\b",
                 txt, maxsplit=1, flags=re.IGNORECASE)[0]
    return re.sub(r"\s+", " ", s).strip(" .,-") or None


def _municipio_uf(t: str):
    """(município, uf) — 'Local: … Açailândia-MA' ou 'na cidade de Açailândia-MA'."""
    m = re.search(r"(?:Local\s*:|cidade\s+de)\s*.*?([A-Za-zÀ-ÿ'’.\- ]{3,40}?)\s*-\s*([A-Z]{2})\b", t)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip(" .,"), m.group(2)
    return None, None


def _area_m2(t: str) -> Optional[float]:
    # "Área (ha): 6,5077 ha / 65.077,00 m²"
    m = re.search(r"[ÁA]rea\s*\(\s*ha\s*\)\s*:?\s*[\d.,]+\s*ha\s*/\s*([\d.,]+)\s*m", t, re.IGNORECASE)
    if m:
        return EX._num(m.group(1))
    m = re.search(r"[ÁA]rea[^\d]{0,20}?([\d.,]+)\s*m[²2]", t, re.IGNORECASE)
    return EX._num(m.group(1)) if m else None


def _fuso_hemis(t: str):
    m = re.search(r"fuso\s*[-–]?\s*(\d{1,2})", t, re.IGNORECASE)
    fuso = int(m.group(1)) if m else None
    # UTM sul: Norte com falso 10.000.000 → N ~9.x milhões indica hemisfério Sul
    hemis = "S" if re.search(r"\bN\s*9\.\d", t) or re.search(r"SIRGAS", t, re.IGNORECASE) else "S"
    return fuso, hemis


def _matricula(t: str) -> dict:
    out = {}
    m = re.search(r"Matr[íi]cula\s*n?[º°.\s]*([\d.]+)", t, re.IGNORECASE)
    if m:
        out["matricula"] = m.group(1).strip(" .")
    for chave, rx in (("livro", r"Livro\s*n?[º°.\s]*([\w\-]+)"),
                      ("folhas", r"Folha[s]?\s*n?[º°.\s]*([\w\-]+)"),
                      ("cri", r"comarca\s+de\s+([A-Za-zÀ-ÿ .]+?)[,\.]")):
        mm = re.search(rx, t, re.IGNORECASE)
        if mm:
            out[chave] = mm.group(1).strip(" .")
    cns = re.search(r"CNS\s*:?\s*([\d.\-]+)", t, re.IGNORECASE)
    if cns:
        out["cns"] = cns.group(1).strip(" .")
    return out


def _proprietario(t: str) -> dict:
    m = re.search(r"Propriet[áa]ri[oa]\s*\(?a?\)?\s*:?\s*(.+?)\s*/\s*CPF\s*n?[º°.\s]*:?\s*" + _DOC, t,
                  re.IGNORECASE)
    if m:
        return {"nome": re.sub(r"\s+", " ", m.group(1)).strip(" .,"), "doc": m.group(2)}
    return {}


def _rt(t: str) -> dict:
    out = {}
    nome = re.search(r"(?:^|\n|\.)\s*(Jos[ée] Rom[áa]rio[^\n]+?)\s*T[ée]cnico", t)
    cft = re.search(r"CFT[/:\s]*([0-9\-]{6,})", t)
    incra = re.search(r"INCRA\s*:?\s*([A-Z0-9]{3,})", t, re.IGNORECASE)
    if cft:
        out["conselho"] = "CFT/MA " + re.sub(r"\D", "", cft.group(1))
    if incra:
        out["credenciamento_incra"] = incra.group(1).upper()
    if nome:
        out["nome"] = re.sub(r"\s+", " ", nome.group(1)).strip(" .,")
    return out


def parse_cnh(pdf_bytes: bytes) -> dict:
    """CNH/RG (documento do proprietário) — normalmente imagem → OCR → nome + CPF.
    Best-effort (só funciona com tesseract disponível; senão devolve {})."""
    t = ""
    for raw in EX._textos_candidatos(pdf_bytes):
        if raw and len(raw) > len(t):
            t = raw
    t = re.sub(r"\s+", " ", t or "")
    doc = re.search(_DOC, t)
    nome = None
    m = re.search(r"NOME\s*[:\-]?\s*([A-ZÀ-Ý][A-ZÀ-Ý '.]{6,})", t)
    if m:
        nome = re.sub(r"\s+", " ", m.group(1)).strip(" .,")
    out = {"nome": nome, "doc": doc.group(0) if doc else None}
    return {k: v for k, v in out.items() if v}


def parse_memorial_onr(pdf_bytes: bytes) -> dict:
    """Extrai TUDO do memorial p/ alimentar o motor SIG-RI. Devolve um dict pronto
    (chaves compatíveis com geo_export/schema_onr) + `_confianca`/`_avisos`."""
    # base: melhor candidato de texto (mesma estratégia do usucapião), reusado
    base, raw_best = {}, ""
    for raw in EX._textos_candidatos(pdf_bytes):
        t = re.sub(r"\s+", " ", raw)
        r = EX._parse_memorial_texto(t)
        if len(r.get("vertices") or []) > len(base.get("vertices") or []):
            base, raw_best = r, t
        elif not base:
            base, raw_best = r, t
    t = raw_best or ""
    avisos = []

    vertices = base.get("vertices") or []
    fuso, hemis = _fuso_hemis(t)
    # converte UTM→geodésica (lat/long decimais) usando o fuso do memorial, p/ o
    # motor gerar o shapefile no fuso certo independentemente do default.
    for v in vertices:
        v["confrontante_lado"] = _confrontante_curto(v.get("confrontante_lado"))
        ce, cn = v.get("coord_e"), v.get("coord_n")
        if ce and cn and fuso:
            try:
                lon, lat = GEO.utm_para_geo(float(ce), float(cn), fuso, hemis or "S")
                v["longitude"], v["latitude"] = lon, lat
            except Exception:  # noqa: BLE001
                pass

    municipio, uf = _municipio_uf(t)
    prop = _proprietario(t)
    mat = _matricula(t)
    area = _area_m2(t)
    if not vertices:
        avisos.append("Não foi possível extrair os vértices do memorial — confira/edite manualmente.")

    out = {
        "denominacao_imovel": base.get("denominacao"),
        "municipio": municipio, "uf": uf,
        "area_declarada_m2": area if area is not None else base.get("area_declarada_m2"),
        "perimetro_m": base.get("perimetro_m"),
        "vertices": vertices,
        "fuso": fuso, "hemisferio": hemis,
        "proprietario": prop,
        "matricula": mat,
        "responsavel_tecnico": _rt(t),
        "_confianca": 0.9 if len(vertices) >= 3 and prop.get("nome") else 0.5,
        "_avisos": avisos,
    }
    return {k: v for k, v in out.items() if v not in (None, "", {}, [])} | {
        "vertices": vertices, "_confianca": out["_confianca"], "_avisos": avisos}
