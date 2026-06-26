# @module services.georef.generators.dossie — Dossiê consolidado (PDF único).
#
# Reúne, na ordem de protocolo cartorial: Capa → Requerimento → Laudo Técnico →
# Memorial → DRL(s) → CCIR → Certidão/cadeia dominial → documento do cliente.
# O shapefile NÃO entra no PDF (vai como anexo .zip + nota no requerimento/laudo).
import io
import math
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas as rl_canvas
from pypdf import PdfReader, PdfWriter

from pdf.themes import prime2_theme as T
from services.georef.generators import textos as TX

logger = logging.getLogger("romatec")

# Títulos amigáveis de cada item no SUMÁRIO.
_TITULOS_DOSSIE = {
    "requerimento": "Requerimento ao Cartório",
    "laudo_tecnico": "Laudo Técnico de Agrimensura",
    "memorial": "Memorial Descritivo (gerado)",
    "drl": "Declarações de Reconhecimento de Limites (DRL)",
    "mapa": "Mapa / Planta (SIGEF)",
    "art_trt": "ART / TRT / RRT",
    "certidao_matricula": "Certidão de Inteiro Teor (Matrícula)",
    "ccir": "CCIR — Certificado de Cadastro de Imóvel Rural",
    "car": "CAR — Cadastro Ambiental Rural",
    "itr": "ITR — Imposto Territorial Rural",
    "memorial_sigef": "Memorial Descritivo SIGEF (original)",
    "doc_cliente": "Documentos do Proprietário",
}
_LINES_PER_PAGE_SUM = 30   # itens por página do sumário (define o nº de páginas)

# Ordem de protocolo definida pelo RT (José Romário):
# capa → requerimento → laudo → Memorial (sistema) → DRL → Mapa/Planta SIGEF →
# TRT → Certidão de inteiro teor → CCIR → CAR → ITR → Memorial SIGEF (original) →
# documentos pessoais do proprietário.
ORDEM_DOSSIE = [
    "requerimento", "laudo_tecnico", "memorial", "drl", "mapa", "art_trt",
    "certidao_matricula", "ccir", "car", "itr", "memorial_sigef", "doc_cliente",
]
# Peças que entram como ANEXO (PDF/imagem, podendo ser lista de vários arquivos).
_ANEXOS_DOSSIE = ("art_trt", "mapa", "ccir", "car", "itr",
                  "certidao_matricula", "memorial_sigef", "doc_cliente")


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

    # Desmembramento/Remembramento: lista as parcelas resultantes NA CAPA.
    tipo_serv = (projeto.get("tipo_servico") or "").strip().lower()
    parcelas = projeto.get("parcelas") or []
    if tipo_serv in ("desmembramento", "remembramento") and parcelas:
        max_w = w - 4.4 * cm
        y -= 0.5 * cm
        c.setFillColor(accent)
        c.setFont(f["sans_bold"], 10)
        c.drawCentredString(w / 2, y, f"PARCELAS RESULTANTES — {tipo_serv.upper()}")
        y -= 0.65 * cm
        c.setFillColor(fg)
        c.setFont(f["sans"], 9.5)
        itens = [f"Parte I — {(im.get('denominacao') or '—')}"]
        for i, pc in enumerate(parcelas):
            rot = pc.get("rotulo") or f"Parte {i + 2}"
            den = (pc.get("denominacao") or "").strip()
            area = pc.get("area_ha")
            txt = rot + (f" — {den}" if den else "") + (f"  ·  {area} ha" if area else "")
            itens.append(txt)
        for ln in itens[:12]:
            t = ln
            while c.stringWidth(t, f["sans"], 9.5) > max_w and len(t) > 8:
                t = t[:-2]
            if t != ln:
                t = t + "…"
            c.drawCentredString(w / 2, y, t)
            y -= 0.55 * cm
        if len(itens) > 12:
            c.drawCentredString(w / 2, y, f"(+{len(itens) - 12} parcela(s))")
            y -= 0.55 * cm

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


def _secao_pdfs(chave: str, val) -> list:
    """Lista de PDFs (bytes) que compõem uma seção do dossiê."""
    if chave == "drl" and isinstance(val, (list, tuple)):
        return [b for b in val if b]
    if chave in _ANEXOS_DOSSIE:
        itens = val if isinstance(val, (list, tuple)) else [val]
        return [_to_pdf(v) for v in itens if v]
    return [val] if val else []


def _concat_pdfs(pdfs: list) -> bytes:
    """Mescla vários PDFs (bytes) em um só."""
    w = PdfWriter()
    for raw in pdfs:
        _append(w, raw)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _contar_paginas(blob: bytes) -> int:
    try:
        return len(PdfReader(io.BytesIO(blob)).pages)
    except Exception:  # noqa: BLE001
        return 0


