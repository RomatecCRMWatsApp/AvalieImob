# @module services.geo_urbano.reconcile — reconciliação matrícula ↔ BCI ↔ IPTU.
#
# Cruza titularidade, área e localização cartográfica entre a certidão de inteiro
# teor (matrícula) e o Boletim de Cadastro Imobiliário (BCI) municipal, e a
# regularidade fiscal (CND/guia paga) de cada matrícula. Divergências viram
# ALERTAS exibidos na Conferência (bloqueantes para o protocolo).
from __future__ import annotations

import re
from typing import List, Optional

TOLERANCIA_AREA_M2 = 0.5  # diferença aceitável matrícula × BCI


def _so_digitos(v: Optional[str]) -> str:
    return re.sub(r"\D", "", v or "")


def _bci_por_cod(bci_list: List[dict]) -> dict:
    idx = {}
    for b in bci_list or []:
        chave = _so_digitos(b.get("cod_imovel")) or (b.get("loc_cartografica") or "")
        if chave:
            idx[chave] = b
    return idx


def _bci_da_matricula(mat: dict, idx_cod: dict, bci_list: List[dict]) -> Optional[dict]:
    # 1) por matricula_id explícito
    if mat.get("id"):
        for b in bci_list or []:
            if b.get("matricula_id") == mat["id"]:
                return b
    # 2) por cod_imovel / loc_cartografica
    chave = _so_digitos(mat.get("cod_imovel")) or (mat.get("loc_cartografica") or "")
    return idx_cod.get(chave)


def reconciliar(projeto: dict) -> dict:
    """Retorna {alertas: [...], resumo: {...}}. Cada alerta tem tipo/severidade/mensagem."""
    matriculas = projeto.get("matriculas") or []
    bci_list = projeto.get("bci") or []
    iptu_list = projeto.get("iptu") or []
    idx_cod = _bci_por_cod(bci_list)
    iptu_por_mat = {i.get("matricula_id"): i for i in iptu_list if i.get("matricula_id")}

    alertas: List[dict] = []
    # Imóvel ÚNICO (usucapião): há 1 matrícula → o (único) BCI e o (único) IPTU/CND são
    # DELA, ainda que o OCR da certidão não tenha trazido o cod. imóvel p/ casar.
    unica = len(matriculas) == 1
    # Na usucapião a titularidade DIVERGE por definição (o possuidor não é o titular
    # registral) — logo é ALERTA informativo, não bloqueante.
    is_usucapiao = projeto.get("tipo_servico") == "usucapiao"

    def add(tipo, severidade, mensagem, matricula=None, acao=None):
        alertas.append({"tipo": tipo, "severidade": severidade, "mensagem": mensagem,
                        "matricula": matricula, "acao_sugerida": acao})

    for mat in matriculas:
        rotulo = mat.get("matricula") or mat.get("lote_origem") or "?"
        bci = _bci_da_matricula(mat, idx_cod, bci_list)
        if not bci and unica and bci_list:
            bci = bci_list[0]

        if not bci:
            add("bci_ausente", "alerta",
                f"Matrícula {rotulo}: BCI não vinculado (sem cod. imóvel correspondente).",
                rotulo, "anexar/vincular o BCI desta matrícula")
        else:
            doc_mat = _so_digitos((mat.get("proprietario_registral") or {}).get("doc"))
            doc_bci = _so_digitos((bci.get("proprietario_cadastral") or {}).get("doc"))
            if doc_mat and doc_bci and doc_mat != doc_bci:
                extra = (" — esperado na usucapião (o possuidor não é o titular registral)"
                         if is_usucapiao else "")
                add("titularidade_divergente", "alerta" if is_usucapiao else "bloqueante",
                    (f"Matrícula {rotulo}: titularidade DIVERGENTE — registro em "
                     f"{(mat.get('proprietario_registral') or {}).get('nome') or doc_mat} "
                     f"e BCI/IPTU em "
                     f"{(bci.get('proprietario_cadastral') or {}).get('nome') or doc_bci}{extra}."),
                    rotulo, None if is_usucapiao else "atualizar o cadastro municipal antes do protocolo")
            am, ab = mat.get("area_m2"), bci.get("area_terreno_m2")
            if am and ab and abs(float(am) - float(ab)) > TOLERANCIA_AREA_M2:
                add("area_divergente", "alerta",
                    f"Matrícula {rotulo}: área registral {am:.2f} m² ≠ BCI {ab:.2f} m².",
                    rotulo, "conferir a área entre certidão e cadastro")
            lc_m = (mat.get("loc_cartografica") or "").strip()
            lc_b = (bci.get("loc_cartografica") or "").strip()
            if lc_m and lc_b and lc_m != lc_b:
                add("localizacao_divergente", "alerta",
                    f"Matrícula {rotulo}: localização cartográfica {lc_m} ≠ BCI {lc_b}.",
                    rotulo, None)

        # fiscal: precisa de UMA via válida (CND negativa ou guia paga)
        iptu = iptu_por_mat.get(mat.get("id"))
        if not iptu and unica and iptu_list:
            # prefere uma via já regular (CND negativa / quitado); senão a primeira
            iptu = next((i for i in iptu_list if i.get("situacao") in ("cnd_negativa", "quitado")), iptu_list[0])
        if not iptu:
            add("iptu_irregular", "bloqueante",
                f"Matrícula {rotulo}: sem regularidade de IPTU (anexar CND negativa ou guia paga).",
                rotulo, "anexar a CND ou a guia paga (DAM + comprovante)")
        else:
            via = iptu.get("via_regularidade")
            sit = iptu.get("situacao")
            if via == "cnd" and sit not in ("cnd_negativa", "quitado"):
                add("iptu_irregular", "bloqueante",
                    f"Matrícula {rotulo}: CND informada não está negativa/quitada.", rotulo,
                    "emitir CND negativa ou anexar guia paga")
            elif via == "guia_paga" and sit in ("debito_aberto",):
                add("iptu_em_aberto", "alerta",
                    f"Matrícula {rotulo}: débito de IPTU em aberto — anexar comprovante de quitação.",
                    rotulo, "anexar o comprovante de pagamento (DAM quitada)")

    bloqueantes = [a for a in alertas if a["severidade"] == "bloqueante"]
    resumo = {
        "total_matriculas": len(matriculas),
        "total_alertas": len(alertas),
        "bloqueantes": len(bloqueantes),
        "pode_protocolar": len(bloqueantes) == 0 and len(matriculas) > 0,
    }
    return {"alertas": alertas, "resumo": resumo}
