# @module services.recibo_zayra — Recibo no padrao ZAYRA/Romatec (REC-IMOB).
# Mesma assinatura de services.recibo_inline: gerar_recibo_pdf(*, ptam, user, perfil, valor,
# forma_pagamento, data_pagamento). Layout: cabecalho com CNPJ/IE, EMITENTE/PAGADOR, valor por
# extenso, REFERENTE A, PAGAMENTO (forma/data/validade/banco/PIX), assinatura e hash + QR de validacao.
import io
import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("romatec")

VERDE = "#1B5E20"
DOURADO = "#B8860B"
CINZA = "#555555"
CINZA_CLR = "#9CA3AF"
PRETO = "#1A1A1A"

# Dados do emitente (padrao Romatec). Sobrescreve com perfil quando houver.
EMIT_DEFAULT = {
    "nome": "Romatec Consultoria Imobiliária",
    "cnpj": "17.261.987/0001-09",
    "ie": "127.450.840",
    "razao": "J R P BEZERRA LTDA",
    "endereco": "Rua São Raimundo, 10 — Centro — Açailândia/MA — CEP 65930-000",
    "tel": "(99) 99181-1246",
    "email": "romateccrm@gmail.com",
    "cidade_uf": "Açailândia/MA",
    "banco": "Banco Santander (033) · Ag. 1225 · CC 13000714-4",
    "banco_titular": "J R P BEZERRA LTDA",
    "pix": "romatec.cad@hotmail.com",
}
# Conta proprietária (Romatec/CEO). SÓ ela usa EMIT_DEFAULT como fallback —
# nunca vaza esses dados para outros usuários.
OWNER_EMAIL = "romateccrm@gmail.com"
VALIDA_URL = "https://app.romatecavalieimob.com.br/v/"
MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _brl(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 0.0
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _extenso(v) -> str:
    try:
        from num2words import num2words
        v = float(v)
        reais = int(v)
        cent = int(round((v - reais) * 100))
        s = num2words(reais, lang="pt_BR") + (" real" if reais == 1 else " reais")
        if cent:
            s += f" e {num2words(cent, lang='pt_BR')} " + ("centavo" if cent == 1 else "centavos")
        return s
    except Exception:
        return ""


def _data_obj(d) -> datetime:
    try:
        return datetime.fromisoformat(str(d)[:10])
    except Exception:
        return datetime.utcnow()


def _data_br(d) -> str:
    return _data_obj(d).strftime("%d/%m/%Y")


def _doc(s) -> str:
    return str(s or "").strip()


def _gen_numero(ptam) -> str:
    num = str(ptam.get("numero_ptam") or ptam.get("number") or "0000")
    ano = ""
    for k in ("conclusion_date", "vistoria_date"):
        v = ptam.get(k)
        if v and str(v)[:4].isdigit():
            ano = str(v)[:4]
            break
    if not ano:
        ano = str(datetime.utcnow().year)
    base = num.split("/")[0].zfill(4)
    return f"REC-PTAM-{ano}-{base}"


def _qr_image(url: str):
    try:
        import qrcode
        qr = qrcode.QRCode(border=1, box_size=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        return bio
    except Exception:
        logger.warning("recibo_zayra: falha ao gerar QR")
        return None


def gerar_recibo_pdf(*, ptam: dict, user: dict, perfil: dict, valor: float,
                     forma_pagamento: str = "PIX", data_pagamento: Optional[str] = None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from textwrap import wrap

    ptam = ptam or {}
    user = user or {}
    perfil = perfil or {}
    valor = float(valor or 0)

    # Emitente vem 100% do PERFIL/USER do avaliador logado (isolado por usuário).
    from utils.avaliador import resolver_dados_avaliador
    dav = resolver_dados_avaliador(perfil=perfil, user=user)
    emit = {
        "nome": (perfil.get("empresa_nome") or perfil.get("empresa")
                 or dav.get("nome") or user.get("name") or ""),
        "cnpj": (perfil.get("empresa_cnpj") or perfil.get("cnpj_empresa")
                 or dav.get("cpf") or ""),
        "ie": (perfil.get("inscricao_estadual") or ""),
        "razao": (perfil.get("empresa_razao_social") or perfil.get("razao_social")
                  or perfil.get("empresa_nome") or ""),
        "endereco": (dav.get("endereco") or perfil.get("endereco_escritorio") or ""),
        "tel": (perfil.get("telefone") or user.get("phone") or ""),
        "email": (perfil.get("email_profissional") or user.get("email") or ""),
        "cidade_uf": ", ".join([p for p in [perfil.get("cidade"), perfil.get("uf")] if p]),
        "banco": (perfil.get("dados_bancarios") or perfil.get("banco") or ""),
        "banco_titular": (perfil.get("banco_titular") or ""),
        "pix": (perfil.get("chave_pix") or perfil.get("pix") or ""),
    }
    # Fallback Romatec SOMENTE para a conta proprietária (nunca para outros).
    if str(user.get("email") or "").lower() == OWNER_EMAIL:
        for _k, _v in EMIT_DEFAULT.items():
            if not emit.get(_k):
                emit[_k] = _v

    pagador_nome = ptam.get("solicitante_nome") or ptam.get("solicitante") or "—"
    pagador_doc = _doc(ptam.get("solicitante_cpf_cnpj"))
    pagador_tel = _doc(ptam.get("solicitante_telefone"))

    numero = _gen_numero(ptam)
    dt_emissao = _data_obj(data_pagamento)
    dt_validade = dt_emissao + timedelta(days=3)
    extenso = _extenso(valor)

    tipo_imovel = ptam.get("property_label") or ptam.get("property_type") or "imóvel"
    num_ptam = ptam.get("numero_ptam") or ptam.get("number") or ""
    referente = (
        f"Honorários técnicos profissionais referentes aos serviços de avaliação imobiliária — "
        f"Parecer Técnico de Avaliação Mercadológica (PTAM nº {num_ptam}) — do imóvel "
        f"\"{tipo_imovel}\", localizado em {ptam.get('property_address', '')}, "
        f"elaborado em conformidade com a ABNT NBR 14653 (partes 1 e 2) e a Resolução COFECI nº 957/2006. "
        f"Compreende vistoria técnica, pesquisa e tratamento estatístico de dados de mercado, "
        f"memória de cálculo, emissão do parecer e responsabilidade técnica do avaliador signatário."
    )

    # Hash de autenticidade
    semente = f"{numero}|{valor:.2f}|{pagador_doc}|{dt_emissao.date()}|{num_ptam}"
    hash_full = hashlib.sha256(semente.encode("utf-8")).hexdigest()
    hash_disp = hash_full[:40]
    valida_url = VALIDA_URL + hash_full

    W, H = A4
    M = 18 * mm
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    def setc(hexcolor):
        c.setFillColor(colors.HexColor(hexcolor))

    # ── Cabecalho ──────────────────────────────────────────────────────────
    y = H - 16 * mm
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'assets', 'avalieimob_logo.png')
    logo_bytes = user.get("_company_logo_bytes")
    try:
        if logo_bytes:
            c.drawImage(ImageReader(io.BytesIO(logo_bytes)), M, y - 13 * mm,
                        width=20 * mm, height=17 * mm, preserveAspectRatio=True, mask='auto')
        elif os.path.exists(logo_path):
            c.drawImage(logo_path, M, y - 13 * mm, width=20 * mm, height=17 * mm,
                        preserveAspectRatio=True, mask='auto')
    except Exception:
        pass
    tx = M + 24 * mm
    setc(VERDE)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(tx, y - 1 * mm, emit["nome"])
    setc(CINZA)
    c.setFont("Helvetica", 8)
    c.drawString(tx, y - 6 * mm, f"CNPJ {emit['cnpj']} · IE: {emit['ie']} · {emit['razao']}")
    c.drawString(tx, y - 10 * mm, emit["endereco"])
    c.drawString(tx, y - 14 * mm, f"{emit['tel']} · {emit['email']}")
    c.setStrokeColor(colors.HexColor(DOURADO))
    c.setLineWidth(2)
    c.line(M, y - 18 * mm, W - M, y - 18 * mm)
    y -= 28 * mm

    # ── RECIBO + numero (esq) + valor (dir) ────────────────────────────────
    setc(VERDE)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(M, y, "RECIBO")
    setc(CINZA)
    c.setFont("Helvetica", 9)
    c.drawString(M, y - 6 * mm, f"Nº {numero}")
    setc(VERDE)
    c.setFont("Helvetica-Bold", 24)
    c.drawRightString(W - M, y, _brl(valor))
    y -= 16 * mm

    def label(txt):
        nonlocal y
        setc(DOURADO)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(M, y, txt)
        y -= 5 * mm

    def linha(txt, font="Helvetica", size=9, cor=PRETO, dy=4.6):
        nonlocal y
        setc(cor)
        c.setFont(font, size)
        c.drawString(M, y, txt)
        y -= dy * mm

    def paragrafo(txt, width=104, size=9, font="Helvetica", cor=PRETO, dy=4.4):
        nonlocal y
        setc(cor)
        c.setFont(font, size)
        for ln in wrap(txt, width=width):
            c.drawString(M, y, ln)
            y -= dy * mm

    # ── EMITENTE ───────────────────────────────────────────────────────────
    label("EMITENTE — RECEBI(EMOS) DE")
    linha(emit["nome"], "Helvetica-Bold", 10)
    linha(f"CNPJ: {emit['cnpj']} · IE: {emit['ie']} · {emit['razao']}", "Helvetica", 8, CINZA)
    linha(emit["endereco"], "Helvetica", 8, CINZA, dy=6)

    # ── PAGADOR ────────────────────────────────────────────────────────────
    label("PAGADOR — A IMPORTÂNCIA DE")
    linha(str(pagador_nome).upper(), "Helvetica-Bold", 10)
    if pagador_doc:
        linha(f"CPF/CNPJ: {pagador_doc}", "Helvetica", 8, CINZA)
    if pagador_tel:
        linha(f"Telefone/WhatsApp: {pagador_tel}", "Helvetica", 8, CINZA)
    y -= 2 * mm
    paragrafo(
        f"A importância de {_brl(valor)}"
        + (f" ({extenso})" if extenso else "")
        + ", referente ao serviço abaixo descrito, dando plena, geral e irrevogável quitação.",
        size=9.5, font="Helvetica-Oblique", cor=CINZA)
    y -= 3 * mm

    # ── REFERENTE A ────────────────────────────────────────────────────────
    label("REFERENTE A")
    paragrafo(referente, width=104, size=9)
    y -= 4 * mm

    # ── PAGAMENTO ──────────────────────────────────────────────────────────
    label("PAGAMENTO")
    linha(f"Forma: {forma_pagamento or 'PIX'}", "Helvetica", 9)
    linha(f"Data de emissão: {dt_emissao.strftime('%d/%m/%Y')}", "Helvetica", 9)
    linha(f"Válido até: {dt_validade.strftime('%d/%m/%Y')}", "Helvetica", 9, dy=6)
    # Bloco bancário só aparece se o avaliador tiver dados (evita label vazio).
    if emit.get("banco") or emit.get("pix"):
        setc(VERDE)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(M, y, "Dados bancários para depósito/PIX:")
        y -= 4.4 * mm
        if emit.get("banco"):
            linha(f"{emit['banco']}", "Helvetica", 8, CINZA)
        if emit.get("banco_titular"):
            linha(f"Titular: {emit['banco_titular']}", "Helvetica", 8, CINZA)
        if emit.get("pix"):
            setc(VERDE)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(M, y, f"PIX: {emit['pix']}")
            y -= 4.4 * mm
        y -= 6 * mm

    # ── Cidade/Data + Assinatura ───────────────────────────────────────────
    cidade = emit["cidade_uf"]
    data_ext = f"{cidade}, {dt_emissao.day} de {MESES[dt_emissao.month]} de {dt_emissao.year}."
    setc(PRETO)
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, y, data_ext)
    y -= 16 * mm
    c.setStrokeColor(colors.HexColor(CINZA_CLR))
    c.setLineWidth(0.7)
    c.line(W / 2 - 42 * mm, y, W / 2 + 42 * mm, y)
    y -= 5 * mm
    setc(PRETO)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(W / 2, y, emit["nome"])
    y -= 4 * mm
    setc(CINZA)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, y, f"CNPJ {emit['cnpj']}")

    # ── Rodape: Hash + QR ──────────────────────────────────────────────────
    setc(CINZA_CLR)
    c.setFont("Helvetica", 7)
    c.drawString(M, 24 * mm, "Hash de autenticidade:")
    c.setFont("Helvetica", 7)
    c.drawString(M, 20 * mm, hash_disp)
    c.setFont("Helvetica", 6)
    c.drawString(M, 15 * mm, valida_url[:96])
    qr = _qr_image(valida_url)
    if qr is not None:
        try:
            from reportlab.lib.utils import ImageReader as _IR
            c.drawImage(_IR(qr), W - M - 22 * mm, 8 * mm, width=22 * mm, height=22 * mm, mask='auto')
            setc(CINZA)
            c.setFont("Helvetica", 6.5)
            c.drawCentredString(W - M - 11 * mm, 6 * mm, "Escaneie para validar")
        except Exception:
            pass

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
