# @module services.recibo_catalogo — Catálogo de serviços técnicos Romatec p/ recibos
"""
Catálogo cascata Categoria → Serviço, portado do padrão ZAYRA/Romatec.

Cada serviço carrega:
  - value:      chave estável
  - label:      rótulo exibido no select
  - descricao:  template de descrição (auto-preenche o textarea do recibo)
  - tipo:       tipo de recibo sugerido (alimenta a numeração REC-{ABREV}-...)

As descrições já saem em linguagem técnica formal, citando as NBR aplicáveis
(NBR 14653 — avaliação; NBR 13133 — topografia; NBR 6118 — concreto) e os
registros profissionais pertinentes (CFT, CREA, CRECI, INCRA), conforme o serviço.
"""
from typing import Optional

# Ordem das categorias preservada (dict ordenado no Python 3.7+).
CATALOGO_SERVICOS: dict[str, dict] = {
    "avaliacao": {
        "label": "Avaliação Imobiliária",
        "servicos": [
            {
                "value": "ptam_urbano",
                "label": "PTAM — Imóvel Urbano",
                "tipo": "honorarios",
                "descricao": (
                    "Honorários técnicos referentes à elaboração de Parecer Técnico de "
                    "Avaliação Mercadológica (PTAM) de imóvel urbano, em conformidade com a "
                    "ABNT NBR 14653 (partes 1 e 2) e a Resolução COFECI nº 957/2006. "
                    "Compreende vistoria técnica, pesquisa e tratamento estatístico de dados "
                    "de mercado, memória de cálculo e emissão do parecer com responsabilidade "
                    "técnica do avaliador signatário."
                ),
            },
            {
                "value": "ptam_rural",
                "label": "PTAM — Imóvel Rural",
                "tipo": "honorarios",
                "descricao": (
                    "Honorários técnicos referentes à elaboração de Parecer Técnico de "
                    "Avaliação Mercadológica (PTAM) de imóvel rural, em conformidade com a "
                    "ABNT NBR 14653 (partes 1 e 3) e diretrizes do INCRA. Compreende vistoria "
                    "de campo, identificação de benfeitorias e culturas, pesquisa de mercado e "
                    "memória de cálculo, com responsabilidade técnica do avaliador signatário."
                ),
            },
            {
                "value": "laudo_avaliacao",
                "label": "Laudo de Avaliação",
                "tipo": "honorarios",
                "descricao": (
                    "Honorários técnicos referentes à elaboração de Laudo de Avaliação de bem "
                    "imóvel, em conformidade com a ABNT NBR 14653, incluindo vistoria, pesquisa "
                    "de mercado, tratamento dos dados e emissão do laudo conclusivo."
                ),
            },
            {
                "value": "parecer_tecnico",
                "label": "Parecer Técnico / Consulta de Valor",
                "tipo": "honorarios",
                "descricao": (
                    "Honorários técnicos referentes à emissão de parecer técnico de valor de "
                    "imóvel, com base em pesquisa de mercado e fundamentação conforme a ABNT "
                    "NBR 14653."
                ),
            },
        ],
    },
    "topografia": {
        "label": "Topografia e Georreferenciamento",
        "servicos": [
            {
                "value": "levantamento_planialtimetrico",
                "label": "Levantamento Planialtimétrico",
                "tipo": "servico",
                "descricao": (
                    "Prestação de serviços de levantamento topográfico planialtimétrico, "
                    "executado em conformidade com a ABNT NBR 13133, incluindo trabalho de "
                    "campo, processamento dos dados e emissão de planta e memorial descritivo, "
                    "sob responsabilidade técnica (ART/TRT — CFT)."
                ),
            },
            {
                "value": "georreferenciamento_incra",
                "label": "Georreferenciamento (INCRA/SIGEF)",
                "tipo": "servico",
                "descricao": (
                    "Prestação de serviços de georreferenciamento de imóvel rural conforme a "
                    "Norma Técnica de Georreferenciamento do INCRA e a ABNT NBR 13133, com "
                    "levantamento dos vértices, processamento, certificação no SIGEF e emissão "
                    "de planta e memorial descritivo, sob responsabilidade técnica."
                ),
            },
            {
                "value": "locacao_obra",
                "label": "Locação de Obra",
                "tipo": "servico",
                "descricao": (
                    "Prestação de serviços de locação topográfica de obra (gabarito/marcação), "
                    "executada em conformidade com a ABNT NBR 13133, sob responsabilidade "
                    "técnica."
                ),
            },
            {
                "value": "retificacao_area",
                "label": "Retificação de Área / Memorial",
                "tipo": "servico",
                "descricao": (
                    "Prestação de serviços técnicos para retificação de área e elaboração de "
                    "memorial descritivo georreferenciado, em conformidade com a ABNT NBR 13133, "
                    "para fins de regularização registral."
                ),
            },
        ],
    },
    "demarcacao": {
        "label": "Demarcação e Divisas",
        "servicos": [
            {
                "value": "laudo_demarcacao",
                "label": "Laudo de Demarcação",
                "tipo": "servico",
                "descricao": (
                    "Prestação de serviços técnicos de demarcação de imóvel e elaboração de "
                    "laudo de demarcação, com levantamento topográfico das divisas, implantação "
                    "de marcos e memorial descritivo, conforme a ABNT NBR 13133, sob "
                    "responsabilidade técnica."
                ),
            },
            {
                "value": "verificacao_divisas",
                "label": "Verificação / Conferência de Divisas",
                "tipo": "vistoria",
                "descricao": (
                    "Prestação de serviços de verificação e conferência de divisas de imóvel, "
                    "com levantamento de campo e parecer técnico, conforme a ABNT NBR 13133."
                ),
            },
        ],
    },
    "vistoria": {
        "label": "Vistorias e Engenharia",
        "servicos": [
            {
                "value": "vistoria_obra",
                "label": "Vistoria de Obra / Medição",
                "tipo": "vistoria",
                "descricao": (
                    "Prestação de serviços de vistoria técnica de obra e medição de etapa "
                    "construtiva, com registro fotográfico e relatório técnico, observadas as "
                    "normas técnicas aplicáveis (ABNT NBR 6118 para estruturas de concreto), "
                    "sob responsabilidade técnica."
                ),
            },
            {
                "value": "vistoria_cautelar",
                "label": "Vistoria Cautelar de Vizinhança",
                "tipo": "vistoria",
                "descricao": (
                    "Prestação de serviços de vistoria cautelar de vizinhança, com registro do "
                    "estado das edificações lindeiras antes do início da obra, conforme ABNT "
                    "NBR 12722, e emissão de laudo com registro fotográfico."
                ),
            },
            {
                "value": "laudo_predial",
                "label": "Laudo de Vistoria Predial",
                "tipo": "vistoria",
                "descricao": (
                    "Prestação de serviços de inspeção predial e elaboração de laudo de "
                    "vistoria, conforme a ABNT NBR 16747, com avaliação das condições da "
                    "edificação e recomendações técnicas."
                ),
            },
        ],
    },
    "documentacao": {
        "label": "Documentação Técnica",
        "servicos": [
            {
                "value": "art_trt",
                "label": "ART / TRT",
                "tipo": "servico",
                "descricao": (
                    "Emissão de Anotação/Termo de Responsabilidade Técnica (ART/TRT) referente "
                    "ao serviço técnico contratado, junto ao conselho/órgão de classe competente "
                    "(CFT / CREA)."
                ),
            },
            {
                "value": "memorial_descritivo",
                "label": "Memorial Descritivo",
                "tipo": "servico",
                "descricao": (
                    "Elaboração de memorial descritivo técnico do imóvel, em conformidade com a "
                    "ABNT NBR 13133, para fins de regularização."
                ),
            },
        ],
    },
    "consultoria": {
        "label": "Consultoria e Intermediação Imobiliária",
        "servicos": [
            {
                "value": "consultoria_imobiliaria",
                "label": "Consultoria Imobiliária",
                "tipo": "consultoria",
                "descricao": (
                    "Prestação de serviços de consultoria imobiliária técnica, observadas as "
                    "atribuições do corretor de imóveis (CRECI) e a Lei nº 6.530/1978."
                ),
            },
            {
                "value": "comissao_intermediacao",
                "label": "Comissão de Intermediação",
                "tipo": "comissao",
                "descricao": (
                    "Comissão referente à intermediação imobiliária na transação do imóvel, "
                    "conforme atribuições do corretor de imóveis (CRECI) e a Lei nº 6.530/1978."
                ),
            },
            {
                "value": "assessoria_documental",
                "label": "Assessoria Documental",
                "tipo": "consultoria",
                "descricao": (
                    "Prestação de serviços de assessoria documental imobiliária, incluindo "
                    "análise e organização de documentação para regularização do imóvel."
                ),
            },
        ],
    },
    "mao_obra": {
        "label": "Mão de Obra",
        "servicos": [
            {
                "value": "mao_obra_diaria",
                "label": "Diária",
                "tipo": "mao_obra",
                "descricao": "Pagamento de mão de obra referente a serviço prestado (diária).",
            },
            {
                "value": "mao_obra_quinzena",
                "label": "Quinzena",
                "tipo": "mao_obra",
                "descricao": (
                    "Pagamento de mão de obra referente ao período quinzenal trabalhado, "
                    "conforme serviço prestado."
                ),
            },
            {
                "value": "mao_obra_empreitada",
                "label": "Empreitada",
                "tipo": "mao_obra",
                "descricao": (
                    "Pagamento de mão de obra por empreitada referente à execução do serviço "
                    "contratado."
                ),
            },
        ],
    },
    "aluguel": {
        "label": "Aluguel",
        "servicos": [
            {
                "value": "aluguel_mensal",
                "label": "Aluguel Mensal",
                "tipo": "aluguel",
                "descricao": "Pagamento referente a aluguel mensal do imóvel locado.",
            },
        ],
    },
}


def listar_catalogo() -> list[dict]:
    """Retorna o catálogo no formato consumido pelo frontend (cascata)."""
    out = []
    for cat_key, cat in CATALOGO_SERVICOS.items():
        out.append({
            "value": cat_key,
            "label": cat["label"],
            "servicos": [
                {
                    "value": s["value"],
                    "label": s["label"],
                    "tipo": s.get("tipo", "servico"),
                    "descricao": s.get("descricao", ""),
                }
                for s in cat["servicos"]
            ],
        })
    return out


def buscar_servico(categoria: Optional[str], servico_value: Optional[str]) -> Optional[dict]:
    """Localiza um serviço pelo par (categoria, value) ou só pelo value."""
    cats = [categoria] if categoria else list(CATALOGO_SERVICOS.keys())
    for ck in cats:
        cat = CATALOGO_SERVICOS.get(ck)
        if not cat:
            continue
        for s in cat["servicos"]:
            if s["value"] == servico_value:
                return {**s, "categoria": ck}
    return None
