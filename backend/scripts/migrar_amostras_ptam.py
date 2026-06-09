"""Migração: puxa todas as amostras já cadastradas dentro dos PTAMs existentes
(ptam_documents.market_samples) para a collection global `amostras_mercado`.

Reusa a mesma lógica de mapeamento/upsert do router (idempotente por
user_id + ptam_origem_id + referencia), respeitando o user_id de cada PTAM.

Uso (a partir de backend/):
    python -m scripts.migrar_amostras_ptam

Variáveis de ambiente necessárias: MONGO_URL e DB_NAME (mesmas do app).
"""
import asyncio
import os
import sys

# Garante que o pacote `backend` (raiz) esteja no path quando rodado direto.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_THIS_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from routes.amostras_mercado import sincronizar_amostras_ptam  # noqa: E402


async def migrar() -> None:
    mongo_url = os.environ.get("MONGO_URL")
    if not mongo_url:
        raise SystemExit("Defina MONGO_URL no ambiente antes de rodar a migração.")
    db_name = os.environ.get("DB_NAME", "railway")

    is_atlas = "mongodb+srv" in mongo_url or "mongodb.net" in mongo_url
    client = AsyncIOMotorClient(mongo_url, tls=True) if is_atlas else AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    cursor = db.ptam_documents.find(
        {"market_samples": {"$exists": True, "$ne": []}},
        {"id": 1, "user_id": 1},
    )
    ptams = await cursor.to_list(None)

    total_amostras = 0
    total_ptams = 0
    for ptam in ptams:
        pid = ptam.get("id")
        uid = ptam.get("user_id")
        if not pid or not uid:
            continue
        res = await sincronizar_amostras_ptam(pid, uid, db)
        total_amostras += int(res.get("sincronizadas", 0))
        total_ptams += 1
        if res.get("erros"):
            print(f"  ⚠ PTAM {pid}: {len(res['erros'])} erro(s) -> {res['erros']}")

    print(f"✅ Migração concluída: {total_amostras} amostras migradas de {total_ptams} PTAM(s).")
    client.close()


if __name__ == "__main__":
    asyncio.run(migrar())
