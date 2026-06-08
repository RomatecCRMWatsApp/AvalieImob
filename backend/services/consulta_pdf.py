# @module services.consulta_pdf — Gera PDF do resultado da Consulta CNPJ (Receita Federal)
"""PDF profissional do cartão de consulta CNPJ, com cabeçalho da Romatec/avaliador,
tabela de dados e rodapé com a fonte. Usado para visualizar, baixar e enviar via
WhatsApp/Telegram a partir do widget de Consulta Rápida."""
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

VERDE = colors.HexColor("#0B6E4F")
VERDE_CLR = colors.HexColor("#EAF4EF")
CINZA = colors.HexColor("#9CA3AF")
PRETO = colors.HexColor("#111827")
VERM = colors.HexColor("#C62828")


def _fmt_moeda(v) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return ""
    if n == 0:
        return ""
    return "R$ " + f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _esc(s) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fonte_label(fonte: str) -> str:
    return {
        "prospectabr": "ProspectaBR (base local) — Receita Federal",
        "cnpjws": "CNPJ.ws — Receita Federal",
        "receitaws": "ReceitaWS — Receita Federal",
    }.get(fonte or "", "Receita Federal")


def gerar_pdf_cnpj(dados: dict, perfil: dict | None = None) -> bytes:
    """Recebe o dict normalizado da consulta CNPJ e retorna os bytes do PDF."""
    dados = dados or {}
    perfil = perfil or {}
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title=f"Consulta CNPJ {dados.get('cnpj', '')}",
    )
    base = getSampleStyleSheet()
    sTitulo = ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold",
                             fontSize=15, textColor=VERDE, spaceAfter=2)
    sSub = ParagraphStyle("s", parent=base["Normal"], fontName="Helvetica",
                          fontSize=9, textColor=CINZA, spaceAfter=2)
    sLabel = ParagraphStyle("lbl", fontName="Helvetica-Bold", fontSize=9,
                            textColor=colors.white, leading=11)
    sCell = ParagraphStyle("cell", fontName="Helvetica", fontSize=9,
                           textColor=PRETO, leading=12)
    sFoot = ParagraphStyle("ft", fontName="Helvetica", fontSize=7.5,
                           textColor=CINZA, leading=10)

    story = []

    # ── Cabeçalho do emitente ──
    nome_emit = (perfil.get("empresa_nome") or perfil.get("nome_completo")
                 or "ROMATEC CONSULTORIA TOTAL")
    regs = perfil.get("registros") or []
    reg_txt = "  |  ".join(
        f"{r.get('tipo', '')} {r.get('numero', '')}".strip()
        for r in regs if isinstance(r, dict) and r.get("numero")
    )
    story.append(Paragraph(_esc(nome_emit), ParagraphStyle(
        "emit", fontName="Helvetica-Bold", fontSize=10, textColor=PRETO)))
    if reg_txt:
        story.append(Paragraph(_esc(reg_txt), sSub))
    story.append(Spacer(1, 8))

    # ── Título ──
    story.append(Paragraph("Consulta de CNPJ", sTitulo))
    story.append(Paragraph("Cadastro Nacional da Pessoa Jurídica — Receita Federal do Brasil", sSub))
    story.append(Spacer(1, 10))

    # ── Identificação principal ──
    razao = _esc(dados.get("razao_social"))
    fantasia = _esc(dados.get("nome_fantasia"))
    situacao = (dados.get("situacao") or "").strip()
    sit_hex = "#0B6E4F" if "ativ" in situacao.lower() else "#C62828"
    cabec = [
        [Paragraph(f"<b>{razao}</b>", ParagraphStyle("rz", fontName="Helvetica-Bold",
                                                     fontSize=12, textColor=PRETO, leading=15)),
         Paragraph(f'<b><font color="{sit_hex}">{_esc(situacao) or "—"}</font></b>',
                   ParagraphStyle("st", fontName="Helvetica-Bold", fontSize=10,
                                  alignment=2, leading=14))],
    ]
    tcab = Table(cabec, colWidths=[12.4 * cm, 4.6 * cm])
    tcab.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(tcab)
    if fantasia:
        story.append(Paragraph(f'"{fantasia}"', ParagraphStyle(
            "fan", fontName="Helvetica-Oblique", fontSize=9.5, textColor=CINZA)))
    story.append(Paragraph(_esc(dados.get("cnpj")), ParagraphStyle(
        "cnpj", fontName="Courier", fontSize=10, textColor=PRETO, spaceBefore=2)))
    story.append(Spacer(1, 10))

    # ── Tabela de dados ──
    endereco = ", ".join(x for x in [
        dados.get("logradouro"), dados.get("numero"), dados.get("bairro"),
        dados.get("municipio"), dados.get("uf"), dados.get("cep"),
    ] if x)
    linhas = [
        ("Data de Abertura", dados.get("data_abertura")),
        ("Natureza Jurídica", dados.get("natureza_juridica")),
        ("Porte", dados.get("porte")),
        ("Capital Social", _fmt_moeda(dados.get("capital_social"))),
        ("Atividade Principal", dados.get("atividade_principal")),
        ("Endereço", endereco),
        ("Telefone", dados.get("telefone")),
        ("E-mail", dados.get("email")),
    ]
    linhas = [(lb, str(vl).strip()) for lb, vl in linhas if vl and str(vl).strip()]
    data = [[Paragraph(_esc(lb), sLabel), Paragraph(_esc(vl), sCell)] for lb, vl in linhas]
    if data:
        t = Table(data, colWidths=[4.8 * cm, 12.2 * cm])
        style = TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), VERDE),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ])
        for i in range(len(data)):
            style.add("BACKGROUND", (1, i), (1, i), VERDE_CLR if i % 2 else colors.white)
        t.setStyle(style)
        story.append(t)

    # ── Rodapé ──
    story.append(Spacer(1, 14))
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    fonte = _fonte_label(dados.get("fonte"))
    story.append(Paragraph(
        f"Fonte: {_esc(fonte)}.<br/>"
        f"Documento gerado por {_esc(nome_emit)} via AvalieImob em {agora}. "
        f"Os dados refletem a base consultada no momento da emissão e têm caráter informativo.",
        sFoot,
    ))

    doc.build(story)
    return buf.getvalue()
