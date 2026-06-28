# @module services.testemunha_pagina — página dedicada de TESTEMUNHAS (anexada ao fim).
#
# Gera uma página A4 com a QUALIFICAÇÃO completa de cada testemunha + a firma desenhada
# (carimbo de identificação) + a trilha de autenticação (WhatsApp/IP/data). Anexada ao
# documento final via append-only (services.testemunha_signing.anexar_pagina_incremental).
from __future__ import annotations

import base64
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black
from reportlab.pdfgen import canvas as rl_canvas

_VERDE = HexColor("#0C3320")
_DOURADO = HexColor("#C9A84C")
_CINZA = HexColor("#555555")


def _fmt_cpf(cpf):
    d = "".join(filter(str.isdigit, str(cpf or "")))
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}" if len(d) == 11 else (cpf or "")


def _fmt_fone(f):
    d = "".join(filter(str.isdigit, str(f or "")))
    if d.startswith("55") and len(d) >= 12:
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return f or ""


_ESTADO_CIVIL = {"solteiro": "solteiro(a)", "casado": "casado(a)", "uniao_estavel": "em união estável",
                 "divorciado": "divorciado(a)", "viuvo": "viúvo(a)", "separado": "separado(a)"}


def _papel_testemunha(t: dict) -> str:
    v = str(t.get("vinculo") or "").strip()
    if not v:
        return "Testemunha instrumentária"
    art = "da" if v.lower().endswith("a") else "do"
    return f"Testemunha {art} {v}"


def pagina_manifestacao_testemunhas(doc: dict, testemunhas: list) -> bytes:
    """Página MANIFESTAÇÃO DE VONTADE E AUTORIA das TESTEMUNHAS (trilha de autenticação:
    CPF, papel, data/hora, IP, geolocalização, dispositivo, hash) — igual à das partes."""
    from reportlab.lib.utils import simpleSplit
    W, H = A4
    M = 2.2 * cm
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setFillColor(_VERDE)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(M, H - 2.3 * cm, "MANIFESTAÇÃO DE VONTADE E AUTORIA — ASSINATURA ELETRÔNICA")
    c.setStrokeColor(_DOURADO)
    c.setLineWidth(1.0)
    c.line(M, H - 2.6 * cm, W - M, H - 2.6 * cm)
    c.setFillColor(_CINZA)
    c.setFont("Helvetica", 7.5)
    c.drawString(M, H - 3.0 * cm,
                 "Lei nº 14.063/2020 (assinatura avançada) · MP 2.200-2/2001 · CC arts. 219, 221 e 1.647 · "
                 "CPC art. 411 — TESTEMUNHAS instrumentárias")
    y = H - 3.9 * cm
    for t in testemunhas:
        papel = _papel_testemunha(t)
        if y < 3.0 * cm:
            c.showPage()
            c.setFillColor(_VERDE)
            c.setFont("Helvetica-Bold", 13)
            c.drawString(M, H - 2.3 * cm, "MANIFESTAÇÃO DE VONTADE E AUTORIA (cont.)")
            y = H - 3.6 * cm
        if t.get("status") == "assinado":
            c.setFillColor(black)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(M, y, f"Signatário: {t.get('nome')}  ·  CPF {_fmt_cpf(t.get('cpf')) or '—'}  ·  Papel: {papel}")
            c.setFillColor(_CINZA)
            c.setFont("Helvetica", 8)
            c.drawString(M, y - 0.42 * cm, f"Data/hora: {_fmt(t.get('assinado_em'))}  ·  IP: {t.get('ip') or '—'}")
            geo = "-, -"
            if t.get("geo_lat") and t.get("geo_lng"):
                geo = f"{t.get('geo_lat')}, {t.get('geo_lng')}"
            ua = str(t.get("user_agent") or "—")
            disp = simpleSplit(f"Geolocalização: {geo}  ·  Dispositivo: {ua}", "Helvetica", 8, W - 2 * M)
            yy = y - 0.78 * cm
            for ln in disp[:2]:
                c.drawString(M, yy, ln)
                yy -= 0.34 * cm
            c.drawString(M, yy, f"Hash do traço (SHA-256): {t.get('hash_validacao') or '—'}")
            y = yy - 0.7 * cm
        else:
            c.setFillColor(black)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(M, y, f"Signatário: {t.get('nome')}  ·  Papel: {papel}")
            c.setFillColor(_DOURADO)
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(M, y - 0.42 * cm, "(aguardando assinatura por WhatsApp)")
            y -= 1.1 * cm
    c.showPage()
    c.save()
    return buf.getvalue()


