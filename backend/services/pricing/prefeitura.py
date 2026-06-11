# @module services.pricing.prefeitura — Taxas da Prefeitura de Açailândia (port da ZAYRA).
# Valores em params.PREFEITURA_ACAILANDIA; quando None → pendente ("A confirmar").
from __future__ import annotations

from services.pricing.params import PREFEITURA_ACAILANDIA

_OBS = "A confirmar com a Prefeitura de Acailandia (Secretaria de Obras)."


def _taxa(valor, rotulo: str) -> dict:
    return {"valor": valor, "pendente": valor is None, "rotulo": rotulo,
            "observacao_pdf": _OBS if valor is None else ""}


def taxa_habite_se() -> dict:
    return _taxa(PREFEITURA_ACAILANDIA["habite_se"], "Taxa de Habite-se — Prefeitura Acailandia")


def taxa_alvara_construcao() -> dict:
    return _taxa(PREFEITURA_ACAILANDIA["alvara_construcao"], "Alvara de Construcao — Prefeitura Acailandia")


def taxa_aprovacao_desmembramento() -> dict:
    return _taxa(PREFEITURA_ACAILANDIA["aprovacao_desmembramento"], "Aprovacao de Desmembramento — Prefeitura Acailandia")
