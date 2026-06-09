# @module services.pdf_preview — Renderiza páginas de um PDF como PNG para o
# visualizador interativo de assinatura posicionada (Feature: Assinatura ICP posicionada).
"""
Converte cada página de um PDF (bytes) em PNG base64 + dimensões reais em pontos,
para o frontend desenhar o retângulo de assinatura e converter coordenadas
pixel→pontos PDF. Usa PyMuPDF (fitz), que já é dependência do projeto.
"""
from __future__ import annotations

import base64


def renderizar_paginas(pdf_bytes: bytes, dpi: int = 120, max_paginas: int = 60) -> list[dict]:
    """
    Retorna [{pagina, imagem_b64, largura_pt, altura_pt, largura_px, altura_px}, ...].
    largura_pt/altura_pt = dimensões reais em pontos (origem bottom-left no PDF).
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    paginas: list[dict] = []
    try:
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            if i >= max_paginas:
                break
            rect = page.rect
            pix = page.get_pixmap(matrix=mat, alpha=False)
            paginas.append({
                "pagina": i,
                "imagem_b64": base64.b64encode(pix.tobytes("png")).decode("ascii"),
                "largura_pt": float(rect.width),
                "altura_pt": float(rect.height),
                "largura_px": int(pix.width),
                "altura_px": int(pix.height),
            })
    finally:
        doc.close()
    return paginas
