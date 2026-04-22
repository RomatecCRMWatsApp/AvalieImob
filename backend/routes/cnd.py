# @module routes.cnd — Endpoints CND: consultar, detalhe, download PDF, histórico, delete
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.cnd import (
    CNDConsultarRequest, CNDConsultarResponse,
    CNDConsulta, CNDCertidao,
)
from services.cnd.cnd_service import consultar_cnd

router = APIRouter(tags=["CND"])
logger = logging.getLogger("romatec")


async def _run_consulta(db, user_id: str, body: CNDConsultarRequest, ip: Optional[str]):
    """Tarefa de background: executa todos os providers e salva resultados."""
    try:
        await consultar_cnd(
            db=db,
            user_id=user_id,
            cpf_cnpj=body.cpf_cnpj,
            nome_parte=body.nome_parte,
            tipo_parte=body.tipo_parte,
            finalidade=body.finalidade,
            ptam_id=body.ptam_id,
            data_nascimento=body.data_nascimento,
            ip=ip,
        )
    except Exception as exc:
        logger.error("Erro background CND: %s", exc)


@router.post("/cnd/consultar", response_model=CNDConsultarResponse)
async def iniciar_consulta(
    body: CNDConsultarRequest,
    request: Request,
    background: BackgroundTasks,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Inicia consulta CND em background. Retorna consulta_id imediatamente."""
    from models.cnd import CNDConsulta
    from models.common import _id
    from datetime import datetime

    consulta_id = _id()
    doc = {
        "id": consulta_id,
        "user_id": uid,
        "cpf_cnpj": body.cpf_cnpj,
        "nome_parte": body.nome_parte,
        "tipo_parte": body.tipo_parte,
        "ptam_id": body.ptam_id,
        "status": "pendente",
        "created_at": datetime.utcnow(),
    }
    await db.cnd_consultas.insert_one(doc)
    ip = request.client.host if request.client else None
    background.add_task(_run_consulta_by_id, db, uid, consulta_id, body, ip)
    return CNDConsultarResponse(consulta_id=consulta_id, status="processando")


async def _run_consulta_by_id(db, user_id: str, consulta_id: str, body: CNDConsultarRequest, ip: Optional[str]):
    """Background: orquestra providers e atualiza consulta existente."""
    try:
        from services.cnd import receita_federal, pgfn, tst, trf1, tjma, cnib, rfb_cadastro
        from services.cnd.cnd_service import PROVIDERS, _run_provider
        from models.cnd import CNDCertidao, CNDLog
        import asyncio

        log = CNDLog(user_id=user_id, cpf_cnpj=body.cpf_cnpj, finalidade=body.finalidade, ip=ip)
        await db.cnd_logs.insert_one(log.model_dump())

        await db.cnd_consultas.update_one({"id": consulta_id}, {"$set": {"status": "processando"}})
        tasks = [_run_provider(fn, body.cpf_cnpj) for fn in PROVIDERS]
        resultados = await asyncio.gather(*tasks, return_exceptions=True)

        for res in resultados:
            if isinstance(res, Exception):
                continue
            cert = CNDCertidao(
                consulta_id=consulta_id,
                provider=res.get("provider", "desconhecido"),
                resultado=res.get("resultado", "erro"),
                pdf_base64=res.get("pdf_base64"),
                validade=res.get("validade"),
                observacao=res.get("observacao"),
                tempo_ms=res.get("tempo_ms", 0),
            )
            await db.cnd_certidoes.insert_one(cert.model_dump())

        await db.cnd_consultas.update_one({"id": consulta_id}, {"$set": {"status": "concluido"}})
    except Exception as exc:
        logger.error("Erro _run_consulta_by_id: %s", exc)
        await db.cnd_consultas.update_one({"id": consulta_id}, {"$set": {"status": "erro"}})


@router.get("/cnd/consulta/{consulta_id}")
async def detalhe_consulta(
    consulta_id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Retorna consulta e todas as certidões associadas."""
    doc = await db.cnd_consultas.find_one({"id": consulta_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    certidoes = await db.cnd_certidoes.find({"consulta_id": consulta_id}).to_list(20)
    return {
        "consulta": serialize_doc(doc),
        "certidoes": [serialize_doc(c) for c in certidoes],
    }


@router.get("/cnd/consulta/{consulta_id}/download/{provider}")
async def download_certidao(
    consulta_id: str,
    provider: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Retorna PDF base64 de uma certidão específica."""
    consulta = await db.cnd_consultas.find_one({"id": consulta_id, "user_id": uid})
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    cert = await db.cnd_certidoes.find_one({"consulta_id": consulta_id, "provider": provider})
    if not cert:
        raise HTTPException(status_code=404, detail="Certidão não encontrada")
    if not cert.get("pdf_base64"):
        raise HTTPException(status_code=404, detail="PDF não disponível para este provider")
    return {"provider": provider, "pdf_base64": cert["pdf_base64"]}


@router.get("/cnd/historico")
async def historico(
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Retorna as últimas 50 consultas CND do usuário."""
    docs = await db.cnd_consultas.find({"user_id": uid}).sort("created_at", -1).to_list(50)
    return [serialize_doc(d) for d in docs]


@router.post("/cnd/consulta/{consulta_id}/anexar")
async def anexar_ptam(
    consulta_id: str,
    body: dict,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Vincula um ptam_id à consulta CND."""
    consulta = await db.cnd_consultas.find_one({"id": consulta_id, "user_id": uid})
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    ptam_id = body.get("ptam_id")
    if not ptam_id:
        raise HTTPException(status_code=422, detail="ptam_id é obrigatório")
    await db.cnd_consultas.update_one({"id": consulta_id}, {"$set": {"ptam_id": ptam_id}})
    return {"ok": True}


@router.delete("/cnd/consulta/{consulta_id}")
async def deletar_consulta(
    consulta_id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Remove consulta e todas as certidões (LGPD)."""
    consulta = await db.cnd_consultas.find_one({"id": consulta_id, "user_id": uid})
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    await db.cnd_certidoes.delete_many({"consulta_id": consulta_id})
    await db.cnd_consultas.delete_one({"id": consulta_id})
    return {"detail": "Consulta e certidões removidas com sucesso"}
