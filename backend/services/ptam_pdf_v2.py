# @module services.ptam_pdf_v2 — Gerador de PDF do PTAM (layout aprovado PTAM_0007_2026_COMPLETO)
# Reproduz fielmente o documento aprovado: capa com logo + bloco verde, sumario clicavel com
# numeracao real (2 passagens), cabecalho/rodape Romatec, 9 secoes + 4 anexos, cards de amostra
# e de foto com foto a esquerda e dados a direita. Le os campos reais do ptam_documents.
# Defensivo: campo ausente -> "—" / placeholder; imagem que falha -> placeholder; nunca lanca.
import os
import re
import logging
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    Flowable, HRFlowable, KeepTogether, Image as RLImage,
)
from reportlab.lib.utils import ImageReader

from utils.extenso import valor_por_extenso
from utils.avaliador import resolver_dados_avaliador, formata_doc, cpf_solicitante
from utils.texto_ia import limpar_texto_ia
from utils.html_render import html_para_blocks, html_to_inline, html_to_plain
from pdf.ptam_pdf import _FINALIDADE_MAP  # fonte única do mapa finalidade-chave → rótulo

logger = logging.getLogger("romatec")

# ── Cores (paleta Modelo 3 — Elegante Escudo Jurídico) ──────────────────────────
VERDE = HexColor('#0B6E4F')
VERDE_MED = HexColor('#2E7D32')
VERDE_CLR = HexColor('#E8F5E9')
DOURADO = HexColor('#B8860B')
DOURADO_CLR = HexColor('#D4AF37')
VERMELHO = HexColor('#CC0000')
CINZA = HexColor('#666666')
CINZA_BRD = HexColor('#CCCCCC')
PRETO = HexColor('#1A1A1A')
BRANCO = colors.white

# ── Dimensoes ─────────────────────────────────────────────────────────────────
W, H = A4
ML = 2.2 * cm
MR = 2.0 * cm
MT = 3.5 * cm
MB = 2.8 * cm
UTIL_W = W - ML - MR
GAP = 0.40 * cm

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'assets', 'avalieimob_logo.png')

NORMAS_RODAPE = ('RomaTec Consultoria Total — ABNT NBR 14653-1/-2/-3 | Res. COFECI 957/2006 | '
                 'Lei 5.194/66 | Lei 6.530/78 | Res. CONFEA 345/90 | Lei 13.786/2018 | CPC art. 156')


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def _txt(v, default="—"):
    if v is None:
        return default
    s = str(v).strip()
    return s if s else default


def fmt_moeda(v) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "R$ 0,00"
    return "R$ " + f"{n:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def fmt_area(v) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{n:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') + " m²"


# ── Apresentação rural (hectare como grandeza principal) ───────────────────
# O sistema sempre armazena área em m² e valor unitário em R$/m². Estas funções
# convertem apenas na exibição do laudo quando o imóvel é rural.
_RURAL_TYPES = {'rural', 'fazenda', 'sitio', 'chacara', 'terreno_rural', 'gleba', 'area_rural'}


def _is_rural(ptam) -> bool:
    return str((ptam or {}).get('property_type') or '').strip().lower() in _RURAL_TYPES


def fmt_area_dual(v) -> str:
    """Rural: 'XX,XXXX ha (XXX.XXX m²)' — 4 casas (ha.are.centiare). Inválido → '—'."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    ha = f"{n / 10000:,.4f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    m2 = f"{n:,.0f}".replace(',', '.')
    return f"{ha} ha ({m2} m²)"


def fmt_area_rural(v, rural) -> str:
    """Área no formato dual (ha + m²) quando rural; senão m²."""
    return fmt_area_dual(v) if rural else fmt_area(v)


def fmt_rs_unit(v, rural) -> str:
    """Valor unitário: R$/ha (R$/m² × 10.000) quando rural; senão R$/m²."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        n = 0.0
    return (fmt_moeda(n * 10000) + "/ha") if rural else (fmt_moeda(n) + "/m²")


def fmt_data(d) -> str:
    if not d:
        return "—"
    if isinstance(d, datetime):
        return d.strftime('%d/%m/%Y')
    return str(d)


def _wrap(text, maxlen=95):
    text = str(text or "")
    out, linha = [], ""
    for palavra in text.split():
        if len(linha) + len(palavra) + 1 > maxlen:
            out.append(linha)
            linha = palavra
        else:
            linha = (linha + " " + palavra).strip()
    if linha:
        out.append(linha)
    return out or [""]


def _load_image_reader(src):
    if not src:
        return None
    try:
        if isinstance(src, (bytes, bytearray)):
            return ImageReader(BytesIO(bytes(src)))
        if isinstance(src, BytesIO):
            return ImageReader(src)
        if isinstance(src, str) and os.path.exists(src):
            return ImageReader(src)
        if isinstance(src, str) and src.startswith(('http://', 'https://')):
            return ImageReader(src)
        return None
    except Exception:
        return None


def _ptam_num(ptam):
    num = ptam.get('numero_ptam') or ptam.get('number') or ''
    num = str(num).strip()
    ano = ''
    for campo in ('conclusion_date', 'vistoria_date', 'resultado_data_referencia'):
        v = ptam.get(campo)
        if v and len(str(v)) >= 4 and str(v)[:4].isdigit():
            ano = str(v)[:4]
            break
    if not ano:
        ano = str(datetime.now().year)
    if num and '/' not in num:
        num = f"{num}/{ano}"
    return num or f"0000/{ano}"


def _draw_logo(canvas, x, y, w, h):
    try:
        if os.path.exists(LOGO_PATH):
            canvas.drawImage(LOGO_PATH, x, y, width=w, height=h,
                             preserveAspectRatio=True, mask='auto')
            return
    except Exception:
        pass
    canvas.setFillColor(VERDE)
    canvas.setFont('Helvetica-Bold', 14)
    canvas.drawString(x, y + h * 0.4, 'ROMATEC')


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  CABECALHO / RODAPE / CAPA                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def make_hf(ptam):
    num = _ptam_num(ptam)
    badge_txt = f'PTAM Nº {num}'
    trt = (ptam.get('art_rrt_numero') or ptam.get('art_trt_numero') or '').strip()
    cidade = (ptam.get('conclusion_city') or ptam.get('property_city') or 'Açailândia-MA').strip()
    from datetime import datetime as _dtnow
    _sub = []
    if trt:
        _sub.append(f'TRT: CFT Nº {trt}')
    if cidade:
        _sub.append(cidade)
    _sub.append(_dtnow.now().strftime('%d/%m/%Y'))
    sub_line = ' · '.join(_sub)
    CINZA_SUB = HexColor('#888888')

    def header_footer(canvas, doc):
        canvas.saveState()
        # 1. Barra dupla no topo: verde (≈5px) + dourado (≈2.5px)
        canvas.setFillColor(VERDE)
        canvas.rect(0, H - 0.18 * cm, W, 0.18 * cm, stroke=0, fill=1)
        canvas.setFillColor(DOURADO)
        canvas.rect(0, H - 0.27 * cm, W, 0.09 * cm, stroke=0, fill=1)
        # 2. Cabeçalho: logo (esq.) + badge PTAM (dir.) + linha TRT/cidade/data
        ly = H - MT + 0.25 * cm
        lh = 1.5 * cm
        _draw_logo(canvas, ML, ly, 3.2 * cm, lh)
        canvas.setFont('Helvetica-Bold', 9.5)
        bw = canvas.stringWidth(badge_txt, 'Helvetica-Bold', 9.5) + 0.55 * cm
        bh = 0.52 * cm
        bx, by = W - MR - bw, ly + lh - bh
        canvas.setFillColor(VERDE)
        canvas.roundRect(bx, by, bw, bh, 0.06 * cm, stroke=0, fill=1)
        canvas.setFillColor(DOURADO)
        canvas.drawCentredString(bx + bw / 2, by + 0.16 * cm, badge_txt)
        canvas.setFillColor(CINZA_SUB)
        canvas.setFont('Helvetica', 7)
        canvas.drawRightString(W - MR, by - 0.32 * cm, sub_line)
        # 3. Separador pós-cabeçalho: dourado + linha verde leve
        sy = ly - 0.1 * cm
        canvas.setStrokeColor(DOURADO)
        canvas.setLineWidth(1.2)
        canvas.line(ML, sy, W - MR, sy)
        canvas.setStrokeColor(VERDE)
        canvas.setLineWidth(0.4)
        canvas.line(ML, sy - 0.06 * cm, W - MR, sy - 0.06 * cm)
        # 4. Rodapé: barra dourada + linha verde + normas + Pág. N
        ry = MB - 0.5 * cm
        canvas.setStrokeColor(DOURADO)
        canvas.setLineWidth(1.0)
        canvas.line(ML, ry + 0.55 * cm, W - MR, ry + 0.55 * cm)
        canvas.setStrokeColor(VERDE)
        canvas.setLineWidth(0.5)
        canvas.line(ML, ry + 0.46 * cm, W - MR, ry + 0.46 * cm)
        # Normas — linha 1 (centralizada)
        canvas.setFillColor(CINZA)
        canvas.setFont('Helvetica', 5.8)
        canvas.drawCentredString(W / 2, ry + 0.30 * cm, NORMAS_RODAPE)
        # Pág. N — linha 2 própria, CENTRALIZADA abaixo das normas (FIX 2: sem sobrepor)
        canvas.setFillColor(VERMELHO)
        canvas.setFont('Helvetica-Bold', 8)
        canvas.drawCentredString(W / 2, ry + 0.10 * cm, f'Pág. {doc.page}')
        canvas.restoreState()

    return header_footer


