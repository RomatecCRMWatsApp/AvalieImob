# @module services.geo_urbano.generators.pdf — renderer PDF do Geo Urbano (3 temas).
#
# REUSA os blocos genéricos do renderer do Georreferenciamento (tema/estilos/
# título/seção/tabelas/assinaturas) — "não duplicar infra" — e acrescenta o
# conteúdo URBANO: Requerimento (2 vias), Memorial Descritivo e Cadeia Dominical.
from __future__ import annotations

import base64
import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Image as RLImage, Table, TableStyle

from pdf.templates.resilient import ResilientSimpleDocTemplate
from services.georef.generators import pdf as GP   # blocos genéricos reusados
from services.geo_urbano.generators import textos as TX
from services.geo_urbano.generators import croqui as CROQUI
from services.geo_urbano import usucapiao as USU

MARGIN = GP.MARGIN
_MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _data_extenso(municipio: str, uf: str) -> str:
    d = datetime.now(timezone.utc)
    return f"{municipio}/{uf}, {d.day} de {_MESES[d.month]} de {d.year}."


def _make_onpage(cfg, titulo_curto, logo_bytes=None):
    def _draw(canvas, doc):
        canvas.saveState()
        w, h = A4
        try:
            from pdf.brand_seal import draw_header_lockup
            if logo_bytes:
                draw_header_lockup(canvas, MARGIN, h - 1.15 * cm, mark=9 * mm,
                                   light=False, logo_bytes=logo_bytes)
            elif cfg["tema"] != "tradicional":
                draw_header_lockup(canvas, MARGIN, h - 1.15 * cm, mark=9 * mm, light=False,
                                   tagline="Topografia & Geo · Geo Urbano")
            else:
                canvas.setFont(cfg["serif_bold"], 11)
                canvas.setFillColor(black)
                canvas.drawString(MARGIN, h - 1.2 * cm, "ROMATEC CONSULTORIA TOTAL")
        except Exception:  # noqa: BLE001
            pass
        canvas.setStrokeColor(cfg["accent"])
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, h - 1.85 * cm, w - MARGIN, h - 1.85 * cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(HexColor("#777777"))
        canvas.drawString(MARGIN, 1.1 * cm, (titulo_curto or "")[:90])
        canvas.drawRightString(w - MARGIN, 1.1 * cm, f"Página {doc.page}")
        canvas.setStrokeColor(HexColor("#CCCCCC"))
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, 1.35 * cm, w - MARGIN, 1.35 * cm)
        canvas.restoreState()
    return _draw


def _build(story, cfg, titulo_curto, logo_bytes=None) -> bytes:
    buf = io.BytesIO()
    doc = ResilientSimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.25 * cm, bottomMargin=1.8 * cm,
    )
    onpage = _make_onpage(cfg, titulo_curto, logo_bytes)
    doc.build(story, onFirstPage=onpage, onLaterPages=onpage)
    return buf.getvalue()


def _largura() -> float:
    return A4[0] - 2 * MARGIN


def _secao_croqui(projeto: dict, cfg, st, L):
    """Seção CROQUI DA POLIGONAL (desenho vetorial) — Requerimento e Memorial.
    O título fica SEMPRE junto do desenho (KeepTogether), nunca órfão no rodapé."""
    dwg = CROQUI.croqui_drawing(projeto)
    if dwg is None:
        return []
    from reportlab.platypus import KeepTogether
    bloco = GP._secao("CROQUI DA POLIGONAL", cfg, st, L) + [
        dwg, Spacer(1, 6),
        Paragraph("Croqui ilustrativo da poligonal resultante (vértices, medidas e confrontantes). "
                  "Vide planilha de coordenadas e o mapa anexo.", st.get("small") or st["corpo"])]
    return [KeepTogether(bloco)]


def _bloco_assinaturas_partes(projeto: dict, st, L):
    """Bloco de assinaturas do requerente. PJ → razão social + CNPJ e, abaixo, o
    representante/sócio que anui (assina pela empresa); PF → nome + papel."""
    from reportlab.platypus import KeepTogether
    partes = projeto.get("partes") or []
    requerente = next((p for p in partes if p.get("papel") == "requerente"), None)
    elems = [Spacer(1, 24)]

    def _add(linhas):
        b = [Spacer(1, 42),  # espaço amplo p/ a firma manuscrita
             Table([[""]], colWidths=[L * 0.6], style=[("LINEABOVE", (0, 0), (-1, -1), 0.8, black)])]
        for txt, bold in linhas:
            b.append(Paragraph(f"<b>{GP._esc(txt)}</b>" if bold else GP._esc(txt), st["assina"]))
        b.append(Spacer(1, 14))
        elems.append(KeepTogether(b))

    if requerente and requerente.get("tipo_pessoa") == "juridica":
        rep = next((p for p in partes if p.get("papel") in ("representante", "socio")), None)
        razao = requerente.get("razao_social") or requerente.get("nome") or ""
        linhas = [(razao, True)]
        if requerente.get("cnpj"):
            linhas.append((f"CNPJ: {requerente['cnpj']}", False))
        if rep and rep.get("nome"):
            papel = "Representante legal" if rep.get("papel") == "representante" else "Sócio administrador"
            linhas.append((f"{rep['nome']} — {papel}", False))
            if rep.get("cpf"):
                linhas.append((f"CPF: {rep['cpf']}", False))
        _add(linhas)
        for p in partes:  # sócios anuentes adicionais
            if p.get("papel") == "socio" and p is not rep and p.get("nome"):
                _add([(p["nome"], True), ("Sócio anuente", False)])
        return elems

    for nome, papel in _partes_assinatura(projeto):
        _add([(nome, True), (papel, False)])
    return elems


