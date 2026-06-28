# @module services.geo_urbano.generators.capa — Capa "Lupa Geo" (Addendum).
#
# Capa-herói de TODOS os processos do Geo Urbano: uma LUPA (lente + aro dourado
# com degradê metálico + cabo rotacionado + sombra + reflexo) exibindo a imagem
# aérea/satélite do imóvel (upload `imagem_imovel`) com o perímetro destacado.
# Composta em Pillow (1240×1754 @150dpi A4) e embutida como página no PDF.
from __future__ import annotations

import io
import math
import os
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageFont

from services.geo_urbano.generators import textos as TX

# Paleta brand Romatec
VERDE = (12, 51, 32)          # #0C3320
VERDE2 = (11, 110, 79)        # #0B6E4F
DOURADO = (201, 168, 76)      # #C9A84C
DOURADO_CLARO = (227, 197, 107)   # #E3C56B
DOURADO_ESCURO = (138, 123, 40)   # #8A7B28
OFFWHITE = (245, 241, 230)    # #F5F1E6

A4_PX = (1240, 1754)          # 150 dpi
_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "pdf", "fonts")

SERVICO_TITULO = {
    "remembramento": "REMEMBRAMENTO", "desdobro": "DESDOBRO",
    "retificacao": "RETIFICAÇÃO", "reurb": "REURB", "usucapiao": "USUCAPIÃO",
}


