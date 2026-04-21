# @module routes.evaluations — CRUD de laudos/avaliações genéricas
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models import EvaluationBase, Evaluation

router = APIRouter(tags=["evaluations"])


@router.get("/evaluations", response_model=List[Evaluation])
async def list_evaluations(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    items = await db.evaluations.find({"user_id": uid}).sort("created_at", -1).to_list(1000)
    return [Evaluation(**serialize_doc(i)) for i in items]


@router.post("/evaluations", response_model=Evaluation)
async def create_evaluation(data: EvaluationBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    year = datetime.utcnow().year
    prefix = {"PTAM": "PTAM", "Laudo": "LAU"}.get(data.type, "GAR")
    count = await db.evaluations.count_documents({"user_id": uid}) + 1
    code = f"{prefix}-{year}-{str(count).zfill(3)}"
    e = Evaluation(user_id=uid, code=code, **data.model_dump())
    await db.evaluations.insert_one(e.model_dump())
    return e


@router.put("/evaluations/{eid}", response_model=Evaluation)
async def update_evaluation(eid: str, data: EvaluationBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.evaluations.find_one({"id": eid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")
    await db.evaluations.update_one({"id": eid}, {"$set": data.model_dump()})
    new_doc = await db.evaluations.find_one({"id": eid})
    return Evaluation(**serialize_doc(new_doc))


@router.delete("/evaluations/{eid}")
async def delete_evaluation(eid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.evaluations.delete_one({"id": eid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")
    return {"ok": True}
