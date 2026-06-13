# @module pdf.templates.contrato_base — CONTEÚDO neutro do contrato (sem tema).
# Monta cláusulas/itens uma única vez; os 3 renderers (Prime I/II/Tradicional)
# só decidem COMO desenhar. Texto jurídico vive AQUI, nunca em JSX ou nos renderers.
# Negritos preservados via marcação ReportLab <b>...</b> (válida nos 3 templates).
from dataclasses import dataclass, field
from typing import List


@dataclass
class Clausula:
    titulo: str                       # "CLÁUSULA TERCEIRA — DA EXCLUSIVIDADE..."
    itens: List[str] = field(default_factory=list)  # já numerados "3.1. ..."


# ── Defaults confirmados (spec §3.3) ──────────────────────────────────────────
DEFAULTS = {
    "prazo_meses": 6,
    "periodo_minimo_dias": 90,
    "aviso_previo_dias": 30,
    "cauda_meses": 12,
    "multa_violacao_percentual": 100,
    "comissao_percentual": 6,
    "comissao_base": "valor_efetivo_venda",
}

_ORDINAIS = [
    "", "PRIMEIRA", "SEGUNDA", "TERCEIRA", "QUARTA", "QUINTA", "SEXTA",
    "SÉTIMA", "OITAVA", "NONA", "DÉCIMA", "DÉCIMA PRIMEIRA", "DÉCIMA SEGUNDA",
    "DÉCIMA TERCEIRA", "DÉCIMA QUARTA", "DÉCIMA QUINTA", "DÉCIMA SEXTA",
    "DÉCIMA SÉTIMA", "DÉCIMA OITAVA", "DÉCIMA NONA", "VIGÉSIMA",
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _ext_int(n) -> str:
    try:
        from num2words import num2words
        return num2words(int(n), lang="pt_BR")
    except Exception:
        return str(n)


def _ext_money(v) -> str:
    try:
        from routes.contratos import _extenso
        return _extenso(v)
    except Exception:
        return ""


def _money(v) -> str:
    try:
        return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def _parte(doc: dict) -> dict:
    vend = doc.get("vendedores") or []
    return (vend[0] if vend else {}) or {}


def _pf(p: dict) -> dict:
    return (p.get("pf") or p) if isinstance(p, dict) else {}


def _g(p: dict, *keys, default=""):
    pf = _pf(p)
    for k in keys:
        for src in (p, pf):
            v = src.get(k) if isinstance(src, dict) else None
            if v not in (None, "", [], {}):
                return v
    return default


def _bool_label(v, sim="autorizado", nao="não autorizado") -> str:
    return sim if v in (True, "true", "sim", 1, "1") else nao


def _endereco_completo(p: dict) -> str:
    partes = [
        _g(p, "endereco"), _g(p, "numero") and f"nº {_g(p, 'numero')}",
        _g(p, "bairro"), _g(p, "cidade", "city"),
        _g(p, "uf") and f"{_g(p, 'uf')}", _g(p, "cep") and f"CEP {_g(p, 'cep')}",
    ]
    return ", ".join([x for x in partes if x]) or "endereço não informado"


def _plain(s) -> str:
    """Remove HTML do editor rich text -> texto inline (tags de bloco viram espaço)."""
    import re as _re
    if not s:
        return ""
    t = str(s)
    t = _re.sub(r"(?i)<br\s*/?>", " ", t)
    t = _re.sub(r"(?i)</(div|p|li|ul|ol|tr)>", " ", t)
    t = _re.sub(r"<[^>]+>", "", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    t = _re.sub(r"\s{2,}", " ", t).strip()
    # Reescapa p/ o Paragraph do ReportLab (texto puro, sem markup intencional).
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _xml_escape(s) -> str:
    """Escapa &, <, > de valores de dados interpolados em cláusulas (ReportLab-safe)."""
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def testemunhas_de(doc: dict) -> list:
    """Normaliza as testemunhas do contrato: prioriza doc['testemunhas'] (array do
    Wizard, Step Testemunhas); fallback p/ testemunha_1/testemunha_2 (legado).
    Retorna só as que têm nome preenchido."""
    if not isinstance(doc, dict):
        return []
    arr = doc.get("testemunhas")
    if isinstance(arr, list) and arr:
        out = [t for t in arr if isinstance(t, dict) and (t.get("nome") or "").strip()]
        if out:
            return out
    legado = [doc.get("testemunha_1"), doc.get("testemunha_2")]
    return [t for t in legado if isinstance(t, dict) and (t.get("nome") or "").strip()]


def codigo_contrato(doc: dict) -> str:
    """Código exibido no PDF, derivado de numero_contrato (ex.: 'CV-2026-0023').
    Prefixo conforme o tipo: exclusividade → 'CONT_EXCLUSIV-'; demais → 'CONT-'.
    Idempotente: normaliza qualquer prefixo conhecido (CV-/CONT-/CONT_EXCLUSIV-)."""
    numero = str(doc.get("numero_contrato") or doc.get("numero") or "").strip() if isinstance(doc, dict) else ""
    is_excl = "exclusiv" in str((doc or {}).get("tipo_contrato") or "").lower()
    pref = "CONT_EXCLUSIV-" if is_excl else "CONT-"
    if not numero:
        return f"{pref}2026"
    base = numero
    for p in ("CONT_EXCLUSIV-", "CONT-", "CV-"):
        if base.startswith(p):
            base = base[len(p):]
            break
    return pref + base


def testemunha_linha(t: dict) -> str:
    """Qualificação inline de UMA testemunha (nome + CPF/RG/documento/CNH/profissão/
    contato/e-mail), só com os campos preenchidos (sem trechos vazios). XML-safe."""
    if not isinstance(t, dict):
        return ""
    nome = _xml_escape((t.get("nome") or "").strip())
    campos = [
        (f"CPF {t['cpf']}" if (t.get("cpf") or "").strip() else None),
        (f"RG {t['rg']}" if (t.get("rg") or "").strip() else None),
        (str(t["documento"]).strip() if (t.get("documento") or "").strip() else None),
        (f"CNH {t['cnh']}" if (t.get("cnh") or "").strip() else None),
        (str(t["profissao"]).strip() if (t.get("profissao") or "").strip() else None),
        (f"contato {t['contato']}" if (t.get("contato") or "").strip() else None),
        (str(t["email"]).strip() if (t.get("email") or "").strip() else None),
    ]
    suf = ", ".join(_xml_escape(c) for c in campos if c)
    return f"{nome} — {suf}" if suf else nome


def _ficha_imovel_txt(objeto: dict) -> str:
    """Compila os campos da ficha (BCI/medidas/IPTU) em frases condicionais p/ a cláusula do imóvel."""
    def _num(v, suf=""):
        return f"{str(v).replace('.', ',')}{suf}" if v not in (None, "", 0, "0") else ""

    def _juntar(prefixo, pares):
        itens = [f"{lbl} {val}" for lbl, val in pares if val not in (None, "", 0, "0")]
        return f"{prefixo} {'; '.join(itens)}." if itens else ""

    partes = []
    bci = _juntar("Conforme o Cadastro Imobiliário Municipal (BCI):", [
        ("código do imóvel (CTI)", objeto.get("cti")),
        ("inscrição cadastral", objeto.get("inscricao_cadastral")),
        ("setor", objeto.get("setor")),
        ("quadra", objeto.get("quadra")),
        ("lote", objeto.get("lote")),
        ("unidade", objeto.get("unidade")),
        ("situação cadastral", objeto.get("situacao_cadastral")),
        ("natureza", objeto.get("natureza")),
        ("data de cadastro", objeto.get("data_cadastro")),
        ("data de construção", objeto.get("data_construcao")),
    ])
    if bci:
        partes.append(bci)
    if objeto.get("proprietario_bci_nome"):
        pb = f"Proprietário/detentor conforme o BCI: {objeto['proprietario_bci_nome']}"
        if objeto.get("proprietario_bci_doc"):
            pb += f", CPF/CNPJ {objeto['proprietario_bci_doc']}"
        partes.append(pb + ".")
    med = _juntar("Medidas cadastrais (BCI):", [
        ("testada principal", _num(objeto.get("testada_principal"), " m")),
        ("profundidade do lote", _num(objeto.get("profundidade_lote"), " m")),
        ("área do terreno", _num(objeto.get("area_terreno"), " m²")),
        ("área da edificação", _num(objeto.get("area_edificacao"), " m²")),
        ("área total da edificação", _num(objeto.get("area_total_edificacao"), " m²")),
    ])
    if med:
        partes.append(med)
    iptu = _juntar("Situação fiscal (IPTU):", [
        ("inscrição do contribuinte", objeto.get("iptu_inscricao_contribuinte")),
        ("exercício de referência", objeto.get("iptu_exercicio")),
        ("valor anual R$", _num(objeto.get("iptu_valor_anual"))),
        ("situação", objeto.get("iptu_situacao")),
        ("vencimento", objeto.get("iptu_vencimento")),
        ("débito total R$", _num(objeto.get("iptu_debito_total"))),
        ("desconto concedido R$", _num(objeto.get("iptu_desconto"))),
        ("valor a pagar R$", _num(objeto.get("iptu_valor_cobrado"))),
    ])
    if iptu:
        partes.append(iptu)

    al = objeto.get("alienacao") or {}
    if al.get("alienado"):
        cred = (al.get("credor") or {}).get("nome") or "credor fiduciário"
        reg_al = (al.get("registro") or {}).get("registro_alienacao") or ""
        g = f"Gravame: Alienação Fiduciária — {cred}"
        if reg_al:
            g += f" ({reg_al})"
        partes.append(g + ".")

    return " " + _xml_escape(" ".join(partes)) if partes else ""


def _ctx(doc: dict) -> dict:
    p = _parte(doc)
    objeto = doc.get("objeto") or {}
    pagamento = doc.get("pagamento") or {}
    corretor = doc.get("corretor") or {}
    excl = doc.get("exclusividade") or {}

    def pick(*vals, default=""):
        for v in vals:
            if v not in (None, "", [], {}):
                return v
        return default

    preco = pick(pagamento.get("valor_total"), doc.get("preco_anunciado"), 0)
    preco_min = pick(doc.get("preco_minimo_autorizado"), excl.get("preco_minimo_autorizado"), preco)
    comissao_pct = pick(corretor.get("comissao_percentual"), doc.get("comissao_percentual"),
                        DEFAULTS["comissao_percentual"])
    comissao_base = pick(doc.get("comissao_base"), excl.get("comissao_base"), DEFAULTS["comissao_base"])
    comissao_base_txt = "o valor efetivo da venda" if comissao_base == "valor_efetivo_venda" else "o preço anunciado"

    regime_raw = str(pick(doc.get("regime_prazo"), excl.get("regime_prazo"),
                          corretor.get("regime_prazo"), "determinado")).lower()
    regime = "indeterminado" if "indetermin" in regime_raw else "determinado"

    conjuge_nome = _g(p, "conjuge_nome") or (p.get("conjuge") or {}).get("nome", "")
    conjuge_cpf = _g(p, "conjuge_cpf") or (p.get("conjuge") or {}).get("cpf", "")
    _cj = p.get("conjuge") or {}
    conjuge_rg = _g(p, "conjuge_rg") or _cj.get("rg", "")
    conjuge_rg_orgao = _g(p, "conjuge_rg_orgao") or _cj.get("orgao_emissor", "")
    conjuge_cnh = _g(p, "conjuge_cnh") or _cj.get("cnh", "")
    conjuge_cnh_categoria = _g(p, "conjuge_cnh_categoria") or _cj.get("cnh_categoria", "")
    conjuge_cnh_orgao = _g(p, "conjuge_cnh_orgao") or _cj.get("cnh_orgao", "")
    conjuge_filiacao_mae = _g(p, "conjuge_filiacao_mae") or _cj.get("filiacao_mae", "")
    conjuge_filiacao_pai = _g(p, "conjuge_filiacao_pai") or _cj.get("filiacao_pai", "")

    return {
        "nome": _g(p, "nome", "razao_social", default=""),
        "nacionalidade": _g(p, "nacionalidade", default="brasileiro(a)"),
        "estado_civil": _g(p, "estado_civil", default=""),
        "profissao": _g(p, "profissao", default=""),
        "rg": _g(p, "rg", default=""),
        "orgao_emissor": _g(p, "orgao_emissor", "rg_orgao", default=""),
        "cpf": _g(p, "cpf", "doc", default=""),
        "cnh": _g(p, "cnh", default=""),
        "cnh_categoria": _g(p, "cnh_categoria", default=""),
        "cnh_orgao": _g(p, "cnh_orgao", default=""),
        "cnh_validade": _g(p, "cnh_validade", default=""),
        "filiacao_mae": _g(p, "filiacao_mae", default=""),
        "filiacao_pai": _g(p, "filiacao_pai", default=""),
        "endereco_completo": _endereco_completo(p),
        "conjuge_nome": conjuge_nome,
        "conjuge_cpf": conjuge_cpf,
        "conjuge_rg": conjuge_rg,
        "conjuge_rg_orgao": conjuge_rg_orgao,
        "conjuge_cnh": conjuge_cnh,
        "conjuge_cnh_categoria": conjuge_cnh_categoria,
        "conjuge_cnh_orgao": conjuge_cnh_orgao,
        "conjuge_filiacao_mae": conjuge_filiacao_mae,
        "conjuge_filiacao_pai": conjuge_filiacao_pai,
        "regime_bens": _g(p, "regime_bens", default="comunhão parcial de bens"),
        "tem_conjuge": bool(conjuge_nome),
        "imovel_descricao": pick(objeto.get("descricao"), objeto.get("denominacao"), "imóvel objeto deste contrato"),
        "endereco": pick(objeto.get("endereco"), "endereço a especificar"),
        "area_total": pick(objeto.get("area_total_ha") and f"{objeto.get('area_total_ha')} ha",
                          objeto.get("area_terreno") and f"{objeto.get('area_terreno')} m²", "área a especificar"),
        "matricula": pick(objeto.get("matricula"), "a indicar"),
        "cartorio": pick(objeto.get("cartorio"), "cartório competente"),
        "onus_declarados": pick(_plain(objeto.get("onus")), doc.get("onus_declarados"),
                               "livre e desembaraçado de ônus, gravames e ações"),
        "ficha_complementar": _ficha_imovel_txt(objeto),
        "preco_anunciado": _money(preco),
        "preco_extenso": _ext_money(preco),
        "preco_minimo_autorizado": _money(preco_min),
        "financiamento": _bool_label(pick(pagamento.get("financiamento_autorizado"), doc.get("financiamento"), False)),
        "permuta": _bool_label(pick(doc.get("permuta_autorizada"), doc.get("permuta"), False), "autorizada", "não autorizada"),
        "condicoes_especiais": pick(doc.get("condicoes_especiais"), excl.get("condicoes_especiais"), ""),
        "comissao_percentual": comissao_pct,
        "percentual_extenso": _ext_int(comissao_pct),
        "comissao_base_txt": comissao_base_txt,
        "comissao_vencimento": pick(doc.get("comissao_vencimento"),
                                    "na data da assinatura do instrumento de venda"),
        "regime": regime,
        "prazo_meses": pick(doc.get("prazo_meses"), excl.get("prazo_meses"), DEFAULTS["prazo_meses"]),
        "renovacao_automatica": bool(pick(doc.get("renovacao_automatica"), excl.get("renovacao_automatica"), False)),
        "periodo_minimo_dias": pick(doc.get("periodo_minimo_dias"), DEFAULTS["periodo_minimo_dias"]),
        "aviso_previo_dias": pick(doc.get("aviso_previo_dias"), DEFAULTS["aviso_previo_dias"]),
        "cauda_meses": pick(doc.get("cauda_meses"), DEFAULTS["cauda_meses"]),
        "multa_violacao_percentual": pick(doc.get("multa_violacao_percentual"), DEFAULTS["multa_violacao_percentual"]),
        "foro_eleito": pick(doc.get("foro_eleito"), doc.get("foro"), "Açailândia/MA"),
        "cidade_assinatura": pick(doc.get("cidade_assinatura"), "Açailândia/MA"),
        "data_assinatura": pick(doc.get("data_assinatura"), "____ de __________ de ______"),
    }


def preambulo_exclusividade(doc: dict) -> List[str]:
    """Qualificação das partes (parágrafos do preâmbulo)."""
    c = _ctx(doc)
    # CNH (documento de habilitação) — opcional
    cnh_part = ""
    if c["cnh"]:
        cnh_part = f", portador(a) da CNH nº {c['cnh']}"
        if c["cnh_categoria"]:
            cnh_part += f" categoria {c['cnh_categoria']}"
        if c["cnh_orgao"]:
            cnh_part += f" ({c['cnh_orgao']})"
    # Filiação — opcional
    filiacao_part = ""
    if c["filiacao_mae"] and c["filiacao_pai"]:
        filiacao_part = f", filho(a) de {c['filiacao_pai']} e {c['filiacao_mae']}"
    elif c["filiacao_mae"]:
        filiacao_part = f", filho(a) de {c['filiacao_mae']}"
    elif c["filiacao_pai"]:
        filiacao_part = f", filho(a) de {c['filiacao_pai']}"
    contratante = (
        f"<b>CONTRATANTE (PROPRIETÁRIO):</b> {c['nome']}, {c['nacionalidade']}, "
        f"{c['estado_civil']}, {c['profissao']}, RG nº {c['rg']} ({c['orgao_emissor']}), "
        f"CPF nº {c['cpf']}{cnh_part}{filiacao_part}, residente e domiciliado(a) em {c['endereco_completo']}."
    )
    if c["tem_conjuge"]:
        cj = f" Cônjuge anuente: {c['conjuge_nome']}, CPF nº {c['conjuge_cpf']}"
        if c["conjuge_rg"]:
            cj += f", RG nº {c['conjuge_rg']}" + (f" ({c['conjuge_rg_orgao']})" if c["conjuge_rg_orgao"] else "")
        if c["conjuge_cnh"]:
            cj += f", CNH nº {c['conjuge_cnh']}"
            if c["conjuge_cnh_categoria"]:
                cj += f" categoria {c['conjuge_cnh_categoria']}"
            if c["conjuge_cnh_orgao"]:
                cj += f" ({c['conjuge_cnh_orgao']})"
        if c["conjuge_filiacao_mae"] and c["conjuge_filiacao_pai"]:
            cj += f", filho(a) de {c['conjuge_filiacao_pai']} e {c['conjuge_filiacao_mae']}"
        elif c["conjuge_filiacao_mae"]:
            cj += f", filho(a) de {c['conjuge_filiacao_mae']}"
        elif c["conjuge_filiacao_pai"]:
            cj += f", filho(a) de {c['conjuge_filiacao_pai']}"
        cj += f", casados sob o regime de {c['regime_bens']}."
        contratante += cj
    contratado = (
        "<b>CONTRATADO (CORRETOR):</b> ROMATEC CONSULTORIA TOTAL, pessoa jurídica de direito "
        "privado, CNPJ nº 17.261.987/0001-09, com sede na Rua São Raimundo, nº 10, Centro, "
        "Açailândia/MA, neste ato representada por JOSÉ ROMÁRIO PINTO BEZERRA, brasileiro, "
        "corretor de imóveis CRECI/MA nº 4.705, avaliador imobiliário CNAI nº 031.161."
    )
    regencia = (
        "O presente contrato rege-se pelos arts. 722 a 729 do Código Civil, pela Lei nº 6.530/78, "
        "pelo Decreto nº 81.871/78 e pelas Resoluções COFECI nº 458/95 e nº 1.256/2018, "
        "mediante as cláusulas seguintes:"
    )
    return [contratante, contratado, regencia]


_INSTRUMENTO_EXTENSO = {
    "INSTRUMENTO_PARTICULAR_EFEITO_ESCRITURA": "Instrumento Particular, com efeito de escritura pública",
    "ESCRITURA_PUBLICA": "Escritura Pública",
    "CEDULA_CREDITO_IMOBILIARIO": "Cédula de Crédito Imobiliário",
    "CONTRATO_GAVETA": "instrumento particular não registrado",
}
_PROGRAMA_EXTENSO = {
    "MCMV": "Programa Minha Casa, Minha Vida",
    "SFH": "Sistema Financeiro da Habitação",
    "SFI": "Sistema de Financiamento Imobiliário",
    "PRO_COTISTA": "Programa Pró-Cotista (FGTS)",
}


def _data_br(s) -> str:
    import re as _re
    if not s:
        return ""
    m = _re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s))
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else str(s)


