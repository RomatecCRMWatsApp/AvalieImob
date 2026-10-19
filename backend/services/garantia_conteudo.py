# @module services.garantia_conteudo — Conteúdo do Laudo de Avaliação de Garantia.
# Fonte ÚNICA do texto: o PDF (pdf/garantia_pdf.py) e o DOCX (docx_gen/garantia_docx.py)
# renderizam a MESMA lista de seções, então os dois formatos nunca divergem.
#
# Cada seção: {"titulo": str, "blocos": [("kv", [(rotulo, valor), ...]) | ("p", texto)]}
# Linhas com valor vazio são omitidas (o laudo não imprime "—" em campo não usado).
from __future__ import annotations

import html
import re
from datetime import datetime

TIPOS = {
    "imovel_rural": "Imóvel Rural", "imovel_urbano": "Imóvel Urbano",
    "apartamento": "Apartamento", "casa": "Casa", "comercial": "Imóvel Comercial",
    "terreno": "Terreno", "graos_safra": "Grãos / Safra", "bovinos": "Bovinos",
    "equipamentos": "Equipamentos", "veiculos": "Veículos", "outros": "Outros bens",
}
MODALIDADES = {
    "sfh_fgts": "SFH / FGTS (Lei 4.380/1964 · Lei 8.036/1990)",
    "sfi_bancario": "SFI / Bancário (Lei 9.514/1997)",
    "alienacao_fiduciaria": "Alienação Fiduciária (Lei 9.514/1997, art. 27)",
    "hipoteca": "Hipoteca",
    "credito_rural": "Crédito Rural",
}
FINALIDADES = {
    "credito_rural": "Crédito Rural", "financiamento": "Financiamento", "penhor": "Penhor",
    "alienacao_fiduciaria": "Alienação Fiduciária", "outros": "Outros",
}
CONSERVACAO = {
    "novo": "Novo", "otimo": "Ótimo", "bom": "Bom", "regular": "Regular",
    "ruim": "Ruim", "pessimo": "Péssimo",
}
BANCARIAS = {"sfh_fgts", "sfi_bancario", "alienacao_fiduciaria", "hipoteca"}
IMOVEIS = {"imovel_rural", "imovel_urbano", "apartamento", "casa", "comercial", "terreno"}


