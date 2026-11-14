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

from datetime import date

from services.pricing.params import (
    HONORARIOS_PROJETO, HONORARIOS_ASSESSORIA, CUB_MA,
    salario_minimo, anotacao_tecnica,
)
from services.pricing.tjma import calcular_emolumentos
from services.pricing.params import cub_por_padrao
from services.inss_obra import ErroSimulacao, simular as simular_inss
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

    inss = _inss_da_obra(dados, modalidade, area_construida, padrao, responsavel)
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
        "secao_4_checklist": secao_4_checklist,
        "secao_5_total": round(secao_5_total, 2),
        "avisos": avisos,
    }
    return {"custos": custos, "fontes": fontes}


# ── INSS da obra (motor do módulo INSS de Obra) ─────────────────────────────
_DEST_POR_MODALIDADE = {"residencial": "residencial_unifamiliar", "comercial": "comercial_salas_lojas"}


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _br(v) -> str:
    s = f"{float(v):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _m2(v) -> str:
    return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v) -> str:
    return (f"{float(v) * 100:.2f}".rstrip("0").rstrip(".")).replace(".", ",") + "%"


def _base_calculo(res: dict) -> list:
    """Memória de cálculo do motor no formato {rotulo, formula, valor_resultado} da proposta."""
    out = []
    for l in res["linhas"]:
        nome = (l.get("descricao") or "").strip() or {
            "principal": "Área principal", "complementar_coberta": "Área complementar coberta",
            "complementar_descoberta": "Área complementar descoberta"}[l["classe"]]
        out.append({
            "rotulo": f"Custo da obra — {nome}",
            "formula": (f"{_m2(l['area_m2'])} m² × {_pct(l['reducao_area'])} = "
                        f"{_m2(l['area_calculo'])} m² × VAU {_br(l['vau'])}/m²"),
            "valor_resultado": float(l["cod"]),
        })
        fatores = f"{_pct(l['pct_mao_de_obra'])} mão de obra"
        pc = float(l["pct_categoria"]) * float(l["pct_destinacao"])
        if pc != 1:
            fatores += f" × {_pct(pc)} categoria/destinação"
        if float(l["fator_social"]) != 1:
            fatores += f" × {_pct(l['fator_social'])} fator social"
        out.append({"rotulo": f"RMT — {nome}", "formula": f"{_br(l['cod'])} × {fatores}",
                    "valor_resultado": float(l["rmt"])})
    dec = res["decadencia"]
    if dec["meses_decadentes"]:
        out.append({"rotulo": "RMT não decadente",
                    "formula": (f"{_br(res['rmt_total'])} × {dec['meses_nao_decadentes']}/{dec['meses_total']} "
                                f"meses não decadentes"),
                    "valor_resultado": float(res["rmt_nao_decadente"])})
    if res["usinado"]["aplicado"] and float(res["usinado"]["credito"]) > 0:
        out.append({"rotulo": "(−) Crédito concreto/argamassa usinada", "formula": "COD × % UF × 5%",
                    "valor_resultado": float(res["usinado"]["credito"])})
    for d in res["debitos"]:
        out.append({"rotulo": f"{d.get('codigo_receita') or d['codigo']} — {d['nome']}",
                    "formula": f"{_br(res['base_calculo'])} × {_pct(d['aliquota'])}",
                    "valor_resultado": float(d["valor"])})
    out.append({"rotulo": "TOTAL INSS DA OBRA (SERO)", "formula": "36,8% sobre a RMT não decadente",
                "valor_resultado": float(res["total"])})
    return out


