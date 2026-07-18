# @module db — Conexão MongoDB compartilhada com injeção de dependência FastAPI
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("romatec")

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


# (coleção, chaves, kwargs) — chaves no formato aceito por create_index.
_INDICES = [
    # Versionamento de PTAM
    ("ptam_versions", [("ptam_id", 1), ("numero_versao", -1)], {}),
    ("ptam_versions", [("ptam_id", 1), ("tipo", 1)], {}),
    ("ptam_versions", [("ptam_id", 1), ("created_at", -1)], {}),
    # Cache CUB (TTL 30 dias)
    ("cub_cache", "chave", {"unique": True}),
    ("cub_cache", "criado_em", {"expireAfterSeconds": 2592000}),
    # Zonas do plano diretor
    ("zonas_planodiretor", [("user_id", 1), ("municipio", 1), ("codigo", 1)], {}),
    # Contratos
    ("contratos", [("user_id", 1), ("updated_at", -1)], {}),
    ("contratos", [("user_id", 1), ("status", 1)], {}),
    ("contratos", "link_publico_token", {"sparse": True}),
    ("contrato_versions", [("contrato_id", 1), ("numero_versao", -1)], {}),
    # Auditoria do link público do laudo
    ("ptam_link_eventos", [("ptam_id", 1), ("created_at", -1)], {}),
    ("ptam_link_eventos", [("user_id", 1), ("created_at", -1)], {}),
    # Banco Global de Amostras de Mercado v2
    ("amostras_mercado", [("user_id", 1), ("categoria", 1), ("municipio", 1), ("data_coleta", -1)], {}),
    ("amostras_mercado", [("user_id", 1), ("ptam_origem_id", 1), ("referencia", 1)], {}),
    ("amostras_mercado", [("user_id", 1), ("tipo_imovel", 1), ("ativo", 1)], {}),
    ("amostras_mercado", [("user_id", 1), ("rs_m2_calculado", 1)], {}),
    ("amostras_mercado", [("user_id", 1), ("rs_ha_calculado", 1)], {}),
    ("amostras_mercado", [("user_id", 1), ("assinatura", 1)], {}),
    ("amostras_mercado", "id", {"sparse": True}),
    # Cupons Promocionais (Kit de Captação)
    ("cupons", "id", {"unique": True, "sparse": True}),
    ("cupons", "codigo", {"unique": True, "sparse": True}),
    ("cupons", "slug_unico", {"unique": True, "sparse": True}),
    ("cupons", [("status", 1), ("validade", 1)], {}),
    ("cupons", "telefone_destinatario", {}),
    # Conformidade COFECI/CNAI (Feature 05)
    ("credenciais", [("user_id", 1), ("ativo", 1)], {}),
    ("alertas_conformidade", [("user_id", 1), ("lido", 1)], {}),
    ("alertas_conformidade", [("user_id", 1), ("created_at", -1)], {}),
    ("config_conformidade", "user_id", {"unique": True}),
]


async def setup_indexes():
    """Cria os índices de PTAM, cache CUB, contratos, amostras, cupons etc.

    RESILIENTE: cada índice é criado isoladamente. Antes era uma cadeia de
    `await` sem proteção — um único índice que falhasse (ex.: valor duplicado
    num `unique`) abortava a função e TODOS os índices seguintes deixavam de
    ser criados. Além disso a função não era chamada em lugar nenhum, então
    nenhum destes índices existia em produção.
    """
    if _db is None:
        return
    criados = 0
    for coll, chaves, kwargs in _INDICES:
        try:
            await _db[coll].create_index(chaves, **kwargs)
            criados += 1
        except Exception as e:
            logger.warning("Índice %s %s não criado: %s", coll, chaves, e)

    try:
        from services.branding_repository import ensure_indexes as _branding_indexes
        await _branding_indexes(_db)
    except Exception as e:
        logger.warning("Índices de branding não criados: %s", e)

    logger.info("setup_indexes: %s/%s índices garantidos", criados, len(_INDICES))


def get_client() -> AsyncIOMotorClient:
    return _client


def get_db():
    return _db


async def close_db():
    if _client:
        _client.close()
