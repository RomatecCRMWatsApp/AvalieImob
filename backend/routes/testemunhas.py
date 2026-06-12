# @module routes.testemunhas — Testemunhas salvas do usuário (autofill no wizard de Contratos)
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.testemunha import Testemunha, TestemunhaBase

router = APIRouter(tags=["testemunhas"])


@router.get("/testemunhas", response_model=List[Testemunha])
async def listar_testemunhas(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Lista as testemunhas salvas do usuário (mais recentes primeiro)."""
    itens = await db.testemunhas.find({"user_id": uid}).sort("nome", 1).to_list(500)
    return [Testemunha(**serialize_doc(i)) for i in itens]


@router.post("/testemunhas", response_model=Testemunha)
async def criar_testemunha(
    data: TestemunhaBase,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Salva uma testemunha. Não duplica por CPF (atualiza a existente)."""
    if not (data.nome or "").strip():
        raise HTTPException(status_code=422, detail="Nome da testemunha é obrigatório")
    cpf_digits = "".join(c for c in (data.cpf or "") if c.isdigit())
    if cpf_digits:
        existente = await db.testemunhas.find_one({"user_id": uid, "cpf_digits": cpf_digits})
        if existente:
            updates = data.model_dump()
            updates["updated_at"] = datetime.utcnow()
            updates["cpf_digits"] = cpf_digits
            await db.testemunhas.update_one(
                {"id": existente["id"], "user_id": uid}, {"$set": updates})
            novo = await db.testemunhas.find_one({"id": existente["id"]})
            return Testemunha(**serialize_doc(novo))
    t = Testemunha(user_id=uid, **data.model_dump())
    doc = t.model_dump()
    doc["cpf_digits"] = cpf_digits
    await db.testemunhas.insert_one(doc)
    return t


@router.put("/testemunhas/{tid}", response_model=Testemunha)
async def atualizar_testemunha(
    tid: str,
    data: TestemunhaBase,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.testemunhas.find_one({"id": tid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Testemunha não encontrada")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    updates["cpf_digits"] = "".join(c for c in (data.cpf or "") if c.isdigit())
    await db.testemunhas.update_one({"id": tid, "user_id": uid}, {"$set": updates})
    novo = await db.testemunhas.find_one({"id": tid})
    return Testemunha(**serialize_doc(novo))


@router.delete("/testemunhas/{tid}")
async def excluir_testemunha(
    tid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    res = await db.testemunhas.delete_one({"id": tid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Testemunha não encontrada")
    return {"ok": True}
