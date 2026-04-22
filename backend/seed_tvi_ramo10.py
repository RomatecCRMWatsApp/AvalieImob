# @module seed_tvi_ramo10 — Ramo 10: COMPLEMENTARES (TVI-44 a TVI-45)
"""Modelos TVI do Ramo 10 — Complementares com novo schema profissional v2."""

MODELOS_RAMO10 = [
    # ─── TVI-44 ─── Relatório Fotográfico ────────────────────────────────────
    {
        "id": "TVI-44",
        "nome": "Relatório Fotográfico Técnico",
        "ramo": "COMPLEMENTARES",
        "aplicacao": "Documentação fotográfica sistematizada e geolocalizada do imóvel vistoriado",
        "normas": ["NBR 14653-1 - Anexo de Registro Fotográfico", "IBAPE - Norma de Vistorias"],
        "requer_art": False,
        "campos_especificos": [
            {
                "id": "grid_fotos",
                "secao": "Registro Fotográfico",
                "tipo": "tabela",
                "label": "Grid de Fotos (12 slots)",
                "opcoes": ["nº", "Foto (referência)", "Local", "Descrição", "Data", "Geolocalização"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Registro sistemático de até 12 fotos com localização e descrição de cada imagem"
            },
            {
                "id": "equipamento_fotografico",
                "secao": "Equipamento",
                "tipo": "text",
                "label": "Equipamento Fotográfico",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Ex.: Smartphone Samsung Galaxy S23, câmera Sony A7",
                "ajuda": "Dispositivo utilizado para o registro fotográfico"
            },
            {
                "id": "condicoes_luz",
                "secao": "Condições",
                "tipo": "select",
                "label": "Condições de Iluminação",
                "opcoes": ["Natural", "Artificial", "Mista"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Condições de iluminação predominantes durante o registro fotográfico"
            },
            {
                "id": "indice_fotos",
                "secao": "Índice",
                "tipo": "tabela",
                "label": "Índice de Fotos (Referência Cruzada)",
                "opcoes": ["Foto nº", "Ambiente/Local", "Referência no Laudo"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Tabela de referência cruzada vinculando cada foto ao item do laudo correspondente"
            },
        ],
    },

    # ─── TVI-45 ─── Checklist Técnico ─────────────────────────────────────────
    {
        "id": "TVI-45",
        "nome": "Checklist Técnico",
        "ramo": "COMPLEMENTARES",
        "aplicacao": "Lista de verificação técnica sistematizada com 100 itens agrupados por grupo e pontuação",
        "normas": ["NBR 15575 - Desempenho", "NBR 9050 - Acessibilidade", "NBR 14653-1"],
        "requer_art": False,
        "campos_especificos": [
            # ── Grupo 1: Estrutura (15 itens) ─────────────────────────────
            {
                "id": "checklist_estrutura",
                "secao": "Grupo 1 — Estrutura (15 itens)",
                "tipo": "tabela",
                "label": "Estrutura",
                "opcoes": [
                    "Item",
                    "Conforme",
                    "Não Conforme",
                    "N/A"
                ],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": (
                    "1-Fundações aparentemente estáveis | 2-Pilares sem fissuras | "
                    "3-Vigas sem fissuras | 4-Lajes sem flechas | 5-Paredes estruturais íntegras | "
                    "6-Sem deformações excessivas | 7-Sem recalques visíveis | 8-Junta de dilatação OK | "
                    "9-Sem armadura exposta | 10-Sem eflorescência estrutural | 11-Concreto sem carbonatação visível | "
                    "12-Sem sinais de colapso iminente | 13-Estrutura metálica sem corrosão | "
                    "14-Madeiramento sem deterioração | 15-Interligação estrutural adequada"
                )
            },
            {
                "id": "pontuacao_estrutura",
                "secao": "Grupo 1 — Estrutura (15 itens)",
                "tipo": "number",
                "label": "Pontuação — Estrutura (0-100%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Percentual de conformidade do grupo Estrutura"
            },

            # ── Grupo 2: Vedação (12 itens) ───────────────────────────────
            {
                "id": "checklist_vedacao",
                "secao": "Grupo 2 — Vedação (12 itens)",
                "tipo": "tabela",
                "label": "Vedação",
                "opcoes": ["Item", "Conforme", "Não Conforme", "N/A"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": (
                    "1-Alvenaria sem fissuras | 2-Revestimento externo íntegro | "
                    "3-Revestimento interno íntegro | 4-Sem umidade ascendente | "
                    "5-Sem manchas de infiltração | 6-Esquadrias sem folgas | "
                    "7-Caixilhos sem corrosão | 8-Vedantes e silicones OK | "
                    "9-Soleiras e peitoris íntegros | 10-Juntas de assentamento OK | "
                    "11-Paredes sem empolamento | 12-Pintura em bom estado"
                )
            },
            {
                "id": "pontuacao_vedacao",
                "secao": "Grupo 2 — Vedação (12 itens)",
                "tipo": "number",
                "label": "Pontuação — Vedação (0-100%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Percentual de conformidade do grupo Vedação"
            },

            # ── Grupo 3: Cobertura (10 itens) ─────────────────────────────
            {
                "id": "checklist_cobertura",
                "secao": "Grupo 3 — Cobertura (10 itens)",
                "tipo": "tabela",
                "label": "Cobertura",
                "opcoes": ["Item", "Conforme", "Não Conforme", "N/A"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": (
                    "1-Telhas sem trincas ou quebras | 2-Cumeeira vedada | "
                    "3-Rufo e calha em bom estado | 4-Sem entulho na cobertura | "
                    "5-Estrutura de suporte íntegra | 6-Impermeabilização adequada | "
                    "7-Platibanda íntegra | 8-Drenos desobstruídos | "
                    "9-Sem vegetação na cobertura | 10-Acesso seguro"
                )
            },
            {
                "id": "pontuacao_cobertura",
                "secao": "Grupo 3 — Cobertura (10 itens)",
                "tipo": "number",
                "label": "Pontuação — Cobertura (0-100%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Percentual de conformidade do grupo Cobertura"
            },

            # ── Grupo 4: Hidráulico (12 itens) ───────────────────────────
            {
                "id": "checklist_hidraulico",
                "secao": "Grupo 4 — Hidráulico (12 itens)",
                "tipo": "tabela",
                "label": "Hidráulico",
                "opcoes": ["Item", "Conforme", "Não Conforme", "N/A"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": (
                    "1-Pressão adequada nos pontos | 2-Sem vazamentos visíveis | "
                    "3-Reservatório limpo e vedado | 4-Boia funcionando | "
                    "5-Tubulação sem corrosão | 6-Registros funcionando | "
                    "7-Ralos desobstruídos | 8-Esgoto com escoamento adequado | "
                    "9-Fossa ou rede pública OK | 10-Caixa de gordura OK | "
                    "11-Aquecedor em bom estado | 12-Chuveiros e torneiras funcionando"
                )
            },
            {
                "id": "pontuacao_hidraulico",
                "secao": "Grupo 4 — Hidráulico (12 itens)",
                "tipo": "number",
                "label": "Pontuação — Hidráulico (0-100%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Percentual de conformidade do grupo Hidráulico"
            },

            # ── Grupo 5: Elétrico (12 itens) ──────────────────────────────
            {
                "id": "checklist_eletrico",
                "secao": "Grupo 5 — Elétrico (12 itens)",
                "tipo": "tabela",
                "label": "Elétrico",
                "opcoes": ["Item", "Conforme", "Não Conforme", "N/A"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": (
                    "1-QDC identificado e organizado | 2-Disjuntores funcionando | "
                    "3-Aterramento presente | 4-Fiação sem emendas expostas | "
                    "5-Tomadas com padrão NBR 14136 | 6-Interruptores funcionando | "
                    "7-Iluminação adequada | 8-SPDA instalado (se necessário) | "
                    "9-Sem sobrecargas visíveis | 10-DPS instalado | "
                    "11-Fiação protegida em eletrodutos | 12-Quadro sem sinais de arco"
                )
            },
            {
                "id": "pontuacao_eletrico",
                "secao": "Grupo 5 — Elétrico (12 itens)",
                "tipo": "number",
                "label": "Pontuação — Elétrico (0-100%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Percentual de conformidade do grupo Elétrico"
            },

            # ── Grupo 6: Acabamentos (12 itens) ───────────────────────────
            {
                "id": "checklist_acabamentos",
                "secao": "Grupo 6 — Acabamentos (12 itens)",
                "tipo": "tabela",
                "label": "Acabamentos",
                "opcoes": ["Item", "Conforme", "Não Conforme", "N/A"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": (
                    "1-Pisos sem trincas | 2-Pisos sem descolamento | "
                    "3-Revestimentos de parede íntegros | 4-Pinturas sem descascamento | "
                    "5-Forros sem manchas ou deformação | 6-Rodapés fixados | "
                    "7-Soleiras e peitoris nivelados | 8-Portas alinhadas e funcionando | "
                    "9-Janelas vedadas e sem folgas | 10-Armários fixados | "
                    "11-Bancadas sem trincas | 12-Rejuntes em bom estado"
                )
            },
            {
                "id": "pontuacao_acabamentos",
                "secao": "Grupo 6 — Acabamentos (12 itens)",
                "tipo": "number",
                "label": "Pontuação — Acabamentos (0-100%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Percentual de conformidade do grupo Acabamentos"
            },

            # ── Grupo 7: Acessibilidade (12 itens) ────────────────────────
            {
                "id": "checklist_acessibilidade",
                "secao": "Grupo 7 — Acessibilidade (12 itens)",
                "tipo": "tabela",
                "label": "Acessibilidade (NBR 9050)",
                "opcoes": ["Item", "Conforme", "Não Conforme", "N/A"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": (
                    "1-Rampas com inclinação ≤8,33% | 2-Largura de corredores ≥1,20m | "
                    "3-Portas com vão ≥0,80m | 4-Piso podotátil instalado | "
                    "5-Sinalização em Braille | 6-Banheiro adaptado PNE | "
                    "7-Barras de apoio instaladas | 8-Estacionamento PNE sinalizado | "
                    "9-Elevador acessível (se necessário) | 10-Alcance de equipamentos OK | "
                    "11-Balcão de atendimento adaptado | 12-Sinalizações visuais e sonoras"
                )
            },
            {
                "id": "pontuacao_acessibilidade",
                "secao": "Grupo 7 — Acessibilidade (12 itens)",
                "tipo": "number",
                "label": "Pontuação — Acessibilidade (0-100%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Percentual de conformidade do grupo Acessibilidade"
            },

            # ── Grupo 8: Segurança (15 itens) ─────────────────────────────
            {
                "id": "checklist_seguranca",
                "secao": "Grupo 8 — Segurança (15 itens)",
                "tipo": "tabela",
                "label": "Segurança",
                "opcoes": ["Item", "Conforme", "Não Conforme", "N/A"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": (
                    "1-Extintores dentro da validade | 2-Extintores sinalizados | "
                    "3-Hidrantes operacionais | 4-Saídas de emergência desobstruídas | "
                    "5-Iluminação de emergência funcionando | 6-Sinalização de rota de fuga | "
                    "7-AVCB válido | 8-Detecção de fumaça instalada | "
                    "9-Alarme de incêndio funcionando | 10-Plano de abandono afixado | "
                    "11-Guarda-corpos com altura ≥1,05m | 12-Escadas com corrimão | "
                    "13-Portão de entrada seguro | 14-Cerca elétrica regulamentada | "
                    "15-CFTV operacional (se houver)"
                )
            },
            {
                "id": "pontuacao_seguranca",
                "secao": "Grupo 8 — Segurança (15 itens)",
                "tipo": "number",
                "label": "Pontuação — Segurança (0-100%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Percentual de conformidade do grupo Segurança"
            },

            # ── Score Geral ────────────────────────────────────────────────
            {
                "id": "score_geral",
                "secao": "Score Geral",
                "tipo": "number",
                "label": "Score Geral de Conformidade (0-100%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Média ponderada de conformidade de todos os grupos avaliados"
            },
        ],
    },
]
