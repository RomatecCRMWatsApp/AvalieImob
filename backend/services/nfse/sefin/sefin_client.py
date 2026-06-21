# @module services.nfse.sefin.sefin_client — Cliente mTLS (httpx) para a Sefin Nacional.
"""Transporte mútuo-TLS: o certificado ICP-Brasil do prestador autentica a conexão.

SEGURANÇA: este cliente NÃO é chamado enquanto `nfse_config.sefin.transmissao_habilitada`
for False (default). Mesmo habilitado, as ROTAS/payload devem casar com o Swagger oficial
de contribuintes ISSQN (notanacional). Nada transmite em testes.
"""
from __future__ import annotations

import logging
import os
import ssl
import tempfile

import httpx

from services.nfse.exceptions import NFSeProviderError

logger = logging.getLogger("romatec")


def montar_ssl_context(key_pem: bytes, cert_pem: bytes, chain_pem: bytes = b"") -> ssl.SSLContext:
    """Cria um SSLContext com o certificado de CLIENTE (mTLS) a partir dos PEM em memória.
    O `load_cert_chain` do stdlib exige arquivo → grava um PEM temporário restrito e o remove."""
    ctx = ssl.create_default_context()
    combinado = cert_pem + (chain_pem or b"") + b"\n" + key_pem
    fd, caminho = tempfile.mkstemp(suffix=".pem")
    try:
        os.write(fd, combinado)
        os.close(fd)
        try:
            os.chmod(caminho, 0o600)
        except OSError:
            pass
        ctx.load_cert_chain(certfile=caminho)
    finally:
        try:
            os.remove(caminho)   # remove o material sensível do disco imediatamente
        except OSError:
            pass
    return ctx


class SefinClient:
    """Cliente mTLS da Sefin. Use sob `transmissao_habilitada=True` (pós-homologação)."""

    def __init__(self, base_url: str, ssl_context: ssl.SSLContext, timeout: float = 30.0):
        if not base_url:
            raise NFSeProviderError("Sefin: base_url não configurada.")
        self._base = base_url.rstrip("/")
        self._ctx = ssl_context
        self._timeout = timeout

    async def transmitir_dps(self, rota: str, payload_b64: str) -> dict:
        """POST do DPS (XML assinado, GZip+Base64) ao endpoint de emissão da Sefin."""
        url = f"{self._base}{rota}"
        async with httpx.AsyncClient(verify=self._ctx, timeout=self._timeout) as client:
            resp = await client.post(url, json={"dpsXmlGZipB64": payload_b64},
                                     headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            return resp.json()

    async def consultar(self, rota: str, chave_acesso: str) -> dict:
        url = f"{self._base}{rota}/{chave_acesso}"
        async with httpx.AsyncClient(verify=self._ctx, timeout=self._timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