def _inss_da_obra(dados: dict, modalidade: str, area_construida: float, padrao: str,
                  responsavel: str) -> dict:
    fonte = "Manual do SERO v3.0 (08/2024) — IN RFB 2.021/2021"
    aviso_base = ("INSS DA OBRA: valor ESTIMADO pela metodologia do Manual do SERO (afericao indireta). "
                  "O valor definitivo e o apurado no SERO/e-CAC na conclusao da afericao (DCTFWeb Afericao "
                  "de Obras).")

    # 1) Simulação vinculada do módulo INSS de Obra
    sim = dados.get("_inss_obra_sim")
    if isinstance(sim, dict) and sim.get("resultado"):
        res = sim["resultado"]
        num = sim.get("numero") or ""
        return {"total": float(res["total"]), "origem": "inss_obra", "fonte": fonte,
                "observacao": f"Conforme simulacao {num} do modulo INSS de Obra (memoria abaixo).",
                "aviso": aviso_base + f" Valor trazido da simulacao {num}.",
                "base_calculo": _base_calculo(res)}

    # PJ com contabilidade regular apura pela escrituração (Manual item 26.2)
    if responsavel == "PJ_com_contabilidade":
        return {"total": 0.0, "origem": "pj_contabilidade", "fonte": fonte,
                "observacao": ("Apurado via contabilidade regular da PJ (Manual do SERO item 26.2) — "
                               "nao se aplica afericao indireta."),
                "aviso": aviso_base, "base_calculo": []}

    if area_construida <= 0:
        return {"total": 0.0, "origem": "sem_area", "fonte": fonte,
                "observacao": "Informe a area construida para estimar o INSS da obra.",
                "aviso": aviso_base, "base_calculo": []}

    # 2) Simulação com os campos da proposta
    destinacao = dados.get("inss_destinacao") or _DEST_POR_MODALIDADE.get(modalidade, "residencial_unifamiliar")
    vau = _num(dados.get("vau_m2"))
    vau_estimado = vau <= 0
    if vau_estimado:
        vau = cub_por_padrao(padrao)
    areas = [{"descricao": "Area principal", "destinacao": destinacao,
              "categoria": dados.get("inss_categoria") or "obra_nova",
              "tipo": dados.get("inss_tipo") or "alvenaria", "classe": "principal",
              "area_m2": area_construida}]
    for classe, chave, rot in (("complementar_coberta", "area_complementar_coberta", "Area complementar coberta"),
                               ("complementar_descoberta", "area_complementar_descoberta",
                                "Area complementar descoberta")):
        a = _num(dados.get(chave))
        if a > 0:
            areas.append({**areas[0], "descricao": rot, "classe": classe, "area_m2": a})
    hoje = date.today().isoformat()
    entrada = {"responsavel": "PF" if responsavel == "PF" else "PJ", "uf": dados.get("uf") or "MA",
               "vau": {destinacao: vau}, "areas": areas, "usinado": bool(dados.get("usinado")),
               "data_inicio": dados.get("data_inicio_obra") or hoje,
               "data_fim": dados.get("data_fim_obra") or dados.get("data_inicio_obra") or hoje,
               "data_afericao": hoje}
    try:
        res = simular_inss(entrada)
    except ErroSimulacao as e:
        return {"total": 0.0, "origem": "erro", "fonte": fonte,
                "observacao": f"Nao foi possivel estimar o INSS: {e}", "aviso": aviso_base,
                "base_calculo": []}
    aviso = aviso_base
    if vau_estimado:
        aviso += (f" VAU ESTIMADO pelo CUB-MA do padrao {padrao} ({_br(vau)}/m²): informe o VAU "
                  f"do SERO (e-CAC > SERO > Consultar Tabela VAU) para um valor mais preciso.")
    obs = (f"RMT {_br(res['rmt_nao_decadente'])} × 36,8% — VAU {_br(vau)}/m² "
           f"({'estimado pelo CUB' if vau_estimado else 'informado do SERO'})")
    return {"total": float(res["total"]), "origem": "proposta", "fonte": fonte, "observacao": obs,
            "aviso": aviso, "base_calculo": _base_calculo(res), "vau": vau, "vau_estimado": vau_estimado}
