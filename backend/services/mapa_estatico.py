"""Mapa estático (PNG) a partir de lat/lon — compõe tiles do OpenStreetMap.

Best-effort: timeout curto + fallback (retorna b"" em qualquer falha) para nunca
travar/inviabilizar a geração do PDF. Reutilizável por contratos, PTAM, etc.
Cache em processo por (lat, lon, zoom, tamanho).
"""
from __future__ import annotations

import io
import math
import logging

logger = logging.getLogger("mapa_estatico")

_CACHE: dict = {}
_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
_UA = "RomatecAvalieImob/1.0 (contrato; romateccrm@gmail.com)"
_TS = 256


def _deg2num(lat: float, lon: float, z: int):
    lat_r = math.radians(lat)
    n = 2.0 ** z
    xt = (lon + 180.0) / 360.0 * n
    yt = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n
    return xt, yt


def gerar_mapa_png(lat, lon, zoom: int = 16, larg: int = 620, alt: int = 300) -> bytes:
    """PNG do mapa centrado em (lat, lon) com marcador. b"" se não der p/ gerar."""
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return b""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return b""
    key = (round(lat, 5), round(lon, 5), zoom, larg, alt)
    if key in _CACHE:
        return _CACHE[key]
    try:
        import httpx
        from PIL import Image, ImageDraw

        xt, yt = _deg2num(lat, lon, zoom)
        ncols = larg // _TS + 3
        nrows = alt // _TS + 3
        x0 = int(round(xt - ncols / 2.0))
        y0 = int(round(yt - nrows / 2.0))
        canvas = Image.new("RGB", (ncols * _TS, nrows * _TS), (236, 236, 236))
        maxt = 2 ** zoom
        import time as _time
        deadline = _time.monotonic() + 8.0  # orçamento TOTAL (não travar o fluxo de assinatura)
        ok_tiles = 0
        with httpx.Client(timeout=4.0, headers={"User-Agent": _UA}) as cli:
            for i in range(ncols):
                for j in range(nrows):
                    if _time.monotonic() > deadline:
                        raise TimeoutError("orçamento de mapa excedido")
                    xtile, ytile = x0 + i, y0 + j
                    if not (0 <= xtile < maxt and 0 <= ytile < maxt):
                        continue
                    try:
                        r = cli.get(_TILE_URL.format(z=zoom, x=xtile, y=ytile))
                        if r.status_code == 200:
                            tile = Image.open(io.BytesIO(r.content)).convert("RGB")
                            canvas.paste(tile, (i * _TS, j * _TS))
                            ok_tiles += 1
                    except (httpx.ConnectError, httpx.ConnectTimeout):
                        raise  # rede indisponível: aborta rápido (não soma timeouts)
                    except Exception:
                        continue
        if ok_tiles == 0:
            return b""

        cw, ch = canvas.size
        px = int((xt - x0) * _TS)
        py = int((yt - y0) * _TS)
        left = min(max(0, px - larg // 2), max(0, cw - larg))
        top = min(max(0, py - alt // 2), max(0, ch - alt))
        crop = canvas.crop((left, top, left + larg, top + alt))

        # marcador (pino) no ponto
        d = ImageDraw.Draw(crop)
        mx, my = px - left, py - top
        d.ellipse([mx - 8, my - 8, mx + 8, my + 8], fill=(192, 57, 43), outline=(255, 255, 255), width=2)
        d.ellipse([mx - 2, my - 2, mx + 2, my + 2], fill=(255, 255, 255))
        # crédito OSM (exigência de atribuição)
        try:
            d.rectangle([larg - 150, alt - 16, larg, alt], fill=(255, 255, 255))
            d.text((larg - 147, alt - 14), "© OpenStreetMap", fill=(90, 90, 90))
        except Exception:
            pass

        out = io.BytesIO()
        crop.save(out, format="PNG", optimize=True)
        data = out.getvalue()
        _CACHE[key] = data
        return data
    except Exception:
        logger.warning("Falha ao gerar mapa estático.", exc_info=True)
        return b""
