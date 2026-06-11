# @module services.pricing.demarcacao — Engine de Demarcação de Lotes (Urbana e Rural).
# Port FIEL de pricing/demarcacaoLotes.ts (ZAYRA v3.40.0, gold standard PROP-2026-0028-R1)
# + adapter adaptarDemarcacaoParaCustosCalculados (integrations/propostasConsultoria.ts).
# Ordem de cálculo: TRT/CFT + tecnicos_campo + adicional_campo (sobre tecnicos, antes da
# complexidade) + marcos + deslocamento + area → ×complexidade → +assessoria 5% → -desconto
# → mínimo garantido 2 SM sobre o core → +itens diretos (laudo, kit GNSS, alinhamento cerca).
# Opcionais (croqui/acompanhamento/jurídica) NÃO somam. Parcelas 3x (40/30/30) ou 2x (50/50).
# Base: Lei 10.267/2001, NTGIR 3a Ed., Lei 6.766/79, Lei 5.868/72, Tabela CFT 2026, CLT 192/193 + NR-15/16.
from __future__ import annotations

from services.pricing.params import DEMARCACAO_LOTES_2026, salario_minimo, anotacao_tecnica
from services.pricing.georreferenciamento import round2

COMPLEX_KEYS = ("simples", "media", "alta")
MARCOS_ORDEM = ("concreto", "tubo_galvanizado", "madeira")

ESCOPO_DEMARCACAO = [
    "Levantamento topografico georreferenciado da poligonal (GNSS RTK)",
    "Locacao/marcacao fisica dos vertices da poligonal com marcos padrao INCRA",
    "Calculo analitico de area e perimetro (fechamento NBR 13133)",
    "Memorial descritivo da demarcacao com coordenadas WGS84/SIRGAS2000",
    "Planta de demarcacao com poligonal, confrontantes e quadro de coordenadas",
    "Codificacao dos marcos conforme NTGIR 3a Edicao (credencial do tecnico)",
    "Termo de Responsabilidade Tecnica (TRT/CFT)",
    "Acompanhamento ate a entrega do trabalho de campo e pecas tecnicas",
]


def _num(v, default=0.0):
    try:
        return float(v) if v is not None else float(default)
    except (TypeError, ValueError):
        return float(default)


