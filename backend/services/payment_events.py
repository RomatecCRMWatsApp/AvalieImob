# @module services.payment_events — log APPEND-ONLY dos webhooks do Mercado Pago.
# Nunca é editado. É a fonte de auditoria para reconstruir o funil e investigar
# "o cliente pagou e não ativou". Complementa (não substitui) `transactions`,
# que registra apenas compras aprovadas.
import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def registrar(
    db, user_id: Optional[str], pagamento: Dict[str, Any], plan_id: Optional[str]
) -> bool:
    """Grava um evento de pagamento. Retorna True se gravou, False se ignorou/falhou.

    Idempotente: um mesmo (mp_payment_id, status) só entra uma vez, mas transições
    de status do mesmo pagamento geram linhas novas (é um log, não um estado).
    """
    try:
        mp_id = str(pagamento.get("id") or "")
        status = (pagamento.get("status") or "").lower()
        if not mp_id:
            logger.warning("payment_events: pagamento sem id, ignorado")
            return False

        ja = await db.payment_events.find_one({"mp_payment_id": mp_id, "status": status})
        if ja:
            return False

        await db.payment_events.insert_one({
            "user_id": user_id,
            "plan_id": plan_id,
            "mp_payment_id": mp_id,
            "status": status,
            "status_detail": pagamento.get("status_detail"),
            "transaction_amount": pagamento.get("transaction_amount"),
            "raw_payload": pagamento,
            "received_at": datetime.utcnow(),
        })
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("payment_events: falha ao registrar evento: %s", e)
        return False


async def ultimo_por_usuario(db, user_id: str) -> Optional[Dict[str, Any]]:
    """Evento mais recente do usuário, ou None."""
    try:
        return await db.payment_events.find_one(
            {"user_id": user_id}, sort=[("received_at", -1)]
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("payment_events: falha ao ler ultimo evento: %s", e)
        return None