def _short_vert(s):
    """FQNS-P-PDN1 → PDN1 (rótulo curto p/ a tabela não quebrar)."""
    return (s or "").split("-")[-1]


def _firma_image(raw, largura=150, max_h=70):
    """RLImage da firma gráfica (PNG), recortada ao conteúdo e escalada p/ a `largura`
    (pt) escolhida, com teto de altura. None em qualquer falha (degrada p/ linha vazia)."""
    try:
        from services.assinatura_cliente_carimbo import _trim_png
        from reportlab.lib.utils import ImageReader
        raw = _trim_png(raw)
        iw, ih = ImageReader(io.BytesIO(raw)).getSize()
        sc = largura / iw
        if ih * sc > max_h:          # respeita o teto de altura
            sc = max_h / ih
        img = RLImage(io.BytesIO(raw), width=iw * sc, height=ih * sc)
        img.hAlign = "LEFT"
        return img
    except Exception:  # noqa: BLE001
        return None


def _assina_rt_memorial(rt_nome, papel_rt, firma_bytes, st, L, pos=None):
    """Bloco de assinatura do RT com a firma GRÁFICA (PNG) carimbada acima da linha.
    `pos` = {largura, align, dx, dy} controla tamanho/alinhamento/deslocamento fino."""
    from reportlab.platypus import KeepTogether
    p = pos or {}
    largura = float(p.get("largura") or 150)
    align = (p.get("align") or "left").upper()
    dx = float(p.get("dx") or 0)
    dy = float(p.get("dy") or 0)
    bloco = [Spacer(1, 16)]                # folga fixa acima da firma
    firma = _firma_image(firma_bytes, largura=largura) if firma_bytes else None
    if firma:
        firma.hAlign = align if align in ("LEFT", "CENTER", "RIGHT") else "LEFT"
        if dx:   # dx: nudge horizontal via padding de uma tabela-wrapper
            lado = "RIGHTPADDING" if (align == "RIGHT") else "LEFTPADDING"
            wrap = Table([[firma]], style=[(lado, (0, 0), (-1, -1), abs(dx)),
                                           ("TOPPADDING", (0, 0), (-1, -1), 0),
                                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)])
            wrap.hAlign = firma.hAlign
            bloco.append(wrap)
        else:
            bloco.append(firma)
    else:
        bloco.append(Spacer(1, 30))
    bloco.append(Spacer(1, max(0, dy)))    # dy: folga ENTRE a firma e a linha (flutua acima)
    bloco += [
        Table([[""]], colWidths=[L * 0.6], style=[("LINEABOVE", (0, 0), (-1, -1), 0.8, black)]),
        Paragraph(f"<b>{GP._esc(rt_nome)}</b>", st["assina"]),
        Paragraph(GP._esc(papel_rt), st["assina"]), Spacer(1, 14)]
    return [KeepTogether(bloco)]


# Rótulo COMPACTO do lado p/ a coluna da tabela (uma linha); o texto pleno
# (LATERAL DIREITA/ESQUERDA) fica na descrição perimétrica e no quadro do wizard.
_LADO_ABREV = {"frente": "FRENTE", "lateral_direita": "LAT. DIR.",
               "lateral_esquerda": "LAT. ESQ.", "fundo": "FUNDOS", "fundos": "FUNDOS"}


def _tabela_vertices(projeto: dict, cfg, st, L):
    """Quadro de vértices/medidas/confrontações (do mapa) — usado no Memorial E no
    Requerimento. Larguras de coluna calibradas + rótulos curtos + fonte menor nas
    colunas numéricas para que as COORDENADAS não quebrem de linha."""
    verts = sorted(projeto.get("vertices") or [], key=lambda v: v.get("ordem", 0))
    if not verts:
        return []
    out = GP._secao("QUADRO DE VÉRTICES, MEDIDAS E CONFRONTAÇÕES", cfg, st, L)
    stn = ParagraphStyle("gu_tabn", parent=st["tab"], fontSize=6.6, leading=8.4)  # numéricas
    # Coluna Fator K só aparece se ALGUM vértice a tem (usucapião: o mapa é imagem, não
    # traz o Fator K — sem valor, a coluna é OCULTADA para não sair vazia).
    mostra_fk = any(v.get("fator_k") is not None for v in verts)
    # Lado (FRENTE/LATERAIS/FUNDO) calculado na hora — mesma lógica da descrição
    # perimétrica, então tabela e texto batem. "—" quando a frente é indefinida.
    try:
        from ..orientacao import classificar_lados
        lados = classificar_lados(verts, frente_idx=projeto.get("frente_idx")).get("lados") or []
    except Exception:  # noqa: BLE001
        lados = []
    header = ["De", "Para", "Coord. N (Y)", "Coord. E (X)", "Azimute", "Dist. (m)"]
    if mostra_fk:
        header.append("Fator K")
    header += ["Lado", "Confront."]
    head = [Paragraph(GP._esc(h), st["tab_h"]) for h in header]
    body = []
    for i, v in enumerate(verts):
        linha = [
            Paragraph(GP._esc(v.get("de") or ""), stn),     # código INCRA completo (fiel)
            Paragraph(GP._esc(v.get("para") or ""), stn),
            Paragraph(GP._esc(TX._n_br(v.get("coord_n"), 4)), stn),
            Paragraph(GP._esc(TX._n_br(v.get("coord_e"), 4)), stn),
            Paragraph(GP._esc(v.get("azimute") or ""), stn),
            Paragraph(GP._esc(TX._n_br(v.get("distancia_m"))), stn),
        ]
        if mostra_fk:
            linha.append(Paragraph(GP._esc(TX._n_br(v.get("fator_k"), 8) if v.get("fator_k") is not None else ""), stn))
        lado = lados[i] if i < len(lados) else None
        linha.append(Paragraph(GP._esc(_LADO_ABREV.get(lado, "—")), stn))
        linha.append(Paragraph(GP._esc(v.get("confrontante_lado") or "—"), st["tab"]))
        body.append(linha)
    # Fator K precisa de ~0.10 (o valor "1,00052614" não pode quebrar de linha);
    # o rótulo do Lado pode quebrar em 2 linhas (LATERAL / ESQUERDA), então recebe menos.
    fr = ([0.095, 0.095, 0.135, 0.135, 0.085, 0.05, 0.10, 0.105, 0.20] if mostra_fk  # soma 1.0
          else [0.115, 0.115, 0.15, 0.15, 0.10, 0.065, 0.10, 0.205])                 # sem Fator K
    t = Table([head] + body, colWidths=[L * f for f in fr], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), cfg["tab_head_bg"]),
        ("GRID", (0, 0), (-1, -1), 0.4, GP.CINZA_BORDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, GP.CINZA_TAB]),
    ]))
    out.append(t)
    return out


