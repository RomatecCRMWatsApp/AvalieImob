# @module seed_tvi_ramo7 — Ramo 7: SEGURANÇA/SINISTROS (TVI-34 a TVI-36)
"""Modelos TVI do Ramo 7 — Segurança e Sinistros com novo schema profissional v2."""

MODELOS_RAMO7 = [
    # ─── TVI-34 ─── Pós-Sinistro ────────────────────────────────────────────────
    {
        "id": "TVI-34",
        "nome": "Vistoria Pós-Sinistro",
        "ramo": "SEGURANÇA/SINISTROS",
        "aplicacao": "Registro técnico de imóvel após sinistro para subsídio de seguro ou ação legal",
        "normas": ["NBR 14653-1", "NBR 15575", "Susep - Circular 256/2004"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "tipo_sinistro",
                "secao": "Identificação do Sinistro",
                "tipo": "select",
                "label": "Tipo de Sinistro",
                "opcoes": ["Incêndio", "Enchente", "Vendaval", "Desmoronamento", "Explosão"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Natureza do evento sinistral ocorrido"
            },
            {
                "id": "data_hora_sinistro",
                "secao": "Identificação do Sinistro",
                "tipo": "data",
                "label": "Data / Hora do Sinistro",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Data e horário aproximado da ocorrência do sinistro"
            },
            {
                "id": "orgaos_acionados",
                "secao": "Atendimento",
                "tipo": "multiselect",
                "label": "Órgãos Acionados",
                "opcoes": ["Corpo de Bombeiros", "Defesa Civil", "Polícia Militar", "Polícia Civil", "SAMU", "Prefeitura"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Órgãos públicos que atenderam a ocorrência"
            },
            {
                "id": "bo_numero",
                "secao": "Atendimento",
                "tipo": "text",
                "label": "Boletim de Ocorrência (BO) nº",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Nº do BO ou relatório do Corpo de Bombeiros",
                "ajuda": "Número do boletim de ocorrência registrado pelos órgãos de atendimento"
            },
            {
                "id": "extensao_danos_percentual",
                "secao": "Extensão dos Danos",
                "tipo": "number",
                "label": "Extensão dos Danos (% da edificação)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0 a 100",
                "ajuda": "Percentual estimado da área ou valor da edificação afetado pelo sinistro"
            },
            {
                "id": "risco_colapso",
                "secao": "Avaliação de Risco",
                "tipo": "select",
                "label": "Risco de Colapso",
                "opcoes": ["Imediato", "Potencial", "Nenhum"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Avaliação do risco estrutural de colapso após o sinistro"
            },
            {
                "id": "interdicao",
                "secao": "Avaliação de Risco",
                "tipo": "select",
                "label": "Interdição",
                "opcoes": ["Total", "Parcial", "Nenhuma"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Nível de interdição recomendado ou já aplicado ao imóvel"
            },
            {
                "id": "custo_recuperacao_estimado",
                "secao": "Valoração",
                "tipo": "number",
                "label": "Custo de Recuperação Estimado (R$)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0,00",
                "ajuda": "Estimativa do custo total de recuperação do imóvel ao estado pré-sinistro"
            },
        ],
    },

    # ─── TVI-35 ─── Risco ────────────────────────────────────────────────────────
    {
        "id": "TVI-35",
        "nome": "Vistoria de Risco",
        "ramo": "SEGURANÇA/SINISTROS",
        "aplicacao": "Avaliação técnica de riscos com recomendação de medidas emergenciais",
        "normas": ["NBR 14653-1", "NBR 15575", "Resolução CONAMA 1/1986", "NBR 11682 - Estabilidade de Taludes"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "tipo_risco",
                "secao": "Identificação do Risco",
                "tipo": "multiselect",
                "label": "Tipo de Risco",
                "opcoes": ["Queda", "Desabamento", "Incêndio", "Inundação", "Deslizamento"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Tipos de risco identificados no imóvel ou área"
            },
            {
                "id": "nivel_risco",
                "secao": "Identificação do Risco",
                "tipo": "select",
                "label": "Nível de Risco",
                "opcoes": ["Baixo", "Médio", "Alto", "Iminente"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Nível geral de risco avaliado pelo técnico"
            },
            {
                "id": "ocupantes_em_risco",
                "secao": "Impacto Humano",
                "tipo": "number",
                "label": "Número de Ocupantes em Risco",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0",
                "ajuda": "Estimativa de pessoas expostas ao risco identificado"
            },
            {
                "id": "desocupacao",
                "secao": "Impacto Humano",
                "tipo": "select",
                "label": "Desocupação",
                "opcoes": ["Sim", "Não", "Parcial"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Necessidade de desocupação total, parcial ou não necessária"
            },
            {
                "id": "medidas_emergenciais",
                "secao": "Providências",
                "tipo": "caixa_texto",
                "label": "Medidas Emergenciais Recomendadas",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Descreva as medidas técnicas emergenciais recomendadas",
                "ajuda": "Ações imediatas necessárias para mitigar o risco identificado"
            },
            {
                "id": "prazo_providencias",
                "secao": "Providências",
                "tipo": "select",
                "label": "Prazo para Providências",
                "opcoes": ["Horas", "Dias", "Semanas"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Urgência estimada para implementação das medidas recomendadas"
            },
            {
                "id": "notificacao_defesa_civil",
                "secao": "Comunicações",
                "tipo": "checkbox",
                "label": "Notificação à Defesa Civil",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Marque se foi realizada ou recomendada notificação à Defesa Civil"
            },
        ],
    },

    # ─── TVI-36 ─── Seguro Imobiliário ────────────────────────────────────────
    {
        "id": "TVI-36",
        "nome": "Vistoria de Seguro Imobiliário",
        "ramo": "SEGURANÇA/SINISTROS",
        "aplicacao": "Vistoria para contratação, renovação ou liquidação de sinistro de seguro imobiliário",
        "normas": ["Circular Susep 256/2004", "NBR 14653-1", "Resolução CNSP 382/2020"],
        "requer_art": False,
        "campos_especificos": [
            {
                "id": "seguradora",
                "secao": "Apólice",
                "tipo": "text",
                "label": "Seguradora",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Nome da seguradora",
                "ajuda": "Empresa seguradora responsável pela apólice"
            },
            {
                "id": "apolice_numero",
                "secao": "Apólice",
                "tipo": "text",
                "label": "Apólice nº",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Número da apólice",
                "ajuda": "Número da apólice de seguro imobiliário"
            },
            {
                "id": "coberturas_contratadas",
                "secao": "Coberturas",
                "tipo": "multiselect",
                "label": "Coberturas Contratadas",
                "opcoes": [
                    "Incêndio",
                    "Raio",
                    "Explosão",
                    "Vendaval",
                    "Alagamento / Enchente",
                    "Desmoronamento",
                    "Danos Elétricos",
                    "Roubo / Furto Qualificado",
                    "Responsabilidade Civil",
                    "Perda de Aluguel",
                    "Vidros",
                    "Equipamentos Elétricos"
                ],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Coberturas expressamente contratadas na apólice"
            },
            {
                "id": "valor_segurado",
                "secao": "Valores",
                "tipo": "number",
                "label": "Valor Segurado (R$)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0,00",
                "ajuda": "Valor declarado segurado na apólice"
            },
            {
                "id": "valor_real",
                "secao": "Valores",
                "tipo": "number",
                "label": "Valor Real / de Mercado (R$)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0,00",
                "ajuda": "Valor real do imóvel apurado na vistoria"
            },
            {
                "id": "franquia",
                "secao": "Valores",
                "tipo": "number",
                "label": "Franquia (R$)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0,00",
                "ajuda": "Valor da franquia prevista na apólice"
            },
            {
                "id": "sinistro_coberto",
                "secao": "Sinistro",
                "tipo": "select",
                "label": "Sinistro Coberto",
                "opcoes": ["Sim", "Não", "Parcial"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Avaliação se o sinistro é coberto pela apólice vigente"
            },
            {
                "id": "valor_indenizavel",
                "secao": "Sinistro",
                "tipo": "number",
                "label": "Valor Indenizável (R$)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0,00",
                "ajuda": "Valor apurado como indenizável após análise técnica e contratual"
            },
            {
                "id": "documentacao_necessaria",
                "secao": "Documentação",
                "tipo": "multiselect",
                "label": "Documentação Necessária",
                "opcoes": [
                    "BO (Boletim de Ocorrência)",
                    "Fotos do sinistro",
                    "Nota fiscal de bens danificados",
                    "Orçamento de reparo",
                    "Contrato / Escritura do imóvel",
                    "IPTU",
                    "Laudo técnico",
                    "ART do laudo",
                    "Laudos de vistoria anteriores"
                ],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Documentos necessários para instrução do processo de sinistro"
            },
        ],
    },
]
