# @module services.nfse.providers.factory — Resolve o provider a partir do NFSeConfig.
from __future__ import annotations

from models.nfse import NFSeConfig, Provider
from services.nfse.providers.base import NFSeProvider
from services.nfse.providers.gateway import GatewayProvider
from services.nfse.providers.sefin_nacional import SefinNacionalProvider
from services.nfse.exceptions import NFSeConfigError


def get_provider(config: NFSeConfig) -> NFSeProvider:
    prov = config.provider
    if prov in (Provider.gateway, "gateway"):
        return GatewayProvider(config)
    if prov in (Provider.sefin_nacional, "sefin_nacional"):
        return SefinNacionalProvider(config)
    raise NFSeConfigError(f"Provider desconhecido: {prov}")
