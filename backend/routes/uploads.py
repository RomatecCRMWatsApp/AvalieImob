# @module routes.uploads — Upload e recuperação de imagens/documentos em base64 no MongoDB
import base64
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from db import get_db
from dependencies import get_active_subscriber
from services.upload_security import detect_content_type, normalize_filename

router = APIRouter(tags=["uploads"])
logger = logging.getLogger("romatec")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "application/pdf"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/upload/image")
async def upload_image(file: UploadFile = File(...), uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    declared_content_type = (file.content_type or "").lower()
    if declared_content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo não permitido: {declared_content_type}.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio não é permitido")
    if len(data) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande. Tamanho máximo: 5MB")
    detected_content_type = detect_content_type(data)
    if detected_content_type not in {"image/jpeg", "image/png", "image/webp", "application/pdf"}:
        raise HTTPException(status_code=400, detail="Conteúdo do arquivo inválido ou não suportado")
    if detected_content_type == "application/pdf" and declared_content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="PDF deve ser enviado com content type application/pdf")
    image_id = str(uuid.uuid4())
    doc = {
        "id": image_id,
        "user_id": uid,
        "filename": normalize_filename(file.filename),
        "content_type": detected_content_type,
        "data_b64": base64.b64encode(data).decode("utf-8"),
        "size_bytes": len(data),
        "created_at": datetime.utcnow(),
    }
    await db.images.insert_one(doc)
    logger.info("Image uploaded: id=%s user=%s size=%d", image_id, uid, len(data))
    return {"id": image_id, "url": f"/api/upload/image/{image_id}", "content_type": detected_content_type}


@router.get("/upload/image/{image_id}")
async def get_image(image_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.images.find_one({"id": image_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    raw = base64.b64decode(doc["data_b64"])
    return Response(content=raw, media_type=doc.get("content_type", "image/jpeg"))


@router.delete("/upload/image/{image_id}")
async def delete_image(image_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.images.delete_one({"id": image_id, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return {"ok": True}
