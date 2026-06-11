# @module pdf.templates.registry — Resolve o renderer de PDF por nome de template.
# Regra de ouro: o CONTEÚDO (cláusulas/dados) é montado uma vez; cada renderer só
# decide COMO desenhar. Todos os renderers compartilham a assinatura:
#     render(doc: dict, uid: str, empresa: str) -> bytes  (PDF, síncrono)
import logging

logger = logging.getLogger("romatec")

TEMPLATES_DISPONIVEIS = ["prime1", "prime2", "tradicional"]
TEMPLATE_PADRAO = "tradicional"   # seguro: gerador clássico já validado em produção


def _renderer_tradicional():
    # Gerador clássico já existente e validado (A4 sóbrio) — serve de "tradicional".
    from routes.contratos import _generate_contrato_pdf_bytes
    return _generate_contrato_pdf_bytes


def _renderer_prime2():
    from pdf.templates.contrato_prime2 import render as r
    return r


def get_renderer(nome: str):
    """Retorna o callable render(doc, uid, empresa)->bytes do template pedido.
    Prime I ainda não tem renderer dedicado → cai no tradicional (sem duplicar conteúdo)."""
    nome = (nome or TEMPLATE_PADRAO).lower().strip()
    if nome == "prime2":
        return _renderer_prime2()
    # prime1 e tradicional usam o gerador clássico por enquanto
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
