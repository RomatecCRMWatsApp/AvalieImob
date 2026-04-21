# @module seed_tvi — Modelos TVI: SEGURANÇA/SINISTROS (3) + COMERCIAL (3) + INSTALAÇÕES (4) + COMPLEMENTARES (5)
"""Definições dos modelos TVI das categorias finais."""
from seed_tvi_base import CAMPOS_BASE

MODELOS_SEGURANCA = [
    {
        "nome": "Vistoria Pós-Sinistro",
        "tipo": "seguranca_pos_sinistro",
        "categoria": "SEGURANÇA/SINISTROS",
        "descricao": "Registro técnico do imóvel após sinistro (incêndio, enchente, etc.)",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "tipo_sinistro",       "label": "Tipo de Sinistro",          "type": "text"},
            {"key": "data_sinistro",       "label": "Data do Sinistro",          "type": "date"},
            {"key": "areas_afetadas",      "label": "Áreas Afetadas",            "type": "textarea"},
            {"key": "valor_prejuizo",      "label": "Valor do Prejuízo (R$)",    "type": "number"},
            {"key": "seguradora",          "label": "Seguradora",                "type": "text"},
            {"key": "numero_sinistro",     "label": "Número do Sinistro",        "type": "text"},
        ],
    },
    {
        "nome": "Vistoria de Risco",
        "tipo": "seguranca_risco",
        "categoria": "SEGURANÇA/SINISTROS",
        "descricao": "Avaliação técnica de riscos no imóvel",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "tipos_risco",         "label": "Tipos de Risco Identificados","type": "textarea"},
            {"key": "nivel_risco",         "label": "Nível de Risco Geral",
             "type": "select", "options": ["Baixo", "Médio", "Alto", "Crítico"]},
            {"key": "medidas_mitigacao",   "label": "Medidas de Mitigação",      "type": "textarea"},
            {"key": "prazo_acao",          "label": "Prazo para Ação",           "type": "text"},
        ],
    },
    {
        "nome": "Vistoria de Seguro Imobiliário",
        "tipo": "seguranca_seguro",
        "categoria": "SEGURANÇA/SINISTROS",
        "descricao": "Vistoria para fins de contratação ou renovação de seguro imobiliário",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "seguradora",          "label": "Seguradora",                "type": "text"},
            {"key": "apolice",             "label": "Apólice",                   "type": "text"},
            {"key": "valor_segurado",      "label": "Valor Segurado (R$)",       "type": "number"},
            {"key": "coberturas",          "label": "Coberturas Contratadas",    "type": "textarea"},
            {"key": "ressalvas_seguro",    "label": "Ressalvas",                 "type": "textarea"},
        ],
    },
]

MODELOS_COMERCIAL = [
    {
        "nome": "Vistoria Comercial",
        "tipo": "comercial_comercial",
        "categoria": "COMERCIAL/INDUSTRIAL",
        "descricao": "Vistoria técnica de imóvel comercial",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "atividade_comercial", "label": "Atividade Comercial",       "type": "text"},
            {"key": "alvara_funcionamento","label": "Alvará de Funcionamento",   "type": "text"},
            {"key": "area_util_m2",        "label": "Área Útil (m²)",            "type": "number"},
            {"key": "instalacoes_especiais","label": "Instalações Especiais",    "type": "textarea"},
            {"key": "acessibilidade_nbr",  "label": "Conformidade ABNT NBR 9050","type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria Industrial",
        "tipo": "comercial_industrial",
        "categoria": "COMERCIAL/INDUSTRIAL",
        "descricao": "Vistoria técnica de imóvel industrial ou galpão",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "tipo_industria",      "label": "Tipo de Indústria",         "type": "text"},
            {"key": "area_construida_m2",  "label": "Área Construída (m²)",      "type": "number"},
            {"key": "pe_direito_m",        "label": "Pé-Direito (m)",            "type": "number"},
            {"key": "carga_piso_kgm2",     "label": "Carga de Piso (kg/m²)",    "type": "number"},
            {"key": "licencas_ambientais", "label": "Licenças Ambientais",       "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Equipamentos e Instalações",
        "tipo": "comercial_equipamentos",
        "categoria": "COMERCIAL/INDUSTRIAL",
        "descricao": "Inventário técnico de equipamentos e instalações do imóvel",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "lista_equipamentos",  "label": "Lista de Equipamentos",     "type": "textarea"},
            {"key": "estado_equipamentos", "label": "Estado dos Equipamentos",   "type": "textarea"},
            {"key": "vida_util_restante",  "label": "Vida Útil Restante",        "type": "textarea"},
            {"key": "valor_equipamentos",  "label": "Valor dos Equipamentos (R$)","type": "number"},
        ],
    },
]

