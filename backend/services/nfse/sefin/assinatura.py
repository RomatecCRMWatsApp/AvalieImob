# @module services.nfse.sefin.assinatura — Assinatura XMLDSIG da DPS (enveloped, RSA-SHA256).
# Usa signxml (dep do requirements). Import LAZY: o módulo importa mesmo sem signxml;
# a função levanta erro claro se a lib não estiver disponível.
from __future__ import annotations

from lxml import etree

from services.nfse.exceptions import NFSeProviderError

NS = "http://www.sped.fazenda.gov.br/nfse"


def assinar_dps(xml: str | bytes, key_pem: bytes, cert_pem: bytes) -> str:
    """Assina a DPS (referência = Id do infDPS) com XMLDSIG enveloped. Retorna o XML assinado."""
    try:
        from signxml import XMLSigner, methods
    except ImportError as e:  # noqa: BLE001
        raise NFSeProviderError("signxml não instalado — assinatura XMLDSIG indisponível.") from e

    root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    inf = root.find(f"{{{NS}}}infDPS")
    ref_id = inf.get("Id") if inf is not None else None

    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
    )
    signed = signer.sign(root, key=key_pem, cert=cert_pem,
                         reference_uri=(f"#{ref_id}" if ref_id else None))
    return etree.tostring(signed, encoding="UTF-8", xml_declaration=True).decode("utf-8")
