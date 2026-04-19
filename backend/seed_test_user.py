"""Script para criar a conta de teste padrao no MongoDB.

Uso:
    python seed_test_user.py

Variaveis de ambiente necessarias (podem estar no .env):
    MONGO_URL   - URL de conexao ao MongoDB
    DB_NAME     - Nome do banco de dados
"""
import asyncio
import os
import uuid
from pathlib import Path
from datetime import datetime, timedelta

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

ROOT_DIR = Path(__file__).parent
# Tenta .env no backend/, depois na raiz do projeto
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR.parent / ".env")

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_USER = {
    "name": "Usuario Teste",
    "email": "teste@avalieimob.com",
    "password": "teste123",
    "role": "user",
    "plan": "mensal",
    "plan_status": "active",
}


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    mongo_client = AsyncIOMotorClient(mongo_url)
    db = mongo_client[db_name]

    existing = await db.users.find_one({"email": TEST_USER["email"]})
    if existing:
        print(f"[INFO] Conta {TEST_USER['email']} ja existe. Nenhuma acao necessaria.")
        mongo_client.close()
        return

    plan_expires = datetime.utcnow() + timedelta(days=365)
    now = datetime.utcnow()

    doc = {
        "id": str(uuid.uuid4()),
        "name": TEST_USER["name"],
        "email": TEST_USER["email"],
        "role": TEST_USER["role"],
        "crea": "",
        "plan": TEST_USER["plan"],
        "plan_status": TEST_USER["plan_status"],
        "plan_expires": plan_expires,
        "company": "",
        "bio": "",
        "created_at": now,
        "password_hash": _pwd_context.hash(TEST_USER["password"]),
    }

    await db.users.insert_one(doc)
    print(f"[OK] Conta de teste criada:")
    print(f"     Email:       {TEST_USER['email']}")
    print(f"     Senha:       {TEST_USER['password']}")
    print(f"     Role:        {TEST_USER['role']}")
    print(f"     Plano:       {TEST_USER['plan']} ({TEST_USER['plan_status']})")
    print(f"     Expira em:   {plan_expires.strftime('%d/%m/%Y')}")

    mongo_client.close()


if __name__ == "__main__":
    asyncio.run(main())
