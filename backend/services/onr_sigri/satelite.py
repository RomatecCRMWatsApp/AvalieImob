# @module services.onr_sigri.satelite — Miniatura de satélite (PNG) com a poligonal.
#
# Compõe tiles do ESRI World Imagery e desenha o polígono SIG-RI por cima, para
# aparecer no card da lista do módulo ONR. Best-effort (b"" em qualquer falha,
# timeout curto) — nunca trava o fluxo. Reutiliza geodesia.resolver_anel.
from __future__ import annotations

import io
import math
import logging

from services.geo_urbano import geodesia as GEO

logger = logging.getLogger("onr_satelite")

_TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
_UA = "RomatecAvalieImob/1.0 (onr-sigri)"
_TS = 256
_GOLD = (201, 162, 39)


def _deg2num(lat: float, lon: float, z: int):
    lat_r = math.radians(lat)
    n = 2.0 ** z
    return (lon + 180.0) / 360.0 * n, (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n


def _fit_zoom(lats, lons, larg, alt, zmax=19, zmin=12):
    for z in range(zmax, zmin - 1, -1):
        xs = [_deg2num(la, lo, z)[0] for la, lo in zip(lats, lons)]
        ys = [_deg2num(la, lo, z)[1] for la, lo in zip(lats, lons)]
        if (max(xs) - min(xs)) * _TS < larg * 0.82 and (max(ys) - min(ys)) * _TS < alt * 0.82:
            return z
    return zmin


def render_satelite_png(vertices, larg: int = 400, alt: int = 250) -> bytes:
    """JPEG do satélite com a poligonal dourada (miniatura leve). b"" se falhar."""
    try:
        ring, _f, _h = GEO.resolver_anel(vertices or [])
        if len(ring) < 4:
            return b""
        lons = [p[0] for p in ring]
        lats = [p[1] for p in ring]
        latc, lonc = sum(lats) / len(lats), sum(lons) / len(lons)
        zoom = _fit_zoom(lats, lons, larg, alt)

        import httpx
        import time as _time
        from PIL import Image, ImageDraw

        xt, yt = _deg2num(latc, lonc, zoom)
        ncols, nrows = larg // _TS + 3, alt // _TS + 3
        x0, y0 = int(round(xt - ncols / 2.0)), int(round(yt - nrows / 2.0))
        canvas = Image.new("RGB", (ncols * _TS, nrows * _TS), (60, 60, 60))
        maxt = 2 ** zoom
        deadline = _time.monotonic() + 9.0
        ok = 0
        with httpx.Client(timeout=4.0, headers={"User-Agent": _UA}) as cli:
            for i in range(ncols):
                for j in range(nrows):
                    if _time.monotonic() > deadline:
                        raise TimeoutError("orçamento de satélite excedido")
                    xtile, ytile = x0 + i, y0 + j
                    if not (0 <= xtile < maxt and 0 <= ytile < maxt):
                        continue
                    try:
                        r = cli.get(_TILE.format(z=zoom, x=xtile, y=ytile))
                        if r.status_code == 200:
                            canvas.paste(Image.open(io.BytesIO(r.content)).convert("RGB"), (i * _TS, j * _TS))
                            ok += 1
                    except (httpx.ConnectError, httpx.ConnectTimeout):
                        raise
                    except Exception:  # noqa: BLE001
                        continue
        if ok == 0:
            return b""

        cw, ch = canvas.size
        px, py = (xt - x0) * _TS, (yt - y0) * _TS
        left = min(max(0, int(px - larg / 2)), max(0, cw - larg))
        top = min(max(0, int(py - alt / 2)), max(0, ch - alt))
        crop = canvas.crop((left, top, left + larg, top + alt))

        # desenha a poligonal (lon/lat → pixel do recorte)
        pts = []
        for lon, lat in ring:
            vx, vy = _deg2num(lat, lon, zoom)
            pts.append(((vx - x0) * _TS - left, (vy - y0) * _TS - top))
        d = ImageDraw.Draw(crop, "RGBA")
        if len(pts) >= 3:
            d.polygon(pts, fill=(201, 162, 39, 60), outline=_GOLD)
            for k in range(len(pts) - 1):
                d.line([pts[k], pts[k + 1]], fill=_GOLD, width=3)
            for (vx, vy) in pts[:-1]:
                d.ellipse([vx - 3, vy - 3, vx + 3, vy + 3], fill=(255, 255, 255), outline=(12, 51, 32))

        out = io.BytesIO()
        crop.convert("RGB").save(out, format="JPEG", quality=72, optimize=True)
        return out.getvalue()
    except Exception:  # noqa: BLE001
        logger.warning("Falha ao gerar satélite ONR.", exc_info=True)
        return b""
