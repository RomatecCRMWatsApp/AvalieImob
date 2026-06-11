# @module services.pricing.retificacao — Engine de Retificação de Área (port fiel da ZAYRA).
# Lei 10.931/2004 (administrativa) / Lei 6.015/73 art. 213 (judicial) · NBR 13133.
from __future__ import annotations

from services.pricing.params import HONORARIOS_PROJETO, HONORARIOS_ASSESSORIA, salario_minimo, anotacao_tecnica
from services.pricing.tjma import calcular_emolumentos

ESCOPO_ADMINISTRATIVA = [
    "Levantamento topografico do imovel", "Calculo da area real (poligonal fechada)",
    "Memorial descritivo retificador", "Planta com a poligonal correta",
    "Coleta de anuencia de todos os confrontantes",
    "Protocolo do procedimento administrativo no cartorio",
    "Acompanhamento ate decisao do oficial registrador",
    "Averbacao da retificacao na matricula",
]
ESCOPO_JUDICIAL = [
    "Levantamento topografico do imovel", "Calculo da area real (poligonal fechada)",
    "Memorial descritivo retificador", "Planta com a poligonal correta",
    "Tentativa de obtencao de anuencia dos confrontantes (etapa premissa)",
    "Petição inicial de retificacao judicial (parceria com advogado)",
    "Acompanhamento processual ate sentenca transitada em julgado",
    "Cumprimento de sentenca e averbacao na matricula",
]


