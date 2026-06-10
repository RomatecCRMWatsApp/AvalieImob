# @module services.recibo_whatsapp — Templates de mensagem WhatsApp p/ recibos
"""
Templates de legenda/mensagem enviados junto ao PDF do recibo via Z-API.
Portado do padrão ZAYRA (receboWhatsappTemplates.ts).
"""
import re as _re
from typing import Optional

VALIDA_BASE = "https://romatecavalieimob.com.br/v/"


def _plain(s) -> str:
    """Remove tags HTML (caso a descrição venha do editor rich text)."""
    if not s:
        return ""
    s = _re.sub(r"(?i)<\s*br\s*/?>|</\s*(p|div|li)\s*>", " ", str(s))
    s = _re.sub(r"<[^>]+>", "", s)
    return s.replace("&nbsp;", " ").replace("&amp;", "&").strip()


def _brl(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 0.0
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def legenda_recibo(recibo: dict) -> str:
    """Legenda padrão que acompanha o PDF do recibo no WhatsApp."""
    nome = (recibo.get("destinatario_nome") or "").split(" ")[0] or "Olá"
    numero = recibo.get("numero") or "—"
    valor = _brl(recibo.get("valor"))
    emitente = recibo.get("emitente_nome") or "Romatec Consultoria Total"
    servico = _plain(recibo.get("servico") or recibo.get("descricao") or "")
    hash_v = recibo.get("hash_validacao")
    ptam_link = recibo.get("ptam_link")

    linhas = [
        f"Olá, {nome}! 👋",
        "",
        f"Segue o recibo *{numero}* no valor de *{valor}*.",
    ]
    if servico:
        linhas.append(f"Referente a: {servico}")
    linhas += [
        "",
        f"Emitido por *{emitente}*.",
    ]
    if hash_v:
        linhas += [
            "Verifique a autenticidade em:",
            f"{VALIDA_BASE}{hash_v}",
        ]
    if ptam_link:
        linhas += [
            "",
            "📄 Laudo (consulta pública):",
            f"{ptam_link}",
        ]
    linhas += ["", "Qualquer dúvida, estou à disposição."]
    return "\n".join(linhas)


def confirmacao_recebimento(recibo: dict) -> str:
    """Mensagem de agradecimento/confirmação após pagamento confirmado."""
    nome = (recibo.get("destinatario_nome") or "").split(" ")[0] or "Olá"
    numero = recibo.get("numero") or "—"
    return (
        f"Obrigado, {nome}! ✅\n\n"
        f"Confirmamos o recebimento referente ao recibo *{numero}*. "
        f"Foi um prazer atendê-lo."
    )
