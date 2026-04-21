# @module db — Conexão MongoDB compartilhada com injeção de dependência FastAPI
import os
from motor.motor_asyncio import AsyncIOMotorClient

_client: AsyncIOMotorClient = None
_db = None


def init_db():
    global _client, _db
    mongo_url = os.environ["MONGO_URL"]
    _client = AsyncIOMotorClient(mongo_url)
    _db = _client[os.environ["DB_NAME"]]


def get_client() -> AsyncIOMotorClient:
    return _client


def get_db():
    return _db


async def close_db():
    if _client:
        _client.close()
