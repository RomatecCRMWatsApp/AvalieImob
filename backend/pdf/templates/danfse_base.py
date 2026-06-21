# @module pdf.templates.danfse_base — Conteúdo NEUTRO do DANFSe (independente de tema).
# Regra de ouro (herdada dos Contratos): o conteúdo é montado UMA vez aqui; cada
# renderer (prime1/prime2/tradicional) só decide COMO desenhar, usando os tokens TEMAS.
# Fonte de verdade visual: danfse-acailandia-prime.html (aprovado).
from __future__ import annotations

import re

# ── Tokens dos 3 temas (derivados do HTML aprovado) ──────────────────────────
# faixa_* = faixas de seção; cab_* = cabeçalho; ghost = numeral-fantasma (Prime II).
TEMAS = {
    "prime1": {
        "serif": "Playfair",
        "ouro": "#C9A84C",
        "verde": "#0C3320",
        # cabeçalho split diagonal preto×verde (preto ~46%)
        "cab_split": ("#0E0E0E", "#0C3320", 0.46),
        "cab_grad": None,
        "cab_fg": "#FFFFFF",
        "faixa_bg": "#0E0E0E", "faixa_fg": "#FFFFFF", "faixa_num": "#C9A84C",
        "titulo_fg": "#0C3320",
        "nota_fg": "#C9A84C",
        "ghost": False,
        "brasao_placa": True,
        "borda": "#CFCFCF",
        "label_fg": "#666666",
        "valor_fg": "#0A0A0A",
        "destaque_fg": "#0C3320",
    },
    "prime2": {
        "serif": "Playfair",
        "ouro": "#C9A84C",
        "verde": "#0C3320",
        "cab_split": None,
        "cab_grad": ("#0C3320", "#15724A"),  # gradiente verde
        "cab_fg": "#FFFFFF",
        "faixa_bg": "#0C3320", "faixa_fg": "#FFFFFF", "faixa_num": "#C9A84C",
        "titulo_fg": "#0C3320",
        "nota_fg": "#C9A84C",
        "ghost": True,  # numeral-fantasma — assinatura do tema
        "brasao_placa": True,
        "borda": "#CFCFCF",
        "label_fg": "#666666",
        "valor_fg": "#0A0A0A",
        "destaque_fg": "#0C3320",
    },
    "tradicional": {
        "serif": "Times-Roman",  # Georgia-like serifa cartorial
        "ouro": "#8A6D1F",
        "verde": "#111111",
        "cab_split": None,
        "cab_grad": None,
        "cab_bg": "#FFFFFF",
        "cab_fg": "#111111",
        "cab_borda_inf": "#111111",
        "faixa_bg": "#EAEAEA", "faixa_fg": "#111111", "faixa_num": "#777777",
        "titulo_fg": "#111111",
        "nota_fg": "#8A6D1F",
        "ghost": False,
        "brasao_placa": False,
        "borda": "#000000",
        "label_fg": "#333333",
        "valor_fg": "#000000",
        "destaque_fg": "#111111",
    },
}


# ── Helpers de formatação (espelham o JS do HTML) ────────────────────────────
def num(v) -> float:
    """'17.500,00' / 17500 / '350,00' → float (formato pt-BR ou número)."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "").strip()
    if not s:
        return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return 0.0


def br(n: float) -> str:
    """float → '1.234,56' (pt-BR)."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        n = 0.0
    s = f"{n:,.2f}"  # 1,234.56
    return s.replace(",", "·").replace(".", ",").replace("·", ".")


