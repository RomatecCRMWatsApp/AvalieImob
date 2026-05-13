# @module pdf.recibo_pdf — Gerador de PDF de Recibo padrão Romatec AvalieImob
"""
Gera PDF de recibo independente (não vinculado a PTAM) com layout profissional:
  - Cabeçalho verde escuro com gradient + logo + dados do emitente
  - Bloco "RECIBO Nº XXX" destacado em dourado
  - Valor em destaque grande
  - Texto formal "Recebi de ... a importância de ..."
  - Imóvel/serviço descritos
  - Forma de pagamento e data
  - Linha de assinatura com nome+cargo+registro
  - Rodapé com dados bancários (PIX, etc.)

Cores:
  - DARK_GREEN  = #1B4D1B (header)
  - GOLD        = #D4A830 (destaques)
  - GRAY_TEXT   = #374151

Compatível com python-reportlab. Aceita logo via image_id (busca via uploads).
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("romatec")


DARK_GREEN = "#1B4D1B"
GOLD = "#D4A830"


def _format_brl(valor: float) -> str:
    s = f"{valor:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _valor_por_extenso(valor: float) -> str:
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


def _format_data_br(data_iso: Optional[str]) -> str:
    """ISO date string -> dd/mm/aaaa. Se vazio, hoje."""
    try:
        if data_iso:
            return datetime.fromisoformat(data_iso[:10]).strftime("%d/%m/%Y")
    except Exception:
        pass
    return datetime.utcnow().strftime("%d/%m/%Y")


def _format_documento(doc: str) -> str:
    """Aplica máscara CPF ou CNPJ baseado no número de dígitos."""
    if not doc:
        return ""
    digits = "".join(c for c in doc if c.isdigit())
    if len(digits) == 11:
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    if len(digits) == 14:
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
    return doc


def gerar_recibo_pdf(
    *,
    recibo: dict,
    user: Optional[dict] = None,
    perfil: Optional[dict] = None,
    logo_bytes: Optional[bytes] = None,
) -> bytes:
    """Gera PDF do recibo. recibo é o dict do MongoDB ou Pydantic dict."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    user = user or {}
    perfil = perfil or {}

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4

    # ─── Header verde com faixa dourada inferior ───────────────────────
    header_h = 38 * mm
    c.setFillColor(colors.HexColor(DARK_GREEN))
    c.rect(0, page_h - header_h, page_w, header_h, fill=1, stroke=0)
    # Faixa dourada de 2mm na base do header
    c.setFillColor(colors.HexColor(GOLD))
    c.rect(0, page_h - header_h - 2 * mm, page_w, 2 * mm, fill=1, stroke=0)

    # Logo à esquerda (custom do usuário OU logo padrão AvalieImob como fallback)
    cursor_x = 18 * mm
    has_logo_image = False
    if logo_bytes:
        try:
            c.drawImage(
                ImageReader(io.BytesIO(logo_bytes)),
                cursor_x, page_h - header_h + 4 * mm,
                width=32 * mm, height=32 * mm,
                preserveAspectRatio=True, mask="auto",
            )
            cursor_x += 36 * mm
            has_logo_image = True
        except Exception as e:
            logger.warning("Falha ao desenhar logo do recibo: %s", e)

    # Marca verbal Romatec — só quando NÃO tem logo de imagem (evita redundância)
    if not has_logo_image:
        c.setFillColor(colors.HexColor(GOLD))
        c.setFont("Helvetica-Bold", 22)
        c.drawString(cursor_x, page_h - 18 * mm, "ROMATEC")
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 9)
        c.drawString(cursor_x, page_h - 23 * mm, "AVALIEIMOB · PTAM · LAUDOS")

    # Nome do emitente + documento
    emitente_nome = recibo.get("emitente_nome") or perfil.get("empresa_nome") or perfil.get("nome_completo") or user.get("name") or ""
    emitente_doc = _format_documento(recibo.get("emitente_documento") or perfil.get("empresa_cnpj") or perfil.get("cpf") or "")
    perfil_emit = recibo.get("emitente_perfil", "PJ")
    rotulo_doc = "CNPJ" if perfil_emit == "PJ" else "CPF"

    c.setFont("Helvetica-Bold", 9)
    c.drawString(cursor_x, page_h - 30 * mm, emitente_nome[:60])
    if emitente_doc:
        c.setFont("Helvetica", 8)
        c.drawString(cursor_x, page_h - 34 * mm, f"{rotulo_doc}: {emitente_doc}")

    # Número do recibo + data (lateral direita)
    numero = recibo.get("numero") or "(rascunho)"
    data_emissao = _format_data_br(recibo.get("data_pagamento") or recibo.get("created_at"))

    c.setFillColor(colors.HexColor(GOLD))
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(page_w - 18 * mm, page_h - 18 * mm, numero)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    c.drawRightString(page_w - 18 * mm, page_h - 24 * mm, f"Emissão: {data_emissao}")
    validade = recibo.get("validade_dias", 7)
    c.drawRightString(page_w - 18 * mm, page_h - 28 * mm, f"Válido por {validade} dias")

    # ─── Título "RECIBO" centralizado ──────────────────────────────────
    cursor_y = page_h - header_h - 14 * mm

    c.setFillColor(colors.HexColor(DARK_GREEN))
    c.setFont("Helvetica-Bold", 22)
    from models.recibo import TIPOS_RECIBO
    tipo_label = TIPOS_RECIBO.get(recibo.get("tipo", "personalizado"), {}).get("label", "Recibo")
    titulo = f"RECIBO — {tipo_label.upper()}"
    c.drawCentredString(page_w / 2, cursor_y, titulo)

    cursor_y -= 14 * mm

    # ─── Caixa do valor destacada ──────────────────────────────────────
    box_w = page_w - 36 * mm
    box_h = 22 * mm
    box_x = (page_w - box_w) / 2
    box_y = cursor_y - box_h

    c.setFillColor(colors.HexColor("#FEF3C7"))  # amber-100
    c.setStrokeColor(colors.HexColor(GOLD))
    c.setLineWidth(1.2)
    c.roundRect(box_x, box_y, box_w, box_h, 4 * mm, fill=1, stroke=1)

    valor = float(recibo.get("valor", 0) or 0)
    c.setFillColor(colors.HexColor(DARK_GREEN))
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(page_w / 2, box_y + box_h - 11 * mm, _format_brl(valor))

    valor_ext = _valor_por_extenso(valor)
    if valor_ext:
        c.setFillColor(colors.HexColor("#78350F"))  # amber-900
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(page_w / 2, box_y + 5 * mm, f"({valor_ext})")

    cursor_y = box_y - 10 * mm

    # ─── Texto do recibo (formal) ──────────────────────────────────────
    pagador = recibo.get("destinatario_nome", "—")
    pagador_doc = _format_documento(recibo.get("destinatario_cpf_cnpj", ""))
    servico = recibo.get("servico") or recibo.get("descricao") or tipo_label

    c.setFillColor(colors.HexColor("#374151"))
    c.setFont("Helvetica", 11)

    texto = (
        f"Recebi de {pagador}"
        + (f" — {pagador_doc}" if pagador_doc else "")
        + f", a importância de {_format_brl(valor)}"
        + (f" ({valor_ext})" if valor_ext else "")
        + f", referente a {servico.lower()}."
    )

    from textwrap import wrap
    for linha in wrap(texto, width=92):
        c.drawString(18 * mm, cursor_y, linha)
        cursor_y -= 5 * mm

    cursor_y -= 4 * mm

    # ─── Detalhes (categoria, descrição extra) ────────────────────────
    if recibo.get("categoria"):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(18 * mm, cursor_y, "Categoria:")
        c.setFont("Helvetica", 10)
        c.drawString(40 * mm, cursor_y, recibo["categoria"][:70])
        cursor_y -= 5 * mm

    if recibo.get("descricao") and recibo["descricao"] != servico:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(18 * mm, cursor_y, "Descrição:")
        cursor_y -= 5 * mm
        c.setFont("Helvetica", 10)
        for linha in wrap(recibo["descricao"], width=95):
            c.drawString(18 * mm, cursor_y, linha)
            cursor_y -= 4.5 * mm

    cursor_y -= 4 * mm

    # ─── Forma de pagamento ───────────────────────────────────────────
    forma = recibo.get("forma_pagamento", "PIX")
    c.setFillColor(colors.HexColor(DARK_GREEN))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, cursor_y, "Forma de pagamento:")
    c.setFillColor(colors.HexColor("#111827"))
    c.setFont("Helvetica", 11)
    c.drawString(60 * mm, cursor_y, forma)
    cursor_y -= 14 * mm

    # ─── Cidade, data e assinatura ────────────────────────────────────
    cidade_uf = ""
    if perfil.get("cidade") and perfil.get("uf"):
        cidade_uf = f"{perfil['cidade']}/{perfil['uf']}"

    rodape = f"{cidade_uf}, {data_emissao}." if cidade_uf else f"{data_emissao}."
    c.setFillColor(colors.HexColor("#374151"))
    c.setFont("Helvetica", 11)
    c.drawString(18 * mm, cursor_y, rodape)
    cursor_y -= 22 * mm

    # Linha de assinatura
    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    c.setLineWidth(0.7)
    c.line(60 * mm, cursor_y, page_w - 60 * mm, cursor_y)
    cursor_y -= 5 * mm

    nome = perfil.get("nome_completo") or user.get("name") or emitente_nome or "Avaliador"
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(page_w / 2, cursor_y, nome)
    cursor_y -= 4 * mm

    # Cargo + registro
    cargo = user.get("role", "")
    registros = perfil.get("registros") or []
    sub_partes = []
    if cargo:
        sub_partes.append(cargo)
    if registros:
        r0 = registros[0]
        sub_partes.append(f"{r0.get('tipo','')} {r0.get('numero','')}".strip())
    if sub_partes:
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#6B7280"))
        c.drawCentredString(page_w / 2, cursor_y, " · ".join(sub_partes))

    # ─── Rodapé com dados bancários (se tiver) ────────────────────────
    bancarios = recibo.get("emitente_dados_bancarios", "")
    if bancarios:
        c.setFillColor(colors.HexColor("#F3F4F6"))
        c.rect(0, 0, page_w, 20 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor(DARK_GREEN))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(18 * mm, 14 * mm, "DADOS BANCÁRIOS / PIX")
        c.setFillColor(colors.HexColor("#374151"))
        c.setFont("Helvetica", 8)
        # Quebra em até 2 linhas
        from textwrap import wrap as _wrap
        linhas_b = _wrap(bancarios, width=110)
        for i, linha in enumerate(linhas_b[:2]):
            c.drawString(18 * mm, 10 * mm - i * 4 * mm, linha)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
