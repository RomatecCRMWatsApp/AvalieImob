# @module services.contrato_exclusividade_pdf — PDF do Contrato de Exclusividade (aceite eletrônico)
"""
Gerador ReportLab do Contrato de Exclusividade com aceite eletrônico via WhatsApp.
Padrão Romatec (verde #0B6E4F, dourado #B8860B, TA_JUSTIFY em todo texto corrido).

API:
  - montar_texto_contrato(contrato) -> str         (mesmo texto exibido na tela de aceite)
  - gerar_pdf_rascunho(contrato)    -> bytes        (marca d'água "AGUARDANDO ACEITE")
  - gerar_pdf_final(contrato)       -> bytes        (selo "✓ ACEITO ELETRONICAMENTE" + QR + auditoria)
"""
import io
import os
from datetime import datetime
from typing import List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("America/Fortaleza")
except Exception:  # pragma: no cover
    _TZ = None

VERDE = colors.HexColor("#0B6E4F")
DOURADO = colors.HexColor("#B8860B")
CINZA = colors.HexColor("#444444")

APP_URL = os.environ.get("APP_PUBLIC_URL", "https://romatecavalieimob.com.br").rstrip("/")

CONTRATADA = {
    "razao": "ROMATEC CONSULTORIA TOTAL",
    "cnpj": "17.261.987/0001-09",
    "endereco": "Rua São Raimundo, nº 10, Centro, Açailândia/MA",
    "rep": "José Romário Pinto Bezerra",
    "creci": "CRECI/MA 4.705",
    "cnai": "Avaliador CNAI 031161",
}

_ESTADO_CIVIL = {
    "solteiro": "solteiro(a)", "casado": "casado(a)",
    "uniao_estavel": "convivente em união estável",
    "divorciado": "divorciado(a)", "viuvo": "viúvo(a)",
}
_REGIME = {
    "comunhao_parcial": "comunhão parcial de bens",
    "comunhao_universal": "comunhão universal de bens",
    "separacao_total": "separação total de bens",
    "participacao_final_aquestos": "participação final nos aquestos",
}
_PAPEL = {"proprietario": "Proprietário(a)", "conjuge": "Cônjuge/Companheiro(a)"}


# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------

def _brl(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 0.0
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_cpf(cpf: str) -> str:
    d = "".join(filter(str.isdigit, cpf or ""))
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}" if len(d) == 11 else (cpf or "")


def _fmt_fone(w: str) -> str:
    d = "".join(filter(str.isdigit, w or ""))
    if len(d) >= 12:  # 55 + DDD + numero
        return f"+{d[:2]} ({d[2:4]}) {d[4:-4]}-{d[-4:]}"
    return w or ""


def _fmt_dt_local(dt) -> str:
    if not dt:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt
    if _TZ is not None and dt.tzinfo is not None:
        dt = dt.astimezone(_TZ)
    return dt.strftime("%d/%m/%Y às %H:%M")


def _esc(t: Optional[str]) -> str:
    if not t:
        return ""
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Qualificação das partes
# ---------------------------------------------------------------------------

def _qualificar_pessoa(p: dict, estado_civil: str = "", regime: str = "") -> str:
    partes = [f"<b>{_esc(p.get('nome'))}</b>", _esc(p.get("nacionalidade") or "brasileiro(a)")]
    if estado_civil:
        ec = _ESTADO_CIVIL.get(estado_civil, estado_civil)
        if regime:
            ec += f", sob o regime de {_REGIME.get(regime, regime)}"
        partes.append(ec)
    if p.get("profissao"):
        partes.append(_esc(p["profissao"]))
    ident = [f"inscrito(a) no CPF sob nº {_fmt_cpf(p.get('cpf'))}"]
    if p.get("rg"):
        rg = f"portador(a) do RG nº {_esc(p['rg'])}"
        if p.get("rg_orgao"):
            rg += f" {_esc(p['rg_orgao'])}"
        ident.insert(0, rg)
    partes.append(", ".join(ident))
    partes.append(f"WhatsApp {_fmt_fone(p.get('whatsapp'))}")
    if p.get("email"):
        partes.append(f"e-mail {_esc(p['email'])}")
    return ", ".join(partes)


# ---------------------------------------------------------------------------
# Corpo do contrato (compartilhado tela + PDF)
# ---------------------------------------------------------------------------