def _qualificacao(t: dict) -> str:
    """Qualificação notarial completa da testemunha (omite o que estiver vazio)."""
    quals = [t.get("nacionalidade"), _ESTADO_CIVIL.get(t.get("estado_civil"), t.get("estado_civil")),
             t.get("profissao")]
    partes = [str(q).strip() for q in quals if q and str(q).strip()]
    rg = str(t.get("rg") or "").strip()
    if rg:
        org = str(t.get("orgao_emissor") or "").strip()
        partes.append(f"portador(a) do RG nº {rg}{(' ' + org) if org else ''}")
    cpf = _fmt_cpf(t.get("cpf"))
    if cpf:
        partes.append(f"inscrito(a) no CPF nº {cpf}")
    end = str(t.get("endereco") or "").strip()
    if end:
        partes.append(f"residente e domiciliado(a) em {end}")
    cont = []
    if t.get("telefone"):
        cont.append(f"contato {_fmt_fone(t.get('telefone'))}")
    if t.get("email"):
        cont.append(f"e-mail {t.get('email')}")
    if cont:
        partes.append(", ".join(cont))
    vinc = str(t.get("parte_vinculada_nome") or "").strip()
    papel = str(t.get("vinculo") or "").strip()
    if vinc or papel:
        partes.append(f"na qualidade de testemunha de {vinc}{(' (' + papel + ')') if papel else ''}")
    return (", ".join(partes) + ".") if partes else ""


def _fmt(dt):
    if not dt:
        return ""
    try:
        d = dt if isinstance(dt, datetime) else datetime.fromisoformat(str(dt))
        return d.strftime("%d/%m/%Y %H:%M")
    except Exception:  # noqa: BLE001
        return str(dt)


def _firma_reader(traco_b64):
    """ImageReader da firma desenhada (PNG), recortada ao conteúdo. None se falhar."""
    try:
        from services.assinatura_cliente_carimbo import _trim_png
        from reportlab.lib.utils import ImageReader
        raw = base64.b64decode(traco_b64) if traco_b64 else None
        if not raw:
            return None
        return ImageReader(io.BytesIO(_trim_png(raw)))
    except Exception:  # noqa: BLE001
        return None


