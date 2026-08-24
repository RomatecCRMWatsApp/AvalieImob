"""QR Code das pecas de divulgacao em PDF VETORIAL (arte para grafica).

O painel ja baixa o QR em PNG, resolucao fixa — bom para WhatsApp, ruim para
impressao grande. Aqui o codigo sai como vetor: a grafica amplia a vontade
(folder, banner, placa) sem serrilhar.

A URL — inclusive a marcacao de origem (utm_*) — vem PRONTA do frontend, que e
a fonte unica das pecas (DivulgacaoPage). Aqui so validamos que o destino e do
proprio site, para o endpoint nao virar um gerador de QR aberto.
"""
from io import BytesIO
from urllib.parse import urlparse

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from pdf.brand_seal import draw_brand_badge  # o "A" da marca, vetorial

VERDE = (12 / 255, 51 / 255, 32 / 255)  # #0C3320

_HOSTS_PERMITIDOS = ("romatecavalieimob.com.br", "www.romatecavalieimob.com.br")

PAGINA = 80 * mm     # arte quadrada; sendo vetor, o tamanho e so referencia
QR_LADO = 68 * mm    # deixa ~6 mm de margem branca (quiet zone) de cada lado

# Badge central: quanto MAIOR a URL, mais denso o QR — e um badge de tamanho fixo
# passa a cobrir um padrao de alinhamento, que derruba a leitura (visto na peca
# de topografia, a URL mais longa). Por isso o badge e medido em MODULOS, nao em
# fracao fixa: no maximo 11 modulos de lado contando a folga branca.
_BADGE_MODULOS = 11    # area branca maxima, em modulos de lado
_BADGE_MAX = 0.19      # teto em QR curto, para o "A" nao virar o codigo todo
_FOLGA = 0.16          # respiro branco ao redor do badge, em fracao do badge


class UrlNaoPermitida(ValueError):
    """Destino fora do nosso dominio."""


def validar_url(url: str) -> str:
    url = (url or "").strip()
    try:
        p = urlparse(url)
    except ValueError:
        raise UrlNaoPermitida("Endereço inválido.")
    if p.scheme not in ("http", "https") or (p.hostname or "").lower() not in _HOSTS_PERMITIDOS:
        raise UrlNaoPermitida("O QR só pode apontar para o site da plataforma.")
    return url


def _desenhar_qr(c: Canvas, matriz, x0: float, y0: float, lado: float) -> None:
    """Modulos como UM path unico, agrupando os vizinhos de cada linha.

    Agrupar evita as linhas-fantasma que aparecem entre retangulos encostados em
    alguns visualizadores/RIPs, e um path unico deixa o arquivo leve.
    """
    n = len(matriz)
    box = lado / n
    p = c.beginPath()
    for i, linha in enumerate(matriz):
        j = 0
        while j < n:
            if not linha[j]:
                j += 1
                continue
            k = j
            while k + 1 < n and linha[k + 1]:
                k += 1
            # y invertido: a matriz comeca no topo, o PDF na base.
            p.rect(x0 + j * box, y0 + lado - (i + 1) * box, (k - j + 1) * box, box)
            j = k + 1
    c.setFillColorRGB(*VERDE)
    c.drawPath(p, stroke=0, fill=1)


def _fracao_badge(n_modulos: int) -> float:
    """Fracao do QR que o badge pode ocupar sem comprometer a leitura."""
    branco = _BADGE_MODULOS / float(n_modulos)   # area branca desejada
    return min(_BADGE_MAX, branco / (1 + 2 * _FOLGA))


def gerar_pdf(url: str, titulo: str = "QR Code") -> bytes:
    """PDF de uma pagina com o QR vetorial da URL + badge da marca no centro."""
    url = validar_url(url)
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    matriz = qr.get_matrix()

    buf = BytesIO()
    c = Canvas(buf, pagesize=(PAGINA, PAGINA))
    c.setTitle(f"{titulo} — AvalieImob")

    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, PAGINA, PAGINA, stroke=0, fill=1)

    x0 = y0 = (PAGINA - QR_LADO) / 2
    _desenhar_qr(c, matriz, x0, y0, QR_LADO)

    # Badge central: abre um vazio branco e assenta o "A" por cima. A correcao
    # de erro H (30%) cobre os modulos perdidos — validado por leitura real.
    lado_badge = QR_LADO * _fracao_badge(len(matriz))
    folga = lado_badge * _FOLGA
    cx = cy = PAGINA / 2
    c.setFillColorRGB(1, 1, 1)
    c.rect(cx - lado_badge / 2 - folga, cy - lado_badge / 2 - folga,
           lado_badge + folga * 2, lado_badge + folga * 2, stroke=0, fill=1)
    draw_brand_badge(c, cx - lado_badge / 2, cy - lado_badge / 2, lado_badge)

    c.showPage()
    c.save()
    return buf.getvalue()
