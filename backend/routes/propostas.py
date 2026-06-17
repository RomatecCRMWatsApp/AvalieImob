# @module routes.propostas — Propostas de Consultoria (catálogo + preview + CRUD).
# Motor de cálculo independente em services.pricing (port fiel da ZAYRA).
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
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


class EnviarPropostaBody(BaseModel):
    phone: Optional[str] = None
    legenda: Optional[str] = None


def _fmt_brl(v) -> str:
    try:
        s = f"{float(v):,.2f}"
    except Exception:
        s = "0,00"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


# ── Enviar por WhatsApp ────────────────────────────────────────────────────
@router.post("/{pid}/enviar")
async def enviar_proposta(pid: str, body: EnviarPropostaBody,
                          uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Envia o PDF da proposta ao cliente via WhatsApp (Z-API/Meta) e marca status=enviada."""
    from services import zapi_service
    from services import meta_whatsapp_service as meta
    from services.integracoes_util import carregar_integracoes

    doc = await db.propostas.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    cfg = await carregar_integracoes(db, uid)
    if not cfg:
        raise HTTPException(status_code=400, detail="Nenhum provedor WhatsApp configurado em Configurações → Integrações.")
    phone = (body.phone or doc.get("cliente_telefone") or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Informe o WhatsApp do destinatário")

    try:
        pdf = _proposta_pdf_bytes(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao gerar PDF: {e}")
    filename = f"{doc.get('numero', 'proposta')}.pdf".replace("/", "-")
    label = SUBTIPO_LABEL.get(doc.get("subtipo"), doc.get("subtipo"))
    legenda = body.legenda or (
        f"Olá! Segue sua proposta {doc.get('numero', '')} — {label}.\n"
        f"Investimento total: {_fmt_brl(doc.get('valor_total'))}.\n"
        f"Validade: {doc.get('validade_dias', 15)} dias. Qualquer dúvida estou à disposição.")

    provider = (cfg.get("whatsapp_provider") or "zapi").lower()
    try:
        if provider == "meta":
            if not cfg.get("meta_phone_number_id") or not cfg.get("meta_access_token"):
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada")
            await meta.send_pdf(phone_number_id=cfg["meta_phone_number_id"], access_token=cfg["meta_access_token"],
                                phone=phone, pdf_bytes=pdf, filename=filename, caption=legenda)
        else:
            if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
                raise HTTPException(status_code=400, detail="Z-API não configurada")
            await zapi_service.send_document_pdf(
                instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
                security_token=cfg.get("zapi_security_token"),
                phone=phone, pdf_bytes=pdf, filename=filename, caption=legenda)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao enviar proposta %s por WhatsApp", pid)
        raise HTTPException(status_code=502, detail=f"Falha ao enviar: {type(e).__name__}: {e}")

    await db.propostas.update_one({"id": pid}, {"$set": {
        "status": "enviada", "enviada_em": datetime.utcnow(), "enviada_phone": phone,
    }})
    return {"ok": True, "status": "enviada", "phone": phone}


# ── Excluir ────────────────────────────────────────────────────────────────
@router.delete("/{pid}")
async def excluir(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.propostas.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return {"ok": True}