def calcular_demarcacao(dados: dict) -> dict:
    """Recebe InputDemarcacaoLotes (dict) e retorna {custos, fontes} adaptado à proposta."""
    cfg = DEMARCACAO_LOTES_2026
    SM = salario_minimo()

    subtipo = dados.get("subtipo")
    if subtipo not in ("demarcacao_urbana", "demarcacao_rural"):
        raise ValueError(f"subtipo invalido: {subtipo} (esperado: demarcacao_urbana | demarcacao_rural)")

    area_m2 = dados.get("area_m2")
    area_hectares = dados.get("area_hectares")
    if subtipo == "demarcacao_urbana":
        if not (_num(area_m2, 0) > 0):
            raise ValueError("subtipo=demarcacao_urbana exige area_m2 > 0")
        if area_hectares is not None:
            raise ValueError("subtipo=demarcacao_urbana nao deve informar area_hectares")
    else:
        if not (_num(area_hectares, 0) > 0):
            raise ValueError("subtipo=demarcacao_rural exige area_hectares > 0")
        if area_m2 is not None:
            raise ValueError("subtipo=demarcacao_rural nao deve informar area_m2")

    num_vertices = _num(dados.get("num_vertices"), 0)
    if not (num_vertices >= 3):
        raise ValueError("num_vertices deve ser >= 3 (poligonal minima)")

    complexidade = dados.get("complexidade")
    if complexidade not in COMPLEX_KEYS:
        raise ValueError(f"complexidade invalida: {complexidade} (esperado: simples | media | alta)")

    desconto_pct = _num(dados.get("desconto_pct"), 0)
    if desconto_pct < 0 or desconto_pct > cfg["desconto_max_pct"]:
        raise ValueError(f"desconto_pct invalido: {desconto_pct} (esperado [0, {cfg['desconto_max_pct']}])")

    diarias_equipe = _num(dados.get("diarias_equipe"), 0)
    if not (diarias_equipe >= 1):
        raise ValueError("diarias_equipe deve ser >= 1")
    km_deslocamento = _num(dados.get("km_deslocamento"), 0)
    if km_deslocamento < 0:
        raise ValueError("km_deslocamento deve ser >= 0")

    marcos = dados.get("marcos") if isinstance(dados.get("marcos"), list) else []
    # Conveniência UI: deriva marcos[] de campos simples (marco_tipo + marco_quantidade)
    # quando a lista detalhada não vem. valor_unitario_congelado vem da tabela cfg.
    if not marcos and dados.get("marco_tipo") in cfg["marcos"] and _num(dados.get("marco_quantidade"), 0) > 0:
        _mt = dados["marco_tipo"]
        marcos = [{"tipo": _mt, "quantidade": _num(dados.get("marco_quantidade"), 0),
                   "valor_unitario_congelado": cfg["marcos"][_mt]["valor_unitario"]}]
    soma_marcos = sum(_num(m.get("quantidade"), 0) for m in marcos)
    if dados.get("servico_piqueteamento") is True:
        if soma_marcos != num_vertices:
            raise ValueError(
                f"servico_piqueteamento=true exige Σ marcos.quantidade ({int(soma_marcos)}) === "
                f"num_vertices ({int(num_vertices)})"
            )

    # ── 1. TRT/CFT ───────────────────────────────────────────────────────────
    at = anotacao_tecnica("trt_cft")
    trt_cft = round2(at["valor"])

    # ── 2. Tecnicos de campo ─────────────────────────────────────────────────
    tecnicos_campo = round2(diarias_equipe * SM * cfg["fator_diaria_tecnico"])

    # ── 2-bis. Adicional de campo (insal/peric) sobre tecnicos_campo ─────────
    adicional_pct = _num(dados.get("adicional_campo_pct"), 0)
    if adicional_pct < 0 or adicional_pct > 40:
        raise ValueError(f"adicional_campo_pct invalido: {adicional_pct} (esperado [0, 40])")
    adicional_valor = round2((tecnicos_campo * adicional_pct) / 100)
    adicional_campo = {"aplicavel": adicional_pct > 0, "pct": adicional_pct, "valor": adicional_valor}

    # ── 3. Marcos discriminados ──────────────────────────────────────────────
    marcos_discriminados = []
    marcos_subtotal = 0.0
    for tipo in MARCOS_ORDEM:
        itens_tipo = [m for m in marcos if m.get("tipo") == tipo]
        qtd = sum(_num(m.get("quantidade"), 0) for m in itens_tipo)
        subtotal = round2(sum(_num(m.get("quantidade"), 0) * _num(m.get("valor_unitario_congelado"), 0) for m in itens_tipo))
        if qtd > 0:
            marcos_discriminados.append({"tipo": tipo, "qtd": qtd, "subtotal": subtotal})
            marcos_subtotal = round2(marcos_subtotal + subtotal)

    # ── 4. Deslocamento ──────────────────────────────────────────────────────
    deslocamento = round2(km_deslocamento * cfg["valor_km_deslocamento"])

    # ── 5. Area × valor unitario ─────────────────────────────────────────────
    if subtipo == "demarcacao_urbana":
        v_unit = dados.get("valor_unitario_area")
        v_unit = _num(v_unit) if v_unit is not None else cfg["valor_m2_urbano_default"]
        area_servico = round2(_num(area_m2) * v_unit)
    else:
        v_unit = dados.get("valor_unitario_area")
        v_unit = _num(v_unit) if v_unit is not None else cfg["valor_hectare_rural_default"]
        area_servico = round2(_num(area_hectares) * v_unit)

    # ── 6. Subtotal bruto (adicional integrado na base) ──────────────────────
    subtotal_bruto = round2(trt_cft + tecnicos_campo + adicional_valor + marcos_subtotal + deslocamento + area_servico)

    # ── 7. Complexidade ──────────────────────────────────────────────────────
    complexidade_multiplicador = cfg["complexidade_multiplicadores"][complexidade]
    subtotal_apos_complexidade = round2(subtotal_bruto * complexidade_multiplicador)

    # ── 8. Assessoria ────────────────────────────────────────────────────────
    assessoria = round2(subtotal_apos_complexidade * cfg["assessoria_pct"])

    # ── 9. Desconto ──────────────────────────────────────────────────────────
    base_desconto = round2(subtotal_apos_complexidade + assessoria)
    desconto_valor = round2((base_desconto * desconto_pct) / 100)

    # ── 10. Core (mínimo garantido 2 SM) ─────────────────────────────────────
    core = round2(base_desconto - desconto_valor)
    minimo = round2(cfg["minimo_garantido_sm"] * SM)
    aplicou_minimo = core < minimo
    if aplicou_minimo:
        core = minimo

    # ── 11. Itens diretos ────────────────────────────────────────────────────
    opcionais_raw = dados.get("opcionais") or {}

    # Laudo técnico direto (com retrocompat opcionais.laudo_tecnico)
    direto = dados.get("laudo_tecnico_direto") or {}
    opt_legacy = opcionais_raw.get("laudo_tecnico") or {}
    if direto.get("contratado"):
        mult = (direto.get("valor_unitario_sm_multiplicador")
                or cfg["laudo_tecnico_direto"]["valor_unitario_sm_multiplicador"] or 1.0)
        laudo_direto = {"contratado": True, "valor": round2(mult * SM)}
    elif opt_legacy.get("contratado"):
        mult = (opt_legacy.get("valor_unitario_sm_multiplicador")
                or cfg["laudo_tecnico_direto"]["valor_unitario_sm_multiplicador"] or 1.0)
        laudo_direto = {"contratado": True, "valor": round2(mult * SM)}
    else:
        laudo_direto = {"contratado": False, "valor": 0}

    # Kit GNSS (item fixo, default qtd=1, diaria 250)
    kit = dados.get("locacao_kit_gnss") or {}
    cfg_kit = cfg["locacao_kit_gnss"]
    diaria_default = cfg_kit["valor_unitario_diaria_default"]
    qtd_kit = _num(kit.get("qtd_diarias"), 1) if kit.get("qtd_diarias") is not None else 1.0
    if qtd_kit < 0:
        raise ValueError(f"locacao_kit_gnss.qtd_diarias invalido: {qtd_kit} (esperado >= 0)")
    diaria_kit = _num(kit.get("diaria"), diaria_default) if kit.get("diaria") is not None else diaria_default
    if diaria_kit < 0:
        raise ValueError(f"locacao_kit_gnss.diaria invalido: {diaria_kit} (esperado >= 0)")
    kit_contratado = qtd_kit > 0
    kit_gnss = {
        "contratado": kit_contratado, "qtd_diarias": qtd_kit, "diaria": round2(diaria_kit),
        "valor": round2(qtd_kit * diaria_kit) if kit_contratado else 0, "descritivo": cfg_kit["descritivo"],
    }

    # Alinhamento de cerca (item direto que soma — v3.63.5)
    ac = opcionais_raw.get("alinhamento_cerca") or {}
    ac_contratado = bool(ac.get("contratado"))
    ac_metros = _num(ac.get("metros"), 0)
    ac_vunit = _num(ac.get("valor_unitario"), cfg["opcionais"]["alinhamento_cerca"]["valor_unitario"]) \
        if ac.get("valor_unitario") is not None else cfg["opcionais"]["alinhamento_cerca"]["valor_unitario"]
    alinhamento_cerca = {
        "contratado": ac_contratado, "metros": ac_metros if ac_contratado else 0,
        "valor_unitario": ac_vunit, "valor": round2(ac_metros * ac_vunit) if ac_contratado else 0,
    }

    # ── 12. Total ────────────────────────────────────────────────────────────
    extras_diretos = round2(laudo_direto["valor"] + kit_gnss["valor"] + alinhamento_cerca["valor"])
    total = round2(core + extras_diretos)

    # Guard de fechamento
    guard_core = minimo if aplicou_minimo else round2(base_desconto - desconto_valor)
    guard_total = round2(guard_core + extras_diretos)
    if round2(total) != round2(guard_total):
        raise ValueError(f"Guard fechamento: esperado {guard_total}, obtido {total}")

    # ── Opcionais (croqui, acompanhamento, jurídica — não somam) ─────────────
    linhas_opcionais = _montar_linhas_opcionais(opcionais_raw, cfg["opcionais"])
    subtotal_opcionais = round2(sum(
        l["valor"] for l in linhas_opcionais if l["contratado"] and isinstance(l["valor"], (int, float))
    ))

    # ── Parcelas (3x default ou 2x) ──────────────────────────────────────────
    num_parcelas = 2 if _num(dados.get("num_parcelas"), 3) == 2 else 3
    parcelas_cfg = cfg["parcelas_2x"] if num_parcelas == 2 else cfg["parcelas"]
    parcelas_out = []
    n = len(parcelas_cfg)
    for i, p in enumerate(parcelas_cfg):
        if i == n - 1:
            soma_ant = sum(round2((total * x["percentual"]) / 100) for x in parcelas_cfg[:-1])
            valor = round2(total - soma_ant)
        else:
            valor = round2((total * p["percentual"]) / 100)
        parcelas_out.append({"numero": i + 1, "rotulo": p["rotulo"], "valor": valor, "percentual": p["percentual"]})

    soma_parcelas = round2(sum(p["valor"] for p in parcelas_out))
    if abs(soma_parcelas - total) > 0.01:
        raise ValueError(f"Erro fechamento parcelas: soma={soma_parcelas} total={total}")

    validade_dias = int(_num(dados.get("validade_dias"), 0)) if _num(dados.get("validade_dias"), 0) > 0 else cfg["validade_dias_default"]

    honorarios_romatec_demarcacao = {
        "trt_cft": trt_cft, "tecnicos_campo": tecnicos_campo, "adicional_campo": adicional_campo,
        "marcos_discriminados": marcos_discriminados, "marcos_subtotal": marcos_subtotal,
        "deslocamento": deslocamento, "area_servico": area_servico,
        "complexidade_multiplicador": complexidade_multiplicador,
        "subtotal_apos_complexidade": subtotal_apos_complexidade, "assessoria": assessoria,
        "desconto_valor": desconto_valor, "laudo_tecnico_direto": laudo_direto,
        "locacao_kit_gnss": kit_gnss, "alinhamento_cerca": alinhamento_cerca, "total": total,
    }

    # ── Adapter → custos (espelha adaptarDemarcacaoParaCustosCalculados) ─────
    secao_3_honorarios = [
        {"ordem": 1, "descricao": "TRT/CFT — Termo de Responsabilidade Tecnica", "valor": trt_cft},
        {"ordem": 2, "descricao": "Tecnicos de campo + Marcos + Deslocamento + Area (com complexidade e assessoria)",
         "valor": round2(total - trt_cft + desconto_valor)},
    ]
    if desconto_valor > 0:
        secao_3_honorarios.append({"ordem": 3, "descricao": "Desconto aplicado", "valor": -desconto_valor})

    condicoes_pagamento = [
        {"rotulo": f"{p['numero']}a parcela — {p['rotulo']}", "descricao": f"{p['percentual']}% do total", "valor": p["valor"]}
        for p in parcelas_out
    ]

    avisos = [
        "BASE LEGAL: Lei 10.267/2001 (CNIR) e NTGIR 3a Edicao (INCRA) — codificacao dos marcos com "
        "credencial do tecnico. Demarcacao urbana: Lei 6.766/79; rural: Lei 5.868/72.",
        "Os marcos sao codificados conforme a credencial CFT/MA do responsavel tecnico no momento do envio ao INCRA.",
    ]
    if adicional_campo["aplicavel"]:
        avisos.append(
            f"ADICIONAL DE CAMPO ({adicional_campo['pct']}%): incide sobre os honorarios de tecnicos de campo "
            "antes da complexidade (CLT art. 192/193 + NR-15/NR-16). Valor: "
            f"R$ {adicional_campo['valor']:.2f}."
        )

    custos = {
        "secao_1_projetos": list(ESCOPO_DEMARCACAO),
        "secao_2_taxas": [],
        "secao_3_honorarios": secao_3_honorarios,
        "condicoes_pagamento": condicoes_pagamento,
        "secao_4_checklist": [],
        "secao_5_total": total,
        "avisos": avisos,
        "honorarios_romatec": {
            "trt": trt_cft,
            "tecnicos": round2(tecnicos_campo + marcos_subtotal + deslocamento + area_servico),
            "assessoria": assessoria, "total": total,
        },
        "honorarios_romatec_demarcacao": honorarios_romatec_demarcacao,
        "secao_opcionais_demarcacao": {"linhas": linhas_opcionais, "subtotal": subtotal_opcionais},
        "salario_minimo_usado": SM, "validade_dias": validade_dias,
    }

    return {"custos": custos, "fontes": {}}