def calcular_retificacao(dados: dict) -> dict:
    sm = salario_minimo()
    area_atual = float(dados.get("area_atual_matricula") or 0)
    area_real = float(dados.get("area_real_levantada") or 0)
    valor_venal = float(dados.get("valor_venal") or 0)
    is_judicial = dados.get("tipo_retificacao") == "judicial"

    if area_atual <= 0:
        raise ValueError("area_atual_matricula deve ser > 0")
    if area_real <= 0:
        raise ValueError("area_real_levantada deve ser > 0")

    divergencia = abs(area_real - area_atual)
    pct_div = (divergencia / area_atual) * 100

    secao_1 = list(ESCOPO_JUDICIAL if is_judicial else ESCOPO_ADMINISTRATIVA)

    secao_2 = []
    fontes = {}
    ordem = 1
    at = anotacao_tecnica("art_crea")
    secao_2.append({"ordem": ordem, "descricao": at["rotulo"], "valor": at["valor"], "observacao": at["fonte"]}); ordem += 1

    emol = calcular_emolumentos("averbacao_construcao", valor_venal)
    secao_2.append({"ordem": ordem,
                    "descricao": "Emolumentos cartorarios (averbacao da retificacao de area na matricula)",
                    "valor": emol["valor"], "observacao": emol["base_calculo"]}); ordem += 1
    fontes["tjma"] = {"fonte": emol["fonte"], "consultadoEm": emol["consultadoEm"]}

    if is_judicial:
        custas = valor_venal * 0.015
        secao_2.append({"ordem": ordem, "descricao": "Custas judiciais TJMA (taxa judiciaria) — ESTIMATIVA",
                        "valor": custas,
                        "observacao": "Estimado em 1,5% do valor venal. Valor exato apurado no protocolo da inicial. Pode haver isencao se cliente comprovar hipossuficiencia."}); ordem += 1
        secao_2.append({"ordem": ordem, "descricao": "Honorarios advocaticios (contratacao a parte)",
                        "valor": 0, "pendente": True,
                        "observacao": "A Romatec NAO inclui honorarios advocaticios. Cliente contrata advogado de confianca diretamente. Tipico: 10-20% do valor venal ou valor fixo."}); ordem += 1

    fator_sm = dados.get("honorario_projeto_sm")
    if fator_sm is None:
        fator_sm = HONORARIOS_PROJETO["retificacao_area_sm_default"]
    fator_sm = float(fator_sm)
    honorario_projeto = sm * fator_sm
    honorario_assessoria = sm * HONORARIOS_ASSESSORIA["padrao_sm"]
    fator_assess_jud = 2.0 if is_judicial else 1.0
    honorario_assessoria_total = honorario_assessoria * fator_assess_jud

    obs_proj = (f"{fator_sm} SM × R$ {sm:.2f} = R$ {honorario_projeto:.2f} "
                f"(Tipo {'JUDICIAL' if is_judicial else 'ADMINISTRATIVA'} — divergencia {pct_div:.2f}%)")
    obs_assess = (f"1 SM × 2.0 (acompanhamento processual estendido — judicial) = R$ {honorario_assessoria_total:.2f}"
                  if is_judicial else f"1 SM × R$ {sm:.2f}")
    secao_3 = [
        {"ordem": ordem, "descricao": ("Honorarios Tecnicos de Retificacao — levantamento topografico, calculo de area "
                                       "real, memorial retificador, planta, ART e responsabilidade tecnica"),
         "valor": honorario_projeto, "observacao": obs_proj},
        {"ordem": ordem + 1,
         "descricao": ("Honorarios de Assessoria Tecnica Processual — acompanhamento ao longo do processo, eventuais "
                       "pericias, complementos solicitados pelo juizo, ate cumprimento da sentenca") if is_judicial else
                      ("Honorarios de Assessoria Administrativa — coleta de anuencias, diligencias junto a confrontantes, "
                       "protocolo cartorio, acompanhamento ate averbacao final"),
         "valor": honorario_assessoria_total, "observacao": obs_assess},
    ]
    ordem += 2

    secao_4 = [
        {"texto": "Certidao de Inteiro Teor da Matricula — ATUALIZADA (max. 30 dias)", "obrigatorio": True, "imprescindivel": True},
        {"texto": "IPTU em dia (todos exercicios) — comprovantes", "obrigatorio": True},
        {"texto": "RG/CPF do proprietario (e conjuge se for o caso)", "obrigatorio": True},
        {"texto": "Comprovante de residencia atualizado", "obrigatorio": True},
        {"texto": ("Documentos comprobatorios da impossibilidade de obter anuencia administrativa (ex: notificacoes recusadas)"
                   if is_judicial else
                   "Anuencia escrita e assinada de TODOS os confrontantes (essencial pra via administrativa)"),
         "obrigatorio": True, "imprescindivel": (not is_judicial)},
        {"texto": "Plantas, medicoes ou levantamentos anteriores (se houver)", "obrigatorio": False},
    ]
    if is_judicial:
        secao_4.append({"texto": "Procuracao ad judicia ao advogado contratado", "obrigatorio": True})
        secao_4.append({"texto": "Documentos pessoais dos confrontantes (RG/CPF/endereco) pra citacao", "obrigatorio": True})

    total_taxas = sum(i["valor"] for i in secao_2)
    total_hon = sum(i["valor"] for i in secao_3)
    secao_5_total = total_taxas + total_hon

    avisos = []
    if is_judicial:
        avisos += [
            "BASE LEGAL JUDICIAL: Lei 6.015/1973 art. 213 e seguintes (Codigo de Processo Civil). Retificacao judicial e o caminho quando ha discordancia de confrontantes ou litigio sobre divisas.",
            "PRAZO ESTIMADO: 6 a 24 meses, dependendo da Vara de Registros Publicos do TJMA, da contestacao dos confrontantes e da producao probatoria. A Romatec nao tem controle sobre o prazo do Judiciario.",
            "IMPORTANTE: a Romatec atua APENAS como ASSISTENTE TECNICO do processo (laudo, pericia, esclarecimentos). O advogado que conduz a acao e contratado a parte pelo cliente. Honorarios advocaticios NAO estao inclusos nesta proposta.",
        ]
    else:
        avisos += [
            "BASE LEGAL ADMINISTRATIVA: Lei 10.931/2004 (alterou a Lei 6.015/1973). Permite retificacao perante o oficial do registro de imoveis, sem necessidade de processo judicial, desde que com anuencia de TODOS os confrontantes.",
            "PRAZO ESTIMADO: 30 a 90 dias, dependendo do tempo de coleta de anuencias e da analise do registrador.",
            "ATENCAO: caso 1 ou mais confrontantes RECUSEM a assinatura da anuencia, o procedimento administrativo e EXTINTO e a unica via passa a ser a JUDICIAL — caso para o qual sera elaborado novo orcamento.",
        ]
    if pct_div > 5:
        avisos.append(f"DIVERGENCIA CONSIDERAVEL: {pct_div:.2f}% entre area da matricula e area real. Confrontantes podem questionar — recomenda-se reuniao previa de conciliacao antes de protocolar.")
    if not dados.get("tem_anuencia_confrontantes") and not is_judicial:
        avisos.append("ANUENCIA DOS CONFRONTANTES PENDENTE: voce indicou que ainda nao tem as anuencias. A Romatec presta apoio na elaboracao das notificacoes e visita aos confrontantes, mas a coleta efetiva e responsabilidade do cliente. Sem 100% das anuencias, a via administrativa nao prospera.")
    avisos.append("IMPORTANTE: os valores de cartorio sao aproximados. Custas judiciais (se aplicavel) sao fixadas pelo TJMA no momento do protocolo da inicial.")

    if is_judicial:
        condicoes = [
            {"rotulo": "1a parcela — na assinatura", "descricao": "100% Honorarios Tecnicos + 50% Honorarios de Assessoria",
             "valor": honorario_projeto + honorario_assessoria_total * 0.5},
            {"rotulo": "2a parcela — na sentenca de procedencia", "descricao": "50% restante dos Honorarios de Assessoria",
             "valor": honorario_assessoria_total * 0.5},
        ]
    else:
        condicoes = [
            {"rotulo": "1a parcela — na assinatura", "descricao": "50% Honorarios Tecnicos + 50% Honorarios de Assessoria",
             "valor": honorario_projeto * 0.5 + honorario_assessoria_total * 0.5},
            {"rotulo": "2a parcela — na coleta das anuencias", "descricao": "50% restante dos Honorarios Tecnicos",
             "valor": honorario_projeto * 0.5},
            {"rotulo": "3a parcela — na averbacao final no cartorio", "descricao": "50% restante dos Honorarios de Assessoria",
             "valor": honorario_assessoria_total * 0.5},
        ]

    base_calculo = [
        {"rotulo": "Area atual (matricula)", "formula": f"{area_atual:.2f} m² ou hectares conforme matricula", "valor_resultado": area_atual},
        {"rotulo": "Area real (levantada GPS/Estacao)", "formula": f"{area_real:.2f} m² ou hectares medidos", "valor_resultado": area_real},
        {"rotulo": "Divergencia", "formula": f"{divergencia:.2f} ({pct_div:.2f}%)", "valor_resultado": divergencia},
        {"rotulo": "Honorarios Tecnicos", "formula": f"{fator_sm} SM × R$ {sm:.2f}", "valor_resultado": honorario_projeto},
        {"rotulo": "Honorarios de Assessoria",
         "formula": (f"2 × 1 SM × R$ {sm:.2f} (judicial estendido)" if is_judicial else f"1 SM × R$ {sm:.2f}"),
         "valor_resultado": honorario_assessoria_total},
    ]

    return {"custos": {
        "secao_1_projetos": secao_1, "secao_2_taxas": secao_2, "secao_3_honorarios": secao_3,
        "condicoes_pagamento": condicoes, "base_calculo": base_calculo, "secao_4_checklist": secao_4,
        "secao_5_total": round(secao_5_total, 2), "avisos": avisos,
    }, "fontes": fontes}
