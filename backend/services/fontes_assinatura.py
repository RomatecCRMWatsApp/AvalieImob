# @module services.fontes_assinatura — fontes manuscritas da assinatura DIGITADA.
#
# A assinatura digitada (nome + fonte cursiva) é RENDERIZADA num PNG transparente
# (mesmo formato do traço desenhado) e reusa TODO o carimbo/posicionamento já
# existente (assinatura_cliente_carimbo.carimbar_multi / carimbar_traco_em_pagina).
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import List

_FONTES_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "assinatura"

# id (fonte_assinatura) → (rótulo, arquivo .ttf)
FONTES_ASSINATURA = {
    "DancingScript": ("Dancing Script", "DancingScript-Regular.ttf"),
    "GreatVibes":    ("Great Vibes", "GreatVibes-Regular.ttf"),
    "Sacramento":    ("Sacramento", "Sacramento-Regular.ttf"),
    "Allura":        ("Allura", "Allura-Regular.ttf"),
    "HomemadeApple": ("Homemade Apple", "HomemadeApple-Regular.ttf"),
    "Pacifico":      ("Pacifico", "Pacifico-Regular.ttf"),
}
_TINTA = (20, 49, 92)   # tinta azul-escura da assinatura (#14315c)


def fontes_disponiveis() -> List[dict]:
    """Lista [{id, label}] das fontes p/ a galeria (front e verificador)."""
    return [{"id": fid, "label": lbl} for fid, (lbl, _) in FONTES_ASSINATURA.items()]


def caminho_fonte(fonte_id: str) -> str:
    if fonte_id not in FONTES_ASSINATURA:
        raise ValueError(f"Fonte de assinatura inválida: {fonte_id}")
    p = _FONTES_DIR / FONTES_ASSINATURA[fonte_id][1]
    if not p.exists():
        raise FileNotFoundError(f"Arquivo de fonte não encontrado: {p}")
    return str(p)


def registrar_fonte_reportlab(fonte_id: str) -> str:
    """Registra a TTF no ReportLab (idempotente) — p/ quem quiser desenhar direto no PDF."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    cam = caminho_fonte(fonte_id)
    if fonte_id not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(fonte_id, cam))
    return fonte_id


def render_assinatura_png(nome: str, fonte_id: str, altura: int = 150,
                          cor=_TINTA) -> bytes:
    """Renderiza o NOME na fonte cursiva escolhida num PNG RGBA transparente (recortado
    ao conteúdo). É usado como o 'traço' da assinatura — o carimbo/posição já existentes
    o aplicam igual à assinatura desenhada."""
    from PIL import Image, ImageDraw, ImageFont
    nome = (nome or "").strip() or " "
    cam = caminho_fonte(fonte_id)
    # tamanho da fonte proporcional à altura pedida (com folga p/ ascendentes/descendentes)
    fonte = ImageFont.truetype(cam, int(altura * 0.72))
    # mede o texto
    tmp = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    bb = ImageDraw.Draw(tmp).textbbox((0, 0), nome, font=fonte)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = int(altura * 0.18)
    W, H = tw + 2 * pad, th + 2 * pad
    img = Image.new("RGBA", (max(W, 40), max(H, 40)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((pad - bb[0], pad - bb[1]), nome, font=fonte, fill=tuple(cor) + (255,))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
