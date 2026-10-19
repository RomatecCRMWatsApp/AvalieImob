# @module pdf.garantia_pdf — PDF do Laudo de Avaliação de Garantia (Res. CMN 4.676/2018 · NBR 14.653).
# Consome o conteúdo de services.garantia_conteudo (fonte única, mesma do DOCX) e os bytes
# preparados por services.garantia_assets.preparar (fotos, anexos, perfil, logo).
# Chamado por routes/garantias (PDF/visualizar/envios) e routes/assinatura (_gerar_pdf, ICP).
from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle,
)

from pdf.templates.resilient import ResilientSimpleDocTemplate
from services import garantia_conteudo as C

VERDE = colors.HexColor("#0C3320")
VERDE_CLARO = colors.HexColor("#EEF4EF")
DOURADO = colors.HexColor("#C9A84C")
CINZA = colors.HexColor("#555555")

W, H = A4
MARGEM = 2.0 * cm
LARG = W - 2 * MARGEM


def _st():
    return {
        "body": ParagraphStyle("b", fontName="Helvetica", fontSize=9.5, leading=13.5,
                               alignment=TA_JUSTIFY, textColor=colors.HexColor("#222222")),
        "lbl": ParagraphStyle("l", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
                              textColor=VERDE),
        "val": ParagraphStyle("v", fontName="Helvetica", fontSize=8.8, leading=11.5),
        "sec": ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=10.5, leading=13,
                              textColor=colors.white),
        "leg": ParagraphStyle("g", fontName="Helvetica-Oblique", fontSize=7.5, leading=9,
                              alignment=TA_CENTER, textColor=CINZA),
        "ass": ParagraphStyle("a", fontName="Helvetica", fontSize=8.8, leading=11.5,
                              alignment=TA_CENTER),
        "assb": ParagraphStyle("ab", fontName="Helvetica-Bold", fontSize=9.5, leading=12,
                               alignment=TA_CENTER),
    }


def _x(t) -> str:
    return escape(str(t or "")).replace("\n", "<br/>")


def _faixa(titulo: str, n: int, st) -> Table:
    rot = f"{n}. {_x(titulo)}" if n else _x(titulo)
    t = Table([[Paragraph(rot, st["sec"])]], colWidths=[LARG])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), VERDE),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, DOURADO),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _tabela_kv(pares, st) -> Table:
    linhas = [[Paragraph(_x(r), st["lbl"]), Paragraph(_x(v), st["val"])] for r, v in pares]
    t = Table(linhas, colWidths=[LARG * 0.36, LARG * 0.64])
    estilo = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(0, len(linhas), 2):
        estilo.append(("BACKGROUND", (0, i), (-1, i), VERDE_CLARO))
    t.setStyle(TableStyle(estilo))
    return t


def _img(raw: bytes, max_w: float, max_h: float):
    try:
        from PIL import Image as PILImage
        im = PILImage.open(io.BytesIO(raw))
        im = im.convert("RGB")
        im.thumbnail((1500, 1500))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80)
        buf.seek(0)
        iw, ih = im.size
        esc = min(max_w / iw, max_h / ih)
        return Image(buf, width=iw * esc, height=ih * esc)
    except Exception:  # noqa: BLE001
        return None


def _paginas_pdf(raw: bytes) -> list[bytes]:
    """Anexo em PDF → páginas PNG (para entrar no laudo como imagem)."""
    try:
        import fitz
        d = fitz.open(stream=raw, filetype="pdf")
        out = [p.get_pixmap(dpi=110).tobytes("png") for p in d][:6]
        d.close()
        return out
    except Exception:  # noqa: BLE001
        return []


