# @module services.pricing.averbacao — Engine de Averbação (residencial + comercial).
# Port FIEL de pricing/averbacao.ts (ZAYRA). Mesmas regras/valores:
#   Projeto    = R$15/m² (residencial) ou R$25/m² (comercial)
#   Assessoria = 1 SM (R$ 1.621,00 em 2026)
#   Taxas terceiros: emolumentos TJMA 16.9 + INSS/SERO + Habite-se + Alvará + ART.
#
# INSS da obra: usa o MESMO motor do módulo INSS de Obra (services.inss_obra), conferido
# com o Manual do SERO v3.0 — equivalência de áreas, VAU, fator social (PF), categoria,
# decadência, usinado e alíquotas por código de receita (36,8%). Duas origens:
#   1) `_inss_obra_sim` (injetado pela rota quando a proposta é vinculada a uma obra do
#      módulo INSS de Obra) → usa a última simulação daquela obra, sem recalcular;
#   2) senão, simula aqui com os campos da proposta. Sem VAU informado, estima o VAU
#      pelo CUB-MA do padrão e AVISA no PDF que é estimativa.
from __future__ import annotations

from services.pricing.params import (
    HONORARIOS_PROJETO, HONORARIOS_ASSESSORIA, CUB_MA,
    salario_minimo, anotacao_tecnica,
)
from services.pricing.tjma import calcular_emolumentos
from services.pricing.inss_proposta import inss_da_obra
from services.pricing.prefeitura import taxa_habite_se, taxa_alvara_construcao

PROJETOS_RESIDENCIAL_BASICO = ["Mapa de Situacao", "Projeto Arquitetonico"]
PROJETOS_COMPLETO = [
    "Mapa de Situacao", "Projeto Arquitetonico", "Projeto Eletrico",
    "Projeto Hidrossanitario", "Projeto Estrutural",
    "Projeto de Combate a Incendio (PPCI)", "Memorial Descritivo da Obra",
]


def _g(d: dict, k: str, default=None):
    v = d.get(k, default)
    return default if v is None else v


