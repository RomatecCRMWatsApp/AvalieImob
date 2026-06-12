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

try:
    from utils.extenso import valor_por_extenso
except Exception:  # pragma: no cover
    def valor_por_extenso(v):
        return ""

try:
    from services.foto_overlay import aplicar_tarja_romatec
except Exception:  # pragma: no cover
    def aplicar_tarja_romatec(b, **kw):
        return b

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

def _pct_extenso(p) -> str:
    try:
        from utils.extenso import _inteiro_extenso
        return _inteiro_extenso(int(round(float(p))))
    except Exception:
        return ""


def _clausula_rescisao(contrato: dict, comissao_pct, imovel: dict) -> Tuple[str, List[str]]:
    """Cláusula 8ª montada dinamicamente: caput + (multa) + (reembolso) + comissão integral."""
    multa = contrato.get("multa_rescisoria")
    reembolso = bool(contrato.get("reembolso_despesas"))
    valor_anunciado = float(imovel.get("valor_anunciado") or 0)
    comissao_estimada = round(valor_anunciado * float(comissao_pct or 0) / 100.0, 2)

    paras = [
        "O presente contrato poderá ser rescindido por mútuo acordo entre as partes, "
        "mediante termo escrito, ou por inadimplemento de quaisquer das obrigações aqui "
        "pactuadas."
    ]
    extras: List[str] = []

    if multa:
        modo = multa.get("modo")
        if modo == "percentual_comissao":
            pct = multa.get("percentual") or 0
            valor_multa = round(comissao_estimada * float(pct) / 100.0, 2)
            extras.append(
                "Em caso de rescisão imotivada por iniciativa do(s) CONTRATANTE(S) antes "
                "do término do prazo de exclusividade previsto na Cláusula Terceira, será "
                f"devida à CONTRATADA multa compensatória equivalente a {str(pct).replace('.', ',')}% "
                f"({_pct_extenso(pct)} por cento) da comissão estimada, calculada sobre o valor "
                f"anunciado do imóvel, correspondente nesta data a {_brl(valor_multa)} "
                f"({valor_por_extenso(valor_multa)})."
            )
        else:  # valor_fixo
            vfixo = round(float(multa.get("valor_fixo") or 0), 2)
            extras.append(
                "Em caso de rescisão imotivada por iniciativa do(s) CONTRATANTE(S) antes "
                "do término do prazo de exclusividade previsto na Cláusula Terceira, será "
                f"devida à CONTRATADA multa compensatória no valor de {_brl(vfixo)} "
                f"({valor_por_extenso(vfixo)})."
            )

    if reembolso:
        prefixo = ("Independentemente da multa prevista no parágrafo anterior, o(s) "
                   if multa else "O(s) ")
        extras.append(
            prefixo +
            "CONTRATANTE(S) reembolsará(ão) à CONTRATADA as despesas de divulgação "
            "comprovadamente realizadas durante a vigência deste contrato, tais como "
            "anúncios em portais imobiliários, impulsionamento em redes sociais, confecção "
            "de placas e material fotográfico profissional, mediante apresentação dos "
            "respectivos comprovantes."
        )

    # Comissão integral — sempre presente (último parágrafo)
    extras.append(
        "A rescisão deste contrato não afasta o direito da CONTRATADA à comissão integral "
        "prevista na Cláusula Quarta, na hipótese de o negócio vir a se concretizar, durante "
        "a vigência da exclusividade, com pessoa por ela apresentada ou em decorrência de sua "
        "mediação, nos termos do art. 726 do Código Civil."
    )

    for i, texto in enumerate(extras, start=1):
        paras.append(f"§{i}º. {texto}")

    return ("CLÁUSULA OITAVA — DA RESCISÃO E PENALIDADES", paras)


_ROMANOS = ["(i)", "(ii)", "(iii)", "(iv)", "(v)", "(vi)", "(vii)", "(viii)", "(ix)", "(x)"]


