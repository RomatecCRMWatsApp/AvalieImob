# @module routes.perfil_avaliador — CRUD do perfil profissional do avaliador
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends
from db import get_db
from services.auth_service import get_current_user_id
from models import PerfilAvaliadorBase, PerfilAvaliador

router = APIRouter(tags=["perfil-avaliador"])


@router.get("/perfil-avaliador")
async def get_perfil_avaliador(uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    doc = await db.perfil_avaliador.find_one({"user_id": uid})
    if not doc:
        return PerfilAvaliador(user_id=uid).model_dump(mode="json")
    doc.pop("_id", None)
    return doc


@router.put("/perfil-avaliador")
async def update_perfil_avaliador(body: PerfilAvaliadorBase, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    now = datetime.utcnow()
    data = body.model_dump(mode="json")
    data["user_id"] = uid
    data["updated_at"] = now
    existing = await db.perfil_avaliador.find_one({"user_id": uid})
    if existing:
        await db.perfil_avaliador.update_one({"user_id": uid}, {"$set": data})
        doc = await db.perfil_avaliador.find_one({"user_id": uid})
    else:
        data["id"] = str(uuid.uuid4())
        data["created_at"] = now
        await db.perfil_avaliador.insert_one(data)
        doc = await db.perfil_avaliador.find_one({"user_id": uid})
    doc.pop("_id", None)
    return doc
