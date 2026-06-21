# @module pdf.templates.danfse_render — Engine ÚNICO (ReportLab) do DANFSe.
# O conteúdo neutro (danfse_base.montar) é desenhado por ESTE engine; o tema só troca
# os TOKENS (cores/fontes/cabeçalho). Os 3 renderers (prime1/prime2/tradicional) são
# wrappers finos que chamam render(conteudo, tema). Visual derivado do HTML aprovado.
from __future__ import annotations

import io
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import qr as _qrmod
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

from pdf.templates.danfse_base import TEMAS
from pdf.themes.prime2_theme import fonts as _fonts

logger = logging.getLogger("romatec")

PAGE_W, PAGE_H = A4
MX = 28.0
W = PAGE_W - 2 * MX
Y_TOP = PAGE_H - 18
Y_BOTTOM = 26


def _serifs(tema: str):
    F = _fonts()
    if tema == "tradicional":
        return "Times-Roman", "Times-Bold"
    return F.get("serif", "Times-Roman"), F.get("serif_bold", "Times-Bold")


def _hex(c):
    try:
        return HexColor(c)
    except Exception:  # noqa: BLE001
        return HexColor("#000000")


def _alpha(hexcolor: str, a: float) -> Color:
    base = _hex(hexcolor)
    return Color(base.red, base.green, base.blue, alpha=a)


def _wrap(c, text, font, size, maxw):
    text = str(text or "")
    c.setFont(font, size)
    linhas, atual = [], ""
    for palavra in text.split():
        teste = (atual + " " + palavra).strip()
        if c.stringWidth(teste, font, size) <= maxw or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas or [""]


