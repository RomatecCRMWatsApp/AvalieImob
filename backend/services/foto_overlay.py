# @module services.foto_overlay — Tarja Romatec queimada na foto (padrão PTAM/VTA)
"""
Aplica a tarja Romatec na base da imagem (server-side, Pillow):
  - faixa semi-transparente escura na base (18% da altura)
  - linha superior dourada #c8a84b
  - até 5 linhas: 📍 coordenadas | 🌐 UTM/SIRGAS 2000 | endereço | 🕐 data/hora | 👤 Romatec·colaborador
  - rosa dos ventos (N) no canto superior direito
  - selo "R" (lupa) dentro da faixa, à direita

Defensivo: qualquer falha devolve a imagem original (nunca quebra a geração do PDF).
"""
import io
import math
from typing import Optional

DOURADO = (200, 168, 75)       # #c8a84b
ESCURO = (12, 18, 16)


def _latlon_to_utm(lat: float, lon: float):
    """Conversão WGS84/SIRGAS2000 → UTM (sem dependência externa)."""
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    zona = int((lon + 180) / 6) + 1
    lon0 = math.radians((zona - 1) * 6 - 180 + 3)
    latr, lonr = math.radians(lat), math.radians(lon)
    N = a / math.sqrt(1 - e2 * math.sin(latr) ** 2)
    T = math.tan(latr) ** 2
    C = (e2 / (1 - e2)) * math.cos(latr) ** 2
    A = math.cos(latr) * (lonr - lon0)
    M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64) * latr
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32) * math.sin(2 * latr)
             + (15 * e2 ** 2 / 256) * math.sin(4 * latr))
    k0 = 0.9996
    easting = k0 * N * (A + (1 - T + C) * A ** 3 / 6) + 500000.0
    northing = k0 * (M + N * math.tan(latr) * (A ** 2 / 2 + (5 - T + 9 * C) * A ** 4 / 24))
    if lat < 0:
        northing += 10000000.0
    hemis = "S" if lat < 0 else "N"
    return f"UTM {zona}{hemis} {easting:.0f}E {northing:.0f}N · SIRGAS 2000"


def aplicar_tarja_romatec(
    image_bytes: bytes,
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    endereco: str = "",
    data_hora: str = "",
    colaborador: str = "Romatec",
) -> bytes:
    try:
        from PIL import Image, ImageDraw, ImageFont

        im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        W, H = im.size
        faixa_h = max(60, int(H * 0.18))
        draw = ImageDraw.Draw(im, "RGBA")

        # Faixa escura translúcida + linha dourada superior
        draw.rectangle([0, H - faixa_h, W, H], fill=(*ESCURO, 200))
        draw.rectangle([0, H - faixa_h, W, H - faixa_h + max(2, int(H * 0.004))], fill=(*DOURADO, 255))

        def _font(sz):
            try:
                return ImageFont.truetype("DejaVuSans.ttf", sz)
            except Exception:
                return ImageFont.load_default()

        fs = max(11, int(faixa_h / 6.5))
        font = _font(fs)

        linhas = []
        if lat is not None and lon is not None:
            linhas.append(f"LAT {lat:.6f}  LON {lon:.6f}")
            linhas.append(_latlon_to_utm(lat, lon))
        if endereco:
            linhas.append(endereco[:80])
        if data_hora:
            linhas.append(str(data_hora))
        linhas.append(f"Romatec · {colaborador}")

        y = H - faixa_h + int(faixa_h * 0.10)
        for ln in linhas[:5]:
            draw.text((int(W * 0.02), y), ln, fill=(245, 239, 226, 255), font=font)
            y += int(fs * 1.25)

        # Rosa dos ventos (N) — canto superior direito
        cx, cy, r = W - int(W * 0.06), int(W * 0.06), max(14, int(W * 0.035))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*DOURADO, 230), width=2)
        draw.polygon([(cx, cy - r + 2), (cx - r // 3, cy), (cx + r // 3, cy)], fill=(*DOURADO, 230))
        draw.text((cx - fs // 3, cy + 2), "N", fill=(245, 239, 226, 255), font=_font(fs))

        # Selo "R" dentro da faixa, à direita
        sr = int(faixa_h * 0.32)
        scx, scy = W - int(W * 0.06), H - faixa_h // 2
        draw.ellipse([scx - sr, scy - sr, scx + sr, scy + sr], fill=(*DOURADO, 255))
        draw.text((scx - sr // 2, scy - sr), "R", fill=ESCURO, font=_font(int(sr * 1.4)))

        out = io.BytesIO()
        im.save(out, format="JPEG", quality=85)
        return out.getvalue()
    except Exception:
        return image_bytes