def _fracao_extenso(f) -> str:
    try:
        f = float(f)
    except (TypeError, ValueError):
        return ""
    intp = int(f)
    dec = int(round((f - intp) * 100))
    if dec == 0:
        return _pct_extenso(intp)
    return f"{_pct_extenso(intp)} vírgula {_pct_extenso(dec)}"


def _qualificar_proprietario(p: dict) -> str:
    """Qualificação notarial de um condômino, com cônjuge inline e fração."""
    partes = [f"<b>{_esc(p.get('nome')) or '____________________'}</b>",
              _esc(p.get("nacionalidade") or "brasileiro(a)")]
    ec = p.get("estado_civil")
    if ec:
        estado = _ESTADO_CIVIL.get(ec, ec)
        conj = p.get("conjuge") or {}
        if conj.get("nome"):
            regime = _REGIME.get(p.get("regime_bens"), p.get("regime_bens") or "")
            estado += f", {('casado(a)' if ec == 'casado' else 'convivente')} sob o regime de {regime} com "
            estado += _qualificar_pessoa(conj)
        partes.append(estado)
    if p.get("profissao"):
        partes.append(_esc(p["profissao"]))
    doc = _so_digitos_pdf(p.get("cpf_cnpj"))
    rotulo = "CPF" if len(doc) == 11 else "CNPJ"
    partes.append(f"inscrito(a) no {rotulo} sob o nº {_fmt_cpf(doc) if len(doc) == 11 else _esc(p.get('cpf_cnpj'))}")
    frac = p.get("fracao_percentual")
    if frac is not None:
        partes.append(f"proprietário(a) de {str(frac).replace('.', ',')}% "
                      f"({_fracao_extenso(frac)} por cento) do imóvel objeto deste contrato")
    return ", ".join(partes) + ";"


def _so_digitos_pdf(v) -> str:
    return "".join(filter(str.isdigit, str(v or "")))