def pagina_testemunhas_pdf(doc: dict, testemunhas: list) -> bytes:
    """Página A4 com as testemunhas (qualificação + firma + autenticação)."""
    W, H = A4
    M = 2.2 * cm
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)

    # cabeçalho
    c.setFillColor(_VERDE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(M, H - 2.4 * cm, "TESTEMUNHAS")
    c.setStrokeColor(_DOURADO)
    c.setLineWidth(1.0)
    c.line(M, H - 2.7 * cm, W - M, H - 2.7 * cm)
    titulo = doc.get("titulo") or doc.get("numero_contrato") or "documento"
    c.setFillColor(_CINZA)
    c.setFont("Helvetica", 8.5)
    c.drawString(M, H - 3.15 * cm,
                 f"Testemunhas do instrumento \"{titulo}\", que assinam eletronicamente o documento "
                 f"já firmado pelas partes (MP 2.200-2/2001 · Lei 14.063/2020).")

    from reportlab.lib.utils import simpleSplit
    y = H - 4.4 * cm
    for t in testemunhas:
        qual = _qualificacao(t)
        qlinhas = simpleSplit(qual, "Helvetica", 8.3, W - 2 * M) if qual else []
        bloco_h = 1.95 * cm + 0.5 * cm + len(qlinhas) * 0.345 * cm + 0.95 * cm
        if y - bloco_h < 2.0 * cm:   # nova página se não couber
            c.showPage()
            c.setFillColor(_VERDE)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(M, H - 2.4 * cm, "TESTEMUNHAS (cont.)")
            y = H - 3.8 * cm
        # firma desenhada acima da linha (ou "aguardando" se ainda não assinou)
        reader = _firma_reader(t.get("traco_b64")) if t.get("status") == "assinado" else None
        if reader:
            iw, ih = reader.getSize()
            esc = min((6.0 * cm) / iw, (1.7 * cm) / ih)
            fw, fh = iw * esc, ih * esc
            try:
                c.drawImage(reader, M, y - fh + 0.2 * cm, width=fw, height=fh, mask="auto")
            except Exception:  # noqa: BLE001
                pass
        elif t.get("status") != "assinado":
            c.setFillColor(_DOURADO)
            c.setFont("Helvetica-Oblique", 7.5)
            c.drawString(M, y - 1.4 * cm, "(aguardando assinatura por WhatsApp)")
        c.setStrokeColor(black)
        c.setLineWidth(0.8)
        c.line(M, y - 1.85 * cm, M + 8.0 * cm, y - 1.85 * cm)
        # nome + qualificação notarial completa (quebrada em linhas)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(M, y - 2.25 * cm, (t.get("nome") or "—"))
        c.setFont("Helvetica", 8.3)
        c.setFillColor(_CINZA)
        yy = y - 2.62 * cm
        for ln in qlinhas:
            c.drawString(M, yy, ln)
            yy -= 0.345 * cm
        auth = f"Assinado eletronicamente via WhatsApp em {_fmt(t.get('assinado_em'))}"
        if t.get("ip"):
            auth += f"  ·  IP {t.get('ip')}"
        if t.get("hash_validacao"):
            auth += f"  ·  cód. {str(t.get('hash_validacao'))[:16]}"
        c.setFont("Helvetica", 7)
        c.drawString(M, yy - 0.05 * cm, auth)
        y -= bloco_h

    c.showPage()
    c.save()
    return buf.getvalue()


def pagina_rotulo_anexo(titulo: str, subtitulo: str = "") -> bytes:
    """Página A4 só com o rótulo do anexo (antecede o PDF anexado da CNH)."""
    W, H = A4
    M = 2.2 * cm
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setFillColor(_VERDE)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(M, H - 2.4 * cm, titulo)
    c.setStrokeColor(_DOURADO)
    c.setLineWidth(1.0)
    c.line(M, H - 2.7 * cm, W - M, H - 2.7 * cm)
    if subtitulo:
        c.setFillColor(_CINZA)
        c.setFont("Helvetica", 10)
        c.drawString(M, H - 3.2 * cm, subtitulo)
    c.showPage()
    c.save()
    return buf.getvalue()


def pagina_sumario_anexos(itens: list, titulo_doc: str = "") -> bytes:
    """Índice (sumário) dos ANEXOS, no estilo do contrato (verde/dourado) — lista cada
    seção anexada com o nº da página. `itens` = [(label, pagina_1idx)]."""
    W, H = A4
    M = 2.4 * cm
    _CAIXA = HexColor("#F3E9C9")
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setFillColor(_DOURADO)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(W / 2, H - 2.7 * cm, "ROMATEC CONSULTORIA TOTAL")
    c.setFillColor(_VERDE)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(W / 2, H - 3.6 * cm, "ANEXOS")
    c.setFillColor(_CINZA)
    c.setFont("Helvetica-Oblique", 10.5)
    c.drawCentredString(W / 2, H - 4.2 * cm, "Qualificação das testemunhas e documentos de identidade")
    c.setStrokeColor(_DOURADO)
    c.setLineWidth(1.3)
    c.line(W / 2 - 3.2 * cm, H - 4.55 * cm, W / 2 + 3.2 * cm, H - 4.55 * cm)
    y = H - 6.0 * cm
    for label, pg in itens:
        bw, bh = 1.25 * cm, 0.62 * cm
        bx, by = W - M - bw, y - 0.18 * cm
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 11.5)
        lbl_w = c.stringWidth(label, "Helvetica-Bold", 11.5)
        c.drawString(M, y, label)
        # leader pontilhado entre o texto e a caixa
        c.setStrokeColor(HexColor("#CFCFCF"))
        c.setLineWidth(0.6)
        c.setDash(1, 3)
        c.line(M + lbl_w + 6, y + 2, bx - 6, y + 2)
        c.setDash()
        # caixa dourada com o nº da página
        c.setFillColor(_CAIXA)
        c.setStrokeColor(_DOURADO)
        c.setLineWidth(1.0)
        c.roundRect(bx, by, bw, bh, 4, fill=1, stroke=1)
        c.setFillColor(_VERDE)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(bx + bw / 2, by + 0.18 * cm, str(pg))
        y -= 1.05 * cm
    c.setFillColor(_CINZA)
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(W / 2, 2.0 * cm, f"Complemento do sumário — {titulo_doc}" if titulo_doc else "Complemento do sumário do instrumento")
    c.showPage()
    c.save()
    return buf.getvalue()


def pagina_documentos_pdf(itens: list) -> bytes:
    """itens = [(label, img_bytes)] — uma página A4 por documento (CNH/RG) da testemunha,
    com cabeçalho + legenda. Imagem ajustada à página preservando a proporção."""
    from reportlab.lib.utils import ImageReader
    W, H = A4
    M = 1.6 * cm
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    for label, img in itens:
        try:
            reader = ImageReader(io.BytesIO(img))
            iw, ih = reader.getSize()
            maxw, maxh = W - 2 * M, H - 3.6 * cm
            esc = min(maxw / iw, maxh / ih)
            fw, fh = iw * esc, ih * esc
            c.setFillColor(_VERDE)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(M, H - 1.7 * cm, "ANEXO — DOCUMENTO DE IDENTIDADE DA TESTEMUNHA")
            c.setStrokeColor(_DOURADO)
            c.setLineWidth(1.0)
            c.line(M, H - 2.0 * cm, W - M, H - 2.0 * cm)
            c.setFillColor(_CINZA)
            c.setFont("Helvetica", 9)
            c.drawString(M, H - 2.45 * cm, label)
            c.drawImage(reader, (W - fw) / 2, M, width=fw, height=fh, mask="auto")
        except Exception:  # noqa: BLE001
            continue
        c.showPage()
    c.save()
    return buf.getvalue()
