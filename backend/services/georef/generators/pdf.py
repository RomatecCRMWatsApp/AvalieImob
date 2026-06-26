# @module services.georef.generators.pdf — Renderer PDF dos documentos (3 temas).
#
# Engine único parametrizado por tema (tradicional / prime_i / prime_ii), reusando
# os tokens de cor/fonte do PRIME II (pdf.themes.prime2_theme) e o template
# resiliente (pula flowables grandes em vez de quebrar o PDF).
import io
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak,
)

from pdf.themes import prime2_theme as T
from pdf.templates.resilient import ResilientSimpleDocTemplate
from services.georef.generators import textos as TX

logger = logging.getLogger("romatec")

MARGIN = 2.2 * cm
CINZA_TAB = HexColor("#EFEDE7")
CINZA_BORDA = HexColor("#CFCabc".upper()) if False else HexColor("#D8D4CB")


# ──────────────────────────────────────────────────────────────────────────────
# Tema
# ──────────────────────────────────────────────────────────────────────────────
def _normalizar_tema(tema):
    t = (tema or "prime_i").lower().strip()
    return {"prime1": "prime_i", "prime2": "prime_ii", "prime": "prime_i"}.get(t, t)


def _cfg(tema):
    f = T.fonts()
    tema = _normalizar_tema(tema)
    base = {
        "tema": tema,
        "serif": f["serif"], "serif_bold": f["serif_bold"], "serif_italic": f["serif_italic"],
        "sans": f["sans"], "sans_bold": f["sans_bold"],
    }
    if tema == "tradicional":               # SÓBRIO: branco, título preto, filete cinza
        return {**base,
                "primary": black, "accent": HexColor("#333333"),
                "titulo_bg": None, "titulo_fg": black, "titulo_doble": False,
                "sec_band": False, "tab_head_bg": CINZA_TAB, "tab_head_fg": black}
    if tema == "prime_ii":                  # BOLD/EDITORIAL: caixa verde + faixas de seção
        return {**base,
                "primary": T.C_VERDE_ESCURO, "accent": T.C_DOURADO,
                "titulo_bg": T.C_VERDE_ESCURO, "titulo_fg": T.C_BRANCO, "titulo_doble": False,
                "sec_band": True, "tab_head_bg": T.C_VERDE_ESCURO, "tab_head_fg": T.C_BRANCO}
    # prime_i (default) — ELEGANTE/CLARO: título verde + filete DOURADO DUPLO, sem caixa/faixa
    return {**base,
            "primary": T.C_VERDE_ESCURO, "accent": T.C_DOURADO,
            "titulo_bg": None, "titulo_fg": T.C_VERDE_ESCURO, "titulo_doble": True,
            "sec_band": False, "tab_head_bg": T.C_DOURADO, "tab_head_fg": T.C_VERDE_ESCURO}


def _styles(cfg):
    return {
        "titulo": ParagraphStyle("g_tit", fontName=cfg["serif_bold"], fontSize=16, leading=20,
                                 textColor=cfg["titulo_fg"], alignment=TA_CENTER),
        "sec": ParagraphStyle("g_sec", fontName=cfg["serif_bold"], fontSize=12, leading=15,
                              textColor=(cfg["titulo_fg"] if cfg["sec_band"] else cfg["primary"])),
        "corpo": ParagraphStyle("g_corpo", fontName=cfg["sans"], fontSize=10, leading=15,
                                textColor=black, alignment=TA_JUSTIFY),
        "corpo_c": ParagraphStyle("g_corpo_c", fontName=cfg["sans"], fontSize=10, leading=15,
                                  textColor=black, alignment=TA_CENTER),
        "kv": ParagraphStyle("g_kv", fontName=cfg["sans"], fontSize=9, leading=13, textColor=black),
        "kv_b": ParagraphStyle("g_kvb", fontName=cfg["sans_bold"], fontSize=9, leading=13,
                               textColor=cfg["primary"]),
        "tab": ParagraphStyle("g_tab", fontName=cfg["sans"], fontSize=7.5, leading=10, textColor=black),
        "tab_h": ParagraphStyle("g_tabh", fontName=cfg["sans_bold"], fontSize=7.5, leading=10,
                                textColor=cfg["tab_head_fg"], alignment=TA_CENTER),
        "assina": ParagraphStyle("g_assina", fontName=cfg["sans"], fontSize=9, leading=12,
                                 textColor=black, alignment=TA_CENTER),
        "small": ParagraphStyle("g_small", fontName=cfg["sans"], fontSize=8, leading=11,
                               textColor=HexColor("#555555")),
    }


def _esc(s):
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _paras(texto, style):
    """Texto multi-parágrafo (linha em branco separa; \\n vira <br/>)."""
    out = []
    for bloco in str(texto or "").split("\n\n"):
        bloco = bloco.strip()
        if not bloco:
            continue
        out.append(Paragraph(_esc(bloco).replace("\n", "<br/>"), style))
        out.append(Spacer(1, 6))
    return out