def _clausula_imovel(im: dict) -> List[str]:
    """Cláusula 2ª condicional — sem trechos vazios (montagem só com o que existe)."""
    frase = f"O imóvel objeto da exclusividade é o seguinte: {_esc(im.get('descricao_geral')) or '____________________'}"
    loc = []
    if im.get("endereco"):
        loc.append(f"situado na {_esc(im['endereco'])}")
    if im.get("bairro"):
        loc.append(f"bairro {_esc(im['bairro'])}")
    cidade_uf = "/".join(x for x in [_esc(im.get("cidade")), _esc(im.get("uf"))] if x)
    if cidade_uf:
        loc.append(cidade_uf)
    if im.get("cep"):
        loc.append(f"CEP {_esc(im['cep'])}")
    if loc:
        frase += ", " + ", ".join(loc)
    if im.get("matricula"):
        frase += f", registrado sob a matrícula nº {_esc(im['matricula'])}"
        if im.get("cartorio"):
            frase += f" no {_esc(im['cartorio'])}"
    if im.get("area_total_m2") is not None:
        frase += f", com área total de {str(im['area_total_m2']).replace('.', ',')} m²"
    if im.get("area_hectares") is not None:
        frase += f", equivalente a {('%.4f' % float(im['area_hectares'])).replace('.', ',')} hectares"
    if im.get("confrontacoes"):
        frase += f", com as seguintes confrontações: {_esc(im['confrontacoes'])}"
    if im.get("latitude") is not None and im.get("longitude") is not None:
        frase += f", georreferenciado nas coordenadas {im['latitude']}, {im['longitude']} (SIRGAS 2000)"
    frase += "."

    paras = [frase]

    def _num(v, sufixo=""):
        return f"{str(v).replace('.', ',')}{sufixo}"

    def _juntar(prefixo, pares):
        itens = [f"{lbl} {val}" for lbl, val in pares if val not in (None, "", 0)]
        return f"{prefixo} {'; '.join(itens)}." if itens else ""

    # Cadastro Imobiliário Municipal (BCI)
    cad = _juntar("Conforme o Cadastro Imobiliário Municipal (BCI):", [
        ("código do imóvel (CTI)", _esc(im.get("cti"))),
        ("inscrição cadastral", _esc(im.get("inscricao_cadastral"))),
        ("setor", _esc(im.get("setor"))),
        ("quadra", _esc(im.get("quadra"))),
        ("lote", _esc(im.get("lote"))),
        ("unidade", _esc(im.get("unidade"))),
        ("situação cadastral", _esc(im.get("situacao_cadastral"))),
        ("natureza", _esc(im.get("natureza"))),
        ("data de cadastro", _esc(im.get("data_cadastro"))),
        ("data de construção", _esc(im.get("data_construcao"))),
    ])
    if cad:
        paras.append(cad)

    # Proprietário/detentor conforme BCI
    if im.get("proprietario_bci_nome"):
        pb = f"Proprietário/detentor conforme o BCI: {_esc(im['proprietario_bci_nome'])}"
        if im.get("proprietario_bci_doc"):
            pb += f", CPF/CNPJ {_esc(im['proprietario_bci_doc'])}"
        paras.append(pb + ".")

    # Medidas (BCI)
    med = _juntar("Medidas cadastrais (BCI):", [
        ("testada principal", _num(im.get("testada_principal"), " m") if im.get("testada_principal") else ""),
        ("profundidade do lote", _num(im.get("profundidade_lote"), " m") if im.get("profundidade_lote") else ""),
        ("área do terreno", _num(im.get("area_terreno"), " m²") if im.get("area_terreno") else ""),
        ("área da edificação", _num(im.get("area_edificacao"), " m²") if im.get("area_edificacao") else ""),
        ("área total da edificação", _num(im.get("area_total_edificacao"), " m²") if im.get("area_total_edificacao") else ""),
    ])
    if med:
        paras.append(med)

    # IPTU / situação fiscal
    iptu = _juntar("Situação fiscal (IPTU):", [
        ("inscrição do contribuinte", _esc(im.get("iptu_inscricao_contribuinte"))),
        ("exercício de referência", _esc(im.get("iptu_exercicio"))),
        ("valor anual", _brl(im.get("iptu_valor_anual")) if im.get("iptu_valor_anual") else ""),
        ("situação", _esc(im.get("iptu_situacao"))),
        ("vencimento", _esc(im.get("iptu_vencimento"))),
        ("débito total", _brl(im.get("iptu_debito_total")) if im.get("iptu_debito_total") else ""),
        ("desconto concedido", _brl(im.get("iptu_desconto")) if im.get("iptu_desconto") else ""),
        ("valor a pagar", _brl(im.get("iptu_valor_cobrado")) if im.get("iptu_valor_cobrado") else ""),
    ])
    if iptu:
        paras.append(iptu)

    paras.append(
        f"Parágrafo único. O imóvel será anunciado pelo valor de {_brl(im.get('valor_anunciado'))} "
        f"({valor_por_extenso(im.get('valor_anunciado'))}), podendo ser ajustado por anuência "
        f"expressa de todos os CONTRATANTES.")
    return paras


def _secoes(contrato: dict) -> List[Tuple[str, List[str]]]:
    props = contrato.get("proprietarios") or []
    imovel = contrato.get("imovel", {})
    comissao = contrato.get("comissao_percentual", 0)
    prazo = contrato.get("prazo_meses", 6)

    secoes: List[Tuple[str, List[str]]] = []

    # DAS PARTES — todos os condôminos como CONTRATANTES (parágrafo notarial)
    if props:
        itens = []
        for idx, p in enumerate(props):
            marc = _ROMANOS[idx] if idx < len(_ROMANOS) else f"({idx + 1})"
            itens.append(f"{marc} {_qualificar_proprietario(p)}")
        contratantes = "CONTRATANTES: " + " ".join(itens)
    else:
        contratantes = "CONTRATANTES: ____________________;"
    partes_txt = [contratantes]
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

    # CLÁUSULA 2ª — DO IMÓVEL (ficha, condicional)
    secoes.append(("CLÁUSULA SEGUNDA — DO IMÓVEL", _clausula_imovel(imovel)))

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

    # CLÁUSULA 8ª — RESCISÃO E PENALIDADES (montagem dinâmica)
    secoes.append(_clausula_rescisao(contrato, comissao, imovel))

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

