# @module services.image_store — armazenamento único das imagens/fotos de upload.
# Prioriza o Cloudflare R2 (só metadata leve no Mongo); cai para base64-no-Mongo
# quando o R2 não está configurado ou falha. A LEITURA resolve os dois formatos
# (r2_key novo OU data_b64 legado), então imagens antigas continuam abrindo.
#
# Motivo: gravar os bytes como base64 dentro do MongoDB estourou a quota do banco
# (Atlas M0 512 MB → "Writes are blocked"). Aqui os bytes vão para o R2 e o Mongo
# guarda apenas a referência (r2_key), mantendo o banco enxuto.
import asyncio
import base64
import logging
import os
import uuid
from datetime import datetime

from services import r2_storage

logger = logging.getLogger("romatec")

_EXT_POR_TIPO = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


def r2_ativo() -> bool:
    """True quando as credenciais do R2 estão presentes no ambiente."""
    return bool(
        os.getenv("R2_ENDPOINT")
        and os.getenv("R2_BUCKET")
        and os.getenv("R2_ACCESS_KEY")
        and os.getenv("R2_SECRET_KEY")
    )


async def salvar_imagem(db, uid, data, content_type, filename, image_id=None, extra=None):
    """Persiste uma imagem e devolve o doc gravado (com 'id').

    Sobe no R2 quando disponível (grava só 'r2_key'); senão grava 'data_b64'
    (comportamento legado). Nunca lança por causa do R2 — cai para base64.
    """
    image_id = image_id or str(uuid.uuid4())
    doc = {
        "id": image_id,
        "user_id": uid,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(data),
        "created_at": datetime.utcnow(),
    }
    if extra:
        doc.update(extra)

    if r2_ativo():
        ext = _EXT_POR_TIPO.get((content_type or "").lower(), "bin")
        key = f"images/{uid}/{image_id}.{ext}"
        try:
            await asyncio.to_thread(r2_storage.upload_bytes, data, key, content_type)
            doc["r2_key"] = key
        except Exception:
            logger.exception(
                "image_store: R2 falhou; gravando base64 no Mongo (fallback) id=%s", image_id
            )
            doc["data_b64"] = base64.b64encode(data).decode("utf-8")
    else:
        doc["data_b64"] = base64.b64encode(data).decode("utf-8")

    await db.images.insert_one(doc)
    return doc


async def bytes_do_doc(doc):
    """Resolve os bytes a partir de um doc de db.images já carregado.

    Prioriza o base64 legado (quando presente) e cai para o R2 via r2_key.
    Devolve None se o doc for vazio ou os bytes não puderem ser obtidos.
    """
    if not doc:
        return None
    b64 = doc.get("data_b64")
    if b64:
        try:
            return base64.b64decode(b64)
        except Exception:
            logger.warning("image_store: data_b64 corrompido id=%s", doc.get("id"))
            return None
    key = doc.get("r2_key")
    if key:
        try:
            return await asyncio.to_thread(r2_storage.download_bytes, key)
        except Exception:
            logger.exception("image_store: falha ao baixar do R2 key=%s", key)
            return None
    return None


async def find_one(db, filtro):
    """find_one em db.images garantindo que 'data_b64' esteja preenchido.

    Se o doc só tiver 'r2_key' (imagem nova, no R2), baixa os bytes e preenche
    'data_b64' no doc retornado. Assim os leitores legados que fazem
    `base64.b64decode(doc["data_b64"])` continuam funcionando SEM mudar a lógica
    deles — basta trocar `db.images.find_one(...)` por `image_store.find_one(db, ...)`.

    NÃO passe projeção que exclua 'data_b64'/'r2_key' aqui (esta função precisa
    dos dois). Para listagens que não querem os bytes, use db.images direto.
    """
    doc = await db.images.find_one(filtro)
    if doc and not doc.get("data_b64") and doc.get("r2_key"):
        raw = await bytes_do_doc(doc)
        if raw is not None:
            doc["data_b64"] = base64.b64encode(raw).decode("utf-8")
    return doc


async def carregar_bytes(db, image_id, uid=None):
    """Busca o doc por id (opcionalmente escopado por user_id) e resolve os bytes.

    Se escopado por uid e não achar, tenta sem o uid (imagens são servidas por
    UUID não-enumerável; vários fluxos leem imagens de outros escopos legítimos,
    ex.: link público, geração de PDF). Devolve None se não encontrar.
    """
    if not image_id:
        return None
    filtro = {"id": image_id}
    if uid is not None:
        filtro["user_id"] = uid
    doc = await db.images.find_one(filtro)
    if not doc and uid is not None:
        doc = await db.images.find_one({"id": image_id})
    return await bytes_do_doc(doc)


async def remover_imagem(db, image_id, uid=None):
    """Remove a imagem do R2 (se houver) e o doc do Mongo. True se removeu."""
    filtro = {"id": image_id}
    if uid is not None:
        filtro["user_id"] = uid
    doc = await db.images.find_one(filtro)
    if not doc:
        return False
    key = doc.get("r2_key")
    if key:
        try:
            await asyncio.to_thread(r2_storage.delete_object, key)
        except Exception:
            logger.warning(
                "image_store: falha ao remover do R2 key=%s (segue removendo do Mongo)", key
            )
    await db.images.delete_one({"id": image_id})
    return True
