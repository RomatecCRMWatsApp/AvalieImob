# @module routes.galeria — Galeria de fotos própria do AvalieImob (com overlay GPS/UTM).
"""
Galeria de fotos do AvalieImob (clone do padrão ZAYRA): a foto já vem com o
overlay técnico (GPS/UTM/endereço/data/logo) renderizado no canvas do frontend.
Aqui só persistimos a imagem final + metadados, listamos e removemos.

Storage: db.images com flag galeria=True (mesma collection das fotos do laudo,
servidas por /api/upload/image/{id}). Numeração sequencial por usuário.
"""
import base64
import logging
import uuid as _uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from services.upload_security import detect_content_type

router = APIRouter(prefix="/galeria", tags=["galeria"])
logger = logging.getLogger("romatec")

_MAX_BYTES = 12 * 1024 * 1024  # 12 MB (foto com overlay)


async def _next_numero(db, uid: str) -> int:
    res = await db.counters.find_one_and_update(
        {"_id": f"galeria_{uid}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(res["seq"])


@router.get("")
async def listar_galeria(
    limit: int = 200,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lista as fotos da galeria do usuário (mais recentes primeiro)."""
    cur = db.images.find(
        {"user_id": uid, "galeria": True},
        {"data_b64": 0},  # não trafega o base64 na listagem
    ).sort("created_at", -1).limit(min(int(limit or 200), 500))
    fotos = []
    async for d in cur:
        fotos.append({
            "id": d.get("id"),
            "numero": d.get("numero"),
            "url": f"/api/upload/image/{d.get('id')}",
            "latitude": d.get("latitude"),
            "longitude": d.get("longitude"),
            "altitude": d.get("altitude"),
            "utm": d.get("utm"),
            "endereco": d.get("endereco"),
            "data_hora": d.get("meta_data_hora") or (d.get("created_at").isoformat() if d.get("created_at") else None),
            "legenda": d.get("legenda") or "",
        })
    return {"fotos": fotos, "total": len(fotos)}


@router.post("/foto")
async def salvar_foto(
    file: UploadFile = File(...),
    latitude: str = Form(""),
    longitude: str = Form(""),
    altitude: str = Form(""),
    utm: str = Form(""),
    endereco: str = Form(""),
    legenda: str = Form(""),
    data_hora: str = Form(""),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Salva uma foto da galeria (já com overlay aplicado no frontend)."""
    raw = await file.read()
    if not raw:
        raise HTTPException(422, "Arquivo vazio.")
    if len(raw) > _MAX_BYTES:
        raise HTTPException(422, f"Foto excede {_MAX_BYTES // (1024*1024)} MB.")

    ctype = detect_content_type(raw)
    if ctype not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(422, f"Tipo inválido ({ctype}). Envie JPG/PNG/WebP.")

    def _f(v):
        try:
            return float(str(v).replace(",", ".")) if str(v).strip() != "" else None
        except ValueError:
            return None

    numero = await _next_numero(db, uid)
    image_id = str(_uuid.uuid4())
    gps_str = ""
    lat_f, lon_f = _f(latitude), _f(longitude)
    if lat_f is not None and lon_f is not None:
        gps_str = f"{lat_f:.6f}, {lon_f:.6f}"

    await db.images.insert_one({
        "id": image_id,
        "user_id": uid,
        "galeria": True,
        "numero": numero,
        "filename": f"galeria_{numero}.jpg",
        "content_type": ctype,
        "data_b64": base64.b64encode(raw).decode("utf-8"),
        "size_bytes": len(raw),
        "latitude": lat_f,
        "longitude": lon_f,
        "altitude": _f(altitude),
        "utm": utm.strip() or None,
        "endereco": endereco.strip() or None,
        "legenda": legenda.strip() or None,
        "meta_gps": gps_str,
        "meta_data_hora": data_hora.strip() or datetime.utcnow().isoformat(),
        "meta_ocr_done": True,
        "origem": "galeria_avalieimob",
        "created_at": datetime.utcnow(),
    })

    return {
        "id": image_id,
        "numero": numero,
        "url": f"/api/upload/image/{image_id}",
    }


@router.delete("/foto/{image_id}")
async def remover_foto(
    image_id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    res = await db.images.delete_one({"id": image_id, "user_id": uid, "galeria": True})
    if res.deleted_count == 0:
        raise HTTPException(404, "Foto não encontrada")
    return {"ok": True}
