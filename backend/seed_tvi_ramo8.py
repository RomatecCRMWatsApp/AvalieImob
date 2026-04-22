# @module seed_tvi_ramo8 — Ramo 8: COMERCIAL/INDUSTRIAL (TVI-37 a TVI-39)
"""Modelos TVI do Ramo 8 — Comercial e Industrial com novo schema profissional v2."""

MODELOS_RAMO8 = [
    # ─── TVI-37 ─── Comercial ────────────────────────────────────────────────────
    {
        "id": "TVI-37",
        "nome": "Vistoria Comercial",
        "ramo": "COMERCIAL/INDUSTRIAL",
        "aplicacao": "Vistoria técnica de imóvel comercial com verificação de alvarás, acessibilidade e segurança",
        "normas": ["NBR 9050 - Acessibilidade", "NBR 14653-1", "Decreto 56.819/2011-SP (AVCB)", "CLT/NRs"],
        "requer_art": False,
        "campos_especificos": [
            {
                "id": "atividade_exercida",
                "secao": "Atividade",
                "tipo": "text",
                "label": "Atividade Exercida",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Ex.: Supermercado, Restaurante, Escritório",
                "ajuda": "Descrição da atividade comercial exercida no imóvel"
            },
            {
                "id": "cnae",
                "secao": "Atividade",
                "tipo": "text",
                "label": "CNAE",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0000-0/00",
                "ajuda": "Classificação Nacional de Atividades Econômicas do estabelecimento"
            },
            {
                "id": "alvara",
                "secao": "Licenças",
                "tipo": "select",
                "label": "Alvará de Funcionamento",
                "opcoes": ["Válido", "Vencido", "Inexistente"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Situação do alvará de funcionamento municipal"
            },
            {
                "id": "avcb",
                "secao": "Licenças",
                "tipo": "select",
                "label": "AVCB (Auto de Vistoria do Corpo de Bombeiros)",
                "opcoes": ["Válido", "Vencido", "Inexistente"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Situação do AVCB expedido pelo Corpo de Bombeiros"
            },
            {
                "id": "vigilancia_sanitaria",
                "secao": "Licenças",
                "tipo": "select",
                "label": "Vigilância Sanitária",
                "opcoes": ["Conforme", "Pendente", "N/A"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Situação do licenciamento sanitário (para atividades que exijam)"
            },
            {
                "id": "acessibilidade_nbr9050",
                "secao": "Acessibilidade",
                "tipo": "select",
                "label": "Acessibilidade NBR 9050",
                "opcoes": ["Conforme", "Parcial", "Não Conforme"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Nível de conformidade com a NBR 9050 de acessibilidade"
            },
            {
                "id": "lotacao_maxima",
                "secao": "Segurança",
                "tipo": "number",
                "label": "Lotação Máxima (pessoas)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0",
                "ajuda": "Capacidade máxima de ocupantes permitida no estabelecimento"
            },
            {
                "id": "saidas_emergencia",
                "secao": "Segurança",
                "tipo": "number",
                "label": "Saídas de Emergência (quantidade)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0",
                "ajuda": "Número de saídas de emergência devidamente sinalizadas e desobstruídas"
            },
            {
                "id": "sinalizacao",
                "secao": "Segurança",
                "tipo": "multiselect",
                "label": "Sinalização de Segurança",
                "opcoes": ["Saída de emergência", "Extintores", "Hidrante", "Rota de fuga", "Iluminação de emergência"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Tipos de sinalização de segurança presentes e conformes"
            },
        ],
    },

    # ─── TVI-38 ─── Industrial ────────────────────────────────────────────────────
    {
        "id": "TVI-38",
        "nome": "Vistoria Industrial",
        "ramo": "COMERCIAL/INDUSTRIAL",
        "aplicacao": "Vistoria técnica de indústria, galpão ou instalação fabril com verificação ambiental e NRs",
        "normas": ["NBR 14653-1", "NR-10", "NR-12", "NR-20", "NR-33", "NR-35", "Resolução CONAMA 237/1997"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "atividade_cnae",
                "secao": "Atividade",
                "tipo": "text",
                "label": "Atividade / CNAE",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Atividade e código CNAE",
                "ajuda": "Atividade industrial exercida e respectivo código CNAE"
            },
            {
                "id": "licenca_ambiental",
                "secao": "Licenças Ambientais",
                "tipo": "select",
                "label": "Licença Ambiental",
                "opcoes": [
                    "LP (Licença Prévia) - Válida",
                    "LP (Licença Prévia) - Vencida",
                    "LI (Licença de Instalação) - Válida",
                    "LI (Licença de Instalação) - Vencida",
                    "LO (Licença de Operação) - Válida",
                    "LO (Licença de Operação) - Vencida",
                    "Dispensada",
                    "Inexistente"
                ],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Tipo e situação da licença ambiental vigente"
            },
            {
                "id": "licenca_semma_sema",
                "secao": "Licenças Ambientais",
                "tipo": "text",
                "label": "Licença SEMMA / SEMA / SEMAS",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Nº e validade da licença estadual/municipal",
                "ajuda": "Licença ambiental estadual ou municipal complementar"
            },
            {
                "id": "efluentes",
                "secao": "Meio Ambiente",
                "tipo": "caixa_texto",
                "label": "Efluentes: Tratamento e Destinação",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Descreva o tratamento e destinação dos efluentes líquidos",
                "ajuda": "Sistema de tratamento e disposição final dos efluentes industriais"
            },
            {
                "id": "residuos_solidos",
                "secao": "Meio Ambiente",
                "tipo": "tabela",
                "label": "Resíduos Sólidos",
                "opcoes": ["Tipo", "Classe (I/IIA/IIB)", "Destinação", "Manifesto nº"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Inventário de resíduos sólidos industriais conforme PNRS/Lei 12.305/2010"
            },
            {
                "id": "estruturas_especiais",
                "secao": "Instalações Especiais",
                "tipo": "multiselect",
                "label": "Estruturas Especiais",
                "opcoes": ["Silos", "Tanques", "Pontes rolantes", "Fornos", "Caldeiras"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Equipamentos e estruturas especiais presentes na instalação"
            },
            {
                "id": "nrs_aplicaveis",
                "secao": "Normas Regulamentadoras",
                "tipo": "multiselect",
                "label": "NRs Aplicáveis",
                "opcoes": ["NR-10 (Elétrica)", "NR-12 (Máquinas)", "NR-20 (Inflamáveis)", "NR-33 (Espaço confinado)", "NR-35 (Trabalho em altura)"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Normas Regulamentadoras do MTE aplicáveis à atividade industrial"
            },
        ],
    },

    # ─── TVI-39 ─── Equipamentos ─────────────────────────────────────────────────
    {
        "id": "TVI-39",
        "nome": "Vistoria de Equipamentos",
        "ramo": "COMERCIAL/INDUSTRIAL",
        "aplicacao": "Inventário técnico e avaliação de equipamentos industriais ou comerciais",
        "normas": ["NBR 14653-1", "NBR 14653-5 - Máquinas e Equipamentos", "NR-12", "NR-13"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "inventario_equipamentos",
                "secao": "Inventário",
                "tipo": "tabela",
                "label": "Inventário de Equipamentos",
                "opcoes": ["Item", "Marca", "Modelo", "Ano", "Estado", "ART nº", "Última Manutenção"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Relação completa dos equipamentos com dados técnicos e de manutenção"
            },
            {
                "id": "laudo_tecnico_equipamento",
                "secao": "Laudos",
                "tipo": "checkbox",
                "label": "Laudo Técnico por Equipamento (ART)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Confirme se cada equipamento do inventário possui laudo técnico com ART"
            },
            {
                "id": "manutencao_preventiva",
                "secao": "Manutenção",
                "tipo": "select",
                "label": "Manutenção Preventiva em Dia",
                "opcoes": ["Sim, todos os equipamentos", "Parcial", "Não"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Situação geral da manutenção preventiva do parque de equipamentos"
            },
            {
                "id": "vida_util_residual",
                "secao": "Avaliação",
                "tipo": "caixa_texto",
                "label": "Vida Útil Residual Estimada",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Ex.: Equipamento A: 5 anos; Equipamento B: 2 anos",
                "ajuda": "Estimativa de vida útil remanescente por equipamento ou conjunto"
            },
        ],
    },
]
