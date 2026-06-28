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


def _to_pdf_bytes(item) -> list:
    """Normaliza bytes / lista de bytes em lista de PDFs legíveis (ignora inválidos)."""
    out = []
    for raw in (item if isinstance(item, (list, tuple)) else [item]):
        if not raw:
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
        ("CMI resultante", projeto.get("cmi_resultante") or ""),
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


def _sumario_bytes(itens, n_paginas_sumario) -> bytes:
    """itens = [(titulo, pagina_inicial), ...] (página já no espaço final)."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    f = T.fonts()
    verde, dourado = T.C_VERDE_ESCURO, T.C_DOURADO
    por_pag = _LINES_POR_PAGINA_SUM
    paginas = [itens[i:i + por_pag] for i in range(0, len(itens), por_pag)] or [[]]
    for chunk in paginas:
        c.setFillColor(verde)
        c.setFont(f["serif_bold"], 18)
        c.drawString(_M, _H - 2.6 * cm, "SUMÁRIO")
        c.setStrokeColor(dourado)
        c.setLineWidth(1.0)
        c.line(_M, _H - 2.9 * cm, _W - _M, _H - 2.9 * cm)
        y = _H - 4.0 * cm
        for i, (titulo, pag) in enumerate(chunk):
            c.setFillColor(black)
            c.setFont(f["sans"], 10)
            num = f"{itens.index((titulo, pag)) + 1:02d}.  "
            c.drawString(_M, y, num + titulo[:70])
            c.setFont(f["sans_bold"], 10)
            c.setFillColor(verde)
            c.drawRightString(_W - _M, y, f"p. {pag}")
            c.setStrokeColor(HexColor("#DDDDDD"))
            c.setLineWidth(0.3)
            c.line(_M, y - 0.18 * cm, _W - _M, y - 0.18 * cm)
            y -= 0.78 * cm
        c.showPage()
    c.save()
    return buf.getvalue()


def gerar_dossie(projeto: dict, partes: dict, capa_pdf: bytes = None) -> bytes:
    """partes = {key: bytes | [bytes,...]}. Monta capa+sumário+seções na ordem §9.
    `capa_pdf` (opcional) = Capa "Lupa Geo" pronta; senão usa a capa textual padrão."""
    # 1) coleta seções presentes (na ordem) + contagem de páginas
    secoes = []  # (titulo, [PdfReader,...], n_paginas)
    for key, titulo in ORDEM_DOSSIE:
        leitores = _to_pdf_bytes(partes.get(key))
        if leitores:
            n = sum(len(r.pages) for r in leitores)
            secoes.append((titulo, leitores, n))

    # 2) páginas do sumário (capa=1 + S) → início real de cada seção
    n_sum = max(1, math.ceil(len(secoes) / _LINES_POR_PAGINA_SUM))
    offset = 1 + n_sum
    itens, cursor = [], offset + 1
    for (titulo, leitores, n) in secoes:
        itens.append((titulo, cursor))
        cursor += n

    capa = PdfReader(io.BytesIO(capa_pdf or _capa_bytes(projeto)))
    sumario = PdfReader(io.BytesIO(_sumario_bytes(itens, n_sum)))

    # 3) monta o writer final
    w = PdfWriter()
    for pg in capa.pages:
        w.add_page(pg)
    for pg in sumario.pages:
        w.add_page(pg)
    for (titulo, leitores, n) in secoes:
        for r in leitores:
            for pg in r.pages:
                w.add_page(pg)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()
