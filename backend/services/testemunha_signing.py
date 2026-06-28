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


def inserir_no_sumario(pdf_bytes: bytes, entries: list, tag: str = "ANEXO") -> tuple:
    """Sobrepõe linhas no SUMÁRIO do contrato (abaixo da última cláusula) via INCREMENTAL
    (append-only, preserva as assinaturas). `entries` = [(label, pagina_1idx)]. Acha a
    página que contém "SUMÁRIO". Retorna (pdf_bytes, ok) — ok=False se não achou/sem espaço."""
    if not entries:
        return pdf_bytes, False
    GOLD, GOLDBG, GREEN, BLACK = (0.79, 0.66, 0.30), (0.95, 0.91, 0.79), (0.047, 0.2, 0.12), (0, 0, 0)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(pdf_bytes)
        tmp.close()
        doc = fitz.open(tmp.name)
        ok = False
        try:
            sp = None
            for i in range(min(6, doc.page_count)):
                hits = []
                for termo in ("SUMÁRIO", "SUMARIO", "Sumário"):
                    try:
                        hits = doc[i].search_for(termo)
                    except Exception:  # noqa: BLE001
                        hits = []
                    if hits:
                        break
                if hits:
                    sp = doc[i]
                    break
            if sp is not None:
                W, Hh, M = sp.rect.width, sp.rect.height, 64
                blocos = [b for b in sp.get_text("blocks") if b[4].strip() and b[3] < Hh * 0.86]
                bottom = max((b[3] for b in blocos), default=Hh * 0.5)
                y = bottom + 16
                for label, pg in entries:
                    if y > Hh - 34:
                        break
                    tag_w = 78
                    sp.draw_rect(fitz.Rect(M, y, M + tag_w, y + 14), color=GOLD, fill=GOLDBG, width=0.8)
                    sp.insert_text((M + 5, y + 10), tag, fontsize=6.5, color=GREEN, fontname="hebo")
                    sp.insert_text((M + tag_w + 12, y + 11), label[:60], fontsize=9.5, color=BLACK, fontname="hebo")
                    bw = 36
                    bx = W - M - bw
                    sp.draw_rect(fitz.Rect(bx, y, bx + bw, y + 15), color=GOLD, fill=GOLDBG, width=1)
                    sp.insert_text((bx + 11, y + 11), str(pg), fontsize=9, color=GREEN, fontname="hebo")
                    y += 22
                    ok = True
                if ok:
                    doc.save(tmp.name, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        finally:
            doc.close()
        if not ok:
            return pdf_bytes, False
        with open(tmp.name, "rb") as fh:
            return fh.read(), True
    except Exception:  # noqa: BLE001
        return pdf_bytes, False
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
