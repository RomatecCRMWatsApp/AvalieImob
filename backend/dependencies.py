# @module dependencies — Dependências FastAPI compartilhadas entre rotas
from datetime import datetime
from fastapi import Depends, HTTPException
from db import get_db
from services.auth_service import get_current_user_id


async def get_active_subscriber(uid: str = Depends(get_current_user_id), db=Depends(get_db)) -> str:
    """Verifica se o usuário possui assinatura ativa. Admin bypassa a verificação."""
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    role = u.get("role", "user")
    if role == "admin":
        return uid
    plan_status = u.get("plan_status", "inactive")
    plan_expires = u.get("plan_expires")
    now = datetime.utcnow()
    if plan_status == "active" and plan_expires and plan_expires < now:
        plan_status = "expired"
        await db.users.update_one({"id": uid}, {"$set": {"plan_status": "expired"}})
    if plan_status != "active":
        raise HTTPException(
            status_code=403,
            detail="Assinatura inativa. Acesse a página de assinatura para ativar seu plano."
        )
    return uid


def serialize_doc(doc):
    if not doc:
        return doc
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc
