# @module services.acesso_log — registro de acesso dos usuários (append-only).
# Toda gravação é best-effort: auditoria JAMAIS derruba a request do usuário.
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from models.auditoria_acesso import (
    DIAS_RETENCAO_HEARTBEAT, MINUTOS_THROTTLE_HEARTBEAT,
)

logger = logging.getLogger(__name__)

# Cache em processo do último heartbeat por usuário. Evita uma leitura no Mongo
# a cada request autenticada. Com 4 workers uvicorn, o pior caso são 4 gravações
# por janela de throttle por usuário — irrelevante em volume.
_ultimo_heartbeat: Dict[str, datetime] = {}


def limpar_cache_throttle() -> None:
    """Zera o cache de throttle. Usado pelos testes."""
    _ultimo_heartbeat.clear()


async def _gravar(
    db, user_id: str, event: str, ip: Optional[str], user_agent: Optional[str],
    ttl: bool, incrementar: bool,
) -> None:
    agora = datetime.utcnow()
    doc: Dict[str, Any] = {
        "user_id": user_id,
        "event": event,
        "ip": ip,
        "user_agent": (user_agent or "")[:400],
        "created_at": agora,
    }
    # Só heartbeats recebem `expira_em`; o índice TTL ignora docs sem o campo,
    # então login/logout ficam permanentes.
    if ttl:
        doc["expira_em"] = agora + timedelta(days=DIAS_RETENCAO_HEARTBEAT)

    await db.user_access_log.insert_one(doc)

    update: Dict[str, Any] = {"$set": {"last_login_at": agora}}
    if incrementar:
        update["$inc"] = {"login_count": 1}
    await db.users.update_one({"id": user_id}, update)


async def registrar_login(
    db, user_id: str, ip: Optional[str] = None, user_agent: Optional[str] = None
) -> None:
    """Evento permanente. Só ele incrementa `login_count`."""
    try:
        _ultimo_heartbeat[user_id] = datetime.utcnow()
        await _gravar(db, user_id, "login", ip, user_agent, ttl=False, incrementar=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("acesso_log: falha ao registrar login de %s: %s", user_id, e)


async def registrar_heartbeat(
    db, user_id: str, ip: Optional[str] = None, user_agent: Optional[str] = None
) -> None:
    """Evento efêmero (TTL). Throttled em MINUTOS_THROTTLE_HEARTBEAT."""
    try:
        agora = datetime.utcnow()
        anterior = _ultimo_heartbeat.get(user_id)
        if anterior and (agora - anterior) < timedelta(minutes=MINUTOS_THROTTLE_HEARTBEAT):
            return
        _ultimo_heartbeat[user_id] = agora
        await _gravar(
            db, user_id, "session_heartbeat", ip, user_agent, ttl=True, incrementar=False
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("acesso_log: falha ao registrar heartbeat de %s: %s", user_id, e)
