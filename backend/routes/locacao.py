# @module routes.locacao — CRUD de Avaliações de Locação e download de PDF
import io
import logging
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from db import get_db
from services.auth_service import get_current_user_id
from models import LocacaoBase
from locacao_pdf import generate_locacao_pdf
from locacao_docx import generate_locacao_docx

router = APIRouter(tags=["locacao"])
logger = logging.getLogger("romatec")


async def _next_locacao_number(db) -> str:
    year = datetime.utcnow().year
    counter_doc = await db.counters.find_one_and_update(
        {"_id": f"locacao_numero_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = counter_doc.get("seq", 1)
    return f"LOC-{seq:04d}/{year}"


@router.post("/locacao", status_code=201)
async def create_locacao(body: LocacaoBase, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    now = datetime.utcnow()
    data = body.model_dump(mode="json")
    data["id"] = str(uuid.uuid4())
    data["user_id"] = uid
    data["created_at"] = now
    data["updated_at"] = now
    if not data.get("numero_locacao"):
        data["numero_locacao"] = await _next_locacao_number(db)
    await db.locacoes.insert_one(data)
    data.pop("_id", None)
    return data


@router.get("/locacao")
async def list_locacoes(
    uid: str = Depends(get_current_user_id),
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_db),
):
    query: dict = {"user_id": uid}
    if tipo:
        query["tipo_locacao"] = tipo
    if status:
        query["status"] = status
    cursor = db.locacoes.find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    total = await db.locacoes.count_documents(query)
    return {"items": docs, "total": total, "skip": skip, "limit": limit}


@router.get("/locacao/{locacao_id}")
async def get_locacao(locacao_id: str, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    doc = await db.locacoes.find_one({"id": locacao_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Avaliação de locação não encontrada")
    doc.pop("_id", None)
    return doc


@router.put("/locacao/{locacao_id}")
async def update_locacao(locacao_id: str, body: LocacaoBase, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    doc = await db.locacoes.find_one({"id": locacao_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Avaliação de locação não encontrada")
    data = body.model_dump(mode="json")
    data["updated_at"] = datetime.utcnow()
    if doc.get("numero_locacao") and not data.get("numero_locacao"):
        data["numero_locacao"] = doc["numero_locacao"]
    await db.locacoes.update_one({"id": locacao_id, "user_id": uid}, {"$set": data})
    updated = await db.locacoes.find_one({"id": locacao_id, "user_id": uid})
    updated.pop("_id", None)
    return updated


@router.delete("/locacao/{locacao_id}", status_code=204)
async def delete_locacao(locacao_id: str, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    result = await db.locacoes.delete_one({"id": locacao_id, "user_id": uid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Avaliação de locação não encontrada")


@router.get("/locacao/{locacao_id}/pdf")
async def download_locacao_pdf(locacao_id: str, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    doc = await db.locacoes.find_one({"id": locacao_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Avaliação de locação não encontrada")
    doc.pop("_id", None)
    user = await db.users.find_one({"id": uid})
    if user:
        user.pop("_id", None)
    try:
        # Buscar imagens do banco antes de gerar PDF
        fotos_imovel = doc.get("fotos_imovel") or []
        for foto in fotos_imovel:
            if isinstance(foto, dict) and foto.get("image_id"):
                img_doc = await db.images.find_one({"id": foto["image_id"]})
                if img_doc and img_doc.get("data_b64"):
                    import base64
                    foto["_image_bytes"] = base64.b64decode(img_doc["data_b64"])
        
        pdf_bytes = generate_locacao_pdf(doc, user)
    except Exception as e:
        logger.exception("Erro ao gerar PDF de locação")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)[:200]}")
    if not pdf_bytes or len(pdf_bytes) < 100:
        raise HTTPException(status_code=500, detail="PDF gerado vazio")
    numero = doc.get("numero_locacao") or locacao_id
    filename = f"avaliacao_locacao_{numero.replace('/', '-')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "Cache-Control": "no-store",
        },
    )


@router.get("/locacao/{locacao_id}/docx")
async def download_locacao_docx(locacao_id: str, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    """Gera e retorna a Avaliação de Locação em DOCX (Word)."""
    doc = await db.locacoes.find_one({"id": locacao_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Avaliação de locação não encontrada")
    doc.pop("_id", None)
    user = await db.users.find_one({"id": uid})
    if user:
        user.pop("_id", None)
    try:
        # Buscar imagens do banco antes de gerar DOCX
        fotos_imovel = doc.get("fotos_imovel") or []
        logger.info(f"DOCX Locação {locacao_id}: {len(fotos_imovel)} fotos encontradas")
        for i, foto in enumerate(fotos_imovel):
            image_id = None
            
            # Novo formato: objeto com image_id
            if isinstance(foto, dict) and foto.get("image_id"):
                image_id = foto["image_id"]
                logger.info(f"  Foto {i}: formato novo — image_id={image_id}")
            # Formato legado: string URL
            elif isinstance(foto, str):
                # Extrair image_id da URL (ex: /api/upload/image/abc-123 ou abc-123)
                parts = foto.replace('/api/upload/image/', '').split('/')
                potential_id = parts[-1] if parts else foto
                # Validar se parece um UUID
                if len(potential_id) > 30 and '-' in potential_id:
                    image_id = potential_id
                    logger.info(f"  Foto {i}: formato legado (string) — extraído image_id={image_id}")
                else:
                    logger.warning(f"  Foto {i}: formato legado sem UUID válido: {foto}")
            else:
                logger.warning(f"  Foto {i}: formato inválido: {type(foto)}")
                continue
            
            if image_id:
                img_doc = await db.images.find_one({"id": image_id})
                if img_doc and img_doc.get("data_b64"):
                    import base64
                    # Se for dict, adicionar _image_bytes; se for string, converter para dict
                    if isinstance(foto, dict):
                        foto["_image_bytes"] = base64.b64decode(img_doc["data_b64"])
                    else:
                        # Substituir string por dict com todos os dados
                        fotos_imovel[i] = {
                            "image_id": image_id,
                            "url": foto if isinstance(foto, str) else None,
                            "_image_bytes": base64.b64decode(img_doc["data_b64"]),
                            "caption": f"Foto {i+1}"
                        }
                    logger.info(f"  Imagem {i}: {len(base64.b64decode(img_doc['data_b64']))} bytes carregados")
                else:
                    logger.warning(f"  Imagem {i}: não encontrada no banco para id={image_id}")
        
        docx_bytes = generate_locacao_docx(doc, user)
        logger.info(f"DOCX Locação {locacao_id}: gerado com sucesso — {len(docx_bytes)} bytes")
    except Exception as e:
        logger.exception(f"Erro ao gerar DOCX de locação {locacao_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar DOCX: {str(e)[:200]}")
    if not docx_bytes or len(docx_bytes) < 100:
        raise HTTPException(status_code=500, detail="DOCX gerado vazio")
    numero = doc.get("numero_locacao") or locacao_id
    filename = f"avaliacao_locacao_{numero.replace('/', '-')}.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(docx_bytes)),
            "Cache-Control": "no-store",
        },
    )