def make_capa(ptam):
    num = _ptam_num(ptam)
    tipo = _txt(ptam.get('property_label') or ptam.get('property_type'), '')
    # Finalidade = texto livre (quando "outros") OU rótulo legível da chave do dropdown.
    # NÃO usar 'purpose' aqui: é a descrição longa do objetivo e estourava sobre o "Data:".
    _fin_key = ptam.get('finalidade') or ''
    finalidade = html_to_plain(limpar_texto_ia(
        ptam.get('finalidade_outros')
        or _FINALIDADE_MAP.get(_fin_key, _fin_key) or ''))
    cidade = _txt(ptam.get('conclusion_city') or ptam.get('property_city'), '')
    data = _txt(ptam.get('conclusion_date') or ptam.get('vistoria_date'), '')

    def capa(canvas, doc):
        canvas.saveState()
        # 1. Logo grande centralizado
        _draw_logo(canvas, W / 2 - 2.5 * cm, H - 9.0 * cm, 5.0 * cm, 5.0 * cm)
        # 2. Bloco verde
        by, bh = H - 14.2 * cm, 2.8 * cm
        canvas.setFillColor(VERDE)
        canvas.rect(ML, by, UTIL_W, bh, stroke=0, fill=1)
        canvas.setFillColor(BRANCO)
        canvas.setFont('Helvetica-Bold', 18)
        canvas.drawCentredString(W / 2, by + bh * 0.60, 'PARECER TÉCNICO DE AVALIAÇÃO')
        canvas.drawCentredString(W / 2, by + bh * 0.20, 'MERCADOLÓGICA')
        # 3. PTAM nº
        canvas.setFillColor(VERDE)
        canvas.setFont('Helvetica-Bold', 13)
        canvas.drawCentredString(W / 2, H - 15.6 * cm, f'PTAM nº {num}')
        # 4. Tipo
        canvas.setFillColor(PRETO)
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(W / 2, H - 16.4 * cm, tipo)
        # 5. Finalidade
        canvas.setFillColor(PRETO)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(ML, H - 18.2 * cm, 'Finalidade:')
        canvas.setFont('Helvetica', 10)
        yy = H - 18.85 * cm
        for ln in _wrap(finalidade, 95):
            canvas.drawString(ML + 2.2 * cm, yy, ln)
            yy -= 0.46 * cm
        # 6. Cidade / Data
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(W / 2 - 1.5 * cm, H - 22.2 * cm, 'Cidade:')
        canvas.drawString(W / 2 - 1.5 * cm, H - 22.8 * cm, 'Data:')
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(PRETO)
        canvas.drawString(W / 2 + 0.8 * cm, H - 22.2 * cm, cidade)
        canvas.drawString(W / 2 + 0.8 * cm, H - 22.8 * cm, data)
        # 7. Linha dourada
        canvas.setStrokeColor(DOURADO)
        canvas.setLineWidth(1.5)
        canvas.line(ML, MB + 2.1 * cm, W - MR, MB + 2.1 * cm)
        # 8/9. Rodape capa
        canvas.setFillColor(PRETO)
        canvas.setFont('Helvetica-Bold', 8)
        canvas.drawCentredString(W / 2, MB + 1.55 * cm, 'RomaTec Consultoria Total — NBR 14.653')
        canvas.setFont('Helvetica-Bold', 6.2)
        canvas.drawCentredString(W / 2, MB + 0.95 * cm,
            'Base normativa: ABNT NBR 14653-1 | NBR 14653-2 | NBR 14653-3 | '
            'Res. COFECI 957/2006 | Lei 5.194/1966 | Lei 6.530/1978')
        canvas.drawCentredString(W / 2, MB + 0.45 * cm,
            'Res. CONFEA 345/90 | Lei 13.786/2018 | CPC art. 156')
        canvas.restoreState()

    return capa


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  SUMARIO (Flowable, com numeracao real + links)                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝
ITENS_SUM = [
    ('1', 'Identificação e Objetivo', 'sec1', 0),
    ('2', 'Documentação Analisada', 'sec2', 0),
    ('3', 'Identificação do Imóvel', 'sec3', 0),
    ('3.1', 'Caracterização do Imóvel', 'sec3carac', 1),
    ('4', 'Contexto Urbano / Análise da Região', 'sec4', 0),
    ('5', 'Análise Mercadológica e Amostras', 'sec5', 0),
    ('6', 'Metodologia', 'sec6', 0),
    ('7', 'Cálculos e Tratamento Estatístico', 'sec7', 0),
    ('7.1', 'Quadro de Amostras com Classificação', 'sec7quadro', 1),
    ('8', 'Resultado da Avaliação', 'sec8', 0),
    ('8.1', 'Cálculo do Valor Final', 'sec8calc', 1),
    ('9', 'Conclusão e Responsabilidade Técnica', 'sec9', 0),
    ('A.1', 'Anexo I — Ficha do Imóvel, Fotos e Documentos', 'anexo1', 0),
    ('•', 'Documentos do Imóvel (Certidões, IPTU, BCI)', 'anexo1b', 1),
    ('A.2', 'Anexo II — Amostras Comparativas', 'anexo2', 0),
    ('A.3', 'Anexo III — Base Legal e Normativa', 'anexo3', 0),
    ('A.4', 'Anexo IV — Currículo do Avaliador', 'anexo4', 0),
]


class Sumario(Flowable):
    def __init__(self, page_map):
        super().__init__()
        self.page_map = page_map or {}
        self.width = UTIL_W
        self.hh = 0.60 * cm
        self.rh = 0.68 * cm
        self.height = self.hh + len(ITENS_SUM) * self.rh + 0.1 * cm

    def wrap(self, aw, ah):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        # Header
        c.setFillColor(VERDE)
        c.rect(0, h - self.hh, w, self.hh, stroke=0, fill=1)
        c.setFillColor(BRANCO)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(0.3 * cm, h - self.hh + 0.18 * cm, 'Seção')
        c.drawString(2.2 * cm, h - self.hh + 0.18 * cm, 'Título')
        c.drawRightString(w - 0.3 * cm, h - self.hh + 0.18 * cm, 'Página')
        for i, item in enumerate(ITENS_SUM):
            num, titulo, ancora = item[0], item[1], item[2]
            nivel = item[3] if len(item) > 3 else 0
            y = h - self.hh - (i + 1) * self.rh
            if i % 2 == 1:
                c.setFillColor(VERDE_CLR)
                c.rect(0, y, w, self.rh, stroke=0, fill=1)
            pag = str(self.page_map.get(ancora, '—'))
            num_x = 0.4 * cm if nivel == 0 else 0.8 * cm
            tit_x = 2.2 * cm if nivel == 0 else 2.9 * cm
            tit_font = 'Helvetica' if nivel == 0 else 'Helvetica-Oblique'
            tit_size = 9 if nivel == 0 else 8
            # numero secao
            c.setFillColor(VERDE if nivel == 0 else CINZA)
            c.setFont('Helvetica-Bold' if nivel == 0 else 'Helvetica', 9 if nivel == 0 else 8)
            c.drawString(num_x, y + 0.22 * cm, num)
            # titulo
            c.setFillColor(PRETO if nivel == 0 else CINZA)
            c.setFont(tit_font, tit_size)
            c.drawString(tit_x, y + 0.22 * cm, titulo)
            # lideres de ponto
            c.setFillColor(CINZA)
            c.setFont('Helvetica', 7)
            tx_end = w - 1.8 * cm
            tx_start = tit_x + c.stringWidth(titulo, tit_font, tit_size) + 0.4 * cm
            dot_w = c.stringWidth('.', 'Helvetica', 7) + 0.5
            x = tx_start
            while x < tx_end - dot_w:
                c.drawString(x, y + 0.26 * cm, '.')
                x += dot_w + 1.2
            # pagina
            c.setFillColor(VERMELHO)
            c.setFont('Helvetica-Bold', 9 if nivel == 0 else 8)
            c.drawRightString(w - 0.3 * cm, y + 0.22 * cm, pag)
            # link — somente para âncoras realmente renderizadas no documento.
            # Seções condicionais (anexo1b, 3.1, 7.1, 8.1) podem não existir;
            # linkar para um destino inexistente quebra o build ("undefined
            # destination target"). page_map contém apenas âncoras desenhadas.
            if ancora and ancora in self.page_map:
                try:
                    c.linkRect('', ancora, (0, y, w, y + self.rh), relative=1, thickness=0)
                except Exception:
                    pass
            # divisoria
            c.setStrokeColor(CINZA_BRD)
            c.setLineWidth(0.3)
            c.line(0, y, w, y)
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.5)
        c.rect(0, 0, w, h, stroke=1, fill=0)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  CARDS (foto a esquerda, dados a direita)                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def _draw_foto_box(c, fx, fy, fw, fh, img, rotulo):
    """Desenha a foto com clipping arredondado ou placeholder cinza."""
    drawn = False
    if img is not None:
        try:
            c.saveState()
            p = c.beginPath()
            p.roundRect(fx, fy, fw, fh, 0.12 * cm)
            c.clipPath(p, stroke=0, fill=0)
            c.drawImage(img, fx, fy, width=fw, height=fh,
                        preserveAspectRatio=True, anchor='c', mask='auto')
            c.restoreState()
            c.setStrokeColor(CINZA_BRD)
            c.setLineWidth(0.4)
            c.roundRect(fx, fy, fw, fh, 0.12 * cm, stroke=1, fill=0)
            drawn = True
        except Exception:
            drawn = False
    if not drawn:
        c.setFillColor(HexColor('#EEEEEE'))
        c.roundRect(fx, fy, fw, fh, 0.12 * cm, stroke=0, fill=1)
        cx, cy = fx + fw / 2, fy + fh / 2 + 0.3 * cm
        c.setFillColor(HexColor('#BBBBBB'))
        c.circle(cx, cy, 1.0 * cm, stroke=0, fill=1)
        c.setFillColor(HexColor('#888888'))
        c.rect(cx - 0.22 * cm, cy - 0.22 * cm, 0.44 * cm, 0.44 * cm, stroke=0, fill=1)
        c.setFillColor(CINZA)
        c.setFont('Helvetica-Oblique', 7)
        c.drawCentredString(fx + fw / 2, fy + 0.30 * cm, rotulo)


def _campos_dir(c, dx, top_y, titulo, campos, dy=0.60 * cm, val_x=1.85 * cm):
    c.setFillColor(VERDE_MED)
    c.setFont('Helvetica-Bold', 8.5)
    c.drawString(dx, top_y, titulo)
    y = top_y - 0.55 * cm
    for label, valor in campos:
        c.setFillColor(PRETO)
        c.setFont('Helvetica-Bold', 8)
        c.drawString(dx, y, label)
        c.setFont('Helvetica', 8)
        c.drawString(dx + val_x, y, _txt(valor)[:60])
        y -= dy


def _amostra_linhas(c, dx, y, campos, val_x=2.0 * cm, dy=0.48 * cm, val_max=60, fsize=8):
    """Renderiza campos em 1 coluna (largura cheia); valores alinhados em val_x. Retorna y final."""
    for label, valor in campos:
        c.setFillColor(PRETO)
        c.setFont('Helvetica-Bold', fsize)
        c.drawString(dx, y, label)
        c.setFont('Helvetica', fsize)
        c.drawString(dx + val_x, y, _txt(valor)[:val_max])
        y -= dy
    return y


def _amostra_linhas_2col(c, dx, y, campos, col_w=4.55 * cm, val_x=1.95 * cm,
                         dy=0.48 * cm, val_max=20, fsize=7.5):
    """Renderiza campos curtos em 2 colunas, rótulos e valores alinhados. Retorna y final."""
    per_col = (len(campos) + 1) // 2
    # Alinha os valores numa coluna logo após o rótulo MAIS LARGO do bloco — evita
    # colar/sobrepor em rótulos longos ("Sala jantar/copa:", "Banheiro social:").
    # Clamp p/ o valor não invadir a 2ª coluna.
    _maxlbl = max((c.stringWidth(l, 'Helvetica-Bold', fsize) for l, _ in campos), default=0)
    _vx = min(max(val_x, _maxlbl + 0.15 * cm), col_w - 0.45 * cm)
    for i, (label, valor) in enumerate(campos):
        col = 0 if i < per_col else 1
        row = i if col == 0 else i - per_col
        cx = dx + col * col_w
        cy = y - row * dy
        c.setFillColor(PRETO)
        c.setFont('Helvetica-Bold', fsize)
        c.drawString(cx, cy, label)
        c.setFont('Helvetica', fsize)
        c.drawString(cx + _vx, cy, _txt(valor)[:val_max])
    return y - per_col * dy


