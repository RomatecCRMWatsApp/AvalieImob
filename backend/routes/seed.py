from fastapi import APIRouter, HTTPException
from db import get_db
from datetime import datetime
import os

router = APIRouter(tags=["seed"])

@router.post("/seed-admin")
async def seed_admin():
    # Protecao simples: so funciona se nao houver usuarios
    db = get_db()
    existing = await db.users.find_one({})
    if existing:
        raise HTTPException(400, "Usuarios ja existem. Seed nao permitido.")
    
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
    return {"ok": True, "message": "Admin criado", "email": "admin@romatec.com", "senha": "430198Ro"}