def _ficha_compacta(pares, cfg, st, L, cols=4):
    """Ficha de identificação COMPACTA (multi-coluna, fundo verde claro) — economiza
    espaço vs o kv vertical. Cada par = (label, value) ou (label, value, span). O par
    flui na grade de `cols` colunas; `span` permite um campo ocupar mais colunas."""
    val = ParagraphStyle("gu_fc", parent=st["kv"], fontSize=8.4, leading=11)

    def _cel(lb, vv):
        return Paragraph(f"<b>{GP._esc(lb)}:</b> {GP._esc('' if vv is None else str(vv))}", val)

    grid, spans, row, col = [], [], [], 0

    def _flush():
        nonlocal row, col
        while len(row) < cols:
            row.append("")
        grid.append(row)
        row, col = [], 0

    for p in pares:
        span = min(p[2] if len(p) > 2 else 1, cols)
        if col + span > cols:
            _flush()
        rowidx, c0 = len(grid), col
        row.append(_cel(p[0], p[1]))
        row.extend([""] * (span - 1))
        if span > 1:
            spans.append(("SPAN", (c0, rowidx), (c0 + span - 1, rowidx)))
        col += span
    if row:
        _flush()

    t = Table(grid, colWidths=[L / cols] * cols)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#EAF3EA")),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#C2D6C2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ] + spans))
    return t