def _paras_bold(texto, termos, style):
    """Como _paras, mas com `termos` em NEGRITO (escapa tudo; injeta <b> só nos termos)."""
    termos = [t.strip() for t in (termos or []) if t and t.strip() and t.strip() != "—"]
    out = []
    for bloco in str(texto or "").split("\n\n"):
        bloco = bloco.strip()
        if not bloco:
            continue
        safe = _esc(bloco)
        for t in termos:
            safe = safe.replace(_esc(t), f"<b>{_esc(t)}</b>")
        out.append(Paragraph(safe.replace("\n", "<br/>"), style))
        out.append(Spacer(1, 6))
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Componentes
# ──────────────────────────────────────────────────────────────────────────────
def _titulo(titulo, cfg, st, largura):
    p = Paragraph(_esc(titulo), st["titulo"])
    if cfg["titulo_bg"] is None:
        out = [p, Spacer(1, 4),
               Table([[""]], colWidths=[largura],
                     style=[("LINEBELOW", (0, 0), (-1, -1), 1.4, cfg["accent"])])]
        if cfg.get("titulo_doble"):        # prime_i: 2º filete fino (dourado duplo)
            out += [Spacer(1, 2),
                    Table([[""]], colWidths=[largura],
                          style=[("LINEBELOW", (0, 0), (-1, -1), 0.6, cfg["accent"])])]
        out.append(Spacer(1, 12))
        return out
    t = Table([[p]], colWidths=[largura])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cfg["titulo_bg"]),
        ("BOX", (0, 0), (-1, -1), 1, cfg["accent"]),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return [t, Spacer(1, 14)]


def _secao(texto, cfg, st, largura):
    p = Paragraph(_esc(texto), st["sec"])
    if cfg["sec_band"]:
        t = Table([[p]], colWidths=[largura])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), cfg["primary"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return [Spacer(1, 8), t, Spacer(1, 8)]
    # prime_i / tradicional: título + filete dourado/cinza
    rule = Table([[""]], colWidths=[largura],
                 style=[("LINEBELOW", (0, 0), (-1, -1), 0.8, cfg["accent"])])
    return [Spacer(1, 10), p, Spacer(1, 2), rule, Spacer(1, 6)]


def _kv_table(pares, cfg, st, largura):
    rows = [[Paragraph(_esc(k), st["kv_b"]), Paragraph(_esc(v), st["kv"])] for k, v in pares]
    t = Table(rows, colWidths=[largura * 0.32, largura * 0.68])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, CINZA_BORDA),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _data_table(header, rows, cfg, st, largura):
    cols = len(header)
    head = [Paragraph(_esc(h), st["tab_h"]) for h in header]
    body = [[Paragraph(_esc(c), st["tab"]) for c in r] for r in rows]
    t = Table([head] + body, colWidths=[largura / cols] * cols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), cfg["tab_head_bg"]),
        ("GRID", (0, 0), (-1, -1), 0.4, CINZA_BORDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, CINZA_TAB]),
    ]))
    return t


def _bloco_assinaturas(assinaturas, st, largura):
    """Linhas de assinatura (nome + papel), empilhadas com espaço para firma."""
    elems = [Spacer(1, 24)]
    for nome, papel in assinaturas:
        linha = Table([[""]], colWidths=[largura * 0.6],
                      style=[("LINEABOVE", (0, 0), (-1, -1), 0.8, black)])
        bloco = [Spacer(1, 30), linha,
                 Paragraph(f"<b>{_esc(nome)}</b>", st["assina"]),
                 Paragraph(_esc(papel), st["assina"]), Spacer(1, 14)]
        elems.append(KeepTogether(bloco))
    return elems


