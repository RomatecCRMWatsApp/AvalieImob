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
        for i, foto in enumerate(fotos_imovel):
            # Extrair image_id da URL (formato: /api/upload/image/abc-123 ou abc-123)
            if isinstance(foto, str):
                url = foto
            elif isinstance(foto, dict):
                url = foto.get("url") or foto.get("image_id", "")
            else:
                continue
            
            parts = str(url).replace('/api/upload/image/', '').split('/')
            image_id = parts[-1] if parts else str(url)
            
            # Validar se parece um UUID
            if len(image_id) > 30 and '-' in image_id:
                img_doc = await db.images.find_one({"id": image_id})
                if img_doc and img_doc.get("data_b64"):
                    import base64
                    # Substituir URL por dict com dados da imagem
                    fotos_imovel[i] = {
                        "image_id": image_id,
                        "url": url,
                        "_image_bytes": base64.b64decode(img_doc["data_b64"]),
                        "caption": f"Foto {i+1}"
                    }
        
        # Buscar documentos digitalizados (certidões)
        docs = doc.get("fotos_documentos") or []
        docs_processados = []
        for i, doc_item in enumerate(docs):
            # Extrair doc_id da URL ou do objeto
            if isinstance(doc_item, str):
                url = doc_item
            elif isinstance(doc_item, dict):
                url = doc_item.get("url") or doc_item.get("doc_id") or doc_item.get("image_id", "")
            else:
                continue
            
            parts = str(url).replace('/api/upload/image/', '').split('/')
            doc_id = parts[-1] if parts else str(url)
            
            # Validar se parece um UUID
            if len(doc_id) > 30 and '-' in doc_id:
                doc_doc = await db.images.find_one({"id": doc_id})
                if doc_doc and doc_doc.get("data_b64"):
                    import base64
                    # Criar dict com dados do documento
                    docs_processados.append({
                        "doc_id": doc_id,
                        "url": url,
                        "_doc_bytes": base64.b64decode(doc_doc["data_b64"]),
                        "name": doc_doc.get("filename") or f"Documento {i+1}",
                        "content_type": doc_doc.get("content_type", "application/pdf")
                    })
                else:
                    # Manter original se não encontrar no banco
                    docs_processados.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
            else:
                docs_processados.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
        
        # Atualizar o doc com os documentos processados
        doc["fotos_documentos"] = docs_processados
        
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
            # Extrair image_id da URL (formato: /api/upload/image/abc-123 ou abc-123)
            if isinstance(foto, str):
                url = foto
            elif isinstance(foto, dict):
                url = foto.get("url") or foto.get("image_id", "")
            else:
                continue
            
            parts = str(url).replace('/api/upload/image/', '').split('/')
            image_id = parts[-1] if parts else str(url)
            
            # Validar se parece um UUID
            if len(image_id) > 30 and '-' in image_id:
                logger.info(f"  Buscando imagem {i}: {image_id}")
                img_doc = await db.images.find_one({"id": image_id})
                if img_doc and img_doc.get("data_b64"):
                    import base64
                    # Substituir URL por dict com dados da imagem
                    fotos_imovel[i] = {
                        "image_id": image_id,
                        "url": url,
                        "_image_bytes": base64.b64decode(img_doc["data_b64"]),
                        "caption": f"Foto {i+1}"
                    }
                    logger.info(f"  Imagem {i}: {len(fotos_imovel[i]['_image_bytes'])} bytes carregados")
                else:
                    logger.warning(f"  Imagem {i}: não encontrada no banco para id={image_id}")
            else:
                logger.warning(f"  Foto {i}: ID inválido: {image_id}")
        
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