def _secoes(contrato: dict) -> List[Tuple[str, List[str]]]:
    prop = contrato.get("proprietario", {})
    conj = contrato.get("conjuge")
    imovel = contrato.get("imovel", {})
    ec = contrato.get("estado_civil", "")
    regime = contrato.get("regime_bens", "") or ""
    comissao = contrato.get("comissao_percentual", 0)
    prazo = contrato.get("prazo_meses", 6)

    secoes: List[Tuple[str, List[str]]] = []

    # DAS PARTES
    partes_txt = ["CONTRATANTE: " + _qualificar_pessoa(prop, ec, regime) + ";"]
    if conj:
        partes_txt.append("CÔNJUGE/COMPANHEIRO(A) ANUENTE: " + _qualificar_pessoa(conj) + ";")
    partes_txt.append(
        "CONTRATADA: <b>{razao}</b>, inscrita no CNPJ sob nº {cnpj}, com sede na {end}, "
        "representada por {rep}, Corretor de Imóveis {creci} e {cnai}.".format(
            razao=CONTRATADA["razao"], cnpj=CONTRATADA["cnpj"], end=CONTRATADA["endereco"],
            rep=CONTRATADA["rep"], creci=CONTRATADA["creci"], cnai=CONTRATADA["cnai"]))
    secoes.append(("DAS PARTES", partes_txt))

    # CLÁUSULA 1ª — OBJETO
    secoes.append(("CLÁUSULA PRIMEIRA — DO OBJETO", [
        "O presente contrato tem por objeto a prestação, pela CONTRATADA, de serviços "
        "de corretagem imobiliária em caráter de EXCLUSIVIDADE, para a intermediação da "
        "venda do imóvel descrito na cláusula segunda, nos termos do art. 726 do Código "
        "Civil e da Lei nº 6.530/1978."]))

    # CLÁUSULA 2ª — DESCRIÇÃO DO IMÓVEL
    desc = [f"Imóvel: {_esc(imovel.get('descricao'))}.",
            f"Endereço: {_esc(imovel.get('endereco'))}, {_esc(imovel.get('bairro'))}, "
            f"{_esc(imovel.get('cidade'))}/{_esc(imovel.get('uf'))}."]
    if imovel.get("matricula"):
        m = f"Matrícula nº {_esc(imovel['matricula'])}"
        if imovel.get("cartorio"):
            m += f", do {_esc(imovel['cartorio'])}"
        desc.append(m + ".")
    if imovel.get("area_total"):
        desc.append(f"Área: {_esc(imovel['area_total'])}.")
    desc.append(f"Valor anunciado: {_brl(imovel.get('valor_anunciado'))}.")
    secoes.append(("CLÁUSULA SEGUNDA — DA DESCRIÇÃO DO IMÓVEL", desc))

    # CLÁUSULA 3ª — PRAZO
    secoes.append(("CLÁUSULA TERCEIRA — DO PRAZO DE EXCLUSIVIDADE", [
        f"A exclusividade ora pactuada vigorará pelo prazo de {prazo} ({prazo}) meses, "
        f"contados da assinatura eletrônica deste instrumento, renovável por igual período "
        f"mediante anuência expressa das partes."]))

    # CLÁUSULA 4ª — COMISSÃO
    pct = f"{comissao:g}%".replace(".", ",")
    secoes.append(("CLÁUSULA QUARTA — DA COMISSÃO", [
        f"Pela intermediação, será devida à CONTRATADA comissão de {pct} sobre o valor "
        f"efetivo da transação, devida ainda que o negócio se realize diretamente pelo(s) "
        f"CONTRATANTE(S) durante a vigência da exclusividade, nos termos da parte final do "
        f"art. 726 do Código Civil."]))

    # CLÁUSULA 5ª — OBRIGAÇÕES DA CONTRATADA
    secoes.append(("CLÁUSULA QUINTA — DAS OBRIGAÇÕES DA CONTRATADA", [
        "Compete à CONTRATADA promover a divulgação do imóvel, acompanhar as visitas, "
        "qualificar interessados e prestar contas das diligências realizadas."]))

    # CLÁUSULA 6ª — OBRIGAÇÕES DO(S) CONTRATANTE(S)
    secoes.append(("CLÁUSULA SEXTA — DAS OBRIGAÇÕES DO(S) CONTRATANTE(S)", [
        "Compete ao(s) CONTRATANTE(S) fornecer a documentação do imóvel, franquear o "
        "acesso para visitas e prestar informações verídicas sobre o bem."]))

    # CLÁUSULA 7ª — ACEITE ELETRÔNICO
    secoes.append(("CLÁUSULA SÉTIMA — DO ACEITE ELETRÔNICO", [
        "As partes reconhecem como válida e eficaz a manifestação de vontade externada por "
        "meio eletrônico, mediante confirmação em link individual enviado ao número de "
        "WhatsApp de cada signatário, nos termos do art. 10, §2º, da MP nº 2.200-2/2001 e da "
        "Lei nº 14.063/2020, atribuindo-se ao registro de aceite (data, hora, endereço IP e "
        "identificador do dispositivo) força probatória da autoria e integridade deste "
        "instrumento, aferível pelo código hash SHA-256 nele consignado."]))

    # CLÁUSULA 8ª — RESCISÃO
    secoes.append(("CLÁUSULA OITAVA — DA RESCISÃO E PENALIDADES", [
        "A rescisão antecipada e imotivada por iniciativa do(s) CONTRATANTE(S), durante a "
        "vigência da exclusividade, não afasta o direito da CONTRATADA à comissão pactuada "
        "quando comprovada a aproximação útil das partes."]))

    # CLÁUSULA 9ª — FORO
    secoes.append(("CLÁUSULA NONA — DO FORO", [
        "Fica eleito o foro da comarca de Açailândia/MA, com renúncia a qualquer outro, por "
        "mais privilegiado que seja, para dirimir quaisquer controvérsias oriundas deste "
        "contrato."]))

    return secoes