class AmostraCard(Flowable):
    CH = 9.2 * cm

    def __init__(self, numero, amostra, rural=False):
        super().__init__()
        self.numero = numero
        self.a = amostra or {}
        self.rural = rural
        self.width = UTIL_W
        self.height = self.CH

    def wrap(self, aw, ah):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        w, h, a = self.width, self.height, self.a
        c.setFillColor(BRANCO)
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 0.18 * cm, stroke=1, fill=1)
        # Topo
        c.setFillColor(VERDE_MED)
        c.setFont('Helvetica-Bold', 10)
        c.drawString(0.3 * cm, h - 0.52 * cm, f'Amostra {self.numero}')
        c.setFillColor(CINZA)
        c.setFont('Helvetica-Oblique', 8)
        endereco = a.get('address') or a.get('endereco') or ''
        bairro = a.get('neighborhood') or ''
        end_full = endereco + (f', {bairro}' if bairro else '')
        c.drawString(4.2 * cm, h - 0.52 * cm, end_full[:75])
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.3)
        c.line(0.2 * cm, h - 0.68 * cm, w - 0.2 * cm, h - 0.68 * cm)
        # Foto
        FW, FH, FX, FY = 7.0 * cm, h - 0.90 * cm, 0.22 * cm, 0.12 * cm
        img = _load_image_reader(a.get('_image_bytes') or a.get('foto_url'))
        _draw_foto_box(c, FX, FY, FW, FH, img, 'Fotografia')
        # Dados à direita da foto
        dx = FX + FW + 0.42 * cm
        area_dir = w - 0.20 * cm - dx  # largura útil dos dados
        area = a.get('area')
        vpm = a.get('value_per_sqm')
        _ru = self.rural
        _vu_lbl = 'R$/ha:' if _ru else 'R$/m²:'
        _vu_val = (fmt_rs_unit(vpm, _ru) if vpm else '—')

        def _tem(x):
            return x not in (None, '', 0, '0', 0.0)

        # Área com justificativa da composição (AE = Área da Edificação + AT = Área do
        # Terreno), exibida só quando ambas existirem (urbano).
        _area_str = fmt_area_rural(area, _ru)
        _ae, _at = a.get('area_construida_m2'), a.get('area_terreno_m2')
        if not _ru and _tem(_ae) and _tem(_at):
            _area_str = f"{_area_str} (AE {fmt_area(_ae)} + AT {fmt_area(_at)})"

        # Bloco A — principais (largura cheia; valores podem ser longos).
        principais = [
            ('Tipo:', a.get('tipo') or a.get('tipo_amostra') or 'Não informado'),
            ('Área:', _area_str),
            ('Valor:', fmt_moeda(a.get('value'))),
            (_vu_lbl, _vu_val),
        ]
        # Bloco B — características (curtas; 2 colunas).
        caracteristicas = []
        if _ru:
            for _lbl, _k, _sfx in [
                ('Topografia:', 'topografia', None), ('Solo:', 'solo', None),
                ('Rec. hídricos:', 'recursos_hidricos', None), ('Vegetação:', 'vegetacao', None),
                ('Atividade:', 'atividade', None), ('Lotação:', 'lotacao_ua_ha', ' UA/ha'),
                ('Benfeitorias:', 'benfeitorias', None), ('Sede/casa:', 'sede', None),
            ]:
                if _tem(a.get(_k)):
                    caracteristicas.append((_lbl, f"{a.get(_k)}{_sfx}" if _sfx else a.get(_k)))
        else:
            for _lbl, _k in [('Área constr.:', 'area_construida_m2'),
                             ('Sala de estar:', 'sala_estar'), ('Sala jantar/copa:', 'sala_jantar'),
                             ('Cozinha:', 'cozinha'), ('Quarto social:', 'quarto_social'),
                             ('Suíte simples:', 'suite_simples'), ('Suíte master:', 'suite_master'),
                             ('Banheiro social:', 'banheiro_social'), ('Lavabo:', 'lavabo'),
                             ('Área de serviço:', 'area_servico'), ('Varanda/sacada:', 'varanda'),
                             ('Varanda gourmet:', 'varanda_gourmet'), ('Escritório:', 'escritorio'),
                             ('Despensa:', 'despensa'), ('Piscina:', 'piscina'),
                             ('Garagem:', 'vagas'),
                             ('Idade (anos):', 'idade_anos'), ('Zoneamento:', 'zoneamento')]:
                if _tem(a.get(_k)):
                    caracteristicas.append((_lbl, a.get(_k)))
        # Bloco C — localização/contato (largura cheia).
        contato = []
        if a.get('municipio') or a.get('uf'):
            _muf = (a.get('municipio') or '') + (f"/{a.get('uf')}" if a.get('uf') else '')
            contato.append(('Município:', _muf.strip('/')))
        contato += [
            ('Fonte:', a.get('source')),
            ('Data:', a.get('collection_date')),
            ('Telefone:', a.get('contact_phone')),
        ]

        # Título
        c.setFillColor(VERDE_MED)
        c.setFont('Helvetica-Bold', 8.5)
        y = h - 1.05 * cm
        c.drawString(dx, y, '1. Identificação e Caracterização')
        y -= 0.52 * cm

        # Espaçamento adaptativo: distribui as linhas para preencher a altura do card.
        _rows = len(principais) + ((len(caracteristicas) + 1) // 2) + len(contato)
        _dy = (y - 0.40 * cm) / max(_rows, 1)
        _dy = max(0.46 * cm, min(_dy, 0.74 * cm))
        _colw = area_dir / 2.0

        y = _amostra_linhas(c, dx, y, principais, dy=_dy)
        if caracteristicas:
            y = _amostra_linhas_2col(c, dx, y, caracteristicas, col_w=_colw, dy=_dy)
        _amostra_linhas(c, dx, y, contato, dy=_dy)


class PlantaBaixaCard(Flowable):
    """Planta baixa da amostra — ocupa o espaço abaixo do AmostraCard na mesma
    página (mantidos juntos via KeepTogether). A imagem vem do upload já como
    PNG 300 DPI (PDF convertido em /upload/image)."""
    CH = 12.0 * cm

    def __init__(self, numero, img):
        super().__init__()
        self.numero = numero
        self.img = img
        self.width = UTIL_W
        self.height = self.CH

    def wrap(self, aw, ah):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(BRANCO)
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 0.18 * cm, stroke=1, fill=1)
        c.setFillColor(VERDE_MED)
        c.setFont('Helvetica-Bold', 10)
        c.drawString(0.3 * cm, h - 0.52 * cm, f'Planta Baixa — Amostra {self.numero}')
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.3)
        c.line(0.2 * cm, h - 0.68 * cm, w - 0.2 * cm, h - 0.68 * cm)
        fx, fy = 0.3 * cm, 0.3 * cm
        fw, fh = w - 0.6 * cm, h - 1.05 * cm
        _draw_foto_box(c, fx, fy, fw, fh, _load_image_reader(self.img), 'Planta Baixa')


class FotoCard(Flowable):
    CH = 10.5 * cm

    def __init__(self, numero, legenda, total, img=None, gps='', data_hora=''):
        super().__init__()
        self.numero = numero
        self.legenda = legenda or ''
        self.total = total
        self.img = img
        self.gps = gps
        self.data_hora = data_hora
        self.width = UTIL_W
        self.height = self.CH

    def wrap(self, aw, ah):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(BRANCO)
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 0.18 * cm, stroke=1, fill=1)
        c.setFillColor(VERDE_MED)
        c.setFont('Helvetica-Bold', 10)
        c.drawString(0.3 * cm, h - 0.52 * cm, f'Foto {self.numero}')
        c.setFillColor(CINZA)
        c.setFont('Helvetica-Oblique', 8)
        c.drawString(4.2 * cm, h - 0.52 * cm, str(self.legenda)[:75])
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.3)
        c.line(0.2 * cm, h - 0.68 * cm, w - 0.2 * cm, h - 0.68 * cm)
        FW, FH, FX, FY = 7.0 * cm, h - 0.90 * cm, 0.22 * cm, 0.12 * cm
        img = _load_image_reader(self.img)
        _draw_foto_box(c, FX, FY, FW, FH, img, 'Fotografia')
        dx = FX + FW + 0.42 * cm
        campos = [
            ('Foto nº:', f'{self.numero} de {self.total}'),
            ('Legenda:', self.legenda),
            ('Imóvel:', 'Avaliando'),
            ('GPS:', self.gps or '—'),
            ('Data/Hora:', self.data_hora or '—'),
        ]
        _campos_dir(c, dx, h - 1.05 * cm, 'Informações da Foto', campos, dy=0.62 * cm, val_x=1.9 * cm)


