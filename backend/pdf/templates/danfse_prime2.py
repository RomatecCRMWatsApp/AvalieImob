# @module pdf.templates.danfse_prime2 — Renderer DANFSe tema prime2 (wrapper fino).
# Conteúdo montado uma vez (danfse_base.montar); o engine único desenha com os tokens do tema.
from pdf.templates.danfse_base import montar
from pdf.templates.danfse_render import render as _render

TEMA = "prime2"


def render(doc: dict, config: dict | None = None, brasao: bytes | None = None) -> bytes:
    return _render(montar(doc, config, brasao), TEMA)
