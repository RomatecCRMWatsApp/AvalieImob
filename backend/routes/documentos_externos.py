# @module routes.documentos_externos — Documentos Externos (doc-ext): upload de PDF arbitrário,
# N signatários, posicionar, enviar por WhatsApp, ICP opcional do RT. Isolado por user_id.
import asyncio
import hashlib
import io
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.documento_externo import novo_signatario, recalcular_status
from services import r2_storage
from services.documento_externo_service import COL, proximo_codigo
from services.upload_security import detect_content_type, normalize_filename

router = APIRouter(prefix="/documentos-externos", tags=["documentos-externos"])
logger = logging.getLogger("romatec")
_MAX_BYTES = 25 * 1024 * 1024


def _contar_paginas(pdf_bytes: bytes) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception:
        return 0


async def _carregar(db, doc_id: str, uid: str) -> dict:
    doc = await db[COL].find_one({"id": doc_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return doc


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    titulo: str = Form(...),
    descricao: str = Form(""),
    requer_icp_rt: bool = Form(True),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
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
    pdf_key = f"documentos-externos/{uid}/{doc_id}.pdf"
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, conteudo, pdf_key, "application/pdf", "private, max-age=0")
    except Exception as e:  # noqa: BLE001
        logger.error("Falha ao subir doc-ext ao R2: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao armazenar o documento.")

    reg = {
        "id": doc_id, "user_id": uid, "codigo": await proximo_codigo(db),
        "titulo": titulo.strip() or nome, "descricao": (descricao or "").strip() or None,
        "requer_icp_rt": bool(requer_icp_rt),
        "pdf_key": pdf_key, "pdf_hash_sha256": hashlib.sha256(conteudo).hexdigest(),
        "nome_arquivo": nome, "paginas": _contar_paginas(conteudo), "tamanho": len(conteudo),
        "signatarios": [], "pdf_key_intermediario": None, "pdf_key_final": None,
        "status": "rascunho", "historico": [{"em": datetime.utcnow(), "tipo": "criado"}],
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    }
    await db[COL].insert_one(reg)
    return serialize_doc(reg)


@router.get("")
async def listar(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    docs = await db[COL].find({"user_id": uid}).sort("created_at", -1).to_list(length=500)
    return [serialize_doc(d) for d in docs]


@router.get("/{doc_id}")
async def obter(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return serialize_doc(await _carregar(db, doc_id, uid))


@router.patch("/{doc_id}")
async def editar(doc_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _carregar(db, doc_id, uid)
    campos = {k: payload[k] for k in ("titulo", "descricao", "requer_icp_rt", "valor_referencia") if k in payload}
    campos["updated_at"] = datetime.utcnow()
    await db[COL].update_one({"id": doc_id, "user_id": uid}, {"$set": campos})
    return serialize_doc(await _carregar(db, doc_id, uid))


@router.delete("/{doc_id}")
async def excluir(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    for key in (doc.get("pdf_key"), doc.get("pdf_key_intermediario"), doc.get("pdf_key_final")):
        if key:
            try:
                await asyncio.to_thread(r2_storage.delete_object, key)
            except Exception:
                pass
    await db[COL].delete_one({"id": doc_id, "user_id": uid})
    try:
        await db["assinaturas_pdf"].delete_many({"doc_tipo": "doc-ext", "doc_id": doc_id})
    except Exception:
        pass
    return {"ok": True}


# ── PDFs ──────────────────────────────────────────────────────────────────────
async def _servir_pdf(db, doc_id: str, uid: str, campo: str, nome: str):
    doc = await _carregar(db, doc_id, uid)
    key = doc.get(campo) or doc.get("pdf_key")
    try:
        pdf = await asyncio.to_thread(r2_storage.download_bytes, key)
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo indisponível.")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nome}"', "Cache-Control": "no-store"})


@router.get("/{doc_id}/pdf-original")
async def pdf_original(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await _servir_pdf(db, doc_id, uid, "pdf_key", "documento.pdf")


@router.get("/{doc_id}/pdf-intermediario")
async def pdf_intermediario(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await _servir_pdf(db, doc_id, uid, "pdf_key_intermediario", "documento_clientes.pdf")


@router.get("/{doc_id}/pdf-final")
async def pdf_final(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Serve o PDF ASSINADO ICP se houver; senão o intermediário; senão o original."""
    from routes.assinatura import _load_assinatura_bytes
    assinado, _ = await _load_assinatura_bytes(db, "doc-ext", doc_id)
    if assinado:
        return Response(content=assinado, media_type="application/pdf",
                        headers={"Content-Disposition": 'inline; filename="documento_final.pdf"', "Cache-Control": "no-store"})
    return await _servir_pdf(db, doc_id, uid, "pdf_key_intermediario", "documento_final.pdf")


# ── Signatários ─────────────────────────────────────────────────────────────────
@router.post("/{doc_id}/signatarios")
async def add_signatario(doc_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _carregar(db, doc_id, uid)
    sig = novo_signatario(payload)
    await db[COL].update_one({"id": doc_id, "user_id": uid},
                             {"$push": {"signatarios": sig}, "$set": {"updated_at": datetime.utcnow()}})
    return sig


@router.patch("/{doc_id}/signatarios/{sid}")
async def edit_signatario(doc_id: str, sid: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    sig = next((s for s in doc.get("signatarios", []) if s.get("id") == sid), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Signatário não encontrado.")
    if sig.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Signatário já assinou — não pode editar.")
    upd = {}
    for k in ("nome", "papel"):
        if k in payload:
            upd[f"signatarios.$.{k}"] = str(payload[k] or "")
    for k in ("cpf_cnpj", "whatsapp"):
        if k in payload:
            upd[f"signatarios.$.{k}"] = "".join(filter(str.isdigit, str(payload[k] or "")))
    if "email" in payload:
        upd["signatarios.$.email"] = payload["email"] or None
    upd["updated_at"] = datetime.utcnow()
    await db[COL].update_one({"id": doc_id, "user_id": uid, "signatarios.id": sid}, {"$set": upd})
    return {"ok": True}


@router.delete("/{doc_id}/signatarios/{sid}")
async def del_signatario(doc_id: str, sid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    sig = next((s for s in doc.get("signatarios", []) if s.get("id") == sid), None)
    if sig and sig.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Signatário já assinou — não pode remover.")
    await db[COL].update_one({"id": doc_id, "user_id": uid},
                             {"$pull": {"signatarios": {"id": sid}}, "$set": {"updated_at": datetime.utcnow()}})
    return {"ok": True}
