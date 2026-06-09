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
from finalidades import _FINALIDADE_MAP  # fonte única do mapa finalidade-chave → rótulo

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


# ── White-label: tema de cores por cliente (override temporário) ───────────────
# As constantes VERDE/DOURADO são usadas em ~100 pontos. Em vez de reescrever cada
# um, aplicamos um override pontual no início da geração e restauramos no fim.
# Seguro aqui porque generate_ptam_pdf_v2 roda como chamada SÍNCRONA bloqueante
# dentro da rota async (uma geração por vez por worker). Multi-worker = globals
# independentes por processo.
_THEME_COLOR_KEYS = ('VERDE', 'VERDE_MED', 'VERDE_CLR', 'DOURADO', 'DOURADO_CLR')
# Estilos de módulo cujo textColor foi fixado a uma cor de tema no import:
_THEME_STYLE_BINDINGS = (('sSec', 'VERDE'), ('sSub', 'VERDE_MED'), ('sTitulo', 'VERDE'))


def _shade(hex_str, toward, amount):
    """Clareia ('white') ou escurece ('black') uma cor hex por `amount` (0..1)."""
    from reportlab.lib.colors import Color
    c = HexColor(hex_str)
    r, g, b = c.red, c.green, c.blue
    if toward == 'white':
        r, g, b = r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount
    else:
        r, g, b = r * (1 - amount), g * (1 - amount), b * (1 - amount)
    return Color(r, g, b)


def _apply_brand_theme(primary_hex, secondary_hex):
    """Aplica as cores do cliente às constantes + estilos de módulo. Devolve o
    estado salvo para restaurar no finally. Retorna None se a cor for inválida."""
    g = globals()
    saved_colors = {k: g[k] for k in _THEME_COLOR_KEYS}
    saved_styles = {}
    try:
        g['VERDE'] = HexColor(primary_hex)
        g['VERDE_MED'] = _shade(primary_hex, 'black', 0.12)
        g['VERDE_CLR'] = _shade(primary_hex, 'white', 0.90)
        if secondary_hex:
            g['DOURADO'] = HexColor(secondary_hex)
            g['DOURADO_CLR'] = _shade(secondary_hex, 'white', 0.25)
        for style_name, color_name in _THEME_STYLE_BINDINGS:
            st = g.get(style_name)
            if st is not None:
                saved_styles[style_name] = st.textColor
                st.textColor = g[color_name]
    except Exception:
        for k, v in saved_colors.items():
            g[k] = v
        for sname, col in saved_styles.items():
            g[sname].textColor = col
        return None
    return (saved_colors, saved_styles)


def _restore_theme(saved):
    if not saved:
        return
    saved_colors, saved_styles = saved
    g = globals()
    for k, v in saved_colors.items():
        g[k] = v
    for sname, col in saved_styles.items():
        if g.get(sname) is not None:
            g[sname].textColor = col

# ── Cards estilo "dashboard" para o tratamento estatístico no PDF ──────────────
_sCardP = ParagraphStyle('cardP', fontName='Helvetica', fontSize=9, leading=12, alignment=TA_CENTER)


def _pdf_card(label, valor, sub='', cor='#0B6E4F', size_val=13, label_cor='#8A8A8A'):
    """Card: rótulo pequeno em cima, valor grande/colorido no meio, sub embaixo."""
    _l = [
        f'<font size=7 color="{label_cor}">{_esc_xml((label or "").upper())}</font>',
        f'<font size={size_val} color="{cor}"><b>{_esc_xml(str(valor))}</b></font>',
    ]
    if sub:
        _l.append(f'<font size=7 color="{label_cor}">{_esc_xml(str(sub))}</font>')
    return Paragraph('<br/>'.join(_l), _sCardP)


def _pdf_cards_row(cells, bgs, cw=None):
    """Linha de cards (Table). 'bgs' = lista de cores de fundo (HexColor) por card."""
    n = len(cells)
    if cw is None:
        cw = [UTIL_W / n] * n
    t = Table([cells], colWidths=cw)
    sty = [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 2.5, BRANCO),  # respiro branco entre os cards
    ]
    for _i, _bg in enumerate(bgs):
        if _bg is not None:
            sty.append(('BACKGROUND', (_i, 0), (_i, 0), _bg))
    t.setStyle(TableStyle(sty))
    return t

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


def _area_avaliando_str(ptam, area_av, rural) -> str:
    """String da 'Área do Imóvel Avaliando'. No urbano, mostra a composição
    AE (área edificada) + AT (área do terreno) quando a área considerada é a soma,
    ou rotula qual área foi considerada — para o leitor ver o valor exato."""
    if rural:
        return fmt_area_rural(area_av, True)

    def _f(v):
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    av = _f(area_av)
    ae = _f((ptam or {}).get('imovel_area_construida'))   # área edificada/construída
    at = _f((ptam or {}).get('imovel_area_terreno'))      # área do terreno
    base = fmt_area(av)
    if ae > 0 and at > 0 and abs(av - (ae + at)) < 0.01:
        return f"{base} (AE {fmt_area(ae)} + AT {fmt_area(at)})"
    if ae > 0 and at > 0 and abs(av - at) < 0.01:
        return f"{base} (AT — área do terreno)"
    if ae > 0 and at > 0 and abs(av - ae) < 0.01:
        return f"{base} (AE — área edificada)"
    return base


