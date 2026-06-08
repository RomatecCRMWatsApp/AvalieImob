# @module services.pdf_consulta — PDF de Consulta Rápida (CNPJ/CPF) — padrão Romatec
"""Documento profissional no padrão visual Romatec (verde escuro institucional +
mourão + dourado sóbrio). Flowables customizados: Header, EmpresaBlock, DivLine,
SecTitle. Usado pelo widget de Consulta Rápida (visualizar / baixar / enviar).

Função pública:
    gerar_pdf_consulta(...) -> bytes   (também grava em output_path se informado)

Adaptadores chamados pelas rotas (recebem o dict normalizado da consulta):
    gerar_pdf_cnpj(dados, perfil) -> bytes
    gerar_pdf_cpf(dados, perfil)  -> bytes
"""
import os
import logging
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Flowable, Paragraph, Spacer, Table, TableStyle,
)

logger = logging.getLogger("romatec")

# ── Paleta Romatec ───────────────────────────────────────────────────────────
VERDE_ESC = colors.HexColor("#1A3A1A")
VERDE_MED = colors.HexColor("#2D5A2D")
VERDE_ACC = colors.HexColor("#4A8C4A")
MOURADO = colors.HexColor("#3D1A3D")
MOURADO_M = colors.HexColor("#6B2D6B")
OURO = colors.HexColor("#B8962E")
CINZA_LN = colors.HexColor("#E8E8E4")
CINZA_ALT = colors.HexColor("#F2F2EF")
CINZA_LBL = colors.HexColor("#6B6B68")
PRETO = colors.HexColor("#1C1C1C")
WHITE = colors.white
VERM = colors.HexColor("#B23A3A")
VERDE_LABEL = colors.HexColor("#99BB99")
CINZA_DIR = colors.HexColor("#AAAAAA")
CINZA_CRED = colors.HexColor("#777777")

# ── Página ───────────────────────────────────────────────────────────────────
MARGEM = 2.2 * cm
W, H = A4
USABLE = W - 2 * MARGEM

LOGO_PATH_PADRAO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "avalieimob_logo.png",
)
DEFAULT_CRED = "CFT/MA 01209185369   |   CRECI/MA 4.705   |   CNAI 031161"


def _logo_padrao() -> str | None:
    """Resolve o logo do tenant. Hoje: AvalieImob (assets) com fallbacks no build."""
    candidatos = [
        LOGO_PATH_PADRAO,
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "frontend", "build", "brand", "logo_principal.jpg"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "frontend", "build", "brand", "icone.png"),
    ]
    for c in candidatos:
        if c and os.path.exists(c):
            return c
    return None


