# @module services.vistoria_averbacao_relatorio — Gerador de relatório (fonte única)
"""
Converte os dados estruturados da Vistoria de Obra para Averbação em prosa técnica
formal. MESMA função alimenta preview do app, PDF e DOCX (fonte única).

Saída principal: `gerar_secoes_averbacao(vistoria) -> list[(titulo, corpo)]`.
`gerar_relatorio_averbacao(vistoria) -> str` apenas junta as seções em texto.

Regras: 3ª pessoa, voz formal, números pt-BR (vírgula decimal, ponto de milhar),
concordância de plural, nunca emitir seção vazia (usa frase neutra).
"""
from __future__ import annotations

from typing import List, Tuple

from models.averbacao import (
    ETAPAS_OBRA, DOCS_AVERBACAO, SISTEMAS_AVERBACAO, PESOS_ETAPAS,
    faixa_divergencia, frase_divergencia, calcular_averbacao,
)

_ETAPA_NOME = {e["id"]: e["nome"] for e in ETAPAS_OBRA}
_DOC_NOME = {d["id"]: d["nome"] for d in DOCS_AVERBACAO}
_DOC_BASE = {d["id"]: d["base"] for d in DOCS_AVERBACAO}
_SIST_NOME = {s["id"]: s["nome"] for s in SISTEMAS_AVERBACAO}

_DESTINACAO_LABEL = {"residencial": "residencial", "comercial": "comercial", "misto": "misto (residencial/comercial)"}
_SITUACAO_LABEL = {
    "concluida": "concluída", "concluida_pendencias": "concluída com pendências",
    "em_conclusao": "em fase de conclusão",
}
_COMPAT_LABEL = {
    "total": "compatibilidade total com o projeto aprovado",
    "regularizavel": "divergência regularizável em relação ao projeto aprovado",
    "relevante": "divergência relevante em relação ao projeto aprovado",
}
_PARECER_LABEL = {
    "apta": "APTA PARA AVERBAÇÃO",
    "apta_apos_saneamento": "APTA PARA AVERBAÇÃO APÓS SANEAMENTO DAS PENDÊNCIAS",
    "inapta": "INAPTA PARA AVERBAÇÃO",
}
_SEVERIDADE_LABEL = {"leve": "leve", "moderada": "moderada", "grave": "grave"}


