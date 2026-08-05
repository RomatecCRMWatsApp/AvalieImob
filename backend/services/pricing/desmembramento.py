# @module services.pricing.desmembramento — Engine de Desmembramento e Remembramento.
# Port FIEL de pricing/desmembramento.ts (ZAYRA). Cobre os modos:
#   auto (paramétrico SM × fator × nº lotes + assessoria 1 SM),
#   manual (lista de mapas OU frações + assessoria jurídica),
#   modo_precificacao (por_imovel / por_lote / personalizado),
#   assessoria_tecnica e despesas_administrativas (toggle),
#   derivação a partir de imoveis[]/fracoes[] e validação status_documentacao (30 dias).
# secao_5_total = secao_2 (ART + emolumentos + prefeitura) + secao_3 (honorários).
# Base legal: Lei 6.766/1979 (urbano), Lei 4.504/1964 (rural), Lei 6.015/1973, CC 1.297/1.298.
from __future__ import annotations

import re
from datetime import datetime, timezone

from services.pricing.params import (
    HONORARIOS_ASSESSORIA, PREFEITURA_ACAILANDIA,
    salario_minimo, anotacao_tecnica,
)
from services.pricing.tjma import calcular_emolumentos

ESCOPO_DESMEMBRAMENTO = [
    "Levantamento topografico do imovel matriz",
    "Projeto urbanistico do desmembramento (memorial + planta de cada lote resultante)",
    "Memoriais descritivos individualizados (um por lote)",
    "Coordenadas de cada vertice da poligonal de cada lote",
    "Submissao do projeto a Prefeitura para aprovacao (zoneamento, infraestrutura, lotes minimos)",
    "Acompanhamento da analise municipal ate o despacho aprovatorio",
    "Protocolo no cartorio competente para cancelamento da matricula matriz e abertura das novas matriculas",
    "Acompanhamento ate emissao das novas matriculas individualizadas",
]

ESCOPO_REMEMBRAMENTO = [
    "Levantamento topografico das matriculas a serem unificadas",
    "Memorial descritivo unificado (poligonal resultante)",
    "Planta georreferenciada da nova area unificada",
    "Verificacao de divisas e confrontantes da area resultante",
    "Protocolo em cartorio para cancelamento das matriculas origem",
    "Abertura da nova matricula unica unificada",
    "Acompanhamento ate registro final",
]


def _num(v, default=0.0):
    try:
        return float(v) if v is not None else float(default)
    except (TypeError, ValueError):
        return float(default)


def _fmt_area(area: float, unidade: str) -> str:
    dec = 4 if unidade == "ha" else 2
    s = f"{float(area):,.{dec}f}"  # 1,234.5600 (en)
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # → pt-BR
    return s


def _pad2(n) -> str:
    return str(n).zfill(2)


