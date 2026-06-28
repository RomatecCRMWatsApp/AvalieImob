# @module services.geo_urbano.generators.dossie — Dossiê consolidado (capa+sumário+ordem §9).
#
# Monta o PDF de protocolo: CAPA descritiva → SUMÁRIO (ordem + página real) →
# documentos na ordem oficial do §9 (Requerimentos → Mapas → Memorial → Cadeia →
# TRT → Certidões → IPTU → BCIs → Documentos do proprietário POR ÚLTIMO).
from __future__ import annotations

import io
import math
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, black
from reportlab.pdfgen import canvas as rl_canvas
from pypdf import PdfReader, PdfWriter

from pdf.themes import prime2_theme as T
from services.geo_urbano.generators import textos as TX

# Ordem oficial de montagem (§9). Cada entrada: (key em `partes`, título no sumário).
ORDEM_DOSSIE = [
    ("requerimento_cartorio", "Requerimento — Via 1 (Cartório de RI)"),
    ("requerimento_superintendencia", "Requerimento — Via 2 (Superintendência)"),
    ("oficio_aprovacao", "Ofício de Aprovação ao Cartório (Superintendência)"),
    ("quadro_retificacao", "Quadro de Retificação (de → para)"),
    ("mapa_atual", "Mapa Atual"),
    ("mapa_remembramento", "Mapa de Remembramento"),
    ("mapa_desdobro", "Mapas de Desdobro (por lote resultante)"),
    ("mapa_retificado", "Mapa Retificado"),
    ("memorial_descritivo", "Memorial Descritivo"),
    ("drl", "Declarações de Reconhecimento de Limites (DRL — anuência)"),
    ("cadeia_dominical", "Cadeia Dominical"),
    ("art_trt", "ART / TRT / RRT"),
    ("boleto_trt", "Boleto da TRT"),
    ("comprovante_pagamento_trt", "Comprovante de Pagamento da TRT"),
    ("certidoes_inteiro_teor", "Certidões de Inteiro Teor (por matrícula)"),
    ("iptu", "Regularidade de IPTU (CND / guia paga)"),
    ("bci", "Boletins de Cadastro Imobiliário (BCI)"),
    ("documentos_proprietario", "Documentos do Proprietário"),
]

_LINES_POR_PAGINA_SUM = 26
_W, _H = A4
_M = 2.2 * cm


def _img_para_pdf(raw: bytes) -> bytes:
    """Converte uma IMAGEM (JPG/PNG/...) numa página A4 de PDF (centralizada)."""
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as rl_canvas
    im = Image.open(io.BytesIO(raw))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    iw, ih = im.size
    margem = 1.5 * cm
    maxw, maxh = _W - 2 * margem, _H - 2 * margem
    esc = min(maxw / iw, maxh / ih)
    w, h = iw * esc, ih * esc
    c.drawImage(ImageReader(im), (_W - w) / 2, (_H - h) / 2, width=w, height=h)
    c.showPage()
    c.save()
    return buf.getvalue()


def _to_pdf_bytes(item) -> list:
    """Normaliza bytes / lista de bytes em lista de PDFs legíveis (imagem→PDF; ignora inválidos)."""
    out = []
    for raw in (item if isinstance(item, (list, tuple)) else [item]):
        if not raw:
            continue
        if raw[:5] != b"%PDF-":            # JPG/PNG (ex.: comprovantes) → vira página PDF
            try:
                raw = _img_para_pdf(raw)
            except Exception:  # noqa: BLE001
                continue
        try:
            r = PdfReader(io.BytesIO(raw))
            if len(r.pages):
                out.append(r)
        except Exception:  # noqa: BLE001
            continue
    return out


