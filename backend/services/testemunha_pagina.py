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


def _mask_cpf(cpf):
    d = "".join(filter(str.isdigit, str(cpf or "")))
    return f"***.{d[3:6]}.{d[6:9]}-**" if len(d) == 11 else (cpf or "—")


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

    y = H - 4.6 * cm
    bloco_h = 3.7 * cm
    for t in testemunhas:
        if y - bloco_h < 2.0 * cm:   # nova página se não couber
            c.showPage()
            c.setFillColor(_VERDE)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(M, H - 2.4 * cm, "TESTEMUNHAS (cont.)")
            y = H - 4.0 * cm
        # firma desenhada acima da linha
        reader = _firma_reader(t.get("traco_b64"))
        if reader:
            iw, ih = reader.getSize()
            esc = min((6.0 * cm) / iw, (1.7 * cm) / ih)
            fw, fh = iw * esc, ih * esc
            try:
                c.drawImage(reader, M, y - fh + 0.2 * cm, width=fw, height=fh, mask="auto")
            except Exception:  # noqa: BLE001
                pass
        c.setStrokeColor(black)
        c.setLineWidth(0.8)
        c.line(M, y - 1.85 * cm, M + 8.0 * cm, y - 1.85 * cm)
        # qualificação
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(M, y - 2.25 * cm, (t.get("nome") or "—"))
        c.setFont("Helvetica", 8.5)
        c.setFillColor(_CINZA)
        vinc = t.get("parte_vinculada_nome") or ""
        papel = t.get("vinculo") or ""
        linha2 = f"CPF: {_mask_cpf(t.get('cpf'))}"
        if vinc or papel:
            linha2 += f"  ·  Testemunha de {vinc}{(' (' + papel + ')') if papel else ''}"
        c.drawString(M, y - 2.65 * cm, linha2)
        auth = f"Assinado via WhatsApp em {_fmt(t.get('assinado_em'))}"
        if t.get("ip"):
            auth += f"  ·  IP {t.get('ip')}"
        if t.get("hash_validacao"):
            auth += f"  ·  cód. {str(t.get('hash_validacao'))[:16]}"
        c.setFont("Helvetica", 7)
        c.drawString(M, y - 3.05 * cm, auth)
        y -= bloco_h

    c.showPage()
    c.save()
    return buf.getvalue()
