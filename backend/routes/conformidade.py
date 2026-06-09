# @module routes.conformidade — Painel de Conformidade COFECI/CNAI (Feature 05).
# Prefixo /conformidade (montado sob /api). Multi-tenant por user_id.
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db
from dependencies import get_active_subscriber, get_authenticated_user
from models.conformidade import Credencial
from services.conformidade_service import rodar_verificacao_completa

router = APIRouter(prefix="/conformidade", tags=["conformidade"])
logger = logging.getLogger("romatec")

def _validade_status(dias: int) -> str:
    if dias < 0:
        return "vencida"
    if dias <= 15:
        return "urgente"
    if dias <= 60:
        return "aviso"
    return "ok"


def _parse_validade(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


# ── CREDENCIAIS ──────────────────────────────────────────────────────────────
@router.post("/credenciais")
async def cadastrar_credencial(payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    payload.pop("user_id", None)
    payload.pop("id", None)
    if not payload.get("validade"):
        raise HTTPException(status_code=422, detail="Validade é obrigatória")
    if not payload.get("numero"):
        raise HTTPException(status_code=422, detail="Número é obrigatório")
    try:
        cred = Credencial(user_id=uid, **payload)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Dados inválidos: {e}")
    await db.credenciais.insert_one(cred.model_dump())
    return {"id": cred.id}


@router.get("/credenciais")
async def listar_credenciais(uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    return await db.credenciais.find(
        {"user_id": uid, "ativo": True}, {"_id": 0}
    ).sort("validade", 1).to_list(50)


@router.put("/credenciais/{cred_id}")
async def atualizar_credencial(cred_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    payload.pop("user_id", None)
    payload.pop("id", None)
    payload["updated_at"] = datetime.utcnow()
    res = await db.credenciais.update_one(
        {"id": cred_id, "user_id": uid}, {"$set": payload}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    return {"message": "Atualizado"}


@router.delete("/credenciais/{cred_id}")
async def desativar_credencial(cred_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await db.credenciais.update_one(
        {"id": cred_id, "user_id": uid}, {"$set": {"ativo": False}}
    )
    return {"message": "Credencial desativada"}


# ── ALERTAS ──────────────────────────────────────────────────────────────────
@router.get("/alertas")
async def listar_alertas(nao_lidos: bool = False, uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    filtro: dict = {"user_id": uid}
    if nao_lidos:
        filtro["lido"] = False
    return await db.alertas_conformidade.find(filtro, {"_id": 0}).sort("created_at", -1).to_list(100)


@router.patch("/alertas/{alerta_id}/lido")
async def marcar_lido(alerta_id: str, uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    await db.alertas_conformidade.update_one(
        {"id": alerta_id, "user_id": uid}, {"$set": {"lido": True}}
    )
    return {"message": "Marcado como lido"}


@router.post("/verificar-agora")
async def verificar_agora(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    total = await rodar_verificacao_completa(db, uid)
    return {"alertas_gerados": total}


# ── CONFIG ───────────────────────────────────────────────────────────────────
@router.get("/config")
async def obter_config(uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    doc = await db.config_conformidade.find_one({"user_id": uid}, {"_id": 0})
    return doc or {"user_id": uid}


@router.put("/config")
async def salvar_config(payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    payload.pop("user_id", None)
    payload["updated_at"] = datetime.utcnow()
    await db.config_conformidade.update_one(
        {"user_id": uid}, {"$set": {**payload, "user_id": uid}}, upsert=True
    )
    return {"message": "Config salva"}


# ── DASHBOARD ────────────────────────────────────────────────────────────────
@router.get("/dashboard")
async def dashboard_conformidade(uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    alertas_urgentes = await db.alertas_conformidade.count_documents(
        {"user_id": uid, "severidade": "urgente", "lido": False}
    )
    alertas_avisos = await db.alertas_conformidade.count_documents(
        {"user_id": uid, "severidade": "aviso", "lido": False}
    )
    creds = await db.credenciais.find({"user_id": uid, "ativo": True}, {"_id": 0}).to_list(20)

    hoje = date.today()
    creds_status = []
    for c in creds:
        try:
            v = _parse_validade(c["validade"])
        except Exception:
            continue
        dias = (v - hoje).days
        creds_status.append({
            "tipo": c.get("tipo"),
            "numero": c.get("numero"),
            "validade": v.strftime("%d/%m/%Y"),
            "dias_restantes": dias,
            "status": _validade_status(dias),
        })
    creds_status.sort(key=lambda x: x["dias_restantes"])

    return {
        "alertas_urgentes": alertas_urgentes,
        "alertas_avisos": alertas_avisos,
        "credenciais": creds_status,
    }
