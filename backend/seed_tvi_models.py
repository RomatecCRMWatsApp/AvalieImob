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
from seed_tvi_cat3 import MODELOS_OBRAS, MODELOS_JUDICIAL, MODELOS_RAMO6
from seed_tvi_cat4 import (
    MODELOS_SEGURANCA,
    MODELOS_COMERCIAL,
    MODELOS_INSTALACOES,
    MODELOS_COMPLEMENTARES,
    MODELOS_RAMO7,
    MODELOS_RAMO8,
    MODELOS_RAMO9,
    MODELOS_RAMO10,
)

# Modelos legados (schema v1 — campos_especificos como lista de {key, label, type})
ALL_MODELOS_LEGADO = (
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

# Modelos v2 — schema profissional com id, ramo, aplicacao, normas, requer_art
# Ramos 6-10: TVI-30 a TVI-45
ALL_MODELOS_V2 = (
    MODELOS_RAMO6
    + MODELOS_RAMO7
    + MODELOS_RAMO8
    + MODELOS_RAMO9
    + MODELOS_RAMO10
)

# Lista unificada para seed
ALL_MODELOS = ALL_MODELOS_LEGADO + ALL_MODELOS_V2


async def seed():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    col = db.vistoria_models

    inserted = 0
    skipped = 0
    for modelo in ALL_MODELOS:
        # Modelos v2 usam campo "id" (ex.: "TVI-30"), legados usam "tipo"
        chave_lookup = modelo.get("id") or modelo.get("tipo")
        existing = await col.find_one(
            {"$or": [{"id": chave_lookup}, {"tipo": chave_lookup}]}
            if modelo.get("id")
            else {"tipo": chave_lookup}
        )
        if existing:
            skipped += 1
            continue
        import uuid
        from datetime import datetime
        doc = {**modelo, "ativo": True, "created_at": datetime.utcnow()}
        if not modelo.get("id"):
            doc["id"] = str(uuid.uuid4())
        await col.insert_one(doc)
        inserted += 1
        cat = modelo.get("ramo") or modelo.get("categoria", "")
        nome = modelo.get("nome", "")
        print(f"  [OK] {cat} | {nome}")

    client.close()
    print(f"\nTotal modelos: {len(ALL_MODELOS)} | Inseridos: {inserted} | Ignorados (já existem): {skipped}")


if __name__ == "__main__":
    asyncio.run(seed())
