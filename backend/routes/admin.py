# @module routes.admin — Endpoints administrativos (criação de usuários teste e listagem)
import logging
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from dependencies import get_admin_user, serialize_doc
from services.auth_service import hash_password
from models import CreateTestUserRequest, AdminUserOut, User

router = APIRouter(tags=["admin"])
logger = logging.getLogger("romatec")


@router.post("/admin/create-test-user")
async def admin_create_test_user(data: CreateTestUserRequest, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 6 caracteres")
    plan_expires = None
    if data.plan_status == "active":
        plan_expires = datetime.utcnow() + timedelta(days=365)
    user = User(name=data.name, email=data.email.lower(), role="user", plan=data.plan, plan_status=data.plan_status, plan_expires=plan_expires)
    doc = user.model_dump()
    doc["password_hash"] = hash_password(data.password)
    await db.users.insert_one(doc)
    logger.info("Admin %s criou usuario de teste: %s", uid, user.email)
    return {"ok": True, "id": user.id, "email": user.email, "plan": user.plan, "plan_status": user.plan_status, "plan_expires": plan_expires.isoformat() if plan_expires else None}


@router.get("/admin/users", response_model=List[AdminUserOut])
async def admin_list_users(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    docs = await db.users.find({}).sort("created_at", -1).to_list(5000)
    result = []
    for d in docs:
        d = serialize_doc(d)
        result.append(AdminUserOut(
            id=d.get("id", ""), name=d.get("name", ""), email=d.get("email", ""),
            role=d.get("role", "user"), plan=d.get("plan", "mensal"),
            plan_status=d.get("plan_status", "inactive"),
            plan_expires=d.get("plan_expires"), created_at=d.get("created_at"),
        ))
    return result
