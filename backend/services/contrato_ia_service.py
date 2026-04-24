# @module services.contrato_ia_service — Roma_IA aplicada ao modulo de Contratos
"""Servico de inteligencia artificial para geracao e validacao de contratos imobiliarios.

Funcoes principais:
  - gerar_clausulas_contrato: gera clausulas juridicas conforme tipo e dados do contrato
  - gerar_clausulas_corretor: gera clausulas especificas de corretagem
  - validar_alertas_juridicos: valida o contrato e gera alertas de compliance
"""
import asyncio
import logging
import os
from typing import List, Dict, Any

from fastapi import HTTPException

logger = logging.getLogger("romatec")

# ── System prompt especifico para contratos ───────────────────────────────────
SYSTEM_PROMPT_CONTRATOS = (
    "Voce e a Roma_IA, especialista senior em contratos imobiliarios brasileiros, "
    "com dominio pleno do Codigo Civil (Lei 10.406/2002), Lei 8.245/91 (Locacoes), "
    "Lei 4.591/64 (Incorporacoes), Lei 9.514/97 (Alienacao Fiduciaria), "
    "Lei 6.766/79 (Parcelamento do Solo), Lei 13.786/2018 (Patrimonio de Afetacao), "
    "Codigo de Defesa do Consumidor (Lei 8.078/90) e normas do COFECI/CRECI.\n\n"
    "COMPETENCIA EM CONTRATOS:\n"
    "- Compra e Venda: art. 481-532 CC; transferencia de propriedade; ITBI; registro\n"
    "- Locacao Residencial/Comercial: Lei 8.245/91; reajuste IGPM/IPCA; despejo; sublocacao\n"
    "- Locacao por Temporada: art. 48-50 Lei 8.245/91; limite 90 dias; caucao\n"
    "- Corretagem: art. 722-729 CC; COFECI 957/2006; comissao; exclusividade; VGV\n"
    "- Permuta: art. 533 CC; torna; ITBI sobre diferenca\n"
    "- Comodato: art. 579-585 CC; uso gratuito; prazo; restituicao\n"
    "- Distrato: art. 472 CC; Lei 13.786/2018; restituicao de valores; penalidades\n"
    "- Hipoteca: art. 1.473-1.505 CC; registro; purga; arrematacao\n\n"
    "REGRAS DE GERACAO DE CLAUSULAS:\n"
    "1. Cada clausula deve ter numero romano (I, II, III...), titulo claro e corpo justificado\n"
    "2. Cite sempre o dispositivo legal pertinente\n"
    "3. Use linguagem tecnico-juridica formal, clara e precisa\n"
    "4. Inclua subclausulas numeradas (1.1, 1.2...) quando necessario\n"
    "5. Retorne SEMPRE em formato JSON valido, sem markdown, sem codigo-cerca\n\n"
    "Responda SEMPRE em portugues-BR, tom tecnico-juridico, objetivo e preciso."
)


# ── Helpers de chamada IA (reusa a cascata do routes/ai.py) ──────────────────

async def _call_groq(messages: list, max_tokens: int) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY nao configurada")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    resp = await asyncio.wait_for(
        client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            max_tokens=max_tokens,
        ),
        timeout=20,
    )
    return resp.choices[0].message.content or ""


async def _call_gemini(messages: list, max_tokens: int) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY nao configurada")
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=next((m["content"] for m in messages if m["role"] == "system"), None),
    )
    history_gemini = []
    for m in messages:
        if m["role"] == "system":
            continue
        role = "user" if m["role"] == "user" else "model"
        history_gemini.append({"role": role, "parts": [m["content"]]})
    if history_gemini and history_gemini[-1]["role"] == "user":
        last_prompt = history_gemini[-1]["parts"][0]
        chat_history = history_gemini[:-1]
    else:
        last_prompt = ""
        chat_history = history_gemini
    chat = model.start_chat(history=chat_history)
    resp = await asyncio.wait_for(
        asyncio.to_thread(
            chat.send_message,
            last_prompt,
            generation_config={"max_output_tokens": max_tokens},
        ),
        timeout=25,
    )
    return resp.text or ""


async def _call_claude(messages: list, max_tokens: int) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY nao configurada")
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=api_key)
    system_content = next((m["content"] for m in messages if m["role"] == "system"), None)
    non_system = [m for m in messages if m["role"] != "system"]
    resp = await asyncio.wait_for(
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system_content or "",
            messages=non_system,
        ),
        timeout=30,
    )
    return resp.content[0].text if resp.content else ""


