# @module routes.documentos_assinatura — Assinatura de PDFs AVULSOS com ICP-Brasil.
# O usuário sobe um PDF qualquer (ART, TRT, ofício, etc.) e assina POSICIONANDO o carimbo,
# reusando o fluxo ICP existente (routes/assinatura: tipo="documento"). O PDF vai p/ o R2;
# o assinado fica em assinaturas_pdf (keyed por doc_tipo="documento"). Isolado por user_id.
from __future__ import annotations

import asyncio
import io
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from services import r2_storage
from services.upload_security import detect_content_type, normalize_filename

router = APIRouter(prefix="/documentos", tags=["documentos-assinatura"])
logger = logging.getLogger("romatec")

COL = "documentos_assinatura"
_MAX_BYTES = 25 * 1024 * 1024  # 25 MB


def _contar_paginas(pdf_bytes: bytes) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception:
        return 0


@router.post("/upload")
async def upload_documento(
    file: UploadFile = File(..., description="PDF para assinar (máx 25 MB)"),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Recebe um PDF, sobe no R2 e cria o registro p/ assinatura ICP."""
    conteudo = await file.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(conteudo) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo excede 25 MB ({len(conteudo)/1024/1024:.1f} MB).")
    if detect_content_type(conteudo) != "application/pdf" or not conteudo.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF válido.")

    doc_id = uuid.uuid4().hex
    nome = normalize_filename(file.filename, fallback="documento")
    if not nome.lower().endswith(".pdf"):
        nome = f"{nome}.pdf"
    pdf_key = f"documentos/{uid}/{doc_id}.pdf"
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, conteudo, pdf_key, "application/pdf", "private, max-age=0")
    except Exception as e:  # noqa: BLE001
        logger.error("Falha ao subir documento ao R2: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao armazenar o documento.")

    reg = {
        "id": doc_id, "user_id": uid, "nome": nome, "pdf_key": pdf_key,
        "tamanho": len(conteudo), "paginas": _contar_paginas(conteudo),
        "icp_status": None, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    }
    await db[COL].insert_one(reg)
    return serialize_doc(reg)


@router.get("")
async def listar_documentos(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    docs = await db[COL].find({"user_id": uid}).sort("created_at", -1).to_list(length=500)
    return [serialize_doc(d) for d in docs]


@router.get("/{doc_id}")
async def obter_documento(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db[COL].find_one({"id": doc_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return serialize_doc(doc)


@router.get("/{doc_id}/pdf")
async def baixar_original(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Serve o PDF ORIGINAL (não assinado) — para visualizar antes de assinar."""
    doc = await db[COL].find_one({"id": doc_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    try:
        pdf = await asyncio.to_thread(r2_storage.download_bytes, doc["pdf_key"])
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo indisponível.")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{doc.get("nome", "documento.pdf")}"',
                             "Cache-Control": "no-store"})


@router.delete("/{doc_id}")
async def excluir_documento(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db[COL].find_one({"id": doc_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    try:
        await asyncio.to_thread(r2_storage.delete_object, doc["pdf_key"])
    except Exception:
        pass
    await db[COL].delete_one({"id": doc_id, "user_id": uid})
    # remove também o assinado, se houver
    try:
        await db["assinaturas_pdf"].delete_many({"doc_tipo": "documento", "doc_id": doc_id})
    except Exception:
        pass
    return {"ok": True}
