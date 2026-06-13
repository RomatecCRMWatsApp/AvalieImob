# @module pdf.templates.registry — Resolve o renderer de PDF por nome de template.
# Regra de ouro: o CONTEÚDO (cláusulas/dados) é montado uma vez; cada renderer só
# decide COMO desenhar. Todos os renderers compartilham a assinatura:
#     render(doc: dict, uid: str, empresa: str) -> bytes  (PDF, síncrono)
import logging

logger = logging.getLogger("romatec")

TEMPLATES_DISPONIVEIS = ["prime1", "prime2", "tradicional"]
# Padrão = PRIME II (mesmo default do Wizard, form.template_pdf || 'prime2').
# Antes era "tradicional", o que fazia o botão PDF/Ver do CARD (que não envia
# ?template=) baixar o layout sóbrio em vez do Prime esperado pelo usuário.
# O gerador tradicional continua como REDE DE SEGURANÇA: qualquer falha no
# renderer escolhido cai nele (ver gerar_pdf_contrato abaixo).
TEMPLATE_PADRAO = "prime2"


def _renderer_tradicional():
    # Gerador clássico já existente e validado (A4 sóbrio) — serve de "tradicional".
    from routes.contratos import _generate_contrato_pdf_bytes
    return _generate_contrato_pdf_bytes


def _renderer_prime2():
    from pdf.templates.contrato_prime2 import render as r
    return r


def _renderer_prime1():
    from pdf.templates.contrato_prime1 import render as r
    return r


def get_renderer(nome: str):
    """Retorna o callable render(doc, uid, empresa)->bytes do template pedido."""
    nome = (nome or TEMPLATE_PADRAO).lower().strip()
    if nome == "prime2":
        return _renderer_prime2()
    if nome == "prime1":
        return _renderer_prime1()
    # tradicional usa o gerador clássico já validado
    return _renderer_tradicional()


def gerar_pdf_contrato(doc: dict, uid: str, empresa: str, template: str | None = None) -> bytes:
    """Gera o PDF no template pedido (ou no salvo no contrato, ou no padrão).
    NUNCA quebra o download: qualquer falha no renderer escolhido cai no tradicional."""
    escolhido = (template or doc.get("template_pdf") or TEMPLATE_PADRAO).lower().strip()
    if escolhido not in TEMPLATES_DISPONIVEIS:
        escolhido = TEMPLATE_PADRAO
    try:
        return get_renderer(escolhido)(doc, uid, empresa)
    except Exception as e:  # noqa: BLE001
        logger.warning("Template '%s' falhou (%s) — fallback tradicional.", escolhido, e)
        return _renderer_tradicional()(doc, uid, empresa)
