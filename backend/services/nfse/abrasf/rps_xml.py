# @module services.nfse.abrasf.rps_xml — Builder do RPS/Lote no padrão ABRASF 1.0.
"""Monta o `EnviarLoteRpsEnvio` (ABRASF 1.0) a partir do NFSeDocumento + NFSeConfig.

⚠️ LEIAUTE: ABRASF 1.0 é base; cada município/provedor (SpeedGov) pode ter variações
(aliquota como fração vs %, campos opcionais, ordem). VALIDAR contra o WSDL/manual do
SpeedGov de Açailândia antes de transmitir. Por isso a transmissão fica TRAVADA.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from lxml import etree

from models.nfse import NFSeConfig, NFSeDocumento, calcular_valores

NS_DEFAULT = "http://www.abrasf.org.br/nfse.xsd"


def _money(v) -> str:
    return str(Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _aliq(v) -> str:
    # SpeedGov (ISS V2 de Açailândia) usa alíquota como PERCENTUAL (ex.: 2.00 = 2%) — confirmado
    # no XML real da NFS-e 59. Aceita fração (0.02) e normaliza p/ percentual.
    a = float(v or 0)
    if a <= 1:           # veio como fração (0.02) → percentual (2.00)
        a = a * 100.0
    return str(Decimal(str(a)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _so_digitos(s: str) -> str:
    return "".join(ch for ch in str(s or "") if ch.isdigit())


def _item_sem_ponto(item: str) -> str:
    return str(item or "").replace(".", "").strip()


def _el(parent, tag, text=None, ns=NS_DEFAULT):
    e = etree.SubElement(parent, f"{{{ns}}}{tag}")
    if text is not None and text != "":
        e.text = str(text)
    return e


def montar_lote_rps_xml(doc: NFSeDocumento, config: NFSeConfig, pretty: bool = False) -> str:
    """Monta o XML `EnviarLoteRpsEnvio` (1 RPS no lote). Sem assinatura (ver assinatura_abrasf)."""
    ab = config.abrasf
    ns = ab.namespace or NS_DEFAULT
    emit = config.emitente
    serv = doc.servico
    tom = doc.tomador
    calc = calcular_valores(serv)

    numero = str(doc.dps.numero or 0)
    serie = ab.serie_rps or "1"
    rps_id = f"rps{numero}"
    lote_id = f"lote{numero}"

    root = etree.Element(f"{{{ns}}}EnviarLoteRpsEnvio", nsmap={None: ns})
    lote = _el(root, "LoteRps", ns=ns)
    lote.set("Id", lote_id)
    lote.set("versao", ab.versao_abrasf or "1.00")
    _el(lote, "NumeroLote", numero, ns)
    _el(lote, "Cnpj", _so_digitos(emit.cnpj), ns)
    _el(lote, "InscricaoMunicipal", _so_digitos(emit.inscricao_municipal), ns)
    _el(lote, "QuantidadeRps", "1", ns)
    lista = _el(lote, "ListaRps", ns=ns)

    rps = _el(lista, "Rps", ns=ns)
    inf = _el(rps, "InfRps", ns=ns)
    inf.set("Id", rps_id)

    ident = _el(inf, "IdentificacaoRps", ns=ns)
    _el(ident, "Numero", numero, ns)
    _el(ident, "Serie", serie, ns)
    _el(ident, "Tipo", ab.tipo_rps or "1", ns)

    dh = (doc.dps.data_emissao.isoformat() if doc.dps.data_emissao else None)
    _el(inf, "DataEmissao", (dh or "")[:19], ns)
    _el(inf, "NaturezaOperacao", "1", ns)                          # 1 = tributação no município
    _el(inf, "OptanteSimplesNacional", "1" if emit.optante_simples else "2", ns)
    _el(inf, "IncentivadorCultural", "2", ns)                      # 2 = não
    _el(inf, "Status", "1", ns)                                    # 1 = normal

    servico = _el(inf, "Servico", ns=ns)
    valores = _el(servico, "Valores", ns=ns)
    _el(valores, "ValorServicos", _money(serv.valor_servico), ns)
    _el(valores, "ValorDeducoes", _money(serv.valor_deducoes), ns)
    _el(valores, "ValorPis", _money(serv.tributos_federais.pis), ns)
    _el(valores, "ValorCofins", _money(serv.tributos_federais.cofins), ns)
    _el(valores, "ValorInss", _money(serv.tributos_federais.inss), ns)
    _el(valores, "ValorIr", _money(serv.tributos_federais.irrf), ns)
    _el(valores, "ValorCsll", _money(serv.tributos_federais.csll), ns)
    _el(valores, "IssRetido", "1" if serv.iss_retido else "2", ns)  # 1=Sim 2=Não
    _el(valores, "ValorIss", _money(calc["valor_iss"]), ns)
    _el(valores, "BaseCalculo", _money(calc["base_calculo"]), ns)
    _el(valores, "Aliquota", _aliq(serv.aliquota_iss), ns)
    _el(valores, "DescontoIncondicionado", _money(serv.desconto_incondicionado), ns)
    _el(valores, "DescontoCondicionado", _money(serv.desconto_condicionado), ns)

    _el(servico, "ItemListaServico", _item_sem_ponto(serv.item_lista_servico or config.fiscal_defaults.item_lista_servico), ns)
    cnae = _so_digitos(config.fiscal_defaults.cnae)
    if cnae:
        _el(servico, "CodigoCnae", cnae, ns)
    cod_mun = serv.codigo_tributacao_municipal or config.fiscal_defaults.codigo_tributacao_municipal
    if cod_mun:
        _el(servico, "CodigoTributacaoMunicipio", cod_mun, ns)
    _el(servico, "Discriminacao", serv.discriminacao or doc.origem.descricao or "", ns)
    _el(servico, "CodigoMunicipio", _so_digitos(config.codigo_ibge), ns)

    prest = _el(inf, "Prestador", ns=ns)
    _el(prest, "Cnpj", _so_digitos(emit.cnpj), ns)
    _el(prest, "InscricaoMunicipal", _so_digitos(emit.inscricao_municipal), ns)

    doc_tom = _so_digitos(tom.documento)
    if doc_tom:
        tomador = _el(inf, "Tomador", ns=ns)
        ident_t = _el(tomador, "IdentificacaoTomador", ns=ns)
        cpfcnpj = _el(ident_t, "CpfCnpj", ns=ns)
        _el(cpfcnpj, "Cnpj" if len(doc_tom) == 14 else "Cpf", doc_tom, ns)
        if tom.razao_nome:
            _el(tomador, "RazaoSocial", tom.razao_nome, ns)
        end = tom.endereco
        if end and (end.logradouro or end.cep):
            e_end = _el(tomador, "Endereco", ns=ns)
            if end.logradouro:
                _el(e_end, "Endereco", end.logradouro, ns)
            if end.numero:
                _el(e_end, "Numero", end.numero, ns)
            if end.bairro:
                _el(e_end, "Bairro", end.bairro, ns)
            if end.codigo_ibge:
                _el(e_end, "CodigoMunicipio", _so_digitos(end.codigo_ibge), ns)
            if end.cep:
                _el(e_end, "Cep", _so_digitos(end.cep), ns)

    return etree.tostring(root, encoding="UTF-8", xml_declaration=True,
                          pretty_print=pretty).decode("utf-8")
