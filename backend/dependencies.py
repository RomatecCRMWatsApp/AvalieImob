# @module dependencies — Dependências FastAPI compartilhadas entre rotas
import asyncio
from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from db import get_db
from services.auth_service import get_current_user_id


def _heartbeat(db, uid: str) -> None:
    """Dispara o heartbeat de auditoria sem bloquear a resposta (fire-and-forget).

    Import interno para evitar import circular com o pacote services.
    Só é chamado em caminhos de acesso CONCEDIDO — request negada não é acesso.
    """
    try:
        from services import acesso_log
        asyncio.create_task(acesso_log.registrar_heartbeat(db, uid))
    except Exception:  # noqa: BLE001
        pass


async def get_active_subscriber(uid: str = Depends(get_current_user_id), db=Depends(get_db)) -> str:
    """Verifica se o usuário possui assinatura ativa. Admin bypassa a verificação."""
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    role = str(u.get("role") or "user").lower()
    if role in ("admin", "owner", "ceo"):
        _heartbeat(db, uid)
        return uid
    plan_status = u.get("plan_status", "inactive")
    plan_expires = u.get("plan_expires")
    # Usa timezone-aware UTC. Se plan_expires vier naive do MongoDB, normaliza
    # pra UTC antes de comparar (evita TypeError em comparação naive vs aware).
    now = datetime.now(timezone.utc)
    if plan_expires is not None and plan_expires.tzinfo is None:
        plan_expires = plan_expires.replace(tzinfo=timezone.utc)
    if plan_status == "active" and plan_expires and plan_expires < now:
        plan_status = "expired"
        await db.users.update_one({"id": uid}, {"$set": {"plan_status": "expired"}})
    if plan_status != "active":
        raise HTTPException(
            status_code=403,
            detail="Assinatura inativa. Acesse a página de assinatura para ativar seu plano."
        )
    _heartbeat(db, uid)
    return uid


async def get_authenticated_user(uid: str = Depends(get_current_user_id), db=Depends(get_db)) -> str:
    """Valida JWT e confirma que o usuário existe, sem exigir plano ativo.
    Use em endpoints de leitura onde usuários com plano expirado ainda devem
    acessar seus próprios dados."""
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    _heartbeat(db, uid)
    return uid


async def get_admin_user(uid: str = Depends(get_current_user_id), db=Depends(get_db)) -> str:
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if str(u.get("role") or "").lower() not in ("admin", "owner", "ceo"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    _heartbeat(db, uid)
    return uid


def serialize_doc(doc):
    if not doc:
        return doc
    payload = dict(doc)
    mongo_id = payload.pop("_id", None)
    if mongo_id is not None and not payload.get("id"):
        payload["id"] = str(mongo_id)
    payload.pop("password_hash", None)
    return payload
