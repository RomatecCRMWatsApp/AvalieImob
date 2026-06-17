# @module services.pricing.projeto_executivo — Engine de Projeto Executivo (port FIEL da ZAYRA).
# Port de src/services/pricing/projetoExecutivo.ts (v3.24.5–v3.24.8 do RomatecVoiceAgent).
# DOIS BLOCOS: 🅰 Honorários Técnicos (Romatec, parcelas 50/50) · 🅱 Despesas Administrativas
# (cliente paga à parte, fora das parcelas). Taxa de esboço R$ 750 é INFORMATIVA (fora do total).
from __future__ import annotations

import math


def round2(n: float) -> float:
    """HALF_UP em 2 casas (espelha Math.round((n+EPSILON)*100)/100 da ZAYRA)."""
    return math.floor(float(n) * 100 + 0.5) / 100.0


def calcular_taxa_ocupacao(area_construir: float, area_terreno: float | None):
    if not area_terreno or area_terreno <= 0:
        return None
    return round2((area_construir / area_terreno) * 100)


DEFAULTS = {
    "VALOR_M2": 25.00,
    "TAXA_ESBOCO": 750.00,
    "ART_VALOR": 233.94,
    "TRT_VALOR": 93.40,
    "AREA_LIMITE_TRT": 80.00,
}

PROJETOS_DEFAULT = [
    {"codigo": "mapa_situacao", "nome": "Mapa de Situação e Localização", "ordem": 1, "selecionado": True,
     "detalhamento_entrega": (
         "Prancha contendo planta de situação (quadra/lote), planta de localização do imóvel, "
         "orientação magnética (Norte), coordenadas de referência (SIRGAS2000), confrontantes, "
         "vias de acesso, recuos, taxa de ocupação e coeficiente de aproveitamento conforme "
         "legislação municipal.")},
    {"codigo": "arquitetonico", "nome": "Projeto Arquitetônico", "ordem": 2, "selecionado": True,
     "detalhamento_entrega": (
         "Plantas baixas de todos os pavimentos com cotas e áreas, planta de cobertura, planta "
         "de implantação, cortes longitudinal e transversal (mínimo 2), fachadas (mínimo 2), "
         "planta de layout, memorial descritivo e quadro de áreas, em conformidade com as "
         "NBR 13531 e NBR 13532.")},
    {"codigo": "hidraulico", "nome": "Projeto Hidráulico (Água Fria)", "ordem": 3, "selecionado": True,
     "detalhamento_entrega": (
         "Planta baixa hidráulica por pavimento, vistas isométricas dos pontos de consumo, "
         "detalhes de barrilete e reservatório, dimensionamento de tubulações, quantitativo de "
         "materiais e memorial de cálculo conforme NBR 5626.")},
    {"codigo": "sanitario", "nome": "Projeto Sanitário (Esgoto e Águas Pluviais)", "ordem": 4, "selecionado": True,
     "detalhamento_entrega": (
         "Planta baixa de esgoto sanitário, planta baixa de águas pluviais, vistas isométricas, "
         "detalhes de caixa de inspeção, fossa séptica e sumidouro (quando aplicável), "
         "dimensionamento conforme NBR 8160 e NBR 10844, e quantitativo de materiais.")},
    {"codigo": "eletrico", "nome": "Projeto Elétrico", "ordem": 5, "selecionado": True,
     "detalhamento_entrega": (
         "Planta baixa de pontos elétricos por pavimento, diagrama unifilar, quadro de cargas, "
         "dimensionamento de condutores e proteções, detalhe de entrada de energia conforme padrão "
         "da concessionária (Equatorial Maranhão), memorial descritivo conforme NBR 5410 e "
         "quantitativo de materiais.")},
    {"codigo": "estrutural", "nome": "Projeto Estrutural", "ordem": 6, "selecionado": True,
     "detalhamento_entrega": (
         "Planta de locação de pilares, planta de formas por pavimento, detalhamento de vigas, "
         "lajes, pilares e fundações, memorial de cálculo, especificação de materiais (concreto "
         "e aço), em conformidade com NBR 6118 e NBR 6122.")},
    {"codigo": "pci", "nome": "Projeto de Prevenção e Combate a Incêndio (PCI)", "ordem": 7, "selecionado": False,
     "detalhamento_entrega": (
         "Planta baixa de PCI com rotas de fuga, localização de extintores, hidrantes, "
         "iluminação de emergência e sinalização, memorial descritivo conforme Normas Técnicas "
         "do CBMMA e NBR 9077, para protocolo junto ao Corpo de Bombeiros Militar do Maranhão.")},
]