def calcular_desmembramento(dados: dict) -> dict:
    """Recebe InputDesmembramento (dict) e retorna {custos, fontes} idêntico à ZAYRA."""
    sm = salario_minimo()
    tipo = dados.get("tipo", "remembramento")
    is_desm = tipo == "desmembramento"
    tipo_zona = dados.get("tipo_zona", "urbana")

    imoveis = dados.get("imoveis") or []
    fracoes = dados.get("fracoes") or []
    mapas = dados.get("mapas") or []

    area_total_m2 = _num(dados.get("area_total_m2"), 0)
    valor_venal_total = _num(dados.get("valor_venal_total"), 0)
    numero_lotes_resultantes = dados.get("numero_lotes_resultantes")
    numero_lotes_origem = dados.get("numero_lotes_origem")
    honorario_projeto_sm = _num(dados.get("honorario_projeto_sm"), 1.0)

    # ── Normalização a partir de imoveis[] (modo detalhado do remembramento) ──
    if imoveis:
        if len(imoveis) < 2:
            raise ValueError("Lista de imóveis exige pelo menos 2 entradas (remembramento une 2 ou mais matrículas)")
        for i in imoveis:
            if not (_num(i.get("area_m2"), 0) > 0):
                raise ValueError(f"Imóvel #{i.get('ordem')}: área deve ser > 0")
            if not str(i.get("endereco") or "").strip():
                raise ValueError(f"Imóvel #{i.get('ordem')}: endereço obrigatório")
            if not str(i.get("matricula") or "").strip():
                raise ValueError(f"Imóvel #{i.get('ordem')}: matrícula obrigatória")
            if i.get("livro") is not None and not str(i.get("livro")).strip():
                raise ValueError(f"Imóvel #{i.get('ordem')}: livro não pode ser vazio")
            if i.get("folha") is not None and not str(i.get("folha")).strip():
                raise ValueError(f"Imóvel #{i.get('ordem')}: folha não pode ser vazia")
            if i.get("cri_cns") and not re.match(r"^\d{2}\.\d{3}-\d$", str(i.get("cri_cns"))):
                raise ValueError(f"Imóvel #{i.get('ordem')}: cri_cns deve seguir formato XX.XXX-X")
        area_soma = sum(_num(i.get("area_m2"), 0) for i in imoveis)
        if not area_total_m2 or area_total_m2 <= 0:
            area_total_m2 = area_soma
        if not is_desm and (not numero_lotes_origem or numero_lotes_origem < 2):
            numero_lotes_origem = len(imoveis)

    # ── Validação status_documentacao (regra dos 30 dias) ────────────────────
    sd = dados.get("status_documentacao")
    if sd:
        if not sd.get("cnd_iptu_anexada"):
            raise ValueError("CND de IPTU é obrigatória (anexar antes de submeter)")
        if not sd.get("bci_anexado"):
            raise ValueError("BCI do imóvel é obrigatório (anexar antes de submeter)")
        data_cert = sd.get("certidao_inteiro_teor_data")
        if not data_cert:
            raise ValueError("Data de emissão da certidão de inteiro teor é obrigatória")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(data_cert)):
            raise ValueError("certidao_inteiro_teor_data inválida (use ISO YYYY-MM-DD)")
        try:
            emissao = datetime.strptime(str(data_cert), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError("certidao_inteiro_teor_data inválida (use ISO YYYY-MM-DD)")
        diff_dias = (datetime.now(timezone.utc) - emissao).total_seconds() / 86400
        if diff_dias > 30:
            raise ValueError(
                f"Certidão de inteiro teor vencida ({int(diff_dias)} dias desde a emissão; "
                f"validade máxima: 30 dias)"
            )
        if diff_dias < -1:
            raise ValueError("certidao_inteiro_teor_data não pode ser futura (tolerância de ±1 dia para skew de relógio)")

    # ── Validação peças técnicas (ART ∨ TRT) ─────────────────────────────────
    pt = dados.get("pecas_tecnicas")
    if pt and not pt.get("art") and not pt.get("trt"):
        raise ValueError("Peça técnica: pelo menos ART (CREA) ou TRT (CFT) deve estar marcado")

    # ── Validação modalidade/unidade_area ────────────────────────────────────
    modalidade = dados.get("modalidade")
    unidade_area = dados.get("unidade_area")
    if modalidade:
        unit_derived = "ha" if modalidade == "rural" else "m2"
        if unidade_area and unidade_area != unit_derived:
            raise ValueError(
                f"Modalidade '{modalidade}' exige unidade '{unit_derived}', mas recebeu '{unidade_area}'"
            )

    # ── Validação de frações ─────────────────────────────────────────────────
    if fracoes:
        if len(fracoes) < 2:
            raise ValueError("Mínimo de 2 frações (desmembramento/desdobro divide em pelo menos 2 partes)")
        for f in fracoes:
            if not (_num(f.get("area"), 0) > 0):
                raise ValueError(f"Fração {f.get('numero')}: área deve ser > 0")
            if not (_num(f.get("valor"), 0) > 0):
                raise ValueError(f"Fração {f.get('numero')}: valor deve ser > 0")
        soma_areas = sum(_num(f.get("area"), 0) for f in fracoes)
        unidade = unidade_area or ("ha" if modalidade == "rural" else "m2")
        tolerancia = 0.01 if unidade == "ha" else 1
        if area_total_m2 and area_total_m2 > 0 and soma_areas > area_total_m2 + tolerancia:
            raise ValueError(
                f"Soma das frações ({soma_areas:.4f}) excede a área da matriz ({area_total_m2}) em {unidade}"
            )
        if is_desm and (not numero_lotes_resultantes or numero_lotes_resultantes < 2):
            numero_lotes_resultantes = len(fracoes)

    # ── Validações finais ────────────────────────────────────────────────────
    if not (area_total_m2 > 0):
        raise ValueError("area_total_m2 deve ser > 0")
    if valor_venal_total < 0:
        raise ValueError("valor_venal_total invalido")
    if is_desm and (not numero_lotes_resultantes or numero_lotes_resultantes < 2):
        raise ValueError("Desmembramento exige numero_lotes_resultantes >= 2")
    if not is_desm and (not numero_lotes_origem or numero_lotes_origem < 2):
        raise ValueError("Remembramento exige numero_lotes_origem >= 2")

    numero_matriculas_afetadas = (
        (numero_lotes_resultantes or 0) + 1 if is_desm else (numero_lotes_origem or 0) + 1
    )

    # ── Seção 1: escopo ──────────────────────────────────────────────────────
    secao_1_projetos = list(ESCOPO_DESMEMBRAMENTO if is_desm else ESCOPO_REMEMBRAMENTO)

    # ── Seção 2: taxas e emolumentos de terceiros ───────────────────────────
    secao_2_taxas = []
    fontes: dict = {}
    ordem = 1

    at = anotacao_tecnica("art_crea")
    secao_2_taxas.append({"ordem": ordem, "descricao": at["rotulo"], "valor": at["valor"], "observacao": at["fonte"]})
    ordem += 1

    try:
        valor_por_matricula = max(valor_venal_total / numero_matriculas_afetadas, 30000)
        emol = calcular_emolumentos("averbacao_construcao", valor_por_matricula)
        total_emol = emol["valor"] * numero_matriculas_afetadas
        secao_2_taxas.append({
            "ordem": ordem,
            "descricao": f"Emolumentos cartorarios — {numero_matriculas_afetadas} matricula(s) afetada(s)"
                         + (" (cancelamento da matriz + abertura das novas)" if is_desm
                            else " (cancelamento das origem + abertura da unificada)"),
            "valor": total_emol,
            "observacao": f"R$ {emol['valor']:.2f} × {numero_matriculas_afetadas} matriculas | {emol.get('base_calculo','')}",
        })
        ordem += 1
        fontes["tjma"] = {"fonte": emol.get("fonte"), "consultadoEm": emol.get("consultadoEm")}
    except Exception as err:  # pragma: no cover
        secao_2_taxas.append({
            "ordem": ordem, "descricao": "Emolumentos cartorarios (cancelamento e abertura de matriculas)",
            "valor": 0, "pendente": True, "observacao": f"A confirmar em cartorio. {err}",
        })
        ordem += 1

    if is_desm and tipo_zona == "urbana":
        taxa_pref = PREFEITURA_ACAILANDIA.get("aprovacao_desmembramento")
        secao_2_taxas.append({
            "ordem": ordem,
            "descricao": "Taxa de Aprovacao do Desmembramento — Prefeitura de Acailandia",
            "valor": taxa_pref if taxa_pref is not None else 0,
            "pendente": taxa_pref is None,
            "observacao": (
                "A confirmar com a Secretaria de Obras/Planejamento da Prefeitura. Costuma ser "
                "proporcional ao numero de lotes ou area total."
                if taxa_pref is None else "Conforme taxa vigente em Acailandia/MA"
            ),
        })
        ordem += 1

    # ── Seção 3: honorários Romatec ─────────────────────────────────────────
    is_manual = dados.get("modo_calculo") == "manual"
    fator_sm = honorario_projeto_sm
    numero_lotes = (numero_lotes_resultantes or 0) if is_desm else (numero_lotes_origem or 0)
    honorario_projeto = sm * fator_sm * numero_lotes
    honorario_assessoria = sm * HONORARIOS_ASSESSORIA["padrao_sm"]
    obs_hon_projeto = (
        f"{fator_sm} SM × {numero_lotes} lote(s) {'resultante(s)' if is_desm else 'origem'} = "
        f"R$ {honorario_projeto:.2f} (1 SM = R$ {sm:.2f})"
    )

    secao_3_honorarios = []

    if is_manual:
        has_mapas = bool(mapas)
        has_fracoes = bool(fracoes)
        if not has_mapas and not has_fracoes:
            raise ValueError("Modo manual exige pelo menos 1 mapa (remembramento) OU 1 fração (desmembramento/desdobro)")
        if has_mapas:
            for m in mapas:
                if not (_num(m.get("valor"), 0) > 0):
                    raise ValueError(f"Mapa {m.get('numero')}: valor deve ser > 0")
            for m in mapas:
                desc = (f"Mapa {_pad2(m.get('numero'))} — {m['descricao']}"
                        if m.get("descricao") else f"Mapa {_pad2(m.get('numero'))}")
                secao_3_honorarios.append({"ordem": ordem, "descricao": desc, "valor": _num(m.get("valor"), 0)})
                ordem += 1
        else:
            unidade = unidade_area or ("ha" if modalidade == "rural" else "m2")
            unidade_label = "ha" if unidade == "ha" else "m²"
            for f in fracoes:
                desc = (f"Fração {_pad2(f.get('numero'))} — {_fmt_area(_num(f.get('area'),0), unidade)} {unidade_label}"
                        + (" · " + f["descricao"] if f.get("descricao") else ""))
                secao_3_honorarios.append({"ordem": ordem, "descricao": desc, "valor": _num(f.get("valor"), 0)})
                ordem += 1
        aj = dados.get("assessoria_juridica")
        if aj and aj.get("incluir"):
            valor_ass = aj.get("valor")
            if not (_num(valor_ass, 0) > 0):
                raise ValueError("Assessoria Técnica Jurídica habilitada exige valor > 0")
            secao_3_honorarios.append({"ordem": ordem, "descricao": "Assessoria Técnica Jurídica", "valor": _num(valor_ass, 0)})
            ordem += 1
    else:
        secao_3_honorarios = [
            {
                "ordem": ordem,
                "descricao": (
                    "Honorarios de Projeto Urbanistico de Desmembramento — levantamento topografico, "
                    "projeto, memorial descritivo de cada lote, planta, ARTs e responsabilidade tecnica"
                    if is_desm else
                    "Honorarios de Projeto de Remembramento — levantamento topografico das matriculas, "
                    "memorial unificado, planta resultante, ARTs e responsabilidade tecnica"
                ),
                "valor": honorario_projeto, "observacao": obs_hon_projeto,
            },
            {
                "ordem": ordem + 1,
                "descricao": "Honorarios de Assessoria e Acompanhamento — diligencias na Prefeitura (se "
                             "aplicavel), protocolo em cartorio, acompanhamento ate emissao das matriculas finais",
                "valor": honorario_assessoria, "observacao": f"1 salario minimo 2026 (R$ {sm:.2f})",
            },
        ]
        ordem += 2

    # ── modo_precificacao reescreve secao_3 do zero ──────────────────────────
    # 'auto'/vazio = cálculo paramétrico padrão (não aciona modo). Conveniência UI:
    # deriva honorarios_personalizados de chaves planas do form genérico.
    modo_prec = dados.get("modo_precificacao")
    if modo_prec in (None, "", "auto"):
        modo_prec = None
    if modo_prec == "personalizado" and dados.get("honorarios_personalizados") is None:
        _vt = dados.get("honorarios_personalizados_valor")
        if _vt is None:
            _vt = dados.get("honorarios_personalizados_valor_total")
        dados["honorarios_personalizados"] = {
            "valor_total": _num(_vt, 0),
            "descritivo": dados.get("honorarios_personalizados_descritivo"),
        }
    if modo_prec:
        secao_3_honorarios = []
        ordem_hon = 1
        if modo_prec == "por_imovel":
            valor_unit = _num(dados.get("valor_por_imovel"), 0)
            if not (valor_unit > 0):
                raise ValueError("valor_por_imovel deve ser > 0 quando modo_precificacao=por_imovel")
            qtd = (len(imoveis) if imoveis else
                   (numero_lotes_resultantes if is_desm else numero_lotes_origem) or 0)
            if qtd < 2:
                raise ValueError("Modo por_imovel exige pelo menos 2 imóveis/lotes")
            secao_3_honorarios.append({
                "ordem": ordem_hon, "descricao": f"Honorários técnicos — {qtd} imóvel(eis) × R$ {valor_unit:.2f} por imóvel",
                "valor": valor_unit * qtd, "observacao": "Precificação por imóvel",
            })
        elif modo_prec == "por_lote":
            lista = dados.get("valores_por_lote") or []
            if not lista:
                raise ValueError("valores_por_lote vazio ou ausente quando modo_precificacao=por_lote")
            for item in lista:
                if not (_num(item.get("valor"), 0) > 0):
                    raise ValueError(f"valores_por_lote[{item.get('ordem')}]: valor deve ser > 0")
                desc = (f"Lote {_pad2(item.get('ordem'))} — {item['descricao']}"
                        if item.get("descricao") else f"Lote {_pad2(item.get('ordem'))}")
                secao_3_honorarios.append({"ordem": ordem_hon, "descricao": desc, "valor": _num(item.get("valor"), 0)})
                ordem_hon += 1
        elif modo_prec == "personalizado":
            hpers = dados.get("honorarios_personalizados")
            if not hpers or not (_num(hpers.get("valor_total"), 0) > 0):
                raise ValueError("honorarios_personalizados.valor_total deve ser > 0")
            if not str(hpers.get("descritivo") or "").strip():
                raise ValueError("honorarios_personalizados.descritivo é obrigatório")
            secao_3_honorarios.append({
                "ordem": ordem_hon, "descricao": "Honorários técnicos — pacote fechado",
                "valor": _num(hpers.get("valor_total"), 0), "observacao": hpers.get("descritivo"),
            })
        else:
            raise ValueError(f"modo_precificacao desconhecido: {modo_prec}")

    # ── Assessoria Técnica (toggle) ──────────────────────────────────────────
    at_tog = dados.get("assessoria_tecnica")
    if at_tog is None and dados.get("assessoria_tecnica_habilitada") is not None:
        at_tog = {"habilitada": bool(dados.get("assessoria_tecnica_habilitada")),
                  "valor": _num(dados.get("assessoria_tecnica_valor"), 0)}
    if at_tog and at_tog.get("habilitada"):
        valor_at = _num(at_tog.get("valor"), 0)
        if valor_at < 0:
            raise ValueError("assessoria_tecnica.valor inválido")
        secao_3_honorarios.append({
            "ordem": len(secao_3_honorarios) + 1, "descricao": "Assessoria Técnica", "valor": valor_at,
            "observacao": "Acompanhamento técnico junto ao cartório e prefeitura (contratação opcional)",
        })

    # ── Seção 4: checklist ───────────────────────────────────────────────────
    secao_4_checklist = [
        {"texto": (
            "Certidao de Inteiro Teor da Matricula MATRIZ — ATUALIZADA (max. 30 dias)" if is_desm else
            f"Certidoes de Inteiro Teor das {numero_lotes_origem or 'todas as'} matriculas a unificar — ATUALIZADAS (max. 30 dias)"
        ), "obrigatorio": True},
        {"texto": "IPTU em dia (todos os exercicios) — comprovantes", "obrigatorio": True, "imprescindivel": True},
        {"texto": "RG/CPF de todos os proprietarios (e conjuges, se for o caso)", "obrigatorio": True},
        {"texto": "Comprovante de residencia atualizado dos proprietarios", "obrigatorio": True},
        {"texto": "Anuencia de confrontantes (assinaturas dos vizinhos na planta da nova divisao)",
         "obrigatorio": True, "imprescindivel": is_desm},
    ]
    if is_desm:
        secao_4_checklist.append({"texto": "Certidao de zoneamento da Prefeitura (constando ZONA permitida pra parcelamento)", "obrigatorio": True})
        secao_4_checklist.append({"texto": "Certidao de viabilidade urbanistica (se exigido pelo municipio)", "obrigatorio": False})
    secao_4_checklist.append({"texto": "CCIR + ITR em dia (se imovel rural)", "obrigatorio": tipo_zona == "rural"})
    secao_4_checklist.append({"texto": "CAR (Cadastro Ambiental Rural) — se imovel rural", "obrigatorio": tipo_zona == "rural"})
    secao_4_checklist.append({"texto": "Eventuais onus, hipotecas ou usufrutos averbados (declaracao)", "obrigatorio": False})

    # ── Seção 5: total ───────────────────────────────────────────────────────
    total_taxas = sum(_num(i.get("valor"), 0) for i in secao_2_taxas)
    total_honorarios = sum(_num(i.get("valor"), 0) for i in secao_3_honorarios)
    secao_5_total = total_taxas + total_honorarios

    # ── Avisos legais ────────────────────────────────────────────────────────
    avisos = []
    if is_desm:
        avisos.append("BASE LEGAL DESMEMBRAMENTO: Lei 6.766/1979 (Parcelamento do Solo Urbano) — exige aprovacao "
                      "previa da Prefeitura, lotes minimos conforme zoneamento (geralmente 125m² em zona urbana de "
                      "Acailandia), e infraestrutura compativel. Cada lote resultante vira matricula propria no cartorio.")
        avisos.append("PRAZO ESTIMADO: levantamento (5-10 dias), projeto e memoriais (5-10 dias), analise Prefeitura "
                      "(30-90 dias), protocolo cartorio (15-30 dias). Total tipico: 60-150 dias.")
    else:
        avisos.append("BASE LEGAL REMEMBRAMENTO: Lei 6.015/1973 (Registros Publicos) art. 234 — unificacao de "
                      "matriculas contiguas pertencentes ao mesmo proprietario. Mais simples que desmembramento, "
                      "geralmente sem analise municipal.")
        avisos.append("IMPORTANTE: as matriculas a unificar devem (1) ser CONTIGUAS, (2) pertencer ao MESMO "
                      "proprietario, (3) estar livres de onus reais ou ter anuencia dos credores. Verificacao previa obrigatoria.")
        avisos.append("PRAZO ESTIMADO: levantamento (3-7 dias), memorial unificado (3-5 dias), protocolo cartorio "
                      "(15-30 dias). Total tipico: 30-60 dias.")

    if not dados.get("iptu_em_dia"):
        avisos.append("ATENCAO IPTU: o IPTU em dia e PRE-REQUISITO ABSOLUTO. Sem comprovacao de quitacao do exercicio "
                      "atual e dos 5 anteriores, a Prefeitura e o cartorio recusam a operacao. Regularize antes do protocolo.")

    avisos.append("IMPORTANTE: Os valores das taxas de Cartorio e Prefeitura sao APROXIMADOS, baseados em estimativas. "
                  "Os valores definitivos podem variar conforme apuracao no momento do protocolo.")

    if tipo_zona == "urbana":
        avisos.append("SENHA GOV.BR: o sistema da Receita Federal pode exigir consultas tributarias durante o tramite. "
                      "A Romatec orienta o cliente a manter conta gov.br nivel prata/ouro ativa pra eventual emissao "
                      "de certidoes negativas.")

    itens_pendentes = [i["descricao"] for i in secao_2_taxas if i.get("pendente")]
    if itens_pendentes:
        avisos.append(f"Itens pendentes de confirmacao: {', '.join(itens_pendentes)}.")
        fontes["prefeitura"] = {"itens_pendentes": itens_pendentes}

    # ── Condições de pagamento ───────────────────────────────────────────────
    total_secao3 = sum(_num(i.get("valor"), 0) for i in secao_3_honorarios)
    if is_manual or modo_prec == "personalizado":
        condicoes_pagamento = [{
            "rotulo": "A combinar entre as partes",
            "descricao": "Forma e cronograma de pagamento dos honorários a serem definidos em comum acordo entre "
                         "Contratante e Contratado, registrados em recibo próprio.",
            "valor": total_secao3,
        }]
    elif modo_prec in ("por_imovel", "por_lote"):
        condicoes_pagamento = [
            {"rotulo": "1a parcela — na assinatura da proposta", "descricao": "50% dos Honorários técnicos", "valor": total_secao3 * 0.5},
            {"rotulo": "2a parcela — no protocolo final em cartório", "descricao": "50% restante dos Honorários técnicos", "valor": total_secao3 * 0.5},
        ]
    elif is_desm:
        condicoes_pagamento = [
            {"rotulo": "1a parcela — na assinatura da proposta",
             "descricao": "50% dos Honorarios de Projeto + 50% dos Honorarios de Assessoria",
             "valor": honorario_projeto * 0.5 + honorario_assessoria * 0.5},
            {"rotulo": "2a parcela — na aprovacao do desmembramento pela Prefeitura",
             "descricao": "50% restante dos Honorarios de Projeto", "valor": honorario_projeto * 0.5},
            {"rotulo": "3a parcela — no protocolo final em cartorio",
             "descricao": "50% restante dos Honorarios de Assessoria", "valor": honorario_assessoria * 0.5},
        ]
    else:
        condicoes_pagamento = [
            {"rotulo": "1a parcela — na assinatura da proposta",
             "descricao": "100% dos Honorarios de Projeto + 50% dos Honorarios de Assessoria",
             "valor": honorario_projeto + honorario_assessoria * 0.5},
            {"rotulo": "2a parcela — no protocolo em cartorio",
             "descricao": "50% restante dos Honorarios de Assessoria", "valor": honorario_assessoria * 0.5},
        ]

    # ── Base de cálculo ──────────────────────────────────────────────────────
    linha_assessoria_tecnica = []
    if at_tog and at_tog.get("habilitada"):
        linha_assessoria_tecnica = [{"rotulo": "Assessoria Técnica",
                                     "formula": "Honorário definido pelo Contratado (opcional)",
                                     "valor_resultado": _num(at_tog.get("valor"), 0)}]

    if modo_prec:
        itens_modo = [
            {"rotulo": i["descricao"], "formula": i.get("observacao") or "Honorário definido pelo Contratado",
             "valor_resultado": i["valor"]}
            for i in secao_3_honorarios if not re.match(r"^Assessoria T[eé]cnica", i["descricao"])
        ]
        base_calculo = itens_modo + linha_assessoria_tecnica + [{
            "rotulo": "Total Romatec",
            "formula": ("Valor por imóvel × quantidade" if modo_prec == "por_imovel"
                        else "Soma dos lotes" if modo_prec == "por_lote" else "Pacote fechado"),
            "valor_resultado": total_secao3,
        }]
    elif is_manual:
        if fracoes:
            itens_manual = [{"rotulo": f"Fração {_pad2(f.get('numero'))}" + (" — " + f["descricao"] if f.get("descricao") else ""),
                             "formula": "Honorário definido pelo Contratado", "valor_resultado": _num(f.get("valor"), 0)}
                            for f in fracoes]
        else:
            itens_manual = [{"rotulo": f"Mapa {_pad2(m.get('numero'))}" + (" — " + m["descricao"] if m.get("descricao") else ""),
                             "formula": "Honorário definido pelo Contratado", "valor_resultado": _num(m.get("valor"), 0)}
                            for m in mapas]
        aj = dados.get("assessoria_juridica")
        aj_linha = ([{"rotulo": "Assessoria Técnica Jurídica", "formula": "Honorário definido pelo Contratado",
                      "valor_resultado": _num(aj.get("valor"), 0)}]
                    if aj and aj.get("incluir") and aj.get("valor") else [])
        base_calculo = itens_manual + aj_linha + linha_assessoria_tecnica + [{
            "rotulo": "Total Romatec",
            "formula": ("Soma das Frações" if fracoes else "Soma dos Mapas")
                       + (" + Assessoria Jurídica" if aj and aj.get("incluir") else "")
                       + (" + Assessoria Técnica" if at_tog and at_tog.get("habilitada") else ""),
            "valor_resultado": total_secao3,
        }]
    else:
        base_calculo = [
            {"rotulo": "Honorarios de Projeto",
             "formula": f"{fator_sm} SM × {numero_lotes} {'lote(s) resultante(s)' if is_desm else 'matricula(s) origem'} × R$ {sm:.2f}",
             "valor_resultado": honorario_projeto},
            {"rotulo": "Honorarios de Assessoria", "formula": f"1 SM × R$ {sm:.2f}", "valor_resultado": honorario_assessoria},
        ] + linha_assessoria_tecnica + [{
            "rotulo": "Total Romatec",
            "formula": "Projeto + Assessoria" + (" + Assessoria Técnica" if at_tog and at_tog.get("habilitada") else ""),
            "valor_resultado": total_secao3,
        }]

    # ── Despesas administrativas (seção separada, NÃO soma ao total) ─────────
    despesas_adm = None
    da = dados.get("despesas_administrativas")
    if da is None and dados.get("despesas_administrativas_habilitada") is not None:
        da = {"habilitada": bool(dados.get("despesas_administrativas_habilitada")),
              "valor": _num(dados.get("despesas_administrativas_valor"), 0),
              "descritivo": dados.get("despesas_administrativas_descritivo")}
    if da and da.get("habilitada"):
        valor = _num(da.get("valor"), 0)
        descritivo = str(da.get("descritivo") or "").strip() or "Despesas administrativas (cartório/prefeitura) — a cargo do cliente"
        if valor < 0:
            valor = 0
        despesas_adm = {"valor": valor, "descritivo": descritivo}

    custos = {
        "secao_1_projetos": secao_1_projetos,
        "secao_2_taxas": secao_2_taxas,
        "secao_3_honorarios": secao_3_honorarios,
        "condicoes_pagamento": condicoes_pagamento,
        "base_calculo": base_calculo,
        "secao_4_checklist": secao_4_checklist,
        "secao_5_total": secao_5_total,
        "avisos": avisos,
    }
    if despesas_adm:
        custos["despesas_administrativas"] = despesas_adm

    return {"custos": custos, "fontes": fontes}
