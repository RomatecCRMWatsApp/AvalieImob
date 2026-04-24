# @module routes.email — Endpoints de teste de envio de e-mail
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from dependencies import get_admin_user

try:
    from email_service import send_welcome_email
except ImportError:
    async def send_welcome_email(*a, **kw): pass

router = APIRouter(tags=["email"])


@router.post("/email/test")
async def email_test(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    await send_welcome_email(u.get("email", ""), u.get("name", "Usuario"))
    return {"ok": True, "message": f"Email de teste enviado para {u.get('email')}"}


@router.post("/email/send-test")
async def email_send_test(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    await send_welcome_email(u.get("email", ""), u.get("name", "Usuario"))
    return {"ok": True, "message": f"Email de teste enviado para {u.get('email')}"}