def montar_texto_contrato(contrato: dict) -> str:
    """Texto integral do contrato (mesmo conteúdo do PDF) para exibição na tela de aceite."""
    linhas = ["CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE CORRETAGEM COM EXCLUSIVIDADE", ""]
    import re
    for titulo, paragrafos in _secoes(contrato):
        linhas.append(titulo)
        for p in paragrafos:
            linhas.append(re.sub(r"</?b>", "", p))  # remove negrito do texto plano
        linhas.append("")
    return "\n".join(linhas).strip()


# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------

def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("t", parent=base["Title"], fontName="Times-Bold",
                                 fontSize=14, textColor=VERDE, alignment=TA_CENTER, spaceAfter=10),
        "clausula": ParagraphStyle("c", parent=base["Heading2"], fontName="Times-Bold",
                                   fontSize=11, textColor=VERDE, spaceBefore=10, spaceAfter=4),
        "corpo": ParagraphStyle("p", parent=base["Normal"], fontName="Times-Roman",
                                fontSize=10.5, alignment=TA_JUSTIFY, leading=15, spaceAfter=5),
        "ass": ParagraphStyle("a", parent=base["Normal"], fontName="Times-Roman",
                              fontSize=9.5, alignment=TA_CENTER, leading=13),
        "legenda": ParagraphStyle("l", parent=base["Normal"], fontName="Helvetica",
                                  fontSize=8, textColor=CINZA, alignment=TA_CENTER),
        "hash": ParagraphStyle("h", parent=base["Normal"], fontName="Courier",
                               fontSize=7, textColor=CINZA, alignment=TA_CENTER),
    }