# ──────────────────────────────────────────────────────────────────────────────
# Header/Footer (onPage)
# ──────────────────────────────────────────────────────────────────────────────
def _make_onpage(cfg, titulo_curto, logo_bytes=None):
    def _draw(canvas, doc):
        canvas.saveState()
        w, h = A4
        # topo: marca + rule (logo PRÓPRIO do usuário tem prioridade — white-label)
        try:
            from pdf.brand_seal import draw_header_lockup
            if logo_bytes:
                draw_header_lockup(canvas, MARGIN, h - 1.15 * cm, mark=9 * mm,
                                   light=False, logo_bytes=logo_bytes)
            elif cfg["tema"] != "tradicional":
                draw_header_lockup(canvas, MARGIN, h - 1.15 * cm, mark=9 * mm, light=False,
                                   tagline="Topografia & Geo · INCRA/SIGEF")
            else:
                canvas.setFont(cfg["serif_bold"], 11)
                canvas.setFillColor(black)
                canvas.drawString(MARGIN, h - 1.2 * cm, "ROMATEC CONSULTORIA TOTAL")
        except Exception:  # noqa: BLE001
            pass
        # filete ABAIXO de todo o lockup (não cruza o nome/tagline)
        canvas.setStrokeColor(cfg["accent"])
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, h - 1.85 * cm, w - MARGIN, h - 1.85 * cm)
        # rodapé: título curto à esquerda + página à direita
        canvas.setFont(cfg["sans"] if "sans" in cfg else "Helvetica", 7.5)
        canvas.setFillColor(HexColor("#777777"))
        canvas.drawString(MARGIN, 1.1 * cm, titulo_curto[:90])
        canvas.drawRightString(w - MARGIN, 1.1 * cm, f"Página {doc.page}")
        canvas.setStrokeColor(HexColor("#CCCCCC"))
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, 1.35 * cm, w - MARGIN, 1.35 * cm)
        canvas.restoreState()
    return _draw


def _build(elements, cfg, titulo_curto, logo_bytes=None):
    T.registrar_fontes()
    buf = io.BytesIO()
    doc = ResilientSimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.25 * cm, bottomMargin=1.8 * cm, title=titulo_curto,
    )
    onpage = _make_onpage(cfg, titulo_curto, logo_bytes)
    doc.build(elements, onFirstPage=onpage, onLaterPages=onpage)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Documentos
# ──────────────────────────────────────────────────────────────────────────────
def _largura():
    return A4[0] - 2 * MARGIN


def pdf_requerimento(projeto, tema="prime_i") -> bytes:
    cfg, st, lar = _cfg(tema), None, _largura()
    st = _styles(cfg)
    d = TX.render_requerimento(projeto)
    e = []
    e += _titulo(d["titulo"], cfg, st, lar)
    e += _paras(d["destinatario"], st["corpo"])
    e.append(Spacer(1, 8))
    e += _paras_bold(d["corpo"], d.get("corpo_negrito"), st["corpo"])
    for doc_item in d["documentos"]:
        e.append(Paragraph(_esc(doc_item), st["corpo"]))
        e.append(Spacer(1, 2))
    # DA CERTIFICAÇÃO E CADASTRO (identificadores cadastrais do imóvel)
    if d.get("certificacao_bloco"):
        e += _secao("DA CERTIFICAÇÃO E CADASTRO", cfg, st, lar)
        for ln in d["certificacao_bloco"]:
            e.append(Paragraph("• " + _esc(ln), st["corpo"]))
            e.append(Spacer(1, 2))
    # PARCELAS RESULTANTES — tabela com Código SIGEF (cai p/ lista quando sem tabela)
    if d.get("parcelas_tabela"):
        e += _secao("PARCELAS RESULTANTES", cfg, st, lar)
        e.append(_data_table(d["parcelas_header"], d["parcelas_tabela"], cfg, st, lar))
    elif d.get("parcelas"):
        e += _secao("PARCELAS RESULTANTES", cfg, st, lar)
        for linha in d["parcelas"]:
            e.append(Paragraph("• " + _esc(linha), st["corpo"]))
            e.append(Spacer(1, 2))
    # Encerramento INDIVISÍVEL: fecho + RT + data + assinatura (nunca assinatura órfã)
    fim = []
    fim += _paras(d["fecho"], st["corpo"])
    fim.append(Spacer(1, 6))
    fim.append(Paragraph(_esc(d["rt_linha"]), st["small"]))
    fim.append(Spacer(1, 10))
    fim.append(Paragraph("Nestes termos, pede deferimento.", st["corpo"]))
    fim.append(Spacer(1, 10))
    fim.append(Paragraph(_esc(d["data"]) + ".", st["corpo_c"]))
    fim += _bloco_assinaturas([(d["assinatura"][0], d["assinatura"][1])], st, lar)
    e.append(KeepTogether(fim))
    return _build(e, cfg, d["titulo"], projeto.get("_brand_logo_bytes"))


def pdf_memorial(projeto, tema="prime_i") -> bytes:
    cfg = _cfg(tema)
    st, lar = _styles(cfg), _largura()
    d = TX.render_memorial(projeto)
    e = []
    e += _titulo(d["titulo"], cfg, st, lar)
    e += _secao("IDENTIFICAÇÃO", cfg, st, lar)
    e.append(_kv_table(d["cabecalho"], cfg, st, lar))
    e += _secao("DESCRIÇÃO DA PARCELA (VÉRTICES)", cfg, st, lar)
    e.append(_data_table(d["tabela_header"], d["tabela"], cfg, st, lar))
    e.append(Spacer(1, 16))
    e.append(Paragraph(_esc(d["data"]) + ".", st["corpo_c"]))
    e += _bloco_assinaturas([(d["rt_assinatura"][0], " — ".join(d["rt_assinatura"][1:]))], st, lar)
    return _build(e, cfg, d["titulo"], projeto.get("_brand_logo_bytes"))


