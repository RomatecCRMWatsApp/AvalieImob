# @module routes.uploads — Upload e recuperação de imagens/documentos em base64 no MongoDB
import asyncio
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
async def get_image(image_id: str, db=Depends(get_db)):
    # Servida SEM exigir o header Authorization: tags <img src="..."> do navegador
    # não enviam o Bearer token, então qualquer dependência de auth (HTTPBearer)
    # retornaria 403 e a imagem nunca carregaria. O UUID v4 é a própria credencial
    # (capability URL, não enumerável) — coerente com a geração de DOCX/PDF, que já
    # busca a imagem só por id, e com o compartilhamento público de PTAM.
    doc = await db.images.find_one({"id": image_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    try:
        raw = base64.b64decode(doc["data_b64"])
    except Exception:
        raise HTTPException(status_code=422, detail="Imagem corrompida")
    return Response(
        content=raw,
        media_type=doc.get("content_type", "image/jpeg"),
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.get("/upload/image/{image_id}/metadata")
async def image_metadata(image_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Extrai GPS e data/hora do EXIF da foto (quando presentes) para copiar."""
    doc = await db.images.find_one({"id": image_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    try:
        raw = base64.b64decode(doc["data_b64"])
    except Exception:
        raise HTTPException(status_code=422, detail="Imagem corrompida")
    fonte = ""
    try:
        from services.ptam_pdf_v2 import _exif_gps_data
        gps, data_hora = _exif_gps_data(raw)
        if gps or data_hora:
            fonte = "exif"
    except Exception:
        gps, data_hora = "", ""

    # Fallback: muitas fotos perdem o EXIF (WhatsApp etc.), mas tem o overlay
    # "queimado" com GPS/data. Le via OCR (Tesseract) em thread separada.
    if not gps and not data_hora:
        try:
            from services.foto_ocr import extrair_gps_data_ocr
            g2, d2 = await asyncio.to_thread(extrair_gps_data_ocr, raw)
            if g2 or d2:
                gps, data_hora, fonte = g2, d2, "ocr"
        except Exception:
            pass

    maps_url = ""
    if gps:
        import re as _re
        m = _re.match(r"\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", gps)
        if m:
            maps_url = f"https://www.google.com/maps?q={m.group(1)},{m.group(2)}"
    # Cacheia na imagem para o PDF reusar (sem reprocessar OCR).
    if gps or data_hora:
        try:
            await db.images.update_one(
                {"id": image_id},
                {"$set": {"meta_gps": gps, "meta_data_hora": data_hora}},
            )
        except Exception:
            pass

    partes = []
    if gps:
        partes.append(f"GPS: {gps}")
    if data_hora:
        partes.append(f"Data/Hora: {data_hora}")
    return {
        "gps": gps,
        "data_hora": data_hora,
        "maps_url": maps_url,
        "fonte": fonte,
        "tem_dados": bool(gps or data_hora),
        "texto_copia": "  |  ".join(partes),
    }


@router.delete("/upload/image/{image_id}")
async def delete_image(image_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.images.delete_one({"id": image_id, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return {"ok": True}