# ── Flowables ────────────────────────────────────────────────────────────────
class Header(Flowable):
    def __init__(self, tipo, documento, status, badge_ok, data_emissao, credenciais, logo_path):
        super().__init__()
        self.tipo = tipo
        self.documento = documento or "—"
        self.status = (status or "").strip()
        self.badge_ok = badge_ok
        self.data = (data_emissao or "").split(" às ")[0]
        self.credenciais = credenciais or DEFAULT_CRED
        self.logo_path = logo_path
        self.height = 82

    def wrap(self, aw, ah):
        self.width = aw
        return (aw, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        # fundo verde
        c.setFillColor(VERDE_ESC); c.rect(0, 0, w, h, fill=1, stroke=0)
        # faixa mourão esquerda
        c.setFillColor(MOURADO); c.rect(0, 0, 5, h, fill=1, stroke=0)
        # linha dourada topo
        c.setFillColor(OURO); c.rect(0, h - 2, w, 2, fill=1, stroke=0)

        # pill branco do logo
        pill_x, pill_w, pill_h = 14, 98, 44
        pill_y = (h - pill_h) / 2.0
        c.setFillColor(WHITE)
        c.roundRect(pill_x, pill_y, pill_w, pill_h, 3, fill=1, stroke=0)
        if self.logo_path:
            try:
                c.drawImage(ImageReader(self.logo_path), pill_x + 5, pill_y + 5, 88, 34,
                            preserveAspectRatio=True, mask="auto")
            except Exception as e:
                logger.warning("PDF consulta: falha ao desenhar logo: %s", e)

        # separador vertical dourado
        c.setStrokeColor(OURO); c.setLineWidth(0.6)
        c.line(pill_x + pill_w + 13, 18, pill_x + pill_w + 13, h - 18)

        # bloco central
        cx = pill_x + pill_w + 26
        c.setFillColor(VERDE_LABEL); c.setFont("Helvetica", 7.5)
        fonte_orgao = "RECEITA FEDERAL DO BRASIL" if self.tipo == "CNPJ" else "VALIDAÇÃO LOCAL"
        c.drawString(cx, h - 22, f"CONSULTA  {self.tipo}  —  {fonte_orgao}")
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 18)
        c.drawString(cx, 30, self.documento)
        # badge
        badge_txt = (self.status or ("ATIVO" if self.badge_ok else "—")).upper()
        c.setFont("Helvetica-Bold", 7.5)
        bw = c.stringWidth(badge_txt, "Helvetica-Bold", 7.5) + 16
        c.setFillColor(VERDE_ACC if self.badge_ok else VERM)
        c.roundRect(cx, 9, bw, 14, 3, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.drawString(cx + 8, 13, badge_txt)

        # bloco direito
        c.setFillColor(OURO); c.setFont("Helvetica-Bold", 11)
        c.drawRightString(w, h - 21, "AvalieImob")
        c.setFillColor(CINZA_DIR); c.setFont("Helvetica", 7.5)
        c.drawRightString(w, h - 34, "PTAM · Laudos")
        c.drawRightString(w, h - 46, self.data)
        c.setFillColor(CINZA_CRED); c.setFont("Helvetica", 6.5)
        c.drawRightString(w, 12, self.credenciais)


class EmpresaBlock(Flowable):
    def __init__(self, tipo_pessoa, nome, nome2):
        super().__init__()
        self.tipo_pessoa = tipo_pessoa
        self.nome = nome or "—"
        self.nome2 = (nome2 or "").strip()
        self.height = 52

    def wrap(self, aw, ah):
        self.width = aw
        return (aw, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(WHITE); c.rect(0, 0, w, h, fill=1, stroke=0)
        # pill mourão
        c.setFillColor(MOURADO)
        c.roundRect(0, 37, 100, 14, 3, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(50, 41, self.tipo_pessoa)
        # nome principal
        c.setFillColor(PRETO); c.setFont("Helvetica-Bold", 15)
        c.drawString(0, 16, self.nome[:70])
        # subtítulo
        if self.nome2:
            c.setFillColor(MOURADO_M); c.setFont("Helvetica", 9)
            c.drawString(0, 3, self.nome2[:90])


class DivLine(Flowable):
    def __init__(self):
        super().__init__()
        self.height = 4

    def wrap(self, aw, ah):
        self.width = aw
        return (aw, self.height)

    def draw(self):
        c = self.canv
        w = self.width
        c.setFillColor(VERDE_MED); c.rect(0, 2.5, w, 1.5, fill=1, stroke=0)
        c.setFillColor(MOURADO); c.rect(0, 0, w, 1.0, fill=1, stroke=0)


class SecTitle(Flowable):
    def __init__(self, titulo):
        super().__init__()
        self.titulo = titulo
        self.height = 22

    def wrap(self, aw, ah):
        self.width = aw
        return (aw, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(CINZA_ALT); c.rect(3, 0, w - 3, h, fill=1, stroke=0)
        c.setFillColor(VERDE_MED); c.rect(0, 0, 3, h, fill=1, stroke=0)
        c.setFillColor(VERDE_ESC); c.setFont("Helvetica-Bold", 8)
        c.drawString(12, 7, (self.titulo or "").upper())


# ── Tabela de uma seção ──────────────────────────────────────────────────────
def _tabela_secao(linhas, s_lbl, s_val):
    """Monta a tabela 2-colunas (2 campos por linha). Cada campo = label + valor."""
    def _cell(par):
        lb, vl = par
        return [Paragraph(_esc(lb), s_lbl), Paragraph(_esc(vl), s_val)]

    linhas = [(lb, vl) for lb, vl in linhas if vl is not None and str(vl).strip()]
    if not linhas:
        return None
    rows = []
    for i in range(0, len(linhas), 2):
        esq = _cell(linhas[i])
        dir_ = _cell(linhas[i + 1]) if i + 1 < len(linhas) else ""
        rows.append([esq, dir_])
    col = USABLE / 2.0
    t = Table(rows, colWidths=[col, col])
    style = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, CINZA_LN),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, CINZA_ALT]),
    ])
    t.setStyle(style)
    return t


