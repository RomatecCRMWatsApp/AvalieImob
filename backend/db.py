# @module db — Conexão MongoDB compartilhada com injeção de dependência FastAPI
import os
from motor.motor_asyncio import AsyncIOMotorClient

_client: AsyncIOMotorClient = None
_db = None


def init_db():
    global _client, _db
    mongo_url = os.environ["MONGO_URL"]
    is_atlas = "mongodb+srv" in mongo_url or "mongodb.net" in mongo_url
    if is_atlas:
        _client = AsyncIOMotorClient(
            mongo_url,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
        )
    else:
        _client = AsyncIOMotorClient(mongo_url)
    db_name = os.environ.get("DB_NAME", "railway")
    _db = _client[db_name]


async def setup_indexes():
    """Cria índices necessários para o versionamento de PTAM."""
    if _db is None:
        return
    # Índices para ptam_versions
    await _db.ptam_versions.create_index([("ptam_id", 1), ("numero_versao", -1)])
    await _db.ptam_versions.create_index([("ptam_id", 1), ("tipo", 1)])
    await _db.ptam_versions.create_index([("ptam_id", 1), ("created_at", -1)])


def get_client() -> AsyncIOMotorClient:
    return _client


def get_db():
    return _db


async def close_db():
    if _client:
        _client.close()
