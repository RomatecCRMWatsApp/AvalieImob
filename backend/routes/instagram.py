# @module routes.instagram — Instagram Studio (admin): gera conteúdo com IA + CRUD do calendário.
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db
from dependencies import get_admin_user, serialize_doc
from models.instagram_post import (
    InstagramPost, InstagramPostCreate, InstagramPostUpdate, _iso,
)
from services import instagram_ia_service

router = APIRouter(tags=["instagram"])
logger = logging.getLogger("romatec")


class GerarBody(BaseModel):
    pilar: str
    assunto: str = ""
    formato: str = "post_unico"


class StatusBody(BaseModel):
    status: str


@router.post("/instagram/gerar")
async def gerar(body: GerarBody, uid: str = Depends(get_admin_user)):
    return await instagram_ia_service.gerar_conteudo(body.pilar, body.assunto, body.formato)


@router.post("/instagram/posts")
async def criar_post(body: InstagramPostCreate, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    doc = InstagramPost(user_id=uid, **body.dict()).dict()
    await db.instagram_posts.insert_one(doc)
    return serialize_doc(doc)


@router.get("/instagram/posts")
async def listar_posts(mes: Optional[str] = None, status: Optional[str] = None,
                       pilar: Optional[str] = None,
                       uid: str = Depends(get_admin_user), db=Depends(get_db)):
    q = {"user_id": uid}
    if status:
        q["status"] = status
    if pilar:
        q["pilar"] = pilar
    if mes:
        q["data_agendada"] = {"$regex": f"^{mes}"}
    docs = await db.instagram_posts.find(q).sort("criado_em", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.get("/instagram/posts/{pid}")
async def obter_post(pid: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Post não encontrado")
    return serialize_doc(doc)


@router.put("/instagram/posts/{pid}")
async def atualizar_post(pid: str, body: InstagramPostUpdate,
                         uid: str = Depends(get_admin_user), db=Depends(get_db)):
    upd = dict(body.dict(exclude_unset=True))
    upd["atualizado_em"] = _iso()
    r = await db.instagram_posts.update_one({"id": pid, "user_id": uid}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Post não encontrado")
    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    return serialize_doc(doc)


@router.post("/instagram/posts/{pid}/status")
async def mudar_status(pid: str, body: StatusBody,
                       uid: str = Depends(get_admin_user), db=Depends(get_db)):
    if body.status not in ("ideia", "aprovado", "publicado"):
        raise HTTPException(400, "Status inválido")
    upd = {"status": body.status, "atualizado_em": _iso()}
    if body.status == "publicado":
        upd["data_publicado"] = _iso()
    r = await db.instagram_posts.update_one({"id": pid, "user_id": uid}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Post não encontrado")
    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    return serialize_doc(doc)


@router.delete("/instagram/posts/{pid}")
async def excluir_post(pid: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    r = await db.instagram_posts.delete_one({"id": pid, "user_id": uid})
    if r.deleted_count == 0:
        raise HTTPException(404, "Post não encontrado")
    return {"ok": True}