CNO_OBSERVACAO = (
    "O Cadastro Nacional de Obras (CNO) junto à Receita Federal do Brasil será gerado e "
    "vinculado a esta obra APÓS a expedição do Alvará de Construção pelo município de "
    "Açailândia/MA, em conformidade com a IN RFB nº 2.021/2021. A CONTRATADA se responsabilizará "
    "pelo cadastramento mediante apresentação prévia do Alvará pelo CONTRATANTE.")

AVISO_TAXA_ESBOCO = (
    "A Hora Técnica de Anteprojeto e Croqui (R$ 750,00 — item informativo) NÃO está incluída no "
    "VALOR TOTAL desta proposta. Será cobrada APENAS se o CONTRATANTE optar por não prosseguir "
    "com a fase executiva após a entrega do esboço arquitetônico aprovado. Caso prossiga, este "
    "valor é absorvido pelo contrato.")

AVISO_CNO_EXECUTIVO = (
    "O CADASTRO NACIONAL DE OBRAS (CNO) na Receita Federal será vinculado à obra apenas APÓS a "
    "expedição do Alvará de Construção pela Prefeitura. A CONTRATADA executa o cadastramento "
    "quando o CONTRATANTE apresentar o Alvará.")

AVISO_DESPESAS = (
    "Os valores das Despesas Administrativas NÃO compõem os Honorários Técnicos e NÃO estão "
    "sujeitos ao parcelamento 50/50. São pagos pelo CONTRATANTE diretamente aos órgãos competentes "
    "ou reembolsados à CONTRATADA mediante apresentação dos comprovantes.")

AVISO_ART = (
    "A ART (Anotação de Responsabilidade Técnica) junto ao CREA-MA exige profissional Engenheiro "
    "ou Arquiteto registrado. A Romatec subcontrata o profissional habilitado mediante aditivo "
    "contratual quando esta opção for selecionada.")

AVISO_TRT = (
    "O TRT (Termo de Responsabilidade Técnica) junto ao CFT/MA é emitido diretamente pelo "
    "profissional José Romário Pinto Bezerra — Técnico em Edificações (CFT/MA 01209185369). "
    "Aplicável a obras de até 80m² conforme Lei 13.639/2018.")

CHECKLIST = [
    {"texto": "RG e CPF do proprietário (cópia simples)", "obrigatorio": True},
    {"texto": "Comprovante de residência atualizado (máx. 90 dias)", "obrigatorio": True},
    {"texto": "Escritura ou matrícula atualizada do imóvel (máx. 90 dias)", "obrigatorio": True, "imprescindivel": True},
    {"texto": "IPTU do exercício atual (com situação em dia)", "obrigatorio": True},
    {"texto": "Croqui ou levantamento topográfico do terreno (se disponível)", "obrigatorio": False},
    {"texto": "Programa de necessidades — descrição dos ambientes desejados", "obrigatorio": True},
    {"texto": "Referências visuais / inspiração (opcional)", "obrigatorio": False},
]


def _fmt(v: float) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def renderizar_forma_pagamento(tag: str, total_honorarios: float, custom: str | None = None) -> dict:
    if tag == "integral":
        return {"tag": tag,
                "texto_renderizado": f"Pagamento à vista no valor de R$ {_fmt(total_honorarios)} na assinatura do contrato."}
    if tag == "sinal_mais_1":
        metade = round2(total_honorarios * 0.5)
        resto = round2(total_honorarios - metade)
        return {"tag": tag, "texto_renderizado": (
            f"Pagamento em 2 (duas) parcelas: R$ {_fmt(metade)} como SINAL no início (assinatura do contrato / "
            f"aprovação do anteprojeto) e R$ {_fmt(resto)} na ENTREGA FINAL dos projetos executivos em PDF "
            f"via WhatsApp e e-mail.")}
    if tag == "sinal_mais_2":
        sinal = round2(total_honorarios * 0.5)
        restante = round2(total_honorarios - sinal)
        parc = round2(restante / 2)
        ultima = round2(restante - parc)
        return {"tag": tag, "texto_renderizado": (
            f"Pagamento em 3 (três) parcelas: R$ {_fmt(sinal)} como SINAL no início; "
            f"R$ {_fmt(parc)} na entrega do anteprojeto aprovado; e R$ {_fmt(ultima)} na ENTREGA FINAL "
            f"dos projetos executivos em PDF via WhatsApp e e-mail.")}
    if tag == "duas_vezes":
        p1 = round2(total_honorarios * 0.5)
        p2 = round2(total_honorarios - p1)
        return {"tag": tag, "texto_renderizado": (
            f"Pagamento em 2 (duas) parcelas: R$ {_fmt(p1)} na assinatura do contrato e R$ {_fmt(p2)} "
            f"na ENTREGA FINAL dos projetos executivos em PDF via WhatsApp e e-mail.")}
    # personalizada
    return {"tag": "personalizada",
            "texto_renderizado": (custom.strip() if (custom and custom.strip()) else "A combinar entre as partes."),
            "detalhes_custom": custom}


