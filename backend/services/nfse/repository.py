# @module services.nfse.repository — Acesso Mongo do módulo NFS-e (config, documentos, contador).
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument

COL_CONFIG = "nfse_config"
COL_DOCS = "nfse_documentos"


async def proximo_numero_dps(db, config_id: str, serie: str) -> int:
    """Número sequencial e SEM buracos da DPS por (município/config + série).
    Incremento atômico ($inc + upsert) — seguro sob emissões concorrentes."""
    counter_id = f"dps_{config_id}_{serie}"
    res = await db.counters.find_one_and_update(
        {"_id": counter_id},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(res["seq"])


# ── Config ───────────────────────────────────────────────────────────────────
async def criar_config(db, doc: dict) -> dict:
    await db[COL_CONFIG].insert_one(doc)
    return doc


async def listar_configs(db) -> list:
    return [c async for c in db[COL_CONFIG].find({}).sort("municipio_nome", 1)]


async def obter_config(db, config_id: str) -> Optional[dict]:
    return await db[COL_CONFIG].find_one({"id": config_id})


async def config_por_municipio(db, codigo_ibge: str) -> Optional[dict]:
    return await db[COL_CONFIG].find_one({"codigo_ibge": codigo_ibge, "ativo": True})


async def atualizar_config(db, config_id: str, patch: dict) -> Optional[dict]:
    patch = {**patch, "updated_at": datetime.now(timezone.utc)}
    return await db[COL_CONFIG].find_one_and_update(
        {"id": config_id}, {"$set": patch}, return_document=ReturnDocument.AFTER)


# ── Documentos ───────────────────────────────────────────────────────────────
async def criar_documento(db, doc: dict) -> dict:
    await db[COL_DOCS].insert_one(doc)
    return doc


async def obter_documento(db, doc_id: str) -> Optional[dict]:
    return await db[COL_DOCS].find_one({"id": doc_id})


async def atualizar_documento(db, doc_id: str, patch: dict) -> Optional[dict]:
    patch = {**patch, "updated_at": datetime.now(timezone.utc)}
    return await db[COL_DOCS].find_one_and_update(
        {"id": doc_id}, {"$set": patch}, return_document=ReturnDocument.AFTER)


async def listar_documentos(db, filtro: dict, skip: int = 0, limit: int = 50) -> list:
    cursor = db[COL_DOCS].find(filtro).sort("created_at", -1).skip(skip).limit(limit)
    return [d async for d in cursor]
