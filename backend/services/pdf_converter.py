# @module services.pdf_converter — Conversão PDF → TIFF 300 DPI (LZW) + render de preview
"""
Serviço de conversão de documentos PDF para imagens rasterizadas.

Para cada página do PDF gera:
  • um TIFF 300 DPI com compressão LZW (lossless) — formato de arquivo/auditoria,
    padrão ABNT/CREA para documentos técnicos impressos;
  • um JPEG de preview (mesma rasterização em 300 DPI, recomprimido) — para
    exibição no navegador e embed no laudo (reportlab), já que TIFF não renderiza
    em <img> nem é embutível diretamente.

Sem dependências de sistema: usa PyMuPDF (fitz) puro para renderizar — não exige
poppler nem pdf2image. PDFs vetoriais (SIGEF/SICAR) saem em qualidade perfeita;
PDFs escaneados são rasterizados na resolução-alvo.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger("romatec")

# Resolução-alvo — 300 DPI é o padrão para documentos técnicos/jurídicos impressos.
_DPI = 300
# PDFs usam 72 DPI como base interna; a matriz escala a renderização para 300 DPI.
_MATRIX = fitz.Matrix(_DPI / 72, _DPI / 72)
# Qualidade do JPEG de preview — alto o suficiente para leitura, leve para o navegador.
_PREVIEW_QUALITY = 85


class PdfConversionError(ValueError):
    """PDF inválido, vazio, corrompido ou protegido por senha."""


@dataclass
class PaginaConvertida:
    """Saída de uma página: caminhos do TIFF e do preview JPEG gerados."""

    numero: int           # 1-based
    tiff_path: Path
    preview_path: Path


@dataclass
class ResultadoConversao:
    paginas: list[PaginaConvertida] = field(default_factory=list)

    @property
    def total_paginas(self) -> int:
        return len(self.paginas)

    @property
    def tiff_paths(self) -> list[Path]:
        return [p.tiff_path for p in self.paginas]

    @property
    def preview_paths(self) -> list[Path]:
        return [p.preview_path for p in self.paginas]


def is_pdf(content_type: str | None, filename: str | None) -> bool:
    """Verifica se o arquivo enviado é um PDF pela content-type ou pela extensão."""
    ct = (content_type or "").lower()
    fn = (filename or "").lower()
    return ct == "application/pdf" or fn.endswith(".pdf")


def _open_doc(pdf_data: bytes) -> "fitz.Document":
    if not pdf_data:
        raise PdfConversionError("Arquivo PDF vazio.")
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
    except Exception as exc:  # fitz.FileDataError e afins
        raise PdfConversionError(f"Arquivo não é um PDF válido: {exc}") from exc
    if doc.needs_pass:
        doc.close()
        raise PdfConversionError("PDF protegido por senha — remova a proteção e reenvie.")
    if doc.page_count == 0:
        doc.close()
        raise PdfConversionError("PDF não contém páginas.")
    return doc


def convert_pdf_to_tiff_pages(
    pdf_data: bytes,
    output_dir: Path,
    base_name: str | None = None,
) -> ResultadoConversao:
    """
    Converte cada página de um PDF em TIFF 300 DPI (LZW) + JPEG de preview.

    Args:
        pdf_data:   Conteúdo binário do PDF.
        output_dir: Diretório de saída (criado se não existir).
        base_name:  Prefixo dos arquivos (sem extensão). UUID hex se None.

    Returns:
        ResultadoConversao com uma PaginaConvertida por página.

    Raises:
        PdfConversionError: PDF inválido/vazio/protegido (mapear para HTTP 422).
        RuntimeError:       Falha de I/O ou render de página (mapear para HTTP 500).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if base_name is None:
        base_name = uuid.uuid4().hex

    doc = _open_doc(pdf_data)
    resultado = ResultadoConversao()
    gerados: list[Path] = []
    page_index = 0
    try:
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            pixmap = page.get_pixmap(matrix=_MATRIX, colorspace=fitz.csRGB, alpha=False)
            img = Image.frombytes(
                mode="RGB",
                size=(pixmap.width, pixmap.height),
                data=pixmap.samples,
            )
            sufixo = f"_p{page_index + 1:03d}"  # _p001, _p002, ...

            tiff_path = output_dir / f"{base_name}{sufixo}.tiff"
            img.save(
                str(tiff_path),
                format="TIFF",
                compression="tiff_lzw",   # LZW: lossless, ~40% menor que raw
                dpi=(_DPI, _DPI),
            )
            gerados.append(tiff_path)

            preview_path = output_dir / f"{base_name}{sufixo}.jpg"
            img.save(
                str(preview_path),
                format="JPEG",
                quality=_PREVIEW_QUALITY,
                optimize=True,
                dpi=(_DPI, _DPI),
            )
            gerados.append(preview_path)

            resultado.paginas.append(
                PaginaConvertida(
                    numero=page_index + 1,
                    tiff_path=tiff_path,
                    preview_path=preview_path,
                )
            )
    except PdfConversionError:
        for p in gerados:
            p.unlink(missing_ok=True)
        raise
    except Exception as exc:
        for p in gerados:
            p.unlink(missing_ok=True)
        raise RuntimeError(f"Falha na conversão da página {page_index + 1}: {exc}") from exc
    finally:
        doc.close()

    logger.info(
        "PDF convertido: base=%s paginas=%d dir=%s",
        base_name, resultado.total_paginas, output_dir,
    )
    return resultado


def render_pdf_first_page_jpeg(pdf_data: bytes, max_side: int = 1600) -> bytes:
    """Render leve da 1ª página em JPEG (thumbnail). Usado para preview rápido.
    Levanta PdfConversionError se o PDF for inválido."""
    doc = _open_doc(pdf_data)
    try:
        page = doc.load_page(0)
        pixmap = page.get_pixmap(matrix=_MATRIX, colorspace=fitz.csRGB, alpha=False)
        img = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side))
        out = BytesIO()
        img.save(out, format="JPEG", quality=_PREVIEW_QUALITY, optimize=True)
        return out.getvalue()
    finally:
        doc.close()
