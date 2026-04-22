# @module seed_tvi — Modelos TVI: OBRAS/ENGENHARIA (5) + JUDICIAL/PERICIAL (4) + Ramo 6 v2 (TVI-30 a TVI-33)
"""Definições dos modelos TVI das categorias OBRAS/ENGENHARIA e JUDICIAL."""
from seed_tvi_base import CAMPOS_BASE

MODELOS_OBRAS = [
    {
        "nome": "Vistoria de Acompanhamento de Obra",
        "tipo": "obras_acompanhamento",
        "categoria": "OBRAS E ENGENHARIA",
        "descricao": "Registro periódico do andamento de obra com medição de avanço físico",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_medicao",      "label": "Número da Medição",         "type": "number"},
            {"key": "percentual_avanco",   "label": "% de Avanço Físico",        "type": "number"},
            {"key": "etapa_atual",         "label": "Etapa Atual da Obra",       "type": "text"},
            {"key": "prazo_previsto",      "label": "Prazo Previsto (data)",      "type": "date"},
            {"key": "responsavel_obra",    "label": "Responsável pela Obra",     "type": "text"},
            {"key": "art_obra",            "label": "ART da Obra",               "type": "text"},
            {"key": "desvios_projeto",     "label": "Desvios do Projeto",        "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Entrega de Obra",
        "tipo": "obras_entrega",
        "categoria": "OBRAS E ENGENHARIA",
        "descricao": "Registro técnico na entrega final da obra ao contratante",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "art_obra",            "label": "ART da Obra",               "type": "text"},
            {"key": "habite_se",           "label": "Habite-se / Auto de Conclusão","type": "text"},
            {"key": "pendencias_obra",     "label": "Pendências da Obra",        "type": "textarea"},
            {"key": "garantias_construtora","label": "Garantias da Construtora", "type": "textarea"},
            {"key": "manual_proprietario", "label": "Manual do Proprietário",    "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Patologias",
        "tipo": "obras_patologias",
        "categoria": "OBRAS E ENGENHARIA",
        "descricao": "Identificação e diagnóstico de patologias construtivas",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "tipos_patologias",    "label": "Tipos de Patologias",       "type": "textarea"},
            {"key": "origem_causa",        "label": "Origem/Causa",              "type": "textarea"},
            {"key": "nivel_criticidade",   "label": "Nível de Criticidade",
             "type": "select", "options": ["Baixo", "Médio", "Alto", "Crítico"]},
            {"key": "intervencao_proposta","label": "Intervenção Proposta",      "type": "textarea"},
            {"key": "custo_estimado",      "label": "Custo Estimado (R$)",       "type": "number"},
        ],
    },
    {
        "nome": "Vistoria Estrutural",
        "tipo": "obras_estrutural",
        "categoria": "OBRAS E ENGENHARIA",
        "descricao": "Avaliação técnica da integridade estrutural do imóvel",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "tipo_estrutura",      "label": "Tipo de Estrutura",         "type": "text"},
            {"key": "anomalias_estruturais","label": "Anomalias Estruturais",    "type": "textarea"},
            {"key": "risco_colapso",       "label": "Risco de Colapso",
             "type": "select", "options": ["Nulo", "Baixo", "Médio", "Alto", "Iminente"]},
            {"key": "laudo_art",           "label": "ART do Laudo",              "type": "text"},
            {"key": "recomendacoes",       "label": "Recomendações",             "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Conformidade (Projeto vs. Executado)",
        "tipo": "obras_conformidade",
        "categoria": "OBRAS E ENGENHARIA",
        "descricao": "Comparação entre o projeto aprovado e a obra executada",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_projeto",      "label": "Número do Projeto Aprovado","type": "text"},
            {"key": "divergencias",        "label": "Divergências Encontradas",  "type": "textarea"},
            {"key": "area_projeto_m2",     "label": "Área do Projeto (m²)",      "type": "number"},
            {"key": "area_executada_m2",   "label": "Área Executada (m²)",       "type": "number"},
            {"key": "regularizacao_necessaria","label": "Regularização Necessária","type": "textarea"},
        ],
    },
]

MODELOS_JUDICIAL = [
    {
        "nome": "Vistoria Pericial Judicial",
        "tipo": "judicial_pericial",
        "categoria": "JUDICIAL/PERICIAL",
        "descricao": "Vistoria técnica para fins periciais em processo judicial",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_processo",     "label": "Número do Processo",        "type": "text"},
            {"key": "vara_tribunal",       "label": "Vara / Tribunal",           "type": "text"},
            {"key": "juiz",                "label": "Juiz",                      "type": "text"},
            {"key": "requerente",          "label": "Requerente",                "type": "text"},
            {"key": "requerido",           "label": "Requerido",                 "type": "text"},
            {"key": "objeto_pericia",      "label": "Objeto da Perícia",         "type": "textarea"},
            {"key": "quesitos",            "label": "Quesitos",                  "type": "textarea"},
            {"key": "respostas_quesitos",  "label": "Respostas aos Quesitos",    "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria Técnica Extrajudicial",
        "tipo": "judicial_extrajudicial",
        "categoria": "JUDICIAL/PERICIAL",
        "descricao": "Vistoria técnica para fins extrajudiciais (câmaras arbitrais, mediação)",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "camara_arbitral",     "label": "Câmara Arbitral",           "type": "text"},
            {"key": "numero_arbitragem",   "label": "Número da Arbitragem",      "type": "text"},
            {"key": "partes_envolvidas",   "label": "Partes Envolvidas",         "type": "textarea"},
            {"key": "objeto_controversia", "label": "Objeto da Controvérsia",    "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Produção de Provas",
        "tipo": "judicial_producao_provas",
        "categoria": "JUDICIAL/PERICIAL",
        "descricao": "Vistoria para produção antecipada de provas",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_processo",     "label": "Número do Processo",        "type": "text"},
            {"key": "urgencia",            "label": "Urgência da Prova",         "type": "textarea"},
            {"key": "fatos_a_provar",      "label": "Fatos a Provar",            "type": "textarea"},
            {"key": "evidencias_coletadas","label": "Evidências Coletadas",      "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Indenização",
        "tipo": "judicial_indenizacao",
        "categoria": "JUDICIAL/PERICIAL",
        "descricao": "Vistoria para quantificação de danos e indenização",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_processo",     "label": "Número do Processo",        "type": "text"},
            {"key": "causa_dano",          "label": "Causa do Dano",             "type": "textarea"},
            {"key": "descricao_danos",     "label": "Descrição dos Danos",       "type": "textarea"},
            {"key": "valor_indenizacao",   "label": "Valor da Indenização (R$)", "type": "number"},
            {"key": "criterio_calculo",    "label": "Critério de Cálculo",       "type": "textarea"},
        ],
    },
]

# ─── Ramo 6 — Schema v2 (TVI-30 a TVI-33) ──────────────────────────────────
# v2 campos profissionais — schema novo com id, ramo, aplicacao, normas, requer_art
from seed_tvi_ramo6 import MODELOS_RAMO6