class DocCard(Flowable):
    """Documento digitalizado (certidao/IPTU/BCI): cabecalho com nome + imagem (ou placeholder PDF)."""
    CH = 13.0 * cm

    def __init__(self, numero, nome, img_bytes=None, content_type='image/jpeg'):
        super().__init__()
        self.numero = numero
        self.nome = nome or f'Documento {numero}'
        self.img = img_bytes
        self.ct = (content_type or '').lower()
        self.width = UTIL_W
        self.height = self.CH

    def wrap(self, aw, ah):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(BRANCO)
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 0.18 * cm, stroke=1, fill=1)
        c.setFillColor(VERDE_MED)
        c.setFont('Helvetica-Bold', 9.5)
        c.drawString(0.4 * cm, h - 0.62 * cm, f'Documento {self.numero}: {str(self.nome)[:72]}')
        c.setStrokeColor(CINZA_BRD)
        c.setLineWidth(0.3)
        c.line(0.2 * cm, h - 0.88 * cm, w - 0.2 * cm, h - 0.88 * cm)
        fx, fy = 0.3 * cm, 0.3 * cm
        fw, fh = w - 0.6 * cm, h - 1.25 * cm
        if 'pdf' in self.ct:
            c.setFillColor(HexColor('#EEEEEE'))
            c.roundRect(fx, fy, fw, fh, 0.12 * cm, stroke=0, fill=1)
            c.setFillColor(CINZA)
            c.setFont('Helvetica-Oblique', 10)
            c.drawCentredString(fx + fw / 2, fy + fh / 2, 'Documento em PDF anexado ao processo.')
        else:
            _draw_foto_box(c, fx, fy, fw, fh, _load_image_reader(self.img), 'Documento')


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  DOC com tracking de paginas (2 passagens)                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝
class TrackingDoc(SimpleDocTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anchor_pages = {}

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            txt = getattr(flowable, 'text', '') or ''
            m = re.search(r'name="([^"]+)"', txt)
            if m:
                self.anchor_pages[m.group(1)] = self.page


# ── Estilos ───────────────────────────────────────────────────────────────────
sNormal = ParagraphStyle('n', fontName='Helvetica', fontSize=9, textColor=PRETO, leading=13)
sBody = ParagraphStyle('b', fontName='Helvetica', fontSize=9, textColor=PRETO,
                       leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
sSec = ParagraphStyle('s', fontName='Helvetica-Bold', fontSize=14, textColor=VERDE,
                      alignment=TA_CENTER, spaceBefore=6, spaceAfter=6)
sSub = ParagraphStyle('sub', fontName='Helvetica-Bold', fontSize=10, textColor=VERDE_MED,
                      spaceBefore=8, spaceAfter=4)
sCenter = ParagraphStyle('c', parent=sBody, alignment=TA_CENTER)
sCell = ParagraphStyle('cell', fontName='Helvetica', fontSize=9, textColor=PRETO, leading=12)
sCellJ = ParagraphStyle('cellJ', parent=sCell, alignment=TA_JUSTIFY)  # FIX 3: texto longo justificado
sPag = ParagraphStyle('p', fontName='Helvetica', fontSize=7.5, textColor=CINZA,
                      alignment=TA_CENTER, spaceAfter=4)
sTitulo = ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=20, textColor=VERDE,
                         alignment=TA_CENTER)


class TituloSecao(Flowable):
    """Título de seção Modelo 3: círculo numerado verde + título + linha tracejada dourada."""
    def __init__(self, texto, width):
        super().__init__()
        m = re.match(r'^(\d+)\.\s*(.+)$', (texto or '').strip())
        if m:
            self.num, self.titulo = m.group(1), m.group(2)
        else:
            self.num, self.titulo = None, (texto or '').strip()
        self.width = width
        self.height = 0.85 * cm

    def wrap(self, aw, ah):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        cy = h * 0.5
        x = 0.0
        if self.num is not None:
            r = 0.32 * cm
            c.setFillColor(VERDE)
            c.circle(r, cy, r, stroke=0, fill=1)
            c.setFillColor(DOURADO)
            c.setFont('Helvetica-Bold', 10.5)
            c.drawCentredString(r, cy - 0.13 * cm, self.num)
            x = 2 * r + 0.25 * cm
        titulo = self.titulo.upper()
        c.setFillColor(VERDE)
        c.setFont('Helvetica-Bold', 10.5)
        c.drawString(x, cy - 0.13 * cm, titulo)
        tw = c.stringWidth(titulo, 'Helvetica-Bold', 10.5)
        lx = x + tw + 0.3 * cm
        if lx < w:
            c.setStrokeColor(DOURADO)
            c.setLineWidth(1.0)
            c.setDash(2, 2)
            c.line(lx, cy, w, cy)
            c.setDash()


def sec(texto, ancora=None):
    out = []
    if ancora:
        out.append(Paragraph(f'<a name="{ancora}"/>', sNormal))
    out.append(TituloSecao(texto, UTIL_W))
    out.append(Spacer(1, 6))
    return out


def subsec(texto, ancora=None):
    out = []
    if ancora:
        out.append(Paragraph(f'<a name="{ancora}"/>', sNormal))
    out.append(Paragraph(texto, sSub))
    return out


def tbl(dados, cw=None):
    cw = cw or [5.0 * cm, UTIL_W - 5.0 * cm]
    # Label (1ª coluna) como Paragraph branco/negrito → quebra a linha em vez de cortar o texto.
    _sLbl = ParagraphStyle('tblLbl', fontName='Helvetica-Bold', fontSize=9,
                           textColor=BRANCO, leading=11)
    # FIX 3: valor com >80 chars é justificado; curto fica à esquerda.
    linhas = [[Paragraph(_esc_xml(_txt(lb)), _sLbl),
               Paragraph(_txt(vl), sCellJ if len(_txt(vl)) > 80 else sCell)] for lb, vl in dados]
    if not linhas:
        linhas = [[Paragraph("—", _sLbl), Paragraph("—", sCell)]]
    t = Table(linhas, colWidths=cw)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), VERDE),
        ('TEXTCOLOR', (0, 0), (0, -1), BRANCO),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.4, CINZA_BRD),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    for i in range(len(linhas)):
        style.add('BACKGROUND', (1, i), (1, i), VERDE_CLR if i % 2 else BRANCO)
    t.setStyle(style)
    return t


def tbl_header(header, linhas, cw, bold_last=False):
    data = [header] + (linhas or [["—"] * len(header)])
    t = Table(data, colWidths=cw, repeatRows=1)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), VERDE),
        ('TEXTCOLOR', (0, 0), (-1, 0), BRANCO),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.4, CINZA_BRD),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BRANCO, VERDE_CLR]),
    ])
    if bold_last:
        style.add('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
        style.add('TEXTCOLOR', (0, -1), (-1, -1), VERDE)
    t.setStyle(style)
    return t


# Cores do destaque da faixa INCRA (azul = dentro / vermelho = fora-mais-próxima).
AZUL_FAIXA = HexColor('#BBDEFB')
AZUL_TEXTO = HexColor('#1565C0')
VERM_FAIXA = HexColor('#FFCDD2')
VERM_TEXTO = HexColor('#C62828')


# Nota técnica padrão (RAMT-MA) — usada quando a tabela não traz notas próprias.
_INCRA_NOTAS_PADRAO = (
    "(1) VTI = Valor Total do Imóvel (inclui benfeitorias); para obter VTN deduzir benfeitorias "
    "conforme laudo de vistoria. (2) Faixas mín/máx estimadas pelo perito aplicando ±30% sobre a "
    "média amostral, conforme metodologia INCRA PPR. (3) Atualização monetária obrigatória via "
    "IPCA-E entre data-base jul/2022 e data da avaliação (NBR 14653-3, item 8.2.1). (4) Dados de "
    "pesquisa primária do avaliador devem complementar e prevalecer sobre os referenciais do RAMT "
    "quando disponíveis (NBR 14653-3, item 8.1). (5) Fonte: INCRA/SR-21-MA — RAMT-MA 2022, "
    "SEI n.º 15897588 / PPR SR(MA) 15854957."
)


def _incra_faixa_match(faixas, media_ha):
    """(índice, dentro) — faixa onde vr_min<=media<=vr_max; senão a mais próxima."""
    lista = faixas or []
    m = float(media_ha or 0)
    ci, cd = 0, float('inf')
    for i, f in enumerate(lista):
        mn = float((f or {}).get('vr_min') or 0)
        mx = float((f or {}).get('vr_max') or 0)
        if mn <= m <= mx:
            return i, True
        d = min(abs(m - mn), abs(m - mx))
        if d < cd:
            cd, ci = d, i
    return ci, False


def incra_section(ptam, media_ha):
    """Seção 'REFERÊNCIA INCRA — Valores de Terra Nua' (somente laudo rural).
    Retorna lista de flowables; vazia se não houver tabela injetada em ptam['incra_tabela']."""
    tab = (ptam or {}).get('incra_tabela') or {}
    faixas = tab.get('faixas') or []
    if not faixas:
        # Sem tabela cadastrada: mostra a seção com aviso discreto (não silencia).
        _sAviso = ParagraphStyle('incraAviso', fontName='Helvetica-Oblique', fontSize=8.5,
                                 textColor=CINZA, leading=11)
        out = subsec('REFERÊNCIA INCRA — Valores de Terra Nua', 'sec7incra')
        out.append(Paragraph(
            'Tabela INCRA de Valores de Terra Nua não cadastrada para esta região. '
            'Cadastre em Ferramentas &#8594; Tabelas INCRA para que a referência apareça no laudo.',
            _sAviso))
        out.append(Spacer(1, 8))
        return out
    idx, dentro = _incra_faixa_match(faixas, media_ha)

    def _milhar(v):
        # Valor exato (sem arredondar): inteiro com milhar; mantém decimais se houver.
        try:
            n = float(v)
        except (TypeError, ValueError):
            return '—'
        if n == int(n):
            return f"{int(n):,}".replace(',', '.')
        return f"{n:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    _sCard = ParagraphStyle('incraCard', fontName='Helvetica', fontSize=7.5, leading=9, textColor=PRETO)
    _sCellL = ParagraphStyle('incraCellL', fontName='Helvetica', fontSize=8, leading=10)
    _sHd = ParagraphStyle('incraHd', fontName='Helvetica-Bold', fontSize=7.5, leading=9,
                          textColor=BRANCO, alignment=TA_CENTER)
    _sHdR = ParagraphStyle('incraHdR', parent=_sHd, alignment=2)  # right
    out = []
    out += subsec('REFERÊNCIA INCRA — Valores de Terra (RAMT)', 'sec7incra')

    # Cabeçalho — 4 cards (Região / Polo regional / Fonte / Norma)
    def _card(lbl, val):
        return Paragraph(f'<font size=6 color="#999999">{_esc_xml(lbl)}</font><br/>'
                         f'<b>{_esc_xml(_txt(val, "—"))}</b>', _sCard)
    _fonte_v = f"{tab.get('fonte', '—')}" + (f" · {tab.get('vigencia')}" if tab.get('vigencia') else '')
    cards = [[_card('REGIÃO', tab.get('regiao')),
              _card('POLO REGIONAL', tab.get('polo_regional') or tab.get('municipio')),
              _card('FONTE', _fonte_v),
              _card('NORMA', tab.get('norma') or 'NBR 14653-3:2019')]]
    tc = Table(cards, colWidths=[UTIL_W / 4.0] * 4)
    tc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F5F5F5')),
        ('BOX', (0, 0), (-1, -1), 0.4, CINZA_BRD),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, CINZA_BRD),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    out.append(tc)
    out.append(Spacer(1, 6))

    # Tabela de tipologias (VTI mín / médio / máx + N amostras)
    header = [Paragraph('Tipologia de uso', _sHd),
              Paragraph('VTI mín.<br/>(R$/ha)', _sHdR), Paragraph('VTI médio<br/>(R$/ha)', _sHdR),
              Paragraph('VTI máx.<br/>(R$/ha)', _sHdR), Paragraph('N<br/>amostras', _sHdR)]
    data = [header]
    for f in faixas:
        data.append([
            Paragraph(_txt(f.get('faixa'), '—'), _sCellL),
            _milhar(f.get('vr_min')), _milhar(f.get('vr_medio')), _milhar(f.get('vr_max')),
            (str(f.get('n_amostras')) if f.get('n_amostras') is not None else '—'),
        ])
    cw = [UTIL_W - (3 * 2.55 + 1.9) * cm, 2.55 * cm, 2.55 * cm, 2.55 * cm, 1.9 * cm]
    t = Table(data, colWidths=cw, repeatRows=1)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), VERDE),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.4, CINZA_BRD),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BRANCO, VERDE_CLR]),
        ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),  # VTI médio em negrito
    ])
    r = idx + 1
    _fundo = AZUL_FAIXA if dentro else VERM_FAIXA
    _texto = AZUL_TEXTO if dentro else VERM_TEXTO
    style.add('BACKGROUND', (0, r), (-1, r), _fundo)
    style.add('TEXTCOLOR', (0, r), (-1, r), _texto)
    style.add('LINEBEFORE', (0, r), (0, r), 3, _texto)
    t.setStyle(style)
    out.append(t)

    # Legenda do valor avaliando
    _leg = ParagraphStyle('incraLeg', fontName='Helvetica-Bold', fontSize=8.5,
                          textColor=_texto, leading=11)
    _faixa_nome = _esc_xml(_txt((faixas[idx] or {}).get('faixa'), '—'))
    _msg = (f"&#9658; Valor da avaliação: {fmt_moeda(media_ha)}/ha &#8212; "
            + (f'dentro da faixa: &#8220;{_faixa_nome}&#8221;' if dentro
               else f'faixa mais próxima: &#8220;{_faixa_nome}&#8221;'))
    out.append(Spacer(1, 3))
    out.append(Paragraph(_msg, _leg))

    # Fatores de homogeneização (NBR 14653-3)
    fatores = tab.get('fatores') or []
    if fatores:
        out.append(Spacer(1, 6))
        out.append(Paragraph(f"<b>Fatores de homogeneização sugeridos — {_esc_xml(tab.get('norma') or 'NBR 14653-3')}</b>",
                             ParagraphStyle('incraFatT', fontName='Helvetica-Bold', fontSize=8, textColor=VERDE)))
        out.append(Spacer(1, 2))
        fdata = [[Paragraph('Fator', _sHd), Paragraph('Variável', _sHd), Paragraph('Faixa de ajuste', _sHdR)]]
        for ft in fatores:
            fdata.append([
                Paragraph(_txt(ft.get('fator'), '—'), _sCellL),
                Paragraph(_txt(ft.get('variavel'), ''), _sCellL),
                _txt(ft.get('faixa_ajuste'), '—'),
            ])
        ft_tbl = Table(fdata, colWidths=[4.6 * cm, UTIL_W - 4.6 * cm - 3.4 * cm, 3.4 * cm], repeatRows=1)
        ft_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERDE),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.4, CINZA_BRD),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BRANCO, VERDE_CLR]),
        ]))
        out.append(ft_tbl)

    # Notas técnicas (usa as da tabela; se não houver, aplica a nota padrão RAMT).
    _notas = limpar_texto_ia(tab.get('notas')) if tab.get('notas') else _INCRA_NOTAS_PADRAO
    if _notas:
        out.append(Spacer(1, 4))
        out.append(Paragraph(f"<b>Notas técnicas:</b> {_esc_xml(_notas)}",
                             ParagraphStyle('incraNotas', fontName='Helvetica', fontSize=7,
                                            textColor=CINZA, leading=9, alignment=TA_JUSTIFY)))
    out.append(Spacer(1, 8))
    return out


