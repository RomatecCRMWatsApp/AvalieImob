# @module routes.perfil_avaliador — CRUD do perfil profissional do avaliador
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from db import get_db
from dependencies import serialize_doc
from services.auth_service import get_current_user_id
from models import PerfilAvaliadorBase, PerfilAvaliador

router = APIRouter(tags=["perfil-avaliador"])


class CartaoRegularidadeBody(BaseModel):
    cartao_regularidade_b64: Optional[str] = None
    cartao_regularidade_link: Optional[str] = None
    cartao_regularidade_anexar: Optional[bool] = None


@router.get("/perfil-avaliador")
async def get_perfil_avaliador(uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    doc = await db.perfil_avaliador.find_one({"user_id": uid})
    if not doc:
        return PerfilAvaliador(user_id=uid).model_dump(mode="json")
    return serialize_doc(doc)


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
    return serialize_doc(doc)


@router.put("/perfil-avaliador/cartao-regularidade")
async def set_cartao_regularidade(body: CartaoRegularidadeBody,
                                  uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    """Salva SÓ o Cartão de Regularidade (CRECI) no perfil — sem mexer no resto.
    Aceita IMAGEM (PNG/JPG/WEBP) ou PDF — o PDF é convertido em páginas-imagem (frente/verso)."""
    upd = {"updated_at": datetime.utcnow()}
    if body.cartao_regularidade_link is not None:
        upd["cartao_regularidade_link"] = body.cartao_regularidade_link
    if body.cartao_regularidade_anexar is not None:
        upd["cartao_regularidade_anexar"] = body.cartao_regularidade_anexar
    if body.cartao_regularidade_b64 is not None:
        from services.cartao_regularidade import is_pdf_b64, pdf_b64_to_paginas_png_b64
        b64 = body.cartao_regularidade_b64
        if b64 == "":  # remoção
            upd["cartao_regularidade_b64"] = ""
            upd["cartao_regularidade_paginas_b64"] = []
        elif is_pdf_b64(b64):
            paginas = pdf_b64_to_paginas_png_b64(b64)
            upd["cartao_regularidade_paginas_b64"] = paginas
            upd["cartao_regularidade_b64"] = ""  # passa a usar a lista de páginas
        else:  # imagem única
            upd["cartao_regularidade_b64"] = b64
            upd["cartao_regularidade_paginas_b64"] = []
    await db.perfil_avaliador.update_one(
        {"user_id": uid},
        {"$set": upd, "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": datetime.utcnow()}},
        upsert=True,
    )
    doc = await db.perfil_avaliador.find_one({"user_id": uid})
    return serialize_doc(doc)