_CUF_CLASSES = {
    '1.00': ('Classe I', 'aptidão boa'),
    '0.90': ('Classe II', 'aptidão regular'),
    '0.75': ('Classe III', 'aptidão restrita'),
    '0.60': ('Classe IV', 'aptidão marginal'),
    '0.40': ('Classes V a VII', 'sem aptidão agrícola relevante'),
}


def _justificativa_metodo(ptam) -> str:
    """Texto técnico-jurídico AUTOMÁTICO que justifica o método de depreciação/valorização
    aplicado (ou a ausência dele). Cobre todos os tipos. Retorna string (com tags <b>) ou ''."""
    p = (ptam or {})
    # Override manual do avaliador, se houver.
    manual = str(p.get('justificativa_metodo') or '').strip()
    if manual:
        return manual

    metodo = str(p.get('metodo_avaliacao') or '').strip().lower()
    par = p.get('metodo_params') or {}

    def _n(v, casas=2):
        try:
            x = float(v)
        except (TypeError, ValueError):
            return ''
        s = f"{x:,.{casas}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return s

    if metodo == 'nbr_rural':
        cuf = par.get('classe_uso') or '1.00'
        try:
            cuf_f = float(cuf)
        except (TypeError, ValueError):
            cuf_f = 1.0
        classe, aptidao = _CUF_CLASSES.get(str(cuf), (f'CUF {_n(cuf_f)}', 'aptidão conforme classificação'))
        ajuste_pct = abs(round((1 - cuf_f) * 100, 2))
        vtn = fmt_moeda(par.get('vtn_hectare'))
        area = _n(par.get('area_ha'), 4)
        benf = par.get('benfeitorias_rurais')
        cperm = par.get('cultura_permanente')
        ctemp = par.get('cultura_temporaria')
        t = (
            "A avaliação do imóvel rural observou a metodologia da <b>ABNT NBR 14653-3:2019</b> "
            "(avaliação de imóveis rurais) e as diretrizes da Instrução Normativa do <b>INCRA</b>. "
            f"O Valor da Terra Nua (VTN) foi apurado a partir do valor de mercado do hectare "
            f"(<b>{vtn}/ha</b>) aplicado à área total de <b>{area} ha</b>, ajustado pelo Coeficiente "
            f"de Uso/Aptidão (CUF) correspondente à <b>{classe} — {aptidao}</b> (CUF = <b>{_n(cuf_f)}</b>). "
        )
        if cuf_f < 1.0:
            t += (
                f"A aplicação do referido coeficiente importa <b>depreciação de {_n(ajuste_pct)}%</b> "
                "sobre o valor pleno do hectare, justificada pelas características de relevo, drenagem, "
                "fertilidade e capacidade de uso do solo apuradas em vistoria, que restringem a aptidão "
                "agrícola da gleba. "
            )
        elif cuf_f > 1.0:
            t += (
                f"A aplicação do referido coeficiente importa <b>valorização de {_n(ajuste_pct)}%</b> "
                "sobre o valor de referência do hectare, justificada pela elevada aptidão agrícola "
                "verificada em vistoria. "
            )
        else:
            t += "Não houve ajuste de aptidão, mantido o valor pleno do hectare (CUF = 1,00). "
        t += (
            "O ajuste decorre de critério técnico-normativo objetivo, em estrita observância à NBR 14653-3 "
            "e à metodologia oficial do INCRA, não configurando depreciação arbitrária, mas a expressão "
            "fidedigna do valor de mercado da terra nua segundo sua real capacidade produtiva. "
        )
        extras = []
        if _preenchido(benf):
            extras.append(f"benfeitorias ({fmt_moeda(benf)})")
        if _preenchido(cperm):
            extras.append(f"cultura permanente ({fmt_moeda(cperm)})")
        if _preenchido(ctemp):
            extras.append(f"cultura temporária ({fmt_moeda(ctemp)})")
        if extras:
            t += ("Ao Valor da Terra Nua foram acrescidos os valores de " + ", ".join(extras)
                  + ", compondo o valor total do imóvel, em conformidade com o princípio da composição de valores.")
        return t

    if metodo == 'ross_heidecke':
        idade = _n(par.get('idade_atual'), 0)
        vida = _n(par.get('vida_util') or 60, 0)
        estado = str(par.get('estado') or 'C')
        dep = _n(p.get('depreciacao_percentual'))
        return (
            "A depreciação da edificação foi apurada pelo critério de <b>Ross-Heidecke</b>, consagrado na "
            "engenharia de avaliações e referendado pela <b>ABNT NBR 14653-2</b>, o qual conjuga a "
            f"depreciação física pela idade (<b>{idade} anos</b> sobre vida útil de <b>{vida} anos</b>) "
            f"com o estado de conservação verificado em vistoria (classe <b>{estado}</b>), resultando em "
            f"depreciação de <b>{dep}%</b> sobre o valor de reedição. O método é objetivo e amplamente "
            "aceito, refletindo a perda de valor da benfeitoria por uso e idade, sem caráter arbitrário."
        )

    if metodo == 'linha_reta':
        idade = _n(par.get('idade_atual'), 0)
        vida = _n(par.get('vida_util') or 40, 0)
        resid = _n(par.get('residual_pct') or 20, 0)
        dep = _n(p.get('depreciacao_percentual'))
        return (
            "A depreciação foi apurada pelo método da <b>Linha Reta</b> (depreciação linear), em conformidade "
            "com a <b>ABNT NBR 14653-2</b>, no qual a perda de valor é proporcional à idade da construção "
            f"(<b>{idade} anos</b>) sobre a vida útil de referência (<b>{vida} anos</b>), respeitado o valor "
            f"residual de <b>{resid}%</b>. Apurou-se depreciação de <b>{dep}%</b> sobre o valor de novo, "
            "critério adequado a galpões e construções de perda de valor uniforme no tempo."
        )

    if metodo == 'fatores_terreno':
        return (
            "O valor do terreno foi apurado por <b>homogeneização por fatores</b>, em conformidade com a "
            "<b>ABNT NBR 14653-2</b>, aplicando-se ao valor unitário de referência os fatores de localização, "
            "topografia, testada/frente e infraestrutura, conforme as características do lote verificadas em "
            "vistoria. Os ajustes têm fundamento técnico e objetivo, refletindo a influência de cada atributo "
            "sobre o valor de mercado, sem caráter arbitrário."
        )

    if metodo == 'renda':
        taxa = _n(par.get('taxa_cap') or 8)
        return (
            "A avaliação adotou o <b>Método da Renda</b> (capitalização da renda líquida), em conformidade com a "
            "<b>ABNT NBR 14653-2</b>, segundo o qual o valor do imóvel corresponde ao valor presente da renda "
            f"por ele produzida, à taxa de capitalização de mercado de <b>{taxa}% a.a.</b>. O critério é pertinente "
            "a imóveis geradores de renda e reflete sua capacidade econômica de produção."
        )

    # Nenhum método específico (ou 'não aplicado'): justifica o Comparativo Direto.
    return (
        "Não foi aplicado método específico de depreciação ou valorização, decorrendo o valor de mercado "
        "diretamente do <b>Método Comparativo Direto de Dados de Mercado</b> (<b>ABNT NBR 14653-2</b>), mediante "
        "pesquisa e tratamento estatístico de elementos amostrais efetivamente comercializados ou ofertados, "
        "homogeneizados às características do imóvel avaliando. O resultado expressa o valor de mercado conforme "
        "o comportamento real do mercado imobiliário na data de referência."
    )


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


