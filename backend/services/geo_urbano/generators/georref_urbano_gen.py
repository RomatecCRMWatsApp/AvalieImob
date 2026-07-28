# @module services.geo_urbano.generators.georref_urbano_gen — Fase 6 (geradores).
#
# Peças do Georreferenciamento de lote urbano (localização e situação), montadas
# pela COMPOSIÇÃO escolhida pelo usuário. REUSA a infra dos geradores existentes
# (harness/temas de `pdf.py`, blocos genéricos do Georref, dossiê de `dossie.py`,
# croqui vetorial) — "não duplicar infra". Nada aqui é remembramento: sem
# requerimento/superintendência; peça central = Mapa + Memorial + ART/TRT.
from __future__ import annotations

import io
import math
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph, Spacer

from pypdf import PdfReader, PdfWriter

from services.georef.generators import pdf as GP            # blocos genéricos (temas/estilos)
from services.geo_urbano.generators import pdf as PDF        # harness + helpers do módulo
from services.geo_urbano.generators import textos as TX
from services.geo_urbano.generators import dossie as DOSSIE
from services.geo_urbano.generators import capa as CAPA      # helpers de imagem (fontes/paleta)
from services.geo_urbano import orientacao as ORI
from services.geo_urbano import georref_urbano as GU6