def _bloco_assinatura(s: dict, st: dict, final: bool, owner_nome: str = "") -> Table:
    if s.get("papel") == "conjuge":
        papel = f"Cônjuge anuente de {_esc(owner_nome)}" if owner_nome else "Cônjuge anuente"
    elif s.get("papel") == "proprietario":
        frac = s.get("fracao_percentual")
        papel = (f"Proprietário(a) — {str(frac).replace('.', ',')}%"
                 if frac is not None else "Proprietário(a)")
    else:
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
    props = contrato.get("proprietarios") or []
    for s in contrato.get("signatarios", []):
        owner_nome = ""
        if s.get("papel") == "conjuge":
            idx = s.get("indice_proprietario")
            if isinstance(idx, int) and 0 <= idx < len(props):
                owner_nome = props[idx].get("nome", "")
        story.append(_bloco_assinatura(s, st, final, owner_nome))
        story.append(Spacer(1, 8))

    # Anexo I — Relatório fotográfico (só se houver fotos com bytes pré-carregados)
    story += _anexo_fotografico(contrato, st)

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


def _anexo_fotografico(contrato: dict, st: dict) -> List:
    """Anexo I — grade 2 colunas com tarja Romatec queimada + legenda. Defensivo."""
    im = contrato.get("imovel", {})
    fotos = [f for f in (im.get("fotos") or []) if f.get("_image_bytes")]
    if not fotos:
        return []
    from reportlab.platypus import PageBreak
    endereco = ", ".join(x for x in [im.get("endereco"), im.get("bairro"),
                                     im.get("cidade"), im.get("uf")] if x)
    colaborador = contrato.get("colaborador_relatorio") or "Romatec"
    elems: List = [PageBreak(),
                   Paragraph("ANEXO I — RELATÓRIO FOTOGRÁFICO DO IMÓVEL", st["clausula"])]
    cell_w = 7.6 * cm
    linha = []
    for idx, f in enumerate(fotos, start=1):
        cel = []
        try:
            tratada = aplicar_tarja_romatec(
                f["_image_bytes"], lat=f.get("gps_lat"), lon=f.get("gps_lng"),
                endereco=endereco, data_hora=f.get("data_hora", ""), colaborador=colaborador)
            img = Image(io.BytesIO(tratada))
            ratio = min(cell_w / img.imageWidth, (5.4 * cm) / img.imageHeight)
            img.drawWidth = img.imageWidth * ratio
            img.drawHeight = img.imageHeight * ratio
            cel.append(img)
        except Exception:
            cel.append(Paragraph("[imagem indisponível]", st["legenda"]))
        cel.append(Paragraph(f"<b>{idx}.</b> {_esc(f.get('legenda') or f'Foto {idx}')}", st["legenda"]))
        linha.append(cel)
        if len(linha) == 2:
            elems.append(_linha_fotos(linha, cell_w))
            linha = []
    if linha:
        linha.append([Spacer(1, 1)])
        elems.append(_linha_fotos(linha, cell_w))
    return elems


def _linha_fotos(linha, cell_w):
    t = Table([linha], colWidths=[cell_w + 0.4 * cm, cell_w + 0.4 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def gerar_pdf_rascunho(contrato: dict) -> bytes:
    return _gerar(contrato, final=False)


def gerar_pdf_final(contrato: dict) -> bytes:
    return _gerar(contrato, final=True)
