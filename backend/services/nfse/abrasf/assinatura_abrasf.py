# @module services.nfse.abrasf.assinatura_abrasf — Assinatura XMLDSIG do RPS/Lote (ABRASF SpeedGov).
"""Assina com **xmlsec** (libxml2) — canonicalização idêntica à do Java (interop com o SpeedGov),
resolvendo o E160 que a c14n do signxml causava. Assina cada `<Rps>` (ref #InfRps.Id) e o
`<LoteRps>` (ref #Id), enveloped, RSA-SHA1, C14N INCLUSIVO (REC-xml-c14n-20010315), com `Id` no
`<Signature>` (XS02) e KeyInfo/X509Data/X509Certificate (XS21). Import lazy de xmlsec.
"""
from __future__ import annotations

from lxml import etree

from services.nfse.exceptions import NFSeProviderError
from services.nfse.abrasf.rps_xml import NS_TIPOS, NS_ENVIO

_NS_DSIG = "http://www.w3.org/2000/09/xmldsig#"


def _strip_ws(el):
    """Remove whitespace ENTRE as tags (text/tail só-espaço → None).
    Manual ABRASF 4.2: 'não incluir caracteres de formatação (line-feed, tab, espaço entre TAGs)'.
    Preserva texto real (base64 do cert/assinatura, valores)."""
    if el.text is not None and not el.text.strip():
        el.text = None
    for ch in el:
        _strip_ws(ch)
    if el.tail is not None and not el.tail.strip():
        el.tail = None


def assinar_lote_rps(xml: str | bytes, key_pem: bytes, cert_pem: bytes,
                     sha: str = "sha1", namespace: str | None = None) -> str:
    """Assina o RPS e o Lote (ABRASF 1.0) via xmlsec. Retorna o XML assinado.
    `sha`/`namespace` mantidos por compat (ABRASF 1.0 usa RSA-SHA1)."""
    try:
        import xmlsec
    except ImportError as e:  # noqa: BLE001
        raise NFSeProviderError("xmlsec não instalado — assinatura ABRASF indisponível.") from e

    root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    xmlsec.tree.add_ids(root, ["Id"])   # registra o atributo Id p/ resolver as referências #Id

    key = xmlsec.Key.from_memory(key_pem, xmlsec.constants.KeyDataFormatPem)
    key.load_cert_from_memory(cert_pem, xmlsec.constants.KeyDataFormatPem)

    def _assinar(elem, ref_id, sig_id):
        sig = xmlsec.template.create(
            elem,
            xmlsec.constants.TransformInclC14N,    # CanonicalizationMethod (inclusivo)
            xmlsec.constants.TransformRsaSha1,     # SignatureMethod (RSA-SHA1)
            ns="ds",
        )
        sig.set("Id", sig_id)                       # XS02: Id obrigatório no <Signature>
        elem.append(sig)                            # Signature dentro do elemento assinado
        ref = xmlsec.template.add_reference(sig, xmlsec.constants.TransformSha1, uri=f"#{ref_id}")
        xmlsec.template.add_transform(ref, xmlsec.constants.TransformEnveloped)
        xmlsec.template.add_transform(ref, xmlsec.constants.TransformInclC14N)
        ki = xmlsec.template.ensure_key_info(sig)
        x509 = xmlsec.template.add_x509_data(ki)
        xmlsec.template.x509_data_add_certificate(x509)   # XS21: só X509Certificate
        # Manual 4.2: SEM whitespace entre as tags. Limpa o template ANTES de assinar
        # (p/ o SignedInfo ser canonizado/assinado JÁ sem formatação — não invalida depois).
        _strip_ws(sig)
        ctx = xmlsec.SignatureContext()
        ctx.key = key
        ctx.sign(sig)
        # Pós-assinatura: o base64 do SignatureValue/X509Certificate vem quebrado em linhas
        # (estão FORA do SignedInfo assinado → seguro colapsar p/ uma linha só).
        for tag in ("SignatureValue", "X509Certificate"):
            for node in sig.iter(f"{{{_NS_DSIG}}}{tag}"):
                if node.text:
                    node.text = "".join(node.text.split())

    # 1) cada RPS (InfRps); 2) o Lote por último (digest já inclui os RPS assinados)
    for rps in root.iter(f"{{{NS_TIPOS}}}Rps"):
        inf = rps.find(f"{{{NS_TIPOS}}}InfRps")
        rid = inf.get("Id") if inf is not None else None
        if rid:
            _assinar(rps, rid, f"sig_{rid}")

    lote = root.find(f"{{{NS_ENVIO}}}LoteRps")
    lid = lote.get("Id") if lote is not None else None
    if lid:
        _assinar(root, lid, f"sig_{lid}")

    return etree.tostring(root, encoding="UTF-8", xml_declaration=True).decode("utf-8")
