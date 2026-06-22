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


def montar_envelope_soap(operacao: str, header_xml: str, rps_xml: str, namespace_ws: str) -> str:
    """Envelope SOAP IDÊNTICO ao modelo oficial do SpeedGov (modelos_xml): `header`/`parameters`
    são strings ESCAPADAS (NÃO CDATA), COM a declaração `<?xml?>`; wrapper `nfse:Operacao`
    (prefixo) e header/parameters UNqualified."""
    from xml.sax.saxutils import escape
    return (
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        f'xmlns:nfse="{namespace_ws}">'
        "<soapenv:Header/>"
        "<soapenv:Body>"
        f"<nfse:{operacao}>"
        f"<header>{escape(header_xml)}</header>"
        f"<parameters>{escape(rps_xml)}</parameters>"
        f"</nfse:{operacao}>"
        "</soapenv:Body></soapenv:Envelope>"
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