_LADO_LABEL = {
    "frente": "Frente", "lateral_direita": "Lateral direita",
    "lateral_esquerda": "Lateral esquerda", "fundo": "Fundos",
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers comuns
# ──────────────────────────────────────────────────────────────────────────────
def _area(projeto: dict):
    """Área a exibir: a LEVANTADA (poligonal) prevalece; cai p/ a declarada."""
    return projeto.get("area_calculada_m2") or projeto.get("area_declarada") or projeto.get("area_declarada_m2")


def _papel_rt(projeto: dict) -> str:
    rt = projeto.get("responsavel_tecnico") or {}
    p = f"Responsável Técnico — {rt.get('formacao') or 'Técnico em Agrimensura'}"
    if rt.get("conselho"):
        p += f" · {rt['conselho']}"
    if rt.get("credenciamento_incra"):
        p += f" · Credenciamento INCRA: {rt['credenciamento_incra']}"
    if projeto.get("trt_numero") or (projeto.get("art_trt") or {}).get("numero"):
        p += f" · TRT/ART {projeto.get('trt_numero') or projeto['art_trt']['numero']}"
    return p


def _ficha_identificacao(projeto: dict, cfg, st, L):
    prop = _proprietario_nome(projeto)
    pares = [p for p in [
        ("Denominação", projeto.get("denominacao_imovel") or "", 3),
        ("Proprietário", prop),
        ("Logradouro", projeto.get("endereco") or "", 3),
        ("Nº / CEP", " / ".join([x for x in [projeto.get("numero"), projeto.get("cep")] if x])),
        ("Quadra / Lote", " / ".join([x for x in [projeto.get("quadra"), projeto.get("lote_resultante")] if x])),
        ("Loteamento", projeto.get("loteamento") or "", 2),
        ("Município/UF", f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}", 2),
        ("Área", TX.m2(_area(projeto))),
        ("Perímetro", TX.metros(projeto.get("perimetro_m"))),
        ("Matrícula", projeto.get("matricula_numero") or (projeto.get("matriculas") or [{}])[0].get("matricula") if projeto.get("matriculas") else None),
    ] if p[1]]
    return PDF._ficha_compacta(pares, cfg, st, L)


def _proprietario_nome(projeto: dict) -> str:
    for p in projeto.get("partes") or []:
        if p.get("papel") in ("requerente", "titular_tabular", None) and (p.get("razao_social") or p.get("nome")):
            return p.get("razao_social") or p.get("nome")
    for p in projeto.get("partes") or []:
        if p.get("razao_social") or p.get("nome"):
            return p.get("razao_social") or p.get("nome")
    return ""


def _lados(projeto: dict):
    """Vértices ordenados com o lado calculado (frente/laterais/fundo)."""
    verts = sorted(projeto.get("vertices") or [], key=lambda v: v.get("ordem", 0))
    if verts:
        cls = ORI.classificar_lados(verts, frente_idx=projeto.get("frente_idx"))
        for v, lado in zip(verts, cls["lados"]):
            v["_lado_calc"] = lado
    return verts


def _rt_flow(projeto: dict, st, L):
    rt = projeto.get("responsavel_tecnico") or {}
    return PDF._assina_rt_memorial(
        rt.get("nome") or "", _papel_rt(projeto),
        projeto.get("_tecnico_assinatura_bytes"), st, L,
        projeto.get("_tecnico_assinatura_pos"))


def _rodape_norma(st):
    return [Spacer(1, 8), Paragraph(
        "Elaborado em conformidade com a NBR 13133 (ABNT) e com as normas do "
        "Sistema Geodésico Brasileiro — SIRGAS 2000.", st["small"])]


# ── Builders calibrados no modelo REAL (QD04 LT20 ROV — Açailândia) ─────────────
_UF_EXTENSO = {
    "MA": "Maranhão", "PA": "Pará", "TO": "Tocantins", "PI": "Piauí", "CE": "Ceará",
    "GO": "Goiás", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "BA": "Bahia",
    "SP": "São Paulo", "MG": "Minas Gerais", "DF": "Distrito Federal",
}


def _estado_extenso(uf) -> str:
    return _UF_EXTENSO.get((uf or "").upper(), (uf or "").upper())


def _coord_br(v) -> str:
    """9450853.3 → '9.450.853,30' (milhar '.', decimal ',')."""
    try:
        return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


def _vn(v) -> str:
    return v.get("de") or f"P{v.get('ordem') or ''}"


def _ficha_georref(projeto: dict, cfg, st, L):
    """Ficha de identificação no layout do modelo real (Bairro/Rua/Quadra/Lote/
    Área/Município/Estado/CIM/TRT)."""
    pares = [p for p in [
        ("Bairro", projeto.get("bairro") or projeto.get("loteamento") or "", 2),
        ("Rua", projeto.get("endereco") or "", 2),
        ("Quadra", projeto.get("quadra") or ""),
        ("Lote", projeto.get("lote_resultante") or ""),
        ("Área", TX.m2(_area(projeto))),
        ("Município", projeto.get("municipio") or ""),
        ("Estado", (projeto.get("uf") or "").upper()),
        ("CIM", TX.cim_completo(projeto) or "", 2),
        ("Proprietário", _proprietario_nome(projeto) or "", 2),
        ("TRT", projeto.get("trt_numero") or (projeto.get("art_trt") or {}).get("numero") or "—"),
    ] if p[1]]
    return PDF._ficha_compacta(pares, cfg, st, L)


def descricao_perimetro(projeto: dict) -> str:
    """MD-PER — prosa vértice a vértice no formato do modelo real (coords N/E
    inline, feição, confrontante por segmento + fecho PPP/SIRGAS2000/UTM)."""
    verts = sorted(projeto.get("vertices") or [], key=lambda v: v.get("ordem", 0))
    n = len(verts)
    if n < 3:
        return ""
    v0 = verts[0]
    s = (f"Inicia-se a descrição deste perímetro no vértice {_vn(v0)}, de coordenadas "
         f"N {_coord_br(v0.get('coord_n'))}m e E {_coord_br(v0.get('coord_e'))}m;")
    if v0.get("feicao"):
        s += f" {v0['feicao']};"
    for i in range(n):
        v, nxt = verts[i], verts[(i + 1) % n]
        conf = v.get("confrontante_lado") or v.get("confrontante") or "confrontante"
        az = v.get("azimute") or "—"
        s += (f" deste, segue confrontando com {conf}, com os seguintes azimutes e distâncias: "
              f"{az} e {TX.metros(v.get('distancia_m'))} até o vértice {_vn(nxt)}")
        if (i + 1) % n == 0:
            s += ", ponto inicial da descrição deste perímetro."
        else:
            s += f", de coordenadas N {_coord_br(nxt.get('coord_n'))}m e E {_coord_br(nxt.get('coord_e'))}m;"
            if nxt.get("feicao"):
                s += f" {nxt['feicao']};"
    lev = projeto.get("levantamento") or {}
    mc = lev.get("meridiano_central") or "45°00'"
    fuso = lev.get("fuso") or "-23"
    s += (" As coordenadas da base foram processadas pelo método de Posicionamento por Ponto "
          "Preciso (PPP). Todas as coordenadas aqui descritas estão georreferenciadas ao Sistema "
          "Geodésico Brasileiro e encontram-se representadas no Sistema U T M, referenciadas ao "
          f"Meridiano Central nº {mc}, fuso {fuso}, tendo como datum o SIRGAS2000. Todos os "
          "azimutes e distâncias, área e perímetro foram calculados no plano de projeção U T M.")
    return s


def descricao_situacao(projeto: dict) -> str:
    """MD-SIT — descrição cartorial de localização e situação (modelo real)."""
    verts = _lados(projeto)

    def side(lado):
        v = next((x for x in verts if x.get("_lado_calc") == lado), None)
        if not v:
            return ("", "")
        return (TX.metros_ext(v.get("distancia_m")),
                v.get("confrontante_lado") or v.get("confrontante") or "")

    fmed, fconf = side("frente")
    ldmed, ldconf = side("lateral_direita")
    lemed, leconf = side("lateral_esquerda")
    fumed, fuconf = side("fundo")
    lote = projeto.get("lote_resultante") or "—"
    quadra = projeto.get("quadra") or "—"
    lot = (projeto.get("loteamento") or "").upper()
    frente_conf = fconf or projeto.get("endereco") or "logradouro público"
    s = (f"Um TERRENO nesta cidade de {projeto.get('municipio') or ''}, "
         f"Estado do {_estado_extenso(projeto.get('uf'))}, Frente para a {frente_conf}, "
         f"constituído de parte do Lote nº {lote}, denominado Lote nº {lote} da Quadra nº {quadra}"
         + (f" – {lot}" if lot else "") + f", com área de {TX.m2_ext(_area(projeto))};")
    med = []
    if fmed:
        med.append(f"medindo de Frente {fmed} com a {frente_conf}")
    if ldmed:
        med.append(f"Lateral Direita: {ldmed} com o {ldconf}")
    if lemed:
        med.append(f"Lateral Esquerda: {lemed} com o {leconf}")
    if fumed:
        med.append(f"Fundo {fumed} com o {fuconf}")
    if med:
        s += " " + "; ".join(med) + "."
    formato = (projeto.get("quadra_dados") or {}).get("formato") or "retangular"
    s += f" Formato do lote {formato}."
    vias = [v.get("nome") for v in ((projeto.get("quadra_dados") or {}).get("vias") or []) if v.get("nome")]
    if vias:
        vs = (", ".join(vias[:-1]) + " e " + vias[-1]) if len(vias) > 1 else vias[0]
        s += f" Situado na quadra formada pelas seguintes confrontantes: {vs}."
    esq = (projeto.get("quadra_dados") or {}).get("esquina") or {}
    if esq.get("distancia_m"):
        s += (f" Distante da esquina com a {esq.get('logradouro') or 'via'}, "
              f"medindo {TX.metros_ext(esq.get('distancia_m'))}.")
    return s


def _marca_urbano(st):
    return [Spacer(1, 10),
            Paragraph("MEMORIAL DESCRITIVO", st.get("small") or st["corpo"]),
            Paragraph("(  ) Imóvel Rural.&nbsp;&nbsp;&nbsp;(X) Imóvel Urbano.",
                      st.get("small") or st["corpo"])]


# ──────────────────────────────────────────────────────────────────────────────
# Memoriais (§6)
# ──────────────────────────────────────────────────────────────────────────────
def memorial_perimetrico(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    """MD-PER — descrição do perímetro vértice a vértice (formato do modelo real)."""
    cfg = GP._cfg(tema); st = GP._styles(cfg); L = PDF._largura()
    story = GP._titulo("MEMORIAL DESCRITIVO PERIMÉTRICO", cfg, st, L)
    story.append(_ficha_georref(projeto, cfg, st, L))
    story += GP._secao("DESCRIÇÃO DO PERÍMETRO", cfg, st, L)
    story += GP._paras(descricao_perimetro(projeto), st["corpo"])
    story += PDF._tabela_vertices(projeto, cfg, st, L)
    story += PDF._secao_croqui(projeto, cfg, st, L)
    story += _rodape_norma(st)
    story.append(Spacer(1, 10))
    story.append(Paragraph(GP._esc(PDF._data_extenso(projeto.get("municipio") or "Açailândia",
                                                     projeto.get("uf") or "MA")), st["corpo_c"]))
    story += _rt_flow(projeto, st, L)
    story += _marca_urbano(st)
    return PDF._build(story, cfg, "Memorial Perimétrico", logo_bytes)


def memorial_situacao(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    """MD-SIT — descrição cartorial de localização e situação (formato do modelo
    real). Nas finalidades municipais leva a linha da Superintendência de Habitação
    e Regularização Fundiária (aprovação); no financiamento bancário, só o RT."""
    cfg = GP._cfg(tema); st = GP._styles(cfg); L = PDF._largura()
    story = GP._titulo("MEMORIAL DESCRITIVO", cfg, st, L)
    story.append(_ficha_georref(projeto, cfg, st, L))
    story += GP._secao("DESCRIÇÃO DO IMÓVEL", cfg, st, L)
    story += GP._paras(descricao_situacao(projeto), st["corpo"])
    story.append(Spacer(1, 10))
    story.append(Paragraph(GP._esc(PDF._data_extenso(projeto.get("municipio") or "Açailândia",
                                                     projeto.get("uf") or "MA")), st["corpo_c"]))
    # a Superintendência aprova o memorial de situação nos processos municipais
    if projeto.get("finalidade") != "financiamento_bancario":
        story += GP._bloco_assinaturas([
            ("SUPERINTENDÊNCIA DE HABITAÇÃO E REGULARIZAÇÃO FUNDIÁRIA", ""),
        ], st, L)
    story += _rt_flow(projeto, st, L)
    story += _marca_urbano(st)
    return PDF._build(story, cfg, "Memorial de Situação", logo_bytes)


def memorial_sucinto(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    """MD-SUC — descrição sucinta (1 página, formato p/ correspondente bancário)."""
    cfg = GP._cfg(tema); st = GP._styles(cfg); L = PDF._largura()
    story = GP._titulo("DESCRIÇÃO SUCINTA (RESUMO TÉCNICO)", cfg, st, L)
    verts = sorted(projeto.get("vertices") or [], key=lambda v: v.get("ordem", 0))
    amarr = verts[0] if verts else {}
    coord = "—"
    if amarr.get("coord_e") and amarr.get("coord_n"):
        coord = f"E {amarr['coord_e']:.3f} m · N {amarr['coord_n']:.3f} m ({amarr.get('de') or 'P-01'})"
    pares = [p for p in [
        ("Imóvel", projeto.get("denominacao_imovel") or "", 3),
        ("Proprietário", _proprietario_nome(projeto), 3),
        ("Endereço", " ".join([x for x in [projeto.get("endereco"), projeto.get("numero")] if x]) or "—", 3),
        ("Quadra / Lote", " / ".join([x for x in [projeto.get("quadra"), projeto.get("lote_resultante")] if x])),
        ("Loteamento", projeto.get("loteamento") or "—", 2),
        ("Município/UF", f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}", 2),
        ("Área", TX.m2(_area(projeto))),
        ("Perímetro", TX.metros(projeto.get("perimetro_m"))),
        ("Vértice de amarração", coord, 3),
        ("Sistema", (projeto.get("levantamento") or {}).get("sistema") or "SIRGAS 2000 / UTM", 2),
        ("Finalidade", GU6.finalidade_texto(projeto) or "localização e situação", 3),
    ] if p[1]]
    story.append(PDF._ficha_compacta(pares, cfg, st, L))
    story += _rodape_norma(st)
    story.append(Spacer(1, 12))
    story.append(Paragraph(GP._esc(PDF._data_extenso(projeto.get("municipio") or "Açailândia",
                                                     projeto.get("uf") or "MA")), st["corpo_c"]))
    story += _rt_flow(projeto, st, L)
    return PDF._build(story, cfg, "Descrição Sucinta", logo_bytes)


def memorial_area_construida(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    """MD-CON — quadro de áreas edificadas (só com benfeitoria)."""
    cfg = GP._cfg(tema); st = GP._styles(cfg); L = PDF._largura()
    story = GP._titulo("MEMORIAL DE ÁREA CONSTRUÍDA", cfg, st, L)
    story.append(_ficha_identificacao(projeto, cfg, st, L))
    story += GP._secao("QUADRO DE ÁREAS EDIFICADAS", cfg, st, L)
    itens = projeto.get("areas_construidas") or []
    total = projeto.get("area_construida_total")
    if itens:
        rows = [[it.get("descricao") or it.get("pavimento") or "", TX.m2(it.get("area"))] for it in itens]
        if total is None:
            try:
                total = sum(float(it.get("area") or 0) for it in itens)
            except (TypeError, ValueError):
                total = None
        story.append(GP._data_table(["Pavimento / Bloco", "Área"], rows, cfg, st, L))
    else:
        story += GP._paras("Áreas edificadas a discriminar por pavimento/bloco.", st["small"])
    if total is not None:
        story.append(Spacer(1, 6))
        story += GP._paras(f"Área total construída: {TX.m2(total)}.", st["corpo"])
    # índices urbanísticos (se informados)
    to = projeto.get("taxa_ocupacao"); ca = projeto.get("coef_aproveitamento")
    if to or ca:
        idx = []
        if to:
            idx.append(f"Taxa de ocupação: {to}%")
        if ca:
            idx.append(f"Coeficiente de aproveitamento: {ca}")
        story += GP._paras(" · ".join(idx) + ".", st["small"])
    story += _rodape_norma(st)
    story.append(Spacer(1, 10))
    story += _rt_flow(projeto, st, L)
    return PDF._build(story, cfg, "Memorial de Área Construída", logo_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# Quadro de vértices (peça isolada) · Mapa do lote (gerado) · Planta de quadra
# ──────────────────────────────────────────────────────────────────────────────
def quadro_vertices(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema); st = GP._styles(cfg); L = PDF._largura()
    story = GP._titulo("QUADRO DE VÉRTICES", cfg, st, L)
    tab = PDF._tabela_vertices(projeto, cfg, st, L)
    story += tab or GP._paras("Nenhum vértice informado.", st["small"])
    story += _rodape_norma(st)
    return PDF._build(story, cfg, "Quadro de Vértices", logo_bytes)


def mapa_lote_gerado(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    """Planta do lote gerada (croqui vetorial + quadro), quando não há mapa anexado."""
    cfg = GP._cfg(tema); st = GP._styles(cfg); L = PDF._largura()
    story = GP._titulo("MAPA DO LOTE (COORDENADAS)", cfg, st, L)
    story += PDF._secao_croqui(projeto, cfg, st, L)
    story += PDF._tabela_vertices(projeto, cfg, st, L)
    story += _rodape_norma(st)
    return PDF._build(story, cfg, "Mapa do Lote", logo_bytes)


def planta_quadra_gerada(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    """Planta de quadra (§8, modo 'gerada'): croqui do lote objeto + quadro de
    lotes/vias da quadra + cota até a esquina."""
    cfg = GP._cfg(tema); st = GP._styles(cfg); L = PDF._largura()
    story = GP._titulo("PLANTA DE QUADRA", cfg, st, L)
    story += PDF._secao_croqui(projeto, cfg, st, L)
    qd = projeto.get("quadra_dados") or {}
    lotes = qd.get("lotes") or []
    if lotes:
        rows = [[l.get("lote") or "", l.get("confrontacao") or "", TX.metros(l.get("medida_frente"))] for l in lotes]
        story += GP._secao("LOTES DA QUADRA", cfg, st, L)
        story.append(GP._data_table(["Lote", "Posição", "Testada"], rows, cfg, st, L))
    vias = qd.get("vias") or []
    if vias:
        rows = [[v.get("nome") or "", (v.get("posicao") or "").upper()] for v in vias]
        story += GP._secao("VIAS LIMÍTROFES", cfg, st, L)
        story.append(GP._data_table(["Logradouro", "Posição (N/S/L/O)"], rows, cfg, st, L))
    esq = qd.get("esquina") or {}
    if esq.get("distancia_m"):
        story += GP._paras(f"Distância até {esq.get('logradouro') or 'a esquina'}: "
                           f"{TX.metros_ext(esq.get('distancia_m'))}.", st["corpo"])
    story += _rodape_norma(st)
    return PDF._build(story, cfg, "Planta de Quadra", logo_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# ART/TRT (§9) · Apresentação (§7.3)
# ──────────────────────────────────────────────────────────────────────────────
def art_trt_peca(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema); st = GP._styles(cfg); L = PDF._largura()
    art = projeto.get("art_trt") or {}
    tipo = (art.get("tipo") or "TRT").upper()
    story = GP._titulo(f"{tipo} — RESPONSABILIDADE TÉCNICA", cfg, st, L)
    rt = projeto.get("responsavel_tecnico") or {}
    atividade = (art.get("atividade") or
                 "Levantamento topográfico planialtimétrico cadastral / georreferenciamento "
                 "de lote urbano para fins de localização e situação.")
    pares = [p for p in [
        ("Documento", f"{tipo} nº {art.get('numero') or '—'}"),
        ("Data de registro", art.get("data") or "—"),
        ("Valor", TX.m2(art.get("valor")).replace(" m²", "") if art.get("valor") else "—"),
        ("Responsável Técnico", rt.get("nome") or "—", 2),
        ("Registro profissional", rt.get("conselho") or "—", 2),
        ("Credenciamento INCRA", rt.get("credenciamento_incra") or "—"),
        ("Atividade técnica", atividade, 4),
    ] if p[1]]
    story.append(PDF._ficha_compacta(pares, cfg, st, L))
    if art.get("observacao"):
        story += GP._secao("OBSERVAÇÕES", cfg, st, L)
        story += GP._paras(str(art["observacao"]), st["corpo"])
    if not (art.get("numero") or (projeto.get("uploads") or {}).get("art_trt_pdf")):
        story += GP._paras("Documento de responsabilidade técnica a ser emitido/anexado.", st["small"])
    story.append(Spacer(1, 12))
    story += _rt_flow(projeto, st, L)
    return PDF._build(story, cfg, f"{tipo}", logo_bytes)


def apresentacao(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    """Página de apresentação (§7.3). Texto default; sobrescrito por
    projeto['apresentacao_texto'] (rich text editado no front)."""
    cfg = GP._cfg(tema); st = GP._styles(cfg); L = PDF._largura()
    story = GP._titulo("APRESENTAÇÃO", cfg, st, L)
    over = (projeto.get("apresentacao_texto") or "").strip()
    if over:
        story += GP._paras(over, st["corpo"])
    else:
        prop = _proprietario_nome(projeto)
        lev = projeto.get("levantamento") or {}
        met = " · ".join([x for x in [
            lev.get("equipamento"), (lev.get("metodo") or "").upper() or None,
            lev.get("sistema") or "SIRGAS 2000 / UTM", lev.get("data_levantamento")] if x])
        pecas = ", ".join(GU6.PECA_LABEL[k] for k in GU6.pecas_no_dossie(projeto)
                          if k not in ("capa", "sumario", "apresentacao")) or "as peças técnicas"
        story += GP._paras(
            f"O presente trabalho tem por objeto o georreferenciamento do lote urbano "
            f"denominado {projeto.get('denominacao_imovel') or ''}"
            + (f", de propriedade de {prop}" if prop else "")
            + f", situado em {projeto.get('endereco') or ''} — "
            f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}, "
            f"para fins de {GU6.finalidade_texto(projeto) or 'localização e situação'}.", st["corpo"])
        story += GP._paras(f"Metodologia: {met or 'levantamento topográfico georreferenciado'}.", st["corpo"])
        story += GP._paras(f"O presente dossiê é composto pelas seguintes peças: {pecas}.", st["corpo"])
        story += GP._paras(
            "Normas aplicadas: NBR 13133 (execução de levantamento topográfico); "
            "SIRGAS 2000 como sistema geodésico oficial (Res. PR nº 1/2015 – IBGE).", st["corpo"])
    story.append(Spacer(1, 10))
    story += _rt_flow(projeto, st, L)
    return PDF._build(story, cfg, "Apresentação", logo_bytes)


# Dispatcher de peça única
_GERADORES = {
    "apresentacao": apresentacao,
    "memorial_perimetrico": memorial_perimetrico,
    "memorial_situacao": memorial_situacao,
    "memorial_sucinto": memorial_sucinto,
    "memorial_area_construida": memorial_area_construida,
    "quadro_vertices": quadro_vertices,
    "mapa_lote": mapa_lote_gerado,
    "planta_quadra": planta_quadra_gerada,
    "art_trt": art_trt_peca,
}


def gerar_peca(tipo: str, projeto: dict, tema: str = "prime_i", logo_bytes=None) -> bytes:
    fn = _GERADORES.get(tipo)
    if not fn:
        raise ValueError(f"peça georref urbano desconhecida: {tipo}")
    return fn(projeto, tema, logo_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# Capa configurável (§7) — foto + imagem de localização lado a lado
# ──────────────────────────────────────────────────────────────────────────────
def _capa_cores(tema: str):
    if tema == "tradicional":
        return dict(bg=(255, 255, 255), titulo=CAPA.VERDE, accent=CAPA.DOURADO,
                    texto=(40, 40, 40), sub=CAPA.VERDE, card=(245, 245, 245), card_txt=(40, 40, 40))
    return dict(bg=CAPA.VERDE, titulo=CAPA.OFFWHITE, accent=CAPA.DOURADO,
                texto=CAPA.OFFWHITE, sub=CAPA.OFFWHITE, card=(8, 38, 24), card_txt=CAPA.OFFWHITE)


def _frame(canvas_img, box, raw_bytes):
    """Cola uma imagem recortada/emoldurada (cantos arredondados) num box (x0,y0,x1,y1)."""
    from PIL import Image, ImageDraw, ImageOps
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    try:
        im = ImageOps.fit(Image.open(io.BytesIO(raw_bytes)).convert("RGB"), (w, h), Image.LANCZOS)
    except Exception:  # noqa: BLE001
        return
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=22, fill=255)
    canvas_img.paste(im, (x0, y0), mask)
    ImageDraw.Draw(canvas_img, "RGBA").rounded_rectangle(
        [x0, y0, x1, y1], radius=22, outline=CAPA.DOURADO + (255,), width=3)


def compor_capa_georref(projeto: dict, foto_bytes=None, imagem_loc_bytes=None, tema="prime_i"):
    from PIL import Image, ImageDraw
    W, H = CAPA.A4_PX
    cores = _capa_cores(tema)
    cv = Image.new("RGB", (W, H), cores["bg"])
    d = ImageDraw.Draw(cv, "RGBA")
    M, cx = 90, W // 2

    d.text((M, 70), "ROMATEC CONSULTORIA TOTAL — ENGENHARIA E AGRIMENSURA",
           font=CAPA._font(19, serif=False), fill=cores["texto"])
    d.line([(M, 112), (W - M, 112)], fill=cores["accent"], width=3)

    CAPA._texto_centrado(d, cx, 150, "GEORREFERENCIAMENTO", CAPA._font(72, bold=True), cores["titulo"])
    CAPA._texto_centrado(d, cx, 240, "DE LOTE URBANO", CAPA._font(52, bold=True), cores["accent"] if tema != "tradicional" else cores["titulo"])
    # definição (editável) — auto-ajuste de fonte
    definicao = (projeto.get("composicao") or {}).get("definicao_capa") or GU6.definicao_capa_default(projeto.get("finalidade"))
    fsz = 26
    while fsz > 16 and d.textbbox((0, 0), definicao, font=CAPA._font(fsz, serif=False))[2] > (W - 2 * M):
        fsz -= 1
    CAPA._texto_centrado(d, cx, 322, definicao, CAPA._font(fsz, serif=False), cores["sub"])
    CAPA._texto_centrado(d, cx, 372, (projeto.get("denominacao_imovel") or "")[:70],
                         CAPA._font(24, bold=True), cores["titulo"])

    # bloco de imagens (foto esq. + localização dir.); só um → largura total
    iy0, iy1 = 440, 1000
    imgs = [b for b in (foto_bytes, imagem_loc_bytes) if b]
    if len(imgs) == 2:
        gap = 30
        halfw = (W - 2 * M - gap) // 2
        _frame(cv, (M, iy0, M + halfw, iy1), foto_bytes)
        _frame(cv, (M + halfw + gap, iy0, W - M, iy1), imagem_loc_bytes)
    elif len(imgs) == 1:
        _frame(cv, (M + 120, iy0, W - M - 120, iy1), imgs[0])

    # card de identificação
    cardy0 = 1060
    cardy1 = cardy0 + 320
    d.rounded_rectangle([M, cardy0, W - M, cardy1], radius=22,
                        fill=cores["card"] + (235,), outline=cores["accent"] + (255,), width=2)
    rt = projeto.get("responsavel_tecnico") or {}
    pares = [
        ("Proprietário", _proprietario_nome(projeto) or "—"),
        ("Endereço", (projeto.get("endereco") or "—")),
        ("Quadra / Lote", f"{projeto.get('quadra') or '—'} / {projeto.get('lote_resultante') or '—'}"),
        ("Área · Perímetro", f"{TX.m2(_area(projeto))} · {TX.metros(projeto.get('perimetro_m'))}"),
        ("Finalidade", (GU6.finalidade_texto(projeto) or 'localização e situação')),
        ("Resp. Técnico", f"{rt.get('nome') or ''} — {rt.get('conselho') or ''}"),
    ]
    yy = cardy0 + 26
    fk = CAPA._font(19, bold=True, serif=False)
    fv = CAPA._font(19, serif=False)
    for k, v in pares:
        d.text((M + 28, yy), f"{k}:", font=fk, fill=cores["accent"])
        d.text((M + 300, yy), str(v)[:60], font=fv, fill=cores["card_txt"])
        yy += 46

    d.line([(M, 1560), (W - M, 1560)], fill=cores["accent"], width=3)
    dt = datetime.now(timezone.utc)
    rod = (f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''} — "
           f"{dt.day:02d}/{dt.month:02d}/{dt.year}   ·   {rt.get('nome') or ''} — {rt.get('conselho') or ''}")
    CAPA._texto_centrado(d, cx, 1590, rod[:110], CAPA._font(17, serif=False), cores["sub"])
    return cv


def capa_georref_pdf(projeto: dict, foto_bytes=None, imagem_loc_bytes=None, tema="prime_i") -> bytes:
    cv = compor_capa_georref(projeto, foto_bytes, imagem_loc_bytes, tema)
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.drawImage(ImageReader(cv), 0, 0, width=A4[0], height=A4[1])
    c.showPage(); c.save()
    return buf.getvalue()


def capa_georref_png(projeto: dict, foto_bytes=None, imagem_loc_bytes=None, tema="prime_i") -> bytes:
    cv = compor_capa_georref(projeto, foto_bytes, imagem_loc_bytes, tema)
    buf = io.BytesIO(); cv.save(buf, "PNG")
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Dossiê montado pela COMPOSIÇÃO (§4)
# ──────────────────────────────────────────────────────────────────────────────
def _anexo_secao(titulo: str, lista_bytes):
    """Uma seção de anexo = páginas tituladas (imagem/PDF → página com título)."""
    out = []
    for raw in lista_bytes or []:
        try:
            out.append(DOSSIE.pagina_documento(raw, titulo))
        except Exception:  # noqa: BLE001
            out.append(raw)
    return out


def _concat(pdfs) -> bytes:
    """Merge simples de PDFs (usado quando a composição dispensa capa/sumário)."""
    w = PdfWriter()
    for raw in pdfs:
        if not raw:
            continue
        for r in DOSSIE._to_pdf_bytes(raw):
            for pg in r.pages:
                w.add_page(pg)
    out = io.BytesIO(); w.write(out)
    return out.getvalue()


def gerar_dossie(projeto: dict, uploads_bytes: dict, tema: str = "prime_i", logo_bytes=None) -> bytes:
    """Monta o dossiê na ORDEM da composição (peças ligadas + habilitadas).
    `uploads_bytes` = {tipo_upload: [bytes,...]} já baixado do R2 pela rota.
    SIMPLIFICADO (sem capa/sumário) → merge simples; senão capa+sumário+bookmarks."""
    ub = uploads_bytes or {}
    ordem = GU6.pecas_no_dossie(projeto)
    com_capa = "capa" in ordem
    com_sumario = "sumario" in ordem

    def _gerado(tp):
        return gerar_peca(tp, projeto, tema, logo_bytes)

    secoes = []  # (titulo, bytes|[bytes])
    for k in ordem:
        if k in ("capa", "sumario"):
            continue
        lbl = GU6.PECA_LABEL[k]
        if k == "imagem_localizacao":
            secoes.append((lbl, _anexo_secao(lbl, ub.get("imagem_localizacao"))))
        elif k == "mapa_lote":
            up = ub.get("mapa_coordenadas")
            secoes.append((lbl, _anexo_secao(lbl, up) if up else _gerado("mapa_lote")))
        elif k == "planta_quadra":
            up = ub.get("planta_quadra")
            secoes.append((lbl, _anexo_secao(lbl, up) if up else _gerado("planta_quadra")))
        elif k == "relatorio_fotografico":
            secoes.append((lbl, _anexo_secao(lbl, ub.get("foto_imovel"))))
        elif k == "art_trt":
            partes = [_gerado("art_trt")]
            partes += ub.get("art_trt_pdf") or []
            partes += ub.get("art_trt_boleto") or []
            secoes.append((lbl, partes))
        elif k == "matricula_anexa":
            secoes.append((lbl, _anexo_secao(lbl, ub.get("matricula_imovel"))))
        elif k == "docs_proprietario":
            docs = (ub.get("doc_proprietario_pf") or []) + (ub.get("doc_proprietario_pj") or [])
            secoes.append((lbl, _anexo_secao(lbl, docs)))
        elif k == "anexos_diversos":
            secoes.append((lbl, _anexo_secao(lbl, ub.get("outros"))))
        else:  # peças geradas (apresentacao, memoriais, quadro_vertices)
            secoes.append((lbl, _gerado(k)))
    # remove seções vazias (anexo sem bytes)
    secoes = [(t, b) for (t, b) in secoes if b]

    capa_pdf = None
    if com_capa:
        foto = (ub.get("foto_imovel") or [None])[0]
        img_loc = (ub.get("imagem_localizacao") or [None])[0]
        capa_pdf = capa_georref_pdf(projeto, foto, img_loc, tema)

    if com_capa and com_sumario:
        return DOSSIE.gerar_dossie_ordenado(projeto, secoes, capa_pdf=capa_pdf)
    # sem sumário (ou sem capa): merge simples, capa primeiro se houver
    pdfs = ([capa_pdf] if capa_pdf else []) + [b for (_t, b) in secoes]
    return _concat(pdfs)