def _font(size, bold=False, serif=True):
    nomes = ([f"PlayfairDisplay-{'Bold' if bold else 'Regular'}.ttf"] if serif
             else [f"DejaVuSans{'-Bold' if bold else ''}.ttf"])
    for nome in nomes:
        p = os.path.join(_FONTS_DIR, nome)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:  # noqa: BLE001
                pass
    # fallbacks do sistema / PIL
    for cand in ("arialbd.ttf" if bold else "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except Exception:  # noqa: BLE001
            continue
    try:
        return ImageFont.load_default(size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ──────────────────────────────────────────────────────────────────────────────
# A LUPA (asset PNG RGBA)
# ──────────────────────────────────────────────────────────────────────────────
def gerar_lupa(img: Image.Image, R=300, ring=34, zoom=1.18, center=(0.5, 0.5)) -> Image.Image:
    R_out = R + ring
    pad = int(R_out * 0.9)            # espaço p/ cabo + sombra
    W = H = 2 * R_out + 2 * pad
    cx = cy = W // 2

    # 1) conteúdo da lente: crop quadrado centralizado + zoom + autocontraste
    src = ImageOps.autocontrast(img.convert("RGB"), cutoff=1)
    iw, ih = src.size
    crop = max(8, min(iw, ih) / max(1.0, zoom))
    ccx, ccy = iw * center[0], ih * center[1]
    left = max(0, min(iw - crop, ccx - crop / 2))
    top = max(0, min(ih - crop, ccy - crop / 2))
    src = src.crop((int(left), int(top), int(left + crop), int(top + crop)))
    lens = src.resize((2 * R, 2 * R), Image.LANCZOS).convert("RGBA")

    # tinte de vidro (verde sutil)
    lens = Image.alpha_composite(lens, Image.new("RGBA", (2 * R, 2 * R), (12, 51, 32, 38)))
    # vinheta anelar
    vig = Image.new("L", (2 * R, 2 * R), 0)
    dv = ImageDraw.Draw(vig)
    for i in range(0, R, 2):
        dv.ellipse([i, i, 2 * R - i, 2 * R - i], outline=int(120 * (i / R) ** 2.2))
    vig = vig.filter(ImageFilter.GaussianBlur(10))
    shade = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    shade.putalpha(vig)
    lens = Image.alpha_composite(lens, shade)
    # reflexo (quadrante superior-esquerdo)
    refl = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    ImageDraw.Draw(refl).pieslice(
        [int(0.10 * 2 * R), int(0.08 * 2 * R), int(0.66 * 2 * R), int(0.58 * 2 * R)],
        200, 360, fill=(255, 255, 255, 70))
    lens = Image.alpha_composite(lens, refl.filter(ImageFilter.GaussianBlur(22)))
    # recorte circular
    mask = Image.new("L", (2 * R, 2 * R), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255)
    lens.putalpha(mask)

    # 2) aro metálico (degradê concêntrico)
    ring_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ring_layer)
    for i in range(ring + 1):
        rad = R_out - i
        col = _lerp(DOURADO_ESCURO, DOURADO_CLARO, i / max(1, ring))
        dr.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=col + (255,))
    hole = Image.new("L", (W, H), 0)
    ImageDraw.Draw(hole).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    ring_layer.paste((0, 0, 0, 0), (0, 0), hole)
    dr.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(70, 58, 18, 255), width=4)
    dr.ellipse([cx - R_out, cy - R_out, cx + R_out, cy + R_out], outline=(247, 232, 168, 255), width=3)

    # 3) cabo (rounded-rect rotacionado ~38°)
    hlen, hw = int(R_out * 1.1), int(ring * 1.4)
    hImg = Image.new("RGBA", (hlen, hw), (0, 0, 0, 0))
    dh = ImageDraw.Draw(hImg)
    dh.rounded_rectangle([0, 0, hlen - 1, hw - 1], radius=hw // 2, fill=DOURADO + (255,))
    dh.rounded_rectangle([0, 0, hlen - 1, hw // 2], radius=hw // 4, fill=DOURADO_CLARO + (210,))
    dh.rounded_rectangle([0, int(hw * 0.62), hlen - 1, hw - 1], radius=hw // 4, fill=DOURADO_ESCURO + (210,))
    ang = -38
    hRot = hImg.rotate(ang, expand=True, resample=Image.BICUBIC)
    # início do cabo na borda inferior-direita do aro (~45°)
    bx = cx + int(R_out * math.cos(math.radians(45)))
    by = cy + int(R_out * math.sin(math.radians(45)))
    hpx = bx - int(hRot.width * 0.12)
    hpy = by - int(hRot.height * 0.12)

    # 4) sombra projetada
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [cx - R_out, cy + R_out - 40, cx + int(R_out * 1.5), cy + R_out + 70], fill=(0, 0, 0, 130))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))

    # composição: sombra → cabo → lente → aro
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(shadow)
    out.alpha_composite(hRot, (hpx, hpy))
    out.alpha_composite(lens, (cx - R, cy - R))
    out.alpha_composite(ring_layer)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# A CAPA (imagem RGB 1240×1754 → embutida no PDF)
# ──────────────────────────────────────────────────────────────────────────────
def _texto_centrado(draw, cx, y, txt, font, fill):
    bb = draw.textbbox((0, 0), txt, font=font)
    draw.text((cx - (bb[2] - bb[0]) / 2, y), txt, font=font, fill=fill)
    return (bb[3] - bb[1])


def _legenda_lupa(projeto: dict) -> str:
    tipo = projeto.get("tipo_servico")
    area = TX.m2(projeto.get("area_declarada_m2"))
    perim = TX.metros(projeto.get("perimetro_m"))
    if tipo == "desdobro":
        n = projeto.get("qtd_lotes_resultantes") or len(projeto.get("lotes_resultantes") or []) or "N"
        return f"LOTE-MÃE {area} → {n} LOTES"
    if tipo == "retificacao":
        return "RETIFICAÇÃO DE ÁREA/REGISTRO"
    # remembramento: a legenda mostra ÁREA e PERÍMETRO (antes dizia "PERÍMETRO" na área)
    return f"ÁREA {area} · PERÍMETRO {perim}"


def compor_capa(projeto: dict, img_bytes: bytes, zoom=1.18, center=(0.5, 0.5)) -> Image.Image:
    W, H = A4_PX
    cv = Image.new("RGB", (W, H), VERDE)
    d = ImageDraw.Draw(cv, "RGBA")

    # grid blueprint sutil
    for x in range(0, W, 62):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 10))
    for y in range(0, H, 62):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 10))

    M = 90
    # faixa de marca
    d.text((M, 70), "ROMATEC CONSULTORIA TOTAL — ENGENHARIA E AGRIMENSURA",
           font=_font(20, serif=False), fill=OFFWHITE)
    marca = "AvalieImob · Geo Urbano"
    fb = _font(20, bold=True, serif=False)
    bb = d.textbbox((0, 0), marca, font=fb)
    d.text((W - M - (bb[2] - bb[0]), 70), marca, font=fb, fill=DOURADO_CLARO)
    d.line([(M, 112), (W - M, 112)], fill=DOURADO, width=3)

    # título
    cx = W // 2
    _texto_centrado(d, cx, 170, "DOSSIÊ", _font(96, bold=True), OFFWHITE)
    _texto_centrado(d, cx, 290, SERVICO_TITULO.get(projeto.get("tipo_servico"), "PROCESSO"),
                    _font(58, bold=True), DOURADO_CLARO)
    sub = " · ".join([x for x in [
        f"Quadra {projeto.get('quadra')}" if projeto.get("quadra") else None,
        projeto.get("loteamento"),
        f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}",
    ] if x])
    _texto_centrado(d, cx, 372, sub[:90], _font(24, serif=False), OFFWHITE)

    # LUPA herói — recorta o padding transparente e fixa a altura no espaço útil
    lupa_bottom = 1010
    try:
        lupa = gerar_lupa(Image.open(io.BytesIO(img_bytes)), R=300, ring=36, zoom=zoom, center=center)
        bb = lupa.getbbox()
        if bb:
            lupa = lupa.crop(bb)
        target_h = 600
        scale = target_h / lupa.height
        lupa = lupa.resize((int(lupa.width * scale), target_h), Image.LANCZOS)
        ly = 420
        cv.paste(lupa, (cx - lupa.width // 2, ly), lupa)
        lupa_bottom = ly + lupa.height
    except Exception:  # noqa: BLE001
        pass

    # legenda da lupa (na faixa livre abaixo da lupa)
    _texto_centrado(d, cx, lupa_bottom + 14, _legenda_lupa(projeto), _font(30, bold=True), DOURADO_CLARO)

    # card de identificação
    cardx0, cardx1, cardy0 = M, W - M, max(1150, lupa_bottom + 70)
    cardy1 = cardy0 + 360
    d.rounded_rectangle([cardx0, cardy0, cardx1, cardy1], radius=22,
                        fill=(8, 38, 24, 210), outline=DOURADO + (255,), width=2)
    d.text((cardx0 + 30, cardy0 + 22), "IDENTIFICAÇÃO DO PROCESSO",
           font=_font(22, bold=True, serif=False), fill=DOURADO_CLARO)
    rt = projeto.get("responsavel_tecnico") or {}
    req = ""
    for p in projeto.get("partes") or []:
        if p.get("papel") == "requerente":
            req = p.get("razao_social") or p.get("nome") or ""
            break
    pares = [
        ("Denominação", projeto.get("denominacao_imovel") or ""),
        ("Serviço · Área", f"{SERVICO_TITULO.get(projeto.get('tipo_servico'), '').title()} · {TX.m2(projeto.get('area_declarada_m2'))}"),
        ("CMI resultante", f"{TX.cim_completo(projeto) or '—'}   (antigo: {projeto.get('cadastro_antigo') or '—'})"),
        ("Requerente", req or "—"),
        ("Resp. Técnico", f"{rt.get('nome') or ''} — {rt.get('conselho') or ''}"),
    ]
    yy = cardy0 + 72
    fk = _font(20, bold=True, serif=False)
    fv = _font(20, serif=False)
    for k, v in pares:
        d.text((cardx0 + 30, yy), f"{k}:", font=fk, fill=DOURADO_CLARO)
        d.text((cardx0 + 280, yy), str(v)[:62], font=fv, fill=OFFWHITE)
        yy += 56

    # rodapé
    d.line([(M, 1600), (W - M, 1600)], fill=DOURADO, width=3)
    cart = (projeto.get("cartorio") or {}).get("nome") or ""
    sup = (projeto.get("superintendencia") or {}).get("nome") or ""
    d.text((M, 1620), f"Destinatários: {cart}", font=_font(17, serif=False), fill=OFFWHITE)
    d.text((M, 1650), f"                  {sup}", font=_font(17, serif=False), fill=OFFWHITE)
    dt = datetime.now(timezone.utc)
    rod = f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''} — {dt.day:02d}/{dt.month:02d}/{dt.year}   ·   AvalieImob · romatecavalieimob.com.br"
    bb = d.textbbox((0, 0), rod, font=_font(17, serif=False))
    d.text((W - M - (bb[2] - bb[0]), 1690), rod, font=_font(17, serif=False), fill=DOURADO_CLARO)
    return cv


def gerar_capa_pdf(projeto: dict, img_bytes: bytes, zoom=1.18, center=(0.5, 0.5)) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as rl_canvas
    cv = compor_capa(projeto, img_bytes, zoom=zoom, center=center)
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.drawImage(ImageReader(cv), 0, 0, width=A4[0], height=A4[1])
    c.showPage()
    c.save()
    return buf.getvalue()


def preview_png(projeto: dict, img_bytes: bytes, zoom=1.18, center=(0.5, 0.5)) -> bytes:
    cv = compor_capa(projeto, img_bytes, zoom=zoom, center=center)
    buf = io.BytesIO()
    cv.save(buf, "PNG")
    return buf.getvalue()