def _qr(url: str, tam: float = 2.6 * cm) -> Optional[Image]:
    try:
        import qrcode
        qr = qrcode.QRCode(border=1, box_size=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0B6E4F", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Image(buf, width=tam, height=tam)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Template (cabeçalho/rodapé + marca d'água/selo)
# ---------------------------------------------------------------------------

class _ContratoDoc(BaseDocTemplate):
    def __init__(self, buf, contrato: dict, final: bool, **kw):
        super().__init__(buf, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                         topMargin=3.0 * cm, bottomMargin=2.4 * cm, **kw)
        self.contrato = contrato
        self.final = final
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="c")
        self.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=self._deco)])

    def _deco(self, canvas, doc):
        canvas.saveState()
        largura, altura = A4
        # Cabeçalho
        canvas.setFillColor(VERDE)
        canvas.rect(0, altura - 1.7 * cm, largura, 1.7 * cm, fill=1, stroke=0)
        canvas.setFillColor(DOURADO)
        canvas.rect(0, altura - 1.78 * cm, largura, 0.08 * cm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Times-Bold", 14)
        canvas.drawString(2.2 * cm, altura - 1.15 * cm, "ROMATEC")
        canvas.setFont("Times-Roman", 8)
        canvas.drawString(2.2 * cm, altura - 1.5 * cm, "Consultoria Total")
        # Rodapé
        canvas.setFillColor(DOURADO)
        canvas.rect(0, 1.4 * cm, largura, 0.05 * cm, fill=1, stroke=0)
        canvas.setFillColor(CINZA)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawCentredString(
            largura / 2, 1.0 * cm,
            f"{CONTRATADA['razao']} · CNPJ {CONTRATADA['cnpj']} · {CONTRATADA['creci']} · "
            f"{CONTRATADA['cnai']} · {CONTRATADA['endereco']}")
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(largura - 2.2 * cm, 1.0 * cm, f"Página {doc.page}")
        # Marca d'água / selo diagonal
        canvas.saveState()
        canvas.translate(largura / 2, altura / 2)
        canvas.rotate(45)
        if self.final:
            canvas.setFillColor(colors.Color(11/255, 110/255, 79/255, alpha=0.10))
            canvas.setFont("Helvetica-Bold", 46)
            canvas.drawCentredString(0, 0, "✓ ACEITO ELETRONICAMENTE")
        else:
            canvas.setFillColor(colors.Color(0.5, 0.5, 0.5, alpha=0.13))
            canvas.setFont("Helvetica-Bold", 34)
            canvas.drawCentredString(0, 10, "AGUARDANDO ACEITE")
            canvas.setFont("Helvetica-Bold", 20)
            canvas.drawCentredString(0, -24, "SEM VALIDADE")
        canvas.restoreState()
        canvas.restoreState()


# ---------------------------------------------------------------------------
# Blocos de assinatura
# ---------------------------------------------------------------------------

def _bloco_assinatura(s: dict, st: dict, final: bool) -> Table:
    papel = _PAPEL.get(s.get("papel"), s.get("papel"))
    linhas = []
    if final and s.get("aceite"):
        a = s["aceite"]
        linhas = [
            "<b>✓ ACEITO ELETRONICAMENTE</b>",
            f"Nome: {_esc(s.get('nome'))} — CPF: {_fmt_cpf(s.get('cpf'))}",
            f"Papel: {papel}",
            f"Data/Hora: {_fmt_dt_local(a.get('data_hora_utc'))} (America/Fortaleza)",
            f"WhatsApp vinculado: {_fmt_fone(a.get('whatsapp_vinculado'))} — IP: {_esc(a.get('ip'))}",
        ]
    else:
        linhas = [
            "_" * 42,
            f"<b>{_esc(s.get('nome'))}</b> — {papel}",
            f"CPF: {_fmt_cpf(s.get('cpf'))}",
            "Aguardando aceite eletrônico",
        ]
    paras = [Paragraph(t, st["ass"]) for t in linhas]
    tbl = Table([[paras]], colWidths=[15 * cm])
    estilo = [("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 6),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]
    if final and s.get("aceite"):
        estilo += [("BOX", (0, 0), (-1, -1), 0.6, VERDE),
                   ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f7f4"))]
    tbl.setStyle(TableStyle(estilo))
    return tbl


# ---------------------------------------------------------------------------
# Construção do PDF
# ---------------------------------------------------------------------------

def _gerar(contrato: dict, final: bool) -> bytes:
    st = _styles()
    buf = io.BytesIO()
    doc = _ContratoDoc(buf, contrato, final)
    story: List = [
        Paragraph("CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE CORRETAGEM COM EXCLUSIVIDADE",
                  st["titulo"]),
    ]
    for titulo, paragrafos in _secoes(contrato):
        story.append(Paragraph(titulo, st["clausula"]))
        for p in paragrafos:
            story.append(Paragraph(p, st["corpo"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("DAS ASSINATURAS ELETRÔNICAS", st["clausula"]))
    for s in contrato.get("signatarios", []):
        story.append(_bloco_assinatura(s, st, final))
        story.append(Spacer(1, 8))

    if final:
        story.append(Spacer(1, 10))
        hash_doc = contrato.get("hash_documento", "")
        url = f"{APP_URL}/verificar/{hash_doc}"
        qr = _qr(url)
        bloco = []
        if qr:
            bloco.append(qr)
        bloco.append(Paragraph("Verificação de autenticidade", st["legenda"]))
        bloco.append(Paragraph(url, st["hash"]))
        bloco.append(Paragraph(f"SHA-256: {hash_doc}", st["hash"]))
        t = Table([[bloco]], colWidths=[8 * cm])
        t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(t)

    doc.multiBuild(story)
    buf.seek(0)
    return buf.read()


def gerar_pdf_rascunho(contrato: dict) -> bytes:
    return _gerar(contrato, final=False)


def gerar_pdf_final(contrato: dict) -> bytes:
    return _gerar(contrato, final=True)