def texto(v) -> str:
    """Texto livre (pode vir com HTML do editor) → texto plano."""
    if v is None:
        return ""
    s = str(v)
    s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</\s*(p|div|li)\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def num(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def brl(v) -> str:
    n = num(v)
    if not n:
        return ""
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def br(v, casas=2, unidade="") -> str:
    n = num(v)
    if not n:
        return ""
    s = f"{n:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s}{(' ' + unidade) if unidade else ''}"


def data_br(v) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    s = str(v)[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(v)


def sim_nao(v) -> str:
    return "Sim" if v else "Não"


def valor_principal(g: dict) -> float:
    return num(g.get("valor_mercado")) or num(g.get("valor_total")) or 0.0


def eh_bancario(g: dict) -> bool:
    return (g.get("modalidade_financeira") or "") in BANCARIAS


def titulo_laudo(g: dict) -> str:
    return "LAUDO DE AVALIAÇÃO DE GARANTIA"


def subtitulo(g: dict) -> str:
    partes = [TIPOS.get(g.get("tipo_garantia"), "Bem")]
    mod = g.get("modalidade_financeira")
    if mod:
        partes.append(MODALIDADES.get(mod, mod).split(" (")[0])
    return " · ".join(partes)


def descricao_curta(g: dict) -> str:
    return (g.get("mutuario_nome") or texto(g.get("descricao_bem"))[:90]
            or g.get("endereco") or g.get("municipio") or "")


def _kv(pares):
    return ("kv", [(r, v) for r, v in pares if v not in (None, "", "R$ 0,00")])


def _p(t):
    t = texto(t)
    return ("p", t) if t else None


def _sec(titulo, *blocos):
    bl = [b for b in blocos if b and (b[0] == "p" or b[1])]
    return {"titulo": titulo, "blocos": bl} if bl else None


def secoes(g: dict) -> list:
    sol = g.get("solicitante") or {}
    tipo = g.get("tipo_garantia") or "outros"
    out = []

    out.append(_sec(
        "IDENTIFICAÇÃO DO LAUDO",
        _kv([
            ("Laudo nº", g.get("numero")),
            ("Tipo de bem", TIPOS.get(tipo, tipo)),
            ("Finalidade", FINALIDADES.get(g.get("finalidade"), g.get("finalidade"))),
            ("Modalidade financeira", MODALIDADES.get(g.get("modalidade_financeira"), g.get("modalidade_financeira"))),
            ("Instituição financeira", g.get("instituicao_financeira") or sol.get("instituicao_financeira")),
            ("Valor do financiamento", brl(g.get("valor_financiamento"))),
            ("LTV máximo", br(g.get("ltv_maximo"), 0, "%") if eh_bancario(g) else ""),
            ("Prazo do financiamento", f"{int(num(g.get('prazo_financiamento_meses')))} meses"
             if num(g.get("prazo_financiamento_meses")) else ""),
            ("Finalidade do crédito", g.get("finalidade_credito")),
            ("Data da avaliação", data_br(g.get("data_avaliacao"))),
            ("Validade do laudo", data_br(g.get("data_validade"))
             or (f"{g.get('validade_laudo_meses')} meses" if g.get("validade_laudo_meses") else "")),
        ]),
    ))

    out.append(_sec(
        "SOLICITANTE E MUTUÁRIO",
        _kv([
            ("Solicitante", sol.get("nome")),
            ("CPF/CNPJ do solicitante", sol.get("cpf_cnpj")),
            ("Telefone", sol.get("telefone")),
            ("E-mail", sol.get("email")),
            ("Mutuário", g.get("mutuario_nome")),
            ("CPF/CNPJ do mutuário", g.get("mutuario_cpf_cnpj")),
        ]),
    ))

    # ── Descrição do bem (campos conforme o tipo) ──────────────────────────
    campos = []
    if tipo in IMOVEIS:
        campos = [
            ("Área total", br(g.get("area_total_ha"), 4, "ha") if tipo == "imovel_rural" else ""),
            ("Área construída", br(g.get("area_construida_m2"), 2, "m²")),
            ("Área privativa (NBR 12.721)", br(g.get("area_privativa_nbr12721"), 2, "m²")),
            ("Perímetro", br(g.get("perimetro_m"), 2, "m")),
            ("Padrão construtivo (IBAPE)", g.get("padrao_construtivo_ibape")),
            ("Idade real", f"{g.get('idade_real_anos')} anos" if num(g.get("idade_real_anos")) else ""),
            ("Idade aparente", f"{g.get('idade_aparente_anos')} anos" if num(g.get("idade_aparente_anos")) else ""),
            ("Estado de conservação", CONSERVACAO.get(g.get("estado_conservacao"), g.get("estado_conservacao"))),
            ("Uso atual", g.get("uso_atual")),
            ("Topografia", g.get("topografia")),
            ("Solo / vegetação", g.get("solo_vegetacao")),
        ]
    elif tipo == "graos_safra":
        campos = [
            ("Cultura", g.get("cultura")),
            ("Quantidade", br(g.get("quantidade_toneladas"), 2, "t")),
            ("Sacas", br(g.get("sacas"), 0, "sc")),
            ("Produtividade", br(g.get("produtividade_sc_ha"), 2, "sc/ha")),
            ("Safra de referência", g.get("safra_referencia")),
            ("Local de armazenagem", g.get("local_armazenagem")),
        ]
    elif tipo == "bovinos":
        campos = [
            ("Raça / tipo", g.get("raca_tipo")),
            ("Quantidade", f"{int(num(g.get('quantidade_cabecas')))} cabeças" if num(g.get("quantidade_cabecas")) else ""),
            ("Categoria", g.get("categoria")),
            ("Peso médio", br(g.get("peso_medio_kg"), 1, "kg")),
            ("Aptidão", g.get("aptidao")),
            ("Local do rebanho", g.get("local_rebanho")),
        ]
    elif tipo in ("equipamentos", "veiculos"):
        campos = [
            ("Marca", g.get("marca")), ("Modelo", g.get("modelo")),
            ("Ano de fabricação", str(g.get("ano_fabricacao")) if num(g.get("ano_fabricacao")) else ""),
            ("Nº de série / chassi", g.get("numero_serie")),
            ("Potência", g.get("potencia")),
            ("Horímetro / hodômetro", g.get("horimetro_hodometro")),
            ("Estado de conservação", CONSERVACAO.get(g.get("estado_conservacao"), g.get("estado_conservacao"))),
        ]
    out.append(_sec("DESCRIÇÃO DO BEM", _p(g.get("descricao_bem")), _kv(campos),
                    _p(("Benfeitorias: " + texto(g.get("benfeitorias"))) if texto(g.get("benfeitorias")) else "")))

    gps = ", ".join([x for x in [g.get("gps_lat"), g.get("gps_lng")] if x])
    out.append(_sec(
        "LOCALIZAÇÃO E DOCUMENTAÇÃO",
        _kv([
            ("Endereço", g.get("endereco")),
            ("Município / UF", " / ".join([x for x in [g.get("municipio"), g.get("uf")] if x])),
            ("CEP", g.get("cep")),
            ("Coordenadas (SIRGAS 2000)", gps),
            ("Matrícula", g.get("matricula")),
            ("Data da matrícula", data_br(g.get("data_matricula"))),
            ("Cartório de Registro de Imóveis", g.get("cartorio")),
            ("CRI nº", g.get("cri_numero")),
            ("Inscrição IPTU", g.get("inscricao_iptu")),
            ("Valor venal", brl(g.get("valor_venal"))),
            ("Certificação SIGEF", g.get("certificacao_sigef")),
            ("Cadastro INCRA", g.get("cadastro_incra")),
            ("CCIR", g.get("ccir")),
            ("NIRF / CIB", g.get("nirf_cib")),
            ("CAR", g.get("car")),
        ]),
        _kv([
            ("Habite-se", sim_nao(g.get("habite_se"))),
            ("Conformidade com o plano diretor", sim_nao(g.get("conformidade_plano_diretor"))),
            ("Regularidade construtiva", sim_nao(g.get("regularidade_construtiva"))),
            ("Ônus reais", sim_nao(g.get("onus_reais"))),
        ]) if tipo in IMOVEIS and tipo != "imovel_rural" else None,
        _p(("Ônus / gravames: " + texto(g.get("onus_descricao"))) if g.get("onus_reais") and texto(g.get("onus_descricao")) else ""),
    ))

    out.append(_sec(
        "VISTORIA",
        _kv([
            ("Data da vistoria", data_br(g.get("data_vistoria"))),
            ("Horário", g.get("vistoria_horario")),
            ("Responsável pela vistoria", g.get("vistoria_responsavel_nome")),
        ]),
        _p(g.get("vistoria_condicoes_obs")),
        _p(g.get("observacoes")),
    ))

    ev = g.get("metodo_evolutivo_resultado") or {}
    out.append(_sec(
        "METODOLOGIA E FUNDAMENTAÇÃO",
        _p(g.get("metodologia")),
        _kv([
            ("Fundamentação legal / normativa", g.get("fundamentacao_legal")),
            ("Mercado de referência", g.get("mercado_referencia")),
            ("Nº de amostras", str(int(num(g.get("num_amostras")))) if num(g.get("num_amostras")) else ""),
            ("Coeficiente de variação", br(g.get("coeficiente_variacao"), 2, "%")),
            ("Fator de homogeneização", g.get("fator_homogeneizacao")),
            ("Infraestrutura do entorno", g.get("infraestrutura_entorno")),
            ("Liquidez de mercado", g.get("liquidez_mercado")),
            ("Fatores de depreciação", g.get("fatores_depreciacao")),
            ("Grau de fundamentação", g.get("grau_fundamentacao")),
            ("Grau de precisão", g.get("grau_precisao")),
        ]),
        _kv([
            ("Método evolutivo — CUB", f"{g.get('metodo_evolutivo_tipo_cub') or ''} {brl(g.get('metodo_evolutivo_valor_cub'))}".strip()),
            ("Fonte do CUB", g.get("metodo_evolutivo_fonte_cub")),
            ("Área construída (evolutivo)", br(g.get("metodo_evolutivo_area_construida"), 2, "m²")),
            ("Valor do terreno", brl(g.get("metodo_evolutivo_valor_terreno"))),
            ("Valor pelo método evolutivo", brl(ev.get("valor_total") or ev.get("valor_final"))),
        ]) if g.get("metodo_evolutivo_valor_cub") else None,
    ))

    vp = valor_principal(g)
    vfin = num(g.get("valor_financiamento")) or 0
    ltv_calc = f"{vfin / vp * 100:.1f}%".replace(".", ",") if vp and vfin else ""
    inf, sup = num(g.get("resultado_intervalo_inf")), num(g.get("resultado_intervalo_sup"))
    amin, amax = num(g.get("campo_arbitrio_min")), num(g.get("campo_arbitrio_max"))
    out.append(_sec(
        "RESULTADO DA AVALIAÇÃO",
        _kv([
            ("Valor unitário", brl(g.get("valor_unitario"))),
            ("Valor de mercado", brl(vp)),
            ("Intervalo de confiança", f"{brl(inf)} a {brl(sup)}" if inf and sup else ""),
            ("Campo de arbítrio", f"{brl(amin)} a {brl(amax)}" if amin and amax else ""),
            ("Valor de liquidação forçada (VLF)", brl(g.get("valor_liquidacao_forcada"))),
            ("Fator de desconto VLF", br(g.get("fator_desconto_vlf"), 2, "%")),
            ("Valor para 1º leilão", brl(g.get("valor_1o_leilao"))),
            ("Valor para 2º leilão", brl(g.get("valor_2o_leilao"))),
            ("Valor máximo de garantia", brl(g.get("valor_maximo_garantia"))),
            ("LTV (financiamento ÷ valor de mercado)", ltv_calc),
        ]),
        _p(("Valor por extenso: " + texto(g.get("resultado_em_extenso"))) if texto(g.get("resultado_em_extenso")) else extenso(vp)),
    ))

    out.append(_sec(
        "DECLARAÇÕES DO AVALIADOR",
        _p("O avaliador declara, sob as penas da lei, "
           + ("que NÃO possui conflito de interesse com as partes envolvidas na operação"
              if not g.get("declaracao_conflito_interesse") else
              "a existência de relação com as partes, descrita abaixo")
           + ", e que a presente avaliação foi elaborada em conformidade com a Resolução CMN "
             "4.676/2018 e a ABNT NBR 14.653.") if eh_bancario(g) else None,
        _p(g.get("declaracao_impedimentos")),
        _kv([
            ("ART / RRT / TRT nº", g.get("art_numero")),
            ("Data de registro da ART", data_br(g.get("art_data_registro"))),
        ]),
    ))

    out.append(_sec("CONSIDERAÇÕES FINAIS", _p(g.get("consideracoes"))))
    out.append(_sec("RESSALVAS", _p(g.get("ressalvas"))))
    return [s for s in out if s]


def extenso(v) -> str:
    if not v:
        return ""
    try:
        from utils.extenso import valor_por_extenso
        e = valor_por_extenso(v)
        return f"Valor por extenso: {e}." if e else ""
    except Exception:  # noqa: BLE001
        return ""


def dados_rt(g: dict) -> dict:
    """Responsável técnico: perfil cadastrado > campos do laudo."""
    from utils.avaliador import resolver_dados_avaliador
    resp = g.get("responsavel") or {}
    base = {
        "responsavel_nome": resp.get("nome"),
        "responsavel_creci": resp.get("creci"),
        "art_trt_numero": g.get("art_numero"),
    }
    d = resolver_dados_avaliador(g.get("_perfil") or {}, g.get("_user") or {}, base)
    regs = list(d.get("registros_linhas") or [])
    for extra in [resp.get("cnai"), resp.get("registro") and f"{g.get('responsavel_tipo') or 'Registro'} {resp.get('registro')}"]:
        if extra and extra not in regs and not any(extra in r for r in regs):
            regs.append(extra)
    d["registros_linhas"] = regs
    return d