def _despesa(item, legado_incluir, legado_valor):
    if item is not None:
        return {"incluir": bool(item.get("incluir")), "valor": float(item.get("valor") or 0)}
    if legado_incluir is not None:
        return {"incluir": bool(legado_incluir), "valor": float(legado_valor or 0)}
    return {"incluir": False, "valor": 0.0}


def calcular_projeto_executivo(dados: dict) -> dict:
    area_construir = float(dados.get("area_construir") or 0)
    if area_construir <= 0:
        raise ValueError("area_construir deve ser maior que zero")
    valor_m2 = float(dados.get("valor_m2") or DEFAULTS["VALOR_M2"])
    if valor_m2 <= 0:
        raise ValueError("valor_m2 deve ser maior que zero")
    area_terreno = dados.get("area_terreno")
    area_terreno = float(area_terreno) if area_terreno not in (None, "", 0) else None
    if area_terreno is not None and area_terreno > 0 and area_construir > area_terreno:
        raise ValueError("Área a construir não pode ser maior que a área do terreno.")
    taxa_ocupacao = calcular_taxa_ocupacao(area_construir, area_terreno)

    valor_projetos = round2(area_construir * valor_m2)

    auto = dados.get("responsabilidade_auto") is not False
    if not auto and dados.get("responsabilidade_tipo"):
        responsabilidade_tipo = dados["responsabilidade_tipo"]
    else:
        responsabilidade_tipo = "ART" if area_construir > DEFAULTS["AREA_LIMITE_TRT"] else "TRT"
    if dados.get("responsabilidade_valor") is not None:
        responsabilidade_valor = round2(float(dados["responsabilidade_valor"]))
    else:
        responsabilidade_valor = round2(DEFAULTS["ART_VALOR"] if responsabilidade_tipo == "ART" else DEFAULTS["TRT_VALOR"])

    subtotal_honorarios = round2(valor_projetos + responsabilidade_valor)
    desconto_honorarios = round2(float(dados.get("desconto_honorarios") or dados.get("desconto") or 0))
    total_honorarios = round2(subtotal_honorarios - desconto_honorarios)
    parcela_inicial = round2(total_honorarios * 0.5)
    parcela_final = round2(total_honorarios - parcela_inicial)

    dilig = _despesa(dados.get("diligencia_secretaria"), dados.get("diligencia_incluir"), dados.get("diligencia_valor"))
    alvara = _despesa(dados.get("taxa_alvara_municipio"), dados.get("alvara_incluir"), dados.get("alvara_valor"))
    placa = _despesa(dados.get("placa_obra"), dados.get("placa_incluir"), dados.get("placa_valor"))
    v_dilig = round2(dilig["valor"]) if dilig["incluir"] else 0
    v_alvara = round2(alvara["valor"]) if alvara["incluir"] else 0
    v_placa = round2(placa["valor"]) if placa["incluir"] else 0
    subtotal_despesas = round2(v_dilig + v_alvara + v_placa)

    taxa_esboco_valor = round2(float(dados.get("taxa_esboco") or DEFAULTS["TAXA_ESBOCO"]))

    forma_tag = dados.get("forma_pagamento_tag") or "sinal_mais_1"
    forma_pagamento = renderizar_forma_pagamento(forma_tag, total_honorarios, dados.get("forma_pagamento_custom"))

    total_geral = round2(total_honorarios + subtotal_despesas)

    projetos = dados.get("projetos_selecionados") or PROJETOS_DEFAULT
    ativos = [p for p in projetos if p.get("selecionado")]
    secao_1 = [f"{p['nome']}: {p['detalhamento_entrega']}" for p in ativos]
    n = len(ativos)

    secao_3 = [
        {"ordem": 1,
         "descricao": (f"Projetos Executivos ({n} projeto{'' if n == 1 else 's'}) — "
                       f"{area_construir:.2f}m² × R$ {valor_m2:.2f}/m²"),
         "valor": valor_projetos},
        {"ordem": 2,
         "descricao": ("ART — Anotação de Responsabilidade Técnica (CREA-MA)" if responsabilidade_tipo == "ART"
                       else "TRT — Termo de Responsabilidade Técnica (CFT/MA)"),
         "valor": responsabilidade_valor,
         "observacao": AVISO_ART if responsabilidade_tipo == "ART" else AVISO_TRT},
    ]

    secao_2 = []
    if dilig["incluir"]:
        secao_2.append({"ordem": 1, "descricao": "Diligência de Protocolo na Secretaria de Habitação e Regularização Fundiária",
                        "valor": v_dilig, "observacao": "Inclui impressão 2 vias, certidões, protocolo, acompanhamento, retirada do Alvará."})
    if alvara["incluir"]:
        secao_2.append({"ordem": 2, "descricao": "Taxa de Expedição de Alvará de Construção",
                        "valor": v_alvara, "observacao": "Valor da Prefeitura Municipal pago direto pelo cliente OU reembolsado."})
    if placa["incluir"]:
        secao_2.append({"ordem": 3, "descricao": "Confecção e Instalação da Placa de Obra",
                        "valor": v_placa, "observacao": "Padrão CREA/CFT + legislação municipal."})

    condicoes = []
    if forma_tag == "integral":
        condicoes.append({"rotulo": "1ª parcela — à vista", "descricao": "100% na assinatura", "valor": total_honorarios})
    elif forma_tag in ("sinal_mais_1", "duas_vezes"):
        condicoes += [
            {"rotulo": "1ª parcela — sinal", "descricao": "50% na assinatura/aprovação do anteprojeto", "valor": parcela_inicial},
            {"rotulo": "2ª parcela — entrega final", "descricao": "50% na entrega via WhatsApp + e-mail", "valor": parcela_final},
        ]
    elif forma_tag == "sinal_mais_2":
        restante = round2(total_honorarios - parcela_inicial)
        meio = round2(restante / 2)
        final = round2(restante - meio)
        condicoes += [
            {"rotulo": "1ª parcela — sinal", "descricao": "50% na assinatura", "valor": parcela_inicial},
            {"rotulo": "2ª parcela — anteprojeto aprovado", "descricao": "25%", "valor": meio},
            {"rotulo": "3ª parcela — entrega final", "descricao": "25%", "valor": final},
        ]

    base_calculo = [
        {"rotulo": f"Projetos Executivos ({n} projeto{'' if n == 1 else 's'})",
         "formula": f"área ({area_construir:.2f} m²) × valor_m2 (R$ {valor_m2:.2f})", "valor_resultado": valor_projetos},
        {"rotulo": f"{responsabilidade_tipo} {'auto' if auto else 'manual'}",
         "formula": (f"área {'> 80m² -> ART' if area_construir > 80 else '<= 80m² -> TRT'}" if auto
                     else f"override manual = {responsabilidade_tipo}"),
         "valor_resultado": responsabilidade_valor},
        {"rotulo": "Parcelamento 50/50", "formula": "total_honorarios / 2", "valor_resultado": parcela_inicial},
    ]

    avisos = [AVISO_TAXA_ESBOCO, AVISO_CNO_EXECUTIVO, AVISO_DESPESAS,
              AVISO_ART if responsabilidade_tipo == "ART" else AVISO_TRT]

    custos = {
        "secao_1_projetos": secao_1, "secao_2_taxas": secao_2, "secao_3_honorarios": secao_3,
        "condicoes_pagamento": condicoes, "base_calculo": base_calculo, "secao_4_checklist": CHECKLIST,
        "secao_5_total": total_geral, "avisos": avisos,
    }

    return {"custos": custos, "fontes": {}, "projeto_executivo": {
        "honorarios": {
            "area_construir": area_construir, "area_terreno": area_terreno,
            "taxa_ocupacao_percentual": taxa_ocupacao, "valor_m2": valor_m2, "valor_projetos": valor_projetos,
            "responsabilidade_tipo": responsabilidade_tipo, "responsabilidade_auto": auto,
            "responsabilidade_valor": responsabilidade_valor, "subtotal_honorarios": subtotal_honorarios,
            "desconto_honorarios": desconto_honorarios, "total_honorarios": total_honorarios,
            "parcela_inicial": parcela_inicial, "parcela_final": parcela_final,
        },
        "despesas_administrativas": {
            "diligencia_secretaria": {"incluir": dilig["incluir"], "valor": v_dilig},
            "taxa_alvara_municipio": {"incluir": alvara["incluir"], "valor": v_alvara},
            "placa_obra": {"incluir": placa["incluir"], "valor": v_placa},
            "subtotal_despesas": subtotal_despesas,
        },
        "taxa_esboco": {"valor": taxa_esboco_valor, "cobranca_condicional": True,
                        "nota": "Cobrada apenas se o CONTRATANTE não prosseguir com a fase executiva."},
        "forma_pagamento": forma_pagamento,
        "resumo": {"total_honorarios": total_honorarios, "total_despesas": subtotal_despesas, "total_geral": total_geral},
        "projetos_selecionados": projetos, "cno_observacao": CNO_OBSERVACAO,
    }}