def _sumario_bytes(secoes: list, tema="prime_i"):
    """Gera a(s) página(s) do SUMÁRIO e devolve (bytes, links) — onde `links` são
    os retângulos clicáveis [{sum_page, rect, target}] para apontar a cada seção."""
    T.registrar_fontes()
    f = T.fonts()
    tradicional = str(tema).lower() in ("tradicional",)
    fg = black if tradicional else HexColor("#1a1a1a")
    accent = HexColor("#444444") if tradicional else T.C_DOURADO
    dotcol = HexColor("#b3b3b3")

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    margin = 2.2 * cm
    line_h = 0.72 * cm
    links = []

    def cabecalho():
        c.setFillColor(accent)
        c.setFont(f["sans_bold"], 16)
        c.drawString(margin, h - margin, "SUMÁRIO")
        c.setStrokeColor(accent)
        c.setLineWidth(1)
        c.line(margin, h - margin - 0.3 * cm, w - margin, h - margin - 0.3 * cm)

    cabecalho()
    y = h - margin - 1.15 * cm
    sum_page = 0
    na_pagina = 0
    for i, s in enumerate(secoes, 1):
        if na_pagina >= _LINES_PER_PAGE_SUM:
            c.showPage()
            sum_page += 1
            cabecalho()
            y = h - margin - 1.15 * cm
            na_pagina = 0
        titulo = s["titulo"]
        pag = str(s["pagina"] + 1)
        c.setFillColor(accent)
        c.setFont(f["sans_bold"], 10.5)
        c.drawString(margin, y, f"{i}.")
        c.setFillColor(fg)
        c.setFont(f["sans"], 10.5)
        tx = margin + 0.85 * cm
        c.drawString(tx, y, titulo)
        c.setFillColor(accent)
        c.setFont(f["sans_bold"], 10.5)
        c.drawRightString(w - margin, y, pag)
        # leader de pontinhos entre o título e a página
        tw = c.stringWidth(titulo, f["sans"], 10.5)
        pw = c.stringWidth(pag, f["sans_bold"], 10.5)
        dx1, dx2 = tx + tw + 5, w - margin - pw - 6
        if dx2 > dx1:
            dotw = c.stringWidth(".", f["sans"], 10.5) or 3
            c.setFillColor(dotcol)
            c.setFont(f["sans"], 10.5)
            c.drawString(dx1, y, "." * max(0, int((dx2 - dx1) / dotw)))
        links.append({"sum_page": sum_page,
                      "rect": (margin, y - 4, w - margin, y + 11),
                      "target": s["pagina"]})
        y -= line_h
        na_pagina += 1
    c.showPage()
    c.save()
    return buf.getvalue(), links


def gerar_dossie(projeto, partes: dict, tema="prime_i") -> bytes:
    """Monta o dossiê: capa → SUMÁRIO (clicável) → seções na ORDEM_DOSSIE.
    `partes`: dict {chave: bytes | [bytes...]} (PDF ou imagem para anexos)."""
    # 1. coleta as seções presentes, na ordem, já com a contagem de páginas
    secoes = []
    for chave in ORDEM_DOSSIE:
        val = partes.get(chave)
        if not val:
            continue
        blob = _concat_pdfs(_secao_pdfs(chave, val))
        n = _contar_paginas(blob)
        if n > 0:
            secoes.append({"titulo": _TITULOS_DOSSIE.get(chave, chave), "bytes": blob, "n": n})

    capa = _capa_bytes(projeto, tema)
    if not secoes:                       # só a capa
        w = PdfWriter()
        _append(w, capa)
        buf = io.BytesIO()
        w.write(buf)
        return buf.getvalue()

    # 2. nº de páginas do sumário e página inicial (0-indexed) de cada seção
    S = max(1, math.ceil(len(secoes) / _LINES_PER_PAGE_SUM))
    running = 1 + S                      # capa(1) + sumário(S)
    for s in secoes:
        s["pagina"] = running
        running += s["n"]

    sumario, links = _sumario_bytes(secoes, tema)

    # 3. montagem final
    writer = PdfWriter()
    _append(writer, capa)
    _append(writer, sumario)
    for s in secoes:
        _append(writer, s["bytes"])

    # 4. marcadores (bookmarks/outline) — navegação lateral
    try:
        writer.add_outline_item("Capa", 0)
        writer.add_outline_item("Sumário", 1)
        for s in secoes:
            writer.add_outline_item(s["titulo"], s["pagina"])
    except Exception as e:  # noqa: BLE001
        logger.warning("Dossiê: outline falhou (%s).", e)

    # 5. links clicáveis no sumário (cada linha → página da seção).
    # Destino com a REFERÊNCIA da página (não índice inteiro) p/ funcionar em todo
    # visualizador; inserido direto no /Annots (add_annotation só aceita o builder).
    try:
        from pypdf.generic import (DictionaryObject, NameObject, ArrayObject,
                                    NumberObject, FloatObject)
        for lk in links:
            sum_pg = writer.pages[1 + lk["sum_page"]]
            page_ref = writer.pages[lk["target"]].indirect_reference
            annot = DictionaryObject({
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Link"),
                NameObject("/Rect"): ArrayObject([FloatObject(v) for v in lk["rect"]]),
                NameObject("/Border"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)]),
                NameObject("/Dest"): ArrayObject([page_ref, NameObject("/Fit")]),
            })
            ref = writer._add_object(annot)
            if "/Annots" in sum_pg:
                sum_pg[NameObject("/Annots")].append(ref)
            else:
                sum_pg[NameObject("/Annots")] = ArrayObject([ref])
    except Exception as e:  # noqa: BLE001
        logger.warning("Dossiê: links do sumário falharam (%s).", e)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
