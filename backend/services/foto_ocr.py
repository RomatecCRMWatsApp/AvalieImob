# @module services.foto_ocr — OCR do overlay de GPS/data queimado nas fotos
"""
Muitas fotos de campo nao tem EXIF (perdido ao enviar por WhatsApp etc.), mas o
app de camera "queima" um rodape com coordenadas e data/hora na propria imagem.
Este modulo le esse rodape via Tesseract OCR e extrai GPS + data/hora por regex.

Requer: pytesseract (Python) + tesseract-ocr (binario, instalado no Dockerfile).
Nunca lanca: retorna ("", "") se algo falhar ou se o OCR nao estiver disponivel.
"""
from __future__ import annotations

import logging
import re
from io import BytesIO

logger = logging.getLogger("romatec")

# Coordenadas decimais: -4.949594, -47.463089   (aceita variacoes de espaco/virgula)
_RE_COORD = re.compile(r"(-?\d{1,3}[.,]\d{4,})\s*[,;]\s*(-?\d{1,3}[.,]\d{4,})")
_RE_ALT = re.compile(r"alt\.?\s*(\d{1,5})\s*m", re.IGNORECASE)
# Data/hora: 28/05/2026, 16:51:54  ou  28/05/2026 16:51
_RE_DATA = re.compile(r"(\d{2}/\d{2}/\d{4})[\s,]+(\d{2}:\d{2}(?::\d{2})?)")


def _norm_num(s: str) -> str:
    return s.replace(",", ".").strip()


def extrair_gps_data_ocr(img_bytes: bytes) -> tuple[str, str]:
    """Retorna (gps_str, data_hora_str) lidos do overlay via OCR. Nunca lanca."""
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except Exception as e:
        logger.warning("OCR indisponivel (pytesseract/Tesseract): %s", e)
        return "", ""

    try:
        im = Image.open(BytesIO(img_bytes))
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size

        # O rodape costuma ficar no terco inferior da imagem. Recorta e amplia
        # para melhorar a leitura. Faz OCR no recorte e, se falhar, na imagem toda.
        candidatos = []
        crop_inf = im.crop((0, int(h * 0.62), w, h))
        # upscale x2 para ajudar o OCR em texto pequeno
        crop_inf = crop_inf.resize((crop_inf.width * 2, crop_inf.height * 2))
        candidatos.append(crop_inf)
        candidatos.append(im)

        texto = ""
        for img in candidatos:
            try:
                t = pytesseract.image_to_string(img, lang="por+eng", config="--psm 6")
            except Exception:
                try:
                    t = pytesseract.image_to_string(img)
                except Exception:
                    t = ""
            texto += "\n" + (t or "")
            if _RE_COORD.search(texto):
                break

        gps = ""
        mco = _RE_COORD.search(texto)
        if mco:
            lat = _norm_num(mco.group(1))
            lon = _norm_num(mco.group(2))
            gps = f"{lat}, {lon}"
            malt = _RE_ALT.search(texto)
            if malt:
                gps += f" alt {malt.group(1)}m"

        data_hora = ""
        mdt = _RE_DATA.search(texto)
        if mdt:
            data_hora = f"{mdt.group(1)} {mdt.group(2)}"

        return gps, data_hora
    except Exception as e:
        logger.warning("Falha no OCR do overlay da foto: %s", e)
        return "", ""
