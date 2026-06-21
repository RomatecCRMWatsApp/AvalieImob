# @module services.nfse.providers.base — Interface (ABC) do provider de NFS-e.
# Regra: o `service.py` orquestra; o provider só sabe TRANSMITIR (gateway OU Sefin direto).
from __future__ import annotations

from abc import ABC, abstractmethod

from models.nfse import NFSeConfig, NFSeDocumento, ResultadoEmissao, ResultadoEvento


class NFSeProvider(ABC):
    """Contrato comum dos adapters de emissão. Os concretos (gateway/sefin) implementam."""

    def __init__(self, config: NFSeConfig):
        self.config = config

    @abstractmethod
    async def emitir(self, doc: NFSeDocumento) -> ResultadoEmissao:
        """Monta a DPS, transmite e devolve status/chave/xml/pdf ou rejeição."""

    @abstractmethod
    async def consultar(self, chave_acesso: str) -> ResultadoEmissao:
        """Consulta a situação da NFS-e pela chave de acesso (50 chars)."""

    @abstractmethod
    async def cancelar(self, chave_acesso: str, motivo: str) -> ResultadoEvento:
        """Registra evento de cancelamento."""

    @abstractmethod
    async def baixar_danfse(self, chave_acesso: str) -> bytes:
        """Retorna o PDF do DANFSe (pode delegar ao gerador próprio do AvalieImob)."""
