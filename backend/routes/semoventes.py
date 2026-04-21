# @module routes.semoventes — CRUD de Semoventes (Penhor Rural Bancário)
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models import SemoventeBase, Semovente

router = APIRouter(tags=["semoventes"])


@router.get("/semoventes", response_model=List[Semovente])
async def list_semoventes(tipo: Optional[str] = None, status: Optional[str] = None, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    q: dict = {"user_id": uid}
    if tipo:
        q["tipo_semovente"] = tipo
    if status:
        q["status"] = status
    items = await db.semoventes.find(q).sort("updated_at", -1).to_list(1000)
    return [Semovente(**serialize_doc(i)) for i in items]


@router.get("/semoventes/{sid}", response_model=Semovente)
async def get_semovente(sid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.semoventes.find_one({"id": sid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Semovente não encontrado")
    return Semovente(**serialize_doc(doc))


@router.post("/semoventes", response_model=Semovente)
async def create_semovente(data: SemoventeBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    numero_laudo = data.numero_laudo
    if not numero_laudo:
        year = datetime.utcnow().year
        count = await db.semoventes.count_documents({"user_id": uid}) + 1
        numero_laudo = f"SEM-{year}-{str(count).zfill(4)}"
    payload = data.model_dump()
    payload["numero_laudo"] = numero_laudo
    s = Semovente(user_id=uid, **payload)
    await db.semoventes.insert_one(s.model_dump())
    return s


@router.put("/semoventes/{sid}", response_model=Semovente)
async def update_semovente(sid: str, data: SemoventeBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.semoventes.find_one({"id": sid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Semovente não encontrado")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    await db.semoventes.update_one({"id": sid}, {"$set": updates})
    new_doc = await db.semoventes.find_one({"id": sid})
    return Semovente(**serialize_doc(new_doc))


@router.delete("/semoventes/{sid}")
async def delete_semovente(sid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.semoventes.delete_one({"id": sid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Semovente não encontrado")
    return {"ok": True}
