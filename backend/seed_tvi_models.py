# @module seed_tvi_models — Popula a collection vistoria_models com todos os 45 modelos TVI
"""
Uso:
    cd AvalieImob/backend
    python seed_tvi_models.py

Requer variáveis de ambiente MONGO_URL e DB_NAME (lidas de .env via dotenv).
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient
from seed_tvi_cat1 import MODELOS_GERAL, MODELOS_LOCACAO
from seed_tvi_cat2 import MODELOS_RURAL, MODELOS_REGULARIZACAO
from seed_tvi_cat3 import MODELOS_OBRAS, MODELOS_JUDICIAL
from seed_tvi_cat4 import MODELOS_SEGURANCA, MODELOS_COMERCIAL, MODELOS_INSTALACOES, MODELOS_COMPLEMENTARES

ALL_MODELOS = (
    MODELOS_GERAL
    + MODELOS_LOCACAO
    + MODELOS_RURAL
    + MODELOS_REGULARIZACAO
    + MODELOS_OBRAS
    + MODELOS_JUDICIAL
    + MODELOS_SEGURANCA
    + MODELOS_COMERCIAL
    + MODELOS_INSTALACOES
    + MODELOS_COMPLEMENTARES
)


async def seed():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    col = db.vistoria_models

    inserted = 0
    skipped = 0
    for modelo in ALL_MODELOS:
        existing = await col.find_one({"tipo": modelo["tipo"]})
        if existing:
            skipped += 1
            continue
        import uuid
        from datetime import datetime
        doc = {**modelo, "id": str(uuid.uuid4()), "ativo": True, "created_at": datetime.utcnow()}
        await col.insert_one(doc)
        inserted += 1
        print(f"  [OK] {modelo['categoria']} | {modelo['nome']}")

    client.close()
    print(f"\nTotal modelos: {len(ALL_MODELOS)} | Inseridos: {inserted} | Ignorados (já existem): {skipped}")


if __name__ == "__main__":
    asyncio.run(seed())
