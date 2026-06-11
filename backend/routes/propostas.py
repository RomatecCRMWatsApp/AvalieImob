# @module routes.propostas — Propostas de Consultoria (catálogo + preview + CRUD).
# Motor de cálculo independente em services.pricing (port fiel da ZAYRA).
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.proposta import Proposta, PropostaBase, PropostaPreviewRequest
from services.pricing import CATALOGO_CONSULTORIA, calcular_consultoria, SUBTIPO_LABEL

logger = logging.getLogger("romatec")
router = APIRouter(tags=["propostas"], prefix="/propostas")


async def _next_numero_proposta(db) -> str:
    ano = datetime.utcnow().year
    res = await db.counters.find_one_and_update(
        {"_id": f"proposta_{ano}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"PROP-{ano}-{res['seq']:04d}"


# ── Catálogo dos tipos ─────────────────────────────────────────────────────
@router.get("/catalogo")
async def catalogo(uid: str = Depends(get_active_subscriber)):
    return {"tipos": CATALOGO_CONSULTORIA}


# ── Preview de cálculo (sem salvar) ────────────────────────────────────────
@router.post("/preview")
async def preview(body: PropostaPreviewRequest, uid: str = Depends(get_active_subscriber)):
    try:
        resultado = calcular_consultoria(body.subtipo, body.dados_imovel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "ok": True, "subtipo": body.subtipo,
        "valor_total": resultado["custos"]["secao_5_total"],
        "custos": resultado["custos"], "fontes": resultado["fontes"],
    }


# ── Criar ──────────────────────────────────────────────────────────────────
@router.post("", status_code=201)
async def criar(body: PropostaBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    try:
        resultado = calcular_consultoria(body.subtipo, body.dados_imovel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    numero = await _next_numero_proposta(db)
    prop = Proposta(
        user_id=uid, numero=numero,
        **body.model_dump(),
    )
    prop.valor_total = resultado["custos"]["secao_5_total"]
    prop.custos_calculados = resultado["custos"]
    prop.fontes_consulta = resultado["fontes"]
    prop.status = "emitida"
    await db.propostas.insert_one(prop.model_dump())
    return serialize_doc(prop.model_dump())


# ── Listar ─────────────────────────────────────────────────────────────────
@router.get("")
async def listar(
    subtipo: Optional[str] = None,
    status: Optional[str] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    query = {"user_id": uid}
    if subtipo:
        query["subtipo"] = subtipo
    if status:
        query["status"] = status
    items = await db.propostas.find(query).sort("created_at", -1).to_list(500)
    return [serialize_doc(i) for i in items]


# ── Detalhe ────────────────────────────────────────────────────────────────
@router.get("/{pid}")
async def detalhe(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.propostas.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return serialize_doc(doc)


# ── Atualizar (recalcula) ──────────────────────────────────────────────────
@router.put("/{pid}")
async def atualizar(pid: str, body: PropostaBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.propostas.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    try:
        resultado = calcular_consultoria(body.subtipo, body.dados_imovel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    update = body.model_dump()
    update["valor_total"] = resultado["custos"]["secao_5_total"]
    update["custos_calculados"] = resultado["custos"]
    update["fontes_consulta"] = resultado["fontes"]
    update["updated_at"] = datetime.utcnow()
    await db.propostas.update_one({"id": pid}, {"$set": update})
    novo = await db.propostas.find_one({"id": pid})
    return serialize_doc(novo)


# ── Excluir ────────────────────────────────────────────────────────────────
@router.delete("/{pid}")
async def excluir(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.propostas.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return {"ok": True}
