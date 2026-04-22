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

# ── Ramos 1-5 (schema v2 profissional — TVI-01 a TVI-29) ──────────────────
from seed_tvi_cat1 import MODELOS_GERAL           # TVI-01 a TVI-08
from seed_tvi_cat2 import MODELOS_LOCACAO, MODELOS_RURAL  # TVI-09 a TVI-18
from seed_tvi_cat3 import MODELOS_REGULARIZACAO, MODELOS_OBRAS  # TVI-19 a TVI-29

# ── Ramos 6-10 (TVI-30 a TVI-45) ────────────────────────────────────────────
from seed_tvi_ramo6  import MODELOS_RAMO6   # TVI-30 a TVI-33 — Judicial/Pericial
from seed_tvi_ramo7  import MODELOS_RAMO7   # TVI-34 a TVI-36 — Segurança/Sinistros
from seed_tvi_ramo8  import MODELOS_RAMO8   # TVI-37 a TVI-39 — Comercial/Empresarial
from seed_tvi_ramo9  import MODELOS_RAMO9   # TVI-40 a TVI-43 — Instalações
from seed_tvi_ramo10 import MODELOS_RAMO10  # TVI-44 a TVI-45 — Complementares

# Todos os 45 modelos TVI
ALL_MODELOS = (
    MODELOS_GERAL           # TVI-01 a TVI-08
    + MODELOS_LOCACAO       # TVI-09 a TVI-12
    + MODELOS_RURAL         # TVI-13 a TVI-18
    + MODELOS_REGULARIZACAO # TVI-19 a TVI-24
    + MODELOS_OBRAS         # TVI-25 a TVI-29
    + MODELOS_RAMO6         # TVI-30 a TVI-33
    + MODELOS_RAMO7         # TVI-34 a TVI-36
    + MODELOS_RAMO8         # TVI-37 a TVI-39
    + MODELOS_RAMO9         # TVI-40 a TVI-43
    + MODELOS_RAMO10        # TVI-44 a TVI-45
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