MODELOS_INSTALACOES = [
    {
        "nome": "Vistoria de Instalações Elétricas",
        "tipo": "instalacoes_eletrica",
        "categoria": "INSTALAÇÕES",
        "descricao": "Avaliação técnica das instalações elétricas conforme NR-10 e ABNT",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "padrao_entrada",      "label": "Padrão de Entrada",         "type": "text"},
            {"key": "carga_instalada_kva", "label": "Carga Instalada (kVA)",     "type": "number"},
            {"key": "aterramento",         "label": "Aterramento",               "type": "text"},
            {"key": "disjuntores",         "label": "Quadro de Disjuntores",     "type": "textarea"},
            {"key": "conformidade_nr10",   "label": "Conformidade NR-10",        "type": "textarea"},
            {"key": "art_eletrica",        "label": "ART das Instalações",       "type": "text"},
        ],
    },
    {
        "nome": "Vistoria Hidrossanitária",
        "tipo": "instalacoes_hidrossanitaria",
        "categoria": "INSTALAÇÕES",
        "descricao": "Avaliação das instalações hidráulicas e sanitárias",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "pressao_rede",        "label": "Pressão da Rede (mca)",     "type": "number"},
            {"key": "material_tubulacao",  "label": "Material da Tubulação",     "type": "text"},
            {"key": "vazamentos",          "label": "Vazamentos Identificados",  "type": "textarea"},
            {"key": "esgoto_tipo",         "label": "Tipo de Esgoto",            "type": "text"},
            {"key": "caixa_gordura",       "label": "Caixa de Gordura",          "type": "text"},
        ],
    },
    {
        "nome": "Vistoria de Instalações de Gás",
        "tipo": "instalacoes_gas",
        "categoria": "INSTALAÇÕES",
        "descricao": "Avaliação das instalações de gás conforme NBR 13103",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "tipo_gas",            "label": "Tipo de Gás (GN/GLP)",      "type": "text"},
            {"key": "pressao_trabalho",    "label": "Pressão de Trabalho (mbar)","type": "number"},
            {"key": "teste_estanqueidade", "label": "Teste de Estanqueidade",    "type": "textarea"},
            {"key": "valvulas_seguranca",  "label": "Válvulas de Segurança",     "type": "textarea"},
            {"key": "art_gas",             "label": "ART das Instalações",       "type": "text"},
        ],
    },
    {
        "nome": "Vistoria de Sistemas de Combate a Incêndio",
        "tipo": "instalacoes_incendio",
        "categoria": "INSTALAÇÕES",
        "descricao": "Avaliação dos sistemas de proteção e combate a incêndio",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "auto_vistoria_cbmerj", "label": "Auto de Vistoria CBMERS/CBMERJ","type": "text"},
            {"key": "extintores",          "label": "Extintores",                "type": "textarea"},
            {"key": "hidrantes",           "label": "Sistema de Hidrantes",      "type": "textarea"},
            {"key": "sprinklers",          "label": "Sistema de Sprinklers",     "type": "textarea"},
            {"key": "saidas_emergencia",   "label": "Saídas de Emergência",      "type": "textarea"},
            {"key": "validade_avcb",       "label": "Validade AVCB",             "type": "date"},
        ],
    },
]

MODELOS_COMPLEMENTARES = [
    {
        "nome": "Relatório Fotográfico",
        "tipo": "complementar_relatorio_fotografico",
        "categoria": "COMPLEMENTARES",
        "descricao": "Relatório técnico com documentação fotográfica sistematizada",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "total_fotos",         "label": "Total de Fotografias",      "type": "number"},
            {"key": "equipamento_utilizado","label": "Equipamento Utilizado",    "type": "text"},
            {"key": "sistematizacao",      "label": "Sistematização das Fotos",  "type": "textarea"},
        ],
    },
    {
        "nome": "Checklist Técnico",
        "tipo": "complementar_checklist",
        "categoria": "COMPLEMENTARES",
        "descricao": "Lista de verificação técnica sistematizada por item",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "itens_verificados",   "label": "Itens Verificados",         "type": "textarea"},
            {"key": "itens_conforme",      "label": "Itens Conformes",           "type": "number"},
            {"key": "itens_nao_conforme",  "label": "Itens Não Conformes",       "type": "number"},
            {"key": "percentual_conformidade","label": "% de Conformidade",      "type": "number"},
        ],
    },
    {
        "nome": "Laudo Técnico",
        "tipo": "complementar_laudo_tecnico",
        "categoria": "COMPLEMENTARES",
        "descricao": "Laudo técnico com análise aprofundada e embasamento normativo",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "normas_referencias",  "label": "Normas de Referência",      "type": "textarea"},
            {"key": "analise_tecnica",     "label": "Análise Técnica",           "type": "textarea"},
            {"key": "fundamentos",         "label": "Fundamentos Técnicos",      "type": "textarea"},
            {"key": "recomendacoes",       "label": "Recomendações",             "type": "textarea"},
        ],
    },
    {
        "nome": "Parecer Técnico",
        "tipo": "complementar_parecer_tecnico",
        "categoria": "COMPLEMENTARES",
        "descricao": "Parecer técnico fundamentado sobre questão específica",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "questao_analisada",   "label": "Questão Analisada",         "type": "textarea"},
            {"key": "analise",             "label": "Análise",                   "type": "textarea"},
            {"key": "parecer",             "label": "Parecer",                   "type": "textarea"},
            {"key": "ressalvas",           "label": "Ressalvas",                 "type": "textarea"},
        ],
    },
    {
        "nome": "Auto de Constatação",
        "tipo": "complementar_auto_constatacao",
        "categoria": "COMPLEMENTARES",
        "descricao": "Documento técnico de constatação de fatos e situações",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "fatos_constatados",   "label": "Fatos Constatados",         "type": "textarea"},
            {"key": "testemunhas",         "label": "Testemunhas Presentes",     "type": "textarea"},
            {"key": "hora_constatacao",    "label": "Hora da Constatação",       "type": "time"},
            {"key": "providencias",        "label": "Providências Indicadas",    "type": "textarea"},
        ],
    },
]
