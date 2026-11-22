# @module routes.receita_rtc — administração da integração com as calculadoras da Receita (CBS/IBS).
#
# Só administrador. Nesta fase: diagnóstico das calculadoras e tabela interna de alíquotas
# (PENDENCIAS.md §3.3). A tela de simulação do assinante entra na Fase 4.
# Sem `from __future__ import annotations` (quebra o FastAPI com o rate limiter; ver avaliacao_publica.py).
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db
from dependencies import get_admin_user
from services.receita_rtc import aliquotas as ALQ
from services.receita_rtc import service as SVC

router = APIRouter(prefix="/admin/receita-rtc", tags=["receita-rtc"], dependencies=[Depends(get_admin_user)])


class AliquotaNova(BaseModel):
    tributo: str
    uf: Optional[str] = None
    codigo_municipio: Optional[str] = None
    aliquota: str
    vigencia_inicio: str
    vigencia_fim: Optional[str] = None
    fonte: str


class Confirmacao(BaseModel):
    confirmado_por: str


class Revogacao(BaseModel):
    motivo: str


def _limpo(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


@router.get("/status")
async def status():
    return await SVC.diagnostico()


@router.get("/aliquotas")
async def listar_aliquotas(db=Depends(get_db)):
    docs = await db[ALQ.COLECAO].find({}).sort("vigencia_inicio", -1).to_list(2000)
    return {"aliquotas": [_limpo(d) for d in docs]}


@router.post("/aliquotas")
async def criar_aliquota(body: AliquotaNova, db=Depends(get_db), uid: str = Depends(get_admin_user)):
    try:
        return _limpo(await ALQ.criar(db, body.model_dump(), uid))
    except ALQ.AliquotaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/aliquotas/{registro_id}/confirmar")
async def confirmar_aliquota(registro_id: str, body: Confirmacao, db=Depends(get_db),
                             uid: str = Depends(get_admin_user)):
    try:
        return _limpo(await ALQ.confirmar(db, registro_id, uid, body.confirmado_por))
    except ALQ.AliquotaInvalida as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/aliquotas/{registro_id}/revogar")
async def revogar_aliquota(registro_id: str, body: Revogacao, db=Depends(get_db),
                           uid: str = Depends(get_admin_user)):
    try:
        return _limpo(await ALQ.revogar(db, registro_id, uid, body.motivo))
    except ALQ.AliquotaInvalida as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/aliquotas/auditoria")
async def auditoria(db=Depends(get_db)):
    docs = await db[ALQ.COLECAO_AUDITORIA].find({}).sort("em", -1).to_list(500)
    return {"eventos": [_limpo(d) for d in docs]}
