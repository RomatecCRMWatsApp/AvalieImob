# @module services.georef.cadeia_dominial — Extração semi-estruturada da cadeia dominial.
#
# A certidão de inteiro teor da matrícula traz a sequência de atos (abertura, R-1,
# R-2, Av-1, Av-2...). O layout varia muito por cartório/UF, então a extração é
# heurística — a conferência/edição manual no front é obrigatória (cada ato fica
# editável). Alimenta a seção "Cadeia Dominial" do Laudo Técnico e do Dossiê.
import io
import re
from typing import List, Union

import pdfplumber

PdfSource = Union[str, bytes, bytearray, io.IOBase]

ATO_RE = re.compile(
    r"\b(R[.\-]?\s?\d+|AV[.\-]?\s?\d+|Av[.\-]?\s?\d+|MATR[ÍI]CULA|TRANSCRI[ÇC][ÃA]O)\b",
    re.IGNORECASE,
)
DATA_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
TIPO_HINTS = [
    r"compra e venda", r"doa[çc][ãa]o", r"partilha", r"invent[áa]rio", r"permuta",
    r"hipoteca", r"usufruto", r"georreferenciamento", r"retifica[çc][ãa]o",
    r"desmembramento", r"unifica[çc][ãa]o", r"penhora", r"arresto", r"cancelamento",
]


def _open(src: PdfSource):
    if isinstance(src, (bytes, bytearray)):
        return pdfplumber.open(io.BytesIO(bytes(src)))
    return pdfplumber.open(src)


def parse_cadeia_dominial(src: PdfSource) -> List[dict]:
    """Extrai os atos da matrícula em ordem. Saída -> List[CadeiaDominialAto] (revisar)."""
    text = ""
    with _open(src) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"

    atos: List[dict] = []
    ordem = 0
    blocos = re.split(r"(?=\b(?:R[.\-]?\s?\d+|AV[.\-]?\s?\d+|Av[.\-]?\s?\d+))", text)
    for b in blocos:
        m = ATO_RE.search(b)
        if not m:
            continue
        ordem += 1
        data = DATA_RE.search(b)
        tipo = None
        for t in TIPO_HINTS:
            mt = re.search(t, b, re.IGNORECASE)
            if mt:
                tipo = mt.group(0)
                break
        atos.append({
            "ordem": ordem,
            "ato": re.sub(r"\s+", "-", m.group(0).upper().replace(".", "")),
            "tipo": tipo,
            "data": data.group(1) if data else None,
            "partes": None,        # preencher/ajustar manualmente na conferência
            "titulo": None,
            "observacao": re.sub(r"\s+", " ", b)[:240].strip(),
        })
    return atos
