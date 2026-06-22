# @module services.nfse.abrasf.rps_xml — Builder do RPS/Lote no padrão ABRASF 1.0 do SpeedGov.
"""Monta o `EnviarLoteRpsEnvio` conforme os XSD OFICIAIS do SpeedGov (Intersol):
  - EnviarLoteRpsEnvio + LoteRps  → ns `http://ws.speedgov.com.br/enviar_lote_rps_envio_v1.xsd`
  - Todo o conteúdo (NumeroLote…InfRps…)  → ns `http://ws.speedgov.com.br/tipos_v1.xsd`
Validado contra `enviar_lote_rps_envio_v1.xsd` + `tipos_v1.xsd`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from lxml import etree

from models.nfse import NFSeConfig, NFSeDocumento, calcular_valores

NS_ENVIO = "http://ws.speedgov.com.br/enviar_lote_rps_envio_v1.xsd"
NS_TIPOS = "http://ws.speedgov.com.br/tipos_v1.xsd"
NS_CABECALHO = "http://ws.speedgov.com.br/cabecalho_v1.xsd"


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


def _money(v) -> str:                       # tsValor: decimal, 2 casas fixas
    return str(Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _aliq(v) -> str:                        # tsAliquota: decimal, 4 casas (percentual, ex.: 2.0000)
    a = float(v or 0)
    if a <= 1:                              # fração (0.02) → percentual (2.0000)
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


def _item(item) -> str:                     # tsItemListaServico: string ≤5 (sem ponto: 1701)
    return str(item or "").replace(".", "").strip()[:5]


def _t(parent, tag, text=None):             # elemento no ns TIPOS
    e = etree.SubElement(parent, f"{{{NS_TIPOS}}}{tag}")
    if text is not None and text != "":
        e.text = str(text)
    return e


# tsVersao = [0-9]{1,4} (só dígitos, SEM ponto). "1.00" → "100".
VERSAO_DADOS = "100"


def montar_cabecalho() -> str:
    """Cabeçalho ABRASF (param `header`) — ns cabecalho_v1.xsd; versaoDados UNqualified.
    versao/versaoDados = dígitos (tsVersao [0-9]{1,4})."""
    cab = etree.Element(f"{{{NS_CABECALHO}}}cabecalho", nsmap={"c": NS_CABECALHO})
    cab.set("versao", VERSAO_DADOS)
    vd = etree.SubElement(cab, "versaoDados")   # sem ns (elementFormDefault unqualified)
    vd.text = VERSAO_DADOS
    return etree.tostring(cab, encoding="unicode")


def montar_lote_rps_xml(doc: NFSeDocumento, config: NFSeConfig, pretty: bool = False) -> str:
    """Monta o `EnviarLoteRpsEnvio` (1 RPS). Sem assinatura (ver assinatura_abrasf)."""
    emit = config.emitente
    serv = doc.servico
    tom = doc.tomador
    fd = config.fiscal_defaults
    calc = calcular_valores(serv)

    numero = str(doc.dps.numero or 0)
    serie = config.abrasf.serie_rps or "1"

    root = etree.Element(f"{{{NS_ENVIO}}}EnviarLoteRpsEnvio",
                         nsmap={None: NS_TIPOS, "e": NS_ENVIO})
    lote = etree.SubElement(root, f"{{{NS_ENVIO}}}LoteRps")    # LoteRps no ns ENVIO; só atributo Id
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
    _t(inf, "DataEmissao", dh.isoformat()[:19])         # xsd:dateTime obrigatório
    _t(inf, "NaturezaOperacao", "1")
    _t(inf, "OptanteSimplesNacional", "1" if emit.optante_simples else "2")
    _t(inf, "IncentivadorCultural", "2")
    _t(inf, "Status", "1")

    servico = _t(inf, "Servico")
    val = _t(servico, "Valores")
    _t(val, "ValorServicos", _money(serv.valor_servico))
    _t(val, "ValorDeducoes", _money(serv.valor_deducoes))
    _t(val, "IssRetido", "1" if serv.iss_retido else "2")     # tsSimNao: 1=Sim 2=Não
    _t(val, "ValorIss", _money(calc["valor_iss"]))
    _t(val, "BaseCalculo", _money(calc["base_calculo"]))
    _t(val, "Aliquota", _aliq(serv.aliquota_iss))
    _t(val, "DescontoCondicionado", _money(serv.desconto_condicionado))      # ordem do XSD:
    _t(val, "DescontoIncondicionado", _money(serv.desconto_incondicionado))  # Cond. antes de Incond.

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
