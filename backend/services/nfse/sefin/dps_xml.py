# @module services.nfse.sefin.dps_xml — Builder do XML da DPS (NFS-e Padrão Nacional).
"""Monta o XML da DPS (Declaração de Prestação de Serviço) a partir do NFSeDocumento.

⚠️ ATENÇÃO (não pular): o LEIAUTE (nomes/ordem de tags, namespace, versão) DEVE ser
validado contra o XSD oficial do MOC NFS-e Nacional / Swagger contribuintes ISSQN ANTES
de qualquer emissão em produção. Este builder reproduz os GRUPOS conhecidos (infDPS,
prest, toma, serv, valores, trib, IBS/CBS) com base na documentação do padrão nacional,
mas a conformidade exata só é garantida pelo XSD + teste em HOMOLOGAÇÃO. Os testes deste
módulo verificam a ESTRUTURA que montamos, não a conformidade com o schema oficial.

Segurança: tpAmb = 2 (HOMOLOGAÇÃO) por padrão; só vira 1 (produção) quando o documento
estiver com ambiente='producao' explicitamente.
"""
from __future__ import annotations

from lxml import etree

from models.nfse import NFSeDocumento, NFSeConfig, Ambiente, calcular_valores

NS = "http://www.sped.fazenda.gov.br/nfse"
VERSAO = "1.00"
VER_APLIC = "AvalieImob-1.0"


def _so_dig(v) -> str:
    return "".join(c for c in str(v or "") if c.isdigit())


def _money(v) -> str:
    try:
        return f"{float(v or 0):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _el(parent, tag, text=None):
    e = etree.SubElement(parent, f"{{{NS}}}{tag}")
    if text is not None and text != "":
        e.text = str(text)
    return e


def montar_dps_xml(doc: NFSeDocumento, config: NFSeConfig, pretty: bool = False) -> str:
    """Retorna o XML (string) da DPS, NÃO assinado. A assinatura é aplicada à parte."""
    calc = calcular_valores(doc.servico)
    tp_amb = "1" if doc.ambiente == Ambiente.producao else "2"   # 2 = homologação (seguro)
    id_dps = doc.dps.id_dps or f"DPS{doc.id}"

    root = etree.Element(f"{{{NS}}}DPS", nsmap={None: NS}, versao=VERSAO)
    inf = _el(root, "infDPS")
    inf.set("Id", id_dps)

    _el(inf, "tpAmb", tp_amb)
    if doc.dps.data_emissao:
        _el(inf, "dhEmi", doc.dps.data_emissao.replace(microsecond=0).isoformat())
    _el(inf, "verAplic", VER_APLIC)
    _el(inf, "serie", doc.dps.serie)
    _el(inf, "nDPS", str(doc.dps.numero or 0))
    _el(inf, "dCompet", (doc.dps.data_emissao.date().isoformat() if doc.dps.data_emissao else ""))
    _el(inf, "tpEmit", "1")  # 1 = prestador
    _el(inf, "cLocEmi", config.emitente.endereco.codigo_ibge or config.codigo_ibge)

    # ── Prestador ────────────────────────────────────────────────────────────
    prest = _el(inf, "prest")
    _el(prest, "CNPJ", _so_dig(config.emitente.cnpj))
    _el(prest, "IM", config.emitente.inscricao_municipal)
    _el(prest, "xNome", config.emitente.razao_social)
    regtrib = _el(prest, "regTrib")
    _el(regtrib, "opSimpNac", "1" if config.emitente.optante_simples else "2")
    _el(regtrib, "regEspTrib", config.fiscal_defaults.regime_especial_tributacao or "0")

    # ── Tomador ──────────────────────────────────────────────────────────────
    toma = _el(inf, "toma")
    docto = _so_dig(doc.tomador.documento)
    if len(docto) == 14:
        _el(toma, "CNPJ", docto)
    elif len(docto) == 11:
        _el(toma, "CPF", docto)
    _el(toma, "xNome", doc.tomador.razao_nome)
    if doc.tomador.email:
        _el(toma, "email", doc.tomador.email)

    # ── Serviço ──────────────────────────────────────────────────────────────
    serv = _el(inf, "serv")
    loc = _el(serv, "locPrest")
    _el(loc, "cLocPrestacao", doc.servico.local_prestacao_ibge or config.codigo_ibge)
    cserv = _el(serv, "cServ")
    _el(cserv, "cTribNac", doc.servico.item_lista_servico.replace(".", ""))
    _el(cserv, "cTribMun", doc.servico.codigo_tributacao_municipal)
    _el(cserv, "xDescServ", doc.servico.discriminacao)

    # ── Valores + Tributação ─────────────────────────────────────────────────
    valores = _el(inf, "valores")
    vserv = _el(valores, "vServPrest")
    _el(vserv, "vServ", _money(doc.servico.valor_servico))
    vdesc = _el(valores, "vDescCondIncond")
    _el(vdesc, "vDescIncond", _money(doc.servico.desconto_incondicionado))
    _el(vdesc, "vDescCond", _money(doc.servico.desconto_condicionado))

    trib = _el(valores, "trib")
    tribmun = _el(trib, "tribMun")
    _el(tribmun, "tribISSQN", "1")  # 1 = exigível/tributável no município
    _el(tribmun, "cLocIncid", doc.servico.local_prestacao_ibge or config.codigo_ibge)
    aliq = doc.servico.aliquota_iss
    pct = aliq * 100 if 0 < aliq <= 1 else aliq
    _el(tribmun, "pAliq", f"{pct:.4f}")
    _el(tribmun, "tpRetISSQN", "1" if doc.servico.iss_retido else "2")  # 1=retido 2=não
    _el(tribmun, "vBC", _money(calc["base_calculo"]))
    _el(tribmun, "vISSQN", _money(calc["valor_iss"]))

    totrib = _el(trib, "totTrib")
    _el(totrib, "indTotTrib", "0")  # 0 = sem valor estimado de tributos (Lei 12.741)

    # ── Grupo IBS/CBS (transição RTC 2026 — sempre presente, zerado) ──────────
    ib = doc.servico.ibscbs
    if ib and ib.incluir:
        gibscbs = _el(valores, "IBSCBS")
        _el(gibscbs, "vIBSMun", _money(ib.valor_ibs_municipal))
        _el(gibscbs, "vIBSUF", _money(ib.valor_ibs_estadual))
        _el(gibscbs, "vCBS", _money(ib.valor_cbs))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                          pretty_print=pretty).decode("utf-8")
