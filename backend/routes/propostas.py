# @module routes.propostas — Propostas de Consultoria (catálogo + preview + CRUD).
# Motor de cálculo independente em services.pricing (port fiel da ZAYRA).
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
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


def _proposta_pdf_bytes(doc: dict) -> bytes:
    from pdf.proposta_pdf import gerar_proposta_pdf
    doc = dict(doc)
    doc["subtipo_label"] = SUBTIPO_LABEL.get(doc.get("subtipo"), doc.get("subtipo"))
    return gerar_proposta_pdf(doc)


# ── PDF (inline) ───────────────────────────────────────────────────────────
@router.get("/{pid}/pdf")
async def proposta_pdf(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.propostas.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    try:
        pdf = _proposta_pdf_bytes(doc)
    except Exception as e:
        logger.exception("Erro ao gerar PDF da proposta %s", pid)
        raise HTTPException(status_code=500, detail=f"Falha ao gerar PDF: {e}")
    nome = f"{doc.get('numero', 'proposta')}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nome}"'})


# ── PDF de preview (sem salvar — calcula na hora a partir do form) ──────────
@router.post("/preview/pdf")
async def preview_pdf(body: PropostaPreviewRequest, uid: str = Depends(get_active_subscriber)):
    try:
        resultado = calcular_consultoria(body.subtipo, body.dados_imovel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    doc = {
        "numero": "PRÉVIA", "subtipo": body.subtipo,
        "subtipo_label": SUBTIPO_LABEL.get(body.subtipo, body.subtipo),
        "custos_calculados": resultado["custos"],
        "dados_imovel": body.dados_imovel,
        "cliente_nome": getattr(body, "cliente_nome", None),
        "validade_dias": getattr(body, "validade_dias", 15),
    }
    from pdf.proposta_pdf import gerar_proposta_pdf
    pdf = gerar_proposta_pdf(doc)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="previa.pdf"'})


# ── Excluir ────────────────────────────────────────────────────────────────
@router.delete("/{pid}")
async def excluir(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.propostas.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return {"ok": True}
