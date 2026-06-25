# @module services.georef.generators.dossie — Dossiê consolidado (PDF único).
#
# Reúne, na ordem de protocolo cartorial: Capa → Requerimento → Laudo Técnico →
# Memorial → DRL(s) → CCIR → Certidão/cadeia dominial → documento do cliente.
# O shapefile NÃO entra no PDF (vai como anexo .zip + nota no requerimento/laudo).
import io
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas as rl_canvas
from pypdf import PdfReader, PdfWriter

from pdf.themes import prime2_theme as T
from services.georef.generators import textos as TX

logger = logging.getLogger("romatec")

ORDEM_DOSSIE = [
    "requerimento", "laudo_tecnico", "memorial", "art_trt", "drl",
    "ccir", "car", "itr", "certidao_matricula", "doc_cliente",
]


def _quebrar_em_duas(c, texto, font, size, max_w):
    """Melhor ponto de quebra (equilibra a largura das 2 linhas). -> (wmax, l1, l2)."""
    palavras = texto.split()
    melhor = None
    for i in range(1, len(palavras)):
        l1, l2 = " ".join(palavras[:i]), " ".join(palavras[i:])
        wmax = max(c.stringWidth(l1, font, size), c.stringWidth(l2, font, size))
        if melhor is None or wmax < melhor[0]:
            melhor = (wmax, l1, l2)
    return melhor


def _draw_titulo_capa(c, texto, w, y_top, font, cor, margem):
    """Título da capa que NUNCA estoura a largura: ajusta a fonte e quebra em 2 linhas."""
    max_w = w - 2 * margem
    c.setFillColor(cor)
    for size in (24, 22, 20, 18, 16):              # 1 linha: maior fonte que couber
        if c.stringWidth(texto, font, size) <= max_w:
            c.setFont(font, size)
            c.drawCentredString(w / 2, y_top, texto)
            return
    palavras = texto.split()
    if len(palavras) >= 2:                          # 2 linhas equilibradas
        for size in (20, 18, 16, 15, 14, 13):
            m = _quebrar_em_duas(c, texto, font, size, max_w)
            if m and m[0] <= max_w:
                c.setFont(font, size)
                c.drawCentredString(w / 2, y_top + 0.45 * cm, m[1])
                c.drawCentredString(w / 2, y_top - 0.45 * cm, m[2])
                return
    t = texto                                       # fallback: trunca com reticências
    c.setFont(font, 16)
    while len(t) > 4 and c.stringWidth(t + "…", font, 16) > max_w:
        t = t[:-1]
    c.drawCentredString(w / 2, y_top, t + "…")


def _capa_bytes(projeto, tema="prime_i") -> bytes:
    T.registrar_fontes()
    f = T.fonts()
    im = projeto.get("imovel") or {}
    rt = projeto.get("responsavel_tecnico") or {}
    tradicional = (str(tema).lower() in ("tradicional",))

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    if not tradicional:
        c.setFillColor(T.C_VERDE_ESCURO)
        c.rect(0, 0, w, h, fill=1, stroke=0)
        fg, accent = white, T.C_DOURADO
    else:
        fg, accent = black, HexColor("#333333")

    try:
        from pdf.brand_seal import draw_header_lockup
        draw_header_lockup(c, 2.2 * cm, h - 2.2 * cm, mark=1.2 * cm, light=not tradicional,
                           tagline="Topografia & Geo · INCRA/SIGEF")
    except Exception:  # noqa: BLE001
        pass

    c.setFillColor(accent)
    c.setFont(f["sans_bold"], 11)
    c.drawCentredString(w / 2, h - 6.5 * cm, "DOSSIÊ TÉCNICO DE GEORREFERENCIAMENTO")
    titulo = (im.get("denominacao") or "Imóvel Rural").strip()
    _draw_titulo_capa(c, titulo, w, h - 8.0 * cm, f["serif_bold"], fg, 2.2 * cm)

    c.setFont(f["sans"], 11)
    linhas = [
        f"Matrícula nº {im.get('matricula') or '—'}  ·  INCRA/SNCR {im.get('cod_incra') or '—'}",
        f"{im.get('municipio') or '—'}/{im.get('uf') or '—'}  ·  {im.get('cartorio_nome') or '—'}",
        f"Área {im.get('area_ha') or '—'} ha  ·  Perímetro {im.get('perimetro_m') or '—'} m",
        f"Proprietário: {im.get('proprietario_nome') or '—'}",
        f"Certificação SIGEF: {im.get('certificacao_sigef') or '—'}",
    ]
    y = h - 10.0 * cm
    for ln in linhas:
        c.drawCentredString(w / 2, y, ln)
        y -= 0.7 * cm

    c.setStrokeColor(accent)
    c.setLineWidth(1)
    c.line(2.2 * cm, 5.0 * cm, w - 2.2 * cm, 5.0 * cm)
    c.setFont(f["sans"], 9)
    c.drawCentredString(
        w / 2, 4.4 * cm,
        f"Responsável Técnico: {rt.get('nome') or '—'} — {rt.get('conselho') or '—'} — "
        f"Cód. INCRA {rt.get('credenciamento_incra') or '—'}",
    )
    c.drawCentredString(w / 2, 3.9 * cm, TX.data_extenso(im.get("municipio"), im.get("uf")))
    c.showPage()
    c.save()
    return buf.getvalue()


def _img_para_pdf(raw: bytes) -> bytes:
    """Converte uma imagem em uma página PDF A4 (encaixe proporcional)."""
    from PIL import Image
    im = Image.open(io.BytesIO(raw))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    margem = 1.2 * cm
    maxw, maxh = w - 2 * margem, h - 2 * margem
    iw, ih = im.size
    escala = min(maxw / iw, maxh / ih)
    dw, dh = iw * escala, ih * escala
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(im), (w - dw) / 2, (h - dh) / 2, dw, dh,
                preserveAspectRatio=True, mask="auto")
    c.showPage()
    c.save()
    return buf.getvalue()


def _to_pdf(raw: bytes) -> bytes:
    """Normaliza um anexo (PDF passa direto; imagem vira página PDF)."""
    if raw[:5] == b"%PDF-":
        return raw
    try:
        return _img_para_pdf(raw)
    except Exception as e:  # noqa: BLE001
        logger.warning("Dossiê: anexo não-PDF/imagem ignorado (%s).", e)
        return b""


def _append(writer: PdfWriter, raw: bytes):
    if not raw:
        return
    try:
        reader = PdfReader(io.BytesIO(raw))
        for page in reader.pages:
            writer.add_page(page)
    except Exception as e:  # noqa: BLE001
        logger.warning("Dossiê: bloco ignorado ao mesclar (%s).", e)


def gerar_dossie(projeto, partes: dict, tema="prime_i") -> bytes:
    """`partes`: {requerimento, laudo_tecnico, memorial, drl:[bytes...],
    ccir, certidao_matricula, doc_cliente} em bytes (PDF ou imagem para anexos)."""
    writer = PdfWriter()
    _append(writer, _capa_bytes(projeto, tema))
    for chave in ORDEM_DOSSIE:
        val = partes.get(chave)
        if not val:
            continue
        if chave == "drl" and isinstance(val, (list, tuple)):
            for drl_bytes in val:
                _append(writer, drl_bytes)
        elif chave in ("art_trt", "ccir", "car", "itr", "certidao_matricula", "doc_cliente"):
            _append(writer, _to_pdf(val))
        else:
            _append(writer, val)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
