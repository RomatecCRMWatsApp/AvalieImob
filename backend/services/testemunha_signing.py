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


_DEJAVU_BOLD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "DejaVuSans-Bold.ttf")
_FONTE_SUM = "Helvetica-Bold"


def _registrar_fonte_sumario():
    """Registra a DejaVuSans-Bold (mesma fonte do sumário do contrato) no ReportLab."""
    global _FONTE_SUM
    if _FONTE_SUM != "Helvetica-Bold":
        return _FONTE_SUM
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        if os.path.exists(_DEJAVU_BOLD):
            pdfmetrics.registerFont(TTFont("SumarioDejaVuBold", _DEJAVU_BOLD))
            _FONTE_SUM = "SumarioDejaVuBold"
    except Exception:  # noqa: BLE001
        pass
    return _FONTE_SUM


def inserir_no_sumario(pdf_bytes: bytes, entries: list, tag: str = "ANEXO") -> tuple:
    """Sobrepõe linhas no SUMÁRIO do contrato, no MESMO padrão das cláusulas (cores/fonte/
    cantos arredondados extraídos do próprio contrato), via show_pdf_page + INCREMENTAL
    (append-only, preserva as assinaturas). `entries` = [(label, pagina_1idx)]."""
    if not entries:
        return pdf_bytes, False
    import io
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.colors import HexColor
    # cores EXATAS extraídas do sumário do contrato
    GOLD = HexColor("#C8A84B")        # preenchimento da tag / borda
    TAG_TXT = HexColor("#051A10")     # texto da tag (verde-escuro)
    LABEL = HexColor("#FFFFFF")       # label (branco)
    NUM = HexColor("#C9A84C")         # número (dourado)
    NUMBG = HexColor("#10241A")       # fundo da caixa do número (verde-escuro)
    DOTS = HexColor("#E2C46B")        # pontilhado

    def _is_gold(c):
        return c and abs(c[0] - 0.784) < 0.11 and abs(c[1] - 0.659) < 0.11 and abs(c[2] - 0.294) < 0.11

    fonte = _registrar_fonte_sumario()
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
                W, Hh = sp.rect.width, sp.rect.height
                # detecta a geometria das TAGS douradas (cláusulas) e da caixa do número
                tags, nbs = [], []
                for dr in sp.get_drawings():
                    r = dr["rect"]
                    if _is_gold(dr.get("fill")) and 70 < r.width < 130 and 12 < r.height < 22 and r.x0 < W * 0.45:
                        tags.append(r)
                    if _is_gold(dr.get("color")) and 28 < r.width < 60 and 12 < r.height < 22 and r.x0 > W * 0.6:
                        nbs.append(r)
                if tags:
                    tags.sort(key=lambda r: r.y0)
                    last = tags[-1]
                    ys = sorted({round(r.y0, 1) for r in tags})
                    spacing = (ys[-1] - ys[-2]) if len(ys) >= 2 else 29.0
                    tag_x, tag_w, tag_h = last.x0, last.width, last.height
                    nbs.sort(key=lambda r: r.y0)
                    nb = nbs[-1] if nbs else None
                    num_x, num_w = (nb.x0, nb.width) if nb else (W - tag_x - 42, 42)
                    label_x = tag_x + tag_w + 12
                    rad = min(4.0, tag_h / 3.5)

                    buf = io.BytesIO()
                    ov = rl_canvas.Canvas(buf, pagesize=(W, Hh))
                    y_top = last.y0
                    for label, pg in entries:
                        y_top += spacing
                        if y_top + tag_h > Hh - 22:
                            break
                        by = Hh - y_top - tag_h        # base da linha (ReportLab)
                        # TAG arredondada dourada + texto verde
                        ov.setFillColor(GOLD)
                        ov.roundRect(tag_x, by, tag_w, tag_h, rad, fill=1, stroke=0)
                        ov.setFillColor(TAG_TXT)
                        ov.setFont(fonte, 8)
                        tw = ov.stringWidth(tag, fonte, 8)
                        ov.drawString(tag_x + (tag_w - tw) / 2, by + (tag_h - 8) / 2 + 1.6, tag)
                        # LABEL branco — encolhe (10.5→8.5) e trunca p/ NÃO invadir o número
                        avail = num_x - label_x - 16
                        lsize = 10.5
                        while lsize > 8.5 and ov.stringWidth(label, fonte, lsize) > avail:
                            lsize -= 0.5
                        lbl = label
                        if ov.stringWidth(lbl, fonte, lsize) > avail:
                            while lbl and ov.stringWidth(lbl + "…", fonte, lsize) > avail:
                                lbl = lbl[:-1]
                            lbl = lbl + "…"
                        ov.setFillColor(LABEL)
                        ov.setFont(fonte, lsize)
                        ov.drawString(label_x, by + (tag_h - lsize) / 2 + 2.0, lbl)
                        lw = ov.stringWidth(lbl, fonte, lsize)
                        # caixa do NÚMERO arredondada (fundo escuro, borda dourada)
                        ov.setFillColor(NUMBG)
                        ov.setStrokeColor(GOLD)
                        ov.setLineWidth(0.8)
                        ov.roundRect(num_x, by, num_w, tag_h, rad, fill=1, stroke=1)
                        ov.setFillColor(NUM)
                        ov.setFont(fonte, 10)
                        nw = ov.stringWidth(str(pg), fonte, 10)
                        ov.drawString(num_x + (num_w - nw) / 2, by + (tag_h - 10) / 2 + 1.8, str(pg))
                        # pontilhado dourado
                        ov.setStrokeColor(DOTS)
                        ov.setLineWidth(1.0)
                        ov.setDash(1, 2.5)
                        ov.line(label_x + lw + 6, by + tag_h / 2, num_x - 6, by + tag_h / 2)
                        ov.setDash()
                        ok = True
                    ov.save()
                    buf.seek(0)
                    if ok:
                        ovd = fitz.open("pdf", buf.read())
                        try:
                            sp.show_pdf_page(sp.rect, ovd, 0)
                            doc.save(tmp.name, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
                        finally:
                            ovd.close()
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