def _esc(s) -> str:
    return str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── Função principal ─────────────────────────────────────────────────────────
def gerar_pdf_consulta(
    *,
    tipo: str,
    documento: str,
    status: str,
    nome: str,
    nome2: str,
    secoes: list,
    fonte: str,
    data_emissao: str,
    logo_path: str | None = None,
    credenciais: str | None = None,
    output_path: str | None = None,
) -> bytes:
    badge_ok = _status_ok(tipo, status)
    tipo_pessoa = "PESSOA JURÍDICA" if tipo == "CNPJ" else "PESSOA FÍSICA"

    s_lbl = ParagraphStyle("lbl", fontName="Helvetica", fontSize=7.5,
                           textColor=CINZA_LBL, leading=10)
    s_val = ParagraphStyle("val", fontName="Helvetica-Bold", fontSize=9.5,
                           textColor=PRETO, leading=13)
    s_foot1 = ParagraphStyle("f1", fontName="Helvetica", fontSize=7.5,
                             textColor=CINZA_LBL, leading=11, alignment=1)
    s_foot2 = ParagraphStyle("f2", fontName="Helvetica", fontSize=7,
                             textColor=CINZA_DIR, leading=10, alignment=1)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title=f"Consulta {tipo} {documento}",
    )

    story = [
        Header(tipo, documento, status, badge_ok, data_emissao,
               credenciais or DEFAULT_CRED, logo_path or _logo_padrao()),
        Spacer(1, 12),
        EmpresaBlock(tipo_pessoa, nome, nome2),
        Spacer(1, 4),
        DivLine(),
        Spacer(1, 6),
    ]

    for sec in secoes or []:
        tab = _tabela_secao(sec.get("linhas") or [], s_lbl, s_val)
        if tab is None:
            continue
        story.append(SecTitle(sec.get("titulo", "")))
        story.append(tab)
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 2))
    story.append(DivLine())
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Fonte: {_esc(fonte)}  ·  Emitido em: {_esc(data_emissao)}", s_foot1))
    story.append(Paragraph(
        f"Romatec Consultoria Total  ·  AvalieImob  ·  {_esc(credenciais or DEFAULT_CRED)}", s_foot2))

    doc.build(story)
    pdf = buf.getvalue()
    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf)
    return pdf


def _status_ok(tipo: str, status: str) -> bool:
    s = (status or "").strip().lower()
    if tipo == "CPF":
        return "vál" in s or "valid" in s
    return "ativ" in s


# ── Formatadores ─────────────────────────────────────────────────────────────
def _moeda(v) -> str | None:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n == 0:
        return None
    return "R$ " + f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data_br(v) -> str | None:
    s = (v or "").strip()
    if not s:
        return None
    if len(s) == 10 and s[4] == "-":  # YYYY-MM-DD
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def _credenciais(perfil: dict | None) -> str:
    regs = (perfil or {}).get("registros") or []
    partes = []
    for r in regs:
        if isinstance(r, dict) and r.get("numero"):
            uf = f"/{r.get('uf')}" if r.get("uf") else ""
            partes.append(f"{r.get('tipo', '')}{uf} {r.get('numero')}".strip())
    return "   |   ".join(partes) if partes else DEFAULT_CRED


