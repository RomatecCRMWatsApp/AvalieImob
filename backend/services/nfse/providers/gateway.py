# @module services.nfse.providers.gateway — Adapter intermediador REST (Focus NFe/PlugNotas/…).
# PR1: STUB seguro — NÃO transmite. A implementação real (httpx + mapeamento por gateway +
# webhook) entra no PR2, com credenciais e em HOMOLOGAÇÃO.
from __future__ import annotations

from services.nfse.providers.base import NFSeProvider
from services.nfse.exceptions import NFSeProviderError
from models.nfse import NFSeDocumento, ResultadoEmissao, ResultadoEvento

NOME = "gateway"


class GatewayProvider(NFSeProvider):
    async def emitir(self, doc: NFSeDocumento) -> ResultadoEmissao:
        raise NFSeProviderError("Adapter 'gateway' ainda não implementado (PR2). Emissão bloqueada.")

    async def consultar(self, chave_acesso: str) -> ResultadoEmissao:
        raise NFSeProviderError("Adapter 'gateway' ainda não implementado (PR2).")

    async def cancelar(self, chave_acesso: str, motivo: str) -> ResultadoEvento:
        raise NFSeProviderError("Adapter 'gateway' ainda não implementado (PR2).")

    async def baixar_danfse(self, chave_acesso: str) -> bytes:
        raise NFSeProviderError("Adapter 'gateway' ainda não implementado (PR2).")
