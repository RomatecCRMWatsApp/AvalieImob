# @module services.mp_webhook_seguranca — validação da assinatura HMAC do webhook
# do Mercado Pago (cabeçalho `x-signature`).
#
# O MP assina cada notificação com um segredo próprio do painel do vendedor
# (Suas integrações ▸ Webhooks ▸ Chave secreta). O manifest assinado segue o
# template `id:{data.id};request-id:{x-request-id};ts:{ts};`, omitindo as partes
# ausentes, e o header traz `ts=...,v1=<hmac_sha256_hex>`.
#
# A validação só é EXIGIDA quando MERCADOPAGO_WEBHOOK_SECRET está configurado.
# Sem segredo, a função devolve True e o webhook segue protegido apenas pelo
# token em query param (comportamento anterior) — assim ligar este código não
# derruba produção antes de o segredo ser cadastrado no Railway.
import hashlib
import hmac
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def montar_manifest(data_id: Optional[str], request_id: Optional[str], ts: Optional[str]) -> str:
    """Monta o manifest no template do MP, omitindo as partes ausentes."""
    partes = []
    if data_id:
        d = str(data_id)
        # Regra do MP: id alfanumérico entra em minúsculas.
        partes.append(f"id:{d.lower() if not d.isdigit() else d};")
    if request_id:
        partes.append(f"request-id:{request_id};")
    if ts:
        partes.append(f"ts:{ts};")
    return "".join(partes)


def _parse_signature(cabecalho: str) -> tuple:
    """Extrai (ts, v1) do header `ts=...,v1=...`. Devolve (None, None) se inválido."""
    ts = v1 = None
    for parte in str(cabecalho).split(","):
        if "=" not in parte:
            continue
        chave, _, valor = parte.partition("=")
        chave, valor = chave.strip(), valor.strip()
        if chave == "ts":
            ts = valor
        elif chave == "v1":
            v1 = valor
    return ts, v1


def validar_assinatura(
    x_signature: Optional[str],
    x_request_id: Optional[str],
    data_id: Optional[str],
    segredo: str,
) -> bool:
    """True se a assinatura confere (ou se não há segredo configurado)."""
    if not segredo:
        return True  # checagem desligada: sem segredo cadastrado
    if not x_signature:
        logger.warning("MP webhook: x-signature ausente com segredo configurado")
        return False

    ts, v1 = _parse_signature(x_signature)
    if not ts or not v1:
        logger.warning("MP webhook: x-signature malformado")
        return False

    manifest = montar_manifest(data_id, x_request_id, ts)
    esperado = hmac.new(segredo.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    # compare_digest evita timing attack.
    if not hmac.compare_digest(esperado, v1):
        logger.warning("MP webhook: assinatura HMAC não confere (id=%s)", data_id)
        return False
    return True