def _capa_bytes(projeto: dict) -> bytes:
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    f = T.fonts()
    verde, dourado = T.C_VERDE_ESCURO, T.C_DOURADO
    # marca
    try:
        from pdf.brand_seal import draw_cover_lockup
        draw_cover_lockup(c, _W / 2, _H - 2.4 * cm)
    except Exception:  # noqa: BLE001
        pass
    c.setStrokeColor(dourado)
    c.setLineWidth(1.2)
    c.line(_M, _H - 4.2 * cm, _W - _M, _H - 4.2 * cm)

    c.setFillColor(verde)
    c.setFont(f["serif_bold"], 22)
    c.drawCentredString(_W / 2, _H - 6.0 * cm, "DOSSIÊ — REMEMBRAMENTO")
    c.setFont(f["serif"], 13)
    titulo = projeto.get("denominacao_imovel") or ""
    c.drawCentredString(_W / 2, _H - 7.1 * cm, titulo[:70])

    y = _H - 9.2 * cm
    linhas = [
        ("Município/UF", f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}"),
        ("Quadra / Lote resultante", f"{projeto.get('quadra') or ''} / {projeto.get('lote_resultante') or ''}"),
        ("Lotes de origem", projeto.get("cadastro_antigo") or ""),
        ("CMI resultante", TX.cim_completo(projeto) or ""),
        ("Área", TX.m2(projeto.get("area_declarada_m2"))),
        ("Perímetro", TX.metros(projeto.get("perimetro_m"))),
        ("Nº da TRT", projeto.get("trt_numero") or "—"),
        ("Requerente", _requerente_nome(projeto)),
    ]
    rt = projeto.get("responsavel_tecnico") or {}
    linhas.append(("Responsável Técnico", f"{rt.get('nome') or ''} — {rt.get('conselho') or ''}"))
    for k, v in linhas:
        c.setFillColor(verde)
        c.setFont(f["sans_bold"], 10)
        c.drawString(_M, y, f"{k}:")
        c.setFillColor(black)
        c.setFont(f["sans"], 10)
        c.drawString(_M + 5.2 * cm, y, str(v)[:60])
        y -= 0.72 * cm

    # destinatários
    y -= 0.4 * cm
    cart = projeto.get("cartorio") or {}
    sup = projeto.get("superintendencia") or {}
    c.setFillColor(dourado)
    c.setFont(f["sans_bold"], 9)
    c.drawString(_M, y, "DESTINATÁRIOS")
    y -= 0.55 * cm
    c.setFillColor(black)
    c.setFont(f["sans"], 9)
    for ln in [cart.get("nome") or "", sup.get("nome") or ""]:
        c.drawString(_M, y, ln[:90])
        y -= 0.5 * cm

    c.setFont(f["sans"], 8)
    c.setFillColor(HexColor("#777777"))
    d = datetime.now(timezone.utc)
    c.drawCentredString(_W / 2, 1.6 * cm, f"Emitido em {d.day:02d}/{d.month:02d}/{d.year} · AvalieImob — Topografia & Geo")
    c.showPage()
    c.save()
    return buf.getvalue()


def _requerente_nome(projeto: dict) -> str:
    for p in projeto.get("partes") or []:
        if p.get("papel") == "requerente":
            return p.get("razao_social") or p.get("nome") or ""
    for p in projeto.get("partes") or []:
        return p.get("razao_social") or p.get("nome") or ""
    return ""


