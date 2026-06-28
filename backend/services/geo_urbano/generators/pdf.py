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
from reportlab.lib.colors import HexColor, black
from reportlab.platypus import Paragraph, Spacer, Image as RLImage, Table, TableStyle

from pdf.templates.resilient import ResilientSimpleDocTemplate
from services.georef.generators import pdf as GP   # blocos genéricos reusados
from services.geo_urbano.generators import textos as TX

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


def _partes_assinatura(projeto: dict):
    """Linhas de assinatura das partes (requerente PJ → representante; ou PF)."""
    out = []
    for p in projeto.get("partes") or []:
        if p.get("papel") == "requerente" and p.get("tipo_pessoa") == "juridica":
            continue  # PJ assina via representante
        nome = p.get("nome") or p.get("razao_social") or ""
        papel = {"requerente": "Requerente", "representante": "Representante legal",
                 "socio": "Sócio", "conjuge": "Cônjuge anuente"}.get(p.get("papel"), "Requerente")
        if nome:
            out.append((nome, papel))
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

    # cadastro / CMI
    pares = [p for p in [
        ("Cadastro novo", projeto.get("cadastro_novo")),
        ("Cadastro antigo", projeto.get("cadastro_antigo")),
        ("CMI resultante", projeto.get("cmi_resultante")),
        ("Área total", TX.m2(projeto.get("area_declarada_m2"))),
        ("Perímetro", TX.metros(projeto.get("perimetro_m"))),
    ] if p[1]]
    if pares:
        story.append(Spacer(1, 6))
        story.append(GP._kv_table(pares, cfg, st, L))

    # fecho
    story += GP._paras("Nestes termos,\nPede deferimento.", st["corpo"])
    story.append(Spacer(1, 4))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story += GP._bloco_assinaturas(_partes_assinatura(projeto), st, L)
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
        ("Logradouro", projeto.get("endereco")),
        ("Quadra", projeto.get("quadra")),
        ("Lote", projeto.get("lote_resultante")),
        ("Área", TX.m2(projeto.get("area_declarada_m2"))),
        ("Perímetro", TX.metros(projeto.get("perimetro_m"))),
        ("Município/UF", f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}"),
        ("CIM", projeto.get("cmi_resultante")),
        ("TRT", projeto.get("trt_numero") or "—"),
    ] if p[1]]
    story.append(GP._kv_table(pares, cfg, st, L))
    story.append(Spacer(1, 6))
    story.append(Paragraph("( ) Rural    (X) Urbano", st["corpo"]))
    story.append(Spacer(1, 8))

    story += GP._secao("DESCRIÇÃO PERIMÉTRICA", cfg, st, L)
    corpo = (f"Imóvel urbano denominado {projeto.get('denominacao_imovel') or ''}, "
             f"com área de {TX.m2(projeto.get('area_declarada_m2'))} e perímetro de "
             f"{TX.metros(projeto.get('perimetro_m'))}, assim descrito: ")
    corpo += TX.descricao_perimetrica(projeto)
    story += GP._paras(corpo, st["corpo"])

    # quadro de vértices
    verts = sorted(projeto.get("vertices") or [], key=lambda v: v.get("ordem", 0))
    if verts:
        story += GP._secao("QUADRO DE VÉRTICES", cfg, st, L)
        header = ["De", "Para", "Coord. N (Y)", "Coord. E (X)", "Azimute", "Dist. (m)", "Confrontante"]
        rows = [[v.get("de") or "", v.get("para") or "", TX._n_br(v.get("coord_n"), 4),
                 TX._n_br(v.get("coord_e"), 4), v.get("azimute") or "", TX._n_br(v.get("distancia_m")),
                 v.get("confrontante_lado") or ""] for v in verts]
        story.append(GP._data_table(header, rows, cfg, st, L))
    else:
        # sem planilha de vértices: lista as confrontações por lado (ex.: lote de desdobro)
        confs = projeto.get("_confrontacoes_lote") or []
        if confs:
            story += GP._secao("CONFRONTAÇÕES", cfg, st, L)
            from services.geo_urbano.generators.textos import _LADO_LABEL
            rows = [[_LADO_LABEL.get((c.get("lado") or "").lower(), c.get("lado") or ""),
                     TX.metros(c.get("medida_m")), c.get("confrontante") or ""] for c in confs]
            story.append(GP._data_table(["Lado", "Medida", "Confrontante"], rows, cfg, st, L))

    story += GP._bloco_assinaturas([
        ("Superintendência de Habitação e Regularização Fundiária", "Aprovação municipal"),
        (rt.get("nome") or "", f"Responsável Técnico — {rt.get('conselho') or ''} · INCRA {rt.get('credenciamento_incra') or ''}"),
    ], st, L)
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
        f"{projeto.get('cmi_resultante') or '—'}, com área de {TX.m2(projeto.get('area_declarada_m2'))} "
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
    raise ValueError(f"tipo de documento desconhecido: {tipo}")
