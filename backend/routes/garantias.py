# @module routes.garantias — CRUD de Garantias (NBR 14.653 partes 3 e 5)
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models import GarantiaBase, Garantia

router = APIRouter(tags=["garantias"])


@router.get("/garantias", response_model=List[Garantia])
async def list_garantias(tipo: Optional[str] = None, status: Optional[str] = None, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    q: dict = {"user_id": uid}
    if tipo:
        q["tipo_garantia"] = tipo
    if status:
        q["status"] = status
    items = await db.garantias.find(q).sort("updated_at", -1).to_list(1000)
    return [Garantia(**serialize_doc(i)) for i in items]


@router.get("/garantias/{gid}", response_model=Garantia)
async def get_garantia(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.garantias.find_one({"id": gid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Garantia não encontrada")
    return Garantia(**serialize_doc(doc))


@router.post("/garantias", response_model=Garantia)
async def create_garantia(data: GarantiaBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    numero = data.numero
    if not numero:
        year = datetime.utcnow().year
        count = await db.garantias.count_documents({"user_id": uid}) + 1
        numero = f"GAR-{year}-{str(count).zfill(4)}"
    payload = data.model_dump()
    payload["numero"] = numero
    g = Garantia(user_id=uid, **payload)
    await db.garantias.insert_one(g.model_dump())
    return g


@router.put("/garantias/{gid}", response_model=Garantia)
async def update_garantia(gid: str, data: GarantiaBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.garantias.find_one({"id": gid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Garantia não encontrada")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    await db.garantias.update_one({"id": gid}, {"$set": updates})
    new_doc = await db.garantias.find_one({"id": gid})
    return Garantia(**serialize_doc(new_doc))


@router.delete("/garantias/{gid}")
async def delete_garantia(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.garantias.delete_one({"id": gid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Garantia não encontrada")
    return {"ok": True}
