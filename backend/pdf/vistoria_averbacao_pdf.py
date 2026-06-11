# @module pdf.vistoria_averbacao_pdf — PDF da Vistoria de Obra para Averbação
"""
Gera o PDF da Vistoria de Obra para Averbação reaproveitando o template/estilos do
TVI (cabeçalho/rodapé/marca d'água) e adicionando os três quadros específicos:
  - Quadro de Confronto de Áreas (com célula de divergência colorida pela faixa);
  - Quadro de Etapas (Etapa | Peso | % Executado) + linha CONCLUSÃO GERAL;
  - Quadro Documental (Documento | Base legal | Situação) OK verde / PEND âmbar / NA cinza.
Todo parágrafo é justificado (TA_JUSTIFY). Galeria fotográfica com GPS reaproveitada.
"""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, PageBreak, Spacer, Table, TableStyle

from pdf.tvi_pdf import (
    _TVIDoc, _make_styles, _spacer, _section, _divider, _build_fotos,
    _build_assinatura, _fetch_logo, GREEN, GOLD, WHITE, LIGHT_GREEN, DARK,
)
from models.averbacao import (
    ETAPAS_OBRA, DOCS_AVERBACAO, SISTEMAS_AVERBACAO, PESOS_ETAPAS,
    faixa_divergencia, calcular_averbacao,
)
from services.vistoria_averbacao_relatorio import gerar_secoes_averbacao

_ETAPA_NOME = {e["id"]: e["nome"] for e in ETAPAS_OBRA}
_DOC_NOME = {d["id"]: d["nome"] for d in DOCS_AVERBACAO}
_DOC_BASE = {d["id"]: d["base"] for d in DOCS_AVERBACAO}

# Cores de célula por estado.
FAIXA_BG = {
    "verde": colors.HexColor("#E8F5E9"),
    "ambar": colors.HexColor("#FFF3E0"),
    "vermelho": colors.HexColor("#FDECEC"),
}
FAIXA_FG = {
    "verde": colors.HexColor("#1E6B38"),
    "ambar": colors.HexColor("#A05C0A"),
    "vermelho": colors.HexColor("#B42318"),
}
SIT_BG = {
    "OK": colors.HexColor("#E8F5E9"),
    "PEND": colors.HexColor("#FFF3E0"),
    "NA": colors.HexColor("#F1F1F1"),
}
SIT_LABEL = {"OK": "OK", "PEND": "PENDENTE", "NA": "N/A", "PENDENTE_AVALIACAO": "—"}


def _num(v, casas: int = 2) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{f:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _so_residencial(av: dict) -> bool:
    return (av.get("destinacao") or "residencial") == "residencial"


def _quadro_confronto(av: dict, styles: dict) -> list:
    conf = av.get("confronto") or {}
    div_pct = conf.get("divergencia_pct")
    faixa = faixa_divergencia(div_pct)
    header = ["Projeto", "Executada", "Matrícula", "Divergência m²", "Divergência %"]
    row = [
        _num(conf.get("area_projeto_m2")),
        _num(conf.get("area_medida_m2")),
        _num(conf.get("area_matricula_m2")) if conf.get("area_matricula_m2") not in (None, "") else "—",
        _num(conf.get("divergencia_m2")) if conf.get("divergencia_m2") is not None else "—",
        (f"{_num(div_pct)}%" if div_pct is not None else "—"),
    ]
    tbl = Table([header, row], colWidths=[3.3 * cm, 3.3 * cm, 3.3 * cm, 3.3 * cm, 3.3 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        # célula de divergência % colorida pela faixa:
        ("BACKGROUND", (4, 1), (4, 1), FAIXA_BG.get(faixa)),
        ("TEXTCOLOR", (4, 1), (4, 1), FAIXA_FG.get(faixa)),
        ("FONTNAME", (4, 1), (4, 1), "Helvetica-Bold"),
    ]))
    return [Paragraph("Quadro de Confronto de Áreas", styles["label"]), _spacer(0.15), tbl, _spacer(0.3)]


def _quadro_etapas(av: dict, styles: dict) -> list:
    etapas = {e.get("etapa_id"): e.get("percentual", 0) for e in (av.get("etapas") or []) if isinstance(e, dict)}
    rows = [["Etapa", "Peso", "% Executado"]]
    for e in ETAPAS_OBRA:
        rows.append([e["nome"], str(e["peso"]), f"{int(etapas.get(e['id'], 0))}%"])
    rows.append(["CONCLUSÃO GERAL", "100", f"{_num(av.get('conclusao_geral_pct'), 1)}%"])
    tbl = Table(rows, colWidths=[9.0 * cm, 3.0 * cm, 4.5 * cm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT_GREEN]),
        ("BACKGROUND", (0, -1), (-1, -1), GOLD),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [Paragraph("Quadro de Etapas (NBR 12721 simplificado)", styles["label"]), _spacer(0.15), tbl, _spacer(0.3)]


