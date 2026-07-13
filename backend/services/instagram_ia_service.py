# @module services.instagram_ia_service — Gera conteúdo de Instagram por pilar (reusa a cascata Roma_IA).
import logging
from typing import Any, Dict

from fastapi import HTTPException

from services.contrato_ia_service import _roma_ia_cascata, _parse_json_safe

logger = logging.getLogger("romatec")

CONTEXTO_SISTEMA = (
    "O AvalieImob é um sistema brasileiro de avaliação imobiliária (PTAM/laudos NBR 14.653), "
    "contratos, assinatura ICP-Brasil, georreferenciamento e prospecção. Público: corretores, "
    "imobiliárias e proprietários. Perfil no Instagram: @avalieimob."
)

_PILAR_INSTRUCAO = {
    "recursos": "Destaque UMA funcionalidade do sistema (PTAM, contratos, assinatura ICP, georreferenciamento) e o benefício prático para o corretor.",
    "autoridade": "Ensine algo útil sobre avaliação imobiliária (NBR 14.653, erros comuns, boas práticas). Tom de especialista.",
    "quanto_vale": "Chame o proprietário/corretor a descobrir o valor do imóvel na calculadora gratuita. Topo de funil.",
    "novidades": "Anuncie uma novidade/oferta do sistema com CTA de cadastro.",
}

_FORMATO_INSTRUCAO = {
    "post_unico": 'Gere "titulo" (frase de impacto curta) e "legenda". Deixe "slides" e "roteiro" vazios.',
    "carrossel": 'Gere "titulo" (capa) e "slides" (4 a 6 itens {titulo, texto}), o último com CTA. Deixe "roteiro" vazio.',
    "reel_roteiro": 'Gere "titulo" e "roteiro" (roteiro falado de 20-40s, com gancho nos 3 primeiros segundos). Deixe "slides" vazio.',
}

_LINK_MAP = {
    "recursos": "/cadastro",
    "autoridade": "/cadastro",
    "quanto_vale": "/quanto-vale-meu-imovel",
    "novidades": "/cadastro",
}


async def gerar_conteudo(pilar: str, assunto: str, formato: str) -> Dict[str, Any]:
    if pilar not in _PILAR_INSTRUCAO:
        raise HTTPException(status_code=400, detail="Pilar inválido")
    if formato not in _FORMATO_INSTRUCAO:
        raise HTTPException(status_code=400, detail="Formato inválido")

    prompt = (
        f"{CONTEXTO_SISTEMA}\n\n"
        "Crie um conteúdo para o Instagram @avalieimob.\n"
        f"PILAR: {_PILAR_INSTRUCAO[pilar]}\n"
        f"FORMATO: {_FORMATO_INSTRUCAO[formato]}\n"
        f"ASSUNTO: {assunto or 'livre, dentro do pilar'}\n\n"
        "REGRAS: português do Brasil; sem clickbait vazio; UM CTA claro; "
        "hashtags do nicho (avaliação imobiliária, corretor, imóveis, laudo); "
        'a legenda deve terminar com "Siga @avalieimob".\n\n'
        "Responda APENAS um JSON válido com as chaves exatas: "
        '{"titulo": str, "legenda": str, "hashtags": [str], '
        '"slides": [{"titulo": str, "texto": str}], "roteiro": str, "cta": str}.'
    )
    messages = [{"role": "user", "content": prompt}]
    texto = await _roma_ia_cascata(messages, max_tokens=2000)
    data = _parse_json_safe(texto)
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="A IA não retornou um JSON válido. Tente novamente.")

    return {
        "titulo": data.get("titulo", ""),
        "legenda": data.get("legenda", ""),
        "hashtags": data.get("hashtags", []) or [],
        "slides": data.get("slides", []) or [],
        "roteiro": data.get("roteiro", ""),
        "cta": data.get("cta", ""),
        "link": _LINK_MAP[pilar],
        "pilar": pilar,
        "formato": formato,
    }