def _onpage_factory(g: dict):
    logo = g.get("_brand_logo_bytes")
    numero = g.get("numero") or ""

    def _onpage(c, doc):
        c.saveState()
        pg = c.getPageNumber()
        if pg == 1:
            c.setFillColor(VERDE)
            c.rect(0, H - 4.2 * cm, W, 4.2 * cm, stroke=0, fill=1)
            c.setFillColor(DOURADO)
            c.rect(0, H - 4.35 * cm, W, 0.15 * cm, stroke=0, fill=1)
            try:
                from pdf.brand_seal import draw_header_lockup
                draw_header_lockup(c, MARGEM, H - 2.1 * cm, mark=13 * mm, light=True,
                                   tagline="AVALIAÇÃO DE GARANTIAS · NBR 14.653", logo_bytes=logo)
            except Exception:  # noqa: BLE001
                pass
        else:
            try:
                from pdf.brand_seal import draw_header_lockup
                draw_header_lockup(c, MARGEM, H - 1.15 * cm, mark=8 * mm,
                                   tagline="AVALIAÇÃO DE GARANTIAS", logo_bytes=logo)
            except Exception:  # noqa: BLE001
                pass
            c.setFont("Helvetica", 7.5)
            c.setFillColor(CINZA)
            c.drawRightString(W - MARGEM, H - 1.15 * cm, f"Laudo {numero}")
            c.setStrokeColor(DOURADO)
            c.setLineWidth(0.8)
            c.line(MARGEM, H - 1.75 * cm, W - MARGEM, H - 1.75 * cm)
        c.setStrokeColor(colors.HexColor("#D9E2DB"))
        c.line(MARGEM, 1.4 * cm, W - MARGEM, 1.4 * cm)
        c.setFont("Helvetica", 7)
        c.setFillColor(CINZA)
        c.drawString(MARGEM, 1.0 * cm, "Res. CMN 4.676/2018 · ABNT NBR 14.653 — Laudo de Avaliação de Garantia")
        c.drawRightString(W - MARGEM, 1.0 * cm, f"Página {pg}")
        c.restoreState()

    return _onpage


def _capa(g: dict, st) -> list:
    cap_t = ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=20, leading=24,
                           alignment=TA_CENTER, textColor=VERDE)
    cap_s = ParagraphStyle("cs", fontName="Helvetica", fontSize=11, leading=15,
                           alignment=TA_CENTER, textColor=CINZA)
    val_s = ParagraphStyle("cv", fontName="Helvetica-Bold", fontSize=22, leading=26,
                           alignment=TA_CENTER, textColor=VERDE)
    rt = C.dados_rt(g)
    els = [Spacer(1, 3.4 * cm),
           Paragraph(C.titulo_laudo(g), cap_t), Spacer(1, 6),
           Paragraph(_x(C.subtitulo(g)), cap_s), Spacer(1, 4),
           Paragraph(f"Laudo nº {_x(g.get('numero') or '—')}", cap_s), Spacer(1, 1.0 * cm)]
    if g.get("_fotos_bytes"):
        im = _img(g["_fotos_bytes"][0][0], LARG, 7.5 * cm)
        if im:
            els += [im, Spacer(1, 0.6 * cm)]
    sol = g.get("solicitante") or {}
    pares = [(r, v) for r, v in [
        ("Bem avaliado", C.descricao_curta(g)),
        ("Localização", " — ".join([x for x in [g.get("endereco"), " / ".join([y for y in [g.get("municipio"), g.get("uf")] if y])] if x])),
        ("Instituição financeira", g.get("instituicao_financeira") or sol.get("instituicao_financeira")),
        ("Solicitante", sol.get("nome")),
        ("Data da avaliação", C.data_br(g.get("data_avaliacao")) or datetime.now().strftime("%d/%m/%Y")),
        ("Responsável técnico", rt.get("nome")),
    ] if v]
    if pares:
        els.append(_tabela_kv(pares, st))
    vp = C.valor_principal(g)
    if vp:
        els += [Spacer(1, 0.8 * cm),
                Paragraph("VALOR DE MERCADO", ParagraphStyle("vl", fontName="Helvetica-Bold", fontSize=9,
                                                             alignment=TA_CENTER, textColor=DOURADO)),
                Paragraph(C.brl(vp), val_s)]
    els.append(PageBreak())
    return els


