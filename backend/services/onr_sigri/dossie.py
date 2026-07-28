# @module services.onr_sigri.dossie — Dossiê de protocolo consolidado do ONR (SIG-RI).
#
# Monta UM PDF com: Capa (identificação do imóvel) + Descrição do polígono (memória
# descritiva) + os ANEXOS selecionados na composição (services.onr_sigri.composicao),
# na ordem dos anexos. PDF passa direto; imagem vira página A4. Reusa reportlab/pypdf/PIL.
from __future__ import annotations

import base64
import io
import logging
from typing import List, Optional

logger = logging.getLogger("romatec")

_GREEN = (0.047, 0.20, 0.122)   # #0C3320
_GOLD = (0.788, 0.659, 0.298)   # #C9A84C


def _br(n, casas=2) -> str:
    try:
        s = f"{float(n):,.{casas}f}"
    except (TypeError, ValueError):
        return "—"
    return s.replace(",", "␟").replace(".", ",").replace("␟", ".")


def descricao_poligono(job: dict) -> str:
    """Memória descritiva p/ colar no mapa.onr.org.br (Prov. CNJ 195/2025).
    Porta a mesma lógica do front (OnrSigriPage.descricaoPoligono)."""
    mat = (job.get("matriculas") or [{}])[0] or {}
    prop = (job.get("partes") or [{}])[0] or {}
    area = float(job.get("area_declarada_m2") or 0)
    nv = len(job.get("vertices") or [])
    uf = job.get("uf") or ""
    serventia = (job.get("cartorio") or {}).get("comarca") or job.get("municipio") or ""
    fuso = job.get("fuso")
    mc = (-183 + 6 * int(fuso)) if fuso else None
    t = "Polígono do imóvel"
    if job.get("denominacao_imovel"):
        t += f" denominado {job['denominacao_imovel']}"
    if mat.get("matricula"):
        t += f", matrícula nº {mat['matricula']}"
        if serventia:
            t += f" do Registro de Imóveis de {serventia}/{uf}"
    if prop.get("nome"):
        t += f", de propriedade de {prop['nome']}"
        if prop.get("cpf"):
            t += f" (CPF/CNPJ {prop['cpf']})"
    if job.get("municipio"):
        t += f", situado no Município de {job['municipio']}/{uf}"
    t += "."
    if area:
        t += f" Área de {_br(area, 2)} m² ({_br(area / 10000, 4)} ha)"
    if job.get("perimetro_m"):
        t += f"{',' if area else '.'} perímetro de {_br(job['perimetro_m'], 2)} m"
    if nv:
        t += f", definido por {nv} vértices"
    t += ". Sistema geodésico de referência: SIRGAS 2000 (EPSG:4674)"
    if fuso:
        t += f", UTM fuso {fuso}{job.get('hemisferio') or 'S'}, MC {mc}°"
    t += "."
    bci = job.get("bci") or {}
    insc = job.get("inscricao_municipal") or bci.get("inscricao_contribuinte")
    if insc:
        t += f" Inscrição municipal nº {insc}"
        if bci.get("area_edificada_m2"):
            t += f", área edificada de {_br(bci['area_edificada_m2'], 2)} m²"
        t += "."
    iptu = job.get("iptu") or {}
    if iptu.get("cnd_numero"):
        t += f" IPTU regular — Certidão Negativa nº {iptu['cnd_numero']}"
        if iptu.get("cnd_validade"):
            t += f" (válida até {'/'.join(reversed(str(iptu['cnd_validade']).split('-')))})"
        t += "."
    elif iptu.get("situacao"):
        t += f" Situação do IPTU: {str(iptu['situacao']).replace('_', ' ')}."
    t += " Levantamento conforme ABNT NBR 17047:2022 e Provimento CNJ nº 195/2025."
    return t


