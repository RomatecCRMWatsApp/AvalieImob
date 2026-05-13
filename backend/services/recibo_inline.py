# @module services.recibo_inline — Gerador minimalista de recibo de honorários
# (Fallback enquanto o módulo completo pdf/recibo_pdf.py não estiver pronto.)
"""
Gera um PDF simples de recibo de honorários baseado nos dados do PTAM + perfil
do avaliador. Padrão visual sóbrio, com logo Romatec AvalieImob.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional


def _format_brl(valor: float) -> str:
    s = f"{valor:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _valor_por_extenso(valor: float) -> str:
    """Conversor simplificado de valor monetário pra extenso PT-BR."""
    try:
        from num2words import num2words
        reais = int(valor)
        centavos = int(round((valor - reais) * 100))
        ext = num2words(reais, lang="pt_BR")
        out = f"{ext} reais"
        if centavos:
            out += f" e {num2words(centavos, lang='pt_BR')} centavos"
        return out
    except Exception:
        return ""


def gerar_recibo_pdf(
    *,
    ptam: dict,
    user: dict,
    perfil: dict,
    valor: float,
    forma_pagamento: str = "PIX",
    data_pagamento: Optional[str] = None,
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4

    # ── Cabeçalho ──────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#1B4D1B"))  # DARK_GREEN
    c.rect(0, page_h - 35 * mm, page_w, 35 * mm, fill=1, stroke=0)

    c.setFillColor(colors.HexColor("#D4A830"))  # GOLD
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, page_h - 18 * mm, "RECIBO DE HONORÁRIOS")

    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    empresa = perfil.get("empresa_nome") or user.get("company") or "Romatec AvalieImob"
    cnpj = perfil.get("empresa_cnpj") or ""
    c.drawString(20 * mm, page_h - 26 * mm, f"{empresa}" + (f" — CNPJ {cnpj}" if cnpj else ""))
    end = perfil.get("endereco_escritorio") or ""
    cidade_uf = ""
    if perfil.get("cidade") and perfil.get("uf"):
        cidade_uf = f"{perfil['cidade']}/{perfil['uf']}"
    c.drawString(20 * mm, page_h - 31 * mm, " · ".join(filter(None, [end, cidade_uf])))

    # ── Número e data do recibo (lateral direita) ─────────────────────
    numero_ptam = ptam.get("numero_ptam", "")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(page_w - 20 * mm, page_h - 18 * mm, f"PTAM {numero_ptam}")
    c.setFont("Helvetica", 9)
    data_str = data_pagamento or datetime.utcnow().strftime("%d/%m/%Y")
    c.drawRightString(page_w - 20 * mm, page_h - 26 * mm, f"Data: {data_str}")

    # ── Corpo ─────────────────────────────────────────────────────────
    cursor_y = page_h - 55 * mm

    c.setFillColor(colors.HexColor("#111827"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(20 * mm, cursor_y, _format_brl(valor))
    cursor_y -= 12 * mm

    valor_ext = _valor_por_extenso(valor)
    pagador = ptam.get("solicitante") or ptam.get("solicitante_nome") or "—"
    pagador_doc = ptam.get("solicitante_cpf_cnpj") or ""

    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#374151"))
    texto = (
        f"Recebi de {pagador}"
        + (f" (CPF/CNPJ {pagador_doc})" if pagador_doc else "")
        + f", a importância de {_format_brl(valor)}"
        + (f" ({valor_ext})" if valor_ext else "")
        + ", referente aos honorários técnicos pelos serviços de avaliação imobiliária "
        + f"objeto do PTAM nº {numero_ptam}, conforme NBR 14.653."
    )

    # quebra simples
    from textwrap import wrap
    linhas = wrap(texto, width=95)
    for linha in linhas:
        c.drawString(20 * mm, cursor_y, linha)
        cursor_y -= 5 * mm

    cursor_y -= 6 * mm

    # ── Imóvel avaliado ───────────────────────────────────────────────
    imovel = ptam.get("property_label") or ptam.get("property_address") or ""
    if imovel:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, cursor_y, "Imóvel avaliado:")
        c.setFont("Helvetica", 10)
        c.drawString(50 * mm, cursor_y, imovel[:80])
        cursor_y -= 6 * mm

    # ── Forma de pagamento ────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, cursor_y, "Forma de pagamento:")
    c.setFont("Helvetica", 10)
    c.drawString(60 * mm, cursor_y, forma_pagamento)
    cursor_y -= 12 * mm

    # ── Cidade, data e assinatura ─────────────────────────────────────
    cidade_emissao = (perfil.get("cidade") or "") + (
        "/" + perfil.get("uf") if perfil.get("uf") else ""
    )
    rodape = f"{cidade_emissao}, {data_str}." if cidade_emissao else f"{data_str}."
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, cursor_y, rodape)
    cursor_y -= 25 * mm

    # Linha
    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    c.line(60 * mm, cursor_y, page_w - 60 * mm, cursor_y)
    cursor_y -= 5 * mm

    nome = perfil.get("nome_completo") or user.get("name") or "Avaliador"
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(page_w / 2, cursor_y, nome)
    cursor_y -= 4 * mm

    cpf = perfil.get("cpf") or ""
    registros = perfil.get("registros") or []
    sub = ""
    if registros:
        r0 = registros[0]
        sub = f"{r0.get('tipo','')} {r0.get('numero','')}".strip()
    if cpf:
        sub = (sub + " · " if sub else "") + f"CPF {cpf}"
    if sub:
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#6B7280"))
        c.drawCentredString(page_w / 2, cursor_y, sub)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