def _assinatura(g: dict, st) -> list:
    rt = C.dados_rt(g)
    els = [Spacer(1, 1.2 * cm)]
    local = " / ".join([x for x in [g.get("municipio"), g.get("uf")] if x])
    data = C.data_br(g.get("data_avaliacao")) or datetime.now().strftime("%d/%m/%Y")
    els.append(Paragraph(_x(f"{local + ', ' if local else ''}{data}."), st["ass"]))
    els.append(Spacer(1, 1.6 * cm))
    els.append(Paragraph("_" * 52, st["ass"]))
    if rt.get("nome"):
        els.append(Paragraph(_x(rt["nome"].upper()), st["assb"]))
    if rt.get("registros_linhas"):
        els.append(Paragraph(_x("Avaliador — " + " · ".join(rt["registros_linhas"])), st["ass"]))
    for k in ("endereco", "telefone", "email"):
        if rt.get(k):
            els.append(Paragraph(_x(rt[k]), st["ass"]))
    return [KeepTogether(els)]


def _fotos(g: dict, st) -> list:
    fotos = g.get("_fotos_bytes") or []
    if not fotos:
        return []
    els = [PageBreak(), _faixa("ANEXO I — RELATÓRIO FOTOGRÁFICO", None, st)]
    els.append(Spacer(1, 8))
    col = LARG / 2 - 6
    celulas = []
    for raw, leg in fotos:
        im = _img(raw, col, 6.2 * cm)
        if im:
            celulas.append([im, Paragraph(_x(leg), st["leg"])])
    linhas = [celulas[i:i + 2] for i in range(0, len(celulas), 2)]
    if linhas and len(linhas[-1]) == 1:
        linhas[-1].append("")
    if linhas:
        t = Table(linhas, colWidths=[LARG / 2, LARG / 2])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
        els.append(t)
    return els


def _anexos(g: dict, st) -> list:
    anexos = g.get("_anexos_bytes") or []
    els = []
    for raw, rotulo in anexos:
        imagens = _paginas_pdf(raw) if raw[:5] == b"%PDF-" else [raw]
        for i, b in enumerate(imagens, 1):
            im = _img(b, LARG, H - 7 * cm)
            if not im:
                continue
            tit = f"ANEXO — {rotulo}" + (f" (pág. {i})" if len(imagens) > 1 else "")
            els += [PageBreak(), Paragraph(_x(tit), st["lbl"]), Spacer(1, 6), im]
    return els


def generate_garantia_pdf(g: dict, perfil: dict | None = None) -> bytes:
    if perfil and not g.get("_perfil"):
        g["_perfil"] = perfil
    st = _st()
    buf = io.BytesIO()
    doc = ResilientSimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=2.3 * cm, bottomMargin=1.9 * cm,
        title=f"Laudo de Avaliação de Garantia {g.get('numero') or ''}".strip(),
        author=C.dados_rt(g).get("nome") or "AvalieImob",
    )
    story = _capa(g, st)
    for n, sec in enumerate(C.secoes(g), 1):
        bloco = [_faixa(sec["titulo"], n, st), Spacer(1, 6)]
        primeiro = True
        for tipo, conteudo in sec["blocos"]:
            el = _tabela_kv(conteudo, st) if tipo == "kv" else Paragraph(_x(conteudo), st["body"])
            if primeiro:
                story.append(KeepTogether(bloco + [el]))
                primeiro = False
            else:
                story.append(el)
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 6))
    story += _assinatura(g, st)
    story += _fotos(g, st)
    story += _anexos(g, st)
    onpage = _onpage_factory(g)
    doc.build(story, onFirstPage=onpage, onLaterPages=onpage)
    return buf.getvalue()