def caixa_valor(valor_total, extenso):
    body = [
        [Paragraph(f'Valor de Mercado Avaliado: {fmt_moeda(valor_total)}',
                   ParagraphStyle('cv1', fontName='Helvetica-Bold', fontSize=13,
                                  textColor=VERDE, alignment=TA_CENTER))],
        [Paragraph(f'({_txt(extenso, "")})',
                   ParagraphStyle('cv2', fontName='Helvetica', fontSize=9,
                                  textColor=PRETO, alignment=TA_CENTER))],
        [Paragraph('(válido por 180 dias)',
                   ParagraphStyle('cv3', fontName='Helvetica-Oblique', fontSize=8.5,
                                  textColor=CINZA, alignment=TA_CENTER))],
    ]
    t = Table(body, colWidths=[UTIL_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F1F8F4')),
        ('BOX', (0, 0), (-1, -1), 1.2, VERDE),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    return t


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  MONTAGEM DAS SECOES                                                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def _g(p, k, default=None):
    v = p.get(k)
    return v if v not in (None, '') else default


def _leg(f, n):
    if isinstance(f, dict):
        return f.get('legenda') or f.get('description') or f.get('caption') or f'Foto {n}'
    return f'Foto {n}'


def _exif_gps_data(img_bytes):
    """Extrai (gps_str, data_hora_str) do EXIF da imagem. Nunca lanca."""
    try:
        from PIL import Image as _PILImg, ExifTags as _ExifTags
        im = _PILImg.open(BytesIO(img_bytes))
        exif = im._getexif() or {}
        tags = {_ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        dh = tags.get('DateTimeOriginal') or tags.get('DateTime') or ''
        if dh:
            try:
                d, t = str(dh).split(' ', 1)
                y, mo, da = d.split(':')
                dh = f"{da}/{mo}/{y} {t}"
            except Exception:
                dh = str(dh)
        gps = ''
        gi = tags.get('GPSInfo')
        if gi:
            g = {_ExifTags.GPSTAGS.get(k, k): v for k, v in gi.items()}

            def _conv(coord, ref):
                dd = float(coord[0]) + float(coord[1]) / 60 + float(coord[2]) / 3600
                return -dd if ref in ('S', 'W') else dd
            if 'GPSLatitude' in g and 'GPSLongitude' in g:
                lat = _conv(g['GPSLatitude'], g.get('GPSLatitudeRef', 'N'))
                lon = _conv(g['GPSLongitude'], g.get('GPSLongitudeRef', 'E'))
                gps = f"{lat:.6f}, {lon:.6f}"
                alt = g.get('GPSAltitude')
                if alt:
                    try:
                        gps += f" alt {float(alt):.0f}m"
                    except Exception:
                        pass
        return gps, dh
    except Exception:
        return '', ''


def _fotocard(f, n, total):
    """Cria um FotoCard a partir do dict da foto, extraindo GPS/Data do EXIF se faltarem."""
    b = f.get('_image_bytes') if isinstance(f, dict) else None
    g = (f.get('gps') if isinstance(f, dict) else '') or ''
    dh = (f.get('data_hora') if isinstance(f, dict) else '') or ''
    if (not g or not dh) and b:
        eg, ed = _exif_gps_data(b)
        g = g or eg
        dh = dh or ed
    return FotoCard(n, _leg(f, n), total, b, g, dh)


# Rótulos legíveis dos documentos analisados (Seção 2) — corrige IDs crus no PDF.
DOCUMENTO_LABELS = {
    'matricula': 'Certidão de Matrícula do Imóvel',
    'iptu': 'Carnê de IPTU',
    'planta': 'Planta / Projeto Aprovado',
    'escritura': 'Escritura Pública / Contrato',
    'fotos': 'Relatório Fotográfico do Imóvel',
    'habite_se': 'Habite-se / Auto de Conclusão de Obra',
    'geo_rural': 'Georreferenciamento (SIGEF / INCRA)',
    'geo_sigef': 'Certificado SIGEF',
    'ccir': 'CCIR — Certificado de Cadastro de Imóvel Rural',
    'itr': 'ITR — Imposto Territorial Rural',
    'car': 'CAR — Cadastro Ambiental Rural',
    'nirf': 'NIRF / CIB — Cadastro do Imóvel na Receita Federal',
    'cib': 'CIB — Cadastro Imobiliário Brasileiro',
    'certidoes': 'Certidões Negativas (débitos e ônus)',
    'onus_reais': 'Certidão de Ônus Reais',
    'bci': 'BCI — Boletim de Cadastro Imobiliário',
    'memorial': 'Memorial Descritivo',
    'patologia': 'Laudo de Patologia das Construções',
    'art_trt': 'ART / TRT — Responsabilidade Técnica',
    'licenca_ambiental': 'Licença Ambiental',
    'valor_venal': 'Certidão de Valor Venal',
    'outros_docs': 'Outros Documentos',
}


def _doc_label(d):
    k = str(d or '').strip()
    return DOCUMENTO_LABELS.get(k) or DOCUMENTO_LABELS.get(k.lower()) or k


def _preenchido(v):
    """True se o valor é relevante para o laudo. 0 / vazio / '—' / 'Não' são omitidos."""
    if v is None:
        return False
    s = str(v).strip()
    if s.lower() in ('', '0', '0.0', '0,00', '0,0', '—', '-', 'não', 'nao', 'r$ 0,00', '0 m²'):
        return False
    try:
        return float(s.replace('.', '').replace(',', '.').split()[0]) != 0
    except (ValueError, TypeError, IndexError):
        return bool(s)


_MESES_PT = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
             'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']


def _data_extenso(iso):
    """ISO -> '03 de junho de 2026.' (cai para hoje se inválido)."""
    from datetime import datetime as _dt
    try:
        d = _dt.fromisoformat(str(iso or '')[:10])
    except Exception:
        d = _dt.now()
    return f'{d.day:02d} de {_MESES_PT[d.month - 1]} de {d.year}.'


def _esc_xml(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _bloco_conclusao(st, titulo, texto):
    """Renderiza um bloco da Seção 9 na íntegra, justificado, com subseções 9.x em verde."""
    txt = limpar_texto_ia(texto)
    if not txt:
        return
    st.append(Spacer(1, 6))
    st.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_BRD, spaceAfter=6))
    if titulo:
        st.append(Paragraph(titulo, ParagraphStyle('c9t', fontName='Helvetica-Bold',
                                                   fontSize=10, textColor=VERDE, spaceAfter=4)))
    # Aceita texto puro OU HTML do RichTextEditor (negrito/itálico/listas/alinhamento).
    for blk in html_para_blocks(txt):
        markup = blk['markup']
        if not markup:
            continue
        plano = re.sub(r'<[^>]+>', '', markup).strip()
        if re.match(r'^\d+\.\d+[\s\.]', plano):
            st.append(Paragraph(markup, ParagraphStyle('c9s', fontName='Helvetica-Bold',
                                                       fontSize=10, textColor=VERDE,
                                                       spaceBefore=4, spaceAfter=3)))
        else:
            _al = {'left': 0, 'center': 1, 'right': 2, 'justify': 4}.get(blk['align'], 4)
            _extra = {'alignment': _al}
            if blk['bullet']:
                _extra['leftIndent'] = 0.5 * cm
            st.append(Paragraph(markup, ParagraphStyle('c9b', parent=sBody, **_extra)))


def build_story(ptam, page_map):
    # BUG-04: resolve o perfil do avaliador para FONTE ÚNICA (nome, CNAI, CRECI/MA,
    # CFT, INCRA, ART/TRT, contatos) — sem hardcode. Alimenta assinatura e currículo.
    perfil = resolver_dados_avaliador(perfil=ptam.get('_perfil') or {}, ptam=ptam)
    fotos = ptam.get('fotos_imovel') or []
    amostras = ptam.get('market_samples') or []
    num = _ptam_num(ptam)
    st = []

    # ── 1. Identificacao e Objetivo ──
    st += sec('1. IDENTIFICAÇÃO E OBJETIVO', 'sec1')
    dados1 = [
        ('Número do PTAM', num),
        ('Finalidade', ptam.get('finalidade_outros')
            or _FINALIDADE_MAP.get(ptam.get('finalidade') or '', ptam.get('finalidade'))),
        ('Solicitante', ptam.get('solicitante_nome') or ptam.get('solicitante')),
        ('CPF/CNPJ', cpf_solicitante(ptam)),
        ('Endereço', ptam.get('solicitante_endereco')),
        ('Telefone', ptam.get('solicitante_telefone')),
    ]
    for lb, campo in [('Processo Judicial', 'judicial_process'), ('Ação Judicial', 'judicial_action'),
                      ('Fórum / Vara', 'forum'), ('Requerente', 'requerente'),
                      ('Requerido', 'requerido'), ('Juiz', 'judge')]:
        if _g(ptam, campo):
            dados1.append((lb, ptam.get(campo)))
    st.append(tbl(dados1))
    # Objetivo da avaliação (descrição livre 'purpose') — íntegra, justificada.
    # Antes só aparecia (errado) na capa; agora vive na seção 1, seu lugar correto.
    _obj = html_to_inline(limpar_texto_ia(ptam.get('purpose')))
    if _obj:
        st.append(Spacer(1, 8))
        st += subsec('Objetivo da Avaliação')
        st.append(Paragraph(_obj, sBody))

    # ── 2. Documentacao Analisada ──
    st.append(PageBreak())
    st += sec('2. DOCUMENTAÇÃO ANALISADA', 'sec2')
    docs_analisados = [d for d in (ptam.get('documentos_analisados') or []) if str(d).strip()]
    docs_scan = ptam.get('fotos_documentos') or []
    if docs_analisados:
        st += subsec('Documentos Analisados')
        linhas_doc = [[str(i), _doc_label(d)] for i, d in enumerate(docs_analisados, 1)]
        st.append(tbl_header(['Nº', 'Documento'], linhas_doc, [1.4 * cm, UTIL_W - 1.4 * cm]))
        st.append(Spacer(1, 8))
    else:
        st.append(Paragraph('<b>Matrícula do imóvel</b> | Fotografias do imóvel', sBody))
    st.append(Paragraph(f'<b>Fotos do imóvel:</b> {len(fotos)} foto(s) anexada(s)', sBody))
    if docs_scan:
        st.append(Paragraph(f'<b>Documentos digitalizados:</b> {len(docs_scan)} arquivo(s) anexado(s)', sBody))

    # ── 3. Identificacao do Imovel ──
    st.append(PageBreak())
    st += sec('3. IDENTIFICAÇÃO DO IMÓVEL', 'sec3')
    _cidade_uf = ' — '.join(x for x in [
        _txt(ptam.get('property_city'), ''), _txt(ptam.get('property_state'), '')
    ] if x)
    _ident_rows = [
        ('Tipo', ptam.get('property_type')),
        ('Endereço', ptam.get('property_address')),
        ('Bairro', ptam.get('property_neighborhood')),
        ('CEP', ptam.get('property_cep')),
        ('Matrícula', ptam.get('property_matricula')),
        ('Cartório', ptam.get('property_cartorio')),
        ('Cidade/UF', _cidade_uf),
    ]
    # Linhas vazias (ex.: Bairro em imóvel rural) não vão ao laudo.
    _ident_rows = [(lb, _txt(vl)) for lb, vl in _ident_rows if _preenchido(vl)]
    st.append(tbl(_ident_rows or [('Identificação', 'Não informada')]))
    # Áreas adicionais (quando informadas)
    _areas_extra = []
    if ptam.get('property_area_sqm'):
        _areas_extra.append(('Área Total (m²)', fmt_area(ptam.get('property_area_sqm'))))
    if ptam.get('property_area_ha'):
        _areas_extra.append(('Área (hectares)', f"{_txt(ptam.get('property_area_ha'))} ha"))
    if _areas_extra:
        st.append(tbl(_areas_extra))
    # Descrição Geral do Imóvel (texto livre da matrícula) — íntegra.
    _desc = html_to_inline(limpar_texto_ia(ptam.get('property_description')))
    if _desc:
        st.append(Spacer(1, 8))
        st += subsec('Descrição Geral do Imóvel')
        st.append(Paragraph(_desc, sBody))
    # Confrontações / Limites
    _conf = html_to_inline(limpar_texto_ia(ptam.get('property_confrontations')))
    if _conf:
        st.append(Spacer(1, 6))
        st += subsec('Confrontações / Limites')
        st.append(Paragraph(_conf, sBody))
    props = [p for p in (ptam.get('proprietarios') or []) if isinstance(p, dict) and p.get('nome')]
    if props:
        st.append(Spacer(1, 8))
        st += subsec('Proprietário(s) do Imóvel')
        # Células em Paragraph para QUEBRAR o texto (nome longo) e não sobrepor o CPF.
        _pcell = ParagraphStyle('propcell', fontName='Helvetica', fontSize=8.5,
                                leading=10.5, textColor=PRETO)

        def _pp(v):
            return Paragraph(
                _txt(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
                _pcell,
            )

        linhas = [[_pp(p.get('nome', '')), _pp(formata_doc(p.get('cpf_cnpj', ''))),
                   _pp(p.get('percentual', ''))] for p in props]
        st.append(tbl_header(['Nome / Razão Social', 'CPF / CNPJ', 'Fração'], linhas,
                             [7.0 * cm, 4.0 * cm, UTIL_W - 11.0 * cm]))
    st.append(Spacer(1, 8))
    st += subsec('Caracterização do Imóvel', 'sec3carac')
    _rural3 = _is_rural(ptam)
    _carac_rows = [
        ('Área do Terreno', fmt_area_rural(ptam.get('imovel_area_terreno'), _rural3)),
        ('Área Construída', fmt_area(ptam.get('imovel_area_construida'))),
        ('Área Considerada', fmt_area_rural(ptam.get('imovel_area_a_considerar'), _rural3)),
        ('Idade Aproximada', f"{ptam.get('imovel_idade')} anos" if ptam.get('imovel_idade') else ''),
        ('Estado de Conservação', ptam.get('imovel_estado_conservacao')),
        ('Padrão de Acabamento', ptam.get('imovel_padrao_acabamento')),
        # Ambientes (quantidade) — mesmos campos das amostras; regra: só > 0 vai ao laudo.
        ('Sala de Estar', ptam.get('imovel_sala_estar')),
        ('Sala de Jantar/Copa', ptam.get('imovel_sala_jantar')),
        ('Cozinha', ptam.get('imovel_cozinha')),
        ('Quarto Social', ptam.get('imovel_quarto_social')),
        ('Suíte Simples', ptam.get('imovel_suite_simples')),
        ('Suíte Master', ptam.get('imovel_suite_master')),
        ('Banheiro Social', ptam.get('imovel_banheiro_social')),
        ('Lavabo', ptam.get('imovel_lavabo')),
        ('Área de Serviço', ptam.get('imovel_area_servico')),
        ('Varanda/Sacada', ptam.get('imovel_varanda')),
        ('Varanda Gourmet', ptam.get('imovel_varanda_gourmet')),
        ('Escritório', ptam.get('imovel_escritorio')),
        ('Despensa', ptam.get('imovel_despensa')),
        ('Piscina', ptam.get('imovel_num_piscinas')),
        ('Garagem', ptam.get('imovel_num_vagas')),
        ('Características Adicionais / Benfeitorias',
         html_to_inline(limpar_texto_ia(ptam.get('imovel_caracteristicas_adicionais')))),
    ]
    # Regra: valor 0 / vazio / "Não" NÃO vai para o laudo.
    _carac_rows = [(lb, _txt(vl)) for lb, vl in _carac_rows if _preenchido(vl)]
    st.append(tbl(_carac_rows or [('Caracterização', 'Não informada')]))

    # ── 4. Contexto Urbano ──
    st.append(PageBreak())
    st += sec('4. CONTEXTO URBANO / ANÁLISE DA REGIÃO', 'sec4')
    dados4 = [
        ('Zoneamento', html_to_inline(limpar_texto_ia(ptam.get('zoneamento')))),
        ('Padrão Construtivo', html_to_inline(limpar_texto_ia(ptam.get('regiao_padrao_construtivo')))),
        ('Tendência de Mercado', html_to_inline(limpar_texto_ia(ptam.get('regiao_tendencia_mercado')))),
        ('Uso Predominante', html_to_inline(limpar_texto_ia(ptam.get('regiao_uso_predominante')))),
        ('Infraestrutura', html_to_inline(limpar_texto_ia(ptam.get('regiao_infraestrutura')))),
        ('Serviços Públicos', html_to_inline(limpar_texto_ia(ptam.get('regiao_servicos_publicos')))),
        ('Observações Complementares', html_to_inline(limpar_texto_ia(ptam.get('regiao_observacoes')))),
    ]
    dados4 = [(lb, vl) for lb, vl in dados4 if vl not in (None, '')]
    st.append(tbl(dados4 or [('Observações', '—')]))

    # ── 5. Analise Mercadologica e Amostras ──
    st.append(PageBreak())
    st += sec('5. ANÁLISE MERCADOLÓGICA E AMOSTRAS', 'sec5')
    if ptam.get('market_analysis'):
        st.append(Paragraph(_txt(html_to_inline(limpar_texto_ia(ptam.get('market_analysis')))), sBody))
        st.append(Spacer(1, 6))
    if amostras:
        _rural5 = _is_rural(ptam)
        for i, a in enumerate(amostras, 1):
            _grupo = [AmostraCard(i, a, rural=_rural5)]
            _planta = a.get('_planta_baixa_bytes') or a.get('planta_baixa_url')
            if _planta:
                _grupo.append(Spacer(1, GAP))
                _grupo.append(PlantaBaixaCard(i, _planta))
            st.append(KeepTogether(_grupo))
            st.append(Spacer(1, GAP))
    else:
        st.append(Paragraph('Nenhuma amostra cadastrada.', sBody))

    # ── 6. Metodologia ──
    st.append(PageBreak())
    st += sec('6. METODOLOGIA', 'sec6')
    st.append(tbl([
        ('Método Utilizado', ptam.get('methodology') or 'Método Comparativo Direto de Dados de Mercado'),
        ('Norma', 'NBR 14653-1:2001 (item 8.2) e NBR 14653-2:2011 (item 8.2.1)'),
        ('Tratamento', html_to_inline(limpar_texto_ia(ptam.get('methodology_justification'))) or 'Média ponderada com peso igualitário (1/N)'),
        ('Grau de Fundamentação', ptam.get('calc_grau_fundamentacao') or ptam.get('fundamentacao_grau')),
        ('Saneamento', 'Eliminação de outliers ±10% da média'),
    ]))

    # ── 7. Calculos ──
    st.append(PageBreak())
    st += sec('7. CÁLCULOS E TRATAMENTO ESTATÍSTICO', 'sec7')
    st += subsec('Quadro de Amostras com Classificação', 'sec7quadro')
    _rural = _is_rural(ptam)
    _uv = 'R$/ha' if _rural else 'R$/m²'   # rótulo da unidade de valor
    _fa = 1.0  # fator de área para exibição: m² → (m² ou ha)
    _vfac = 10000 if _rural else 1         # R$/m² → R$/ha
    # Estatísticas descritivas das amostras (sempre calculadas em R$/m²) — NBR 14653-2
    _vals = [v for v in (float(a.get('value_per_sqm') or 0) for a in amostras) if v > 0]
    _n = len(_vals)
    if _n:
        _media = sum(_vals) / _n
        _minimo, _maximo = min(_vals), max(_vals)
        _desvio = (sum((x - _media) ** 2 for x in _vals) / _n) ** 0.5
        _cv = (_desvio / _media * 100) if _media else 0.0
        _li, _ls = _media * 0.9, _media * 1.1
        _dentro = [x for x in _vals if _li <= x <= _ls]
        _ponderada = (sum(_dentro) / len(_dentro)) if _dentro else _media
    else:
        _media = _minimo = _maximo = _desvio = _cv = _li = _ls = _ponderada = 0.0
        _dentro = []

    # Quadro de amostras (coluna "Local" com quebra de linha — evita sobreposição)
    _num_br = lambda x: f"{float(x):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    _num_ha = lambda x: f"{float(x):,.4f}".replace(',', 'X').replace('.', ',').replace('X', '.')  # área: 4 casas
    linhas7 = []
    for i, a in enumerate(amostras, 1):
        local = f"{a.get('address', '')} / {a.get('neighborhood', '')}".strip(' /')
        _vpm = float(a.get('value_per_sqm') or 0)
        _sit = ('Dentro' if _li <= _vpm <= _ls else 'Fora') if _n else '—'
        _area_cell = (_num_ha(float(a.get('area') or 0) / 10000) if _rural
                      else fmt_area(a.get('area')).replace(' m²', ''))
        linhas7.append([
            str(i), Paragraph(local[:90] or '—', sCell),
            _area_cell,
            fmt_moeda(a.get('value')).replace('R$ ', ''),
            _num_br(_vpm * _vfac),
            _sit,
        ])
    st.append(tbl_header(['Nº', 'Bairro / Local', f'Área ({"ha" if _rural else "m²"})',
                          'Valor (R$)', _uv, 'Situação'],
                         linhas7, [1.0 * cm, 6.5 * cm, 2.3 * cm, 3.0 * cm, 2.3 * cm, 1.7 * cm]))
    st.append(Spacer(1, 8))
    st += subsec('8B. Cálculo de Ponderância')
    st.append(Paragraph('Método comparativo com saneamento das amostras fora da faixa de ±10% '
                        'em torno da média simples dos valores unitários (ABNT NBR 14653-2). '
                        'As amostras dentro da faixa compõem a média ponderada final.', sBody))
    st.append(Spacer(1, 6))
    _num = lambda x: f"{float(x):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    _nv = lambda x: _num(float(x) * _vfac)  # valor unitário na unidade de exibição (R$/ha ou R$/m²)
    _stats_rows = [
        ['Nº de Amostras', str(_n)],
        [f'Valor Mínimo ({_uv})', _nv(_minimo)],
        [f'Valor Máximo ({_uv})', _nv(_maximo)],
        [f'Média Simples ({_uv})', _nv(_media)],
        [f'Desvio Padrão ({_uv})', _nv(_desvio)],
        ['Coeficiente de Variação (%)', _num(_cv) + '%'],
        [f'Limite Inferior (–10%) ({_uv})', _nv(_li)],
        [f'Limite Superior (+10%) ({_uv})', _nv(_ls)],
        ['Amostras dentro da faixa', str(len(_dentro))],
        [f'Média Ponderada Final ({_uv})', _nv(_ponderada)],
    ]
    if _rural:
        _stats_rows.append(['Média Ponderada Final (R$/m²) — referência', _num(_ponderada)])
    st.append(tbl_header(['Estatística', 'Valor'], _stats_rows,
                         [9.0 * cm, UTIL_W - 9.0 * cm], bold_last=True))
    # Referência INCRA (Valores de Terra Nua) — só rural e se marcado para o laudo.
    if _rural and ptam.get('incra_incluir_laudo', True):
        try:
            _vu_inc = float(ptam.get('resultado_valor_unitario') or ptam.get('ponderancia_media') or _ponderada or 0)
        except (TypeError, ValueError):
            _vu_inc = float(_ponderada or 0)
        st.append(Spacer(1, 8))
        st += incra_section(ptam, _vu_inc * 10000)
    # Fatores de homogeneização + observações dos cálculos (texto do avaliador).
    _fat = html_to_inline(limpar_texto_ia(ptam.get('calc_fatores_homogeneizacao')))
    if _fat:
        st.append(Spacer(1, 6))
        st += subsec('Fatores de Homogeneização Aplicados')
        st.append(Paragraph(_fat, sBody))
    _obs_calc = html_to_inline(limpar_texto_ia(ptam.get('calc_observacoes')))
    if _obs_calc:
        st.append(Spacer(1, 6))
        st += subsec('Observações sobre os Cálculos')
        st.append(Paragraph(_obs_calc, sBody))

    # ── 8. Resultado ──
    st.append(PageBreak())
    st += sec('8. RESULTADO DA AVALIAÇÃO', 'sec8')
    vu = ptam.get('resultado_valor_unitario')
    area_av = ptam.get('imovel_area_a_considerar') or ptam.get('imovel_area_construida')
    vtotal = ptam.get('resultado_valor_total') or ptam.get('total_indemnity')
    st.append(Paragraph(
        f"Com fundamento na vistoria realizada, na documentação fundiária analisada (Matrícula nº "
        f"{_txt(ptam.get('property_matricula'), '—')}) e no tratamento estatístico das amostras de "
        f"mercado coletadas, conclui-se que o valor de mercado do imóvel é:", sBody))
    _rural8 = _is_rural(ptam)
    st += subsec('Cálculo do Valor Final', 'sec8calc')
    _calc_rows = [
        ['Média Ponderada Final', fmt_rs_unit(vu, _rural8)],
        ['Área do Imóvel Avaliando', fmt_area_rural(area_av, _rural8)],
        [f"Valor Final = {fmt_rs_unit(vu, _rural8)} × {fmt_area_rural(area_av, _rural8)}", fmt_moeda(vtotal)],
    ]
    if _rural8:
        _calc_rows.insert(1, ['Valor unitário de referência', f"{fmt_moeda(vu)}/m²"])
    st.append(tbl_header(['Componente', 'Valor'], _calc_rows,
                         [UTIL_W - 4.5 * cm, 4.5 * cm], bold_last=True))
    st.append(Spacer(1, 10))
    st.append(caixa_valor(vtotal, ptam.get('total_indemnity_words') or valor_por_extenso(vtotal)))
    st.append(Spacer(1, 10))
    _res_rows = []
    if _rural8:
        try:
            _vu_f = float(vu)
        except (TypeError, ValueError):
            _vu_f = 0.0
        _res_rows.append(('Valor Unitário R$/ha', fmt_moeda(_vu_f * 10000)))
        _res_rows.append(('Valor Unitário R$/m² (referência)', fmt_moeda(_vu_f)))
    else:
        _res_rows.append(('Valor Unitário R$/m²', fmt_moeda(vu)))
    _res_rows += [
        ('Intervalo de Confiança',
         f"{fmt_moeda(ptam.get('resultado_intervalo_inf'))} a {fmt_moeda(ptam.get('resultado_intervalo_sup'))}"),
        ('Grau de Precisão', ptam.get('grau_precisao') or ptam.get('precisao_grau')),
        ('Data de Referência', ptam.get('resultado_data_referencia')),
        ('Prazo de Validade', ptam.get('resultado_prazo_validade') or '180 dias'),
    ]
    st.append(tbl(_res_rows))

    # ── 9. Conclusao ──
    st.append(PageBreak())
    st += sec('9. CONCLUSÃO E RESPONSABILIDADE TÉCNICA', 'sec9')
    st.append(Paragraph(
        'O(A) profissional signatário(a) deste Parecer Técnico de Avaliação Mercadológica é '
        '<b>Corretor de Imóveis habilitado nos termos da Resolução COFECI 957/2006</b>, '
        'responsabilizando-se técnica e legalmente pelo conteúdo e pelos valores aqui expressos, '
        'conforme as normas regulamentadoras vigentes.', sBody))
    # Conteúdo técnico-jurídico preenchido pelo avaliador — íntegra, justificado.
    _bloco_conclusao(st, 'CONSIDERAÇÕES E PRESSUPOSTOS ADOTADOS', ptam.get('consideracoes_pressupostos'))
    _bloco_conclusao(st, 'RESSALVAS E LIMITAÇÕES', ptam.get('consideracoes_ressalvas'))
    _bloco_conclusao(st, 'CONSIDERAÇÕES E LIMITAÇÕES', ptam.get('consideracoes_limitacoes'))
    _bloco_conclusao(st, None, ptam.get('conclusion_text'))
    st.append(Spacer(1, 8))
    st.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_BRD, spaceAfter=6))
    # TRT — sem prefixo duplicado; omitido se vazio ou só zeros (Fix C).
    _art = (ptam.get('art_rrt_numero') or ptam.get('art_trt_numero') or '').strip()
    if _art and not re.match(r'^0+$', _art):
        _trt = _art if _art.upper().startswith('CFT') else f'CFT Nº {_art}'
        st.append(Paragraph(f'<b>Nº TRT (Res. CONFEA 345/90):</b> {_esc_xml(_trt)}', sBody))
    # Data por extenso, sem espaço antes da vírgula e sem ISO (Fix A).
    _cid = re.sub(r'\s+', ' ', (ptam.get('conclusion_city') or ptam.get('property_city') or 'Açailândia')).strip()
    _cid = (re.split(r'[/,]', _cid)[0].strip() or 'Açailândia')
    st.append(Spacer(1, 6))
    st.append(Paragraph(f'{_cid}-MA, {_data_extenso(ptam.get("conclusion_date"))}',
                        ParagraphStyle('dt', parent=sBody, alignment=2)))
    st.append(Spacer(1, 1.4 * cm))
    nome = perfil.get('nome') or ptam.get('responsavel_nome') or ''
    creci = perfil.get('creci') or ptam.get('responsavel_creci') or ''
    cnai = perfil.get('cnai') or ptam.get('responsavel_cnai') or ''
    end = perfil.get('endereco') or ''
    tel = perfil.get('telefone') or ''
    st.append(Paragraph('_____________________________________________', sCenter))
    st.append(Paragraph(_txt(nome, '').upper(),
              ParagraphStyle('sg', fontName='Helvetica-BoldOblique', fontSize=11,
                             textColor=PRETO, alignment=TA_CENTER)))
    _regs = ' · '.join(perfil.get('registros_linhas') or [r for r in [creci, cnai] if r])
    st.append(Paragraph(f'Avaliador — {_txt(_regs, "")}' if _regs else 'Avaliador',
              ParagraphStyle('sg2', fontName='Helvetica', fontSize=9, textColor=CINZA, alignment=TA_CENTER)))
    st.append(Paragraph(f'{_txt(end, "")} | {_txt(tel, "")}',
              ParagraphStyle('sg3', fontName='Helvetica', fontSize=9, textColor=CINZA, alignment=TA_CENTER)))

    # ── ANEXO I — Relatorio Fotografico ──
    st.append(PageBreak())
    st += sec('ANEXO I — RELATÓRIO FOTOGRÁFICO DO IMÓVEL AVALIANDO', 'anexo1')
    total = len(fotos)
    st.append(Paragraph(f'Imagens obtidas na data da vistoria — {total} fotografias — 2 por página.', sPag))
    if total == 0:
        st.append(Paragraph('Nenhuma foto do imóvel cadastrada.', sBody))
    else:
        for i in range(0, total, 2):
            n2 = min(i + 2, total)
            st.append(Paragraph(f'Fotografias {i + 1} e {n2} de {total}'
                                if n2 > i + 1 else f'Fotografia {i + 1} de {total}', sPag))
            st.append(_fotocard(fotos[i], i + 1, total))
            if i + 1 < total:
                st.append(Spacer(1, GAP))
                st.append(_fotocard(fotos[i + 1], i + 2, total))
            if n2 < total:
                st.append(PageBreak())

    # ── Documentos digitalizados do imovel (Certidoes, IPTU, BCI...) ──
    documentos = ptam.get('documentos_resolvidos') or []
    if documentos:
        st.append(PageBreak())
        st += sec('ANEXO I.B — DOCUMENTOS DO IMÓVEL', 'anexo1b')
        st.append(Paragraph('Certidões, IPTU, BCI e demais documentos analisados, anexados ao parecer.', sPag))
        for k, d in enumerate(documentos, 1):
            if not isinstance(d, dict):
                continue
            st.append(DocCard(k, d.get('name') or f'Documento {k}',
                              d.get('_doc_bytes'), d.get('content_type', 'image/jpeg')))
            st.append(Spacer(1, GAP))

    # ── ANEXO II — Amostras Comparativas (galeria 2×2, 4 por página) ──
    st.append(PageBreak())
    st += sec('ANEXO II — AMOSTRAS COMPARATIVAS', 'anexo2')
    if amostras:
        st.append(Paragraph(
            f'Galeria comparativa das amostras de mercado — {len(amostras)} amostra(s). '
            'Foto e planta baixa lado a lado.', sPag))
        st.append(Spacer(1, 6))
        _col_w = UTIL_W / 2
        _img_w = _col_w - 0.4 * cm
        _foto_h = 6.0 * cm
        _sTitAm = ParagraphStyle('galtit', fontName='Helvetica-Bold', fontSize=9,
                                 textColor=DOURADO, spaceAfter=3, alignment=TA_CENTER)

        def _cel_imagem(titulo, raw, placeholder='Sem imagem'):
            """Célula da galeria: título + imagem em miniatura (ou placeholder)."""
            elems = [Paragraph(titulo, _sTitAm)]
            try:
                if raw:
                    elems.append(RLImage(BytesIO(bytes(raw)), width=_img_w,
                                         height=_foto_h, kind='proportional'))
                else:
                    raise ValueError('sem imagem')
            except Exception:
                ph = Table([[placeholder]], colWidths=[_img_w], rowHeights=[_foto_h])
                ph.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), VERDE_CLR),
                    ('TEXTCOLOR', (0, 0), (-1, -1), CINZA),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOX', (0, 0), (-1, -1), 0.4, CINZA_BRD),
                ]))
                elems.append(ph)
            return elems

        # Uma amostra por linha: foto (esq.) + planta baixa em miniatura (dir.).
        for idx, a in enumerate(amostras, 1):
            local = (f"{a.get('address', '')} / {a.get('neighborhood', '')}".strip(' /')
                     or a.get('nome_local') or '—')
            foto_cell = _cel_imagem(f'Amostra {idx} — {local[:55]}', a.get('_image_bytes'))
            planta_raw = a.get('_planta_baixa_bytes')
            planta_cell = (_cel_imagem(f'Planta Baixa — Amostra {idx}', planta_raw,
                                       placeholder='Sem planta')
                           if planta_raw else '')
            gal = Table([[foto_cell, planta_cell]], colWidths=[_col_w, _col_w])
            gal.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            st.append(KeepTogether([gal]))
    else:
        st.append(Paragraph('Nenhuma amostra cadastrada.', sBody))

    # ── ANEXO III — Base Legal ──
    st.append(PageBreak())
    st += sec('ANEXO III — BASE LEGAL E NORMATIVA', 'anexo3')
    st.append(tbl([
        ('NBR 14653-1:2019', 'Procedimentos Gerais de Avaliação de Bens'),
        ('NBR 14653-2:2011', 'Imóveis Urbanos'),
        ('NBR 14653-3:2004', 'Imóveis Rurais'),
        ('Res. COFECI 957/2006', 'Regulamenta o PTAM'),
        ('Lei 5.194/1966', 'Engenharia, Arquitetura e Agronomia'),
        ('Lei 6.530/1978', 'Profissão de Corretor de Imóveis'),
        ('Res. CONFEA 345/90', 'Responsabilidade Técnica — ART/TRT'),
        ('Lei 13.786/2018', 'Alienação de unidades imobiliárias'),
        ('CPC art. 156', 'Perito judicial — nomeação e deveres'),
    ], cw=[5.0 * cm, UTIL_W - 5.0 * cm]))

    # ── ANEXO IV — Curriculo ──
    st.append(PageBreak())
    st += sec('ANEXO IV — CURRÍCULO DO AVALIADOR', 'anexo4')
    _sCurH = ParagraphStyle('curH', fontName='Helvetica-Bold', fontSize=16,
                            textColor=VERDE, alignment=TA_CENTER, spaceAfter=10)
    _sCurSec = ParagraphStyle('curSec', fontName='Helvetica-Bold', fontSize=10,
                              textColor=VERDE, spaceBefore=8, spaceAfter=4)
    _sCurBody = ParagraphStyle('curB', fontName='Helvetica', fontSize=10, textColor=PRETO,
                               alignment=TA_JUSTIFY, leading=14, spaceAfter=3)
    _sCurInd = ParagraphStyle('curInd', parent=_sCurBody, leftIndent=0.8 * cm)

    def _cur_sep():
        st.append(Spacer(1, 4))
        st.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_BRD))
        st.append(Spacer(1, 4))

    st.append(Paragraph('CURRICULUM DO AVALIADOR', _sCurH))

    # DADOS PROFISSIONAIS
    st.append(Paragraph('DADOS PROFISSIONAIS', _sCurSec))
    if perfil.get('nome'):
        st.append(Paragraph(f"Nome: {perfil['nome']}", _sCurBody))
    if perfil.get('bio_resumo') or perfil.get('cargo'):
        st.append(Paragraph(f"<b>{_txt(perfil.get('bio_resumo') or perfil.get('cargo'), '')}</b>", _sCurBody))
    _cur_sep()

    # QUALIFICAÇÕES E FORMAÇÃO PROFISSIONAL
    st.append(Paragraph('<u>QUALIFICAÇÕES E FORMAÇÃO PROFISSIONAL</u>', _sCurSec))
    for reg in (perfil.get('registros_linhas') or []):
        st.append(Paragraph(f'• {reg}', _sCurBody))
    for f in (perfil.get('formacoes') or []):
        if not isinstance(f, dict):
            continue
        linha = ' '.join(x for x in [
            f.get('tipo'), ('em' if f.get('curso') else ''), f.get('curso'),
            (f"— {f.get('instituicao')}" if f.get('instituicao') else ''),
            (f"({f.get('ano_conclusao')})" if f.get('ano_conclusao') else ''),
        ] if x)
        if linha:
            st.append(Paragraph(f'• {linha}', _sCurBody))
    _cur_sep()

    # EXPERIÊNCIA PROFISSIONAL
    _exps = [e for e in (perfil.get('experiencias') or []) if isinstance(e, dict)]
    if _exps:
        st.append(Paragraph('<u>EXPERIÊNCIA PROFISSIONAL</u>', _sCurSec))
        for e in _exps:
            periodo = ' – '.join(x for x in [e.get('periodo_inicio'), e.get('periodo_fim') or 'Atual'] if x)
            cab = ' – '.join(x for x in [e.get('cargo'), e.get('empresa')] if x)
            if periodo:
                cab = f"{cab} ({periodo})"
            if cab:
                st.append(Paragraph(f'▪ <b>{cab}</b>', _sCurBody))
            if e.get('descricao'):
                st.append(Paragraph(limpar_texto_ia(e['descricao']), _sCurInd))
        _cur_sep()

    # COMPETÊNCIAS E ESPECIALIDADES
    _comp = (list(perfil.get('especializacoes') or [])
             + list(perfil.get('areas_atuacao') or [])
             + list(perfil.get('habilitacoes') or []))
    if _comp:
        st.append(Paragraph('<u>COMPETÊNCIAS E ESPECIALIDADES</u>', _sCurSec))
        for c in _comp:
            st.append(Paragraph(f'• {_txt(c, "")}', _sCurBody))
        _cur_sep()

    # DADOS DE CONTATO
    st.append(Paragraph('<u>DADOS DE CONTATO</u>', _sCurSec))
    if perfil.get('endereco'):
        st.append(Paragraph(f"Endereço: {perfil['endereco']}", _sCurBody))
    _contato = ' // '.join(x for x in [
        (f"Telefone: {perfil['telefone']}" if perfil.get('telefone') else ''),
        (f"E-mail: {perfil['email']}" if perfil.get('email') else ''),
    ] if x)
    if _contato:
        st.append(Paragraph(_contato, _sCurBody))
    if perfil.get('site'):
        st.append(Paragraph(f"Site: {perfil['site']}", _sCurBody))

    # Fallback: perfil não cadastrado → orienta o avaliador
    if not perfil.get('perfil_completo'):
        st.append(Spacer(1, 6))
        st.append(Paragraph('Complete seu perfil de avaliador no sistema para que o currículo '
                            'seja preenchido automaticamente nos laudos.', sPag))
    return st


