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
    """Cria índices necessários para o versionamento de PTAM e cache CUB."""
    if _db is None:
        return
    # Índices para ptam_versions
    await _db.ptam_versions.create_index([("ptam_id", 1), ("numero_versao", -1)])
    await _db.ptam_versions.create_index([("ptam_id", 1), ("tipo", 1)])
    await _db.ptam_versions.create_index([("ptam_id", 1), ("created_at", -1)])
    # Índices para cub_cache (TTL 30 dias)
    await _db.cub_cache.create_index("chave", unique=True)
    await _db.cub_cache.create_index("criado_em", expireAfterSeconds=2592000)
    # Índices para zonas_planodiretor
    await _db.zonas_planodiretor.create_index([("user_id", 1), ("municipio", 1), ("codigo", 1)])
    # Índices para contratos
    await _db.contratos.create_index([("user_id", 1), ("updated_at", -1)])
    await _db.contratos.create_index([("user_id", 1), ("status", 1)])
    await _db.contratos.create_index("link_publico_token", sparse=True)
    # Índices para contrato_versions
    await _db.contrato_versions.create_index([("contrato_id", 1), ("numero_versao", -1)])
    # Índice único do white-label por usuário (tenant_branding)
    from services.branding_repository import ensure_indexes as _branding_indexes
    await _branding_indexes(_db)

    # Auditoria do link público do laudo (controle de envios/visualizações)
    await _db.ptam_link_eventos.create_index([("ptam_id", 1), ("created_at", -1)])
    await _db.ptam_link_eventos.create_index([("user_id", 1), ("created_at", -1)])

    # Banco Global de Amostras de Mercado v2
    await _db.amostras_mercado.create_index([("user_id", 1), ("categoria", 1), ("municipio", 1), ("data_coleta", -1)])
    await _db.amostras_mercado.create_index([("user_id", 1), ("ptam_origem_id", 1), ("referencia", 1)])
    await _db.amostras_mercado.create_index([("user_id", 1), ("tipo_imovel", 1), ("ativo", 1)])
    await _db.amostras_mercado.create_index([("user_id", 1), ("rs_m2_calculado", 1)])
    await _db.amostras_mercado.create_index([("user_id", 1), ("rs_ha_calculado", 1)])
    await _db.amostras_mercado.create_index("id", sparse=True)

    # Conformidade COFECI/CNAI (Feature 05)
    await _db.credenciais.create_index([("user_id", 1), ("ativo", 1)])
    await _db.alertas_conformidade.create_index([("user_id", 1), ("lido", 1)])
    await _db.alertas_conformidade.create_index([("user_id", 1), ("created_at", -1)])
    await _db.config_conformidade.create_index("user_id", unique=True)


def get_client() -> AsyncIOMotorClient:
    return _client


def get_db():
    return _db


async def close_db():
    if _client:
        _client.close()