def _sumario_bytes(itens, n_paginas_sumario):
    """itens = [(titulo, pagina_inicial), ...]. Retorna (bytes, links) — links =
    [{sum_page, rect, target}] (retângulos CLICÁVEIS que apontam a cada seção)."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    f = T.fonts()
    verde, dourado = T.C_VERDE_ESCURO, T.C_DOURADO
    por_pag = _LINES_POR_PAGINA_SUM
    paginas = [itens[i:i + por_pag] for i in range(0, len(itens), por_pag)] or [[]]
    links, gi = [], 0
    for sp, chunk in enumerate(paginas):
        c.setFillColor(verde)
        c.setFont(f["serif_bold"], 18)
        c.drawString(_M, _H - 2.6 * cm, "SUMÁRIO")
        c.setStrokeColor(dourado)
        c.setLineWidth(1.0)
        c.line(_M, _H - 2.9 * cm, _W - _M, _H - 2.9 * cm)
        y = _H - 4.0 * cm
        for (titulo, pag) in chunk:
            c.setFillColor(black)
            c.setFont(f["sans"], 10)
            c.drawString(_M, y, f"{gi + 1:02d}.  " + titulo[:70])
            c.setFont(f["sans_bold"], 10)
            c.setFillColor(verde)
            c.drawRightString(_W - _M, y, f"p. {pag}")
            c.setStrokeColor(HexColor("#DDDDDD"))
            c.setLineWidth(0.3)
            c.line(_M, y - 0.18 * cm, _W - _M, y - 0.18 * cm)
            links.append({"sum_page": sp, "rect": (_M, y - 0.20 * cm, _W - _M, y + 0.34 * cm),
                          "target": pag - 1})
            gi += 1
            y -= 0.78 * cm
        c.showPage()
    c.save()
    return buf.getvalue(), links


def gerar_dossie_ordenado(projeto: dict, secoes_in, capa_pdf: bytes = None) -> bytes:
    """`secoes_in` = [(titulo, bytes|[bytes,...]), ...] JÁ na ordem desejada.
    Monta capa → sumário (com paginação + bookmarks clicáveis) → seções na ordem dada."""
    secoes = []  # (titulo, [PdfReader,...], n_paginas)
    for titulo, item in secoes_in:
        leitores = _to_pdf_bytes(item)
        if leitores:
            secoes.append((titulo, leitores, sum(len(r.pages) for r in leitores)))

    n_sum = max(1, math.ceil(len(secoes) / _LINES_POR_PAGINA_SUM))
    itens, cursor = [], 1 + n_sum + 1     # capa(1) + sumário(n_sum) → 1ª seção
    for (titulo, _l, n) in secoes:
        itens.append((titulo, cursor))
        cursor += n

    capa = PdfReader(io.BytesIO(capa_pdf or _capa_bytes(projeto)))
    sum_bytes, links = _sumario_bytes(itens, n_sum)
    sumario = PdfReader(io.BytesIO(sum_bytes))

    w = PdfWriter()
    for pg in capa.pages:
        w.add_page(pg)
    n_capa = len(capa.pages)
    for pg in sumario.pages:
        w.add_page(pg)
    # bookmarks (TOC clicável no leitor de PDF)
    try:
        w.add_outline_item("Capa", 0)
        w.add_outline_item("Sumário", n_capa)
    except Exception:  # noqa: BLE001
        pass
    idx = n_capa + len(sumario.pages)
    inicios = []
    for (titulo, leitores, n) in secoes:
        inicios.append((titulo, idx))
        for r in leitores:
            for pg in r.pages:
                w.add_page(pg)
        idx += n
    for (titulo, pidx) in inicios:
        try:
            w.add_outline_item(titulo, pidx)
        except Exception:  # noqa: BLE001
            pass
    # LINKS clicáveis no texto do sumário → cada linha aponta à 1ª página da seção.
    # add_annotation/Link(target_page_index) gera [int /Fit] que muitos visualizadores
    # ignoram; inserimos /Dest com a REFERÊNCIA da página direto no /Annots (igual Georref).
    try:
        from pypdf.generic import (DictionaryObject, NameObject, ArrayObject,
                                   FloatObject, NumberObject)
        total = len(w.pages)
        for lk in links:
            tgt = lk["target"]
            if tgt < 0 or tgt >= total:
                continue
            sum_pg = w.pages[n_capa + lk["sum_page"]]
            page_ref = w.pages[tgt].indirect_reference
            annot = DictionaryObject({
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Link"),
                NameObject("/Rect"): ArrayObject([FloatObject(v) for v in lk["rect"]]),
                NameObject("/Border"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)]),
                NameObject("/Dest"): ArrayObject([page_ref, NameObject("/Fit")]),
            })
            ref = w._add_object(annot)
            if "/Annots" in sum_pg:
                sum_pg[NameObject("/Annots")].append(ref)
            else:
                sum_pg[NameObject("/Annots")] = ArrayObject([ref])
    except Exception:  # noqa: BLE001
        pass
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def gerar_dossie(projeto: dict, partes: dict, capa_pdf: bytes = None) -> bytes:
    """Compat: monta na ORDEM_DOSSIE padrão a partir do dict `partes`."""
    secoes_in = [(titulo, partes.get(key)) for key, titulo in ORDEM_DOSSIE]
    return gerar_dossie_ordenado(projeto, secoes_in, capa_pdf)
