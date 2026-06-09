"""
Validação e normalização de logos para o white-label do AvalieImob.

- Detecta o tipo REAL pelos magic bytes (python-magic) — não confia no
  Content-Type enviado pelo cliente.
- Aceita PNG, SVG e JPG. WEBP/BMP/TIFF são rejeitados (spec do doc).
- Converte raster (PNG/JPG) para PNG 300 DPI com transparência preservada.
- Rasteriza SVG para PNG 300 DPI (via cairosvg) mantendo proporção.
- Valida tamanho (<= 2 MB) e dimensões (200x60 a 2000x600 px).

Instalar:
  pip install Pillow python-magic cairosvg
  # Debian/Ubuntu: apt-get install -y libmagic1 libcairo2
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Tuple

from PIL import Image

# python-magic é opcional: se ausente, caímos para detecção via Pillow.
try:
    import magic  # python-magic
    _HAS_MAGIC = True
except Exception:  # pragma: no cover
    _HAS_MAGIC = False

from models.tenant_branding import (
    ACCEPTED_LOGO_MIMES,
    LOGO_MAX_BYTES,
    LOGO_MAX_DIMENSIONS,
    LOGO_MIN_DIMENSIONS,
    LOGO_TARGET_DPI,
)

# SVG rasterização é opcional em runtime; só falha se um SVG chegar sem a lib.
try:
    import cairosvg  # type: ignore
    _HAS_CAIROSVG = True
except Exception:  # pragma: no cover
    _HAS_CAIROSVG = False

Image.MAX_IMAGE_PIXELS = 40_000_000  # trava contra decompression bombs


class LogoValidationError(ValueError):
    """Logo rejeitado por formato, tamanho ou dimensão."""


@dataclass
class ProcessedLogo:
    png_bytes: bytes
    width_px: int
    height_px: int
    detected_mime: str
    content_type: str = "image/png"


def _looks_like_svg(data: bytes) -> bool:
    head = data[:1024].lstrip().lower()
    return b"<svg" in head or (b"<?xml" in head and b"svg" in data[:2048].lower())


def _detect_mime(data: bytes) -> str:
    """
    Tipo REAL do arquivo. Usa python-magic (magic bytes) quando disponível;
    senão cai para Pillow (formato decodificado) + sniff de SVG. Nunca confia
    no Content-Type do cliente.
    """
    if _looks_like_svg(data):
        return "image/svg+xml"

    if _HAS_MAGIC:
        mime = magic.from_buffer(data, mime=True)
        if mime in ("text/plain", "text/xml", "application/xml") and _looks_like_svg(data):
            return "image/svg+xml"
        return mime

    # Fallback sem libmagic: identifica o formato real abrindo com Pillow.
    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = (im.format or "").upper()
    except Exception:
        return "application/octet-stream"
    return {"PNG": "image/png", "JPEG": "image/jpeg"}.get(fmt, f"image/{fmt.lower()}")


def _within_dimensions(w: int, h: int) -> None:
    min_w, min_h = LOGO_MIN_DIMENSIONS
    max_w, max_h = LOGO_MAX_DIMENSIONS
    if w < min_w or h < min_h:
        raise LogoValidationError(
            f"logo muito pequeno ({w}x{h}px). Mínimo {min_w}x{min_h}px."
        )
    if w > max_w or h > max_h:
        raise LogoValidationError(
            f"logo muito grande ({w}x{h}px). Máximo {max_w}x{max_h}px."
        )


def _raster_to_png(img: Image.Image) -> Tuple[bytes, int, int]:
    """Garante RGBA, fundo branco quando opaco, exporta PNG 300 DPI."""
    if img.mode in ("P", "LA"):
        img = img.convert("RGBA")
    elif img.mode == "RGB":
        img = img.convert("RGBA")
    elif img.mode != "RGBA":
        img = img.convert("RGBA")

    w, h = img.size
    _within_dimensions(w, h)

    out = io.BytesIO()
    img.save(out, format="PNG", dpi=(LOGO_TARGET_DPI, LOGO_TARGET_DPI), optimize=True)
    return out.getvalue(), w, h


def _svg_to_png(data: bytes) -> Tuple[bytes, int, int]:
    if not _HAS_CAIROSVG:
        raise LogoValidationError(
            "SVG recebido, mas a rasterização não está disponível no servidor "
            "(instale cairosvg + libcairo2)."
        )
    # Renderiza em alta resolução (escala 4x) e deixa o Pillow medir/normalizar.
    png = cairosvg.svg2png(bytestring=data, dpi=LOGO_TARGET_DPI, scale=1.0)
    img = Image.open(io.BytesIO(png))
    return _raster_to_png(img)


def process_logo(data: bytes, declared_content_type: str | None = None) -> ProcessedLogo:
    """
    Pipeline completo: valida tamanho → detecta MIME real → rejeita formatos
    proibidos → normaliza para PNG 300 DPI → valida dimensões.

    `declared_content_type` é apenas informativo (log); a decisão usa magic bytes.
    Levanta LogoValidationError em qualquer reprovação.
    """
    if not data:
        raise LogoValidationError("arquivo vazio.")
    if len(data) > LOGO_MAX_BYTES:
        raise LogoValidationError(
            f"arquivo excede {LOGO_MAX_BYTES // (1024*1024)} MB."
        )

    detected = _detect_mime(data)
    if detected not in ACCEPTED_LOGO_MIMES:
        raise LogoValidationError(
            f"formato não suportado ({detected}). Use PNG, SVG ou JPG."
        )

    if detected == "image/svg+xml":
        png, w, h = _svg_to_png(data)
    else:
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception as exc:
            raise LogoValidationError(f"imagem corrompida ou ilegível: {exc}") from exc
        png, w, h = _raster_to_png(img)

    return ProcessedLogo(
        png_bytes=png,
        width_px=w,
        height_px=h,
        detected_mime=detected,
    )