def _rs_ext(v, *, zero_ok: bool = False) -> str:
    """'R$ 1.234,56 (mil duzentos...)' ou '' se vazio."""
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return ""
    if fv == 0 and not zero_ok:
        return ""
    ext = _ext_money(fv)
    return f"R$ {_money(fv)}" + (f" ({ext})" if ext else "")


def clausula_gravame_itens(objeto: dict) -> list:
    """Itens da cláusula DO GRAVAME (alienação fiduciária) — caput + parágrafos
    condicionais, sem trechos vazios. Retorna [] se o imóvel não for alienado."""
    al = (objeto or {}).get("alienacao") or {}
    if not al.get("alienado"):
        return []
    credor = al.get("credor") or {}
    instr = al.get("instrumento") or {}
    prog = al.get("programa") or {}
    reg = al.get("registro") or {}
    val = al.get("valores") or {}
    cond = al.get("condicoes") or {}
    saldo = al.get("saldo_devedor") or {}

    matricula = objeto.get("matricula") or "____"
    registro_imoveis = objeto.get("registro_imovel") or objeto.get("cartorio") or "Cartório de Registro de Imóveis competente"

    # ── Caput ────────────────────────────────────────────────────────────────
    caput = (
        "O CONTRATANTE declara, para todos os fins de direito, que o imóvel objeto do presente "
        f"contrato encontra-se gravado com ALIENAÇÃO FIDUCIÁRIA em favor de {credor.get('nome') or '____'}"
    )
    if credor.get("cnpj"):
        caput += f", inscrito no CNPJ sob nº {credor['cnpj']}"
    if credor.get("agencia"):
        caput += f", por sua {credor['agencia']}"
    tipo_ext = _INSTRUMENTO_EXTENSO.get(instr.get("tipo")) or instr.get("tipo_outro_descricao") or "instrumento contratual"
    caput += f", conforme {tipo_ext}"
    if instr.get("numero"):
        caput += f" nº {instr['numero']}"
    if instr.get("data"):
        caput += f", datado de {_data_br(instr['data'])}"
    prog_ext = _PROGRAMA_EXTENSO.get(prog.get("nome")) or (prog.get("nome_outro_descricao") if prog.get("nome") == "OUTRO" else "")
    if prog_ext:
        caput += f", celebrado no âmbito do {prog_ext}"
        if prog.get("lei_referencia"):
            caput += f", nos termos da {prog['lei_referencia']}"
    if reg.get("registro_alienacao"):
        caput += f", registrado sob {reg['registro_alienacao']}"
    caput += f" na matrícula nº {matricula} do {registro_imoveis}."

    itens = [caput]

    # ── §1º — valores da operação original ───────────────────────────────────
    if any(val.get(k) for k in ("valor_compra", "entrada_recursos_proprios", "subsidio", "valor_financiado")):
        partes = []
        if val.get("valor_compra"):
            partes.append(f"a operação original de compra e venda foi realizada pelo valor de {_rs_ext(val['valor_compra'])}")
        det = []
        if val.get("entrada_recursos_proprios"):
            det.append(f"{_rs_ext(val['entrada_recursos_proprios'])} pagos com recursos próprios")
        if val.get("subsidio"):
            origem = val.get("subsidio_origem") or "subsídio"
            det.append(f"{_rs_ext(val['subsidio'])} concedidos a título de {origem}")
        if val.get("valor_financiado"):
            det.append(f"{_rs_ext(val['valor_financiado'])} financiados pelo credor fiduciário")
        frase = (partes[0] if partes else "a operação original de compra e venda foi financiada")
        if det:
            frase += ", sendo " + "; ".join(det)
        if cond.get("prazo_meses"):
            frase += f", em {cond['prazo_meses']} ({_ext_int(cond['prazo_meses'])}) prestações mensais"
        if cond.get("parcela_inicial"):
            frase += f", com parcela inicial de {_rs_ext(cond['parcela_inicial'])}"
        if cond.get("amortizacao_inicio") and cond.get("amortizacao_fim"):
            frase += f", e período de amortização de {_data_br(cond['amortizacao_inicio'])} a {_data_br(cond['amortizacao_fim'])}"
        itens.append(frase + ".")

    # ── §2º — saldo devedor ──────────────────────────────────────────────────
    if saldo.get("valor") is not None and saldo.get("data_referencia"):
        itens.append(
            f"O saldo devedor do financiamento, conforme extrato emitido pelo credor fiduciário, é de "
            f"{_rs_ext(saldo['valor'], zero_ok=True)}, apurado em {_data_br(saldo['data_referencia'])}, "
            f"documento que integra o presente contrato como anexo."
        )

    # ── §3º e §4º — efeitos legais (fixos) ───────────────────────────────────
    itens.append(
        "As partes reconhecem que a propriedade resolúvel do imóvel pertence ao credor fiduciário, na "
        "forma dos arts. 22 a 33 da Lei nº 9.514/1997, detendo o CONTRATANTE a posse direta na qualidade "
        "de devedor fiduciante, razão pela qual a alienação do imóvel a terceiros fica condicionada à "
        "prévia quitação do financiamento, à interveniência ou à anuência expressa do credor fiduciário, "
        "conforme o caso."
    )
    itens.append(
        "O CONTRATADO (corretor) não responde, em nenhuma hipótese, por eventual recusa do credor "
        "fiduciário em anuir com a transferência, tampouco por divergências entre o saldo devedor "
        "declarado e o efetivamente apurado pelo credor na data da quitação, obrigando-se o CONTRATANTE a "
        "manter atualizadas as informações do financiamento durante a vigência deste contrato."
    )
    return [_xml_escape(x) for x in itens]


