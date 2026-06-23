# @module services.nfse.abrasf.rps_xml — Builder do RPS/Lote ABRASF 1.0 do SpeedGov (Intersol).
"""Monta o `EnviarLoteRpsEnvio` IDÊNTICO ao modelo oficial do SpeedGov (modelos_xml/envio_lote):
  - prefixos `p`(envio)/`p1`(tipos)/`ds`(dsig)/`xsi`; `xsi:schemaLocation` no root;
  - EnviarLoteRpsEnvio+LoteRps em `enviar_lote_rps_envio_v1.xsd`; conteúdo em `tipos_v1.xsd`;
  - todos os campos de Valores (federais zerados), na ordem do XSD;
  - cabeçalho com versao="1"/versaoDados="1" (tsVersao [0-9]{1,4}) + schemaLocation.
Validado contra `enviar_lote_rps_envio_v1.xsd`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from lxml import etree

from models.nfse import NFSeConfig, NFSeDocumento, calcular_valores

NS_ENVIO = "http://ws.speedgov.com.br/enviar_lote_rps_envio_v1.xsd"
NS_TIPOS = "http://ws.speedgov.com.br/tipos_v1.xsd"
NS_CABECALHO = "http://ws.speedgov.com.br/cabecalho_v1.xsd"
NS_DSIG = "http://www.w3.org/2000/09/xmldsig#"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"

NS_CONS_RPS = "http://ws.speedgov.com.br/consultar_nfse_rps_envio_v1.xsd"

VERSAO_DADOS = "1"          # tsVersao [0-9]{1,4} — modelo oficial usa "1"
_XSD_DIR = __import__("os").path.join(__import__("os").path.dirname(__file__), "xsd")


def validar_rps_xsd(xml: str | bytes):
    """Valida o EnviarLoteRpsEnvio contra o XSD oficial empacotado. Retorna (ok, [erros])."""
    import os
    caminho = os.path.join(_XSD_DIR, "enviar_lote_rps_envio_v1.xsd")
    if not os.path.exists(caminho):
        return None, ["XSD não empacotado"]
    try:
        schema = etree.XMLSchema(etree.parse(caminho))
        tree = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ok = schema.validate(tree)
        return ok, [e.message for e in schema.error_log][:8]
    except Exception as e:  # noqa: BLE001
        return False, [str(e)]


def _money(v) -> str:                       # tsValor: decimal, 2 casas
    return str(Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _aliq(v) -> str:                        # tsAliquota: percentual, 4 casas (2.0000)
    a = float(v or 0)
    if a <= 1:
        a = a * 100.0
    return str(Decimal(str(a)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _digitos(s) -> str:
    return "".join(ch for ch in str(s or "") if ch.isdigit())


def _texto_simples(s) -> str:
    """Remove HTML (do RichText) e normaliza — a Discriminação da NFS-e é texto puro."""
    import re
    from html import unescape
    t = str(s or "")
    t = re.sub(r"(?i)</(p|div|li|br)>", "\n", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = unescape(t)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", t)).strip()


def _item(item) -> str:                     # tsItemListaServico: string ≤5 (sem ponto)
    return str(item or "").replace(".", "").strip()[:5]


def _t(parent, tag, text=None):             # elemento no ns TIPOS (prefixo p1)
    e = etree.SubElement(parent, f"{{{NS_TIPOS}}}{tag}")
    if text is not None and text != "":
        e.text = str(text)
    return e


def _tnz(parent, tag, valor):
    """Emite a tag de valor SÓ se > 0 (manual 4.2: 'TAG nula deve ser OMITIDA, não enviada
    vazia/zerada'). Mantém a sequência do XSD e elimina a ambiguidade de ordem das tags
    opcionais (ex.: ValorIssRetido) — quando zeradas, simplesmente não aparecem."""
    try:
        v = float(valor or 0)
    except (TypeError, ValueError):
        v = 0.0
    if v > 0:
        _t(parent, tag, _money(valor))


def montar_cabecalho() -> str:
    """Cabeçalho (param `header`) — idêntico ao modelo oficial (com declaração, p/p1/ds/xsi,
    schemaLocation; versao/versaoDados='1'; versaoDados UNqualified)."""
    cab = etree.Element(f"{{{NS_CABECALHO}}}cabecalho",
                        nsmap={"ds": NS_DSIG, "p": NS_CABECALHO, "p1": NS_TIPOS, "xsi": NS_XSI})
    cab.set("versao", VERSAO_DADOS)
    cab.set(f"{{{NS_XSI}}}schemaLocation", f"{NS_CABECALHO} cabecalho_v1.xsd ")
    vd = etree.SubElement(cab, "versaoDados")    # sem ns (unqualified)
    vd.text = VERSAO_DADOS
    return etree.tostring(cab, encoding="UTF-8", xml_declaration=True).decode("utf-8")


def montar_consultar_nfse_rps_xml(config: NFSeConfig, numero, serie="1", tipo="1") -> str:
    """Monta o `ConsultarNfseRpsEnvio` (operação ConsultarNfsePorRps) — modelo oficial.
    Consulta se uma NFS-e foi gerada a partir do RPS (numero/serie/tipo + prestador)."""
    emit = config.emitente
    root = etree.Element(f"{{{NS_CONS_RPS}}}ConsultarNfseRpsEnvio",
                         nsmap={"ds": NS_DSIG, "p": NS_CONS_RPS, "p1": NS_TIPOS, "xsi": NS_XSI})
    root.set(f"{{{NS_XSI}}}schemaLocation", f"{NS_CONS_RPS} consultar_nfse_rps_envio_v1.xsd ")
    ident = etree.SubElement(root, f"{{{NS_CONS_RPS}}}IdentificacaoRps")
    _t(ident, "Numero", str(numero))
    _t(ident, "Serie", serie or "1")
    _t(ident, "Tipo", tipo or "1")
    prest = etree.SubElement(root, f"{{{NS_CONS_RPS}}}Prestador")
    _t(prest, "Cnpj", _digitos(emit.cnpj))
    _t(prest, "InscricaoMunicipal", _digitos(emit.inscricao_municipal))
    return etree.tostring(root, encoding="UTF-8", xml_declaration=True).decode("utf-8")


def montar_lote_rps_xml(doc: NFSeDocumento, config: NFSeConfig, pretty: bool = False) -> str:
    """Monta o `EnviarLoteRpsEnvio` (1 RPS) idêntico ao modelo oficial. Sem assinatura."""
    emit = config.emitente
    serv = doc.servico
    tom = doc.tomador
    fd = config.fiscal_defaults
    tf = serv.tributos_federais
    calc = calcular_valores(serv)

    numero = str(doc.dps.numero or 0)
    serie = config.abrasf.serie_rps or "1"

    root = etree.Element(f"{{{NS_ENVIO}}}EnviarLoteRpsEnvio",
                         nsmap={"ds": NS_DSIG, "p": NS_ENVIO, "p1": NS_TIPOS, "xsi": NS_XSI})
    root.set(f"{{{NS_XSI}}}schemaLocation", f"{NS_ENVIO} enviar_lote_rps_envio_v1.xsd ")

    lote = etree.SubElement(root, f"{{{NS_ENVIO}}}LoteRps")    # p:LoteRps
    lote.set("Id", f"lote{numero}")
    _t(lote, "NumeroLote", numero)
    _t(lote, "Cnpj", _digitos(emit.cnpj))
    _t(lote, "InscricaoMunicipal", _digitos(emit.inscricao_municipal))
    _t(lote, "QuantidadeRps", "1")
    lista = _t(lote, "ListaRps")

    rps = _t(lista, "Rps")
    inf = _t(rps, "InfRps")
    inf.set("Id", f"rps{numero}")

    ident = _t(inf, "IdentificacaoRps")
    _t(ident, "Numero", numero)
    _t(ident, "Serie", serie)
    _t(ident, "Tipo", config.abrasf.tipo_rps or "1")

    dh = doc.dps.data_emissao or datetime.now(timezone.utc)
    _t(inf, "DataEmissao", dh.isoformat()[:19])
    _t(inf, "NaturezaOperacao", "1")
    _t(inf, "OptanteSimplesNacional", "1" if emit.optante_simples else "2")
    _t(inf, "IncentivadorCultural", "2")
    _t(inf, "Status", "1")

    servico = _t(inf, "Servico")
    val = _t(servico, "Valores")                # ordem do tcValores (XSD); zeros OMITIDOS (manual 4.2)
    _t(val, "ValorServicos", _money(serv.valor_servico))          # 1-1 obrigatório
    _tnz(val, "ValorDeducoes", serv.valor_deducoes)
    _tnz(val, "ValorPis", tf.pis)
    _tnz(val, "ValorCofins", tf.cofins)
    _tnz(val, "ValorInss", tf.inss)
    _tnz(val, "ValorIr", tf.irrf)
    _tnz(val, "ValorCsll", tf.csll)
    _t(val, "IssRetido", "1" if serv.iss_retido else "2")        # 1-1 obrigatório
    _tnz(val, "ValorIss", calc["valor_iss"])
    _tnz(val, "ValorIssRetido", calc["valor_iss"] if serv.iss_retido else 0)
    _tnz(val, "OutrasRetencoes", 0)
    _t(val, "BaseCalculo", _money(calc["base_calculo"]))
    _t(val, "Aliquota", _aliq(serv.aliquota_iss))
    _tnz(val, "DescontoCondicionado", serv.desconto_condicionado)
    _tnz(val, "DescontoIncondicionado", serv.desconto_incondicionado)

    _t(servico, "ItemListaServico", _item(serv.item_lista_servico or fd.item_lista_servico))
    if _digitos(fd.cnae):
        _t(servico, "CodigoCnae", _digitos(fd.cnae))
    cod_mun = serv.codigo_tributacao_municipal or fd.codigo_tributacao_municipal
    if cod_mun:
        _t(servico, "CodigoTributacaoMunicipio", cod_mun)
    _t(servico, "Discriminacao", _texto_simples(serv.discriminacao or doc.origem.descricao or ""))
    _t(servico, "CodigoMunicipio", _digitos(config.codigo_ibge))

    prest = _t(inf, "Prestador")
    _t(prest, "Cnpj", _digitos(emit.cnpj))
    _t(prest, "InscricaoMunicipal", _digitos(emit.inscricao_municipal))

    doc_tom = _digitos(tom.documento)
    if doc_tom:
        tomador = _t(inf, "Tomador")
        ident_t = _t(tomador, "IdentificacaoTomador")
        cpfcnpj = _t(ident_t, "CpfCnpj")
        _t(cpfcnpj, "Cnpj" if len(doc_tom) == 14 else "Cpf", doc_tom)
        if tom.razao_nome:
            _t(tomador, "RazaoSocial", tom.razao_nome)
        end = tom.endereco
        if end and (end.logradouro or end.cep):
            e_end = _t(tomador, "Endereco")
            if end.logradouro:
                _t(e_end, "Endereco", end.logradouro)
            if end.numero:
                _t(e_end, "Numero", end.numero)
            if end.complemento:
                _t(e_end, "Complemento", end.complemento)
            if end.bairro:
                _t(e_end, "Bairro", end.bairro)
            if end.codigo_ibge:
                _t(e_end, "CodigoMunicipio", _digitos(end.codigo_ibge))
            if end.cep:
                _t(e_end, "Cep", _digitos(end.cep))

    return etree.tostring(root, encoding="UTF-8", xml_declaration=True,
                          pretty_print=pretty).decode("utf-8")