# ──────────────────────────────────────────────────────────────────────────────
# Páginas geradas (capa + descrição) e conversão imagem→PDF
# ──────────────────────────────────────────────────────────────────────────────
def _capa_e_descricao_bytes(job: dict, com_capa: bool, com_descr: bool) -> Optional[bytes]:
    """Capa (identificação + miniatura de satélite) e/ou a descrição do polígono,
    num único PDF gerado. Retorna None se nada foi pedido."""
    if not (com_capa or com_descr):
        return None
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)

    if com_capa:
        c.setFillColorRGB(*_GREEN)
        c.rect(0, H - 34 * mm, W, 34 * mm, fill=1, stroke=0)
        c.setFillColorRGB(*_GOLD)
        c.rect(0, H - 35.2 * mm, W, 1.2 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(20 * mm, H - 20 * mm, "DOSSIÊ DE PROTOCOLO — SIG-RI / ONR")
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, H - 28 * mm,
                     f"{job.get('numero') or ''}  ·  ABNT NBR 17047 · Prov. CNJ 195/2025")

        mat = (job.get("matriculas") or [{}])[0] or {}
        prop = (job.get("partes") or [{}])[0] or {}
        area = float(job.get("area_declarada_m2") or 0)
        rt = job.get("responsavel_tecnico") or {}
        linhas = [
            ("Imóvel", job.get("denominacao_imovel") or job.get("nome") or "—"),
            ("Matrícula", mat.get("matricula") or "—"),
            ("Proprietário", prop.get("nome") or "—"),
            ("Município/UF", f"{job.get('municipio') or '—'}/{job.get('uf') or ''}"),
            ("Cartório", (job.get("cartorio") or {}).get("nome") or "—"),
            ("Área", f"{_br(area, 2)} m²  ({_br(area / 10000, 4)} ha)" if area else "—"),
            ("Perímetro", f"{_br(job.get('perimetro_m'), 2)} m" if job.get("perimetro_m") else "—"),
            ("Vértices", str(len(job.get("vertices") or [])) or "—"),
            ("SRC", f"SIRGAS 2000 · UTM fuso {job.get('fuso')}{job.get('hemisferio') or 'S'}"
                    if job.get("fuso") else "SIRGAS 2000 (EPSG:4674)"),
            ("ART/TRT", job.get("trt_numero") or "—"),
            ("Resp. técnico", f"{rt.get('nome') or '—'} — {rt.get('conselho') or ''}"),
        ]
        y = H - 48 * mm
        c.setFillColorRGB(0.13, 0.13, 0.13)
        for rot, val in linhas:
            c.setFont("Helvetica-Bold", 9.5)
            c.drawString(20 * mm, y, f"{rot}:")
            c.setFont("Helvetica", 9.5)
            c.drawString(55 * mm, y, str(val)[:70])
            y -= 7 * mm

        # Miniatura de satélite com a poligonal (se houver)
        prev = job.get("preview_b64") or ""
        if prev.startswith("data:image"):
            try:
                raw = base64.b64decode(prev.split(",", 1)[1])
                img = ImageReader(io.BytesIO(raw))
                iw, ih = img.getSize()
                dw = W - 40 * mm
                dh = dw * ih / iw
                if dh > (y - 25 * mm):
                    dh = y - 25 * mm
                    dw = dh * iw / ih
                c.drawImage(img, (W - dw) / 2, y - dh - 4 * mm, dw, dh,
                            preserveAspectRatio=True, mask="auto")
            except Exception:  # noqa: BLE001
                pass
        c.showPage()

    if com_descr:
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Frame, Paragraph
        c.setFillColorRGB(*_GREEN)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(20 * mm, H - 22 * mm, "Descrição do polígono (memória descritiva)")
        c.setFillColorRGB(*_GOLD)
        c.rect(20 * mm, H - 25 * mm, W - 40 * mm, 0.8 * mm, fill=1, stroke=0)
        styles = getSampleStyleSheet()
        st = styles["BodyText"]
        st.fontSize = 11
        st.leading = 16
        p = Paragraph(descricao_poligono(job), st)
        Frame(20 * mm, 20 * mm, W - 40 * mm, H - 50 * mm, showBoundary=0).addFromList([p], c)
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(20 * mm, 14 * mm,
                     'Texto para colar no campo "Descrição do polígono" do mapa.onr.org.br.')
        c.showPage()

    c.save()
    return buf.getvalue()


def _imagem_para_pdf(raw: bytes) -> Optional[bytes]:
    """Imagem (bytes) → 1 página A4 (PDF bytes), centralizada e escalada."""
    try:
        from PIL import Image
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
        im = Image.open(io.BytesIO(raw))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        buf = io.BytesIO()
        W, H = A4
        c = canvas.Canvas(buf, pagesize=A4)
        iw, ih = im.size
        margin = 28
        maxw, maxh = W - 2 * margin, H - 2 * margin
        sc = min(maxw / iw, maxh / ih)
        dw, dh = iw * sc, ih * sc
        c.drawImage(ImageReader(im), (W - dw) / 2, (H - dh) / 2, dw, dh,
                    preserveAspectRatio=True, mask="auto")
        c.showPage()
        c.save()
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return None


def gerar_dossie(job: dict, com_capa: bool, com_descr: bool, anexos: List[dict]) -> bytes:
    """Concatena capa/descrição (gerados) + os anexos selecionados.
    `anexos`: [{'nome','mime','bytes'}] na ordem. PDF passa direto; imagem vira página."""
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()

    def _add(pdf_bytes: Optional[bytes]):
        if not pdf_bytes:
            return
        try:
            for pg in PdfReader(io.BytesIO(pdf_bytes)).pages:
                writer.add_page(pg)
        except Exception:  # noqa: BLE001
            logger.warning("ONR dossiê: página inválida ignorada")

    _add(_capa_e_descricao_bytes(job, com_capa, com_descr))
    for a in anexos or []:
        raw = a.get("bytes")
        if not raw:
            continue
        if raw[:5] == b"%PDF-":
            _add(raw)
        else:
            _add(_imagem_para_pdf(raw))

    if not writer.pages:                 # nada selecionado → capa mínima p/ não sair vazio
        _add(_capa_e_descricao_bytes(job, True, False))
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
