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
    "regiao": "MRT Pré-Amazônico — Polo Imperatriz/Açailândia",
    "municipio": "Açailândia",
    "ano": 2022,
    "mes": 7,
    "vigencia": "RAMT-MA 2022",
    "fonte": "INCRA/SR-21-MA — RAMT-MA 2022 (VTI R$/ha — atualizar por IPCA-E)",
    "faixas": [
        {"faixa": "Pastagem formada — cap. alta (pecuária bovina)", "vr_min": 11230.0, "vr_max": 20857.0, "vr_medio": 16044.0},
        {"faixa": "Pastagem nativa/formada — cap. baixa (pecuária extensiva)", "vr_min": 6961.0, "vr_max": 12927.0, "vr_medio": 9944.0},
        {"faixa": "Vegetação nativa — floresta amazônica/transição/capoeira", "vr_min": 2640.0, "vr_max": 4903.0, "vr_medio": 3771.0},
        {"faixa": "Uso indefinido / misto (geral MRT-1)", "vr_min": 1800.0, "vr_max": 250000.0, "vr_medio": 11360.0},
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
