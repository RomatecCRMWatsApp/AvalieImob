# @module routes.properties — CRUD de imóveis
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models import PropertyBase, Property

router = APIRouter(tags=["properties"])


@router.get("/properties", response_model=List[Property])
async def list_properties(type: Optional[str] = None, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    q = {"user_id": uid}
    if type and type.lower() != "todos":
        q["type"] = type
    items = await db.properties.find(q).sort("created_at", -1).to_list(1000)
    return [Property(**serialize_doc(i)) for i in items]


@router.post("/properties", response_model=Property)
async def create_property(data: PropertyBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    p = Property(user_id=uid, **data.model_dump())
    await db.properties.insert_one(p.model_dump())
    return p


@router.put("/properties/{pid}", response_model=Property)
async def update_property(pid: str, data: PropertyBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.properties.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    await db.properties.update_one({"id": pid}, {"$set": data.model_dump()})
    new_doc = await db.properties.find_one({"id": pid})
    return Property(**serialize_doc(new_doc))


@router.delete("/properties/{pid}")
async def delete_property(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.properties.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return {"ok": True}