def _quadro_documental(av: dict, styles: dict) -> list:
    docs = {d.get("doc_id"): d for d in (av.get("documentos") or []) if isinstance(d, dict)}
    so_res = _so_residencial(av)
    rows = [["Documento", "Base legal", "Situação"]]
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    r = 1
    for d in DOCS_AVERBACAO:
        if d.get("comercial") and so_res:
            continue
        item = docs.get(d["id"]) or {}
        sit = item.get("situacao", "PENDENTE_AVALIACAO")
        rows.append([d["nome"], d["base"], SIT_LABEL.get(sit, "—")])
        if sit in SIT_BG:
            style_cmds.append(("BACKGROUND", (2, r), (2, r), SIT_BG[sit]))
            style_cmds.append(("FONTNAME", (2, r), (2, r), "Helvetica-Bold"))
        r += 1
    tbl = Table(rows, colWidths=[8.5 * cm, 5.0 * cm, 3.0 * cm], repeatRows=1)
    tbl.setStyle(TableStyle(style_cmds))
    return [Paragraph("Quadro Documental para Averbação", styles["label"]), _spacer(0.15), tbl, _spacer(0.3)]


def _cover(vistoria: dict, av: dict, logo_bytes, styles: dict) -> list:
    story = []
    banner = Table([[Paragraph("VISTORIA TÉCNICA DE OBRA PARA AVERBAÇÃO", styles["title"])]], colWidths=[16.5 * cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 14), ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(_spacer(0.6))
    story.append(banner)
    story.append(_spacer(0.5))
    numero = vistoria.get("numero_tvi") or "TVI-0000/0000"
    story.append(Paragraph(f"<b>Nº {numero}</b>", ParagraphStyle(
        "av_num", fontName="Helvetica-Bold", fontSize=14, alignment=TA_CENTER, textColor=GREEN, spaceAfter=4)))
    if vistoria.get("imovel_endereco"):
        story.append(Paragraph(vistoria["imovel_endereco"], ParagraphStyle(
            "av_end", fontName="Helvetica", fontSize=12, alignment=TA_CENTER, textColor=DARK, spaceAfter=6)))
    meta = []
    if vistoria.get("imovel_matricula"):
        meta.append(["Matrícula:", vistoria["imovel_matricula"]])
    meta.append(["Destinação:", (av.get("destinacao") or "residencial").capitalize()])
    meta.append(["Conclusão geral:", f"{_num(av.get('conclusao_geral_pct'), 1)}%"])
    meta.append(["Data:", vistoria.get("data_vistoria") or datetime.utcnow().strftime("%d/%m/%Y")])
    t = Table(meta, colWidths=[5 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11), ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(_spacer(0.4))
    story.append(t)
    story.append(_spacer(0.8))
    story.append(_divider())
    story.append(Paragraph("Lei 6.015/73 (arts. 167, II e 246) · Lei 8.212/91 · NBR 16747 · NBR 12721",
                           ParagraphStyle("av_brand", fontName="Helvetica", fontSize=8.5,
                                          alignment=TA_CENTER, textColor=GOLD, spaceBefore=6)))
    story.append(PageBreak())
    return story


def generate_averbacao_pdf(vistoria: dict, user: dict, photos: list | None = None,
                           signatures: list | None = None) -> bytes:
    """Gera o PDF da Vistoria de Obra para Averbação. Retorna bytes."""
    av = calcular_averbacao(dict(vistoria.get("averbacao") or {}))
    vistoria = dict(vistoria)
    vistoria["averbacao"] = av

    buf = io.BytesIO()
    logo = _fetch_logo()
    doc = _TVIDoc(buf, logo_bytes=logo)
    doc._tvi_number = vistoria.get("numero_tvi") or ""
    doc._company_name = user.get("company", "") or "RomaTec Consultoria Imobiliária"
    styles = _make_styles()

    story: list = []
    story += _cover(vistoria, av, logo, styles)

    secoes = gerar_secoes_averbacao(vistoria)
    for i, (titulo, corpo) in enumerate(secoes, 1):
        story += _section(styles, f"{i}. {titulo}")
        for par in (corpo or "").split("\n"):
            if par.strip():
                story.append(Paragraph(par.strip(), styles["body"]))
        # Insere o quadro logo após a seção correspondente.
        if titulo == "CONFRONTO DE ÁREAS":
            story.append(_spacer(0.2)); story += _quadro_confronto(av, styles)
        elif titulo == "ESTÁGIO DA OBRA":
            story.append(_spacer(0.2)); story += _quadro_etapas(av, styles)
        elif titulo == "DOCUMENTAÇÃO PARA AVERBAÇÃO":
            story.append(_spacer(0.2)); story += _quadro_documental(av, styles)
        story.append(_spacer(0.3))

    story += _build_fotos(photos or [], styles)
    story += _build_assinatura(vistoria, signatures or [], styles)

    doc.build(story)
    return buf.getvalue()
