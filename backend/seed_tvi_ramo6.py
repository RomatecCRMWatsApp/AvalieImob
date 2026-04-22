# @module seed_tvi_ramo6 — Ramo 6: JUDICIAL/PERICIAL (TVI-30 a TVI-33)
"""Modelos TVI do Ramo 6 — Judicial/Pericial com novo schema profissional v2."""

MODELOS_RAMO6 = [
    # ─── TVI-30 ─── Pericial Judicial ──────────────────────────────────────────
    {
        "id": "TVI-30",
        "nome": "Vistoria Pericial Judicial",
        "ramo": "JUDICIAL/PERICIAL",
        "aplicacao": "Vistoria técnica determinada por juízo para subsidiar decisão judicial",
        "normas": ["CPC Art. 156-158", "NBR 14653-1", "IBAPE - Norma de Perícias"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "numero_processo",
                "secao": "Identificação Processual",
                "tipo": "text",
                "label": "Número do Processo",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0000000-00.0000.0.00.0000",
                "ajuda": "Número CNJ do processo judicial"
            },
            {
                "id": "vara_comarca_tribunal",
                "secao": "Identificação Processual",
                "tipo": "text",
                "label": "Vara / Comarca / Tribunal",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Ex.: 3ª Vara Cível - Comarca de Belém/PA",
                "ajuda": "Identificação completa do juízo competente"
            },
            {
                "id": "autor",
                "secao": "Partes do Processo",
                "tipo": "text",
                "label": "Autor (Nome completo)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Nome do autor/requerente",
                "ajuda": "Parte autora conforme petição inicial"
            },
            {
                "id": "reu",
                "secao": "Partes do Processo",
                "tipo": "text",
                "label": "Réu (Nome completo)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Nome do réu/requerido",
                "ajuda": "Parte ré conforme citação"
            },
            {
                "id": "quesitos_juizo",
                "secao": "Quesitos",
                "tipo": "tabela",
                "label": "Quesitos do Juízo",
                "opcoes": ["nº", "Quesito", "Resposta"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Quesitos formulados pelo juízo e respectivas respostas técnicas"
            },
            {
                "id": "quesitos_autor",
                "secao": "Quesitos",
                "tipo": "tabela",
                "label": "Quesitos do Autor",
                "opcoes": ["nº", "Quesito", "Resposta"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Quesitos formulados pela parte autora e respectivas respostas"
            },
            {
                "id": "quesitos_reu",
                "secao": "Quesitos",
                "tipo": "tabela",
                "label": "Quesitos do Réu",
                "opcoes": ["nº", "Quesito", "Resposta"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Quesitos formulados pela parte ré e respectivas respostas"
            },
            {
                "id": "assistentes_tecnicos",
                "secao": "Assistentes Técnicos",
                "tipo": "caixa_texto",
                "label": "Assistentes Técnicos das Partes",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Nome, CREA/CAU e parte que representa",
                "ajuda": "Assistentes técnicos indicados pelas partes presentes na diligência"
            },
            {
                "id": "data_pericia",
                "secao": "Execução",
                "tipo": "data",
                "label": "Data da Perícia",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Data de realização da diligência pericial"
            },
            {
                "id": "prazo_entrega",
                "secao": "Execução",
                "tipo": "data",
                "label": "Prazo de Entrega do Laudo",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Data limite determinada pelo juízo para entrega do laudo"
            },
            {
                "id": "fundamento_legal",
                "secao": "Fundamentação",
                "tipo": "caixa_texto",
                "label": "Fundamento Legal e Normativo",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Arts., normas ABNT, referências técnicas aplicadas",
                "ajuda": "Base legal e normativa utilizada na elaboração do laudo pericial"
            },
        ],
    },

    # ─── TVI-31 ─── Extrajudicial ────────────────────────────────────────────
    {
        "id": "TVI-31",
        "nome": "Vistoria Técnica Extrajudicial",
        "ramo": "JUDICIAL/PERICIAL",
        "aplicacao": "Vistoria para câmaras de mediação, arbitragem, seguro ou solicitação particular",
        "normas": ["Lei 9.307/1996 - Arbitragem", "Lei 13.140/2015 - Mediação", "NBR 14653-1"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "solicitante_nome",
                "secao": "Solicitante",
                "tipo": "text",
                "label": "Nome do Solicitante",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Nome completo ou razão social",
                "ajuda": "Pessoa física ou jurídica que solicitou a vistoria"
            },
            {
                "id": "solicitante_cpf_cnpj",
                "secao": "Solicitante",
                "tipo": "text",
                "label": "CPF / CNPJ do Solicitante",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "000.000.000-00 ou 00.000.000/0000-00",
                "ajuda": "Documento de identificação do solicitante"
            },
            {
                "id": "finalidade",
                "secao": "Finalidade",
                "tipo": "select",
                "label": "Finalidade da Vistoria",
                "opcoes": ["Mediação", "Arbitragem", "Seguro", "Particular"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Objetivo principal da vistoria extrajudicial"
            },
            {
                "id": "quesitos_solicitante",
                "secao": "Quesitos",
                "tipo": "tabela",
                "label": "Quesitos do Solicitante",
                "opcoes": ["nº", "Quesito", "Resposta"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Questões técnicas formuladas pelo solicitante e respostas"
            },
            {
                "id": "documentos_analisados",
                "secao": "Documentação",
                "tipo": "multiselect",
                "label": "Documentos Analisados",
                "opcoes": [
                    "Escritura / Matrícula",
                    "Projeto Aprovado",
                    "Habite-se",
                    "IPTU",
                    "Fotos anteriores",
                    "Contrato de locação",
                    "Laudo anterior",
                    "Apólice de seguro",
                    "Nota fiscal de materiais",
                    "ART/RRT",
                    "Memorial descritivo",
                    "Planta cadastral"
                ],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Documentos analisados durante a elaboração da vistoria"
            },
            {
                "id": "ressalvas_limitacoes",
                "secao": "Limitações",
                "tipo": "caixa_texto",
                "label": "Ressalvas e Limitações",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Descreva ressalvas, limitações de acesso ou restrições ao trabalho",
                "ajuda": "Condicionantes que limitaram ou restringiram o trabalho técnico"
            },
        ],
    },

    # ─── TVI-32 ─── Produção de Provas ────────────────────────────────────────
    {
        "id": "TVI-32",
        "nome": "Vistoria de Produção de Provas",
        "ramo": "JUDICIAL/PERICIAL",
        "aplicacao": "Vistoria para produção antecipada de provas com cadeia de custódia",
        "normas": ["CPC Art. 381-383", "NBR 14653-1", "IBAPE - Norma de Perícias"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "fatos_a_provar",
                "secao": "Objeto da Prova",
                "tipo": "caixa_texto",
                "label": "Fatos a Provar",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Descreva detalhadamente os fatos que se pretende provar",
                "ajuda": "Fatos técnicos a serem documentados e comprovados pela vistoria"
            },
            {
                "id": "evidencias_fisicas",
                "secao": "Evidências",
                "tipo": "tabela",
                "label": "Evidências Físicas",
                "opcoes": ["nº", "Descrição", "Local", "Foto nº"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Inventário detalhado de cada evidência física coletada"
            },
            {
                "id": "documentacao_geolocalizada",
                "secao": "Evidências",
                "tipo": "caixa_texto",
                "label": "Documentação Geolocalizada",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Coordenadas GPS, data/hora EXIF das fotos, etc.",
                "ajuda": "Registros com geolocalização e timestamp para autenticidade das provas"
            },
            {
                "id": "cadeia_custodia",
                "secao": "Custódia",
                "tipo": "caixa_texto",
                "label": "Cadeia de Custódia",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Descreva o protocolo de custódia das evidências",
                "ajuda": "Procedimento que garante a integridade e autenticidade das evidências"
            },
            {
                "id": "testemunhas",
                "secao": "Testemunhas",
                "tipo": "tabela",
                "label": "Testemunhas Presentes",
                "opcoes": ["Nome", "CPF", "Contato"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Pessoas presentes na diligência que podem atestar os fatos"
            },
        ],
    },

    # ─── TVI-33 ─── Indenização ────────────────────────────────────────────────
    {
        "id": "TVI-33",
        "nome": "Vistoria de Indenização",
        "ramo": "JUDICIAL/PERICIAL",
        "aplicacao": "Vistoria para quantificação de danos e cálculo de indenização",
        "normas": ["NBR 14653-1", "NBR 14653-3", "IBAPE - Norma de Perícias", "CC Art. 186/927"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "evento_causador_data",
                "secao": "Evento",
                "tipo": "data",
                "label": "Data do Evento Causador",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Data em que ocorreu o evento que gerou os danos"
            },
            {
                "id": "evento_causador_tipo",
                "secao": "Evento",
                "tipo": "select",
                "label": "Tipo do Evento Causador",
                "opcoes": ["Incêndio", "Enchente", "Desabamento", "Vendaval", "Explosão", "Outro"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Natureza do evento que gerou os danos a serem indenizados"
            },
            {
                "id": "danos_materiais",
                "secao": "Danos",
                "tipo": "tabela",
                "label": "Danos Materiais",
                "opcoes": ["Item", "Descrição do Dano", "Valor R$"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Relação detalhada de cada dano material com valor estimado"
            },
            {
                "id": "total_perdas",
                "secao": "Danos",
                "tipo": "number",
                "label": "Total das Perdas (R$)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0,00",
                "ajuda": "Somatório de todos os danos materiais apurados"
            },
            {
                "id": "metodologia_valoracao",
                "secao": "Metodologia",
                "tipo": "select",
                "label": "Metodologia de Valoração",
                "opcoes": [
                    "Custo de Reprodução Novo (CRN)",
                    "Custo de Reprodução Depreciado (CRD)",
                    "Valor de Mercado",
                    "Orçamento Paramétrico",
                    "Tabela SINAPI",
                    "Tabela SEINFRA/SIURB",
                    "Nota Fiscal / NF-e"
                ],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Método técnico utilizado para valorar os danos"
            },
            {
                "id": "responsavel_dano",
                "secao": "Responsabilidade",
                "tipo": "text",
                "label": "Responsável pelo Dano",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Nome / razão social do responsável",
                "ajuda": "Parte identificada como causadora dos danos"
            },
            {
                "id": "cobertura_seguro",
                "secao": "Seguro",
                "tipo": "caixa_texto",
                "label": "Cobertura de Seguro",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Seguradora, nº apólice, coberturas e valor segurado",
                "ajuda": "Informações sobre cobertura securitária existente para os danos"
            },
        ],
    },
]
