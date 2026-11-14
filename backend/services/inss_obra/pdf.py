# @module services.inss_obra.pdf — PDF da simulação do INSS de obra (para o cliente).
#
# Mostra a memória de cálculo na mesma ordem do SERO e o aviso de que é SIMULAÇÃO.
# Cabeçalho verde com o lockup da marca (ou o logo próprio do usuário, white-label).
from __future__ import annotations

import io
from decimal import Decimal as D

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from pdf.brand_seal import draw_header_lockup
from pdf.templates.resilient import ResilientSimpleDocTemplate
from services.inss_obra import params as P

VERDE = colors.HexColor("#0C3320")
OURO = colors.HexColor("#C9A84C")
CINZA = colors.HexColor("#F3F4F1")


def _brl(v) -> str:
    s = f"{D(str(v)):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _num(v, casas=2) -> str:
    s = f"{D(str(v)):,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v) -> str:
    p = D(str(v)) * 100
    txt = f"{p:.2f}".rstrip("0").rstrip(".")
    return txt.replace(".", ",") + "%"


def _data(iso: str | None) -> str:
    if not iso:
        return "—"
    a, m, d = str(iso)[:10].split("-")
    return f"{d}/{m}/{a}"


def _nome_param(k: str) -> str:
    if k.startswith("equivalencia:"):
        return "percentual de equivalência (" + P.DESTINACOES.get(k.split(":", 1)[1], k).lower() + ")"
    return {"aliquotas": "divisão das alíquotas por código de receita",
            "usinado": "percentual do usinado por UF"}.get(k, k)


def _estilos():
    base = ParagraphStyle("b", fontName="Helvetica", fontSize=9, leading=12, alignment=TA_JUSTIFY)
    return {
        "body": base,
        "small": ParagraphStyle("s", parent=base, fontSize=7.5, leading=10, textColor=colors.HexColor("#555555")),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=VERDE,
                            spaceBefore=8, spaceAfter=4),
        "title": ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=VERDE),
        "cell": ParagraphStyle("c", fontName="Helvetica", fontSize=7.5, leading=9.5),
        "aviso": ParagraphStyle("a", parent=base, fontName="Helvetica-Bold", textColor=colors.HexColor("#8A1C1C")),
    }


