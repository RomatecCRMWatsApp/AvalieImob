# @module services.nfse.abrasf.soap_client — Cliente SOAP do webservice ABRASF (municipal).
"""Envia o `EnviarLoteRpsEnvio` (já assinado) dentro de um envelope SOAP ao webservice do
município/provedor (ex.: SpeedGov/Açailândia). mTLS com o e-CNPJ (reusa o SSLContext do Sefin).

SEGURANÇA: só é chamado quando `abrasf.transmissao_habilitada=True` (default False). O
envelope/SOAPAction/estrutura de resposta DEVEM casar com o WSDL do SpeedGov — VALIDAR antes.
"""
from __future__ import annotations

import logging
import ssl

import httpx

from services.nfse.exceptions import NFSeProviderError

logger = logging.getLogger("romatec")


def _sem_decl(xml: str) -> str:
    """Remove a declaração <?xml ...?> (não pode ir aninhada dentro de outro XML)."""
    return xml.split("?>", 1)[-1].strip() if xml.lstrip().startswith("<?xml") else xml


def _cdata(xml: str) -> str:
    return f"<![CDATA[{_sem_decl(xml)}]]>"


def montar_envelope_soap(operacao: str, header_xml: str, rps_xml: str, namespace_ws: str) -> str:
    """Envelope SOAP 1.1 — operação `RecepcionarLoteRps` com 2 parâmetros STRING (confirmado no
    XSD do SpeedGov): `header` (cabeçalho) e `parameters` (EnviarLoteRpsEnvio assinado), em CDATA."""
    return (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soap:Body>"
        f'<{operacao} xmlns="{namespace_ws}">'
        f"<header>{_cdata(header_xml)}</header>"
        f"<parameters>{_cdata(rps_xml)}</parameters>"
        f"</{operacao}>"
        "</soap:Body></soap:Envelope>"
    )


class AbrasfClient:
    """Cliente SOAP do webservice ABRASF. Use só sob transmissao_habilitada=True."""

    def __init__(self, url: str, ssl_context: ssl.SSLContext | None = None, timeout: float = 40.0):
        if not url:
            raise NFSeProviderError("ABRASF: url_ws do webservice não configurada.")
        self._url = url
        self._ctx = ssl_context
        self._timeout = timeout

    async def chamar(self, soap_action: str, envelope: str) -> str:
        """POST do envelope SOAP. Retorna o corpo da resposta (XML) pra parse posterior.
        WSDL do SpeedGov: SOAPAction VAZIO (soap_action="")."""
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": soap_action or "",
        }
        verify = self._ctx if self._ctx is not None else True
        async with httpx.AsyncClient(verify=verify, timeout=self._timeout) as client:
            resp = await client.post(self._url, content=envelope.encode("utf-8"), headers=headers)
            resp.raise_for_status()
            return resp.text
