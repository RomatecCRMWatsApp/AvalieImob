# @module scripts.seed_incra — Insere uma tabela INCRA de EXEMPLO para testar a seção rural do laudo.
#
# Uso (PowerShell/CMD no Windows, com a venv do backend ativa):
#   set MONGO_URL=<sua_string_de_conexao>
#   set DB_NAME=railway
#   python backend/scripts/seed_incra.py
#
# Ou no Railway:  railway run python backend/scripts/seed_incra.py
#
# É idempotente: só insere se ainda não existir a tabela de exemplo (mesma região + vigência).
# ATENÇÃO: os valores abaixo são EXEMPLO. Substitua pela tabela oficial do INCRA/SR-26/MA
# pela tela Ferramentas → Tabelas INCRA quando tiver os números reais.
import asyncio
import os
import uuid
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

EXEMPLO = {
    "id": str(uuid.uuid4()),
    "regiao": "Sudoeste Maranhense / Imperatriz - MA",
    "municipio": "Açailândia",
    "ano": 2025,
    "mes": 1,
    "vigencia": "Jan/2025",
    "fonte": "INCRA/SR-26/MA — VALORES DE EXEMPLO (substituir pela tabela oficial)",
    "faixas": [
        {"faixa": "Lavoura — aptidão boa", "vr_min": 18000.0, "vr_max": 28000.0, "vr_medio": 23000.0},
        {"faixa": "Lavoura — aptidão regular/restrita", "vr_min": 12000.0, "vr_max": 18000.0, "vr_medio": 15000.0},
        {"faixa": "Pastagem plantada", "vr_min": 8000.0, "vr_max": 12000.0, "vr_medio": 10000.0},
        {"faixa": "Pastagem natural", "vr_min": 5000.0, "vr_max": 8000.0, "vr_medio": 6500.0},
        {"faixa": "Preservação / Reserva Legal", "vr_min": 2500.0, "vr_max": 5000.0, "vr_medio": 3750.0},
    ],
    "user_id": None,
    "ativo": True,
    "created_at": datetime.utcnow(),
}


async def main():
    url = os.environ.get("MONGO_URL")
    if not url:
        raise SystemExit("Defina a variável MONGO_URL antes de rodar (string de conexão do Mongo).")
    is_atlas = "mongodb+srv" in url or "mongodb.net" in url
    if is_atlas:
        client = AsyncIOMotorClient(url, tls=True, serverSelectionTimeoutMS=30000,
                                    connectTimeoutMS=30000, socketTimeoutMS=30000)
    else:
        client = AsyncIOMotorClient(url)
    db = client[os.environ.get("DB_NAME", "railway")]

    existe = await db.incra_tabelas.find_one(
        {"regiao": EXEMPLO["regiao"], "vigencia": EXEMPLO["vigencia"]}
    )
    if existe:
        print("Tabela INCRA de exemplo já existe — nada a fazer.")
    else:
        await db.incra_tabelas.insert_one(EXEMPLO)
        print("OK — tabela INCRA de EXEMPLO inserida:")
        print(f"   {EXEMPLO['regiao']} · {EXEMPLO['municipio']} · {EXEMPLO['vigencia']}")
        print(f"   {len(EXEMPLO['faixas'])} faixas (R$/ha). Abra um laudo rural para ver a seção.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