def render(conteudo: dict, tema: str = "prime1") -> bytes:
    """Desenha o DANFSe completo e devolve os bytes do PDF."""
    T = TEMAS.get(tema, TEMAS["prime1"])
    SERIF, SERIF_B = _serifs(tema)
    SANS, SANS_B = "Helvetica", "Helvetica-Bold"

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    st = {"y": Y_TOP}

    def quebra(necessario):
        if st["y"] - necessario < Y_BOTTOM:
            c.showPage()
            st["y"] = Y_TOP
            _filete(Y_TOP + 6, 5)

    def _filete(y, h):
        c.setFillColor(_hex(T["ouro"]))
        c.rect(MX, y, W, h, fill=1, stroke=0)

    def _grad_rect(x, y, w, h, c1, c2, steps=48):
        a, b = _hex(c1), _hex(c2)
        for i in range(steps):
            t = i / (steps - 1)
            c.setFillColor(Color(a.red + (b.red - a.red) * t, a.green + (b.green - a.green) * t,
                                 a.blue + (b.blue - a.blue) * t))
            c.rect(x + w * i / steps, y, w / steps + 1, h, fill=1, stroke=0)

    def _qr(x, y, size, data):
        # branco atrás p/ contraste (cabeçalho escuro nos temas Prime) + QR preto
        c.setFillColor(HexColor("#FFFFFF"))
        c.roundRect(x - 3, y - 3, size + 6, size + 6, 3, fill=1, stroke=0)
        try:
            w = _qrmod.QrCodeWidget(str(data or " "), barLevel="M")
            b = w.getBounds()
            bw, bh = (b[2] - b[0]) or 1, (b[3] - b[1]) or 1
            d = Drawing(size, size, transform=[size / bw, 0, 0, size / bh, 0, 0])
            d.add(w)
            renderPDF.draw(d, c, x, y)
        except Exception:  # noqa: BLE001
            pass

    def _brasao(x, y, lado, cab):
        placa = T.get("brasao_placa", True)
        if placa:
            c.setFillColor(HexColor("#FFFFFF"))
            c.roundRect(x, y, lado, lado, 5, fill=1, stroke=0)
        raw = cab.get("brasao")
        if raw:
            try:
                c.drawImage(ImageReader(io.BytesIO(raw)), x + 3, y + 3, lado - 6, lado - 6,
                            preserveAspectRatio=True, mask="auto")
                return
            except Exception:  # noqa: BLE001
                pass
        c.setFillColor(HexColor("#2D5A2D") if placa else _hex(T["cab_fg"]))
        c.setFont(SANS_B, 6.5)
        c.drawCentredString(x + lado / 2, y + lado / 2 + 3, "BRASÃO")
        c.drawCentredString(x + lado / 2, y + lado / 2 - 5, "AÇAILÂNDIA")

    # ── Cabeçalho governamental ──────────────────────────────────────────────
    def cabecalho(cab):
        H = 84
        y = st["y"] - H
        # fundo do cabeçalho conforme tema
        if T.get("cab_split"):
            esq, dir_, frac = T["cab_split"]
            seam = MX + W * frac
            c.setFillColor(_hex(dir_)); c.rect(MX, y, W, H, fill=1, stroke=0)
            p = c.beginPath(); p.moveTo(MX, y); p.lineTo(seam + 26, y); p.lineTo(seam - 26, y + H)
            p.lineTo(MX, y + H); p.close()
            c.setFillColor(_hex(esq)); c.drawPath(p, fill=1, stroke=0)
        elif T.get("cab_grad"):
            _grad_rect(MX, y, W, H, T["cab_grad"][0], T["cab_grad"][1])
        else:  # tradicional — branco com borda inferior
            c.setFillColor(HexColor("#FFFFFF")); c.rect(MX, y, W, H, fill=1, stroke=0)
            if T.get("cab_borda_inf"):
                c.setStrokeColor(_hex(T["cab_borda_inf"])); c.setLineWidth(1.5)
                c.line(MX, y, MX + W, y)
        # ghost numeral (Prime II) — atrás do conteúdo
        if T.get("ghost"):
            c.setFillColor(_alpha(T["ouro"], 0.10))
            c.setFont(SERIF_B, 120)
            c.drawRightString(MX + W - 12, y + 8, cab.get("ghost", ""))
        fg = _hex(T["cab_fg"])
        # brasão
        _brasao(MX + 14, y + (H - 62) / 2, 62, cab)
        gx = MX + 14 + 62 + 14
        # textos gov
        c.setFillColor(fg)
        c.setFont(SANS, 8); c.drawString(gx, y + H - 24, (cab.get("estado") or "").upper())
        c.setFont(SERIF_B, 17); c.drawString(gx, y + H - 46, cab.get("prefeitura", ""))
        c.setFont(SANS, 8.5); c.drawString(gx, y + H - 60, cab.get("secretaria", ""))
        # QR Code (canto superior direito) — espelha o DANFSe municipal
        qr_sz = 46
        qr_x = MX + W - qr_sz - 6
        qr_y = y + (H - qr_sz) / 2
        if cab.get("qr"):
            _qr(qr_x, qr_y, qr_sz, cab.get("qr"))
        # nota box (à esquerda do QR)
        rx = qr_x - 12
        c.setFillColor(fg); c.setFont(SANS, 7.5)
        c.drawRightString(rx, y + H - 22, "NOTA FISCAL Nº")
        c.setFillColor(_hex(T["nota_fg"])); c.setFont(SERIF_B, 23)
        c.drawRightString(rx, y + H - 48, cab.get("numero", ""))
        c.setFillColor(fg); c.setFont(SANS, 7)
        c.drawRightString(rx, y + H - 60, f"SÉRIE · {cab.get('serie', '')}")
        st["y"] = y

    def titulo(txt):
        _filete(st["y"] - 3, 3)
        st["y"] -= 3
        c.setFillColor(_hex(T["titulo_fg"])); c.setFont(SERIF_B, 12.5)
        c.drawCentredString(MX + W / 2, st["y"] - 16, txt)
        st["y"] -= 24

    # ── Célula (rótulo em cima, valor embaixo) ───────────────────────────────
    def cell(x, y, w, h, rotulo, valor, align="l", destaque=False, multiline=False):
        c.setStrokeColor(_hex(T["borda"])); c.setLineWidth(0.5)
        c.rect(x, y, w, h, fill=0, stroke=1)
        pad = 4
        if rotulo:
            c.setFillColor(_hex(T["label_fg"])); c.setFont(SANS, 6.5)
            c.drawString(x + pad, y + h - 9, (rotulo or "").upper())
            vy = (y + h - 18) if multiline else (y + 5)
        else:
            vy = (y + h - 8) if multiline else (y + h / 2 - 3)
        vfont = SANS_B if destaque else SANS
        vsize = 9 if destaque else 8.2
        c.setFillColor(_hex(T["destaque_fg"]) if destaque else _hex(T["valor_fg"]))
        if multiline:
            for ln in _wrap(c, valor, vfont, vsize, w - 2 * pad):
                c.setFont(vfont, vsize); c.drawString(x + pad, vy, ln)
                vy -= vsize + 2.5
        else:
            c.setFont(vfont, vsize)
            txt = str(valor or "")
            while txt and c.stringWidth(txt, vfont, vsize) > w - 2 * pad:
                txt = txt[:-1]
            if align == "r":
                c.drawRightString(x + w - pad, vy, txt)
            else:
                c.drawString(x + pad, vy, txt)

    def _cell_h(linha, base=21):
        h = base
        for cl in linha:
            if len(cl) >= 4 and cl[3] == "multiline":
                texto = str(cl[1] or "")
                nlin = max(1, len(texto) // 78 + texto.count("\n") + 1)
                h = max(h, 15 + nlin * 10.5)
        return h

    def grid(linhas):
        for linha in linhas:
            h = _cell_h(linha)
            quebra(h + 2)
            y = st["y"] - h
            x = MX
            for cl in linha:
                rot, val = cl[0], cl[1]
                span = cl[2] if len(cl) > 2 else 1
                hint = cl[3] if len(cl) > 3 else ""
                cw = W * span / 4.0
                cell(x, y, cw, h, rot, val, align="r" if hint == "r" else "l",
                     multiline=(hint == "multiline"))
                x += cw
            st["y"] = y

    def band(n, tit):
        h = 15
        quebra(h + 2)
        y = st["y"] - h
        c.setFillColor(_hex(T["faixa_bg"])); c.rect(MX, y, W, h, fill=1, stroke=0)
        c.setFillColor(_hex(T["faixa_num"])); c.setFont(SANS_B, 8)
        c.drawString(MX + 8, y + 5, n)
        c.setFillColor(_hex(T["faixa_fg"])); c.setFont(SERIF_B, 10)
        c.drawString(MX + 26, y + 5, (tit or "").upper())
        st["y"] = y

    def tricol(colunas):
        pair_h = 14
        alturas = [10 + len(col) * pair_h for col in colunas]
        H = max(alturas)
        quebra(H + 2)
        y = st["y"] - H
        cw = W / 3.0
        for i, col in enumerate(colunas):
            x = MX + i * cw
            c.setStrokeColor(_hex(T["borda"])); c.setLineWidth(0.5)
            c.rect(x, y, cw, H, fill=0, stroke=1)
            yy = y + H - 4
            for (rot, val, dest) in col:
                c.setFillColor(_hex(T["label_fg"])); c.setFont(SANS, 6.3)
                c.drawString(x + 5, yy - 6, (rot or "").upper())
                vfont = SANS_B if dest else SANS
                vsize = 9 if dest else 8
                c.setFillColor(_hex(T["destaque_fg"]) if dest else _hex(T["valor_fg"]))
                c.setFont(vfont, vsize)
                # valores monetários/curtos à direita; textos à esquerda
                if any(ch.isdigit() for ch in str(val)) and len(str(val)) <= 16:
                    c.drawRightString(x + cw - 5, yy - 6, str(val or ""))
                else:
                    txt = str(val or "")
                    while txt and c.stringWidth(txt, vfont, vsize) > cw - 10:
                        txt = txt[:-1]
                    c.drawString(x + 5, yy - 6, txt)
                yy -= pair_h
        st["y"] = y

    def rodape(r):
        h = 22
        quebra(h + 4)
        _filete(st["y"] - 3, 3)
        st["y"] -= 3
        y = st["y"] - h
        c.setFillColor(HexColor("#FAFAFA")); c.rect(MX, y, W, h, fill=1, stroke=0)
        c.setFillColor(_hex(T["titulo_fg"])); c.setFont(SERIF_B, 9)
        c.drawString(MX + 10, y + 7, r.get("marca", ""))
        c.setFillColor(HexColor("#555555")); c.setFont(SANS, 8)
        wmarca = c.stringWidth(r.get("marca", ""), SERIF_B, 9)
        c.drawString(MX + 16 + wmarca, y + 7, r.get("via", ""))
        c.drawRightString(MX + W - 10, y + 7,
                          f"Impressa em {r.get('impressa_em', '')} · Emissão {r.get('hora_emissao', '')}")
        st["y"] = y

    # ── Composição (ordem do HTML aprovado) ──────────────────────────────────
    _filete(Y_TOP + 6, 5)
    cabecalho(conteudo["cabecalho"])
    titulo(conteudo["titulo"])
    grid(conteudo["controle"])
    for sec in conteudo["secoes"]:
        band(sec["n"], sec["titulo"])
        if sec.get("tipo") == "tricol":
            tricol(sec["colunas"])
        else:
            grid(sec["linhas"])
    rodape(conteudo["rodape"])

    c.save()
    return buf.getvalue()
