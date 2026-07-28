"""Composição do dossiê do Georreferenciamento RURAL (SIGEF/INCRA).

Espelha o motor de composição do Geo Urbano (services/geo_urbano/georref_urbano.py):
o RT liga/desliga peças e escolhe um preset; o dossiê sai só com as peças LIGADAS
(e que tenham insumo). É um filtro sobre a ORDEM_DOSSIE existente
(services/georef/generators/dossie.py) — a ordem no PDF continua a canônica; a
composição só controla o ON/OFF de cada peça (retrocompatível: sem composição,
tudo entra, como sempre).
"""
from __future__ import annotations

from typing import List, Optional, Tuple

# Peças do dossiê (mesma ordem/chaves de dossie.ORDEM_DOSSIE). capa/sumário são
# montados pelo próprio gerar_dossie (não são peças alternáveis).
PECAS = [
    "requerimento", "laudo_tecnico", "memorial", "drl", "drl_unificada",
    "mapa", "art_trt", "certidao_matricula", "ccir", "car", "cnd_itr", "itr",
    "memorial_sigef", "doc_cliente",
]
PECA_LABEL = {
    "requerimento": "Requerimento",
    "laudo_tecnico": "Laudo Técnico de Agrimensura",
    "memorial": "Memorial Descritivo (gerado)",
    "drl": "DRL — Reconhecimento de Limites (por confrontante)",
    "drl_unificada": "DRL Unificada (RT + proprietário)",
    "mapa": "Mapa / Planta SIGEF",
    "art_trt": "ART / TRT",
    "certidao_matricula": "Certidão de Inteiro Teor da Matrícula",
    "ccir": "CCIR",
    "car": "CAR — Cadastro Ambiental Rural",
    "cnd_itr": "CND ITR",
    "itr": "ITR — Imposto Territorial Rural",
    "memorial_sigef": "Memorial Descritivo SIGEF (original)",
    "doc_cliente": "Documentos do Proprietário",
}

# Presets. COMPLETO = tudo; PROTOCOLO = o essencial p/ protocolo no cartório;
# SIMPLIFICADO = mínimo. PERSONALIZADO = toggles manuais.
_PRESET_PROTOCOLO = {
    "requerimento", "laudo_tecnico", "memorial", "drl", "drl_unificada",
    "mapa", "art_trt", "certidao_matricula",
}
_PRESET_SIMPLIFICADO = {"requerimento", "memorial", "mapa", "art_trt"}
PRESETS = ["COMPLETO", "PROTOCOLO", "SIMPLIFICADO", "PERSONALIZADO"]


def preset_pecas(preset: str) -> dict:
    """{chave: bool} de um preset. COMPLETO/PERSONALIZADO = base tudo ligado
    (a habilitação por insumo é aplicada depois em resolver_composicao)."""
    preset = (preset or "").upper()
    if preset == "PROTOCOLO":
        ligadas = _PRESET_PROTOCOLO
    elif preset == "SIMPLIFICADO":
        ligadas = _PRESET_SIMPLIFICADO
    else:  # COMPLETO / PERSONALIZADO
        ligadas = set(PECAS)
    return {p: (p in ligadas) for p in PECAS}


def composicao_default() -> dict:
    return {"preset": "COMPLETO", "pecas": preset_pecas("COMPLETO"), "ordem": list(PECAS)}


def _uploads(doc: dict) -> dict:
    return doc.get("uploads") or {}


def _tem_upload(doc: dict, tipo: str) -> bool:
    v = _uploads(doc).get(tipo)
    return bool(v)


def _insumo_status(doc: dict, peca: str) -> Tuple[bool, Optional[str]]:
    """(habilitada, motivo_se_bloqueada). Peça sem insumo → desabilitada c/ tooltip.
    As chaves de upload seguem o mapeamento de _montar_dossie (routes/georef)."""
    if peca in ("requerimento", "laudo_tecnico", "memorial"):
        return True, None  # sempre geradas
    if peca == "drl":
        return bool(doc.get("confrontantes")), "sem confrontantes cadastrados para a DRL"
    if peca == "drl_unificada":
        ok = doc.get("tipo_servico") in ("desmembramento", "remembramento")
        return ok, "só para desmembramento / remembramento"
    if peca == "art_trt":
        return _tem_upload(doc, "art_trt"), "anexe a ART/TRT"
    if peca == "mapa":
        return _tem_upload(doc, "mapa"), "anexe o mapa / planta SIGEF"
    if peca == "certidao_matricula":
        return _tem_upload(doc, "certidao"), "anexe a certidão de matrícula"
    if peca == "ccir":
        return _tem_upload(doc, "ccir"), "anexe o CCIR"
    if peca == "car":
        return _tem_upload(doc, "car"), "anexe o CAR"
    if peca == "cnd_itr":
        return _tem_upload(doc, "cnd_itr"), "anexe a CND ITR"
    if peca == "itr":
        return _tem_upload(doc, "itr"), "anexe o(s) ITR"
    if peca == "memorial_sigef":
        return _tem_upload(doc, "memorial"), "anexe o memorial SIGEF original"
    if peca == "doc_cliente":
        return _tem_upload(doc, "doc_cliente"), "anexe os documentos do proprietário"
    return True, None


def pecas_ligadas(doc: dict) -> dict:
    """{chave: bool} — só o toggle (independe de insumo). Sem composição → tudo True
    (retrocompatível: dossiê inalterado)."""
    comp = doc.get("composicao") or {}
    ligadas = comp.get("pecas") or {}
    if not ligadas:
        return {p: True for p in PECAS}
    return {p: bool(ligadas.get(p, True)) for p in PECAS}


def resolver_composicao(doc: dict) -> dict:
    """Resolve a composição p/ o preview do front: por peça {ligada, habilitada,
    motivo, no_pdf} + preset. Não altera a ordem do PDF (a ordem é a canônica)."""
    comp = doc.get("composicao") or composicao_default()
    ligadas = comp.get("pecas") or {}
    sem_comp = not ligadas
    itens = []
    for p in PECAS:
        hab, motivo = _insumo_status(doc, p)
        lig = True if sem_comp else bool(ligadas.get(p, True))
        no_pdf = lig and hab
        itens.append({
            "chave": p, "label": PECA_LABEL[p], "ligada": lig,
            "habilitada": hab, "motivo": None if hab else motivo, "no_pdf": no_pdf,
        })
    return {
        "preset": comp.get("preset", "PERSONALIZADO"),
        "pecas": itens,
        "ordem": list(PECAS),
    }


def opcoes() -> dict:
    """Catálogo estático p/ o picker de composição do Georref-rural."""
    return {
        "presets": PRESETS,
        "pecas": [{"chave": p, "label": PECA_LABEL[p]} for p in PECAS],
    }