def _draw_logo(canvas, x, y, w, h, logo_bytes=None):
    # White-label: se o usuário enviou logo próprio (BrandingWizard → R2), usa-o;
    # senão cai no logo padrão AvalieImob (LOGO_PATH). Fallback nunca quebra o PDF.
    if logo_bytes:
        try:
            import io as _io
            from reportlab.lib.utils import ImageReader as _ImageReader
            canvas.drawImage(_ImageReader(_io.BytesIO(logo_bytes)), x, y, width=w, height=h,
                             preserveAspectRatio=True, mask='auto')
            return
        except Exception:
            pass
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
    _brand_logo = ptam.get('_brand_logo_bytes')
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
        _draw_logo(canvas, ML, ly, 3.2 * cm, lh, logo_bytes=_brand_logo)
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
    _brand_logo = ptam.get('_brand_logo_bytes')
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
        _draw_logo(canvas, W / 2 - 2.5 * cm, H - 9.0 * cm, 5.0 * cm, 5.0 * cm, logo_bytes=_brand_logo)
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
    ('7.2', 'Saneamento e Estatísticas Finais', 'sec7stats', 1),
    ('7.3', 'Cálculo de Ponderância', 'sec7pond', 1),
    ('7.4', 'Graus de Fundamentação e Precisão', 'sec7graus', 1),
    ('8', 'Resultado da Avaliação', 'sec8', 0),
    ('8.1', 'Método de Avaliação — Depreciação/Valorização', 'sec8metodo', 1),
    ('8.2', 'Cálculo do Valor Final', 'sec8calc', 1),
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
        self.title_h = 1.0 * cm
        self.height = self.title_h + self.hh + len(ITENS_SUM) * self.rh + 0.1 * cm

    def wrap(self, aw, ah):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        # Título "Sumário"
        c.setFillColor(VERDE)
        c.setFont('Helvetica-Bold', 17)
        c.drawString(0, h - 0.62 * cm, 'Sumário')
        c.setStrokeColor(DOURADO)
        c.setLineWidth(1.2)
        c.line(0, h - self.title_h + 0.20 * cm, w, h - self.title_h + 0.20 * cm)
        h = h - self.title_h
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