def _so_dig(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


def mascara_doc(v) -> str:
    """CNPJ (14) → 00.000.000/0000-00 · CPF (11) → 000.000.000-00 · senão mantém."""
    d = _so_dig(v)
    if len(d) == 14:
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
    if len(d) == 11:
        return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"
    return str(v or "")


# ── Cálculos fiscais (espelham recalc() do HTML) ─────────────────────────────
def calcular(doc: dict) -> dict:
    """Recebe o doc FLAT (chaves do HTML aprovado) e devolve os valores calculados."""
    servico = num(doc.get("valor_servico"))
    deducao = num(doc.get("deducao"))
    desc_incond = num(doc.get("desc_incond"))
    desc_cond = num(doc.get("desc_cond"))
    ret_fed = num(doc.get("ret_fed"))
    outras_ret = num(doc.get("outras_ret"))
    iss_retido_v = num(doc.get("iss_retido_v"))

    aliquota = num(doc.get("aliquota_iss"))
    pct = aliquota * 100 if 0 < aliquota <= 1 else aliquota  # aceita 0.02 OU 2,0000

    base = servico - deducao - desc_incond
    valor_iss = base * pct / 100
    valor_liquido = servico - desc_incond - desc_cond - ret_fed - outras_ret - iss_retido_v
    return {
        "servico": servico, "deducao": deducao, "desc_incond": desc_incond,
        "desc_cond": desc_cond, "ret_fed": ret_fed, "outras_ret": outras_ret,
        "iss_retido_v": iss_retido_v, "aliquota_pct": pct,
        "base": base, "valor_iss": valor_iss, "valor_liquido": valor_liquido,
    }


# ── Montagem do CONTEÚDO NEUTRO ──────────────────────────────────────────────
def montar(doc: dict, config: dict | None = None, brasao: bytes | None = None) -> dict:
    """Monta a estrutura neutra do DANFSe (blocos na ordem do HTML aprovado).
    `doc` é o documento FLAT (chaves do HTML / adaptado de nfse_documentos)."""
    doc = dict(doc or {})
    c = calcular(doc)

    def g(k, d=""):
        v = doc.get(k, d)
        return "" if v is None else str(v)

    numero = g("numero_nfse", "0000000000")
    ghost = (numero.lstrip("0") or "0")

    return {
        "cabecalho": {
            "estado": g("estado", "Estado do Maranhão"),
            "prefeitura": g("prefeitura", "Prefeitura Municipal de Açailândia"),
            "secretaria": g("secretaria", "Secretaria de Economia e Finanças"),
            "numero": numero,
            "serie": g("serie", "ELETRÔNICA"),
            "brasao": brasao,
            "ghost": ghost,
        },
        "titulo": "Nota Fiscal Eletrônica de Prestação de Serviços",
        # Controle (rótulo, valor, colspan/4)
        "controle": [
            [("Data de Geração", g("data_geracao"), 1), ("Competência", g("competencia"), 1),
             ("Nº do RPS", g("numero_rps", "0"), 1), ("Nº DPS Substituída", g("dps_substituida", "0"), 1)],
            [("Local da Prestação", g("local_prestacao"), 2), ("Optante do Simples", g("optante_simples", "NÃO"), 1),
             ("Regime Especial", g("regime_esp", "0-Nenhum"), 1)],
            [("Chave de Acesso", g("chave_acesso"), 4)],
        ],
        "secoes": [
            {"n": "01", "titulo": "Dados do Prestador do Serviço", "tipo": "grid", "linhas": [
                [("Razão Social", g("prest_razao"), 3), ("Nome Fantasia", g("prest_fantasia"), 1)],
                [("Endereço", g("prest_endereco"), 4)],
                [("CPF/CNPJ", mascara_doc(g("prest_cnpj")), 1), ("Insc. Municipal", g("prest_im"), 1),
                 ("UF", g("prest_uf"), 1), ("Insc. Estadual", g("prest_ie", "0"), 1)],
                [("Cidade", g("prest_cidade"), 1), ("C.E.P", g("prest_cep"), 1), ("Telefone", g("prest_fone"), 2)],
            ]},
            {"n": "02", "titulo": "Dados do Tomador do Serviço", "tipo": "grid", "linhas": [
                [("Razão Social / Nome", g("tom_razao"), 2), ("E-mail", g("tom_email"), 2)],
                [("Endereço", g("tom_endereco"), 4)],
                [("CPF/CNPJ", mascara_doc(g("tom_cnpj")), 2), ("Insc. Municipal", g("tom_im", "0"), 1),
                 ("Telefone", g("tom_fone"), 1)],
            ]},
            {"n": "03", "titulo": "Discriminação dos Serviços", "tipo": "grid", "linhas": [
                [("", g("discriminacao"), 4, "multiline")],
                [("Código da Atividade / Serviço", g("cod_atividade"), 4)],
            ]},
            {"n": "04", "titulo": "Tributos Federais", "tipo": "grid", "linhas": [
                [("Tipo Retenção", g("tipo_ret", "Não Retido"), 1), ("Aliq. PIS %", g("aliq_pis", "0,00"), 1, "r"),
                 ("PIS R$", br(num(g("pis"))), 1, "r"), ("Aliq. COFINS %", g("aliq_cofins", "0,00"), 1, "r")],
                [("COFINS R$", br(num(g("cofins"))), 1, "r"), ("INSS R$", br(num(g("inss"))), 1, "r"),
                 ("CSLL R$", br(num(g("csll"))), 1, "r"), ("IRRF R$", br(num(g("irrf"))), 1, "r")],
            ]},
            {"n": "05", "titulo": "Valores · Operação · Cálculo do ISS", "tipo": "tricol", "colunas": [
                [("Valor dos Serviços", br(c["servico"]), False), ("(-) Desc. Incondicionado", br(c["desc_incond"]), False),
                 ("(-) Desc. Condicionado", br(c["desc_cond"]), False), ("(-) Retenções Federais", br(c["ret_fed"]), False),
                 ("Outras Retenções", br(c["outras_ret"]), False), ("(-) ISS Retido", br(c["iss_retido_v"]), False),
                 ("(=) Valor Líquido", br(c["valor_liquido"]), True)],
                [("Natureza da Operação", g("natureza", "Tributada no Município"), False),
                 ("Código de Validação", g("cod_validacao"), False), ("Link de Consulta", g("link_consulta"), False),
                 ("ISS a Reter", g("iss_a_reter", "Não"), False)],
                [("Valor dos Serviços", br(c["servico"]), False), ("(-) Dedução em lei", br(c["deducao"]), False),
                 ("(-) Desc. Incondicionado", br(c["desc_incond"]), False), ("Base de Cálculo", br(c["base"]), False),
                 ("(X) Alíquota ISS %", br(c["aliquota_pct"]) if c["aliquota_pct"] else g("aliquota_iss"), False),
                 ("(=) Valor do ISS", br(c["valor_iss"]), True)],
            ]},
            {"n": "06", "titulo": "Reforma Tributária — IBS / CBS", "tipo": "grid", "linhas": [
                [("Valor IBS Municipal R$", br(num(g("ibs_mun"))), 1, "r"),
                 ("Valor IBS Estadual R$", br(num(g("ibs_est"))), 1, "r"),
                 ("Valor CBS R$", br(num(g("cbs"))), 2, "r")],
            ]},
            {"n": "07", "titulo": "Serviços de Construção Civil", "tipo": "grid", "linhas": [
                [("Código CNO/CEI da Obra", g("cno"), 1), ("Insc. Imobiliária (IPTU)", g("iptu"), 1)],
                [("Endereço da Obra", g("end_obra"), 2)],
                [("Outras Informações", g("outras_info"), 2, "multiline")],
            ]},
        ],
        "rodape": {
            "marca": "Romatec Consultoria Total",
            "via": "· Documento emitido via AvalieImob",
            "impressa_em": g("impressa_em"),
            "hora_emissao": g("hora_emissao"),
        },
        "_calc": c,
    }


# ── Documento de EXEMPLO (NFS-e nº 59 — Açailândia, jun/2026) ─────────────────
def documento_exemplo_59() -> dict:
    """Caso real de referência (SPEC seção 12): serviço 17.500 · ISS 2% → 350 · líquido 17.500."""
    return {
        "numero_nfse": "0000000059", "serie": "ELETRÔNICA",
        "estado": "Estado do Maranhão", "prefeitura": "Prefeitura Municipal de Açailândia",
        "secretaria": "Secretaria de Economia e Finanças",
        "data_geracao": "12/06/2026", "competencia": "JUN/2026", "numero_rps": "0", "dps_substituida": "0",
        "local_prestacao": "AÇAILÂNDIA-MA", "optante_simples": "NÃO", "regime_esp": "0-Nenhum",
        "chave_acesso": "21000551217261987000109000000000005926060160875518",
        "prest_razao": "J R P BEZERRA LTDA", "prest_fantasia": "ROMATEC CONSULTORIA TOTAL",
        "prest_endereco": "RUA MANOEL ELZEBRIO, 14 - NOVA AÇAILÂNDIA - 2ª PART - QUADRA 104",
        "prest_cnpj": "17261987000109", "prest_im": "26800", "prest_uf": "MA", "prest_ie": "0",
        "prest_cidade": "Açailândia", "prest_cep": "65930000", "prest_fone": "9991811246",
        "tom_razao": "RODO RANCHO COMBUSTIVEIS LTDA", "tom_email": "autopostorancho@...",
        "tom_endereco": "ROD BR010, 15 KM1407 SETOR LADEIRA VERMELHA 65930000 AÇAILÂNDIA-MA",
        "tom_cnpj": "57123389000180", "tom_im": "0", "tom_fone": "",
        "discriminacao": ("4ª parcela do contrato de serviços de engenharia e agrimensura para a obra "
                          "comercial Posto Chapadão (Itinga/MA), cliente RODO RANCHO COMBUSTÍVEIS LTDA. "
                          "Quinzena 09/06/2026 a 22/06/2026. Valor: R$ 17.500,00 de um total contratual de R$ 70.000,00."),
        "cod_atividade": ("1701 / 0 / 821130001 - Serviços de análise, exame, pesquisa, coleta, compilação e "
                          "fornecimento de dados e informações de qualquer natureza, inclusive cadastro e similares"),
        "tipo_ret": "Não Retido", "aliq_pis": "1,50", "pis": "0,00", "aliq_cofins": "1,50",
        "cofins": "0,00", "inss": "0,00", "csll": "0,00", "irrf": "0,00",
        "valor_servico": "17.500,00", "desc_incond": "0,00", "desc_cond": "0,00", "ret_fed": "0,00",
        "outras_ret": "0,00", "iss_retido_v": "0,00",
        "natureza": "Tributada no Município", "cod_validacao": "38ejmlvaqcwns6yt5gurfi42xzo",
        "link_consulta": "https://servicos2.speedgov.com.br/acailandia/", "iss_a_reter": "Não",
        "deducao": "0,00", "aliquota_iss": "2,0000",
        "ibs_mun": "0,00", "ibs_est": "0,00", "cbs": "0,00",
        "cno": "", "iptu": "", "end_obra": "", "outras_info": "",
        "impressa_em": "12/06/26 12:13", "hora_emissao": "12:12:40",
    }
