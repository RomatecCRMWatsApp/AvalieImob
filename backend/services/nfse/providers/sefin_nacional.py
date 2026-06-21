# @module services.nfse.providers.sefin_nacional — Adapter direto Sefin Nacional.
# PR1: STUB seguro — NÃO transmite. Implementação real (mTLS + XMLDSIG + GZip/Base64 +
# grupo IBS/CBS) entra no PR6, com certificado ICP-Brasil e em HOMOLOGAÇÃO.
from __future__ import annotations

from services.nfse.providers.base import NFSeProvider
from services.nfse.exceptions import NFSeProviderError
from models.nfse import NFSeDocumento, ResultadoEmissao, ResultadoEvento

NOME = "sefin_nacional"


class SefinNacionalProvider(NFSeProvider):
    async def emitir(self, doc: NFSeDocumento) -> ResultadoEmissao:
        raise NFSeProviderError("Adapter 'sefin_nacional' ainda não implementado (PR6). Emissão bloqueada.")

    async def consultar(self, chave_acesso: str) -> ResultadoEmissao:
        raise NFSeProviderError("Adapter 'sefin_nacional' ainda não implementado (PR6).")

    async def cancelar(self, chave_acesso: str, motivo: str) -> ResultadoEvento:
        raise NFSeProviderError("Adapter 'sefin_nacional' ainda não implementado (PR6).")

    async def baixar_danfse(self, chave_acesso: str) -> bytes:
        raise NFSeProviderError("Adapter 'sefin_nacional' ainda não implementado (PR6).")
