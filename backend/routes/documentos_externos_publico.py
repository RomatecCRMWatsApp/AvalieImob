# @module routes.documentos_externos_publico — página pública de assinatura do doc-ext.
# SEM auth + rate-limit. O signatário desenha a assinatura (PNG) e consente; quando todos
# assinam, dispara o carimbo (service.processar_carimbo).
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from services.documento_externo_service import COL, atualizar_status, processar_carimbo

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)
router_publico = APIRouter(prefix="/publico/documentos-externos", tags=["Documentos Externos Público"])


def _sig(sessao: dict, token: str):
    return next((s for s in sessao.get("signatarios", []) if s.get("token") == token), None)


@router_publico.get("/{token}")
@limiter.limit("30/minute")
async def obter_por_token(token: str, request: Request, db=Depends(get_db)):
    doc = await db[COL].find_one({"signatarios.token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Link inválido")
    sig = _sig(doc, token)
    if not sig:
        raise HTTPException(status_code=404, detail="Link inválido")
    # mostra o documento + a posição da assinatura deste signatário (quadro/seta)
    from services.pdf_preview import renderizar_paginas
    from services import r2_storage
    paginas = []
    try:
        raw = await asyncio.to_thread(r2_storage.download_bytes, doc.get("pdf_key"))
        paginas = await asyncio.to_thread(renderizar_paginas, raw)
    except Exception:  # noqa: BLE001
        paginas = []
    documentos = [{"tipo": "documento", "titulo": doc.get("titulo") or "Documento",
                   "paginas": paginas, "posicoes": sig.get("posicoes") or []}]
    return {"ok": True, "nome": sig.get("nome"), "papel": sig.get("papel"),
            "titulo": doc.get("titulo"), "cpf_cnpj": sig.get("cpf_cnpj"),
            "ja_assinado": sig.get("status") == "assinado", "documentos": documentos}


@router_publico.post("/{token}")
@limiter.limit("10/minute")
async def assinar(token: str, payload: dict, request: Request, db=Depends(get_db)):
    doc = await db[COL].find_one({"signatarios.token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Link inválido")
    sig = _sig(doc, token)
    if not sig:
        raise HTTPException(status_code=404, detail="Link inválido")
    if sig.get("status") == "assinado":
        return {"ok": True, "ja_assinado": True}
    traco = payload.get("traco_base64") or ""
    if not traco.startswith("data:image/png;base64,"):
        raise HTTPException(status_code=400, detail="Assinatura (traço) inválida")
    if not payload.get("concordo"):
        raise HTTPException(status_code=400, detail="É necessário concordar para assinar")

    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "0.0.0.0")
    ua = (request.headers.get("user-agent") or "")[:255]
    await db[COL].update_one(
        {"id": doc["id"], "signatarios.token": token},
        {"$set": {
            "signatarios.$.status": "assinado", "signatarios.$.assinado_em": datetime.utcnow(),
            "signatarios.$.ip": ip, "signatarios.$.user_agent": ua,
            "signatarios.$.geo_lat": payload.get("geo_lat"), "signatarios.$.geo_lng": payload.get("geo_lng"),
            "signatarios.$.traco_b64": traco.split(",", 1)[1], "updated_at": datetime.utcnow(),
        }})
    doc = await db[COL].find_one({"id": doc["id"]})
    await atualizar_status(db, doc["id"])
    todos = all(s.get("status") == "assinado" for s in doc["signatarios"])
    if todos:
        try:
            await processar_carimbo(db, doc)
        except Exception:
            logger.error("Falha ao carimbar doc-ext %s", doc["id"], exc_info=True)
    return {"ok": True, "concluido": todos}


@router_publico.post("/{token}/recusar")
@limiter.limit("10/minute")
async def recusar(token: str, payload: dict = None, request: Request = None, db=Depends(get_db)):
    doc = await db[COL].find_one({"signatarios.token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Link inválido")
    await db[COL].update_one({"id": doc["id"], "signatarios.token": token},
                             {"$set": {"signatarios.$.status": "recusado", "updated_at": datetime.utcnow()}})
    await atualizar_status(db, doc["id"])
    return {"ok": True}
