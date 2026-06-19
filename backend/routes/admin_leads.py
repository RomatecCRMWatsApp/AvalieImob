# @module routes.admin_leads — Painel admin dos leads da Calculadora pública.
"""Gestão dos leads capturados em `leads_avaliacao` (calculadora "Quanto vale meu
imóvel?"): listagem com filtro/busca/paginação, stats (cards + taxa de conversão),
troca de status, nota e exclusão.

Adaptado do spec (que usava ADMIN_API_TOKEN) p/ a auth real do AvalieImob:
auth via `get_admin_user` (JWT; roles admin/owner/ceo) + db Depends(get_db).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from db import get_db
from dependencies import get_admin_user

logger = logging.getLogger("romatec")

router = APIRouter(
    prefix="/admin/leads",
    tags=["Admin · Leads"],
    dependencies=[Depends(get_admin_user)],
)

StatusLead = Literal["novo", "em_contato", "convertido", "descartado"]
COL = "leads_avaliacao"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    for campo in ("criado_em", "atualizado_em"):
        v = doc.get(campo)
        if isinstance(v, datetime):
            doc[campo] = v.isoformat()
    return doc


class AtualizarLead(BaseModel):
    status: Optional[StatusLead] = None
    nota: Optional[str] = Field(default=None, max_length=2000)


@router.get("")
async def listar_leads(
    status: Optional[StatusLead] = None,
    q: Optional[str] = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db=Depends(get_db),
):
    filtro: dict = {}
    if status:
        filtro["status"] = status
    if q:
        regex = {"$regex": q.strip(), "$options": "i"}
        filtro["$or"] = [{"nome": regex}, {"whatsapp": regex}, {"email": regex}]

    try:
        total = await db[COL].count_documents(filtro)
        cursor = db[COL].find(filtro).sort("criado_em", -1).skip((page - 1) * limit).limit(limit)
        itens = [_serialize(d) async for d in cursor]
    except Exception as e:  # noqa: BLE001
        logger.exception("admin_leads: erro ao listar")
        raise HTTPException(500, "Falha ao listar leads.") from e

    return {"total": total, "page": page, "limit": limit, "items": itens}


@router.get("/stats")
async def stats(db=Depends(get_db)):
    try:
        cursor = db[COL].aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}])
        por_status = {d["_id"]: d["n"] async for d in cursor}
        desde = datetime.now(timezone.utc) - timedelta(days=30)
        ultimos_30 = await db[COL].count_documents({"criado_em": {"$gte": desde}})
    except Exception as e:  # noqa: BLE001
        logger.exception("admin_leads: erro nas stats")
        raise HTTPException(500, "Falha ao calcular estatísticas.") from e

    total = sum(por_status.values())
    convertidos = por_status.get("convertido", 0)
    taxa = round((convertidos / total) * 100, 1) if total else 0.0
    return {
        "total": total,
        "novos": por_status.get("novo", 0),
        "em_contato": por_status.get("em_contato", 0),
        "convertidos": convertidos,
        "descartados": por_status.get("descartado", 0),
        "ultimos_30_dias": ultimos_30,
        "taxa_conversao": taxa,
    }


@router.patch("/{lead_id}")
async def atualizar_lead(lead_id: str, dados: AtualizarLead, db=Depends(get_db)):
    try:
        oid = ObjectId(lead_id)
    except InvalidId:
        raise HTTPException(422, "ID inválido.")

    update: dict = {"atualizado_em": datetime.now(timezone.utc)}
    if dados.status is not None:
        update["status"] = dados.status
    if dados.nota is not None:
        update["nota"] = dados.nota.strip()

    try:
        doc = await db[COL].find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    except Exception as e:  # noqa: BLE001
        logger.exception("admin_leads: erro ao atualizar")
        raise HTTPException(500, "Falha ao atualizar lead.") from e

    if not doc:
        raise HTTPException(404, "Lead não encontrado.")
    return _serialize(doc)


@router.delete("/{lead_id}")
async def excluir_lead(lead_id: str, db=Depends(get_db)):
    try:
        oid = ObjectId(lead_id)
    except InvalidId:
        raise HTTPException(422, "ID inválido.")
    res = await db[COL].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Lead não encontrado.")
    return {"ok": True}