async def _call_openai(messages: list, max_tokens: int) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY nao configurada")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)
    resp = await asyncio.wait_for(
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens,
        ),
        timeout=35,
    )
    return resp.choices[0].message.content or ""


_PROVIDERS = [
    ("groq", _call_groq),
    ("gemini", _call_gemini),
    ("claude", _call_claude),
    ("openai", _call_openai),
]


async def _roma_ia_cascata(messages: list, max_tokens: int = 3000) -> str:
    """Tenta provedores em ordem. Retorna texto da resposta."""
    last_error = None
    for name, fn in _PROVIDERS:
        try:
            reply = await fn(messages, max_tokens)
            if reply:
                logger.info("Roma_IA contratos respondeu via: %s", name)
                return reply
        except ValueError as e:
            logger.debug("Provedor %s ignorado: %s", name, e)
            last_error = e
        except asyncio.TimeoutError:
            logger.warning("Provedor %s timeout", name)
            last_error = asyncio.TimeoutError(f"{name} timeout")
        except Exception as e:
            logger.warning("Provedor %s falhou: %s", name, str(e)[:120])
            last_error = e
    raise HTTPException(
        status_code=503,
        detail=f"Nenhum provedor de IA disponivel. Ultimo erro: {str(last_error)[:200]}",
    )