def _story_completo(ptam, page_map):
    # PageBreak inicial reserva a pagina 1 para a capa (onFirstPage).
    # Sumario na pagina 2, secoes a partir da pagina 3.
    return [PageBreak(), Sumario(page_map), PageBreak()] + build_story(ptam, page_map)


def build_ptam_pdf(ptam: dict) -> bytes:
    capa = make_capa(ptam)
    hf = make_hf(ptam)
    # Passagem 1 — detectar paginas reais das ancoras (mesmo layout da passagem 2)
    buf1 = BytesIO()
    doc1 = TrackingDoc(buf1, pagesize=A4, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB)
    try:
        doc1.build(_story_completo(ptam, {}), onFirstPage=capa, onLaterPages=hf)
        page_map = doc1.anchor_pages
    except Exception:
        logger.exception('ptam_pdf_v2: passagem 1 falhou')
        page_map = {}
    # Passagem 2 — PDF final com numeracao real no sumario
    buf2 = BytesIO()
    doc2 = TrackingDoc(buf2, pagesize=A4, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB)
    doc2.build(_story_completo(ptam, page_map), onFirstPage=capa, onLaterPages=hf)
    buf2.seek(0)
    return buf2.getvalue()


def generate_ptam_pdf_v2(ptam: dict, perfil: dict = None) -> bytes:
    """Ponto de entrada: gera o PDF do PTAM (layout aprovado) e retorna bytes."""
    ptam = dict(ptam or {})
    if perfil is not None:
        ptam['_perfil'] = perfil
    return build_ptam_pdf(ptam)
