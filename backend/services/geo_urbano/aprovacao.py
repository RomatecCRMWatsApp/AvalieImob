# @module services.geo_urbano.aprovacao — fluxo de Aprovação & Assinaturas (Addendum).
#
# Matriz de assinaturas (quem assina o quê, por qual meio/papel) + derivação do
# status geral do fluxo a partir do estado `projeto.aprovacao`. A COLETA real das
# assinaturas (técnico ICP / proprietário WhatsApp) é de um increment posterior;
# aqui montamos o esqueleto: papéis nos campos, máquina de status e a matriz §1.
from __future__ import annotations

from typing import List

# Papel → meio padrão de coleta (Addendum §1).
METODO_PAPEL = {
    "proprietario": "whatsapp_desenhada",      # ou govbr/cert_digital (gancho futuro)
    "tecnico": "tecnico_sistema",              # ICP/e-CPF no sistema
    "superintendente": "aprovacao_superintendencia",  # carimbo/assinatura do órgão
}

# Matriz: cada documento gerado, os papéis que o assinam, e se há carimbo.
MATRIZ_ASSINATURAS: List[dict] = [
    {"documento": "requerimento_cartorio", "label": "Requerimento — Via Cartório",
     "papeis": ["proprietario"], "carimbo": []},
    {"documento": "requerimento_superintendencia", "label": "Requerimento — Via Superintendência",
     "papeis": ["proprietario"], "carimbo": []},
    {"documento": "art_trt", "label": "ART / TRT", "papeis": ["proprietario"], "carimbo": []},
    {"documento": "memorial_descritivo", "label": "Memorial Descritivo",
     "papeis": ["tecnico", "superintendente"], "carimbo": ["superintendente"]},
    {"documento": "mapa", "label": "Mapa", "papeis": ["tecnico", "superintendente"],
     "carimbo": ["superintendente"]},
]

PAPEL_LABEL = {"proprietario": "Proprietário", "tecnico": "Técnico",
               "superintendente": "Superintendência"}


def status_geral(aprov: dict) -> str:
    """Deriva o status geral do fluxo (Addendum §2.2/§3)."""
    aprov = aprov or {}
    s = aprov.get("superintendencia") or {}
    if s.get("oficio_emitido"):
        return "oficio_emitido"
    if s.get("memorial_aprovado") and s.get("mapa_aprovado"):
        return "aprovado"
    if aprov.get("enviado_superintendencia"):
        return "enviado_superintendencia"
    if (aprov.get("tecnico") or {}).get("assinado"):
        return "assinatura_tecnico"
    if any((p.get("requerimento") or p.get("art_trt")) for p in (aprov.get("proprietarios") or [])):
        return "assinatura_partes"
    return "rascunho"


def _status_proprietario(aprov: dict, documento: str) -> str:
    props = aprov.get("proprietarios") or []
    if not props:
        return "pendente"
    campo = "art_trt" if documento == "art_trt" else "requerimento"
    feitos = sum(1 for p in props if p.get(campo))
    if feitos == 0:
        return "pendente"
    return "assinado" if feitos == len(props) else "parcial"


def _status_celula(aprov: dict, documento: str, papel: str) -> str:
    if papel == "proprietario":
        return _status_proprietario(aprov, documento)
    if papel == "tecnico":
        return "assinado" if (aprov.get("tecnico") or {}).get("assinado") else "pendente"
    if papel == "superintendente":
        s = aprov.get("superintendencia") or {}
        chave = "memorial_aprovado" if documento == "memorial_descritivo" else "mapa_aprovado"
        return "aprovado" if s.get(chave) else "pendente"
    return "pendente"


def build_status(projeto: dict) -> dict:
    """Matriz §1 + status geral. O Ofício é EXPEDIDO pela Superintendência (órgão
    externo) e devolvido por UPLOAD (`oficio_assinado`) — não é emitido pelo sistema."""
    aprov = projeto.get("aprovacao") or {}
    oficio_anexado = bool((projeto.get("uploads") or {}).get("oficio_assinado"))
    linhas = []
    for row in MATRIZ_ASSINATURAS:
        celulas = {}
        for papel in row["papeis"]:
            celulas[papel] = {
                "status": _status_celula(aprov, row["documento"], papel),
                "metodo": METODO_PAPEL.get(papel),
                "carimbo": papel in (row.get("carimbo") or []),
                "label": PAPEL_LABEL.get(papel, papel),
            }
        linhas.append({"documento": row["documento"], "label": row["label"],
                       "papeis": row["papeis"], "celulas": celulas})
    geral = "oficio_emitido" if oficio_anexado else status_geral(aprov)
    sup = (aprov.get("superintendencia") or {})
    return {
        "status_geral": geral,
        "matriz": linhas,
        "superintendencia": {
            "enviado": bool(aprov.get("enviado_superintendencia")),
            "memorial_aprovado": bool(sup.get("memorial_aprovado")),
            "mapa_aprovado": bool(sup.get("mapa_aprovado")),
            "oficio_anexado": oficio_anexado,
            "responsavel": (projeto.get("superintendencia") or {}).get("responsavel"),
            "portaria": (projeto.get("superintendencia") or {}).get("portaria"),
        },
    }