def calcular_averbacao(dados: dict) -> dict:
    """Recebe InputAverbacao (dict) e retorna {custos, fontes} idêntico à ZAYRA."""
    modalidade = dados.get("modalidade", "residencial")
    area_construida = float(_g(dados, "area_construida", 0) or 0)
    valor_venal = float(_g(dados, "valor_venal_imovel", 0) or 0)
    padrao = dados.get("padrao_construtivo", "normal")
    responsavel = dados.get("responsavel", "PF")
    sm = salario_minimo()

    # ── Seção 1: projetos ────────────────────────────────────────────────
    usa_completo = modalidade == "comercial" or bool(dados.get("apresentar_projetos_complementares"))
    secao_1_projetos = PROJETOS_COMPLETO if usa_completo else PROJETOS_RESIDENCIAL_BASICO

    # ── Seção 2: taxas de terceiros ──────────────────────────────────────
    secao_2_taxas = []
    fontes: dict = {}
    ordem = 1

    emol = calcular_emolumentos("averbacao_construcao", valor_venal)
    secao_2_taxas.append({
        "ordem": ordem, "descricao": "Emolumentos cartorarios (averbacao de construcao) — Tabela TJMA 2026",
        "valor": emol["valor"], "observacao": emol.get("base_calculo"),
    }); ordem += 1
    fontes["tjma"] = {"fonte": emol["fonte"], "consultadoEm": emol["consultadoEm"]}

    inss = inss_da_obra(dados, modalidade, area_construida, padrao, responsavel)
    obs_sero = inss["observacao"]
    if dados.get("parcelar_inss") and inss["total"] > 0 and int(_g(dados, "numero_parcelas_inss", 0) or 0) >= 2:
        n = min(60, max(2, int(dados["numero_parcelas_inss"])))
        parcela = inss["total"] / n
        obs_sero += (f" | Opcao de parcelamento direto com a Receita Federal: {n}x de aprox. "
                     f"R$ {parcela:.2f} (a Romatec presta assessoria; CND liberada para averbacao apos 1a parcela).")
    secao_2_taxas.append({
        "ordem": ordem, "descricao": "INSS da obra (SERO — Receita Federal, afericao indireta)",
        "valor": inss["total"], "observacao": obs_sero,
    }); ordem += 1
    fontes["sero"] = {"fonte": inss["fonte"], "aviso": inss["aviso"], "origem": inss["origem"]}
    if inss.get("vau_estimado"):
        fontes["cub"] = {"valor": inss["vau"], "padrao": padrao, "mes_referencia": CUB_MA["ultima_atualizacao"]}

    habite = taxa_habite_se()
    secao_2_taxas.append({
        "ordem": ordem, "descricao": habite["rotulo"], "valor": habite["valor"] or 0,
        "pendente": habite["pendente"], "observacao": habite["observacao_pdf"],
    }); ordem += 1

    if not dados.get("tem_alvara_construcao"):
        alvara = taxa_alvara_construcao()
        secao_2_taxas.append({
            "ordem": ordem, "descricao": alvara["rotulo"], "valor": alvara["valor"] or 0,
            "pendente": alvara["pendente"],
            "observacao": alvara["observacao_pdf"] or "Cobrado por nao haver Alvara emitido previamente.",
        }); ordem += 1

    at = anotacao_tecnica(dados.get("anotacao_tecnica") or "art_crea")
    secao_2_taxas.append({
        "ordem": ordem, "descricao": at["rotulo"], "valor": at["valor"], "observacao": at["fonte"],
    }); ordem += 1

    # ── Seção 3: honorários Romatec ──────────────────────────────────────
    valor_por_m2 = (HONORARIOS_PROJETO["averbacao_residencial_por_m2"] if modalidade == "residencial"
                    else HONORARIOS_PROJETO["averbacao_comercial_por_m2"])
    honorario_projeto = area_construida * valor_por_m2
    honorario_assessoria = sm * HONORARIOS_ASSESSORIA["padrao_sm"]
    secao_3_honorarios = [
        {"ordem": 6,
         "descricao": ("Honorarios de Projeto e Diligencia Tecnica — confeccao dos projetos da Secao 1, "
                       "vistoria, levantamento, ARTs, responsabilidade tecnica"),
         "valor": honorario_projeto, "observacao": f"R$ {valor_por_m2:.2f}/m2 x {area_construida} m2"},
        {"ordem": 7,
         "descricao": ("Honorarios de Assessoria e Acompanhamento — emissao de Alvara, retirada de Habite-se, "
                       "emissao de CND Receita Federal, diligencias em cartorio, acompanhamento integral ate "
                       "averbacao final na matricula"),
         "valor": honorario_assessoria, "observacao": f"1 salario minimo 2026 (R$ {sm:.2f})"},
    ]

    # ── Seção 4: checklist ───────────────────────────────────────────────
    secao_4_checklist = [
        {"texto": "Certidao de Inteiro Teor da Matricula — ATUALIZADA (max. 30 dias)", "obrigatorio": True},
        {"texto": "IPTU em dia (comprovante do exercicio atual)", "obrigatorio": True},
    ]
    if modalidade == "comercial":
        secao_4_checklist.append({"texto": "CNPJ + Contrato Social", "obrigatorio": True})
        secao_4_checklist.append({"texto": "RG/CPF dos socios", "obrigatorio": True})
    else:
        secao_4_checklist.append({"texto": "RG/CPF do proprietario", "obrigatorio": True})
    secao_4_checklist += [
        {"texto": "Alvara de Construcao (se ja possuir)", "obrigatorio": False},
        {"texto": "Habite-se (se ja possuir)", "obrigatorio": False},
        {"texto": "CND da Receita Federal — Imovel (se ja possuir)", "obrigatorio": False},
        {"texto": ("Senha gov.br (nivel prata ou ouro) do proprietario — necessaria para acesso ao portal e-CAC, "
                   "geracao do CNO da obra e calculo definitivo do SERO/INSS"), "obrigatorio": True},
    ]

    # ── Seção 5: total ───────────────────────────────────────────────────
    total_taxas = sum(i["valor"] for i in secao_2_taxas)
    total_honorarios = sum(i["valor"] for i in secao_3_honorarios)
    secao_5_total = total_taxas + total_honorarios

    # ── Avisos ───────────────────────────────────────────────────────────
    avisos = [
        ("IMPORTANTE: Os valores das taxas de Cartorio e da Receita Federal informados nesta proposta sao "
         "APROXIMADOS, calculados com base nas tabelas oficiais vigentes (TJMA Resolucao GP 143/2025 e IN RFB "
         "2021/2021). Os valores definitivos podem variar conforme apuracao real do cartorio competente e do "
         "portal SERO/e-CAC no momento do pagamento."),
    ]
    if inss["total"] > 0 or inss["origem"] != "pj_contabilidade":
        avisos.append(inss["aviso"])
    avisos.append(
        "SENHA GOV.BR — DETALHAMENTO DE USO. Para concluir a averbacao, a Romatec precisa acessar, EM NOME DO "
        "PROPRIETARIO, os portais e-CAC, modulo CNO, portal SERO e emissao da CND da obra (todos exigem login "
        "gov.br nivel prata/ouro). A senha NAO e compartilhada com terceiros — o proprietario acompanha o login."
    )
    if dados.get("parcelar_inss") and inss["total"] > 0 and int(_g(dados, "numero_parcelas_inss", 0) or 0) >= 2:
        n = min(60, max(2, int(dados["numero_parcelas_inss"])))
        avisos.append(
            f"PARCELAMENTO INSS/SERO: o cliente pode parcelar o debito diretamente com a Receita Federal "
            f"(portal e-CAC) em ate {n} parcelas. A Romatec presta assessoria completa. A CND da obra fica "
            f"liberada para averbacao apos o pagamento da 1a parcela.")
    elif inss["total"] > 0:
        avisos.append(
            "PARCELAMENTO OPCIONAL: caso o cliente prefira nao pagar o INSS/SERO a vista, e possivel parcelar o "
            "debito diretamente com a Receita Federal (portal e-CAC) em ate 60x. A CND da obra fica liberada "
            "para averbacao apos pagamento da 1a parcela.")
    itens_pendentes = [i["descricao"] for i in secao_2_taxas if i.get("pendente")]
    if itens_pendentes:
        avisos.append(f"Itens pendentes de confirmacao com a Prefeitura: {', '.join(itens_pendentes)}.")
        fontes["prefeitura"] = {"itens_pendentes": itens_pendentes}

    # ── Condições de pagamento ───────────────────────────────────────────
    primeira = honorario_projeto + honorario_assessoria * 0.5
    segunda = honorario_assessoria * 0.5
    condicoes_pagamento = [
        {"rotulo": "1a parcela — na assinatura da proposta",
         "descricao": "100% dos Honorarios de Projeto e Diligencia Tecnica + 50% dos Honorarios de Assessoria",
         "valor": primeira},
        {"rotulo": "2a parcela — no protocolo em cartorio",
         "descricao": "50% restante dos Honorarios de Assessoria e Acompanhamento", "valor": segunda},
    ]

    # ── Base de cálculo (INSS/SERO) ──────────────────────────────────────
    base_calculo = inss["base_calculo"]

    custos = {
        "secao_1_projetos": secao_1_projetos,
        "secao_2_taxas": secao_2_taxas,
        "secao_3_honorarios": secao_3_honorarios,
        "condicoes_pagamento": condicoes_pagamento,
        "base_calculo": base_calculo,
        "inss_memoria": inss["base_calculo"],
        "secao_4_checklist": secao_4_checklist,
        "secao_5_total": round(secao_5_total, 2),
        "avisos": avisos,
    }
    return {"custos": custos, "fontes": fontes}
