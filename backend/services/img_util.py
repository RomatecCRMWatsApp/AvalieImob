# @module services.img_util — reduz resolucao das imagens embutidas nos PDFs
"""
Fotos de campo costumam ter 3-5 MB cada. Embutir 15-20 delas em alta resolucao
gera PDFs de dezenas de MB — o que estoura a memoria na hora de assinar (pyhanko
carrega o PDF inteiro). Este util reamostra a imagem para um lado maximo razoavel,
mantendo qualidade visual de laudo. Nunca lanca: em erro, devolve os bytes originais.
"""
from __future__ import annotations

import logging
from io import BytesIO

logger = logging.getLogger("romatec")


def downscale_image(raw: bytes, max_side: int = 1600, quality: int = 82) -> bytes:
    """Reamostra a imagem para `max_side` px no maior lado e recomprime em JPEG.
    Devolve os bytes originais se algo falhar (ou se ja for menor)."""
    try:
        from PIL import Image, ImageOps
        im = Image.open(BytesIO(raw))
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        w, h = im.size
        if max(w, h) <= max_side and len(raw) < 900_000:
            return raw
        if max(w, h) > max_side:
            im.thumbnail((max_side, max_side))
        out = BytesIO()
        im.save(out, format="JPEG", quality=quality, optimize=True)
        data = out.getvalue()
        return data if data and len(data) < len(raw) else raw
    except Exception as e:
        logger.warning("Falha ao reamostrar imagem: %s", e)
        return raw
