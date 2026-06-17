# @module services.pricing — Motor de precificação de Propostas de Consultoria (port da ZAYRA).
# Dispatcher + catálogo dos subtipos. Engines portados incrementalmente; subtipos
# ainda não portados aparecem como "em breve" no catálogo (não calculam).
from __future__ import annotations

from services.pricing.averbacao import calcular_averbacao
from services.pricing.retificacao import calcular_retificacao
from services.pricing.ptam import calcular_avaliacao_ptam
from services.pricing.georreferenciamento import calcular_georreferenciamento
from services.pricing.desmembramento import calcular_desmembramento
from services.pricing.demarcacao import calcular_demarcacao
from services.pricing.projeto_executivo import calcular_projeto_executivo

# Catálogo dos tipos de proposta de consultoria (espelha a ZAYRA).
# `disponivel=False` → aparece no card como "Em breve" (engine ainda não portado).
# `verificado=True` → card verde "✓ Configurado e testado" (engine com paridade verificada
# contra os testes da ZAYRA). `disponivel=False` → "Em breve".
CATALOGO_CONSULTORIA = [
    {"subtipo": "averbacao_residencial", "label": "Averbação Residencial", "icone": "Home", "disponivel": True, "verificado": True},
    {"subtipo": "averbacao_comercial", "label": "Averbação Comercial", "icone": "Store", "disponivel": True, "verificado": True},
    {"subtipo": "georreferenciamento_rural", "label": "Georreferenciamento Rural", "icone": "Compass", "disponivel": True, "verificado": True},
    {"subtipo": "demarcacao_urbana", "label": "Demarcação Urbana", "icone": "MapPin", "disponivel": True, "verificado": True},
    {"subtipo": "demarcacao_rural", "label": "Demarcação Rural", "icone": "TreePine", "disponivel": True, "verificado": True},
    {"subtipo": "desmembramento", "label": "Desmembramento", "icone": "Scissors", "disponivel": True, "verificado": True},
    {"subtipo": "remembramento", "label": "Remembramento", "icone": "Link2", "disponivel": True, "verificado": True},
    {"subtipo": "retificacao_area", "label": "Retificação de Área", "icone": "Ruler", "disponivel": True, "verificado": False},
    {"subtipo": "avaliacao_ptam", "label": "Avaliação PTAM", "icone": "Coins", "disponivel": True, "verificado": False},
    {"subtipo": "projeto_executivo", "label": "Projeto Executivo", "icone": "DraftingCompass", "disponivel": True, "verificado": False},
    {"subtipo": "desmembramento_obra", "label": "Desmembramento de Obra", "icone": "Layers", "disponivel": False, "verificado": False},
]

SUBTIPOS_DISPONIVEIS = {c["subtipo"] for c in CATALOGO_CONSULTORIA if c["disponivel"]}
SUBTIPO_LABEL = {c["subtipo"]: c["label"] for c in CATALOGO_CONSULTORIA}


def calcular_consultoria(subtipo: str, dados: dict) -> dict:
    """Dispatcher: retorna {custos, fontes}. Lança ValueError se subtipo não portado."""
    dados = dict(dados or {})
    if subtipo == "averbacao_residencial":
        dados["modalidade"] = "residencial"
        return calcular_averbacao(dados)
    if subtipo == "averbacao_comercial":
        dados["modalidade"] = "comercial"
        return calcular_averbacao(dados)
    if subtipo == "retificacao_area":
        return calcular_retificacao(dados)
    if subtipo == "avaliacao_ptam":
        return calcular_avaliacao_ptam(dados)
    if subtipo == "georreferenciamento_rural":
        return calcular_georreferenciamento(dados)
    if subtipo == "desmembramento":
        dados["tipo"] = "desmembramento"
        return calcular_desmembramento(dados)
    if subtipo == "remembramento":
        dados["tipo"] = "remembramento"
        return calcular_desmembramento(dados)
    if subtipo == "demarcacao_urbana":
        dados["subtipo"] = "demarcacao_urbana"
        return calcular_demarcacao(dados)
    if subtipo == "demarcacao_rural":
        dados["subtipo"] = "demarcacao_rural"
        return calcular_demarcacao(dados)
    if subtipo == "projeto_executivo":
        return calcular_projeto_executivo(dados)
    raise ValueError(
        f"O cálculo do tipo '{SUBTIPO_LABEL.get(subtipo, subtipo)}' ainda não está disponível "
        f"(em implementação). Tipos disponíveis: {', '.join(sorted(SUBTIPOS_DISPONIVEIS))}."
    )
