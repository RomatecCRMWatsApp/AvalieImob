# @module seed_tvi — Modelos TVI: GERAL (8) + LOCAÇÃO (4)
"""Definições dos modelos TVI das categorias GERAL e LOCAÇÃO."""
from seed_tvi_base import CAMPOS_BASE

MODELOS_GERAL = [
    {
        "nome": "Vistoria de Avaliação (PTAM)",
        "tipo": "geral_avaliacao_ptam",
        "categoria": "GERAL",
        "descricao": "Vistoria vinculada ao Parecer Técnico de Avaliação Mercadológica",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_ptam",         "label": "Número do PTAM",            "type": "text"},
            {"key": "metodo_avaliacao",    "label": "Método de Avaliação",       "type": "text"},
            {"key": "valor_estimado",      "label": "Valor Estimado (R$)",       "type": "number"},
            {"key": "grau_fundamentacao",  "label": "Grau de Fundamentação",     "type": "text"},
        ],
    },
    {
        "nome": "Vistoria de Compra e Venda",
        "tipo": "geral_compra_venda",
        "categoria": "GERAL",
        "descricao": "Vistoria do imóvel para fins de compra e venda",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "valor_negociado",     "label": "Valor Negociado (R$)",      "type": "number"},
            {"key": "condicoes_pagamento", "label": "Condições de Pagamento",    "type": "textarea"},
            {"key": "pendencias_documentais","label": "Pendências Documentais",  "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Entrega de Imóvel",
        "tipo": "geral_entrega",
        "categoria": "GERAL",
        "descricao": "Registro do estado do imóvel no momento da entrega ao novo ocupante",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "chaves_entregues",    "label": "Chaves Entregues",          "type": "text"},
            {"key": "leituras_medidores",  "label": "Leituras dos Medidores",    "type": "textarea"},
            {"key": "pendencias_entrega",  "label": "Pendências na Entrega",     "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Recebimento de Imóvel",
        "tipo": "geral_recebimento",
        "categoria": "GERAL",
        "descricao": "Registro do estado do imóvel no momento do recebimento",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "chaves_recebidas",    "label": "Chaves Recebidas",          "type": "text"},
            {"key": "leituras_medidores",  "label": "Leituras dos Medidores",    "type": "textarea"},
            {"key": "divergencias",        "label": "Divergências Observadas",   "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Conservação",
        "tipo": "geral_conservacao",
        "categoria": "GERAL",
        "descricao": "Avaliação periódica do estado de conservação do imóvel",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "grau_conservacao",    "label": "Grau de Conservação",       "type": "select",
             "options": ["Ótimo", "Bom", "Regular", "Ruim", "Péssimo"]},
            {"key": "intervencoes_necessarias","label": "Intervenções Necessárias","type": "textarea"},
            {"key": "prazo_intervencao",   "label": "Prazo para Intervenção",    "type": "text"},
        ],
    },
    {
        "nome": "Vistoria Cautelar de Vizinhança",
        "tipo": "geral_cautelar_vizinhanca",
        "categoria": "GERAL",
        "descricao": "Documentação do estado do imóvel vizinho antes de obras",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "obra_responsavel",    "label": "Responsável pela Obra",     "type": "text"},
            {"key": "obra_tipo",           "label": "Tipo de Obra",              "type": "text"},
            {"key": "distancia_obra_m",    "label": "Distância da Obra (m)",     "type": "number"},
            {"key": "patologias_pre",      "label": "Patologias Pré-existentes", "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria Pré-Ocupação",
        "tipo": "geral_pre_ocupacao",
        "categoria": "GERAL",
        "descricao": "Vistoria realizada antes da ocupação do imóvel",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "pendencias_construtoras","label": "Pendências da Construtora","type": "textarea"},
            {"key": "itens_aceitos",       "label": "Itens Aceitos",             "type": "textarea"},
            {"key": "itens_rejeitados",    "label": "Itens Rejeitados",          "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria Pós-Ocupação",
        "tipo": "geral_pos_ocupacao",
        "categoria": "GERAL",
        "descricao": "Avaliação do uso e desgastes após ocupação do imóvel",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "periodo_ocupacao",    "label": "Período de Ocupação",       "type": "text"},
            {"key": "desgastes_normais",   "label": "Desgastes por Uso Normal",  "type": "textarea"},
            {"key": "danos_indevidos",     "label": "Danos Indevidos",           "type": "textarea"},
        ],
    },
]

MODELOS_LOCACAO = [
    {
        "nome": "Vistoria de Entrada (Locação)",
        "tipo": "locacao_entrada",
        "categoria": "LOCAÇÃO",
        "descricao": "Registro do estado do imóvel no início do contrato de locação",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_contrato",     "label": "Número do Contrato",        "type": "text"},
            {"key": "data_inicio_locacao", "label": "Data de Início da Locação", "type": "date"},
            {"key": "valor_aluguel",       "label": "Valor do Aluguel (R$)",     "type": "number"},
            {"key": "nome_locatario",      "label": "Nome do Locatário",         "type": "text"},
            {"key": "leituras_medidores",  "label": "Leituras dos Medidores",    "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria de Saída (Locação)",
        "tipo": "locacao_saida",
        "categoria": "LOCAÇÃO",
        "descricao": "Registro do estado do imóvel ao término do contrato de locação",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_contrato",     "label": "Número do Contrato",        "type": "text"},
            {"key": "data_termino_locacao","label": "Data de Término",           "type": "date"},
            {"key": "nome_locatario",      "label": "Nome do Locatário",         "type": "text"},
            {"key": "leituras_medidores",  "label": "Leituras dos Medidores",    "type": "textarea"},
            {"key": "danos_ressarcimento", "label": "Danos para Ressarcimento",  "type": "textarea"},
            {"key": "desconto_deposito",   "label": "Desconto do Depósito (R$)", "type": "number"},
        ],
    },
    {
        "nome": "Vistoria de Renovação Contratual",
        "tipo": "locacao_renovacao",
        "categoria": "LOCAÇÃO",
        "descricao": "Vistoria realizada na renovação do contrato de locação",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_contrato",     "label": "Número do Contrato",        "type": "text"},
            {"key": "novo_valor_aluguel",  "label": "Novo Valor do Aluguel (R$)","type": "number"},
            {"key": "novo_prazo_meses",    "label": "Novo Prazo (meses)",        "type": "number"},
            {"key": "ajustes_negociados",  "label": "Ajustes Negociados",        "type": "textarea"},
        ],
    },
    {
        "nome": "Vistoria Periódica (Locação)",
        "tipo": "locacao_periodica",
        "categoria": "LOCAÇÃO",
        "descricao": "Vistoria de acompanhamento periódico durante a locação",
        "campos": CAMPOS_BASE,
        "campos_especificos": [
            {"key": "numero_contrato",     "label": "Número do Contrato",        "type": "text"},
            {"key": "periodicidade",       "label": "Periodicidade",             "type": "text"},
            {"key": "numero_vistoria",     "label": "Número da Vistoria",        "type": "number"},
            {"key": "ocorrencias",         "label": "Ocorrências Observadas",    "type": "textarea"},
        ],
    },
]
