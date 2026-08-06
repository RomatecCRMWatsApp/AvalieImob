# @module routes.novidades — Central de Novidades (JWT; rotas /admin exigem admin).
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from db import get_db
from dependencies import get_active_subscriber, get_admin_user
from models.novidade import NovidadeInput
from services import novidades as NOV
from services.ratelimit import pub_limiter

logger = logging.getLogger("romatec")
router = APIRouter(tags=["novidades"], prefix="/novidades")


@router.get("/pendentes")
@pub_limiter.limit("60/minute")
async def pendentes(request: Request, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Novidades pendentes p/ o modal (após o login). Chamado uma vez por sessão."""
    return await NOV.listar_pendentes(db, uid)


@router.get("/historico")
async def historico(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await NOV.listar_historico(db, uid)


@router.post("/{novidade_id}/visualizada")
async def visualizada(novidade_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await NOV.marcar_visualizada(db, uid, novidade_id)
    return {"ok": True}


@router.post("/{novidade_id}/dispensar")
async def dispensar(novidade_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await NOV.dispensar(db, uid, novidade_id)
    return {"ok": True}


@router.post("/{novidade_id}/cta")
async def cta(novidade_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await NOV.registrar_cta(db, uid, novidade_id)
    return {"ok": True}


# ── Admin ─────────────────────────────────────────────────────────────────────
@router.get("/admin")
async def admin_listar(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    return await NOV.listar_admin(db)


@router.post("/admin", status_code=201)
async def admin_criar(body: NovidadeInput, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    try:
        return await NOV.criar(db, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.put("/admin/{novidade_id}")
async def admin_editar(novidade_id: str, body: NovidadeInput,
                       uid: str = Depends(get_admin_user), db=Depends(get_db)):
    return await NOV.editar(db, novidade_id, body.model_dump())


@router.post("/admin/{novidade_id}/publicar")
async def admin_publicar(novidade_id: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    return await NOV.publicar(db, novidade_id)


@router.get("/admin/{novidade_id}/metricas")
async def admin_metricas(novidade_id: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    return await NOV.metricas(db, novidade_id)