def clausulas_exclusividade(doc: dict) -> List[Clausula]:
    """As 12 cláusulas canônicas do Contrato de Intermediação com Exclusividade.
    Numeração N.i gerada automaticamente. Sem placeholders no resultado."""
    c = _ctx(doc)

    # Cada cláusula = (resto_do_título, [itens sem prefixo N.i])
    blocos = []

    blocos.append(("DO OBJETO", [
        f"O CONTRATANTE outorga ao CONTRATADO, com exclusividade, a intermediação da venda do "
        f"imóvel: {c['imovel_descricao']}, situado em {c['endereco']}, área total de {c['area_total']}, "
        f"matrícula nº {c['matricula']} do {c['cartorio']}.{c['ficha_complementar']}",
        f"O CONTRATANTE declara, sob as penas da lei, ser legítimo proprietário do imóvel e que este "
        f"se encontra {c['onus_declarados']}, responsabilizando-se civil e criminalmente pela "
        f"veracidade desta declaração.",
    ]))

    item_22 = (f"Financiamento bancário: {c['financiamento']}. Permuta: {c['permuta']}.")
    if c["condicoes_especiais"]:
        item_22 += f" Condições especiais: {c['condicoes_especiais']}."
    blocos.append(("DO PREÇO", [
        f"O imóvel será ofertado por R$ {c['preco_anunciado']} ({c['preco_extenso']}), autorizadas "
        f"propostas a partir de R$ {c['preco_minimo_autorizado']}. Propostas inferiores dependem de "
        f"anuência expressa do CONTRATANTE, admitida por meio eletrônico.",
        item_22,
    ]))

    blocos.append(("DA EXCLUSIVIDADE E DA COMISSÃO DEVIDA EM QUALQUER VENDA (art. 726 CC)", [
        "Durante a vigência deste contrato, o CONTRATADO é o único autorizado a anunciar, negociar "
        "e intermediar a venda do imóvel.",
        "A comissão será integralmente devida ao CONTRATADO em <b>TODA E QUALQUER alienação onerosa</b> "
        "do imóvel concretizada durante a vigência deste contrato — venda, promessa de venda, permuta "
        "ou dação em pagamento —, <b>QUALQUER QUE SEJA A ORIGEM DO COMPRADOR OU O MEIO PELO QUAL O "
        "NEGÓCIO SE REALIZOU</b>, inclusive: (a) venda direta pelo CONTRATANTE; (b) venda a parente, "
        "amigo ou conhecido; (c) venda intermediada por terceiro, outro corretor ou imobiliária; "
        "(d) negócio iniciado por anúncio ou contato alheio ao CONTRATADO — ressalvada unicamente a "
        "hipótese de comprovada inércia ou ociosidade do CONTRATADO, nos exatos termos do art. 726 do "
        "Código Civil.",
        "O CONTRATANTE encaminhará ao CONTRATADO todo interessado que o procurar diretamente, "
        "abstendo-se de negociar pessoalmente.",
    ]))

    blocos.append(("DA COMISSÃO", [
        f"A comissão é de {c['comissao_percentual']}% ({c['percentual_extenso']} por cento) sobre "
        f"{c['comissao_base_txt']}, vencível {c['comissao_vencimento']}.",
        "Arrependimento (art. 725 CC): obtido o acordo de vontades por efeito da mediação (proposta "
        "aceita, contrato preliminar, recibo de sinal ou instrumento definitivo), a comissão é devida "
        "ainda que o negócio não se efetive por arrependimento ou desistência de qualquer das partes.",
        "Na permuta, a comissão incide sobre o valor de avaliação do bem recebido; na dação parcial, "
        "sobre o valor total da operação.",
        "Comissão não paga no vencimento: multa de 2%, juros de 1% ao mês, correção pelo IPCA e "
        "honorários de 20% em cobrança judicial ou extrajudicial.",
    ]))

    # CLÁUSULA QUINTA — DO PRAZO (regime-dependente)
    if c["regime"] == "determinado":
        itens_prazo = [
            f"O presente contrato vigorará pelo prazo de {c['prazo_meses']} ({_ext_int(c['prazo_meses'])}) "
            f"meses, contados de sua assinatura, nos termos da Resolução COFECI nº 458/95.",
        ]
        if c["renovacao_automatica"]:
            itens_prazo.append(
                "Findo o prazo sem oposição escrita de qualquer das partes, manifestada com antecedência "
                "mínima de 30 (trinta) dias, o contrato prorrogar-se-á automaticamente por prazo "
                f"indeterminado, mantida a exclusividade, podendo então ser denunciado por qualquer das "
                f"partes mediante notificação escrita com antecedência mínima de {c['aviso_previo_dias']} "
                f"({_ext_int(c['aviso_previo_dias'])}) dias."
            )
    else:
        itens_prazo = [
            f"O presente contrato vigorará por prazo indeterminado, observado o período mínimo inicial de "
            f"{c['periodo_minimo_dias']} ({_ext_int(c['periodo_minimo_dias'])}) dias, durante o qual não "
            f"será admitida denúncia imotivada pelo CONTRATANTE.",
            f"Decorrido o período mínimo, qualquer das partes poderá denunciar o contrato mediante "
            f"notificação escrita — admitida a forma da Cláusula Décima Primeira — com antecedência "
            f"mínima de {c['aviso_previo_dias']} ({_ext_int(c['aviso_previo_dias'])}) dias, permanecendo "
            f"íntegras, durante o aviso prévio, todas as obrigações pactuadas, inclusive a exclusividade.",
        ]
    blocos.append(("DO PRAZO", itens_prazo))

    blocos.append(("DA VIGÊNCIA PÓS-CONTRATUAL (art. 727 CC)", [
        f"Extinto o contrato por qualquer causa, a comissão integral permanecerá devida se o imóvel for "
        f"vendido, prometido à venda ou objeto de proposta aceita, no prazo de {c['cauda_meses']} "
        f"({_ext_int(c['cauda_meses'])}) meses contados da extinção, a pessoa apresentada, atendida ou "
        f"captada pelo CONTRATADO durante a vigência — ou a cônjuge, companheiro, parente até o 3º grau, "
        f"sócio ou pessoa jurídica a ela vinculada.",
        "O CONTRATADO manterá relação nominal dos interessados apresentados (Anexo I), comunicada ao "
        "CONTRATANTE pelos meios da Cláusula Décima Primeira e presumida aceita se não impugnada em "
        "5 (cinco) dias úteis.",
    ]))

    blocos.append(("DAS OBRIGAÇÕES DO CONTRATADO", [
        "Exercer a mediação com diligência e prudência (art. 723 CC); divulgar o imóvel por placa, "
        "portais e redes sociais, às suas expensas ordinárias; acompanhar todas as visitas; prestar ao "
        "CONTRATANTE, ao menos mensalmente, informações sobre o andamento da comercialização e propostas "
        "recebidas; e auxiliar na documentação até a conclusão do negócio.",
    ]))

    blocos.append(("DAS OBRIGAÇÕES DO CONTRATANTE", [
        "Entregar em até 10 (dez) dias a documentação do imóvel e dos proprietários; permitir visitas "
        "agendadas, placa e captação de imagens; informar de imediato qualquer fato que altere a situação "
        "jurídica do imóvel; e não anunciar, negociar ou alienar o imóvel, direta ou indiretamente, "
        "durante a vigência.",
    ]))

    blocos.append(("DA PENALIDADE POR VIOLAÇÃO DA EXCLUSIVIDADE", [
        f"A violação das Cláusulas Terceira ou 8.1 (parte final) sujeita o CONTRATANTE ao pagamento: "
        f"(a) da comissão integral, calculada sobre o maior valor entre o preço anunciado e o da venda "
        f"realizada; e, cumulativamente, (b) de multa penal não compensatória equivalente a "
        f"{c['multa_violacao_percentual']}% ({_ext_int(c['multa_violacao_percentual'])} por cento) do "
        f"valor da comissão, sem prejuízo de perdas e danos suplementares (art. 416, parágrafo único, CC).",
    ]))

    # CLÁUSULA DÉCIMA — DA RESCISÃO (regime-dependente no item .1)
    if c["regime"] == "determinado":
        item_101 = (
            "A rescisão imotivada pelo CONTRATANTE antes do término do prazo contratual obriga-o ao "
            "pagamento da comissão integral calculada sobre o preço anunciado, a título de cláusula penal "
            "compensatória, além do reembolso das despesas de publicidade comprovadas."
        )
    else:
        item_101 = (
            "A rescisão imotivada pelo CONTRATANTE durante o período mínimo, ou a denúncia sem observância "
            "do aviso prévio, obriga-o ao pagamento da comissão integral calculada sobre o preço anunciado, "
            "a título de cláusula penal compensatória, além do reembolso das despesas de publicidade "
            "comprovadas."
        )
    blocos.append(("DA RESCISÃO", [
        item_101,
        "Não constitui rescisão imotivada a retirada do imóvel do mercado por caso fortuito ou força maior "
        "comprovados, hipótese em que serão devidas apenas as despesas de publicidade comprovadas. É "
        "facultada a qualquer das partes a resolução por justa causa, mediante comprovado descumprimento "
        "de obrigação essencial pela outra.",
    ]))

    blocos.append(("DAS COMUNICAÇÕES E DA LGPD", [
        "As partes reconhecem plena validade jurídica às comunicações por e-mail e WhatsApp dirigidas aos "
        "contatos indicados neste contrato, inclusive para notificações, denúncia e aprovação de propostas "
        "(art. 107 CC). Os dados pessoais serão tratados exclusivamente para a execução deste contrato "
        "(Lei nº 13.709/2018).",
    ]))

    # Cláusula DO GRAVAME (alienação fiduciária) — penúltima quando o imóvel é alienado.
    # Inserida aqui (e não após o objeto) para não desalinhar as referências cruzadas
    # internas das cláusulas anteriores (3ª, 8.1, 11ª), que são fixas no texto canônico.
    _gravame_itens = clausula_gravame_itens(doc.get("objeto") or {})
    if _gravame_itens:
        blocos.append(("DO GRAVAME (ALIENAÇÃO FIDUCIÁRIA)", _gravame_itens))

    blocos.append(("DAS DISPOSIÇÕES GERAIS E DO FORO", [
        "Este contrato obriga as partes, herdeiros e sucessores; não admite cessão sem anuência escrita; "
        "e a tolerância não importa novação ou renúncia. Integram-no o Anexo I (Relação de Interessados "
        "Apresentados) e o Anexo II (Autorização de Publicidade).",
        f"Fica eleito o foro da Comarca de {c['foro_eleito']}, com renúncia a qualquer outro.",
    ]))

    # Monta as Clausula com numeração automática N.i
    clausulas: List[Clausula] = []
    for i, (resto, itens) in enumerate(blocos, start=1):
        titulo = f"CLÁUSULA {_ORDINAIS[i]} — {resto}"
        itens_num = [f"{i}.{j}. {txt}" for j, txt in enumerate(itens, start=1)]
        clausulas.append(Clausula(titulo=titulo, itens=itens_num))
    return clausulas