def _tabela(linhas, larguras, header=True, destaque_ultima=False):
    t = Table(linhas, colWidths=larguras, repeatRows=1 if header else 0)
    st = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8CEC9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), VERDE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
        for i in range(1, len(linhas)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), CINZA))
    if destaque_ultima:
        st += [("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
               ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFE6C8"))]
    t.setStyle(TableStyle(st))
    return t


def gerar_pdf(obra: dict, sim: dict, logo_bytes: bytes | None = None, autor: dict | None = None) -> bytes:
    s = _estilos()
    buf = io.BytesIO()
    W, H = A4
    numero = obra.get("numero") or ""

    def _on_page(c, doc):
        c.saveState()
        c.setFillColor(VERDE)
        c.rect(0, H - 2.2 * cm, W, 2.2 * cm, fill=1, stroke=0)
        c.setFillColor(OURO)
        c.rect(0, H - 2.2 * cm - 1.2, W, 1.2, fill=1, stroke=0)
        draw_header_lockup(c, 1.6 * cm, H - 1.1 * cm, mark=10 * mm, light=True,
                           tagline="INSS DE OBRA · AFERIÇÃO", logo_bytes=logo_bytes)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.white)
        c.drawRightString(W - 1.6 * cm, H - 1.25 * cm, f"{numero}  ·  Pág. {doc.page}")
        c.setFillColor(colors.HexColor("#8A1C1C"))
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(W / 2, 1.0 * cm,
                            "SIMULAÇÃO — não substitui a aferição oficial no SERO/e-CAC")
        c.restoreState()

    doc = ResilientSimpleDocTemplate(buf, pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                                     topMargin=2.9 * cm, bottomMargin=1.8 * cm,
                                     title=f"Simulação INSS de obra {numero}")
    largura = W - 3.2 * cm
    st = []
    st.append(Paragraph("Simulação do INSS da obra (aferição indireta)", s["title"]))
    st.append(Spacer(1, 4))
    st.append(Paragraph(sim["aviso"], s["aviso"]))
    st.append(Spacer(1, 6))

    st.append(Paragraph("1. Identificação", s["h"]))
    ent = sim["entrada"]
    resp = "Pessoa física" if ent["responsavel"] == "PF" else "Pessoa jurídica"
    ident = [
        ["Cliente / responsável", obra.get("cliente_nome") or "—", "CPF/CNPJ", obra.get("cpf_cnpj") or "—"],
        ["Responsável pela obra", resp, "CNO", obra.get("cno") or "a inscrever"],
        ["Endereço", Paragraph(obra.get("endereco") or "—", s["cell"]), "Município/UF",
         f"{obra.get('municipio') or '—'}/{ent['uf']}"],
        ["Início da obra", _data(ent["data_inicio"]), "Fim da obra", _data(ent["data_fim"])],
        ["Data da simulação", _data(ent["data_afericao"]), "Competência", ent["competencia_afericao"]],
    ]
    t = Table(ident, colWidths=[3.6 * cm, 5.6 * cm, 2.6 * cm, largura - 11.8 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8CEC9")),
        ("BACKGROUND", (0, 0), (0, -1), CINZA), ("BACKGROUND", (2, 0), (2, -1), CINZA),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    st.append(t)

    st.append(Paragraph("2. Áreas, custo da obra (COD) e remuneração da mão de obra (RMT)", s["h"]))
    cab = ["#", "Destinação / categoria", "Área", "m²", "Red.", "m² cálc.", "VAU", "COD",
           "% M.O.", "% cat.", "F. soc.", "RMT"]
    lin = [cab]
    for l in sim["linhas"]:
        desc = f"{P.DESTINACOES[l['destinacao']]}<br/>{P.CATEGORIAS[l['categoria']]} · {P.TIPOS[l['tipo']]}"
        if l.get("descricao"):
            desc += f"<br/><i>{l['descricao']}</i>"
        classe = {"principal": "Principal", "complementar_coberta": "Compl. cob.",
                  "complementar_descoberta": "Compl. desc."}[l["classe"]]
        lin.append([l["n"], Paragraph(desc, s["cell"]), classe, _num(l["area_m2"]),
                    _pct(l["reducao_area"]), _num(l["area_calculo"]), _num(l["vau"]),
                    _num(l["cod"]), _pct(l["pct_mao_de_obra"]),
                    _pct(D(l["pct_categoria"]) * D(l["pct_destinacao"])),
                    _pct(l["fator_social"]), _num(l["rmt"])])
    lin.append(["", "Total", "", "", "", "", "", _num(sim["cod_total"]), "", "", "", _num(sim["rmt_total"])])
    st.append(_tabela(lin, [0.5 * cm, 3.7 * cm, 1.5 * cm, 1.2 * cm, 1.0 * cm, 1.4 * cm, 1.4 * cm,
                            2.0 * cm, 1.1 * cm, 1.0 * cm, 1.1 * cm, largura - 15.9 * cm],
                      destaque_ultima=True))

    st.append(Paragraph("3. Decadência, créditos e base de cálculo", s["h"]))
    dec = sim["decadencia"]
    resumo = [
        ["Item", "Valor"],
        ["RMT total", _brl(sim["rmt_total"])],
        [f"Meses da obra: {dec['meses_total']} · decadentes: {dec['meses_decadentes']}",
         f"{_pct(dec['percentual_nao_decadente'])} não decadente"],
        ["RMT não decadente", _brl(sim["rmt_nao_decadente"])],
        ["(−) Crédito por concreto/argamassa usinada ou massa asfáltica",
         _brl(sim["usinado"]["credito"]) if sim["usinado"]["aplicado"] else "não informado"],
        ["Base de cálculo das contribuições", _brl(sim["base_calculo"])],
    ]
    st.append(_tabela(resumo, [largura - 5 * cm, 5 * cm], destaque_ultima=True))

    st.append(Paragraph("4. Contribuições a pagar (estimativa)", s["h"]))
    deb = [["Cód. receita", "Contribuição", "Alíquota", "Valor"]]
    for d in sim["debitos"]:
        deb.append([d.get("codigo_receita") or d["codigo"], d["nome"], _pct(d["aliquota"]), _brl(d["valor"])])
    deb.append(["", "TOTAL ESTIMADO", "36,8%", _brl(sim["total"])])
    st.append(_tabela(deb, [2.2 * cm, largura - 7.7 * cm, 2.2 * cm, 3.3 * cm], destaque_ultima=True))

    if sim.get("alertas"):
        st.append(Paragraph("5. Observações", s["h"]))
        for a in sim["alertas"]:
            st.append(Paragraph("• " + a, s["body"]))

    st.append(Paragraph("Metodologia e limites", s["h"]))
    st.append(Paragraph(
        f"Cálculo pela metodologia do Capítulo III do {sim['versao_manual']} (Receita Federal): "
        "área × percentual de equivalência ou redução das áreas complementares × VAU = custo da obra; "
        "× percentual de mão de obra, de categoria, de destinação e fator social (pessoa física) = RMT; "
        "ajuste pelo período não decadente; dedução do crédito do usinado; alíquotas por contribuição. "
        "O VAU usado foi informado pelo usuário a partir da consulta no SERO. "
        "Não inclui crédito de remuneração declarada (eSocial/GFIP), fator de ajuste, notas de pré-moldado "
        "nem desoneração. Valores sujeitos a juros e multa se pagos após o vencimento.", s["small"]))
    if sim.get("parametros_a_conferir"):
        st.append(Spacer(1, 3))
        st.append(Paragraph("Parâmetros desta simulação ainda em conferência com o PDF oficial do Manual: "
                            + ", ".join(_nome_param(k) for k in sim["parametros_a_conferir"]) + ".", s["small"]))
    if autor and autor.get("nome"):
        st.append(Spacer(1, 18))
        st.append(Paragraph(f"<b>{autor['nome']}</b><br/>{autor.get('registros') or ''}", s["body"]))
    doc.build(st, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()
