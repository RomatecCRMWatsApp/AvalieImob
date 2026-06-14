"""Gera uma assinatura manuscrita (cursiva) por PADRÃO a partir do nome completo.

Usado quando o corretor/usuário ainda não DESENHOU a própria assinatura: o sistema
pega o nome completo do cadastro e renderiza num traço cursivo (fonte Great Vibes,
licença OFL), fundo TRANSPARENTE — pronto para ser carimbado no PDF (mesma mecânica
do traço desenhado à mão). O usuário pode sempre redesenhar por cima.
"""
from __future__ import annotations

import base64
import io
import logging
import os

logger = logging.getLogger("assinatura_default")

_FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "GreatVibes-Regular.ttf")
_COR_TINTA = (20, 49, 92)  # azul-caneta escuro (#14315c) — igual ao traço do canvas


def gerar_assinatura_nome_png(nome: str, largura: int = 700, altura: int = 220) -> bytes:
    """Renderiza o nome em estilo de assinatura (PNG RGBA, fundo transparente).

    Ajusta o tamanho da fonte para caber na largura. Devolve b"" se não houver nome
    ou se a fonte/PIL falhar (o chamador trata como 'sem assinatura padrão')."""
    nome = " ".join((nome or "").split()).strip()
    if not nome:
        return b""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        logger.warning("PIL indisponível para gerar assinatura padrão.", exc_info=True)
        return b""

    try:
        img = Image.new("RGBA", (largura, altura), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # maior tamanho de fonte que cabe em ~92% da largura e ~70% da altura
        fonte = None
        bbox = None
        for sz in range(150, 28, -3):
            try:
                f = ImageFont.truetype(_FONT_PATH, sz)
            except Exception:
                f = ImageFont.load_default()
            bb = draw.textbbox((0, 0), nome, font=f)
            w, h = bb[2] - bb[0], bb[3] - bb[1]
            if w <= largura * 0.92 and h <= altura * 0.70:
                fonte, bbox = f, bb
                break
        if fonte is None:  # nome enorme: usa o menor tamanho mesmo assim
            try:
                fonte = ImageFont.truetype(_FONT_PATH, 28)
            except Exception:
                fonte = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), nome, font=fonte)

        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (largura - tw) // 2 - bbox[0]
        y = (altura - th) // 2 - bbox[1]
        draw.text((x, y), nome, font=fonte, fill=_COR_TINTA + (255,))

        # rubrica: traço reto por baixo do nome (cara de assinatura)
        ly = y + th + max(6, th // 8)
        x0, x1 = x + bbox[0], x + bbox[0] + tw
        draw.line([(x0, ly), (x1, ly)], fill=_COR_TINTA + (200,), width=3)

        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue()
    except Exception:
        logger.warning("Falha ao gerar assinatura padrão do nome.", exc_info=True)
        return b""


def gerar_assinatura_nome_b64(nome: str) -> str:
    """Devolve o PNG base64 PURO (sem prefixo data:) ou '' se não houver."""
    png = gerar_assinatura_nome_png(nome)
    return base64.b64encode(png).decode("ascii") if png else ""
