# @module services.pricing.georreferenciamento — Engine de Georreferenciamento Rural (INCRA/SIGEF).
# Port FIEL de pricing/georreferenciamento.ts (ZAYRA v3.23.6, modelo PROP-2026-0011-R1).
# Regras:
#   Honorários Romatec (secao_5_total) = TRT (CFT R$93,40) + Técnicos + Assessoria (1 SM).
#   Técnicos = (área×R$/ha + vértices×R$/v + diárias×R$/dia + km×R$/km) × complexidade,
#              com mínimo garantido de 2 SM. Emolumentos cartório/SIGEF ficam em secao_2
#              como INFORMATIVO (a cargo do cliente, fora do total).
#   Opcionais (CCIR/CAR/ITR/anuência/retificação) saem em seção informativa própria.
# Base normativa: Lei 10.267/2001, NTGIR 3a Ed. INCRA, Res. CONFEA 1.108/2020, Lei 6.015/1973.
from __future__ import annotations

from services.pricing.params import (
    HONORARIOS_PROJETO, HONORARIOS_ASSESSORIA, OPCIONAIS_GEORREF,
    salario_minimo, anotacao_tecnica,
)
from services.pricing.tjma import calcular_emolumentos

ESCOPO_GEO_RURAL = [
    "Levantamento topografico georreferenciado (GNSS RTK / Estacao Total)",
    "Marcacao fisica e coleta de coordenadas WGS84/SIRGAS2000 nos vertices da poligonal",
    "Calculo analitico de area e perimetro com fechamento dentro da tolerancia NBR 13133",
    "Memorial Descritivo conforme NTGIR 3a Edicao (INCRA)",
    "Planta georreferenciada com poligonal, confrontantes e quadro de coordenadas",
    "Submissao ao SIGEF/INCRA com certificado digital",
    "Acompanhamento de exigencias ate a certificacao final pelo INCRA",
    "Apoio ao protocolo de averbacao do memorial certificado no Cartorio",
]


def round2(n: float) -> float:
    """HALF_UP em 2 casas — espelha Math.round((n+EPSILON)*100)/100 do TS."""
    import math
    return math.floor((n + 1e-9) * 100 + 0.5) / 100


def _num(d: dict, k: str, default: float = 0) -> float:
    v = d.get(k, default)
    try:
        return float(v) if v is not None else float(default)
    except (TypeError, ValueError):
        return float(default)


