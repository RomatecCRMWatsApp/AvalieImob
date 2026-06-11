# @module services.pricing.params — Constantes/tabelas de precificação (port fiel da ZAYRA).
# Fonte: RomatecVoiceAgent/config/pricing-params.json (_meta versao 1.0, 2026-05-05).
# Mantém os MESMOS valores da ZAYRA para que as propostas saiam idênticas.
from __future__ import annotations

SALARIO_MINIMO_2026 = 1621.00

CUB_MA = {
    "base_r8n": 1814.39,
    "ultima_atualizacao": "2025-12",
    "fonte": "Sinduscon-MA",
    "multiplicadores_padrao": {"popular": 0.75, "normal": 1.00, "alto": 1.45},
}

ART_CREA_MA_2026 = {"faixa_1": 93.40, "faixa_2": 124.13, "faixa_3": 168.53,
                    "fonte": "Decisao Plenaria 0450/2025 Confea"}

ANOTACAO_TECNICA_2026 = {
    "art_crea": {"rotulo": "ART CREA-MA (Anotacao de Responsabilidade Tecnica)",
                 "conselho": "CREA-MA", "valor": 93.40,
                 "fonte": "Decisao Plenaria 0450/2025 Confea (Engenheiros)"},
    "rrt_cau": {"rotulo": "RRT CAU/MA (Registro de Responsabilidade Tecnica)",
                "conselho": "CAU/MA", "valor": 95.45,
                "fonte": "Resolucao CAU/BR 91/2014 atualizada (Arquitetos e Urbanistas)"},
    "trt_cft": {"rotulo": "TRT CFT/MA (Termo de Responsabilidade Tecnica)",
                "conselho": "CFT", "valor": 93.40,
                "fonte": "Tabela CFT 2026 — Tec. Agrim. CFT/MA n. 01209185369"},
}

HONORARIOS_PROJETO = {
    "averbacao_residencial_por_m2": 15.00,
    "averbacao_comercial_por_m2": 25.00,
    "desmembramento_meio_sm": 0.5,
    "desmembramento_sm_completo": 1.0,
    "remembramento_meio_sm": 0.5,
    "remembramento_sm_completo": 1.0,
    "retificacao_area_sm_default": 1.0,
    "ptam_lote_urbano_sm": 1.0,
    "ptam_sitio_proximo_sm": 2.0,
    "ptam_rural_medio_sm": 3.0,
    "ptam_fazenda_grande_sm": 4.0,
    "geo_rural_por_hectare": 80.00,
    "geo_rural_por_vertice": 200.00,
    "geo_rural_diaria_campo": 600.00,
    "geo_rural_por_km_deslocamento": 3.50,
    "geo_rural_minimo_sm": 2.0,
    "geo_rural_complexidade_simples": 1.00,
    "geo_rural_complexidade_media": 1.30,
    "geo_rural_complexidade_alta": 1.60,
}

HONORARIOS_ASSESSORIA = {
    "padrao_sm": 1.0,
    "descricao": "Universal: 1 SM independente do subtipo. Cobre alvara, Habite-se, "
                 "CND, diligencias cartorio, acompanhamento integral.",
}

SERO_INSS = {
    "aliquota_inss": 0.20,
    "aliquota_sistema_s": 0.08,
    "fonte": "IN RFB 2021/2021",
    "percentual_mao_obra": {
        "residencial_alvenaria_sem_premoldado": 0.14,
        "residencial_alvenaria_com_premoldado": 0.04,
        "residencial_madeira": 0.14,
        "comercial_medio": 0.10,
    },
    "aviso_pdf": "Valor estimado conforme afericao indireta IN RFB 2021/2021. Calculo "
                 "definitivo apenas mediante apuracao no portal SERO/e-CAC pelo "
                 "contribuinte ou contador habilitado.",
}

PREFEITURA_ACAILANDIA = {
    "habite_se": None,
    "alvara_construcao": None,
    "aprovacao_desmembramento": None,
}

TJMA_EMOLUMENTOS_2026 = {
    "fonte": "Resolucao GP 143/2025 TJMA - valores TOTAL (incluem FERC+FADEP+FEMP+FERRFIS)",
    "limite_maximo_total": 23946.65,
}

