# @module services.geo_urbano.usucapiao — regras do serviço de Usucapião Extrajudicial.
#
# Catálogo de modalidades (Prov. CNJ 149/2023 + CC/CF), validação do tempo de posse
# (soma de posses art. 1.243 CC) e da área-limite por modalidade, com a exceção do
# STF Tema 815 (especial urbana não se condiciona ao módulo mínimo municipal), e a
# checklist dinâmica de documentos (blocos A-G) por modalidade/situação registral.
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

# Catálogo das modalidades (define prazo, área-limite, justo título e fundamento).
MODALIDADES = {
    "extraordinaria": {
        "label": "Extraordinária", "fundamento": "art. 1.238 do Código Civil",
        "prazo_anos": 15, "prazo_reduzido": 10,
        "condicao_reducao": "moradia habitual ou obras/serviços de caráter produtivo",
        "area_max_m2": None, "exige_justo_titulo": False, "escopo": "ambos",
    },
    "ordinaria": {
        "label": "Ordinária", "fundamento": "art. 1.242 do Código Civil",
        "prazo_anos": 10, "prazo_reduzido": 5,
        "condicao_reducao": "aquisição onerosa com registro cancelado + moradia/investimentos",
        "area_max_m2": None, "exige_justo_titulo": True, "escopo": "ambos",
    },
    "especial_urbana": {
        "label": "Especial Urbana", "fundamento": "art. 183 da CF e art. 1.240 do Código Civil",
        "prazo_anos": 5, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_m2": 250.0, "exige_justo_titulo": False, "escopo": "urbano",
        "ignora_modulo_municipal": True,
    },
    "especial_rural": {
        "label": "Especial Rural", "fundamento": "art. 191 da CF e art. 1.239 do Código Civil",
        "prazo_anos": 5, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_ha": 50.0, "exige_justo_titulo": False, "escopo": "rural",
    },
    "familiar": {
        "label": "Especial Urbana Familiar", "fundamento": "art. 1.240-A do Código Civil",
        "prazo_anos": 2, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_m2": 250.0, "exige_justo_titulo": False, "escopo": "urbano",
    },
    "coletiva": {
        "label": "Coletiva", "fundamento": "art. 10 da Lei nº 10.257/2001 (Estatuto da Cidade)",
        "prazo_anos": 5, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_m2": None, "exige_justo_titulo": False, "escopo": "urbano",
    },
    "outra": {
        "label": "Outra (cartório define)", "fundamento": None,
        "prazo_anos": None, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_m2": None, "exige_justo_titulo": False, "escopo": "ambos",
    },
}


def fundamento_legal(projeto: dict) -> str:
    """Fundamento da modalidade escolhida (ou o texto livre quando 'outra')."""
    mod = projeto.get("modalidade_usucapiao") or "extraordinaria"
    info = MODALIDADES.get(mod) or {}
    return info.get("fundamento") or (projeto.get("fundamento_legal") or "").strip() or "—"


def _ano(v) -> Optional[int]:
    """Extrai o ano (int) de 2010 / '2010' / '2010-05-01'. None se vazio/atual."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"\d{4}", str(v))
    return int(m.group()) if m else None


def anos_cobertos(projeto: dict, ano_ref: Optional[int] = None) -> int:
    """Soma de posses (art. 1.243 CC): soma a duração dos períodos contíguos. Sem
    soma_posses, usa posse.inicio → ano de referência."""
    if ano_ref is None:
        ano_ref = datetime.now(timezone.utc).year
    periodos = projeto.get("soma_posses") or []
    total = 0
    if periodos:
        for p in periodos:
            ini = _ano(p.get("inicio"))
            fim = _ano(p.get("fim")) or ano_ref
            if ini is not None:
                total += max(0, fim - ini)
        return total
    ini = _ano((projeto.get("posse") or {}).get("inicio"))
    return max(0, ano_ref - ini) if ini is not None else 0


def validar_posse(projeto: dict, ano_ref: Optional[int] = None) -> dict:
    """Valida tempo de posse (vs prazo da modalidade) e área (vs limite), com a
    exceção do STF Tema 815 para a especial urbana. Retorna o relatório (não trava)."""
    mod = projeto.get("modalidade_usucapiao") or "extraordinaria"
    info = MODALIDADES.get(mod) or MODALIDADES["outra"]
    avisos = []

    cobertos = anos_cobertos(projeto, ano_ref)
    prazo = info.get("prazo_anos")
    prazo_ok = True if prazo is None else cobertos >= prazo
    faltam = 0 if (prazo is None or prazo_ok) else (prazo - cobertos)

    area = projeto.get("area_declarada_m2")
    area_max = info.get("area_max_m2")
    area_ha_max = info.get("area_max_ha")
    if area_ha_max is not None and area is not None:
        area_ok = (area / 10000.0) <= area_ha_max
    elif area_max is not None and area is not None:
        area_ok = area <= area_max
    else:
        area_ok = True
    ignora_modulo = bool(info.get("ignora_modulo_municipal"))
    if ignora_modulo:
        avisos.append("STF Tema 815 (RE 422.349): a usucapião especial urbana não se "
                      "condiciona ao módulo mínimo de área municipal.")

    exige_jt = bool(info.get("exige_justo_titulo"))
    justo_titulo_ok = (not exige_jt) or bool((projeto.get("posse") or {}).get("justo_titulo"))
    if exige_jt and not justo_titulo_ok:
        avisos.append("Modalidade ordinária exige justo título e boa-fé (art. 1.242 CC).")

    return {
        "modalidade": mod, "fundamento": fundamento_legal(projeto),
        "anos_cobertos": cobertos, "prazo_exigido": prazo, "prazo_reduzido": info.get("prazo_reduzido"),
        "prazo_ok": prazo_ok, "faltam_anos": faltam,
        "area_m2": area, "area_max": area_max, "area_max_ha": area_ha_max, "area_ok": area_ok,
        "ignora_modulo_municipal": ignora_modulo,
        "exige_justo_titulo": exige_jt, "justo_titulo_ok": justo_titulo_ok,
        "avisos": avisos,
    }
