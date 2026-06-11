# @module services.pricing.ptam — Engine de Avaliação PTAM (port fiel da ZAYRA). NBR 14653.
from __future__ import annotations

from services.pricing.params import (
    HONORARIOS_PROJETO, HONORARIOS_ASSESSORIA, ART_CREA_MA_2026,
    salario_minimo, anotacao_tecnica,
)

ESCOPO_PTAM_BASE = [
    "Vistoria tecnica do imovel (caracteristicas fisicas, conservacao, infraestrutura)",
    "Levantamento de dados de mercado (amostras de imoveis comparaveis na regiao)",
    "Pesquisa cadastral e documental (matricula, IPTU/ITR, restricoes)",
    "Analise das caracteristicas do imovel-alvo vs amostras (homogeneizacao)",
    "Calculo do valor de mercado pelo metodo comparativo direto",
    "Memorial descritivo do imovel + reportagem fotografica",
    "Laudo de avaliacao com base na NBR 14653",
]
ESCOPO_RIGOROSO = [
    "Tratamento estatistico avancado (regressao linear multipla, teste F, R², t-Student)",
    "Validacao por correlacao Pearson dos coeficientes",
    "Intervalos de confianca de 80% (NBR) e 95% (judicial)",
    "Tabela completa de amostras com homogeneizacao detalhada",
]

_FAIXAS = {
    "1_lote_urbano": ("ptam_lote_urbano_sm", "Lote urbano (ate 1000m²)"),
    "2_sitio_proximo": ("ptam_sitio_proximo_sm", "Sitio proximo (ate 50ha)"),
    "3_rural_medio": ("ptam_rural_medio_sm", "Rural medio (ate 500ha)"),
    "4_fazenda_grande": ("ptam_fazenda_grande_sm", "Fazenda grande (>500ha)"),
}