# Demarcação de Lotes (urbana e rural) — port fiel do bloco demarcacao_lotes_2026 (v3.40.0).
DEMARCACAO_LOTES_2026 = {
    "valor_m2_urbano_default": 1.50,
    "valor_hectare_rural_default": 80.00,
    "fator_diaria_tecnico": 0.42,
    "fator_diaria_tecnico_fonte": "CFT-MA Resolucao no 12/2025 art. 4o — diaria de tecnico em agrimensura: 0,42 SM por dia em campo",
    "valor_km_deslocamento": 3.50,
    "marcos": {
        "concreto": {"valor_unitario": 120.00, "rotulo": "Marco de Concreto Padrao INCRA", "codigo_funcao": "M", "codigo_material": "CC", "largura_numero": 4},
        "madeira": {"valor_unitario": 35.00, "rotulo": "Marco de Madeira de Lei", "codigo_funcao": "P", "codigo_material": "MD", "largura_numero": 3},
        "tubo_galvanizado": {"valor_unitario": 85.00, "rotulo": "Marco em Tubo Galvanizado", "codigo_funcao": "M", "codigo_material": "TG", "largura_numero": 4},
    },
    "vertices": {"codigo_funcao": "V", "largura_numero": 3},
    "opcionais": {
        "laudo_tecnico": {"rotulo": "Laudo Tecnico de Demarcacao", "valor_unitario_sm_multiplicador": 1.0},
        "alinhamento_cerca": {"rotulo": "Alinhamento de Cerca", "valor_unitario": 0.42, "unidade": "metro"},
        "croqui_assinado": {"rotulo": "Croqui Assinado em Cartorio", "valor_unitario": 180.00},
        "acompanhamento_obra": {"rotulo": "Acompanhamento de Obra", "valor_unitario": 350.00, "unidade": "diaria"},
        "consultoria_juridica": {"rotulo": "Consultoria Juridica", "valor": "sob_orcamento"},
    },
    "laudo_tecnico_direto": {"rotulo": "Laudo Tecnico de Demarcacao", "valor_unitario_sm_multiplicador": 1.0},
    "locacao_kit_gnss": {
        "rotulo": "Locacao de equipamentos — Kit GNSS",
        "valor_unitario_diaria_default": 250.00,
        "descritivo": "Receptor ComNav S6 (base); Receptor T30 Plus com laser (rover); tripe; base niveladora; bastao/bipe; coletora R80.",
    },
    "minimo_garantido_sm": 2,
    "complexidade_multiplicadores": {"simples": 1.0, "media": 1.3, "alta": 1.6},
    "assessoria_pct": 0.05,
    "desconto_max_pct": 30,
    "parcelas": [
        {"numero": 1, "rotulo": "Assinatura do contrato", "percentual": 40},
        {"numero": 2, "rotulo": "Entrega do trabalho de campo", "percentual": 30},
        {"numero": 3, "rotulo": "Entrega final + TRT/CFT", "percentual": 30},
    ],
    "parcelas_2x": [
        {"numero": 1, "rotulo": "Assinatura do contrato (sinal)", "percentual": 50},
        {"numero": 2, "rotulo": "Entrega final + TRT/CFT", "percentual": 50},
    ],
    "validade_dias_default": 15,
}

# Serviços adicionais opcionais de Georreferenciamento Rural (v3.23.6).
# NÃO somam ao total Romatec — saem em seção informativa própria do PDF.
OPCIONAIS_GEORREF = {
    "ccir": {"rotulo": "Atualizacao do CCIR (INCRA)", "valor_unitario": 1621.00, "editavel": True},
    "car": {"rotulo": "Atualizacao / emissao do CAR (SICAR)", "valor_unitario": 1621.00, "editavel": True},
    "itr": {"rotulo": "Regularizacao de ITR em atraso", "valor_unitario": 300.00, "unidade": "por exercicio", "editavel": True},
    "anuencia": {"rotulo": "Coleta de anuencia dos confrontantes", "valor_unitario": 150.00, "unidade": "por confrontante", "editavel": True},
    "retificacao": {"rotulo": "Retificacao de area (Lei 10.931/2004)", "valor": "sob_orcamento"},
}

# Adicional de campo (insalubridade/periculosidade) — percentuais (textos no engine futuro).
ADICIONAL_CAMPO_2026 = {
    "percentuais": {
        "insalubridade": {"minimo": 10, "medio": 20, "maximo": 40},
        "periculosidade": {"unico": 30},
    },
}


# ── Helpers (espelham params.ts) ───────────────────────────────────────────
def salario_minimo() -> float:
    return SALARIO_MINIMO_2026


def cub_por_padrao(padrao: str) -> float:
    return CUB_MA["base_r8n"] * CUB_MA["multiplicadores_padrao"][padrao]


def art_crea_faixa1() -> float:
    return ART_CREA_MA_2026["faixa_1"]


def anotacao_tecnica(tipo: str) -> dict:
    at = ANOTACAO_TECNICA_2026.get(tipo)
    if at:
        return at
    return {
        "rotulo": "ART CREA-MA (Anotacao de Responsabilidade Tecnica)",
        "conselho": "CREA-MA", "valor": ART_CREA_MA_2026["faixa_1"],
        "fonte": ART_CREA_MA_2026["fonte"],
    }
