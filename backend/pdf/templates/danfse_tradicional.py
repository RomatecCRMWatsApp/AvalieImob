# @module pdf.templates.danfse_tradicional — Renderer DANFSe tema tradicional (wrapper fino).
# Conteúdo montado uma vez (danfse_base.montar); o engine único desenha com os tokens do tema.
from pdf.templates.danfse_base import montar
from pdf.templates.danfse_render import render as _render

TEMA = "tradicional"


def render(doc: dict, config: dict | None = None, brasao: bytes | None = None) -> bytes:
    return _render(montar(doc, config, brasao), TEMA)