def _num(v, casas: int = 2) -> str:
    """Formata número em pt-BR (vírgula decimal, ponto de milhar)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    s = f"{f:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _m2(v) -> str:
    return f"{_num(v)} m²" if v not in (None, "") else "—"


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular}" if n == 1 else f"{n} {plural}"


def _sistemas_visiveis(av: dict) -> set:
    """IDs de sistemas/documentos comerciais só entram se destinação ≠ residencial."""
    destinacao = av.get("destinacao", "residencial")
    so_residencial = destinacao == "residencial"
    return so_residencial


def gerar_secoes_averbacao(vistoria: dict) -> List[Tuple[str, str]]:
    """Retorna lista de (titulo, corpo) — uma entrada por seção."""
    av = vistoria.get("averbacao") or {}
    # Garante cálculos atualizados (idempotente).
    av = calcular_averbacao(dict(av))
    conf = av.get("confronto") or {}
    so_residencial = _sistemas_visiveis(av)
    destinacao = av.get("destinacao", "residencial")

    endereco = vistoria.get("imovel_endereco") or "endereço não informado"
    matricula = vistoria.get("imovel_matricula") or ""
    cartorio = av.get("cartorio") or vistoria.get("campos_extras", {}).get("cartorio", "")
    secoes: List[Tuple[str, str]] = []

    # ── 1. OBJETO E FINALIDADE ──────────────────────────────────────────────
    p = [
        f"O presente documento constitui Vistoria Técnica de Obra para fins de averbação "
        f"da construção na matrícula do imóvel, nos termos do art. 167, inciso II, e do "
        f"art. 246 da Lei nº 6.015/1973 (Lei de Registros Públicos). A edificação destina-se "
        f"a uso {_DESTINACAO_LABEL.get(destinacao, destinacao)} e localiza-se em {endereco}."
    ]
    if matricula:
        p.append(f"Imóvel objeto da matrícula nº {matricula}" + (f", do {cartorio}" if cartorio else "") + ".")
    docs_obra = []
    if av.get("alvara_numero"):
        docs_obra.append(f"alvará de construção nº {av['alvara_numero']}")
    if av.get("habitese_numero"):
        docs_obra.append(f"habite-se/auto de conclusão nº {av['habitese_numero']}")
    if av.get("cno"):
        docs_obra.append(f"CNO da obra nº {av['cno']}")
    if docs_obra:
        p.append("A obra está vinculada a: " + "; ".join(docs_obra) + ".")
    secoes.append(("OBJETO E FINALIDADE", " ".join(p)))

    # ── 2. METODOLOGIA ──────────────────────────────────────────────────────
    metodologia = (
        "A vistoria foi conduzida por inspeção predominantemente visual, em conformidade com "
        "a ABNT NBR 16747:2020 (Inspeção Predial) e a ABNT NBR 13752 (Perícias de Engenharia), "
        "compreendendo levantamento dimensional in loco com confronto entre as áreas de projeto, "
        "executada e constante da matrícula; aferição do estágio de execução por etapas ponderadas "
        "segundo critério simplificado da ABNT NBR 12721; classificação dos sistemas construtivos "
        "em conforme (C), não conforme (NC) e não aplicável (NA); conferência da documentação "
        "registral necessária à averbação; e registro fotográfico georreferenciado."
    )
    secoes.append(("METODOLOGIA", metodologia))

    # ── 3. ESTÁGIO DA OBRA ──────────────────────────────────────────────────
    conclusao_geral = av.get("conclusao_geral_pct")
    etapas = av.get("etapas") or []
    p3 = [
        f"A obra apresenta conclusão geral ponderada de {_num(conclusao_geral, 1)}%, "
        f"calculada pela média das etapas executadas ponderada pelos respectivos pesos."
    ]
    parciais = []
    for e in etapas:
        if not isinstance(e, dict):
            continue
        nome = _ETAPA_NOME.get(e.get("etapa_id"))
        if not nome:
            continue
        pct = e.get("percentual", 0)
        peso = PESOS_ETAPAS.get(e.get("etapa_id"), 0)
        parciais.append(f"{nome} (peso {peso}): {pct}%")
    if parciais:
        p3.append("Execução por etapa — " + "; ".join(parciais) + ".")
    secoes.append(("ESTÁGIO DA OBRA", " ".join(p3)))

    # ── 4. CONFRONTO DE ÁREAS ───────────────────────────────────────────────
    a_proj = conf.get("area_projeto_m2")
    a_med = conf.get("area_medida_m2")
    a_mat = conf.get("area_matricula_m2")
    a_terr = conf.get("area_terreno_m2")
    div_m2 = conf.get("divergencia_m2")
    div_pct = conf.get("divergencia_pct")
    taxa = conf.get("taxa_ocupacao_pct")
    p4 = []
    p4.append(
        "Do confronto dimensional apurou-se: área de projeto aprovado de "
        f"{_m2(a_proj)}; área executada medida in loco de {_m2(a_med)}"
        + (f"; área constante da matrícula de {_m2(a_mat)}" if a_mat not in (None, "") else "")
        + (f"; área do terreno de {_m2(a_terr)}" if a_terr not in (None, "") else "")
        + "."
    )
    if div_m2 is not None and div_pct is not None:
        sinal = "acréscimo" if div_m2 >= 0 else "supressão"
        p4.append(
            f"A divergência entre a área executada e a aprovada é de {_m2(abs(div_m2))} "
            f"({_num(abs(div_pct))}%), correspondente a {sinal} de área construída."
        )
        p4.append(frase_divergencia(div_pct))
    if taxa is not None:
        p4.append(f"A taxa de ocupação apurada é de {_num(taxa)}%.")
    if conf.get("detalhe_pavimentos"):
        p4.append(f"Detalhamento por pavimento/anexo: {conf['detalhe_pavimentos']}.")
    secoes.append(("CONFRONTO DE ÁREAS", " ".join(p4)))

    # ── 5. SISTEMAS CONSTRUTIVOS ────────────────────────────────────────────
    sistemas = av.get("sistemas") or []
    def _sis_visivel(sid: str) -> bool:
        meta = next((s for s in SISTEMAS_AVERBACAO if s["id"] == sid), None)
        if not meta:
            return False
        if meta.get("comercial") and so_residencial:
            return False
        return True
    conformes = [s for s in sistemas if isinstance(s, dict) and s.get("conformidade") == "C" and _sis_visivel(s.get("sistema_id"))]
    nc = [s for s in sistemas if isinstance(s, dict) and s.get("conformidade") == "NC" and _sis_visivel(s.get("sistema_id"))]
    na = [s for s in sistemas if isinstance(s, dict) and s.get("conformidade") == "NA" and _sis_visivel(s.get("sistema_id"))]
    p5 = []
    if conformes:
        nomes = [_SIST_NOME.get(s.get("sistema_id"), s.get("sistema_id")) for s in conformes]
        p5.append("Apresentaram-se em conformidade: " + ", ".join(nomes) + ".")
    if nc:
        p5.append("Foram identificadas as seguintes não conformidades:")
        for i, s in enumerate(nc, 1):
            nome = _SIST_NOME.get(s.get("sistema_id"), s.get("sistema_id"))
            pat = ", ".join(s.get("patologias") or []) or "anomalia construtiva"
            sev = _SEVERIDADE_LABEL.get(s.get("severidade"), "não classificada")
            obs = f" Observação: {s['observacao']}." if s.get("observacao") else ""
            p5.append(f"{i}) {nome} — manifestações: {pat}; severidade {sev}.{obs}")
    if not conformes and not nc:
        p5.append("Não foram registradas observações relevantes quanto aos sistemas construtivos vistoriados.")
    if na:
        nomes_na = [_SIST_NOME.get(s.get("sistema_id"), s.get("sistema_id")) for s in na]
        p5.append("Não se aplicam ao imóvel: " + ", ".join(nomes_na) + ".")
    secoes.append(("SISTEMAS CONSTRUTIVOS", "\n".join(p5)))

    # ── 6. DOCUMENTAÇÃO PARA AVERBAÇÃO ──────────────────────────────────────
    documentos = av.get("documentos") or []
    def _doc_visivel(did: str) -> bool:
        meta = next((d for d in DOCS_AVERBACAO if d["id"] == did), None)
        if not meta:
            return False
        if meta.get("comercial") and so_residencial:
            return False
        return True
    apresentados = [d for d in documentos if isinstance(d, dict) and d.get("situacao") == "OK" and _doc_visivel(d.get("doc_id"))]
    pendentes = [d for d in documentos if isinstance(d, dict) and d.get("situacao") == "PEND" and _doc_visivel(d.get("doc_id"))]
    p6 = []
    if apresentados:
        nomes = [_DOC_NOME.get(d.get("doc_id"), d.get("doc_id")) for d in apresentados]
        p6.append("Foram apresentados/conferidos: " + ", ".join(nomes) + ".")
    else:
        p6.append("Não foram conferidos documentos registrais nesta vistoria.")
    if pendentes:
        nomes = [_DOC_NOME.get(d.get("doc_id"), d.get("doc_id")) for d in pendentes]
        p6.append(
            "PENDÊNCIAS IMPEDITIVAS: " + ", ".join(nomes) + ". "
            "A averbação da construção somente se efetiva após o saneamento integral das pendências acima."
        )
    else:
        p6.append("Não há pendências documentais impeditivas registradas.")
    secoes.append(("DOCUMENTAÇÃO PARA AVERBAÇÃO", " ".join(p6)))

    # ── 7. CONCLUSÃO E PARECER ──────────────────────────────────────────────
    p7 = []
    p7.append(
        f"A obra encontra-se {_SITUACAO_LABEL.get(av.get('situacao_obra'), 'concluída')}, "
        f"com {_COMPAT_LABEL.get(av.get('compatibilidade'), 'compatibilidade total com o projeto aprovado')}."
    )
    if av.get("necessita_asbuilt"):
        p7.append("Recomenda-se a elaboração de levantamento as-built para regularização da área efetivamente executada.")
    else:
        p7.append("Não se identificou necessidade de levantamento as-built.")
    p7.append(f"PARECER: {_PARECER_LABEL.get(av.get('parecer'), 'APTA PARA AVERBAÇÃO')}.")
    if av.get("recomendacoes"):
        p7.append(f"Recomendações: {av['recomendacoes']}.")
    if av.get("prazo_saneamento"):
        p7.append(f"Prazo sugerido para saneamento: {av['prazo_saneamento']}.")
    secoes.append(("CONCLUSÃO E PARECER", " ".join(p7)))

    return secoes


def gerar_relatorio_averbacao(vistoria: dict) -> str:
    """Texto integral do relatório (para preview do app e cache)."""
    partes = []
    for i, (titulo, corpo) in enumerate(gerar_secoes_averbacao(vistoria), 1):
        partes.append(f"{i}. {titulo}\n{corpo}")
    return "\n\n".join(partes)