def _fonte_label(fonte: str) -> str:
    return {
        "prospectabr": "ProspectaBR (base local) — Receita Federal do Brasil",
        "cnpjws": "CNPJ.ws — Receita Federal do Brasil",
        "receitaws": "ReceitaWS — Receita Federal do Brasil",
    }.get(fonte or "", "Receita Federal do Brasil")


# ── Adaptadores chamados pelas rotas ─────────────────────────────────────────
def gerar_pdf_cnpj(dados: dict, perfil: dict | None = None) -> bytes:
    d = dados or {}
    end_log = ", ".join(x for x in [d.get("logradouro"), d.get("numero")] if x and str(x).strip())
    municipio = (d.get("municipio") or "").strip()
    uf = (d.get("uf") or "").strip()
    cep = (d.get("cep") or "").strip()
    munic = municipio
    if uf:
        munic = f"{munic} / {uf}" if munic else uf
    if cep:
        munic = f"{munic} · CEP {cep}" if munic else f"CEP {cep}"

    secoes = [
        {"titulo": "Dados Cadastrais", "linhas": [
            ("Natureza Jurídica", d.get("natureza_juridica")),
            ("Porte da Empresa", d.get("porte")),
            ("Capital Social", _moeda(d.get("capital_social"))),
            ("Data de Abertura", d.get("data_abertura")),
        ]},
        {"titulo": "Atividade Econômica", "linhas": [
            ("Atividade Principal (CNAE)", d.get("atividade_principal")),
            ("Situação Cadastral", d.get("situacao")),
        ]},
        {"titulo": "Contato e Localização", "linhas": [
            ("Telefone", d.get("telefone")),
            ("E-mail", d.get("email")),
            ("Bairro", d.get("bairro")),
            ("Logradouro", end_log or None),
            ("Município", munic or None),
        ]},
    ]
    return gerar_pdf_consulta(
        tipo="CNPJ",
        documento=d.get("cnpj") or "",
        status=d.get("situacao") or "Ativa",
        nome=d.get("razao_social") or "—",
        nome2=d.get("nome_fantasia") or "",
        secoes=secoes,
        fonte=_fonte_label(d.get("fonte")),
        data_emissao=datetime.now().strftime("%d/%m/%Y às %H:%M"),
        credenciais=_credenciais(perfil),
    )


def gerar_pdf_cpf(dados: dict, perfil: dict | None = None) -> bytes:
    d = dados or {}
    valido = bool(d.get("valido"))
    secoes = [
        {"titulo": "Resultado da Validação", "linhas": [
            ("CPF", d.get("cpf")),
            ("Situação", d.get("mensagem")),
            ("Data de Nascimento", _data_br(d.get("data_nascimento_informada"))),
            ("Tipo de Consulta", "Validação local (dígitos verificadores)"),
        ]},
        {"titulo": "Informações Complementares", "linhas": [
            ("Método de Validação", "Cálculo dos dígitos verificadores (módulo 11)"),
            ("Observação", d.get("observacao")),
        ]},
    ]
    return gerar_pdf_consulta(
        tipo="CPF",
        documento=d.get("cpf") or "",
        status="Válido" if valido else "Inválido",
        nome="Validação de CPF",
        nome2="Cadastro de Pessoas Físicas — verificação dos dígitos verificadores",
        secoes=secoes,
        fonte="Validação matemática local (não consulta base nominal)",
        data_emissao=datetime.now().strftime("%d/%m/%Y às %H:%M"),
        credenciais=_credenciais(perfil),
    )