def fecho_exclusividade(doc: dict) -> str:
    c = _ctx(doc)
    return (
        "E, por estarem justas e contratadas, as partes assinam em 2 (duas) vias de igual teor, na "
        f"presença das testemunhas abaixo. {c['cidade_assinatura']}, {c['data_assinatura']}."
    )


def montar_clausulas(doc: dict) -> List[Clausula]:
    """Dispatcher: exclusividade usa o texto canônico; demais tipos convertem
    as cláusulas livres do documento (doc['clausulas']) para a mesma estrutura."""
    tipo = (doc.get("tipo_contrato") or "").lower()
    if "exclusiv" in tipo:
        return clausulas_exclusividade(doc)
    out: List[Clausula] = []
    for cl in (doc.get("clausulas") or []):
        if not isinstance(cl, dict):
            continue
        titulo = (cl.get("titulo") or "").strip()
        num = cl.get("numero")
        cab = f"CLÁUSULA {num} — {titulo}" if num else titulo
        conteudo = (cl.get("conteudo") or "").strip()
        out.append(Clausula(titulo=cab, itens=[conteudo] if conteudo else []))
    return out


def clausulas_para_texto(doc: dict) -> str:
    """Renderiza o texto montado em string plana (para golden snapshot/testes)."""
    linhas = []
    if "exclusiv" in (doc.get("tipo_contrato") or "").lower():
        linhas.extend(preambulo_exclusividade(doc))
        linhas.append("")
    for cl in montar_clausulas(doc):
        linhas.append(cl.titulo)
        linhas.extend(cl.itens)
        linhas.append("")
    if "exclusiv" in (doc.get("tipo_contrato") or "").lower():
        linhas.append(fecho_exclusividade(doc))
    texto = "\n".join(linhas)
    return texto.replace("<b>", "").replace("</b>", "")