def _montar_linhas_opcionais(opcionais: dict, cfg_opc: dict) -> list:
    """3 linhas (v3.63.5: alinhamento e laudo viraram itens diretos): croqui, acompanhamento, jurídica (sob_orcamento)."""
    linhas = []
    # Croqui assinado
    it = opcionais.get("croqui_assinado") or {}
    contratado = bool(it.get("contratado"))
    v_unit = _num(it.get("valor_unitario"), cfg_opc["croqui_assinado"]["valor_unitario"]) \
        if it.get("valor_unitario") is not None else cfg_opc["croqui_assinado"]["valor_unitario"]
    linhas.append({"rotulo": cfg_opc["croqui_assinado"]["rotulo"], "contratado": contratado,
                   "valor": round2(v_unit) if contratado else 0})
    # Acompanhamento de obra
    it = opcionais.get("acompanhamento_obra") or {}
    contratado = bool(it.get("contratado"))
    diarias = _num(it.get("diarias"), 0)
    v_unit = _num(it.get("valor_unitario"), cfg_opc["acompanhamento_obra"]["valor_unitario"]) \
        if it.get("valor_unitario") is not None else cfg_opc["acompanhamento_obra"]["valor_unitario"]
    linhas.append({"rotulo": cfg_opc["acompanhamento_obra"]["rotulo"], "contratado": contratado,
                   "valor": round2(diarias * v_unit) if contratado else 0})
    # Consultoria jurídica (literal 'sob_orcamento')
    it = opcionais.get("consultoria_juridica") or {}
    contratado = bool(it.get("contratado"))
    linhas.append({"rotulo": cfg_opc["consultoria_juridica"]["rotulo"], "contratado": contratado, "valor": "sob_orcamento"})
    return linhas