def _partes_assinatura(projeto: dict):
    """Linhas de assinatura das partes (requerente PJ → representante; ou PF + cônjuge)."""
    _LABEL = {"requerente": "Requerente", "representante": "Representante legal",
              "socio": "Sócio", "conjuge": "Cônjuge anuente"}
    out = []
    for p in projeto.get("partes") or []:
        if p.get("papel") == "requerente" and p.get("tipo_pessoa") == "juridica":
            continue  # PJ assina via representante
        if p.get("papel") not in _LABEL:   # advogado/herdeiro/testemunha/titular: bloco próprio
            continue
        nome = p.get("nome") or p.get("razao_social") or ""
        if nome:
            out.append((nome, _LABEL[p.get("papel")]))
    if not out:
        out = [("", "Requerente")]
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Requerimento (2 vias — Cartório de RI / Superintendência)
# ──────────────────────────────────────────────────────────────────────────────
def requerimento(projeto: dict, via: str, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    story = []

    # bloco destinatário (varia por via)
    if via == "superintendencia":
        d = projeto.get("superintendencia") or {}
        dest = [f"À {d.get('nome') or 'Superintendência de Habitação e Regularização Fundiária'}",
                d.get("orgao") or "", f"A/C {d.get('responsavel') or ''}".strip(" A/C")]
        if d.get("portaria"):
            dest.append(f"Portaria {d['portaria']}")
        titulo_curto = "Requerimento de Remembramento — Superintendência"
    else:
        d = projeto.get("cartorio") or {}
        dest = [f"Ao Ilustríssimo Senhor Oficial do {d.get('nome') or 'Cartório de Registro de Imóveis'}",
                d.get("endereco") or ""]
        if d.get("titular"):
            dest.append(f"A/C {d['titular']}")
        titulo_curto = "Requerimento de Remembramento — Cartório de RI"

    for ln in [x for x in dest if x]:
        story.append(Paragraph(GP._esc(ln), st["corpo"]))
    story.append(Spacer(1, 16))
    tipo = projeto.get("tipo_servico") or "remembramento"
    story += GP._titulo(TX.TITULO_REQUERIMENTO.get(tipo, "REQUERIMENTO"), cfg, st, L)

    # qualificação dos requerentes + verbo (ação por tipo de serviço)
    n_mat = len(projeto.get("matriculas") or [])
    obj = "das seguintes matrículas" if n_mat != 1 else "da seguinte matrícula"
    intro = (TX.bloco_requerentes(projeto)
             + f"vem, respeitosamente, à presença de Vossa Senhoria, REQUERER "
             + f"{TX.ACAO_REQUERIMENTO.get(tipo, 'o ato requerido')}, objeto {obj}:")
    story += GP._paras(intro, st["corpo"])

    # transcrição FIEL, item por item
    for item in TX.lista_transcricoes(projeto):
        story += GP._paras(item, st["corpo"])

    # bloco resultante por tipo de serviço
    if tipo == "desdobro":
        story += GP._secao("DOS LOTES RESULTANTES", cfg, st, L)
        story += GP._paras(TX.descricao_lotes_resultantes(projeto), st["corpo"])
    elif tipo == "retificacao":
        story += GP._secao("DA RETIFICAÇÃO", cfg, st, L)
        story += GP._paras(TX.relacao_retificacao(projeto), st["corpo"])
        story += GP._paras("Fundamento legal: art. 213 da Lei nº 6.015/1973 e legislação municipal aplicável.",
                           st["small"])
    else:
        story += GP._secao("DO IMÓVEL RESULTANTE", cfg, st, L)
        story += GP._paras(TX.descricao_resultante(projeto), st["corpo"])
        # quadro de medidas e confrontações do mapa (mesmo do Memorial)
        story += _tabela_vertices(projeto, cfg, st, L)
        story += _secao_croqui(projeto, cfg, st, L)

    # cadastro / CMI (ficha compacta)
    pares = [p for p in [
        ("Cadastro novo", projeto.get("cadastro_novo"), 2),
        ("Cadastro antigo", projeto.get("cadastro_antigo"), 2),
        ("CMI resultante", TX.cim_completo(projeto), 2),
        ("Área total", TX.m2(projeto.get("area_declarada_m2"))),
        ("Perímetro", TX.metros(projeto.get("perimetro_m"))),
    ] if p[1]]
    if pares:
        story.append(Spacer(1, 6))
        story.append(_ficha_compacta(pares, cfg, st, L))

    # fecho
    story += GP._paras("Nestes termos,\nPede deferimento.", st["corpo"])
    story.append(Spacer(1, 4))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story += _bloco_assinaturas_partes(projeto, st, L)
    return _build(story, cfg, titulo_curto, logo_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# Memorial Descritivo (gerado do mapa)
# ──────────────────────────────────────────────────────────────────────────────
def memorial(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    rt = projeto.get("responsavel_tecnico") or {}
    story = GP._titulo("MEMORIAL DESCRITIVO", cfg, st, L)

    pares = [p for p in [
        ("Bairro", projeto.get("bairro")),
        ("Logradouro", projeto.get("endereco"), 3),
        ("Quadra", projeto.get("quadra")),
        ("Lote", projeto.get("lote_resultante")),
        ("Área", TX.m2(projeto.get("area_declarada_m2"))),
        ("Perímetro", TX.metros(projeto.get("perimetro_m"))),
        ("Município/UF", f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}", 2),
        ("CIM", TX.cim_completo(projeto)),
        ("TRT", projeto.get("trt_numero") or "—"),
    ] if p[1]]
    story.append(_ficha_compacta(pares, cfg, st, L))
    story.append(Spacer(1, 6))
    story.append(Paragraph("( ) Rural    (X) Urbano", st["corpo"]))
    story.append(Spacer(1, 8))

    story += GP._secao("DESCRIÇÃO PERIMÉTRICA", cfg, st, L)
    corpo = (f"Imóvel urbano denominado {projeto.get('denominacao_imovel') or ''}, "
             f"com área de {TX.m2_ext(projeto.get('area_declarada_m2'))} e perímetro de "
             f"{TX.metros_ext(projeto.get('perimetro_m'))}, assim descrito: ")
    corpo += TX.descricao_perimetrica(projeto)
    story += GP._paras(corpo, st["corpo"])

    # quadro de vértices, medidas e confrontações (do mapa) + croqui da poligonal
    quadro = _tabela_vertices(projeto, cfg, st, L)
    if quadro:
        story += quadro
        story += _secao_croqui(projeto, cfg, st, L)
    else:
        # sem planilha de vértices: lista as confrontações por lado (ex.: lote de desdobro)
        confs = projeto.get("_confrontacoes_lote") or []
        if confs:
            story += GP._secao("CONFRONTAÇÕES", cfg, st, L)
            from services.geo_urbano.generators.textos import _LADO_LABEL
            rows = [[_LADO_LABEL.get((c.get("lado") or "").lower(), c.get("lado") or ""),
                     TX.metros(c.get("medida_m")), c.get("confrontante") or ""] for c in confs]
            story.append(GP._data_table(["Lado", "Medida", "Confrontante"], rows, cfg, st, L))

    # papel do RT — SEMPRE traz a TRT/ART do processo
    papel_rt = f"Responsável Técnico — {rt.get('conselho') or ''} · INCRA {rt.get('credenciamento_incra') or ''}"
    papel_rt += f" · TRT/ART {projeto.get('trt_numero') or '—'}"
    story += GP._bloco_assinaturas([
        ("Superintendência de Habitação e Regularização Fundiária", "Aprovação municipal"),
    ], st, L)
    # RT com a firma gráfica já carimbada (se houver no perfil); senão só a linha
    story += _assina_rt_memorial(rt.get("nome") or "", papel_rt,
                                 projeto.get("_tecnico_assinatura_bytes"), st, L,
                                 projeto.get("_tecnico_assinatura_pos"))
    return _build(story, cfg, "Memorial Descritivo — " + (projeto.get("lote_resultante") or ""), logo_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# Cadeia Dominical (consolidada por matrícula)
# ──────────────────────────────────────────────────────────────────────────────
def cadeia_dominical(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    story = GP._titulo("CADEIA DOMINICAL", cfg, st, L)
    story += GP._paras(
        "Consolidação da origem e da cadeia de transmissões de cada matrícula até a "
        "titularidade atual da requerente, conforme as certidões de inteiro teor anexas.",
        st["corpo"])

    mats = sorted(projeto.get("matriculas") or [], key=lambda m: m.get("ordem", 0))
    for m in mats:
        cab = f"Matrícula nº {m.get('matricula') or '—'}"
        if m.get("lote_origem"):
            cab += f" — Lote {m['lote_origem']}, Quadra {m.get('quadra') or ''}"
        story += GP._secao(cab, cfg, st, L)
        prop = m.get("proprietario_registral") or {}
        linha = f"Proprietário registral atual: {prop.get('nome') or '—'}"
        if prop.get("doc"):
            linha += f" ({prop['doc']})"
        if m.get("registro_anterior"):
            linha += f". Origem: {m['registro_anterior']}"
        story += GP._paras(linha, st["corpo"])
        cadeia = m.get("cadeia") or []
        if cadeia:
            header = ["Ato", "Data", "Natureza", "Transmitente → Adquirente", "Protocolo"]
            rows = [[a.get("ato") or "", a.get("data") or "", a.get("tipo") or "",
                     f"{a.get('transmitente') or '—'} → {a.get('adquirente') or '—'}",
                     a.get("protocolo") or ""] for a in cadeia]
            story.append(GP._data_table(header, rows, cfg, st, L))
        else:
            story += GP._paras("Sem atos posteriores registrados além do Registro Geral.", st["small"])
    return _build(story, cfg, "Cadeia Dominical", logo_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# Ofício de Aprovação (Superintendência → Cartório de RI)
# ──────────────────────────────────────────────────────────────────────────────
def _img_b64(b64, largura):
    """data-uri/base64 → RLImage escalado à largura (None se inválido)."""
    if not b64:
        return None
    try:
        raw = b64.split(",", 1)[-1] if "," in b64 else b64
        data = base64.b64decode(raw)
        from reportlab.lib.utils import ImageReader
        iw, ih = ImageReader(io.BytesIO(data)).getSize()
        w = min(largura, float(iw))
        return RLImage(io.BytesIO(data), width=w, height=w * ih / iw)
    except Exception:  # noqa: BLE001
        return None


def oficio_aprovacao(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    sup = projeto.get("superintendencia") or {}
    cart = projeto.get("cartorio") or {}
    aprov_sup = (projeto.get("aprovacao") or {}).get("superintendencia") or {}
    numero = aprov_sup.get("oficio_numero") or "OF-____"

    story = []
    for ln in [sup.get("orgao") or "", sup.get("nome") or "Superintendência de Habitação e Regularização Fundiária"]:
        story.append(Paragraph(GP._esc(ln), st["corpo_c"]))
    story += GP._titulo(f"OFÍCIO Nº {numero}", cfg, st, L)

    # destinatário + referência
    story.append(Paragraph(GP._esc(f"Ao(À) {cart.get('nome') or 'Cartório de Registro de Imóveis'}"), st["corpo"]))
    if cart.get("endereco"):
        story.append(Paragraph(GP._esc(cart["endereco"]), st["corpo"]))
    story.append(Spacer(1, 8))
    ref = (f"Ref.: Processo de {projeto.get('tipo_servico') or 'remembramento'} — "
           f"{projeto.get('denominacao_imovel') or ''}; Matrícula(s) {TX.lista_matriculas_str(projeto) or '—'}.")
    story += GP._paras(ref, st["kv_b"])

    # corpo
    acao = TX.ACAO_SERVICO.get(projeto.get("tipo_servico"), "o ato requerido")
    corpo = (
        f"Senhor(a) Oficial,\n\n"
        f"A {sup.get('nome') or 'Superintendência de Habitação e Regularização Fundiária'}, "
        f"no uso de suas atribuições, COMUNICA a APROVAÇÃO do Memorial Descritivo e do Mapa "
        f"referentes ao imóvel {projeto.get('denominacao_imovel') or ''}, CMI "
        f"{TX.cim_completo(projeto) or '—'}, com área de {TX.m2(projeto.get('area_declarada_m2'))} "
        f"e perímetro de {TX.metros(projeto.get('perimetro_m'))}, AUTORIZANDO {acao}, com a abertura/"
        f"averbação do ato no Registro de Imóveis, conforme as peças técnicas aprovadas e anexas."
    )
    story += GP._paras(corpo, st["corpo"])

    # data + assinatura do Superintendente (+ carimbo/assinatura do órgão, se houver)
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story.append(Spacer(1, 28))
    assina_img = _img_b64(sup.get("assinatura_b64"), 6 * cm)
    carimbo_img = _img_b64(sup.get("carimbo_b64"), 4 * cm)
    if assina_img or carimbo_img:
        cels = [c for c in (carimbo_img, assina_img) if c]
        t = Table([cels], colWidths=[L / len(cels)] * len(cels))
        t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
        story.append(t)
    linha = Table([[""]], colWidths=[L * 0.55], style=[("LINEABOVE", (0, 0), (-1, -1), 0.8, black)])
    story.append(linha)
    story.append(Paragraph(f"<b>{GP._esc(sup.get('responsavel') or '')}</b>", st["assina"]))
    story.append(Paragraph(GP._esc(f"Superintendência de Habitação e Regularização Fundiária"
                                   f"{' — Portaria ' + sup['portaria'] if sup.get('portaria') else ''}"), st["assina"]))
    return _build(story, cfg, f"Ofício de Aprovação {numero}", logo_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# Quadro de Retificação (peça "de → para")
# ──────────────────────────────────────────────────────────────────────────────
def quadro_retificacao(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    an = projeto.get("retificacao_analise") or {}
    story = GP._titulo("QUADRO DE RETIFICAÇÃO", cfg, st, L)
    story += GP._paras(
        f"Imóvel: {projeto.get('denominacao_imovel') or ''} — Matrícula "
        f"{(projeto.get('matriculas') or [{}])[0].get('matricula') or '—'}. "
        f"Tipo: {an.get('retificacao_tipo') or projeto.get('retificacao_tipo') or '—'}.", st["corpo"])
    cad = an.get("cadastral_diffs") or []
    if cad:
        story += GP._secao("EIXO CADASTRAL — Matrícula × BCI", cfg, st, L)
        rows = [[d.get("campo"), str(d.get("valor_registro")), str(d.get("valor_bci")),
                 str(d.get("valor_correto")), "DIVERGENTE" if d.get("divergente") else "ok"] for d in cad]
        story.append(GP._data_table(["Campo", "Registro (matrícula)", "BCI (município)", "Valor correto", "Status"],
                                    rows, cfg, st, L))
    g = an.get("geometrico") or {}
    if g:
        story += GP._secao("EIXO GEOMÉTRICO — Mapa atual × Retificado", cfg, st, L)
        story.append(GP._data_table(
            ["Grandeza", "Antes", "Depois", "Variação"],
            [["Área", TX.m2(g.get("area_antes_m2")), TX.m2(g.get("area_depois_m2")), "Δ " + TX.m2(g.get("area_delta_m2"))],
             ["Perímetro", TX.metros(g.get("perimetro_antes_m")), TX.metros(g.get("perimetro_depois_m")),
              "Δ " + TX.metros(g.get("perimetro_delta_m"))]], cfg, st, L))
        confs = g.get("confrontantes_diff") or []
        if confs:
            story += GP._secao("CONFRONTAÇÕES (de → para)", cfg, st, L)
            rows = [[c.get("lado"), str(c.get("de")), str(c.get("para")),
                     "ALTERADO" if c.get("alterado") else "—"] for c in confs]
            story.append(GP._data_table(["Lado", "De", "Para", "Status"], rows, cfg, st, L))
    return _build(story, cfg, "Quadro de Retificação", logo_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# DRL — Declaração de Reconhecimento de Limites (anuência do confrontante, art. 213)
# ──────────────────────────────────────────────────────────────────────────────
def drl(projeto: dict, confrontante: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    mat = (projeto.get("matriculas") or [{}])[0]
    nome = confrontante.get("confrontante") or "—"
    story = GP._titulo("DECLARAÇÃO DE RECONHECIMENTO DE LIMITES (DRL)", cfg, st, L)
    qual = []
    if confrontante.get("doc"):
        qual.append(f"inscrito(a) sob o nº {confrontante['doc']}")
    if confrontante.get("endereco"):
        qual.append(f"residente e domiciliado(a) em {confrontante['endereco']}")
    corpo = (
        f"Eu, {nome}{(', ' + ', '.join(qual)) if qual else ''}, na qualidade de CONFRONTANTE do imóvel objeto "
        f"da Matrícula nº {mat.get('matricula') or '—'}"
        f"{(', situado em ' + projeto['endereco']) if projeto.get('endereco') else ''}, no Município de "
        f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}, DECLARO, para os fins do art. 213 da "
        f"Lei nº 6.015/1973, RECONHECER e ANUIR com os limites e confrontações constantes do Memorial Descritivo "
        f"e do Mapa Retificado do referido imóvel, especialmente quanto ao lado "
        f"{(confrontante.get('lado') or '').replace('_', ' ').upper()}, medindo "
        f"{TX.metros(confrontante.get('medida_m'))}, que divisa com a minha propriedade, nada tendo a opor à "
        f"presente retificação."
    )
    story += GP._paras(corpo, st["corpo"])
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story += GP._bloco_assinaturas([(nome, "Confrontante anuente")], st, L)
    return _build(story, cfg, f"DRL — {nome}", logo_bytes)


def confrontantes_para_drl(projeto: dict) -> list:
    """Só confrontantes PARTICULARES geram DRL (via/área pública dispensam)."""
    return [c for c in (projeto.get("confrontantes") or []) if (c.get("tipo") or "particular") == "particular"]


# ──────────────────────────────────────────────────────────────────────────────
# Usucapião Extrajudicial — Requerimento, Ata Notarial, Anuência, Notificação, Edital
# ──────────────────────────────────────────────────────────────────────────────
def _bloco_advogado(projeto: dict, st, L):
    """Bloco de assinatura do ADVOGADO (com OAB) — exigido no usucapião (art. 216-A)."""
    from reportlab.platypus import KeepTogether
    adv = next((p for p in (projeto.get("partes") or []) if p.get("papel") == "advogado"), None)
    if not adv or not adv.get("nome"):
        return []
    oab = adv.get("oab") or ""
    uf = adv.get("uf_oab") or ""
    if oab and uf and not oab.upper().startswith(("OAB/", "OAB ")):
        oab = f"OAB/{uf} {oab}"
    linhas = [(adv["nome"], True), (f"Advogado(a) — {oab}".rstrip(" —"), False)]
    b = [Spacer(1, 42),
         Table([[""]], colWidths=[L * 0.6], style=[("LINEABOVE", (0, 0), (-1, -1), 0.8, black)])]
    for txt, bold in linhas:
        b.append(Paragraph(f"<b>{GP._esc(txt)}</b>" if bold else GP._esc(txt), st["assina"]))
    b.append(Spacer(1, 14))
    return [KeepTogether(b)]


def requerimento_usucapiao(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    d = projeto.get("cartorio") or {}
    story = []
    for ln in [f"Ao Ilustríssimo Senhor Oficial do {d.get('nome') or 'Cartório de Registro de Imóveis'}",
               d.get("endereco") or ""]:
        if ln:
            story.append(Paragraph(GP._esc(ln), st["corpo"]))
    story.append(Spacer(1, 16))
    story += GP._titulo("REQUERIMENTO DE USUCAPIÃO EXTRAJUDICIAL", cfg, st, L)

    info = USU.MODALIDADES.get(projeto.get("modalidade_usucapiao") or "extraordinaria") or {}
    fund = USU.fundamento_legal(projeto)
    intro = (TX.bloco_requerentes(projeto)
             + "por seu advogado adiante assinado (art. 216-A da Lei nº 6.015/1973), vem REQUERER "
             + f"o RECONHECIMENTO EXTRAJUDICIAL DE USUCAPIÃO, na modalidade {info.get('label') or '—'} "
             + f"({fund}), do imóvel adiante descrito:")
    story += GP._paras(intro, st["corpo"])

    # Descrição do imóvel (matrícula ou pedido de abertura de matrícula).
    sit = projeto.get("situacao_registral") or "nao_matriculado"
    mats = projeto.get("matriculas") or []
    if sit == "nao_matriculado" or not mats:
        desc = (f"Imóvel urbano denominado {projeto.get('denominacao_imovel') or '—'}, situado em "
                f"{projeto.get('endereco') or '—'}, no Município de {projeto.get('municipio') or ''}/"
                f"{projeto.get('uf') or ''}, com área de {TX.m2(projeto.get('area_declarada_m2'))}, "
                f"SEM REGISTRO ANTERIOR, requerendo-se a ABERTURA DE MATRÍCULA.")
    else:
        desc = TX.transcricao_matricula(mats[0], projeto.get("municipio") or "", projeto.get("uf") or "")
    story += GP._secao("DO IMÓVEL", cfg, st, L)
    story += GP._paras(desc, st["corpo"])

    # Da posse + soma de posses.
    posse = projeto.get("posse") or {}
    pcorpo = (f"O requerente exerce posse {posse.get('natureza') or 'mansa, pacífica e ininterrupta'} "
              f"sobre o imóvel desde {posse.get('inicio') or '—'}"
              + (f", com origem em {posse['origem']}" if posse.get("origem") else "") + ". "
              + TX.soma_posses_texto(projeto))
    if posse.get("benfeitorias"):
        pcorpo += (f" Existem as seguintes benfeitorias: {posse['benfeitorias']}"
                   + (f" (desde {posse['benfeitorias_data']})" if posse.get("benfeitorias_data") else "") + ".")
    story += GP._secao("DA POSSE", cfg, st, L)
    story += GP._paras(pcorpo, st["corpo"])

    # Confrontantes + valor atribuído.
    confs = projeto.get("confrontantes") or []
    if confs:
        rol = "; ".join(f"{(c.get('lado') or '').replace('_', ' ')}: {c.get('confrontante') or '—'}"
                        for c in confs)
        story += GP._secao("DOS CONFRONTANTES", cfg, st, L)
        story += GP._paras("O imóvel confronta com: " + rol + ".", st["corpo"])
    story += GP._paras(f"Valor atribuído ao imóvel: {TX.valor_atribuido_texto(projeto)}.", st["corpo"])

    story += GP._paras("Nestes termos,\nPede deferimento.", st["corpo"])
    story.append(Spacer(1, 4))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story += _bloco_assinaturas_partes(projeto, st, L)
    story += _bloco_advogado(projeto, st, L)
    return _build(story, cfg, "Requerimento de Usucapião", logo_bytes)


def ata_notarial(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    story = GP._titulo("MINUTA DE ATA NOTARIAL DE POSSE", cfg, st, L)
    story += GP._paras(
        "SAIBAM quantos esta virem que, perante o Tabelionato de Notas da circunscrição do imóvel, "
        "comparece o requerente abaixo qualificado, a fim de que seja lavrada ATA NOTARIAL atestando, "
        "com fé pública, o tempo, a natureza e as condições da posse exercida (art. 216-A da Lei nº "
        "6.015/1973; Provimento CNJ nº 149/2023).", st["corpo"])
    story += GP._paras(TX.bloco_requerentes(projeto), st["corpo"])
    posse = projeto.get("posse") or {}
    story += GP._secao("DA POSSE DECLARADA", cfg, st, L)
    story += GP._paras(
        f"O requerente declara exercer posse {posse.get('natureza') or 'mansa, pacífica e ininterrupta'} "
        f"sobre o imóvel denominado {projeto.get('denominacao_imovel') or '—'}, situado em "
        f"{projeto.get('endereco') or '—'}, {projeto.get('municipio') or ''}/{projeto.get('uf') or ''}, "
        f"desde {posse.get('inicio') or '—'}. {TX.soma_posses_texto(projeto)}", st["corpo"])
    testemunhas = [p for p in (projeto.get("partes") or []) if p.get("papel") == "testemunha"]
    if testemunhas:
        story += GP._secao("DAS TESTEMUNHAS", cfg, st, L)
        story += GP._paras("Ouvidas as testemunhas: "
                           + "; ".join(t.get("nome") or "—" for t in testemunhas) + ".", st["corpo"])
    story += GP._paras("Documentos apresentados e demais declarações são consignados pelo Tabelião no "
                       "ato da lavratura. Esta minuta serve de subsídio ao Tabelionato de Notas.", st["small"])
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story += _bloco_assinaturas_partes(projeto, st, L)
    return _build(story, cfg, "Minuta de Ata Notarial", logo_bytes)


def edital_usucapiao(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    info = USU.MODALIDADES.get(projeto.get("modalidade_usucapiao") or "extraordinaria") or {}
    story = GP._titulo("EDITAL DE RECONHECIMENTO EXTRAJUDICIAL DE USUCAPIÃO", cfg, st, L)
    story += GP._paras(
        "O Oficial de Registro de Imóveis FAZ SABER, para conhecimento de eventuais interessados "
        "incertos e não sabidos, que tramita pedido de reconhecimento extrajudicial de usucapião "
        f"(art. 216-A da Lei nº 6.015/1973; Provimento CNJ nº 149/2023), na modalidade "
        f"{info.get('label') or '—'} ({USU.fundamento_legal(projeto)}), referente ao imóvel "
        f"{projeto.get('denominacao_imovel') or '—'}, situado em {projeto.get('endereco') or '—'}, "
        f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}, com área de "
        f"{TX.m2(projeto.get('area_declarada_m2'))}, requerido por "
        f"{TX.bloco_requerentes(projeto).rstrip(', ')}.", st["corpo"])
    story += GP._paras(
        "Ficam INTIMADOS eventuais interessados a se manifestarem no prazo de 15 (quinze) dias. "
        "Decorrido o prazo sem impugnação fundamentada, presumir-se-á a concordância (art. 216-A, "
        "§ 4º, da Lei nº 6.015/1973, com a redação da Lei nº 13.465/2017).", st["corpo"])
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    return _build(story, cfg, "Edital de Usucapião", logo_bytes)


def declaracao_anuencia(projeto: dict, anuente: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    nome = anuente.get("nome") or "—"
    papel = "TITULAR DE DIREITOS" if anuente.get("papel") == "titular_tabular" else "CONFRONTANTE"
    story = GP._titulo("DECLARAÇÃO DE ANUÊNCIA", cfg, st, L)
    qual = []
    if anuente.get("doc"):
        qual.append(f"inscrito(a) sob o nº {anuente['doc']}")
    if anuente.get("endereco"):
        qual.append(f"residente e domiciliado(a) em {anuente['endereco']}")
    lado_txt = ""
    if anuente.get("lado"):
        lado_txt = (f", especialmente quanto ao lado {(anuente.get('lado') or '').replace('_', ' ').upper()}"
                    f", medindo {TX.metros(anuente.get('medida_m'))}")
    corpo = (
        f"Eu, {nome}{(', ' + ', '.join(qual)) if qual else ''}, na qualidade de {papel} do imóvel "
        f"objeto do pedido de reconhecimento extrajudicial de usucapião — {projeto.get('denominacao_imovel') or '—'}, "
        f"situado em {projeto.get('endereco') or '—'}, {projeto.get('municipio') or ''}/{projeto.get('uf') or ''} —, "
        f"DECLARO, para os fins do art. 216-A da Lei nº 6.015/1973, RECONHECER e ANUIR com os limites e "
        f"confrontações constantes da Planta e do Memorial Descritivo do referido imóvel{lado_txt}, nada "
        f"tendo a opor ao presente pedido."
    )
    story += GP._paras(corpo, st["corpo"])
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story += GP._bloco_assinaturas([(nome, papel.title() + " anuente")], st, L)
    return _build(story, cfg, f"Anuência — {nome}", logo_bytes)


def notificacao(projeto: dict, anuente: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    nome = anuente.get("nome") or "—"
    story = GP._titulo("NOTIFICAÇÃO DE CONFRONTANTE", cfg, st, L)
    story += GP._paras(f"Prezado(a) Sr.(a) {nome},", st["corpo"])
    story += GP._paras(
        "Fica V.Sa. NOTIFICADO(A), na qualidade de confrontante/titular de direitos, acerca do pedido "
        f"de reconhecimento extrajudicial de usucapião do imóvel {projeto.get('denominacao_imovel') or '—'}, "
        f"situado em {projeto.get('endereco') or '—'}, {projeto.get('municipio') or ''}/{projeto.get('uf') or ''}, "
        "para que se manifeste no prazo de 15 (quinze) dias. O silêncio será interpretado como CONCORDÂNCIA "
        "(art. 216-A, § 4º, da Lei nº 6.015/1973, com a redação da Lei nº 13.465/2017).", st["corpo"])
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    return _build(story, cfg, f"Notificação — {nome}", logo_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────────────────────
def gerar_pdf(tipo: str, projeto: dict, tema: str = "prime_i", logo_bytes=None) -> bytes:
    if tipo == "quadro_retificacao":
        return quadro_retificacao(projeto, tema, logo_bytes)
    if tipo == "requerimento_cartorio":
        return requerimento(projeto, "cartorio", tema, logo_bytes)
    if tipo == "requerimento_superintendencia":
        return requerimento(projeto, "superintendencia", tema, logo_bytes)
    if tipo == "memorial_descritivo":
        return memorial(projeto, tema, logo_bytes)
    if tipo == "cadeia_dominical":
        return cadeia_dominical(projeto, tema, logo_bytes)
    if tipo == "oficio_aprovacao":
        return oficio_aprovacao(projeto, tema, logo_bytes)
    if tipo == "requerimento_usucapiao":
        return requerimento_usucapiao(projeto, tema, logo_bytes)
    if tipo == "ata_notarial":
        return ata_notarial(projeto, tema, logo_bytes)
    if tipo == "edital_usucapiao":
        return edital_usucapiao(projeto, tema, logo_bytes)
    raise ValueError(f"tipo de documento desconhecido: {tipo}")
