# @module routes.tvi — CRUD do Kit TVI (Termo de Vistoria de Imóvel)
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.tvi import (
    VistoriaBase, Vistoria,
    VistoriaPhoto, VistoriaSignature, VistoriaShare,
    PhotoUploadRequest, SignatureRequest, VistoriaShareBase,
)

router = APIRouter(tags=["tvi"])
logger = logging.getLogger("romatec")


# ── Numeração automática TVI-XXXX/AAAA ─────────────────────────────────────
async def _next_tvi_numero(db) -> str:
    ano = datetime.utcnow().year
    result = await db.counters.find_one_and_update(
        {"_id": f"tvi_numero_{ano}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"TVI-{result['seq']:04d}/{ano}"


# ── Modelos de formulário ───────────────────────────────────────────────────
@router.get("/tvi/models")
async def list_tvi_models(
    categoria: Optional[str] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lista todos os modelos TVI, agrupados por categoria."""
    query: dict = {"ativo": True}
    if categoria:
        query["categoria"] = categoria
    docs = await db.vistoria_models.find(query).sort("categoria", 1).to_list(200)
    for d in docs:
        d.pop("_id", None)
    # Agrupa por categoria
    grouped: dict = {}
    for d in docs:
        cat = d.get("categoria", "OUTROS")
        grouped.setdefault(cat, []).append(d)
    return {"categorias": grouped, "total": len(docs)}


@router.get("/tvi/models/{model_id}")
async def get_tvi_model(
    model_id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Retorna modelo com campos (inclui campos_especificos)."""
    doc = await db.vistoria_models.find_one({"id": model_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Modelo TVI não encontrado")
    doc.pop("_id", None)
    return doc


# ── Vistorias ───────────────────────────────────────────────────────────────
@router.post("/tvi/vistoria", response_model=Vistoria, status_code=201)
async def create_vistoria(
    data: VistoriaBase,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    numero = await _next_tvi_numero(db)
    payload = data.model_dump()
    payload["numero_tvi"] = numero
    v = Vistoria(user_id=uid, **payload)
    await db.vistorias.insert_one(v.model_dump())
    return v


@router.get("/tvi/vistorias")
async def list_vistorias(
    status: Optional[str] = None,
    model_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    query: dict = {"user_id": uid}
    if status:
        query["status"] = status
    if model_id:
        query["model_id"] = model_id
    cursor = db.vistorias.find(query).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    total = await db.vistorias.count_documents(query)
    return {"items": docs, "total": total, "skip": skip, "limit": limit}


@router.get("/tvi/vistoria/{vid}", response_model=Vistoria)
async def get_vistoria(
    vid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.vistorias.find_one({"id": vid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Vistoria não encontrada")
    return Vistoria(**serialize_doc(doc))


@router.put("/tvi/vistoria/{vid}", response_model=Vistoria)
async def update_vistoria(
    vid: str,
    data: VistoriaBase,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.vistorias.find_one({"id": vid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Vistoria não encontrada")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    # Preserva número
    if doc.get("numero_tvi") and not updates.get("numero_tvi"):
        updates["numero_tvi"] = doc["numero_tvi"]
    await db.vistorias.update_one({"id": vid}, {"$set": updates})
    new_doc = await db.vistorias.find_one({"id": vid})
    return Vistoria(**serialize_doc(new_doc))


@router.delete("/tvi/vistoria/{vid}")
async def delete_vistoria(
    vid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    res = await db.vistorias.delete_one({"id": vid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vistoria não encontrada")
    # Remove documentos relacionados
    await db.vistoria_photos.delete_many({"vistoria_id": vid})
    await db.vistoria_signatures.delete_many({"vistoria_id": vid})
    return {"ok": True}


# ── Fotos ───────────────────────────────────────────────────────────────────
@router.post("/tvi/vistoria/{vid}/photos", response_model=VistoriaPhoto, status_code=201)
async def add_photo(
    vid: str,
    data: PhotoUploadRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.vistorias.find_one({"id": vid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Vistoria não encontrada")
    photo = VistoriaPhoto(vistoria_id=vid, url=data.url, ambiente=data.ambiente, legenda=data.legenda)
    await db.vistoria_photos.insert_one(photo.model_dump())
    return photo


@router.get("/tvi/vistoria/{vid}/photos", response_model=List[VistoriaPhoto])
async def list_photos(
    vid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.vistorias.find_one({"id": vid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Vistoria não encontrada")
    photos = await db.vistoria_photos.find({"vistoria_id": vid}).to_list(500)
    return [VistoriaPhoto(**serialize_doc(p)) for p in photos]


# ── Assinatura ──────────────────────────────────────────────────────────────
@router.post("/tvi/vistoria/{vid}/signature", response_model=VistoriaSignature, status_code=201)
async def save_signature(
    vid: str,
    data: SignatureRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.vistorias.find_one({"id": vid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Vistoria não encontrada")
    sig = VistoriaSignature(
        vistoria_id=vid,
        data_b64=data.data_b64,
        signatario=data.signatario,
        cargo=data.cargo,
    )
    await db.vistoria_signatures.insert_one(sig.model_dump())
    return sig


@router.get("/tvi/vistoria/{vid}/signatures", response_model=List[VistoriaSignature])
async def list_signatures(
    vid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.vistorias.find_one({"id": vid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Vistoria não encontrada")
    sigs = await db.vistoria_signatures.find({"vistoria_id": vid}).to_list(50)
    return [VistoriaSignature(**serialize_doc(s)) for s in sigs]


# ── Compartilhamento ────────────────────────────────────────────────────────
@router.post("/tvi/vistoria/{vid}/share", response_model=VistoriaShare, status_code=201)
async def share_vistoria(
    vid: str,
    data: VistoriaShareBase,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.vistorias.find_one({"id": vid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Vistoria não encontrada")
    if data.canal not in ("email", "whatsapp"):
        raise HTTPException(status_code=400, detail="Canal deve ser 'email' ou 'whatsapp'")
    share = VistoriaShare(**data.model_dump())
    await db.vistoria_shares.insert_one(share.model_dump())
    logger.info("TVI %s compartilhada via %s para %s", vid, data.canal, data.destinatario)
    return share
