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


def montar_envelope_soap(operacao: str, xml_payload: str, namespace: str) -> str:
    """Envelope SOAP 1.1 ABRASF: o XML (EnviarLoteRpsEnvio assinado) vai como conteúdo da
    operação. ABRASF 1.0 costuma usar <cabecalho>+<xml> ou nfseCabecMsg/nfseDadosMsg —
    AJUSTAR ao WSDL do SpeedGov. Aqui: forma padrão `<Operacao><xml>...</xml></Operacao>`."""
    # remove a declaração <?xml ...?> do payload (não pode ir aninhada)
    corpo = xml_payload.split("?>", 1)[-1].strip() if xml_payload.lstrip().startswith("<?xml") else xml_payload
    return (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soap:Body>"
        f'<{operacao} xmlns="{namespace}">'
        f"<xml>{_escape_cdata(corpo)}</xml>"
        f"</{operacao}>"
        "</soap:Body></soap:Envelope>"
    )


def _escape_cdata(xml: str) -> str:
    # alguns webservices recebem o XML como string escapada; outros como CDATA. CDATA é o mais comum.
    return f"<![CDATA[{xml}]]>"


class AbrasfClient:
    """Cliente SOAP do webservice ABRASF. Use só sob transmissao_habilitada=True."""

    def __init__(self, url: str, ssl_context: ssl.SSLContext | None = None, timeout: float = 40.0):
        if not url:
            raise NFSeProviderError("ABRASF: url_ws do webservice não configurada.")
        self._url = url
        self._ctx = ssl_context
        self._timeout = timeout

    async def chamar(self, soap_action: str, envelope: str, namespace: str) -> str:
        """POST do envelope SOAP. Retorna o corpo da resposta (XML) pra parse posterior."""
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f"{namespace}/{soap_action}" if namespace else soap_action,
        }
        verify = self._ctx if self._ctx is not None else True
        async with httpx.AsyncClient(verify=verify, timeout=self._timeout) as client:
            resp = await client.post(self._url, content=envelope.encode("utf-8"), headers=headers)
            resp.raise_for_status()
            return resp.text