def tbl_header(header, linhas, cw, bold_last=False, fontsize=8.5):
    # Quebra automática de texto longo nas células do corpo (Paragraph), evitando
    # que o conteúdo "vaze" da célula. Cabeçalho segue como string (estilo da tabela).
    _lead = fontsize + 2
    _sCellN = ParagraphStyle('hcellN', fontName='Helvetica', fontSize=fontsize, leading=_lead)
    _sCellB = ParagraphStyle('hcellB', fontName='Helvetica-Bold', fontSize=fontsize, leading=_lead, textColor=VERDE)
    linhas = linhas or [["—"] * len(header)]
    _ult = len(linhas) - 1
    _body = []
    for _i, _row in enumerate(linhas):
        _stl = _sCellB if (bold_last and _i == _ult) else _sCellN
        _body.append([(Paragraph(_esc_xml(_c), _stl) if isinstance(_c, str) else _c) for _c in _row])
    data = [header] + _body
    t = Table(data, colWidths=cw, repeatRows=1)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), VERDE),
        ('TEXTCOLOR', (0, 0), (-1, 0), BRANCO),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), fontsize),
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


def _bloco_bci_iptu(ptam):
    """Seções 3.2 (Cadastro Imobiliário Municipal — BCI) e 3.3 (Situação do IPTU).
    Somente imóvel urbano. Retorna lista de flowables; omite linhas vazias e não
    renderiza nada (sem seção fantasma) se BCI e IPTU estiverem ambos vazios."""
    if _is_rural(ptam):
        return []
    bci = ptam.get('bci') or {}
    iptu = ptam.get('iptu') or {}
    if not isinstance(bci, dict):
        bci = {}
    if not isinstance(iptu, dict):
        iptu = {}

    def _fa(v):
        return fmt_area(v) if _preenchido(v) else None

    def _fm(v):
        return fmt_moeda(v) if _preenchido(v) else None

    # ── 3.2 — BCI ──
    _sql = ' / '.join(x for x in [
        _txt(bci.get('setor'), ''), _txt(bci.get('quadra'), ''),
        _txt(bci.get('lote'), ''), _txt(bci.get('unidade'), ''),
    ] if x)
    _bci_rows = [
        ('Inscrição Cadastral', bci.get('inscricao_cadastral')),
        ('Código do Imóvel (CTI)', bci.get('codigo_imovel')),
        ('Setor / Quadra / Lote / Unidade', _sql or None),
        ('Natureza', bci.get('natureza')),
        ('Situação Cadastral', bci.get('situacao')),
        ('Data de Cadastro', bci.get('data_cadastro')),
        ('Data de Construção', bci.get('data_construcao')),
        ('Proprietário / Detentor (BCI)', bci.get('proprietario_nome')),
        ('CPF / CNPJ', formata_doc(bci.get('proprietario_doc')) if bci.get('proprietario_doc') else None),
        ('Testada Principal', _fa(bci.get('testada_principal'))),
        ('Profundidade do Lote', _fa(bci.get('prof_lote'))),
        ('Área do Terreno', _fa(bci.get('area_terreno'))),
        ('Área da Edificação', _fa(bci.get('area_edificacao'))),
        ('Área Total da Edificação', _fa(bci.get('area_total_edificacao'))),
    ]
    _bci_rows = [(lb, _txt(vl)) for lb, vl in _bci_rows if _preenchido(vl)]

    # ── 3.3 — IPTU ──
    _sit = _txt(iptu.get('situacao'), '')
    _sit_low = _sit.strip().lower()
    _sit_fmt = _sit
    if _sit_low in ('em aberto', 'parcelado'):
        _sit_fmt = f'<b><font color="#C62828">{_esc_xml(_sit.upper())}</font></b>'
    _exerc = iptu.get('exercicio')
    _iptu_rows = [
        ('Inscrição do Contribuinte', iptu.get('inscricao_contribuinte')),
        ('Exercício de Referência', str(_exerc) if _exerc else None),
        ('Valor Anual do IPTU', _fm(iptu.get('valor_anual'))),
        ('Situação', _sit_fmt if _sit else None),
        ('Nº do Acordo de Parcelamento', iptu.get('acordo') if _sit_low == 'parcelado' else None),
        ('Vencimento', iptu.get('vencimento')),
        ('Débito Total', _fm(iptu.get('debito_total'))),
        ('Desconto Concedido', _fm(iptu.get('desconto'))),
        ('Valor Cobrado / a Pagar', _fm(iptu.get('valor_cobrado'))),
        ('Exercícios com Débito', iptu.get('exercicios_debito') if _sit_low in ('em aberto', 'parcelado') else None),
    ]
    # 'Situação' preserva o markup (negrito/vermelho); demais passam por _txt.
    _iptu_rows = [(lb, vl if lb == 'Situação' else _txt(vl))
                  for lb, vl in _iptu_rows if _preenchido(vl)]

    out = []
    if _bci_rows:
        out.append(Spacer(1, 8))
        out += subsec('3.2 Cadastro Imobiliário Municipal (BCI)')
        out.append(tbl(_bci_rows))
    if _iptu_rows:
        out.append(Spacer(1, 8))
        out += subsec('3.3 Situação do IPTU')
        out.append(tbl(_iptu_rows))
    return out


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
    # 3.2 Cadastro Imobiliário Municipal (BCI) + 3.3 IPTU — só urbano, logo após a identificação.
    st += _bloco_bci_iptu(ptam)
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

    # ── Benfeitorias estruturadas (somente imóvel rural) ──
    _benf = ptam.get('benfeitorias_rurais') or []
    if _rural3 and isinstance(_benf, list) and any(isinstance(b, dict) for b in _benf):
        _sBenf = ParagraphStyle('benfCell', fontName='Helvetica', fontSize=8, leading=10)

        def _fmt_medida_benf(med, uni):
            """Formata a medida conforme a unidade: 'un' (quantidade), 'm' (linear) ou 'm²' (área)."""
            try:
                n = float(str(med).replace(',', '.'))
            except (TypeError, ValueError):
                return ''
            u = uni or 'm²'
            if u == 'un':
                return f"{n:,.0f}".replace(',', '.') + ' un'
            s = f"{n:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"{s} {u}"

        _benf_rows = []
        for _b in _benf:
            if not isinstance(_b, dict):
                continue
            _tipo = _txt(_b.get('tipo'), '—')
            _desc = _txt(html_to_inline(limpar_texto_ia(_b.get('descricao'))), '')
            _med = _b.get('medida')
            if not _preenchido(_med):
                _med = _b.get('area_m2')  # compat com registros antigos
            _uni = _b.get('unidade') or 'm²'
            _estado = _txt(_b.get('estado'), '')
            _valor = _b.get('valor')
            if not (_preenchido(_tipo) or _preenchido(_desc)):
                continue
            _benf_rows.append([
                Paragraph(_esc_xml(_tipo), _sBenf),
                Paragraph(_esc_xml(_desc), _sBenf),
                _fmt_medida_benf(_med, _uni) if _preenchido(_med) else '',
                _estado or '',
                fmt_moeda(_valor) if _preenchido(_valor) else '',
            ])
        if _benf_rows:
            st += subsec('Benfeitorias do Imóvel Rural', 'sec3benf')
            _wT, _wM, _wE, _wV = 3.4 * cm, 2.1 * cm, 1.9 * cm, 2.6 * cm
            _wD = UTIL_W - (_wT + _wM + _wE + _wV)
            st.append(tbl_header(
                ['Benfeitoria', 'Descrição', 'Medida', 'Estado', 'Valor est.'],
                _benf_rows, [_wT, _wD, _wM, _wE, _wV]))

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
    _validas = len(_dentro)
    _eliminadas = max(_n - _validas, 0)
    # Mediana das amostras válidas (pós-saneamento)
    _ord = sorted(_dentro)
    if _ord:
        _mm = len(_ord)
        _mediana = _ord[_mm // 2] if _mm % 2 else (_ord[_mm // 2 - 1] + _ord[_mm // 2]) / 2.0
    else:
        _mediana = 0.0
    _ptam_inf = _ponderada * 0.95
    _ptam_sup = _ponderada * 1.05
    _un = 'ha' if _rural else 'm²'
    _cval = lambda x: f'R$ {_nv(x)}/{_un}'

    # Desvio padrão amostral (n-1) e CV sobre as válidas — espelha o sistema.
    _nvd = len(_dentro)
    if _nvd > 1:
        _media_vd = sum(_dentro) / _nvd
        _desvio_am = (sum((x - _media_vd) ** 2 for x in _dentro) / (_nvd - 1)) ** 0.5
    else:
        _desvio_am = 0.0
    _cv_final = (_desvio_am / _ponderada * 100) if _ponderada else 0.0
    _cv_lbl = ('Excelente' if _cv_final <= 10 else 'Bom' if _cv_final <= 15
               else 'Regular' if _cv_final <= 30 else 'Alto')

    _BG_NEU, _BG_RED, _BG_BLU, _BG_GRN = (HexColor('#F4F6F8'), HexColor('#FEECEC'),
                                          HexColor('#E8F1FE'), VERDE_CLR)

    # A. Saneamento das amostras (faixa ±10% em torno da média simples)
    st += subsec('A. Saneamento das Amostras', 'sec7stats')
    st.append(_pdf_cards_row([
        _pdf_card('Média Inicial', _cval(_media), '', '#1A1A1A'),
        _pdf_card('Limite Inferior (–10%)', _cval(_li), '', '#B91C1C'),
        _pdf_card('Limite Superior (+10%)', _cval(_ls), '', '#B91C1C'),
    ], [_BG_NEU, _BG_RED, _BG_RED]))
    st.append(Spacer(1, 4))
    st.append(_pdf_cards_row([
        _pdf_card('Total de Amostras', str(_n), '', '#1A1A1A', 12),
        _pdf_card('Válidas após Saneamento', str(_validas), '', '#0B6E4F', 12),
        _pdf_card('Eliminadas', str(_eliminadas), '', '#B91C1C', 12),
    ], [_BG_NEU, _BG_GRN, _BG_RED]))
    st.append(Spacer(1, 8))

    # B. Estatísticas finais (sobre as amostras válidas)
    st += subsec('B. Estatísticas Finais (pós-saneamento)')
    st.append(_pdf_cards_row([
        _pdf_card('Amostras Válidas', str(_validas), f'de {_n} inseridas', '#0B6E4F'),
        _pdf_card('Média Final', _cval(_ponderada), 'Valor adotado base', '#0B6E4F'),
        _pdf_card('Mediana', _cval(_mediana), '', '#1565C0'),
    ], [_BG_GRN, _BG_GRN, _BG_BLU]))
    st.append(Spacer(1, 4))
    st.append(_pdf_cards_row([
        _pdf_card('Desvio Padrão', _cval(_desvio_am), 'amostral (n-1)', '#1A1A1A'),
        _pdf_card('Coef. Variação', f'{_num(_cv_final)}%', _cv_lbl, '#0B6E4F'),
        _pdf_card('Intervalo PTAM ±5%', _cval(_ptam_inf), f'a {_cval(_ptam_sup)}', '#1A1A1A', 10),
    ], [_BG_NEU, _BG_GRN, _BG_NEU]))
    st.append(Spacer(1, 8))

    # C. Intervalo de valores do PTAM (±5%) — faixa em verde (Valor Adotado destacado)
    st += subsec('C. Intervalo de Valores do PTAM (±5%)')
    st.append(_pdf_cards_row([
        _pdf_card('Limite Inferior (–5%)', _cval(_ptam_inf), '', '#FFFFFF', 13, '#A7D7C5'),
        _pdf_card('Valor Adotado', _cval(_ponderada), 'Média final pós-saneamento', '#FFFFFF', 15, '#A7D7C5'),
        _pdf_card('Limite Superior (+5%)', _cval(_ptam_sup), '', '#FFFFFF', 13, '#A7D7C5'),
    ], [VERDE, HexColor('#0A5F44'), VERDE]))

    # Cálculo de Ponderância — Ponderação dos Valores (peso igualitário 1/N)
    _valid_am = [a for a in amostras if _li <= float(a.get('value_per_sqm') or 0) <= _ls] if amostras else []
    _nvp = len(_valid_am)
    if _nvp > 0:
        st.append(Spacer(1, 8))
        st += subsec('Cálculo de Ponderância — Ponderação dos Valores', 'sec7pond')
        # Card destaque (dashboard): Média Ponderada Final
        st.append(_pdf_cards_row([
            _pdf_card('Média Ponderada Final', f'R$ {_nv(_ponderada)}/{_un}',
                      f'Σ valores ponderados · peso 1/{_nvp} · {_nvp} amostras válidas',
                      '#FFFFFF', 17, '#EAF7F0'),
        ], [VERDE]))
        st.append(Spacer(1, 6))
        st.append(Paragraph(
            f'Fórmula: Média Ponderada Final = Σ (valor unitário × peso), com peso igualitário '
            f'1/{_nvp} sobre as {_nvp} amostras válidas (ABNT NBR 14653-2).', sBody))
        st.append(Spacer(1, 4))
        _peso = 1.0 / _nvp
        _rs = lambda x: 'R$ ' + _nv(x)
        _pond_rows = []
        _soma = 0.0
        for _ip, _ap in enumerate(_valid_am, 1):
            _vpm = float(_ap.get('value_per_sqm') or 0)
            _vp = _vpm * _peso
            _soma += _vp
            _bairro = str(_ap.get('neighborhood') or _ap.get('address') or '—')[:48]
            _pond_rows.append([str(_ip), _bairro, _rs(_vpm),
                               f'{_peso * 100:.2f}'.replace('.', ',') + '%', _rs(_vp)])
        _pond_rows.append(['', 'SOMA — Média Ponderada Final', '', '100,00%', _rs(_soma)])
        _wN, _wVu, _wP, _wVp = 1.0 * cm, 3.0 * cm, 2.2 * cm, 3.0 * cm
        _wB = UTIL_W - (_wN + _wVu + _wP + _wVp)
        st.append(tbl_header(['Nº', 'Bairro / Local', f'Valor ({_uv})', 'Peso (1/N)',
                              f'Valor Ponderado ({_uv})'],
                             _pond_rows, [_wN, _wB, _wVu, _wP, _wVp], bold_last=True, fontsize=7.5))

    # D. Graus de Fundamentação e Precisão (NBR 14653-2) — enquadramento do imóvel avaliando.
    # Fundamentação pelo nº de dados de mercado; Precisão pelo coeficiente de variação.
    _ndados = _nvp or _validas or _n
    _gf = 'III' if _ndados >= 12 else ('II' if _ndados >= 6 else ('I' if _ndados >= 3 else '—'))
    _gp = 'III' if _cv_final <= 10 else ('II' if _cv_final <= 20 else ('I' if _cv_final <= 30 else '—'))
    _gf_lbl = {'III': 'Máximo', 'II': 'Intermediário', 'I': 'Mínimo'}.get(_gf, 'Insuficiente')
    _gp_lbl = {'III': 'Máxima', 'II': 'Intermediária', 'I': 'Mínima'}.get(_gp, 'Fora dos limites')
    st.append(Spacer(1, 8))
    st += subsec('D. Graus de Fundamentação e Precisão (NBR 14653-2)', 'sec7graus')
    st.append(_pdf_cards_row([
        _pdf_card('Grau de Fundamentação', f'Grau {_gf}', f'{_gf_lbl} · {_ndados} dados de mercado', '#B8860B', 15),
        _pdf_card('Grau de Precisão', f'Grau {_gp}', f'{_gp_lbl} · CV {_num(_cv_final)}%', '#0B6E4F', 15),
    ], [HexColor('#FFF8E6'), VERDE_CLR]))
    st.append(Spacer(1, 4))
    st.append(Paragraph(
        f'Conforme a ABNT NBR 14653-2, o imóvel avaliando <b>enquadra-se no Grau {_gf} de Fundamentação</b> '
        f'(Método Comparativo Direto de Dados de Mercado, com {_ndados} dados) <b>e no Grau {_gp} de '
        f'Precisão</b> (coeficiente de variação de {_num(_cv_final)}%).', sBody))

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

    def _f8(v):
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    _valor_base = round(_f8(vu) * _f8(area_av), 2)   # valor pelo comparativo direto
    _metodo8 = str(ptam.get('metodo_avaliacao') or '').strip().lower()
    _MET_NOMES = {
        'ross_heidecke': 'Ross-Heidecke', 'linha_reta': 'Linha Reta',
        'fatores_terreno': 'Fatores de Terreno', 'nbr_rural': 'NBR Rural (INCRA)',
        'renda': 'Método da Renda',
    }
    _nome_met8 = _MET_NOMES.get(_metodo8, '')
    _dep_pct8 = ptam.get('depreciacao_percentual')
    _val_dep8 = ptam.get('valor_depreciacao')
    _val_met8 = ptam.get('valor_total_metodo')

    # ── Método de Avaliação — Depreciação/Valorização (DASHBOARD, antes do resultado) ──
    if _metodo8 and _metodo8 != 'nao_aplicado':
        _p8 = ptam.get('metodo_params') or {}
        st += subsec('Método de Avaliação — Depreciação/Valorização', 'sec8metodo')
        _met_rows = [('Método Aplicado', _nome_met8 or _metodo8)]
        if _metodo8 in ('ross_heidecke', 'linha_reta'):
            if _preenchido(_p8.get('valor_novo')):
                _met_rows.append(('Valor de Novo', fmt_moeda(_p8.get('valor_novo'))))
            if _preenchido(_p8.get('idade_atual')):
                _met_rows.append(('Idade Atual', f"{_num(_p8.get('idade_atual'))} anos"))
            if _preenchido(_p8.get('vida_util')):
                _met_rows.append(('Vida Útil', f"{_num(_p8.get('vida_util'))} anos"))
            if _metodo8 == 'ross_heidecke' and _p8.get('estado'):
                _met_rows.append(('Estado de Conservação', str(_p8.get('estado'))))
        elif _metodo8 == 'nbr_rural':
            if _preenchido(_p8.get('vtn_hectare')):
                _met_rows.append(('VTN — Valor por Hectare', f"{fmt_moeda(_p8.get('vtn_hectare'))}/ha"))
            if _preenchido(_p8.get('area_ha')):
                _met_rows.append(('Área Total', f"{_num(_p8.get('area_ha'))} ha"))
            if _preenchido(_p8.get('classe_uso')):
                _met_rows.append(('Classe de Uso / CUF', _num(_p8.get('classe_uso'))))
        elif _metodo8 == 'renda':
            if _preenchido(_p8.get('renda_mensal')):
                _met_rows.append(('Renda Mensal', fmt_moeda(_p8.get('renda_mensal'))))
            if _preenchido(_p8.get('taxa_cap')):
                _met_rows.append(('Taxa de Capitalização', f"{_num(_p8.get('taxa_cap'))}% a.a."))
        st.append(tbl(_met_rows))
        st.append(Spacer(1, 6))
        # Cards de resultado do método (dashboard)
        if _metodo8 in ('ross_heidecke', 'linha_reta'):
            _kd = _f8(_dep_pct8) / 100.0
            st.append(_pdf_cards_row([
                _pdf_card('Coeficiente Kd', f'{_kd:.4f}'.replace('.', ','), f'{_num(_dep_pct8)}% depreciado', '#B8860B', 15),
                _pdf_card('Depreciação', fmt_moeda(_val_dep8), 'sobre o valor de novo', '#B91C1C', 14),
                _pdf_card('Valor Residual', fmt_moeda(vtotal), 'após depreciação', '#0B6E4F', 14),
            ], [HexColor('#FFF8E6'), HexColor('#FEECEC'), VERDE_CLR]))
        elif _metodo8 == 'nbr_rural':
            _vterra = _f8(_p8.get('vtn_hectare')) * _f8(_p8.get('area_ha')) * (_f8(_p8.get('classe_uso')) or 1)
            st.append(_pdf_cards_row([
                _pdf_card('Valor da Terra Nua', fmt_moeda(_vterra), 'VTN × área × CUF', '#0B6E4F', 14),
                _pdf_card('Valor Total Rural', fmt_moeda(_val_met8), 'terra + benfeitorias + culturas', '#0B6E4F', 14),
            ], [VERDE_CLR, VERDE_CLR]))
        elif _metodo8 == 'renda':
            st.append(_pdf_cards_row([
                _pdf_card('Renda Anual', fmt_moeda(_f8(_p8.get('renda_mensal')) * 12), '', '#1A1A1A', 14),
                _pdf_card('Taxa de Capitalização', f"{_num(_p8.get('taxa_cap') or 8)}% a.a.", '', '#1565C0', 14),
                _pdf_card('Valor Capitalizado', fmt_moeda(_val_met8), '', '#0B6E4F', 14),
            ], [HexColor('#F4F6F8'), HexColor('#E8F1FE'), VERDE_CLR]))
        st.append(Spacer(1, 8))

    # ── E. Área considerada — conversões e valor unitário (planilha, antes do resultado) ──
    _avm2 = _f8(area_av)
    if _avm2 > 0:
        _vuf = _f8(vu)
        _ha = _avm2 / 10000.0
        _alq = _ha / 4.84
        st += subsec('Área Considerada — Conversões e Valor Unitário')
        st.append(tbl([
            ('Área (m²)', f"{_num(_avm2)} m²"),
            ('Área (hectares)', f"{('%.4f' % _ha).replace('.', ',')} ha"),
            ('Área (alqueires mineiros)', f"{('%.4f' % _alq).replace('.', ',')} alq  (1 alq = 4,84 ha)"),
            ('Valor Unitário (R$/m²)', fmt_moeda(_vuf)),
            ('Valor Unitário (R$/ha)', fmt_moeda(_vuf * 10000)),
            ('Valor Unitário (R$/alqueire mineiro)', fmt_moeda(_vuf * 48400)),
        ]))
        st.append(Spacer(1, 8))

    # ── RESULTADO: Cálculo do Valor Final + Valor de Mercado — MANTIDO NA MESMA PÁGINA ──
    _calc_rows = [['Média Ponderada Final', fmt_rs_unit(vu, _rural8)]]
    if _rural8:
        _calc_rows.append(['Valor unitário de referência', f"{fmt_moeda(vu)}/m²"])
    _calc_rows.append(['Área do Imóvel Avaliando', _area_avaliando_str(ptam, area_av, _rural8)])
    if _metodo8 in ('ross_heidecke', 'linha_reta') and _preenchido(_val_dep8):
        _calc_rows.append([
            f"Valor de Referência (Comparativo) = {fmt_rs_unit(vu, _rural8)} × {fmt_area_rural(area_av, _rural8)}",
            fmt_moeda(_valor_base)])
        _pct8 = f" ({_num(_dep_pct8)}%)" if _preenchido(_dep_pct8) else ""
        _calc_rows.append([f"(−) Depreciação — {_nome_met8}{_pct8}", fmt_moeda(_val_dep8)])
        _calc_rows.append([f"Valor Final (após depreciação — {_nome_met8})", fmt_moeda(vtotal)])
    elif _metodo8 in ('nbr_rural', 'fatores_terreno', 'renda') and _preenchido(_val_met8):
        _calc_rows.append([f"Valor Apurado pelo Método {_nome_met8}", fmt_moeda(vtotal)])
    else:
        _calc_rows.append([
            f"Valor Final = {fmt_rs_unit(vu, _rural8)} × {fmt_area_rural(area_av, _rural8)}",
            fmt_moeda(vtotal)])

    _res_rows = []
    if _rural8:
        _vu_f = _f8(vu)
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

    _resultado = []
    _resultado += subsec('Cálculo do Valor Final', 'sec8calc')
    _resultado.append(tbl_header(['Componente', 'Valor'], _calc_rows,
                                 [UTIL_W - 4.5 * cm, 4.5 * cm], bold_last=True))
    _resultado.append(Spacer(1, 10))
    _resultado.append(caixa_valor(vtotal, ptam.get('total_indemnity_words') or valor_por_extenso(vtotal)))
    _resultado.append(Spacer(1, 10))
    _resultado.append(tbl(_res_rows))
    st.append(KeepTogether(_resultado))

    # ── Justificativa técnico-jurídica do método/depreciação (após o valor, antes da conclusão) ──
    _justif = _justificativa_metodo(ptam)
    if _justif:
        st.append(Spacer(1, 10))
        st += subsec('Justificativa Técnica do Método e da Depreciação/Valorização', 'sec8justif')
        # Aceita texto puro/<b> (automático) OU HTML do RichTextEditor (negrito/itálico/listas/alinhamento).
        for _blk in html_para_blocks(_justif):
            _mk = _blk.get('markup')
            if not _mk:
                continue
            _al = {'left': 0, 'center': 1, 'right': 2, 'justify': 4}.get(_blk.get('align'), 4)
            _ex = {'alignment': _al}
            if _blk.get('bullet'):
                _ex['leftIndent'] = 0.5 * cm
            st.append(Paragraph(_mk, ParagraphStyle('s8justifb', parent=sBody, **_ex)))

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
    """Ponto de entrada: gera o PDF do PTAM (layout aprovado) e retorna bytes.

    White-label: se ptam trouxer _brand_primary/_brand_secondary (injetado pela
    rota quando o usuário tem marca própria), as cores do tema são aplicadas só
    durante esta geração e restauradas em seguida — PTAMs de quem usa o padrão
    saem com o verde/dourado de sempre.
    """
    ptam = dict(ptam or {})
    if perfil is not None:
        ptam['_perfil'] = perfil
    primary = ptam.get('_brand_primary')
    secondary = ptam.get('_brand_secondary')
    saved = _apply_brand_theme(primary, secondary) if primary else None
    try:
        return build_ptam_pdf(ptam)
    finally:
        _restore_theme(saved)
