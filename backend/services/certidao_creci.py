# @module services.certidao_creci — Lê a Certidão de Regularidade do CRECI enviada pelo usuário.
"""O site do CRECI não oferece API e bloqueia acesso automatizado, então o sistema não
busca a certidão sozinho. O que dá para automatizar é a LEITURA: o usuário sobe o PDF
ou um print da tela e o sistema tira daí a validade, a data de emissão e o código de
autenticidade — sem precisar digitar a data.

PDF com texto → pdfplumber/fitz; imagem ou PDF escaneado → OCR (tesseract `por`,
disponível no container de produção). Tudo best-effort: sem leitura, devolve {}.
"""
import base64
import io
import logging
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger("romatec")

VALIDADE_DIAS = 30


def _sem_acento(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c)).upper()


def _data(s: str) -> Optional[date]:
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


def ler_texto(texto: str) -> dict:
    """Extrai validade/emissão/código do texto da certidão (função PURA)."""
    t = _sem_acento(texto)
    t = re.sub(r"[ \t]+", " ", t)
    out = {}
    m = re.search(r"EMITIDA EM:?\s*(\d{2}/\d{2}/\d{4})", t)
    emitida = _data(m.group(1)) if m else None
    m = re.search(r"VALIDA POR\s*\d+\s*DIAS\s*[-–>=\s]*ATE\s*(\d{2}/\d{2}/\d{4})", t) \
        or re.search(r"\bATE\s*(\d{2}/\d{2}/\d{4})", t)
    validade = _data(m.group(1)) if m else None
    if not validade and emitida:
        validade = emitida + timedelta(days=VALIDADE_DIAS)
    # Sanidade: validade entre a emissão e no máximo ~1 ano depois (OCR pode ler lixo).
    if validade and emitida and not (emitida <= validade <= emitida + timedelta(days=370)):
        validade = emitida + timedelta(days=VALIDADE_DIAS)
    m = re.search(r"AUTENTICIDADE:?\s*([A-Z0-9]{5,12})\b", t)
    if m:
        out["codigo"] = m.group(1)
    m = re.search(r"SOB O N[OºO°]?\.?\s*(\d{3,6})", t)
    if m:
        out["creci"] = m.group(1)
    if emitida:
        out["emitida_em"] = emitida.isoformat()
    if validade:
        out["validade"] = validade.isoformat()
    return out


def _bytes(b64: str) -> bytes:
    if "," in b64[:100] and b64.startswith("data:"):
        b64 = b64.split(",", 1)[1]
    return base64.b64decode(b64)


def extrair_texto(b64: str) -> str:
    """Texto do arquivo enviado (PDF ou imagem). '' se não der para ler."""
    try:
        raw = _bytes(b64)
    except Exception:  # noqa: BLE001
        return ""
    if raw[:5] == b"%PDF-":
        texto = ""
        try:
            import fitz
            d = fitz.open("pdf", raw)
            texto = "\n".join(d[i].get_text() for i in range(min(2, d.page_count)))
        except Exception:  # noqa: BLE001
            texto = ""
        if len(texto.strip()) > 40:
            return texto
        try:
            from services.geo_urbano.extractor import ocr_pdf
            return ocr_pdf(raw, max_paginas=2)
        except Exception:  # noqa: BLE001
            return texto
    try:
        import pytesseract
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img).convert("L")
        if img.width < 1400:  # prints de celular: ampliar ajuda o OCR
            f = 1400 / img.width
            img = img.resize((int(img.width * f), int(img.height * f)))
        return pytesseract.image_to_string(img, lang="por")
    except Exception as e:  # noqa: BLE001 — sem tesseract (ex.: ambiente local)
        logger.info("certidao_creci: OCR indisponível (%s)", type(e).__name__)
        return ""


def ler_certidao(b64: str) -> dict:
    try:
        return ler_texto(extrair_texto(b64))
    except Exception as e:  # noqa: BLE001
        logger.warning("certidao_creci: falha na leitura: %s", e)
        return {}
