# @module services.testemunha_signing — núcleo da assinatura de TESTEMUNHA (append-only).
#
# A testemunha assina um documento JÁ assinado pelas partes (PAdES/ICP). Tudo é feito
# por ATUALIZAÇÃO INCREMENTAL (append-only) para NÃO quebrar as assinaturas existentes:
#   - carimbo visual via PyMuPDF incremental (doc.save(incremental=True, PDF_ENCRYPT_KEEP));
#   - assinatura PAdES adicional via pyhanko IncrementalPdfFileWriter (campo próprio).
# Cada nova assinatura cobre a revisão anterior; as anteriores permanecem VÁLIDAS.
from __future__ import annotations

import io
import os
import tempfile

import fitz  # PyMuPDF


def carimbar_incremental(pdf_bytes: bytes, page_idx: int, rect, png_bytes: bytes,
                         legenda: str = "") -> bytes:
    """Carimba a imagem (PNG) no rect (pontos, origem inf-esq) da página `page_idx` via
    INCREMENTAL UPDATE (append-only) — preserva os byte-ranges das assinaturas existentes.
    `rect` = (x0, y0, x1, y1). Levanta em página inválida."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(pdf_bytes)
        tmp.close()
        doc = fitz.open(tmp.name)
        try:
            if page_idx < 0 or page_idx >= doc.page_count:
                raise ValueError(f"Página inválida p/ carimbo: {page_idx} (0..{doc.page_count - 1})")
            page = doc[page_idx]
            r = fitz.Rect(*rect)
            if png_bytes:
                page.insert_image(r, stream=png_bytes, overlay=True, keep_proportion=True)
            if legenda:
                page.insert_textbox(fitz.Rect(r.x0, r.y1 + 1, r.x1 + 200, r.y1 + 28),
                                    legenda, fontsize=6, color=(0.30, 0.30, 0.30))
            # incremental: só ACRESCENTA bytes ao fim; mantém a cifra/estrutura originais
            doc.save(tmp.name, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        finally:
            doc.close()
        with open(tmp.name, "rb") as fh:
            return fh.read()
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:  # noqa: BLE001
            pass


def anexar_pagina_incremental(pdf_bytes: bytes, pagina_pdf_bytes: bytes) -> bytes:
    """Anexa a(s) página(s) de `pagina_pdf_bytes` ao FIM do PDF via INCREMENTAL UPDATE
    (append-only) — preserva os byte-ranges das assinaturas existentes."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(pdf_bytes)
        tmp.close()
        doc = fitz.open(tmp.name)
        nd = fitz.open(stream=pagina_pdf_bytes, filetype="pdf")
        try:
            doc.insert_pdf(nd)
            doc.save(tmp.name, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        finally:
            doc.close()
            nd.close()
        with open(tmp.name, "rb") as fh:
            return fh.read()
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:  # noqa: BLE001
            pass


def aplicar_sumario_incremental(pdf_bytes: bytes, toc: list) -> bytes:
    """Define o SUMÁRIO/índice (marcadores) do PDF via INCREMENTAL UPDATE (append-only) —
    preserva as assinaturas. `toc` = [[nivel, titulo, pagina_1idx], ...]. Em falha,
    devolve o PDF original (best-effort)."""
    if not toc:
        return pdf_bytes
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(pdf_bytes)
        tmp.close()
        doc = fitz.open(tmp.name)
        try:
            doc.set_toc(toc)
            doc.save(tmp.name, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        finally:
            doc.close()
        with open(tmp.name, "rb") as fh:
            return fh.read()
    except Exception:  # noqa: BLE001
        return pdf_bytes
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:  # noqa: BLE001
            pass


def assinar_pades_incremental(pdf_bytes: bytes, pfx_bytes: bytes, password: str,
                              field_name: str, reason: str = "Assinatura de testemunha — Romatec AvalieImob") -> bytes:
    """Anexa uma assinatura PAdES ADICIONAL (incremental) num campo `field_name` único.
    Preserva as assinaturas anteriores (PAdES multi-assinatura: cada uma cobre a revisão
    anterior). Reusa o mesmo carregador de .pfx do selo ICP existente (pyhanko)."""
    from services.pades_service import _carregar_signer
    from pyhanko.sign import signers
    from pyhanko.sign.fields import SigFieldSpec, append_signature_field
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

    signer = _carregar_signer(pfx_bytes, password)
    if signer is None:
        raise RuntimeError("Falha ao carregar o certificado (.pfx) no pyhanko")
    w = IncrementalPdfFileWriter(io.BytesIO(pdf_bytes))
    append_signature_field(w, SigFieldSpec(sig_field_name=field_name))
    meta = signers.PdfSignatureMetadata(field_name=field_name, reason=reason, location="Brasil")
    out = io.BytesIO()
    signers.sign_pdf(w, meta, signer=signer, output=out)
    return out.getvalue()


def status_assinaturas(pdf_bytes: bytes):
    """[(field_name, intact, valid)] de cada assinatura embutida — p/ auditoria/teste."""
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    r = PdfFileReader(io.BytesIO(pdf_bytes))
    out = []
    for sig in r.embedded_signatures:
        try:
            st = validate_pdf_signature(sig)
            out.append((sig.field_name, bool(st.intact), bool(st.valid)))
        except Exception:  # noqa: BLE001
            out.append((sig.field_name, False, False))
    return out
