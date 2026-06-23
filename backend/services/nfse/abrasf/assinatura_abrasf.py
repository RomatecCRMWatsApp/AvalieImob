# @module services.nfse.abrasf.assinatura_abrasf — Assinatura XMLDSIG do RPS/Lote (ABRASF SpeedGov).
"""Assina cada `<Rps>` (referência = Id do InfRps, ns tipos) e o `<LoteRps>` (Id, ns envio).
Ordem: assina cada RPS primeiro, depois o Lote. ABRASF 1.0 usa RSA-SHA1. Import lazy de signxml.
"""
from __future__ import annotations

from lxml import etree

from services.nfse.exceptions import NFSeProviderError
from services.nfse.abrasf.rps_xml import NS_TIPOS, NS_ENVIO


def assinar_lote_rps(xml: str | bytes, key_pem: bytes, cert_pem: bytes,
                     sha: str = "sha1", namespace: str | None = None) -> str:
    """Assina cada <Rps> (ref #InfRps.Id) e o <LoteRps> (ref #Id). Retorna o XML assinado.
    `namespace` é ignorado (mantido por compat — usa os ns oficiais do SpeedGov)."""
    try:
        from signxml import XMLSigner, methods
    except ImportError as e:  # noqa: BLE001
        raise NFSeProviderError("signxml não instalado — assinatura ABRASF indisponível.") from e

    sha = (sha or "sha1").lower()
    # ABRASF 1.0 EXIGE RSA-SHA1; o signxml bloqueia SHA1 por padrão (check_deprecated_methods).
    # Subclasse que NEUTRALIZA esse bloqueio (o município valida exatamente assim).

    class _AbrasfSigner(XMLSigner):
        def check_deprecated_methods(self):  # noqa: D401 - intencional: permite SHA1 p/ ABRASF
            return None

    def _signer():
        return _AbrasfSigner(
            method=methods.enveloped,
            signature_algorithm=f"rsa-{sha}",
            digest_algorithm=sha,
            # ABRASF 1.0 usa C14N INCLUSIVO (REC-xml-c14n-20010315)
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        )

    SIG = "{http://www.w3.org/2000/09/xmldsig#}Signature"
    root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)

    # IDs dos RPS a assinar (cada InfRps). Assina-se SOBRE O DOCUMENTO INTEIRO (digest no contexto
    # real de namespaces) e move-se a <Signature> p/ dentro do <Rps> correspondente.
    ids_rps = [inf.get("Id") for inf in root.iter(f"{{{NS_TIPOS}}}InfRps") if inf.get("Id")]
    for rid in ids_rps:
        signed = _signer().sign(root, key=key_pem, cert=cert_pem, reference_uri=f"#{rid}")
        sig = signed[-1]                              # a Signature recém-anexada (último filho)
        # acha o <Rps> cujo <InfRps> tem esse Id e move a assinatura p/ dentro dele
        for rps in signed.iter(f"{{{NS_TIPOS}}}Rps"):
            inf = rps.find(f"{{{NS_TIPOS}}}InfRps")
            if inf is not None and inf.get("Id") == rid:
                rps.append(sig)
                break
        root = signed

    # Assina o Lote por último (digest do LoteRps já inclui os RPS assinados); fica ao fim do root.
    lote = root.find(f"{{{NS_ENVIO}}}LoteRps")
    lid = lote.get("Id") if lote is not None else None
    if lid:
        root = _signer().sign(root, key=key_pem, cert=cert_pem, reference_uri=f"#{lid}")

    return etree.tostring(root, encoding="UTF-8", xml_declaration=True).decode("utf-8")
