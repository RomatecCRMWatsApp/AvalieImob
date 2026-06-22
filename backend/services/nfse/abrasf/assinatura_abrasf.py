# @module services.nfse.abrasf.assinatura_abrasf — Assinatura XMLDSIG do RPS/Lote (ABRASF).
"""ABRASF assina o RPS (referência = Id do InfRps, dentro de <Rps>) e o Lote (Id do LoteRps).
Ordem: assina cada RPS primeiro, depois o Lote (o digest do Lote já inclui o RPS assinado).
ABRASF 1.0 usa RSA-SHA1; 2.x pode usar SHA-256 (configurável). Import lazy de signxml.

⚠️ A POSIÇÃO exata da assinatura e o algoritmo variam por provedor (SpeedGov) — VALIDAR
contra o WSDL/manual antes de transmitir. Transmissão fica travada até lá.
"""
from __future__ import annotations

from lxml import etree

from services.nfse.exceptions import NFSeProviderError

NS_DEFAULT = "http://www.abrasf.org.br/nfse.xsd"


def assinar_lote_rps(xml: str | bytes, key_pem: bytes, cert_pem: bytes,
                     sha: str = "sha1", namespace: str = NS_DEFAULT) -> str:
    """Assina cada <Rps> (ref #InfRps.Id) e o <LoteRps> (ref #Id). Retorna o XML assinado."""
    try:
        from signxml import XMLSigner, methods
    except ImportError as e:  # noqa: BLE001
        raise NFSeProviderError("signxml não instalado — assinatura ABRASF indisponível.") from e

    sha = (sha or "sha1").lower()
    ns = namespace or NS_DEFAULT

    def _signer():
        return XMLSigner(
            method=methods.enveloped,
            signature_algorithm=f"rsa-{sha}",
            digest_algorithm=sha,
            c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
        )

    root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)

    # 1) assina cada RPS (Signature vai dentro de <Rps>, irmã de <InfRps>)
    for rps in list(root.iter(f"{{{ns}}}Rps")):
        inf = rps.find(f"{{{ns}}}InfRps")
        rid = inf.get("Id") if inf is not None else None
        signed_rps = _signer().sign(rps, key=key_pem, cert=cert_pem,
                                    reference_uri=(f"#{rid}" if rid else None))
        rps.getparent().replace(rps, signed_rps)

    # 2) assina o Lote (Signature ao fim do EnviarLoteRpsEnvio; digest já inclui o RPS assinado)
    lote = root.find(f"{{{ns}}}LoteRps")
    lid = lote.get("Id") if lote is not None else None
    signed_root = _signer().sign(root, key=key_pem, cert=cert_pem,
                                 reference_uri=(f"#{lid}" if lid else None))

    return etree.tostring(signed_root, encoding="UTF-8", xml_declaration=True).decode("utf-8")
