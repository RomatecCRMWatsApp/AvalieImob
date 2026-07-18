# @module routes.admin — Endpoints administrativos (criação de usuários teste e listagem)
import logging
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from dependencies import get_admin_user, serialize_doc
from services.auth_service import hash_password
from models import CreateTestUserRequest, AdminUserOut, User
from models.auditoria_acesso import (
    AuditoriaUsuarioOut, TimelineOut, derivar_status_funil,
)

router = APIRouter(tags=["admin"])
logger = logging.getLogger("romatec")


@router.get("/admin/email/status")
async def admin_email_status(uid: str = Depends(get_admin_user)):
    """Estado da configuração de e-mail (provedor, remetente) — sem expor segredos."""
    from email_service import email_config_status
    return email_config_status()


@router.post("/admin/email/test")
async def admin_email_test(body: dict, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Envia um e-mail de TESTE para o endereço informado e devolve o resultado real."""
    import re
    to = str((body or {}).get("to") or "").strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to):
        raise HTTPException(status_code=422, detail="Informe um e-mail válido para o teste.")
    from email_service import send_test_email
    import asyncio
    try:
        res = await asyncio.to_thread(send_test_email, to)
    except Exception as e:  # noqa: BLE001 — devolve o erro real do provedor p/ diagnóstico
        logger.error("Teste de e-mail falhou: %s", e, exc_info=True)
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return res


@router.post("/admin/email/welcome")
async def admin_send_welcome(body: dict, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Envia o e-mail de BOAS-VINDAS (com todas as opções da plataforma) — a um e-mail
    específico OU a todos os usuários já cadastrados (no e-mail de cadastro de cada um)."""
    import re
    import asyncio
    from email_service import send_welcome_email

    to = str((body or {}).get("to") or "").strip().lower()
    todos = bool((body or {}).get("all"))

    if todos:
        users = await db.users.find({}, {"email": 1, "name": 1}).to_list(5000)
    elif to:
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to):
            raise HTTPException(status_code=422, detail="Informe um e-mail válido.")
        u = await db.users.find_one({"email": to}, {"email": 1, "name": 1})
        # aceita e-mail avulso (ainda não cadastrado) — nome vazio
        users = [u] if u else [{"email": to, "name": ""}]
    else:
        raise HTTPException(status_code=422, detail="Informe um e-mail ou marque 'todos'.")

    destinatarios = [u for u in users if u and str(u.get("email") or "").strip()]
    # send_welcome_email é fire-and-forget (loga erros internamente); roda em paralelo.
    await asyncio.gather(
        *[send_welcome_email(u["email"], u.get("name") or "") for u in destinatarios],
        return_exceptions=True,
    )
    logger.info("Admin %s reenviou boas-vindas para %s destinatario(s)", uid, len(destinatarios))
    return {"ok": True, "enviados": len(destinatarios), "todos": todos}


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


@router.get("/admin/users/audit", response_model=List[AuditoriaUsuarioOut])
async def admin_users_audit(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Funil de acesso e pagamento de todos os usuários. Somente leitura.

    `status_funil` é DIAGNÓSTICO — não reflete permissão de acesso, que continua
    sendo decidida por `plan_status` em dependencies.get_active_subscriber.
    """
    users = await db.users.find({}).sort("created_at", -1).to_list(5000)
    ids = [u["id"] for u in users if u.get("id")]

    # Último evento de pagamento por usuário, em UMA passada (evita N+1).
    ultimo_por_uid = {}
    cursor = db.payment_events.find({"user_id": {"$in": ids}}).sort("received_at", 1)
    async for ev in cursor:
        ultimo_por_uid[ev.get("user_id")] = ev  # ascendente ⇒ sobra o mais recente

    saida = []
    for u in users:
        ev = ultimo_por_uid.get(u.get("id"))
        saida.append(AuditoriaUsuarioOut(
            id=u.get("id", ""),
            name=u.get("name") or "",
            email=u.get("email") or "",
            role=u.get("role") or "",
            cadastrado_em=u.get("created_at"),
            ultimo_acesso=u.get("last_login_at"),
            total_acessos=int(u.get("login_count") or 0),
            nunca_acessou=not u.get("last_login_at"),
            plan=u.get("plan") or "",
            plan_status=u.get("plan_status") or "",
            plan_expires=u.get("plan_expires"),
            status_funil=derivar_status_funil(u, ev),
            checkout_iniciado_em=u.get("checkout_started_at"),
            ultimo_evento_pagamento=({
                "status": ev.get("status"),
                "status_detail": ev.get("status_detail"),
                "em": ev.get("received_at"),
            } if ev else None),
        ))
    return saida


@router.get("/admin/users/{user_id}/timeline", response_model=TimelineOut)
async def admin_user_timeline(
    user_id: str, uid: str = Depends(get_admin_user), db=Depends(get_db)
):
    """Linha do tempo de acessos e pagamentos de um usuário."""
    acessos = await db.user_access_log.find({"user_id": user_id}) \
        .sort("created_at", -1).to_list(50)
    pagamentos = await db.payment_events.find({"user_id": user_id}) \
        .sort("received_at", -1).to_list(200)
    return TimelineOut(
        acessos=[serialize_doc(a) for a in acessos],
        pagamentos=[serialize_doc(p) for p in pagamentos],
    )


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Exclui um usuário (admin). Não permite excluir a própria conta."""
    if user_id == uid:
        raise HTTPException(status_code=400, detail="Você não pode excluir a sua própria conta.")
    res = await db.users.delete_one({"id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    logger.info("Admin %s excluiu usuario %s", uid, user_id)
    return {"ok": True}


@router.post("/admin/users/excluir-inativos")
async def admin_delete_inactive_users(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Exclui em massa os usuários SEM assinatura ativa (exceto a própria conta)."""
    res = await db.users.delete_many({
        "id": {"$ne": uid},
        "$or": [
            {"plan_status": {"$ne": "active"}},
            {"plan_status": {"$exists": False}},
        ],
    })
    logger.info("Admin %s excluiu %s usuarios inativos", uid, res.deleted_count)
    return {"ok": True, "excluidos": res.deleted_count}
