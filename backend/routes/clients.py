# @module routes.clients — CRUD de clientes
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from services.auth_service import get_current_user_id
from dependencies import get_active_subscriber
from models import ClientBase, Client

router = APIRouter(tags=["clients"])


def _serialize(doc):
    if not doc:
        return doc
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


@router.get("/clients", response_model=List[Client])
async def list_clients(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    items = await db.clients.find({"user_id": uid}).sort("created_at", -1).to_list(1000)
    return [Client(**_serialize(i)) for i in items]


@router.post("/clients", response_model=Client)
async def create_client(data: ClientBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    c = Client(user_id=uid, **data.model_dump())
    await db.clients.insert_one(c.model_dump())
    return c


@router.put("/clients/{cid}", response_model=Client)
async def update_client(cid: str, data: ClientBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.clients.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    await db.clients.update_one({"id": cid}, {"$set": data.model_dump()})
    new_doc = await db.clients.find_one({"id": cid})
    return Client(**_serialize(new_doc))


@router.delete("/clients/{cid}")
async def delete_client(cid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.clients.delete_one({"id": cid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"ok": True}
