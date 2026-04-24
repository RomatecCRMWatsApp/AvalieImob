from fastapi import APIRouter, Header, HTTPException
from db import get_db
from datetime import datetime
import os

router = APIRouter(tags=["seed"])

@router.post("/seed-admin")
async def seed_admin(x_seed_token: str | None = Header(default=None)):
    if os.getenv("ENABLE_SEED_ADMIN", "false").lower() != "true":
        raise HTTPException(404, "Rota não disponível")

    expected_token = os.getenv("SEED_ADMIN_TOKEN", "")
    if not expected_token:
        raise HTTPException(503, "SEED_ADMIN_TOKEN não configurado")
    if x_seed_token != expected_token:
        raise HTTPException(403, "Token de seed inválido")

    db = get_db()
    existing = await db.users.find_one({"role": "admin"})
    if existing:
        raise HTTPException(400, "Administrador já existe. Seed não permitido.")
    
    admin_user = {
        "id": "admin-001",
        "nome": "Administrador",
        "email": "admin@romatec.com",
        "cpf_cnpj": "00000000000",
        "telefone": "(99) 99999-9999",
        "password_hash": "$2b$12$F10KB.hC/fTjhUdjxcBJ0e/3jYAJv.ugf8OPWKw1.3mroa5dTaK1S",  # senha: 430198Ro
        "plano": "anual",
        "plan_status": "active",
        "role": "admin",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(admin_user)
    return {"ok": True, "message": "Admin criado", "email": "admin@romatec.com"}
