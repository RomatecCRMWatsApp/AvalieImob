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


# ──────────────────────────────────────────────────────────────────────────────
# Checklist dinâmica de documentos (blocos A-G), por modalidade/situação/herdeiro.
# ──────────────────────────────────────────────────────────────────────────────
# Itens base sempre presentes: (bloco, chave, label, obrigatorio)
_CHECKLIST_BASE = [
    ("A", "requerimento", "Requerimento de reconhecimento (assinado por advogado)", True),
    ("A", "procuracao_oab", "Procuração + OAB do advogado", True),
    ("A", "ata_notarial", "Ata notarial de posse (tabelião de notas)", True),
    ("B", "planta_memorial", "Planta e memorial descritivo (assinados pelos confrontantes)", True),
    ("B", "art_trt", "ART/TRT/RRT — guia paga", True),
    ("C", "doc_requerente", "Documentos do requerente e cônjuge (CPF, RG/CNH)", True),
    ("C", "comprovante_endereco", "Comprovante de endereço", True),
    ("C", "certidao_estado_civil", "Certidão de estado civil (< 90 dias)", True),
    ("E", "provas_posse", "Provas do período aquisitivo (água/luz/IPTU/contratos)", True),
    ("F", "certidao_distribuidor", "Certidões negativas dos distribuidores (comarca do imóvel + domicílio)", True),
    ("G", "anuencia_confrontantes", "Declaração de anuência dos confrontantes", True),
]


def _eh_herdeiro(projeto: dict) -> bool:
    if any((p.get("papel") == "herdeiro") for p in (projeto.get("partes") or [])):
        return True
    return any((p.get("vinculo") == "de_cujus") for p in (projeto.get("soma_posses") or []))


def checklist_para(projeto: dict) -> list:
    """Monta a checklist dinâmica (blocos A-G). Preserva status/upload já marcados
    (casados por `chave`)."""
    mod = projeto.get("modalidade_usucapiao") or "extraordinaria"
    info = MODALIDADES.get(mod) or {}
    sit = projeto.get("situacao_registral") or "nao_matriculado"
    itens = list(_CHECKLIST_BASE)

    # D) Imóvel — varia pela situação registral
    if sit == "nao_matriculado":
        itens.append(("D", "negativa_propriedade", "Certidão negativa de propriedade (RI competente)", True))
    else:
        itens.append(("D", "certidao_matricula", "Certidão de inteiro teor da matrícula (atualizada)", True))
    itens += [
        ("D", "certidao_confrontante", "Certidões dos confrontantes (inteiro teor/negativas)", True),
        ("D", "certidao_negativa_onus", "Certidões negativas de ônus e ações reais", True),
        ("D", "iptu_valor_venal", "Carnê de IPTU/ITR + comprovante de valor venal", True),
        ("G", "anuencia_titular", "Anuência dos titulares de direitos da matrícula",
         sit != "nao_matriculado"),
    ]

    # Ordinária: exige justo título
    if info.get("exige_justo_titulo"):
        itens.append(("A", "justo_titulo", "Justo título (contrato/cessão de direitos)", True))

    # Caso herdeiro: óbito, partilha, certidões dos demais herdeiros, posse exclusiva
    if _eh_herdeiro(projeto):
        itens += [
            ("C", "certidao_obito", "Certidão de óbito do de cujus", True),
            ("C", "formal_partilha", "Formal de partilha / escritura de inventário", False),
            ("C", "certidao_herdeiros", "Certidões de nascimento/casamento dos demais herdeiros", True),
            ("C", "prova_posse_exclusiva", "Prova da posse exclusiva (rompimento da composse)", True),
        ]

    # Rural: georreferenciamento certificado + CCIR + CAR
    if info.get("escopo") == "rural":
        itens += [
            ("B", "georef_sigef", "Georreferenciamento certificado INCRA/SIGEF", True),
            ("B", "ccir", "CCIR", True),
            ("B", "car", "CAR (Cadastro Ambiental Rural)", True),
        ]

    # Preserva status/upload já marcados (por chave).
    atual = {i.get("chave"): i for i in (projeto.get("checklist") or [])}
    out = []
    for (bloco, chave, label, obrig) in itens:
        prev = atual.get(chave) or {}
        out.append({
            "bloco": bloco, "chave": chave, "label": label, "obrigatorio": bool(obrig),
            "status": prev.get("status") or "pendente",
            "upload_id": prev.get("upload_id"), "observacao": prev.get("observacao"),
        })
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Anuentes (planta/memorial) — confrontantes + titular tabular da matrícula.
# ──────────────────────────────────────────────────────────────────────────────
def _matricula_usucapienda(projeto: dict) -> dict:
    mid = projeto.get("matricula_usucapienda_id")
    mats = projeto.get("matriculas") or []
    if mid:
        for m in mats:
            if m.get("id") == mid:
                return m
    return mats[0] if mats else {}


def anuentes_de(projeto: dict) -> list:
    """Deriva os anuentes de `confrontantes` (lados) + titular tabular da matrícula,
    fundindo com os anuentes já cadastrados (por nome+doc)."""
    existentes = {((a.get("nome") or "").strip().lower(), (a.get("doc") or "")): a
                  for a in (projeto.get("anuentes") or [])}

    def _merge(base: dict) -> dict:
        chave = ((base.get("nome") or "").strip().lower(), (base.get("doc") or ""))
        prev = existentes.get(chave)
        if prev:
            merged = dict(base)
            merged.update({k: v for k, v in prev.items() if v not in (None, "")})
            return merged
        return base

    out = []
    for c in (projeto.get("confrontantes") or []):
        out.append(_merge({
            "papel": "confrontante", "nome": c.get("confrontante"), "doc": c.get("doc"),
            "lado": c.get("lado"), "medida_m": c.get("medida_m"),
            "tipo": c.get("tipo") or "particular", "endereco": c.get("endereco"),
            "telefone": c.get("telefone"), "canal": "presencial",
            "anuencia": {"status": "pendente"},
        }))

    if (projeto.get("situacao_registral") or "nao_matriculado") != "nao_matriculado":
        mat = _matricula_usucapienda(projeto)
        tit = (mat.get("proprietario_registral") or {}) if mat else {}
        if tit.get("nome"):
            out.append(_merge({
                "papel": "titular_tabular", "nome": tit.get("nome"), "doc": tit.get("doc"),
                "tipo": "particular", "canal": "presencial", "anuencia": {"status": "pendente"},
            }))

    # anuentes manuais que não vieram de confrontante/titular
    vistos = {((a.get("nome") or "").strip().lower(), (a.get("doc") or "")) for a in out}
    for a in (projeto.get("anuentes") or []):
        chave = ((a.get("nome") or "").strip().lower(), (a.get("doc") or ""))
        if chave not in vistos:
            out.append(a)
    return out
