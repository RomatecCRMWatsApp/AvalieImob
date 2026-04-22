# @module docx.tvi_docx — Geração de DOCX para Termo de Vistoria de Imóvel (TVI)
"""DOCX generator for TVI documents — RomaTec branding.

Uses python-docx to produce a Word-compatible document with:
  - Header: título + número TVI
  - Seções: Identificação, Imóvel, Vistoria, Ambientes, Campos Extras
  - Conclusão técnica
  - Bloco de assinatura: signatário + ART/TRT + data + local
  - Seguindo o mesmo layout do ptam_docx.py
"""
from __future__ import annotations

import base64
import io
import urllib.request
from datetime import datetime
from typing import Any

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BRAND_GREEN = RGBColor(0x1B, 0x4D, 0x1B)
BRAND_GOLD = RGBColor(0xD4, 0xA8, 0x30)
DARK = RGBColor(0x1A, 0x1A, 0x1A)


# ── low-level helpers ─────────────────────────────────────────────────────────

def _set_cell_bg(cell, color_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tc_pr.append(shd)


def _add_heading(doc: Document, text: str, size: int = 14, center: bool = True) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    r.font.color.rgb = BRAND_GREEN
    r.font.name = "Calibri"


def _add_section_title(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text.upper())
    r.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = BRAND_GREEN
    r.font.name = "Calibri"
    rule = doc.add_paragraph("─" * 80)
    rule.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _fmt_val(val: Any) -> str:
    """Formata valor de campo para exibição em texto plano."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "Sim" if val else "Não"
    if isinstance(val, list):
        items = [str(i) for i in val if i is not None and str(i).strip()]
        return ", ".join(items)
    if isinstance(val, dict):
        parts = [f"{k}: {v}" for k, v in val.items() if v is not None and str(v).strip()]
        return " | ".join(parts)
    return str(val)


def _add_label_value(doc: Document, label: str, value: Any) -> None:
    text = _fmt_val(value)
    if not text or not text.strip():
        return
    p = doc.add_paragraph()
    r1 = p.add_run(f"{label}: ")
    r1.bold = True
    r1.font.size = Pt(11)
    r1.font.name = "Calibri"
    r2 = p.add_run(text)
    r2.font.size = Pt(11)
    r2.font.name = "Calibri"


def _add_para(doc: Document, text: str, bold: bool = False, size: int = 11) -> None:
    if not text or not text.strip():
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.name = "Calibri"


# ── section renderers ─────────────────────────────────────────────────────────

def _render_cover(doc: Document, v: dict, model_nome: str) -> None:
    _add_heading(doc, "TERMO DE VISTORIA DE IMÓVEL", size=16)
    if model_nome:
        _add_heading(doc, model_nome.upper(), size=13)
    _add_heading(doc, f"Nº {v.get('numero_tvi') or 'TVI-0000/0000'}", size=14)
    doc.add_paragraph()

    _add_section_title(doc, "Imóvel Vistoriado")
    _add_label_value(doc, "Endereço", v.get("imovel_endereco"))
    _add_label_value(doc, "Bairro", v.get("imovel_bairro"))
    city_uf = " / ".join(filter(None, [v.get("imovel_cidade"), v.get("imovel_uf")]))
    _add_label_value(doc, "Cidade / UF", city_uf)
    doc.add_paragraph()

    _add_label_value(doc, "Solicitante", v.get("cliente_nome"))
    _add_label_value(doc, "CPF / CNPJ", v.get("cliente_cpf_cnpj"))
    _add_label_value(doc, "Telefone", v.get("cliente_telefone"))
    _add_label_value(doc, "E-mail", v.get("cliente_email"))
    doc.add_paragraph()

    _add_label_value(doc, "Responsável Técnico", v.get("responsavel_nome"))
    _add_label_value(doc, "CREA", v.get("responsavel_crea"))
    _add_label_value(doc, "CAU", v.get("responsavel_cau"))
    _add_label_value(doc, "CFTMA", v.get("responsavel_cftma"))
    _add_label_value(doc, "ART / TRT nº", v.get("art_trt_numero"))


def _render_imovel(doc: Document, v: dict) -> None:
    _add_section_title(doc, "2. Dados do Imóvel")
    _add_label_value(doc, "Tipo", v.get("imovel_tipo"))
    _add_label_value(doc, "Endereço completo", v.get("imovel_endereco"))
    _add_label_value(doc, "Bairro", v.get("imovel_bairro"))
    city_uf = " / ".join(filter(None, [v.get("imovel_cidade"), v.get("imovel_uf")]))
    _add_label_value(doc, "Cidade / UF", city_uf)
    _add_label_value(doc, "CEP", v.get("imovel_cep"))
    _add_label_value(doc, "Matrícula", v.get("imovel_matricula"))


def _render_vistoria_dados(doc: Document, v: dict) -> None:
    _add_section_title(doc, "3. Dados da Vistoria")
    _add_label_value(doc, "Data", v.get("data_vistoria"))
    _add_label_value(doc, "Hora", v.get("hora_vistoria"))
    _add_label_value(doc, "Condições Climáticas", v.get("condicoes_climaticas"))
    _add_label_value(doc, "Objetivo", v.get("objetivo"))
    _add_label_value(doc, "Metodologia", v.get("metodologia"))


def _render_ambientes(doc: Document, v: dict) -> None:
    ambientes = v.get("ambientes") or []
    if not ambientes:
        return
    _add_section_title(doc, "4. Ambientes Vistoriados")
    for amb in ambientes:
        if not (isinstance(amb, dict) and amb.get("nome")):
            continue
        _add_heading(doc, amb["nome"], size=12, center=False)
        _add_label_value(doc, "Descrição", amb.get("descricao"))
        _add_label_value(doc, "Estado de Conservação", amb.get("estado_conservacao"))
        _add_label_value(doc, "Observações", amb.get("observacoes"))
        doc.add_paragraph()


def _render_campos_extras(doc: Document, v: dict, campos_especificos: list | None = None) -> None:
    extras = v.get("campos_extras") or {}
    if not extras:
        return

    # Mapa id→{label, secao} do modelo
    campo_meta: dict[str, dict] = {}
    if campos_especificos:
        for c in campos_especificos:
            cid = c.get("id") or c.get("key") or ""
            if cid:
                campo_meta[cid] = {
                    "label": c.get("label") or cid.replace("_", " ").title(),
                    "secao": c.get("secao") or "Informações Complementares",
                }

    # Agrupa por seção
    secoes: dict[str, list] = {}
    for key, val in extras.items():
        text = _fmt_val(val)
        if not text or not text.strip():
            continue
        meta = campo_meta.get(key, {})
        label = meta.get("label") or key.replace("_", " ").title()
        secao = meta.get("secao") or "Informações Complementares"
        secoes.setdefault(secao, []).append((label, text))

    if not secoes:
        return

    _add_section_title(doc, "5. Campos Específicos do Modelo")
    for secao, itens in secoes.items():
        p = doc.add_paragraph(secao)
        p.runs[0].bold = True
        for label, text in itens:
            _add_label_value(doc, label, text)


def _render_fotos(doc: Document, photos: list) -> None:
    if not photos:
        return
    _add_section_title(doc, "6. Registro Fotográfico")
    MAX_W = Cm(7.5)
    MAX_H = Cm(5.5)

    # Build 2-column photo table
    row_pairs: list = []
    pair: list = []
    for photo in photos:
        url = photo.get("url", "") if isinstance(photo, dict) else ""
        legenda = photo.get("legenda", "") if isinstance(photo, dict) else ""
        ambiente = photo.get("ambiente", "") if isinstance(photo, dict) else ""
        caption = legenda or ambiente or ""

        img_bytes: bytes | None = None
        if url:
            try:
                if url.startswith("data:"):
                    b64 = url.split(",", 1)[-1]
                    img_bytes = base64.b64decode(b64)
                else:
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        img_bytes = resp.read()
            except Exception:
                img_bytes = None

        pair.append({"img": img_bytes, "caption": caption})
        if len(pair) == 2:
            row_pairs.append(pair)
            pair = []
    if pair:
        while len(pair) < 2:
            pair.append({"img": None, "caption": ""})
        row_pairs.append(pair)

    for pair in row_pairs:
        tbl = doc.add_table(rows=2, cols=2)
        tbl.style = "Table Grid"
        for col_idx, cell_data in enumerate(pair):
            img_cell = tbl.rows[0].cells[col_idx]
            img_cell.width = Cm(8.5)
            cap_cell = tbl.rows[1].cells[col_idx]

            if cell_data["img"]:
                try:
                    para = img_cell.paragraphs[0]
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = para.add_run()
                    run.add_picture(io.BytesIO(cell_data["img"]), width=MAX_W, height=MAX_H)
                except Exception:
                    img_cell.text = "[Foto indisponível]"

            cap_para = cap_cell.paragraphs[0]
            cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap_run = cap_para.add_run(cell_data["caption"])
            cap_run.italic = True
            cap_run.font.size = Pt(9)
            cap_run.font.name = "Calibri"

        doc.add_paragraph()


def _render_conclusao(doc: Document, v: dict) -> None:
    _add_section_title(doc, "7. Conclusão Técnica")
    _add_para(doc, v.get("conclusao_tecnica", ""))


def _render_assinatura(doc: Document, v: dict, sigs: list) -> None:
    doc.add_paragraph()
    doc.add_paragraph()

    city = v.get("imovel_cidade", "")
    date_str = v.get("data_vistoria") or datetime.utcnow().strftime("%d/%m/%Y")
    loc_text = f"{city}, {date_str}." if city else date_str
    loc_para = doc.add_paragraph(loc_text)
    loc_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_paragraph()
    doc.add_paragraph()

    # Signature image
    first_sig = next(
        (s for s in (sigs or []) if isinstance(s, dict) and s.get("data_b64")), None
    )
    if first_sig:
        try:
            sig_data = base64.b64decode(first_sig["data_b64"])
            sig_para = doc.add_paragraph()
            sig_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = sig_para.add_run()
            run.add_picture(io.BytesIO(sig_data), width=Cm(5.5), height=Cm(2.0))
        except Exception:
            pass

    sig_line = doc.add_paragraph("_" * 50)
    sig_line.alignment = WD_ALIGN_PARAGRAPH.CENTER

    nome = v.get("responsavel_nome") or (first_sig or {}).get("signatario", "")
    if nome:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(nome)
        r.bold = True
        r.font.size = Pt(11)
        r.font.name = "Calibri"

    for field, label in [
        ("responsavel_crea", "CREA"),
        ("responsavel_cau", "CAU"),
        ("responsavel_cftma", "CFTMA"),
        ("art_trt_numero", "ART/TRT nº"),
    ]:
        val = v.get(field, "")
        if val:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(f"{label} {val}").font.size = Pt(10)

    if first_sig and first_sig.get("cargo"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(first_sig["cargo"]).font.size = Pt(10)


# ── main entry point ──────────────────────────────────────────────────────────

def generate_tvi_docx(
    vistoria: dict,
    user: dict,
    photos: list | None = None,
    signatures: list | None = None,
    model_nome: str = "",
    campos_especificos: list | None = None,
) -> bytes:
    """Generate TVI DOCX. Returns bytes.

    Args:
        vistoria: Vistoria document dict.
        user: Logged-in user dict.
        photos: List of VistoriaPhoto dicts [{url, ambiente, legenda}, …].
        signatures: List of VistoriaSignature dicts [{data_b64, signatario, cargo}, …].
        model_nome: Human-readable model name.
    """
    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    _render_cover(doc, vistoria, model_nome)
    doc.add_page_break()

    _render_imovel(doc, vistoria)
    doc.add_paragraph()

    _render_vistoria_dados(doc, vistoria)
    doc.add_paragraph()

    _render_ambientes(doc, vistoria)
    doc.add_paragraph()

    _render_campos_extras(doc, vistoria, campos_especificos or [])
    doc.add_paragraph()

    _render_fotos(doc, photos or [])
    doc.add_paragraph()

    _render_conclusao(doc, vistoria)
    doc.add_page_break()

    _render_assinatura(doc, vistoria, signatures or [])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
