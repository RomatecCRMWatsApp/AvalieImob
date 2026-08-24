# @module services.inferencia.vinculo_ptam — liga o modelo homologado ao PTAM.
#
# O laudo passa a tirar o valor da REGRESSÃO em vez do tratamento por fatores.
# Duas regras duras:
#   1. só modelo HOMOLOGADO entra num laudo (rascunho/estimado não);
#   2. o snapshot é CONGELADO no vínculo — versionar o modelo depois não altera
#      o laudo já emitido (ADR-018).
import copy
from datetime import datetime
from typing import Optional


class VinculoError(Exception):
    """Regra de negócio do vínculo modelo ↔ PTAM."""


CAMPOS_SNAPSHOT = ("resultado", "enquadramento", "graficos", "especificacao",
                   "avaliando", "area_total_avaliando", "amostra", "nome",
                   "versao", "norma", "tipo_imovel", "homologado_em", "id")


def montar_snapshot(modelo: dict) -> dict:
    """Cópia imutável do que o laudo precisa — não guarda referência viva.

    deepcopy é essencial: com cópia rasa, `resultado`/`enquadramento` continuariam
    sendo o MESMO objeto do modelo e uma alteração posterior nele mudaria o laudo
    já emitido — exatamente o que a imutabilidade existe para impedir.
    """
    snap = {c: copy.deepcopy(modelo.get(c)) for c in CAMPOS_SNAPSHOT}
    snap["modelo_id"] = modelo.get("id")
    snap["congelado_em"] = datetime.utcnow().isoformat()
    return snap


def valores_para_o_laudo(modelo: dict) -> dict:
    """Campos do PTAM que passam a vir da regressão (Seções 6, 8.2 e 9)."""
    r = modelo.get("resultado") or {}
    pred = r.get("predicao") or {}
    enq = modelo.get("enquadramento") or r.get("enquadramento") or {}
    total = pred.get("total") or {}

    unitario = float(pred.get("valor_central") or 0)
    vtotal = float(total.get("valor_central") or 0)
    if not vtotal:
        area = float(modelo.get("area_total_avaliando") or 0)
        vtotal = unitario * area if area else unitario

    # O intervalo do laudo é o IP 80% — é ele que define o Grau de Precisão.
    ip = pred.get("ip80") or {}
    inf = float(ip.get("inferior") or 0)
    sup = float(ip.get("superior") or 0)
    if total.get("ip80"):
        inf = float(total["ip80"].get("inferior") or inf)
        sup = float(total["ip80"].get("superior") or sup)

    grau_f = enq.get("grau_fundamentacao") or ""
    grau_p = enq.get("grau_precisao") or ""
    return {
        "methodology": ("Método Comparativo Direto de Dados de Mercado — "
                        "tratamento científico por inferência estatística"),
        "resultado_valor_unitario": round(unitario, 2),
        "resultado_valor_total": round(vtotal, 2),
        "total_indemnity": round(vtotal, 2),
        "resultado_intervalo_inf": round(inf, 2),
        "resultado_intervalo_sup": round(sup, 2),
        "calc_grau_fundamentacao": f"Grau {grau_f}" if grau_f else "",
        "fundamentacao_grau": f"Grau {grau_f}" if grau_f else "",
        "grau_precisao": f"Grau {grau_p}" if grau_p else "",
        "precisao_grau": f"Grau {grau_p}" if grau_p else "",
    }


def preparar(modelo: Optional[dict], ptam: dict) -> dict:
    """Valida e devolve o `$set` do PTAM. Levanta VinculoError com o motivo."""
    if not modelo:
        raise VinculoError("Modelo de inferência não encontrado.")
    if modelo.get("status") != "homologado":
        raise VinculoError(
            "Só modelo HOMOLOGADO pode alimentar um laudo. "
            "Estime, confira o enquadramento e homologue antes de vincular.")
    if not (modelo.get("resultado") or {}).get("predicao"):
        raise VinculoError("Modelo homologado sem resultado — reestime o modelo.")
    if ptam.get("locked") or ptam.get("assinado"):
        raise VinculoError("Laudo já assinado/lacrado: não é possível trocar o método.")

    campos = valores_para_o_laudo(modelo)
    campos.update({
        "inferencia_modelo_id": modelo.get("id"),
        "inferencia_snapshot": montar_snapshot(modelo),
        "inferencia_vinculado_em": datetime.utcnow(),
        "metodo_avaliacao": "comparativo_inferencia",
    })
    return campos


def desvincular_campos() -> dict:
    """Volta o laudo ao tratamento por fatores (os valores voltam a ser do wizard)."""
    return {"inferencia_modelo_id": None, "inferencia_snapshot": None,
            "inferencia_vinculado_em": None, "metodo_avaliacao": None}