def pdf_drl(projeto, conf, tema="prime_i") -> bytes:
    cfg = _cfg(tema)
    st, lar = _styles(cfg), _largura()
    d = TX.render_drl(projeto, conf)
    e = []
    e += _titulo(d["titulo"], cfg, st, lar)
    for linha in d["cabecalho"]:
        e.append(Paragraph(_esc(linha), st["kv"]))
        e.append(Spacer(1, 2))
    e.append(Spacer(1, 8))
    e += _paras(d["corpo"], st["corpo"])
    e += _secao("SEGMENTOS DIVISÓRIOS (SIRGAS 2000)", cfg, st, lar)
    if d["tabela"]:
        e.append(_data_table(d["tabela_header"], d["tabela"], cfg, st, lar))
    else:
        e.append(Paragraph("Sem segmentos vinculados a este confrontante.", st["small"]))
    e.append(Spacer(1, 14))
    e.append(Paragraph(_esc(d["data"]) + ".", st["corpo_c"]))
    e += _bloco_assinaturas(d["assinaturas"], st, lar)
    return _build(e, cfg, d["titulo"], projeto.get("_brand_logo_bytes"))


def pdf_laudo(projeto, tema="prime_i") -> bytes:
    cfg = _cfg(tema)
    st, lar = _styles(cfg), _largura()
    d = TX.render_laudo_tecnico(projeto)
    e = []
    e += _titulo(d["titulo"], cfg, st, lar)
    e += _secao("1. IDENTIFICAÇÃO", cfg, st, lar)
    e += _paras_bold(d["identificacao"], d.get("identificacao_negrito"), st["corpo"])
    e += _secao("2. OBJETO", cfg, st, lar)
    e += _paras(d["objeto"], st["corpo"])
    if d.get("teor_matricula"):
        e += _secao("DO TEOR DA MATRÍCULA", cfg, st, lar)
        e += _paras_bold(d["teor_matricula"], d.get("identificacao_negrito"), st["corpo"])
    e += _secao("3. JUSTIFICATIVA TÉCNICO-JURÍDICA", cfg, st, lar)
    e += _paras(d["justificativa"], st["corpo"])
    e += _secao("4. METODOLOGIA E PARÂMETROS TÉCNICOS DE AGRIMENSURA", cfg, st, lar)
    e += _paras(d["metodologia"], st["corpo"])
    e += _secao("5. RESULTADO — POLIGONAL", cfg, st, lar)
    e.append(_data_table(d["resultado_header"], d["resultado_tabela"], cfg, st, lar))
    if d.get("parcelas_tabela"):
        e += _secao("PARCELAS RESULTANTES", cfg, st, lar)
        e.append(_data_table(d["parcelas_header"], d["parcelas_tabela"], cfg, st, lar))
        if d.get("observacao_areas"):
            e.append(Spacer(1, 4))
            e.append(Paragraph(_esc(d["observacao_areas"]), st["small"]))
    e += _secao("6. CADEIA DOMINIAL", cfg, st, lar)
    if d["cadeia_tabela"]:
        e.append(_data_table(d["cadeia_header"], d["cadeia_tabela"], cfg, st, lar))
    else:
        e.append(Paragraph(_esc(d["cadeia_nota"]), st["corpo"]))
    e += _secao("7. CONFRONTAÇÕES", cfg, st, lar)
    e.append(_data_table(d["confrontacoes_header"], d["confrontacoes_tabela"], cfg, st, lar))
    e += _secao("8. CONCLUSÃO", cfg, st, lar)
    e += _paras(d["conclusao"], st["corpo"])
    e.append(Spacer(1, 14))
    e.append(Paragraph(_esc(d["data"]) + ".", st["corpo_c"]))
    e += _bloco_assinaturas([(d["rt_assinatura"][0], " — ".join(d["rt_assinatura"][1:]))], st, lar)
    return _build(e, cfg, d["titulo"], projeto.get("_brand_logo_bytes"))


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────────────────────
def gerar_pdf(tipo, projeto, tema="prime_i", conf=None) -> bytes:
    tema = projeto.get("tema_pdf") if tema is None else tema
    tema = tema or "prime_i"
    if tipo == "requerimento":
        return pdf_requerimento(projeto, tema)
    if tipo == "memorial":
        return pdf_memorial(projeto, tema)
    if tipo == "laudo_tecnico":
        return pdf_laudo(projeto, tema)
    if tipo == "drl":
        if conf is None:
            raise ValueError("DRL requer o confrontante (conf).")
        return pdf_drl(projeto, conf, tema)
    raise ValueError(f"Tipo de documento desconhecido: {tipo}")