def calcular_avaliacao_ptam(dados: dict) -> dict:
    sm = salario_minimo()
    tipo_imovel = dados.get("tipo_imovel", "urbano_residencial")
    finalidade = dados.get("finalidade", "particular")
    nivel = dados.get("nivel_precisao", "normal")
    faixa = dados.get("faixa_honorario", "1_lote_urbano")
    valor_outro = float(dados.get("valor_outro") or 0)

    secao_1 = list(ESCOPO_PTAM_BASE)
    if nivel == "rigorosa":
        secao_1 += ESCOPO_RIGOROSO
    if tipo_imovel in ("rural", "glebas"):
        secao_1 += ["Analise de aptidao agricola/ambiental (NBR 14653-3)",
                    "Avaliacao de benfeitorias rurais (galpoes, currais, açudes, cercas)"]
    if tipo_imovel == "industrial":
        secao_1 += ["Avaliacao de instalacoes industriais (NBR 14653-5)", "Verificacao de licenciamento ambiental"]
    if finalidade == "judicial":
        secao_1 += ["Quesitos do juiz/partes — respostas formais para fins processuais",
                    "Apresentacao em audiencia/pericia se solicitado"]

    secao_2 = []
    fontes = {}
    ordem = 1
    at = anotacao_tecnica("art_crea")
    valor_art = at["valor"]
    obs_art = at["fonte"]
    if nivel == "rigorosa":
        valor_art = ART_CREA_MA_2026["faixa_2"]
        obs_art = f"{at['fonte']} — Faixa 2 aplicada por nivel rigoroso"
    secao_2.append({"ordem": ordem, "descricao": at["rotulo"], "valor": valor_art, "observacao": obs_art}); ordem += 1

    if faixa == "outro":
        if valor_outro <= 0:
            raise ValueError("Faixa outro exige valor_outro > 0")
        mult_sm = valor_outro / sm
        desc_faixa = "Customizado"
        honorario_projeto = valor_outro
    else:
        chave, desc_faixa = _FAIXAS.get(faixa, _FAIXAS["1_lote_urbano"])
        mult_sm = HONORARIOS_PROJETO[chave]
        honorario_projeto = sm * mult_sm

    fator_precisao = 1.0
    if nivel == "rigorosa":
        fator_precisao = 1.5
    elif nivel == "expedita":
        fator_precisao = 0.7
    honorario_projeto *= fator_precisao

    fator_finalidade = 1.3 if finalidade == "judicial" else 1.0
    honorario_projeto *= fator_finalidade

    honorario_assessoria = sm * HONORARIOS_ASSESSORIA["padrao_sm"] * 0.5

    obs_proj = (f"Valor customizado R$ {valor_outro:.2f} × {fator_precisao}x precisao {nivel} × {fator_finalidade}x finalidade {finalidade}"
                if faixa == "outro" else
                f"{mult_sm} SM ({desc_faixa}) × R$ {sm:.2f} × {fator_precisao}x precisao {nivel} × {fator_finalidade}x finalidade {finalidade}")
    secao_3 = [
        {"ordem": ordem, "descricao": "Honorarios Tecnicos PTAM — vistoria, pesquisa de mercado, calculo do valor, laudo conforme NBR 14653",
         "valor": honorario_projeto, "observacao": obs_proj},
        {"ordem": ordem + 1, "descricao": "Entrega e Revisao do Laudo — apresentacao do laudo ao cliente, revisao ate 1 vez se necessario, esclarecimentos por email/whatsapp",
         "valor": honorario_assessoria, "observacao": f"0.5 SM × R$ {sm:.2f}"},
    ]
    ordem += 2

    secao_4 = [
        {"texto": "Certidao de Inteiro Teor da Matricula (max. 30 dias) — pra confirmar titularidade e onus", "obrigatorio": True, "imprescindivel": True},
        {"texto": "IPTU/ITR atualizado — pra ver descricao oficial", "obrigatorio": True},
        {"texto": "RG/CPF do solicitante (proprietario, advogado ou interessado)", "obrigatorio": True},
        {"texto": "Endereco completo e ponto de referencia do imovel", "obrigatorio": True},
        {"texto": ("Numero do processo + nome das partes + quesitos formulados pelo juiz/advogados"
                   if finalidade == "judicial" else
                   "Finalidade detalhada do laudo (compra, venda, garantia bancaria, partilha, etc)"),
         "obrigatorio": True},
    ]
    if tipo_imovel in ("rural", "glebas"):
        secao_4 += [{"texto": "CCIR + ITR em dia (Certificado de Cadastro de Imovel Rural)", "obrigatorio": True},
                    {"texto": "CAR (Cadastro Ambiental Rural)", "obrigatorio": True}]
    if tipo_imovel == "industrial":
        secao_4 += [{"texto": "Alvara de funcionamento + licenca ambiental", "obrigatorio": True},
                    {"texto": "Plantas das instalacoes industriais", "obrigatorio": False}]
    if finalidade == "bancaria":
        secao_4 += [{"texto": "Indicacao do banco/instituicao financeira", "obrigatorio": True},
                    {"texto": "Modelo/template de laudo exigido pelo banco (se houver)", "obrigatorio": False}]

    total_taxas = sum(i["valor"] for i in secao_2)
    total_hon = sum(i["valor"] for i in secao_3)
    secao_5_total = total_taxas + total_hon

    avisos = [
        "BASE NORMATIVA: NBR 14653 (todas as partes aplicaveis), Resolucao CONFEA 1.010/2005, Resolucao COFECI 957/2006. Profissional habilitado: Engenheiro Civil/Agronomo (CREA) ou Corretor de Imoveis Avaliador (CRECI/CNAI).",
        (f"NIVEL DE PRECISAO: {nivel.upper()}. " + (
            "Inclui tratamento estatistico completo (regressao linear, intervalo de confianca 80-95%) — nivel adequado para pericia judicial." if nivel == "rigorosa" else
            "Fundamentacao padrao com 5-15 amostras de mercado — adequado para finalidades particulares e bancarias." if nivel == "normal" else
            "Fundamentacao limitada com poucas amostras — laudo estimativo, nao recomendado para pericia judicial.")),
        "PRAZO DE ENTREGA: vistoria em 3-5 dias uteis. Elaboracao do laudo em 7-15 dias uteis (rigorosa pode levar ate 30 dias). Total: 10-35 dias do recebimento dos documentos a entrega final.",
        "IMPORTANTE: o laudo tem validade conforme proposito. Para fins bancarios, geralmente 90 dias. Para pericia judicial, conforme determinacao do juizo. Para venda particular, recomenda-se atualizar a cada 6 meses.",
    ]
    if finalidade == "judicial":
        avisos.append("PERICIA JUDICIAL: o profissional e nomeado pelo juizo OU contratado por uma das partes como ASSISTENTE TECNICO. Em ambos os casos, o profissional pode ser convocado a comparecer em audiencia para esclarecimentos. Honorarios de comparecimento em audiencia (se solicitado) NAO estao inclusos — cobrados a parte (R$ 500-1500/comparecimento).")
    if finalidade == "bancaria":
        avisos.append("AVALIACAO BANCARIA: alguns bancos exigem template proprio (Caixa Sistema SIC, BB ALFA, etc). A Romatec adapta o formato conforme exigencia da instituicao. Bancos podem exigir cadastro previo do avaliador na sua plataforma.")

    condicoes = [
        {"rotulo": "1a parcela — na assinatura", "descricao": "50% do valor total da avaliacao", "valor": secao_5_total * 0.5},
        {"rotulo": "2a parcela — na entrega do laudo", "descricao": "50% restante", "valor": secao_5_total * 0.5},
    ]

    base_calculo = []
    if faixa != "outro":
        base_calculo.append({"rotulo": f"Faixa {desc_faixa}", "formula": f"{mult_sm} SM × R$ {sm:.2f}", "valor_resultado": sm * mult_sm})
    else:
        base_calculo.append({"rotulo": "Honorario base customizado", "formula": "Valor acordado", "valor_resultado": valor_outro})
    if fator_precisao != 1.0:
        base_proj = (sm * mult_sm if faixa != "outro" else valor_outro) * fator_precisao
        base_calculo.append({"rotulo": f"Fator de precisao {nivel}", "formula": f"× {fator_precisao:.2f}", "valor_resultado": base_proj})
    if fator_finalidade != 1.0:
        base_calculo.append({"rotulo": f"Fator de finalidade {finalidade}", "formula": f"× {fator_finalidade:.2f}", "valor_resultado": honorario_projeto})
    base_calculo.append({"rotulo": "Honorarios Tecnicos finais", "formula": "Base × precisao × finalidade", "valor_resultado": honorario_projeto})
    base_calculo.append({"rotulo": "Entrega e Revisao", "formula": f"0.5 SM × R$ {sm:.2f}", "valor_resultado": honorario_assessoria})

    return {"custos": {
        "secao_1_projetos": secao_1, "secao_2_taxas": secao_2, "secao_3_honorarios": secao_3,
        "condicoes_pagamento": condicoes, "base_calculo": base_calculo, "secao_4_checklist": secao_4,
        "secao_5_total": round(secao_5_total, 2), "avisos": avisos,
    }, "fontes": fontes}