def calcular_georreferenciamento(dados: dict) -> dict:
    """Recebe InputGeorreferenciamento (dict) e retorna {custos, fontes} idêntico à ZAYRA."""
    sm = salario_minimo()
    hp = HONORARIOS_PROJETO

    area_hectares = _num(dados, "area_hectares", 0)
    numero_vertices = _num(dados, "numero_vertices", 0)
    distancia_km = _num(dados, "distancia_km", 0)
    numero_diarias = _num(dados, "numero_diarias", 0)
    complexidade = dados.get("complexidade", "media")
    finalidade = dados.get("finalidade")
    tem_matricula = bool(dados.get("tem_matricula", True))
    valor_outros_servicos = _num(dados, "valor_outros_servicos", 0)

    # Validações mínimas
    if not (area_hectares > 0):
        raise ValueError("area_hectares deve ser > 0")
    if not (numero_vertices >= 3):
        raise ValueError("numero_vertices deve ser >= 3 (poligonal minima)")
    if complexidade not in ("simples", "media", "alta"):
        raise ValueError(
            f"complexidade invalida: {complexidade} (esperado: simples | media | alta)"
        )

    # ── Seção 1: escopo do serviço ──────────────────────────────────────────
    secao_1_projetos = list(ESCOPO_GEO_RURAL)

    # ── Seção 2: taxas/emolumentos de terceiros (INFORMATIVO — pago pelo cliente)
    secao_2_taxas = []
    fontes: dict = {}
    ordem = 1

    valor_estimado_imovel = max(area_hectares * 5000, 50000)
    try:
        emol = calcular_emolumentos("averbacao_construcao", valor_estimado_imovel)
        secao_2_taxas.append({
            "ordem": ordem, "descricao": "Emolumentos cartorarios — averbacao do memorial certificado",
            "valor": emol["valor"],
            "observacao": "Tabela TJMA Res. 143/2025 | Estimativa baseada em area x R$ 5.000/ha",
        })
        ordem += 1
        fontes["tjma"] = {"fonte": emol.get("fonte"), "consultadoEm": emol.get("consultadoEm")}
    except Exception as err:  # pragma: no cover
        secao_2_taxas.append({
            "ordem": ordem, "descricao": "Emolumentos cartorarios — averbacao do memorial certificado",
            "valor": 0, "pendente": True,
            "observacao": f"A confirmar em cartorio competente. Erro consulta: {err}",
        })
        ordem += 1

    if finalidade in ("DESMEMBRAMENTO", "REMEMBRAMENTO"):
        secao_2_taxas.append({
            "ordem": ordem,
            "descricao": (
                "Emolumentos cartorarios — encerramento da matricula atual + abertura de nova matricula"
                if finalidade == "DESMEMBRAMENTO"
                else "Emolumentos cartorarios — unificacao das matriculas em matricula unica"
            ),
            "valor": 0, "pendente": True,
            "observacao": "A apurar no Cartorio competente conforme tabela TJMA vigente",
        })
        ordem += 1

    secao_2_taxas.append({
        "ordem": ordem, "descricao": "Certificacao SIGEF/INCRA", "valor": 0,
        "observacao": "Gratuita por lei (Lei 10.267/2001). Tempo medio analise INCRA: 60-180 dias.",
    })
    ordem += 1

    if valor_outros_servicos > 0:
        secao_2_taxas.append({
            "ordem": ordem, "descricao": "Outros servicos / despesas especificas do projeto",
            "valor": valor_outros_servicos,
            "observacao": "Conforme acordado com o cliente (taxas extras, certidoes, deslocamentos especiais)",
        })
        ordem += 1

    # ── Seção 3: honorários Romatec (TRT + Técnicos + Assessoria) ────────────
    valor_por_hectare = _num(dados, "valor_por_hectare", 0) or hp["geo_rural_por_hectare"]
    valor_por_vertice = _num(dados, "valor_por_vertice", 0) or hp["geo_rural_por_vertice"]
    valor_diaria = _num(dados, "valor_diaria_campo", 0) or hp["geo_rural_diaria_campo"]
    valor_por_km = _num(dados, "valor_km_deslocamento", 0) or hp["geo_rural_por_km_deslocamento"]

    subtotal_area = round2(area_hectares * valor_por_hectare)
    subtotal_vertices = round2(numero_vertices * valor_por_vertice)
    subtotal_diarias = round2(numero_diarias * valor_diaria)
    subtotal_km = round2(distancia_km * valor_por_km)
    subtotal_campo = round2(subtotal_area + subtotal_vertices + subtotal_diarias + subtotal_km)

    multiplicador = (
        hp["geo_rural_complexidade_alta"] if complexidade == "alta"
        else hp["geo_rural_complexidade_media"] if complexidade == "media"
        else hp["geo_rural_complexidade_simples"]
    )

    honorario_tecnico = round2(subtotal_campo * multiplicador)
    minimo_garantido = round2(sm * hp["geo_rural_minimo_sm"])
    aplicou_minimo = False
    if honorario_tecnico < minimo_garantido:
        honorario_tecnico = minimo_garantido
        aplicou_minimo = True

    honorario_assessoria = round2(sm * HONORARIOS_ASSESSORIA["padrao_sm"])

    at = anotacao_tecnica("trt_cft")
    trt = round2(at["valor"])

    if aplicou_minimo:
        memoria_tecnico = (
            f"Minimo garantido aplicado ({hp['geo_rural_minimo_sm']} SM = R$ {minimo_garantido:.2f}). "
            f"Calculo de campo: {area_hectares}ha x R$ {valor_por_hectare:.2f} + {numero_vertices}v x "
            f"R$ {valor_por_vertice:.2f} + {numero_diarias}d x R$ {valor_diaria:.2f} + {distancia_km}km x "
            f"R$ {valor_por_km:.2f} = R$ {subtotal_campo:.2f} x {multiplicador}x = "
            f"R$ {subtotal_campo * multiplicador:.2f} (abaixo do minimo)."
        )
    else:
        memoria_tecnico = (
            f"Area: {area_hectares} ha x R$ {valor_por_hectare:.2f}/ha = R$ {subtotal_area:.2f} | "
            f"Vertices: {numero_vertices} x R$ {valor_por_vertice:.2f} = R$ {subtotal_vertices:.2f} | "
            f"Diarias de campo: {numero_diarias} x R$ {valor_diaria:.2f} = R$ {subtotal_diarias:.2f} | "
            f"Deslocamento: {distancia_km} km x R$ {valor_por_km:.2f}/km = R$ {subtotal_km:.2f} | "
            f"Subtotal R$ {subtotal_campo:.2f} x {multiplicador}x (complexidade {complexidade}) = "
            f"R$ {honorario_tecnico:.2f}"
        )

    secao_3_honorarios = [
        {
            "ordem": ordem,
            "descricao": f"{at['rotulo']} — Tec. em Agrimensura CFT/MA n. 01209185369. "
                         f"Anotacao obrigatoria do responsavel tecnico.",
            "valor": trt, "observacao": at["fonte"],
        },
        {
            "ordem": ordem + 1,
            "descricao": "Honorarios Tecnicos de Georreferenciamento — levantamento topografico, "
                         "marcacao de vertices, memorial descritivo, planta georreferenciada e "
                         "submissao ao SIGEF/INCRA",
            "valor": honorario_tecnico, "observacao": memoria_tecnico,
        },
        {
            "ordem": ordem + 2,
            "descricao": "Honorarios de Assessoria e Acompanhamento — submissao SIGEF, diligencias "
                         "junto ao INCRA, atendimento exigencias, emissao certificacao final, "
                         "averbacao no cartorio",
            "valor": honorario_assessoria,
            "observacao": f"Referencia: 1 salario minimo 2026 (R$ {sm:.2f})",
        },
    ]
    ordem += 3

    # ── Total Romatec — só os 3 itens acima ─────────────────────────────────
    total_romatec = round2(trt + honorario_tecnico + honorario_assessoria)

    # ── Condições de pagamento (3 parcelas) ─────────────────────────────────
    p1 = round2(trt + honorario_tecnico * 0.5 + honorario_assessoria * 0.5)
    p2 = round2(honorario_tecnico * 0.5)
    p3 = round2(honorario_assessoria * 0.5)

    soma_parcelas = round2(p1 + p2 + p3)
    if abs(soma_parcelas - total_romatec) > 0.01:
        raise ValueError(
            f"Erro de fechamento das parcelas: p1+p2+p3 = R$ {soma_parcelas:.2f} != "
            f"total R$ {total_romatec:.2f}"
        )

    condicoes_pagamento = [
        {"rotulo": "1a parcela — na assinatura",
         "descricao": "TRT integral + 50% Honorarios Tecnicos + 50% Honorarios de Assessoria", "valor": p1},
        {"rotulo": "2a parcela — entrega do memorial e submissao SIGEF",
         "descricao": "50% restante dos Honorarios Tecnicos", "valor": p2},
        {"rotulo": "3a parcela — certificacao final INCRA",
         "descricao": "50% restante dos Honorarios de Assessoria", "valor": p3},
    ]

    # ── Seção 4: checklist de documentos do cliente ─────────────────────────
    secao_4_checklist = [
        {"texto": "Certidao de Inteiro Teor da Matricula — ATUALIZADA (max. 30 dias)",
         "obrigatorio": True, "imprescindivel": not tem_matricula},
        {"texto": "CCIR (Certificado de Cadastro de Imovel Rural — INCRA) atualizado", "obrigatorio": True},
        {"texto": "ITR pago (5 ultimos exercicios)", "obrigatorio": True},
        {"texto": "CAR (Cadastro Ambiental Rural) emitido", "obrigatorio": True},
        {"texto": "RG/CPF do proprietario", "obrigatorio": True},
        {"texto": "Comprovante de residencia do proprietario", "obrigatorio": True},
        {"texto": "Anuencia dos confrontantes (planta com assinatura dos vizinhos confrontantes da poligonal)",
         "obrigatorio": True, "imprescindivel": True},
        {"texto": "Senha gov.br (nivel prata ou ouro) do proprietario — necessaria para acesso ao Portal SIGEF/INCRA",
         "obrigatorio": True},
        {"texto": "Documentos de eventuais usufrutuarios, hipotecas ou onus reais averbados (se houver)",
         "obrigatorio": False},
        {"texto": "Plantas, medicoes ou levantamentos anteriores do imovel (se houver)", "obrigatorio": False},
    ]

    # ── Seção opcional: serviços adicionais (5 linhas, sempre renderiza) ─────
    opc = dados.get("opcionais") or {}
    op_param = OPCIONAIS_GEORREF

    def _opc(chave: str) -> dict:
        v = opc.get(chave)
        if v:
            return v
        # fallback p/ o form genérico (flat): opc_ccir / opc_car / ... = bool
        flat = dados.get(f"opc_{chave}")
        if flat is not None:
            return {"contratado": bool(flat)}
        return {}

    opc_itens = []
    subtotal_opcionais = 0.0

    # CCIR
    o = _opc("ccir")
    vu = o.get("valor_unitario", op_param["ccir"]["valor_unitario"])
    contratado = bool(o.get("contratado"))
    sub = round2(vu) if contratado else 0
    if contratado:
        subtotal_opcionais = round2(subtotal_opcionais + sub)
    opc_itens.append({"chave": "ccir", "rotulo": op_param["ccir"]["rotulo"],
                      "contratado": contratado, "valor_unitario": vu, "subtotal": sub})

    # CAR
    o = _opc("car")
    vu = o.get("valor_unitario", op_param["car"]["valor_unitario"])
    contratado = bool(o.get("contratado"))
    sub = round2(vu) if contratado else 0
    if contratado:
        subtotal_opcionais = round2(subtotal_opcionais + sub)
    opc_itens.append({"chave": "car", "rotulo": op_param["car"]["rotulo"],
                      "contratado": contratado, "valor_unitario": vu, "subtotal": sub})

    # ITR (por exercício)
    o = _opc("itr")
    vu = o.get("valor_unitario", op_param["itr"]["valor_unitario"])
    qtd = o.get("quantidade", 0) or 0
    contratado = bool(o.get("contratado"))
    sub = round2(vu * qtd) if contratado else 0
    if contratado:
        subtotal_opcionais = round2(subtotal_opcionais + sub)
    opc_itens.append({"chave": "itr", "rotulo": op_param["itr"]["rotulo"], "contratado": contratado,
                      "quantidade": qtd, "valor_unitario": vu, "subtotal": sub})

    # Anuência (por confrontante)
    o = _opc("anuencia")
    vu = o.get("valor_unitario", op_param["anuencia"]["valor_unitario"])
    qtd = o.get("quantidade", 0) or 0
    contratado = bool(o.get("contratado"))
    sub = round2(vu * qtd) if contratado else 0
    if contratado:
        subtotal_opcionais = round2(subtotal_opcionais + sub)
    opc_itens.append({"chave": "anuencia", "rotulo": op_param["anuencia"]["rotulo"], "contratado": contratado,
                      "quantidade": qtd, "valor_unitario": vu, "subtotal": sub})

    # Retificação (sob orçamento — não soma)
    o = _opc("retificacao")
    contratado = bool(o.get("contratado"))
    opc_itens.append({"chave": "retificacao", "rotulo": op_param["retificacao"]["rotulo"],
                      "contratado": contratado, "valor_unitario": "sob_orcamento", "subtotal": "sob_orcamento"})

    secao_opcionais_georref = {"itens": opc_itens, "subtotal": subtotal_opcionais}

    # ── Avisos e condições técnicas ─────────────────────────────────────────
    avisos = [
        "IMPORTANTE: Esta proposta esta em conformidade com a Lei 10.267/2001 (CNIR), NTGIR 3a Edicao "
        "(INCRA) e Resolucao CONFEA 1.108/2020. O servico exige profissional habilitado em Engenharia "
        "Cartografica/Agrimensura/Agronomia com habilitacao especifica no CREA ou CFT.",
        "TEMPO DE EXECUCAO: levantamento de campo (3-15 dias conforme acessibilidade), gabinete e memorial "
        "(5-10 dias), submissao SIGEF (2-5 dias), analise INCRA (60-180 dias). Total tipico: 90-210 dias "
        "do contrato a certificacao.",
        "ANUENCIA DOS CONFRONTANTES E IMPRESCINDIVEL. Sem a assinatura dos vizinhos confrontantes na planta, "
        "o INCRA rejeita a certificacao. A Romatec orienta o proprietario sobre a coleta das anuencias.",
        "EVENTUAIS DIVERGENCIAS DE AREA: se a area certificada (real, GPS) divergir significativamente da "
        "area registrada na matricula, sera necessaria RETIFICACAO DE AREA em paralelo (Lei 10.931/2004 "
        "administrativa OU judicial). Isso e cobrado a parte como servico adicional.",
    ]

    if finalidade:
        finalidade_aviso = {
            "CERTIFICACAO": "FINALIDADE: Certificacao no SIGEF/INCRA e averbacao do memorial certificado na matricula vigente.",
            "DESMEMBRAMENTO": "FINALIDADE: Certificacao no SIGEF/INCRA, encerramento da matricula atual e abertura de nova matricula para a area desmembrada.",
            "REMEMBRAMENTO": "FINALIDADE: Certificacao no SIGEF/INCRA e unificacao de matriculas confrontantes em matricula unica.",
            "RETIFICACAO": "FINALIDADE: Certificacao no SIGEF/INCRA e averbacao da nova area na matricula.",
        }.get(finalidade)
        if finalidade_aviso:
            avisos.append(finalidade_aviso)

    if not tem_matricula:
        avisos.append("ATENCAO: Imovel sem matricula registrada. Sera necessario USUCAPIAO ou abertura de "
                      "matricula previa antes do georreferenciamento. Esses procedimentos sao cobrados a parte.")

    if complexidade == "alta":
        avisos.append("COMPLEXIDADE ALTA: terreno acidentado, vegetacao densa, litigios de divisas ou inumeros "
                      "confrontantes. Multiplicador 1.6x sobre o calculo de campo. Diarias podem aumentar "
                      "conforme necessidade real.")

    # ── Base de cálculo explícita ───────────────────────────────────────────
    base_calculo = [
        {"rotulo": "Area (R$/hectare)",
         "formula": f"{area_hectares} ha x R$ {valor_por_hectare:.2f}/ha", "valor_resultado": subtotal_area},
        {"rotulo": "Vertices (R$/vertice GPS RTK)",
         "formula": f"{numero_vertices} vertices x R$ {valor_por_vertice:.2f}", "valor_resultado": subtotal_vertices},
    ]
    if numero_diarias > 0:
        base_calculo.append({"rotulo": "Diarias de campo",
                             "formula": f"{numero_diarias} dia(s) x R$ {valor_diaria:.2f}/dia",
                             "valor_resultado": subtotal_diarias})
    if distancia_km > 0:
        base_calculo.append({"rotulo": "Deslocamento",
                             "formula": f"{distancia_km} km x R$ {valor_por_km:.2f}/km",
                             "valor_resultado": subtotal_km})
    base_calculo.append({"rotulo": f"Subtotal de campo x complexidade {complexidade}",
                        "formula": f"R$ {subtotal_campo:.2f} x {multiplicador}x",
                        "valor_resultado": round2(subtotal_campo * multiplicador)})
    if aplicou_minimo:
        base_calculo.append({"rotulo": "Minimo garantido aplicado",
                            "formula": f"{hp['geo_rural_minimo_sm']} SM x R$ {sm:.2f}",
                            "valor_resultado": minimo_garantido})
    base_calculo.append({"rotulo": "Honorarios Tecnicos finais",
                        "formula": "Maior entre calculado e minimo" if aplicou_minimo else "Subtotal x complexidade",
                        "valor_resultado": honorario_tecnico})

    custos = {
        "secao_1_projetos": secao_1_projetos,
        "secao_2_taxas": secao_2_taxas,
        "secao_3_honorarios": secao_3_honorarios,
        "condicoes_pagamento": condicoes_pagamento,
        "base_calculo": base_calculo,
        "secao_4_checklist": secao_4_checklist,
        "secao_5_total": total_romatec,
        "avisos": avisos,
        "honorarios_romatec": {
            "trt": trt, "tecnicos": honorario_tecnico,
            "assessoria": honorario_assessoria, "total": total_romatec,
        },
        "secao_opcionais_georref": secao_opcionais_georref,
    }

    return {"custos": custos, "fontes": fontes}