def _parse_json_safe(text: str) -> Any:
    """Tenta parsear JSON da resposta da IA, removendo blocos markdown se presentes."""
    import json
    import re
    # Remove blocos ```json ... ``` se presentes
    cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    # Tenta parsear diretamente
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Tenta extrair primeiro objeto/array JSON do texto
        match = re.search(r"(\{[\s\S]+\}|\[[\s\S]+\])", cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return None


# ── FUNCAO 1: Gerar clausulas do contrato ────────────────────────────────────

async def gerar_clausulas_contrato(tipo: str, dados: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gera clausulas juridicas completas para o tipo de contrato informado.

    Args:
        tipo: Tipo do contrato (ex: "Compra e Venda de Imovel Urbano")
        dados: Dados do contrato (partes, objeto, condicoes_pagamento etc.)

    Returns:
        Lista de dicts com: numero, titulo, conteudo, tipo, base_legal
    """
    # Monta resumo de dados para o prompt
    partes_info = ""
    partes = dados.get("partes") or []
    for p in partes[:4]:
        qual = p.get("qualificacao", "Parte")
        if p.get("tipo") == "pf" and p.get("pf"):
            nome = p["pf"].get("nome", "")
            partes_info += f"- {qual}: {nome} (PF)\n"
        elif p.get("tipo") == "pj" and p.get("pj"):
            razao = p["pj"].get("razao_social", "")
            partes_info += f"- {qual}: {razao} (PJ)\n"

    objeto = dados.get("objeto") or {}
    objeto_info = (
        f"Endereco: {objeto.get('endereco', '')} {objeto.get('cidade', '')} {objeto.get('uf', '')}\n"
        f"Matricula: {objeto.get('matricula', '')}\n"
        f"Area terreno: {objeto.get('area_terreno', '')} m2 | Construida: {objeto.get('area_construida', '')} m2"
    )

    cond = dados.get("condicoes_pagamento") or {}
    valor = cond.get("valor_total", 0)
    valor_extenso = cond.get("valor_total_extenso", "")
    sinal = cond.get("sinal_valor", "")
    arras = cond.get("sinal_arras_tipo", "")
    multa = cond.get("multa_inadimplemento", "")
    juros = cond.get("juros_mora", "")

    prompt = (
        f"Gere as clausulas juridicas completas para um contrato do tipo: {tipo}\n\n"
        f"DADOS DAS PARTES:\n{partes_info}\n"
        f"OBJETO DO CONTRATO:\n{objeto_info}\n\n"
        f"CONDICOES FINANCEIRAS:\n"
        f"- Valor total: R$ {valor} ({valor_extenso})\n"
        f"- Sinal/Arras: R$ {sinal} ({arras})\n"
        f"- Multa por inadimplemento: {multa}%\n"
        f"- Juros de mora: {juros}% a.m.\n\n"
        "INSTRUCOES:\n"
        "1. Gere entre 8 e 15 clausulas completas\n"
        "2. Numere em romano (I, II, III...)\n"
        "3. Cada clausula deve ter: numero_romano, titulo, conteudo, tipo (padrao|especial|obrigatoria), base_legal\n"
        "4. Retorne APENAS um array JSON valido, sem texto antes ou depois\n"
        "5. Formato: [{\"numero_romano\": \"I\", \"titulo\": \"DO OBJETO\", \"conteudo\": \"...\", "
        "\"tipo\": \"obrigatoria\", \"base_legal\": \"art. 481 CC\"}]\n"
        "6. O conteudo deve ser completo, detalhado e juridicamente correto\n"
        "7. Inclua clausulas sobre: objeto, preco, pagamento, entrega, responsabilidades, "
        "penalidades, foro, disposicoes gerais"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CONTRATOS},
        {"role": "user", "content": prompt},
    ]

    reply = await _roma_ia_cascata(messages, max_tokens=4000)
    parsed = _parse_json_safe(reply)

    if not isinstance(parsed, list):
        logger.warning("gerar_clausulas_contrato: resposta nao e lista JSON valida")
        return []

    # Normaliza para o modelo Clausula
    clausulas = []
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            continue
        num_romano = item.get("numero_romano") or _to_roman(idx)
        clausulas.append({
            "numero": idx,
            "titulo": item.get("titulo") or f"CLAUSULA {num_romano}",
            "conteudo": item.get("conteudo") or "",
            "tipo": item.get("tipo") or "padrao",
            "base_legal": item.get("base_legal") or "",
            "_numero_romano": num_romano,
        })

    return clausulas


# ── FUNCAO 2: Gerar clausulas de corretagem ───────────────────────────────────

async def gerar_clausulas_corretor(corretor: Dict[str, Any], tipo_contrato: str) -> List[Dict[str, Any]]:
    """Gera clausulas especificas de corretagem e intermediacao imobiliaria.

    Args:
        corretor: Dados do corretor (nome, creci, comissao, exclusividade etc.)
        tipo_contrato: Tipo do contrato principal

    Returns:
        Lista de dicts com clausulas de corretagem
    """
    nome = corretor.get("nome", "")
    creci = corretor.get("creci", "")
    imobiliaria = corretor.get("imobiliaria", "")
    comissao_pct = corretor.get("comissao_percentual", "")
    comissao_val = corretor.get("comissao_valor", "")
    exclusividade = corretor.get("exclusividade", False)
    excl_prazo = corretor.get("exclusividade_prazo_dias", "")
    responsavel = corretor.get("comissao_responsavel", "")

    prompt = (
        f"Gere as clausulas de corretagem/intermediacao imobiliaria para o contrato de: {tipo_contrato}\n\n"
        f"DADOS DO CORRETOR/IMOBILIARIA:\n"
        f"- Nome: {nome}\n"
        f"- CRECI: {creci}\n"
        f"- Imobiliaria: {imobiliaria}\n"
        f"- Comissao: {comissao_pct}% (R$ {comissao_val})\n"
        f"- Responsavel pelo pagamento da comissao: {responsavel}\n"
        f"- Exclusividade: {'Sim, por ' + str(excl_prazo) + ' dias' if exclusividade else 'Nao'}\n\n"
        "INSTRUCOES:\n"
        "1. Gere entre 3 e 6 clausulas especificas de corretagem\n"
        "2. Inclua: identificacao do corretor/CRECI, valor da comissao, condicoes de pagamento, "
        "exclusividade (se houver), protecao do direito a comissao (art. 725 CC), "
        "responsabilidades do corretor, nullidade em caso de nao registro no CRECI\n"
        "3. Base legal: art. 722-729 CC; Resolucao COFECI 957/2006; Lei 6.530/78\n"
        "4. Retorne APENAS array JSON: [{\"numero_romano\": \"I\", \"titulo\": \"...\", "
        "\"conteudo\": \"...\", \"tipo\": \"especial\", \"base_legal\": \"...\"}]\n"
        "5. Sem texto antes ou depois do JSON"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CONTRATOS},
        {"role": "user", "content": prompt},
    ]

    reply = await _roma_ia_cascata(messages, max_tokens=2000)
    parsed = _parse_json_safe(reply)

    if not isinstance(parsed, list):
        logger.warning("gerar_clausulas_corretor: resposta nao e lista JSON valida")
        return []

    clausulas = []
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            continue
        clausulas.append({
            "numero": idx,
            "titulo": item.get("titulo") or f"DA CORRETAGEM {_to_roman(idx)}",
            "conteudo": item.get("conteudo") or "",
            "tipo": "especial",
            "base_legal": item.get("base_legal") or "art. 722-729 CC; Res. COFECI 957/2006",
            "_numero_romano": item.get("numero_romano") or _to_roman(idx),
        })

    return clausulas


# ── FUNCAO 2B: Gerar clausulas de exclusividade ───────────────────────────────

async def gerar_clausulas_exclusividade(dados: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gera clausulas especificas para contrato de exclusividade de venda.
    
    Args:
        dados: Dados do contrato de exclusividade (corretor, prazo, imovel, etc.)
        
    Returns:
        Lista de dicts com clausulas de exclusividade
    """
    corretor_nome = dados.get("corretor_nome", "")
    corretor_creci = dados.get("corretor_creci", "")
    prazo_dias = dados.get("prazo_dias", 90)
    data_inicio = dados.get("data_inicio", "")
    data_fim = dados.get("data_fim", "")
    comissao_pct = dados.get("comissao_percentual", 6)
    imovel_endereco = dados.get("imovel_endereco", "")
    proprietario_nome = dados.get("proprietario_nome", "")
    
    prompt = (
        f"Gere as clausulas completas para um CONTRATO DE EXCLUSIVIDADE DE VENDA imobiliaria.\n\n"
        f"DADOS DO CONTRATO:\n"
        f"- Corretor exclusivo: {corretor_nome} (CRECI: {corretor_creci})\n"
        f"- Proprietario: {proprietario_nome}\n"
        f"- Imovel: {imovel_endereco}\n"
        f"- Prazo de exclusividade: {prazo_dias} dias\n"
        f"- Periodo: {data_inicio} a {data_fim}\n"
        f"- Comissao: {comissao_pct}%\n\n"
        f"CLÁUSULAS OBRIGATÓRIAS (gerar no minimo 8 clausulas):\n"
        f"1. DO OBJETO - exclusividade de venda do imovel descrito\n"
        f"2. DA EXCLUSIVIDADE - apenas o corretor indicado pode vender; proibicao ao proprietario de vender diretamente ou por outro corretor\n"
        f"3. DO PRAZO - vigencia da exclusividade com data de inicio e termino\n"
        f"4. DA COMISSAO - percentual e valor; pagamento independentemente de quem trouxer o comprador (direito a comissao integral)\n"
        f"5. DAS OBRIGACOES DO CORRETOR - promocao, anuncios, visitas, negociacao\n"
        f"6. DAS OBRIGACOES DO PROPRIETARIO - nao vender diretamente, manter documentacao em dia, liberar acesso\n"
        f"7. DA PROTECAO AO CORRETOR - direito a comissao mesmo se venda direta pelo proprietario (Súmula 335 STJ); multa por venda direta\n"
        f"8. DA RESCISAO - condicoes de rescisao antecipada e penalidades\n"
        f"9. DA RENOVACAO - condicoes para renovacao automatica ou nao\n\n"
        f"BASE LEGAL PRINCIPAL:\n"
        f"- art. 725 CC (corretagem)\n"
        f"- Súmula 335 STJ (direito a comissao integral na exclusividade)\n"
        f"- Resolucao COFECI 957/2006\n"
        f"- Lei 6.530/78 (CRECI)\n\n"
        f"INSTRUCOES:\n"
        f"1. Retorne APENAS array JSON valido\n"
        f"2. Formato: [{{'numero_romano': 'I', 'titulo': '...', 'conteudo': '...', 'base_legal': '...'}}]\n"
        f"3. Linguagem juridica formal e precisa\n"
        f"4. Sem texto antes ou depois do JSON"
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CONTRATOS},
        {"role": "user", "content": prompt},
    ]
    
    reply = await _roma_ia_cascata(messages, max_tokens=2500)
    parsed = _parse_json_safe(reply)
    
    if not isinstance(parsed, list):
        logger.warning("gerar_clausulas_exclusividade: resposta nao e lista JSON valida")
        return []
    
    clausulas = []
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            continue
        clausulas.append({
            "numero": idx,
            "titulo": item.get("titulo") or f"CLÁUSULA {_to_roman(idx)}",
            "conteudo": item.get("conteudo") or "",
            "tipo": "especial",
            "base_legal": item.get("base_legal") or "art. 725 CC; Súmula 335 STJ",
            "_numero_romano": item.get("numero_romano") or _to_roman(idx),
        })
    
    return clausulas


# ── FUNCAO 3: Validar alertas juridicos ──────────────────────────────────────

async def validar_alertas_juridicos(contrato: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Valida o contrato e retorna lista de alertas juridicos e de compliance.

    Args:
        contrato: Dados completos do contrato

    Returns:
        Lista de dicts com alertas: nivel (info|aviso|critico), campo, mensagem, sugestao
    """
    tipo = contrato.get("tipo_contrato", "")
    partes = contrato.get("partes") or []
    objeto = contrato.get("objeto") or {}
    cond = contrato.get("condicoes_pagamento") or {}
    clausulas = contrato.get("clausulas") or []
    testemunhas = contrato.get("testemunhas") or []
    corretor = contrato.get("corretor")

    # Monta resumo para a IA
    resumo = (
        f"TIPO DE CONTRATO: {tipo}\n"
        f"PARTES: {len(partes)} parte(s) cadastrada(s)\n"
        f"OBJETO: endereco={objeto.get('endereco', '')}, matricula={objeto.get('matricula', '')}, "
        f"situacao={objeto.get('situacao', '')}, onus={objeto.get('onus', '')}\n"
        f"VALOR TOTAL: R$ {cond.get('valor_total', 0)}\n"
        f"VALOR EXTENSO: {cond.get('valor_total_extenso', 'nao informado')}\n"
        f"ARRAS/SINAL: R$ {cond.get('sinal_valor', 0)} ({cond.get('sinal_arras_tipo', 'nao informado')})\n"
        f"MULTA INADIMPLEMENTO: {cond.get('multa_inadimplemento', 'nao informada')}%\n"
        f"CLAUSULAS: {len(clausulas)} clausula(s)\n"
        f"TESTEMUNHAS: {len(testemunhas)} testemunha(s)\n"
        f"CORRETOR: {'sim, CRECI=' + (corretor.get('creci') or 'nao informado') if corretor else 'nao'}\n"
        f"STATUS: {contrato.get('status', 'rascunho')}\n"
    )

    # Verifica campos criticos diretamente (sem IA) para alertas basicos
    alertas_basicos = _verificar_alertas_basicos(tipo, partes, objeto, cond, clausulas, testemunhas)

    # Pede a IA para alertas juridicos avancados
    prompt = (
        f"Analise este contrato imobiliario e identifique alertas juridicos:\n\n{resumo}\n\n"
        "INSTRUCOES:\n"
        "1. Identifique entre 3 e 10 alertas juridicos importantes\n"
        "2. Classifique cada alerta como: critico, aviso ou info\n"
        "3. Niveis: critico=risco de nulidade/ilegalidade; aviso=protecao das partes; info=boas praticas\n"
        "4. Verifique: qualificacao completa das partes, matricula do imovel, valor por extenso, "
        "tipo de arras (confirmatoria x penitencial), multas dentro do limite legal, "
        "numero de clausulas, testemunhas necessarias, CRECI do corretor, "
        "prazo de vigencia, foro competente, clausula rescisoria\n"
        "5. Base legal: CC/2002, Lei 8.245/91, Lei 13.786/2018, CPC, CDC\n"
        "6. Retorne APENAS array JSON: [{\"nivel\": \"critico|aviso|info\", \"campo\": \"nome_do_campo\", "
        "\"mensagem\": \"descricao do problema\", \"sugestao\": \"como corrigir\"}]\n"
        "7. Sem texto antes ou depois do JSON"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CONTRATOS},
        {"role": "user", "content": prompt},
    ]

    try:
        reply = await _roma_ia_cascata(messages, max_tokens=2500)
        parsed = _parse_json_safe(reply)
        alertas_ia = parsed if isinstance(parsed, list) else []
    except Exception as e:
        logger.warning("validar_alertas_juridicos: IA falhou, usando apenas basicos: %s", e)
        alertas_ia = []

    # Mescla alertas basicos (sincronos) com alertas da IA
    todos_alertas = alertas_basicos + [
        {
            "nivel": a.get("nivel", "info"),
            "campo": a.get("campo") or "",
            "mensagem": a.get("mensagem") or "",
            "sugestao": a.get("sugestao") or "",
            "resolvido": False,
        }
        for a in alertas_ia
        if isinstance(a, dict) and a.get("mensagem")
    ]

    return todos_alertas


def _verificar_alertas_basicos(
    tipo: str,
    partes: list,
    objeto: dict,
    cond: dict,
    clausulas: list,
    testemunhas: list,
) -> List[Dict[str, Any]]:
    """Verifica alertas basicos de forma sincrona, sem chamada a IA."""
    alertas = []

    # Partes
    if len(partes) < 2:
        alertas.append({
            "nivel": "critico",
            "campo": "partes",
            "mensagem": "O contrato deve ter pelo menos 2 partes (ex: vendedor e comprador).",
            "sugestao": "Cadastre todas as partes do contrato com qualificacao completa.",
            "resolvido": False,
        })

    for p in partes:
        pf = p.get("pf") or {}
        pj = p.get("pj") or {}
        qual = p.get("qualificacao", "Parte")
        if p.get("tipo") == "pf":
            if not pf.get("cpf"):
                alertas.append({
                    "nivel": "aviso",
                    "campo": f"partes.{qual}.cpf",
                    "mensagem": f"CPF nao informado para {qual}.",
                    "sugestao": "Informe o CPF para qualificacao completa da parte.",
                    "resolvido": False,
                })
            if not pf.get("estado_civil"):
                alertas.append({
                    "nivel": "aviso",
                    "campo": f"partes.{qual}.estado_civil",
                    "mensagem": f"Estado civil nao informado para {qual}.",
                    "sugestao": "Estado civil e obrigatorio para contratos de imoveis (art. 1647 CC).",
                    "resolvido": False,
                })
        elif p.get("tipo") == "pj":
            if not pj.get("cnpj"):
                alertas.append({
                    "nivel": "aviso",
                    "campo": f"partes.{qual}.cnpj",
                    "mensagem": f"CNPJ nao informado para {qual} (PJ).",
                    "sugestao": "Informe o CNPJ da pessoa juridica.",
                    "resolvido": False,
                })

    # Objeto
    if not objeto.get("matricula"):
        alertas.append({
            "nivel": "aviso",
            "campo": "objeto.matricula",
            "mensagem": "Matricula do imovel nao informada.",
            "sugestao": "Informe o numero da matricula no Cartorio de Registro de Imoveis.",
            "resolvido": False,
        })

    # Valor
    valor = cond.get("valor_total", 0)
    if not valor or float(valor) <= 0:
        alertas.append({
            "nivel": "critico",
            "campo": "condicoes_pagamento.valor_total",
            "mensagem": "Valor total do contrato nao informado.",
            "sugestao": "Informe o valor total do negocio.",
            "resolvido": False,
        })

    if not cond.get("valor_total_extenso"):
        alertas.append({
            "nivel": "aviso",
            "campo": "condicoes_pagamento.valor_total_extenso",
            "mensagem": "Valor por extenso nao informado.",
            "sugestao": "O valor por extenso e obrigatorio em contratos de imoveis para evitar fraudes.",
            "resolvido": False,
        })

    # Clausulas
    if len(clausulas) < 5:
        alertas.append({
            "nivel": "aviso",
            "campo": "clausulas",
            "mensagem": f"Contrato com apenas {len(clausulas)} clausula(s). Contratos imobiliarios tipicamente possuem 8-15 clausulas.",
            "sugestao": "Use o gerador de clausulas Roma_IA para completar o contrato.",
            "resolvido": False,
        })

    # Testemunhas (obrigatorias para escritura particular)
    if tipo in ("Compra e Venda de Imovel Urbano", "Compra e Venda de Imovel Rural", "Promessa de Compra e Venda"):
        if len(testemunhas) < 2:
            alertas.append({
                "nivel": "aviso",
                "campo": "testemunhas",
                "mensagem": "Instrumento particular de C&V requer 2 testemunhas (art. 221 CC).",
                "sugestao": "Adicione 2 testemunhas com qualificacao completa.",
                "resolvido": False,
            })

    return alertas


# ── Utilitarios ───────────────────────────────────────────────────────────────

_ROMANOS = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def _to_roman(n: int) -> str:
    """Converte inteiro para numero romano."""
    if n <= 0:
        return str(n)
    result = ""
    for val, sym in _ROMANOS:
        while n >= val:
            result += sym
            n -= val
    return result


# ── Simulador de penalidades ──────────────────────────────────────────────────

def calcular_penalidades(contrato: Dict[str, Any], dias_atraso: int = 30) -> Dict[str, Any]:
    """Calcula penalidades por inadimplemento com base nas clausulas do contrato.

    Args:
        contrato: Dados do contrato
        dias_atraso: Numero de dias de atraso para simulacao

    Returns:
        Dict com valores de multa, juros, correcao e total
    """
    cond = contrato.get("condicoes_pagamento") or {}
    valor_total = float(cond.get("valor_total") or 0)
    multa_pct = float(cond.get("multa_inadimplemento") or 2.0)  # default 2% (CDC)
    juros_pct = float(cond.get("juros_mora") or 1.0)  # default 1% a.m. (art. 406 CC)

    # Verifica arras penitenciais
    sinal = float(cond.get("sinal_valor") or 0)
    arras_tipo = cond.get("sinal_arras_tipo", "")

    # Multa contratual
    multa_valor = valor_total * (multa_pct / 100)

    # Juros de mora pro-rata temporis
    juros_diario = juros_pct / 100 / 30
    juros_valor = valor_total * juros_diario * dias_atraso

    # Correcao monetaria estimada (IPCA aproximado: 0.4% a.m.)
    correcao_diaria = 0.004 / 30
    correcao_valor = valor_total * correcao_diaria * dias_atraso

    total_penalidades = multa_valor + juros_valor + correcao_valor

    resultado = {
        "valor_base": valor_total,
        "dias_atraso": dias_atraso,
        "multa_percentual": multa_pct,
        "multa_valor": round(multa_valor, 2),
        "juros_percentual_mensal": juros_pct,
        "juros_valor": round(juros_valor, 2),
        "correcao_monetaria_estimada": round(correcao_valor, 2),
        "total_penalidades": round(total_penalidades, 2),
        "total_a_pagar": round(valor_total + total_penalidades, 2),
        "base_legal_multa": "art. 52 §1 CDC (max 2%); Clausulas contratuais",
        "base_legal_juros": "art. 406 CC (1% a.m.); SELIC",
        "base_legal_correcao": "IPCA/IGPM conforme clausula de reajuste",
    }

    # Arras penitenciais: dobro do sinal em caso de inadimplemento do comprador
    if arras_tipo == "penitenciais" and sinal > 0:
        resultado["arras_penitenciais"] = {
            "sinal_pago": sinal,
            "perda_pelo_comprador": sinal,
            "restituicao_em_dobro_pelo_vendedor": sinal * 2,
            "base_legal": "art. 418 CC",
        }

    return resultado


# ── Checklist de verificacao ──────────────────────────────────────────────────

def gerar_checklist(contrato: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gera checklist de verificacao do contrato antes da assinatura.

    Returns:
        Lista de itens do checklist com: item, categoria, ok, observacao
    """
    tipo = contrato.get("tipo_contrato", "")
    partes = contrato.get("partes") or []
    objeto = contrato.get("objeto") or {}
    cond = contrato.get("condicoes_pagamento") or {}
    clausulas = contrato.get("clausulas") or []
    testemunhas = contrato.get("testemunhas") or []
    corretor = contrato.get("corretor")

    checklist = []

    # ── Identificacao ──
    checklist.append({
        "item": "Tipo de contrato definido",
        "categoria": "Identificacao",
        "ok": bool(tipo),
        "observacao": tipo if tipo else "Tipo nao definido",
    })
    checklist.append({
        "item": "Numero do contrato gerado",
        "categoria": "Identificacao",
        "ok": bool(contrato.get("numero_contrato")),
        "observacao": contrato.get("numero_contrato") or "Sera gerado automaticamente",
    })

    # ── Partes ──
    checklist.append({
        "item": "Pelo menos 2 partes cadastradas",
        "categoria": "Partes",
        "ok": len(partes) >= 2,
        "observacao": f"{len(partes)} parte(s) cadastrada(s)",
    })
    for p in partes:
        qual = p.get("qualificacao", "Parte")
        pf = p.get("pf") or {}
        pj = p.get("pj") or {}
        if p.get("tipo") == "pf":
            nome = pf.get("nome", "")
            checklist.append({
                "item": f"{qual} — Nome completo",
                "categoria": "Partes",
                "ok": bool(nome),
                "observacao": nome or "Nao informado",
            })
            checklist.append({
                "item": f"{qual} — CPF",
                "categoria": "Partes",
                "ok": bool(pf.get("cpf")),
                "observacao": pf.get("cpf") or "Nao informado",
            })
            checklist.append({
                "item": f"{qual} — Estado civil",
                "categoria": "Partes",
                "ok": bool(pf.get("estado_civil")),
                "observacao": pf.get("estado_civil") or "Nao informado",
            })
        elif p.get("tipo") == "pj":
            checklist.append({
                "item": f"{qual} — Razao social",
                "categoria": "Partes",
                "ok": bool(pj.get("razao_social")),
                "observacao": pj.get("razao_social") or "Nao informado",
            })
            checklist.append({
                "item": f"{qual} — CNPJ",
                "categoria": "Partes",
                "ok": bool(pj.get("cnpj")),
                "observacao": pj.get("cnpj") or "Nao informado",
            })

    # ── Objeto ──
    checklist.append({
        "item": "Endereco do imovel/objeto",
        "categoria": "Objeto",
        "ok": bool(objeto.get("endereco")),
        "observacao": objeto.get("endereco") or "Nao informado",
    })
    checklist.append({
        "item": "Matricula no CRI",
        "categoria": "Objeto",
        "ok": bool(objeto.get("matricula")),
        "observacao": objeto.get("matricula") or "Nao informado",
    })
    checklist.append({
        "item": "Situacao juridica do imovel",
        "categoria": "Objeto",
        "ok": bool(objeto.get("situacao")),
        "observacao": objeto.get("situacao") or "Nao informado",
    })

    # ── Financeiro ──
    valor = float(cond.get("valor_total") or 0)
    checklist.append({
        "item": "Valor total do negocio",
        "categoria": "Financeiro",
        "ok": valor > 0,
        "observacao": f"R$ {valor:,.2f}" if valor > 0 else "Nao informado",
    })
    checklist.append({
        "item": "Valor por extenso",
        "categoria": "Financeiro",
        "ok": bool(cond.get("valor_total_extenso")),
        "observacao": cond.get("valor_total_extenso") or "Nao informado",
    })
    checklist.append({
        "item": "Forma de pagamento definida",
        "categoria": "Financeiro",
        "ok": bool(cond.get("forma_principal")),
        "observacao": cond.get("forma_principal") or "Nao definida",
    })
    checklist.append({
        "item": "Multa por inadimplemento",
        "categoria": "Financeiro",
        "ok": cond.get("multa_inadimplemento") is not None,
        "observacao": f"{cond.get('multa_inadimplemento', 0)}%" if cond.get("multa_inadimplemento") is not None else "Nao definida",
    })

    # ── Clausulas ──
    checklist.append({
        "item": f"Clausulas contratuais (minimo 5)",
        "categoria": "Clausulas",
        "ok": len(clausulas) >= 5,
        "observacao": f"{len(clausulas)} clausula(s) cadastrada(s)",
    })

    # ── Assinatura ──
    checklist.append({
        "item": "Testemunhas (minimo 2)",
        "categoria": "Assinatura",
        "ok": len(testemunhas) >= 2,
        "observacao": f"{len(testemunhas)} testemunha(s) cadastrada(s)",
    })
    checklist.append({
        "item": "Data de assinatura",
        "categoria": "Assinatura",
        "ok": bool(contrato.get("data_assinatura")),
        "observacao": contrato.get("data_assinatura") or "Nao definida",
    })
    checklist.append({
        "item": "Cidade de assinatura",
        "categoria": "Assinatura",
        "ok": bool(contrato.get("cidade_assinatura")),
        "observacao": contrato.get("cidade_assinatura") or "Nao definida",
    })

    # ── Corretor (se presente) ──
    if corretor:
        checklist.append({
            "item": "CRECI do corretor",
            "categoria": "Corretagem",
            "ok": bool(corretor.get("creci")),
            "observacao": corretor.get("creci") or "Nao informado",
        })
        checklist.append({
            "item": "Comissao definida",
            "categoria": "Corretagem",
            "ok": bool(corretor.get("comissao_percentual") or corretor.get("comissao_valor")),
            "observacao": f"{corretor.get('comissao_percentual', 0)}%" if corretor.get("comissao_percentual") else "Nao definida",
        })

    # Resumo
    total = len(checklist)
    ok_count = sum(1 for c in checklist if c["ok"])

    return {
        "itens": checklist,
        "resumo": {
            "total": total,
            "ok": ok_count,
            "pendente": total - ok_count,
            "percentual_completo": round((ok_count / total) * 100, 1) if total > 0 else 0,
        },
    }
