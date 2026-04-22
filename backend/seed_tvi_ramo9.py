# @module seed_tvi_ramo9 — Ramo 9: INSTALAÇÕES (TVI-40 a TVI-43)
"""Modelos TVI do Ramo 9 — Instalações com novo schema profissional v2."""

MODELOS_RAMO9 = [
    # ─── TVI-40 ─── Elétrica NBR 5410 / NR-10 ────────────────────────────────
    {
        "id": "TVI-40",
        "nome": "Vistoria de Instalações Elétricas",
        "ramo": "INSTALAÇÕES",
        "aplicacao": "Avaliação técnica de instalações elétricas conforme NBR 5410 e NR-10",
        "normas": ["NBR 5410 - Instalações Elétricas de Baixa Tensão", "NR-10 - Segurança em Eletricidade", "NBR 5419 - SPDA", "NBR 14136 - Tomadas"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "padrao_entrada",
                "secao": "Padrão de Entrada",
                "tipo": "select",
                "label": "Padrão de Entrada",
                "opcoes": ["Monofásico", "Bifásico", "Trifásico"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Tipo de fornecimento elétrico da concessionária"
            },
            {
                "id": "capacidade_ramal",
                "secao": "Padrão de Entrada",
                "tipo": "number",
                "label": "Capacidade do Ramal (A)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0",
                "ajuda": "Capacidade em amperes do ramal de entrada da concessionária"
            },
            {
                "id": "qdc",
                "secao": "Quadro de Distribuição",
                "tipo": "tabela",
                "label": "QDC — Quadro de Distribuição de Circuitos",
                "opcoes": ["Disjuntor nº", "Capacidade (A)", "Identificação", "Estado"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Inventário dos disjuntores do quadro geral de distribuição"
            },
            {
                "id": "aterramento",
                "secao": "Proteções",
                "tipo": "checkbox",
                "label": "Aterramento (NBR 5410)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Confirme a presença e conformidade do sistema de aterramento"
            },
            {
                "id": "aterramento_medicao_ohms",
                "secao": "Proteções",
                "tipo": "number",
                "label": "Medição de Aterramento (Ω)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0,0",
                "ajuda": "Valor medido da resistência de aterramento em ohms (máx. 5Ω per NBR 5410)"
            },
            {
                "id": "spda",
                "secao": "Proteções",
                "tipo": "select",
                "label": "SPDA — Para-Raios (NBR 5419)",
                "opcoes": ["Sim", "Não", "N/A"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Presença e conformidade do Sistema de Proteção contra Descargas Atmosféricas"
            },
            {
                "id": "tomadas_nbr14136",
                "secao": "Pontos Elétricos",
                "tipo": "select",
                "label": "Tomadas (NBR 14136)",
                "opcoes": ["Todas conformes", "Parcialmente conformes", "Nenhuma conforme"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Conformidade das tomadas com o padrão NBR 14136 (3 pinos)"
            },
            {
                "id": "fiacao_material",
                "secao": "Fiação",
                "tipo": "select",
                "label": "Material da Fiação",
                "opcoes": ["Cobre", "Alumínio", "Mista"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Material condutor predominante na instalação elétrica"
            },
            {
                "id": "estado_fiacao",
                "secao": "Fiação",
                "tipo": "select",
                "label": "Estado Geral da Fiação",
                "opcoes": ["Bom", "Regular", "Ruim", "Crítico"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Avaliação visual do estado de conservação da fiação"
            },
            {
                "id": "laudo_eletrico_art",
                "secao": "Documentação",
                "tipo": "text",
                "label": "Laudo Elétrico / ART nº",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Nº ART do laudo elétrico vigente",
                "ajuda": "Número da ART do laudo elétrico mais recente"
            },
            {
                "id": "risco_curto_circuito",
                "secao": "Risco",
                "tipo": "select",
                "label": "Risco de Curto-Circuito",
                "opcoes": ["Baixo", "Médio", "Alto"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Avaliação técnica do risco de curto-circuito nas instalações"
            },
        ],
    },

    # ─── TVI-41 ─── Hidrossanitária NBR 5626/8160 ────────────────────────────
    {
        "id": "TVI-41",
        "nome": "Vistoria Hidrossanitária",
        "ramo": "INSTALAÇÕES",
        "aplicacao": "Avaliação das instalações hidráulicas e sanitárias conforme NBR 5626 e NBR 8160",
        "normas": ["NBR 5626 - Água Fria", "NBR 8160 - Esgoto Sanitário", "NBR 7229 - Fossa", "NBR 10844 - Drenagem"],
        "requer_art": False,
        "campos_especificos": [
            {
                "id": "abastecimento",
                "secao": "Abastecimento",
                "tipo": "multiselect",
                "label": "Fonte de Abastecimento",
                "opcoes": ["Rede pública", "Poço artesiano", "Poço semi-artesiano", "Cisterna", "Carro-pipa"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Fontes de abastecimento de água utilizadas no imóvel"
            },
            {
                "id": "reservatorio_capacidade",
                "secao": "Reservatório",
                "tipo": "number",
                "label": "Capacidade do Reservatório (litros)",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "0",
                "ajuda": "Capacidade total de armazenamento de água do reservatório"
            },
            {
                "id": "reservatorio_material",
                "secao": "Reservatório",
                "tipo": "select",
                "label": "Material do Reservatório",
                "opcoes": ["Fibra de vidro", "Polietileno", "Concreto", "Aço inox"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Material de fabricação do reservatório de água"
            },
            {
                "id": "reservatorio_estado",
                "secao": "Reservatório",
                "tipo": "multiselect",
                "label": "Estado do Reservatório",
                "opcoes": ["Tampa vedada", "Sem rachaduras", "Boia OK", "Limpo", "Extravasor", "Suporte estrutural OK"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Condições de conservação e funcionamento do reservatório"
            },
            {
                "id": "esgoto",
                "secao": "Esgoto",
                "tipo": "multiselect",
                "label": "Sistema de Esgoto",
                "opcoes": ["Rede pública", "Fossa séptica", "Fossa rudimentar", "Sumidouro"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Tipo de sistema de coleta e disposição de esgoto sanitário"
            },
            {
                "id": "pressao_por_ambiente",
                "secao": "Pressão",
                "tipo": "tabela",
                "label": "Pressão Hidráulica por Ambiente",
                "opcoes": ["Ambiente", "Pressão (Adequada / Baixa / Alta)"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Avaliação da pressão hidráulica por ambiente do imóvel"
            },
            {
                "id": "tubulacoes",
                "secao": "Tubulações",
                "tipo": "multiselect",
                "label": "Estado das Tubulações",
                "opcoes": ["Sem vazamentos", "Sem corrosão", "Conexões fixas", "Ralos OK"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Condições de conservação das tubulações hidráulicas"
            },
            {
                "id": "pontos_hidraulicos",
                "secao": "Pontos Hidráulicos",
                "tipo": "multiselect",
                "label": "Pontos Hidráulicos",
                "opcoes": ["Torneiras OK", "Registros OK", "Chuveiros OK", "Louças fixas OK"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Estado dos pontos de uso e peças de utilização"
            },
            {
                "id": "aquecimento",
                "secao": "Aquecimento",
                "tipo": "select",
                "label": "Sistema de Aquecimento",
                "opcoes": ["Gás", "Elétrico", "Solar", "Sem aquecimento"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Tipo de sistema de aquecimento de água do imóvel"
            },
            {
                "id": "patologias_hidro",
                "secao": "Patologias",
                "tipo": "multiselect",
                "label": "Patologias Identificadas",
                "opcoes": ["Vazamento", "Infiltração", "Entupimento", "Mau cheiro", "Pressão insuficiente"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Problemas e patologias hidrossanitárias encontrados no imóvel"
            },
        ],
    },

    # ─── TVI-42 ─── Gás NBR 15526/13523 ──────────────────────────────────────
    {
        "id": "TVI-42",
        "nome": "Vistoria de Instalações de Gás",
        "ramo": "INSTALAÇÕES",
        "aplicacao": "Avaliação das instalações de gás combustível conforme NBR 15526 e NBR 13523",
        "normas": ["NBR 15526 - Redes de Distribuição Interna para GN", "NBR 13523 - Central de GLP", "NBR 13714 - Extintores"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "tipo_gas",
                "secao": "Tipo de Gás",
                "tipo": "select",
                "label": "Tipo de Gás",
                "opcoes": ["GLP (Gás Liquefeito de Petróleo)", "GN (Gás Natural)"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Tipo de combustível gasoso utilizado na instalação"
            },
            {
                "id": "central_glp",
                "secao": "Central de GLP",
                "tipo": "caixa_texto",
                "label": "Central GLP — Capacidade / Localização / Ventilação",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Capacidade total em kg, localização e ventilação natural/forçada",
                "ajuda": "Detalhes da central de GLP conforme NBR 13523 (apenas para GLP)"
            },
            {
                "id": "ramal_distribuicao",
                "secao": "Ramal de Distribuição",
                "tipo": "caixa_texto",
                "label": "Ramal de Distribuição — Material / Estado / Fixação",
                "opcoes": [],
                "obrigatorio": True,
                "placeholder": "Material (cobre/aço/PVC), estado de conservação e fixação",
                "ajuda": "Características do ramal de distribuição de gás"
            },
            {
                "id": "registro_geral",
                "secao": "Registro Geral",
                "tipo": "multiselect",
                "label": "Registro Geral",
                "opcoes": ["Acessível", "Identificado", "Funcionando"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Condições do registro geral de gás da instalação"
            },
            {
                "id": "teste_estanqueidade",
                "secao": "Testes",
                "tipo": "select",
                "label": "Teste de Estanqueidade",
                "opcoes": ["Aprovado", "Reprovado", "Não Realizado"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Resultado do teste de estanqueidade realizado nas tubulações"
            },
            {
                "id": "art_gas",
                "secao": "Documentação",
                "tipo": "text",
                "label": "ART das Instalações de Gás nº",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Nº da ART do projeto/instalação de gás",
                "ajuda": "Número da Anotação de Responsabilidade Técnica das instalações de gás"
            },
            {
                "id": "equipamentos_gas",
                "secao": "Equipamentos",
                "tipo": "tabela",
                "label": "Equipamentos de Gás",
                "opcoes": ["Tipo", "Marca", "Estado", "Última Manutenção"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Relação dos equipamentos que consomem gás (fogão, aquecedor, caldeira etc.)"
            },
        ],
    },

    # ─── TVI-43 ─── Combate a Incêndio NBR 13714/17240 ───────────────────────
    {
        "id": "TVI-43",
        "nome": "Vistoria de Sistemas de Combate a Incêndio",
        "ramo": "INSTALAÇÕES",
        "aplicacao": "Avaliação dos sistemas de proteção e combate a incêndio conforme NBR 13714 e NBR 17240",
        "normas": ["NBR 13714 - Hidrantes", "NBR 17240 - Detecção e Alarme", "NBR 12693 - Extintores", "IT CBMPA"],
        "requer_art": True,
        "campos_especificos": [
            {
                "id": "avcb_numero",
                "secao": "AVCB",
                "tipo": "text",
                "label": "AVCB nº",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Número do AVCB",
                "ajuda": "Número do Auto de Vistoria do Corpo de Bombeiros"
            },
            {
                "id": "avcb_emissao",
                "secao": "AVCB",
                "tipo": "data",
                "label": "AVCB — Data de Emissão",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Data de emissão do AVCB vigente"
            },
            {
                "id": "avcb_validade",
                "secao": "AVCB",
                "tipo": "data",
                "label": "AVCB — Validade",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Data de vencimento do AVCB"
            },
            {
                "id": "deteccao_fumaca",
                "secao": "Detecção",
                "tipo": "select",
                "label": "Detecção de Fumaça",
                "opcoes": ["Sim", "Não"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Presença de sistema de detecção de fumaça"
            },
            {
                "id": "deteccao_quantidade",
                "secao": "Detecção",
                "tipo": "number",
                "label": "Quantidade de Detectores",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0",
                "ajuda": "Número total de detectores de fumaça instalados"
            },
            {
                "id": "alarme",
                "secao": "Alarme",
                "tipo": "select",
                "label": "Alarme de Incêndio",
                "opcoes": ["Sim — Funcionando", "Sim — Com Defeito", "Não"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Presença e estado de funcionamento do sistema de alarme de incêndio"
            },
            {
                "id": "sprinklers",
                "secao": "Sprinklers",
                "tipo": "select",
                "label": "Sprinklers",
                "opcoes": ["Sim", "Não"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Presença de sistema de chuveiros automáticos (sprinklers)"
            },
            {
                "id": "sprinklers_cobertura",
                "secao": "Sprinklers",
                "tipo": "number",
                "label": "Cobertura dos Sprinklers (%)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "0 a 100",
                "ajuda": "Percentual da área coberta pelo sistema de sprinklers"
            },
            {
                "id": "extintores",
                "secao": "Extintores",
                "tipo": "tabela",
                "label": "Extintores",
                "opcoes": ["Tipo", "Capacidade", "Validade", "Local"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Relação de todos os extintores com tipo, capacidade, validade e localização"
            },
            {
                "id": "hidrantes",
                "secao": "Hidrantes",
                "tipo": "tabela",
                "label": "Hidrantes",
                "opcoes": ["nº", "Pressão (mca)", "Mangueira", "Estado"],
                "obrigatorio": False,
                "placeholder": "",
                "ajuda": "Relação dos hidrantes com pressão, mangueira e estado de conservação"
            },
            {
                "id": "saidas_emergencia_incendio",
                "secao": "Saídas de Emergência",
                "tipo": "tabela",
                "label": "Saídas de Emergência",
                "opcoes": ["nº", "Largura (m)", "Iluminação de emergência"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Relação das saídas de emergência com largura e iluminação"
            },
            {
                "id": "plano_abandono",
                "secao": "Plano de Emergência",
                "tipo": "select",
                "label": "Plano de Abandono",
                "opcoes": ["Existe e equipe treinada", "Existe mas sem treinamento", "Inexistente"],
                "obrigatorio": True,
                "placeholder": "",
                "ajuda": "Situação do plano de abandono / emergência do imóvel"
            },
            {
                "id": "responsavel_spci",
                "secao": "Responsável",
                "tipo": "text",
                "label": "Responsável pelo SPCI (CREA/CAU)",
                "opcoes": [],
                "obrigatorio": False,
                "placeholder": "Nome e registro profissional",
                "ajuda": "Responsável técnico pelo Sistema de Proteção e Combate a Incêndio"
            },
        ],
    },
]
