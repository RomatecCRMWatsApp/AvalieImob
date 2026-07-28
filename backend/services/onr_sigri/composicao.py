# @module services.onr_sigri.composicao — Composição do Dossiê de protocolo do ONR (SIG-RI).
#
# Espelha o motor de composição do Georref/Geo Urbano, mas as "peças" aqui são os
# ANEXOS do processo (documentos classificáveis) + duas peças fixas (Capa e Descrição
# do polígono). O RT escolhe um preset (por TIPO de anexo) ou liga/desliga anexo a
# anexo; o Dossiê consolidado (PDF) sai só com o que estiver LIGADO. É um filtro sobre
# os anexos existentes — a ORDEM segue a dos anexos (arrastável na tela).
#
# Modelo (retrocompatível): sem composição salva → tudo entra (capa + descrição + todos
# os anexos). Guardamos uma BLACKLIST (`anexos_off`) para que anexos NOVOS entrem por
# padrão.
from __future__ import annotations

from typing import List

# Presets — conjuntos de TIPOS de anexo (os rótulos de routes.onr_sigri.TIPOS_ANEXO).
_PRESET_PROTOCOLO = {
    "Certidão de Matrícula", "Escritura", "Documento Pessoal (RG/CPF/CNH)",
    "CND (Certidão Negativa)", "IPTU / BCI", "Mapa / Planta", "Memorial Descritivo",
    "ART / TRT", "Procuração",
}
_PRESET_SIMPLIFICADO = {
    "Certidão de Matrícula", "Mapa / Planta", "Memorial Descritivo", "ART / TRT",
}
PRESETS = ["COMPLETO", "PROTOCOLO", "SIMPLIFICADO", "PERSONALIZADO"]
PRESET_LABEL = {
    "COMPLETO": "Completo — capa + descrição + todos os anexos",
    "PROTOCOLO": "Protocolo no cartório — anexos essenciais",
    "SIMPLIFICADO": "Simplificado — matrícula, mapa, memorial e ART",
    "PERSONALIZADO": "Personalizado",
}


def _preset_tipos(preset: str):
    preset = (preset or "").upper()
    if preset == "PROTOCOLO":
        return _PRESET_PROTOCOLO
    if preset == "SIMPLIFICADO":
        return _PRESET_SIMPLIFICADO
    return None  # COMPLETO / PERSONALIZADO → sem filtro por tipo


def composicao_default() -> dict:
    return {"preset": "COMPLETO", "capa": True, "descricao_poligono": True, "anexos_off": []}


def _anexos_ordenados(job: dict) -> List[dict]:
    return sorted(list(job.get("anexos") or []), key=lambda a: a.get("ordem", 0))


def anexos_off_do_preset(job: dict, preset: str) -> List[str]:
    """Ids dos anexos que ficam DESLIGADOS ao aplicar um preset (por tipo)."""
    tipos = _preset_tipos(preset)
    if tipos is None:            # COMPLETO / PERSONALIZADO → nenhum desligado por tipo
        return []
    return [a.get("id") for a in _anexos_ordenados(job)
            if a.get("id") and (a.get("tipo") or "Outro") not in tipos]


def resolver_composicao(job: dict) -> dict:
    """Estado da composição p/ o preview do front: peças fixas + anexos {ligada}."""
    comp = job.get("composicao") or composicao_default()
    off = set(comp.get("anexos_off") or [])
    capa = comp.get("capa", True)
    descr = comp.get("descricao_poligono", True)
    tem_vertices = len(job.get("vertices") or []) >= 3
    anexos = [{
        "id": a.get("id"), "nome": a.get("nome") or a.get("filename"),
        "tipo": a.get("tipo") or "Outro", "ligada": a.get("id") not in off,
    } for a in _anexos_ordenados(job)]
    no_dossie = (1 if capa else 0) + (1 if descr else 0) + sum(1 for a in anexos if a["ligada"])
    return {
        "preset": comp.get("preset", "PERSONALIZADO"),
        "capa": bool(capa),
        "descricao_poligono": bool(descr),
        "descricao_habilitada": tem_vertices,   # descrição só faz sentido com poligonal
        "anexos": anexos,
        "total_no_dossie": no_dossie,
    }


def anexos_ligados(job: dict) -> List[dict]:
    """Anexos que EFETIVAMENTE entram no dossiê (ligados), na ordem."""
    comp = job.get("composicao") or {}
    off = set(comp.get("anexos_off") or [])
    return [a for a in _anexos_ordenados(job) if a.get("id") not in off]


def opcoes() -> dict:
    return {
        "presets": PRESETS,
        "preset_label": PRESET_LABEL,
        "pecas_fixas": [
            {"chave": "capa", "label": "Capa (identificação do imóvel)"},
            {"chave": "descricao_poligono", "label": "Descrição do polígono (memória descritiva)"},
        ],
    }
