# @module routes.zonas — CRUD de Zonas do Plano Diretor por usuário com seed automático
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from services.auth_service import get_current_user_id
from dependencies import get_active_subscriber
from models.zonas import ZonaPlanoDiretor, ZonaPlanoDiretorCreate, ZonaPlanoDiretorUpdate

router = APIRouter(tags=["zonas"])

ZONAS_PADRAO = [
    {"codigo": "ZR1",  "nome": "Zona Residencial 1",               "descricao": "Uso residencial unifamiliar de baixa densidade"},
    {"codigo": "ZR2",  "nome": "Zona Residencial 2",               "descricao": "Uso residencial de media densidade"},
    {"codigo": "ZR3",  "nome": "Zona Residencial 3",               "descricao": "Uso residencial de alta densidade"},
    {"codigo": "ZC",   "nome": "Zona Comercial",                   "descricao": "Uso comercial e de servicos"},
    {"codigo": "ZCI",  "nome": "Zona Comercial e Industrial",      "descricao": "Uso misto comercial e industrial"},
    {"codigo": "ZI",   "nome": "Zona Industrial",                  "descricao": "Uso industrial"},
    {"codigo": "ZEI",  "nome": "Zona de Expansao Industrial",      "descricao": "Reserva para expansao industrial"},
    {"codigo": "ZRu",  "nome": "Zona Rural",                       "descricao": "Uso agropecuario e atividades rurais"},
    {"codigo": "ZEIS", "nome": "Zona Especial de Interesse Social", "descricao": "Habitacao de interesse social"},
    {"codigo": "ZPA",  "nome": "Zona de Protecao Ambiental",       "descricao": "Areas de preservacao permanente"},
    {"codigo": "ZM",   "nome": "Zona Mista",                       "descricao": "Uso misto residencial e comercial"},
    {"codigo": "ZCB",  "nome": "Zona de Centralidade de Bairro",   "descricao": "Comercio e servicos de bairro"},
]


def _serialize(doc):
    if not doc:
        return doc
    doc.pop("_id", None)
    return doc


async def _seed_if_empty(uid: str, db):
    """Insere zonas padrão se o usuário ainda não tem nenhuma cadastrada."""
    count = await db.zonas_planodiretor.count_documents({"user_id": uid})
    if count == 0:
        docs = []
        for z in ZONAS_PADRAO:
            zona = ZonaPlanoDiretor(user_id=uid, **z)
            docs.append(zona.model_dump())
        if docs:
            await db.zonas_planodiretor.insert_many(docs)


@router.get("/zonas", response_model=List[ZonaPlanoDiretor])
async def listar_zonas(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _seed_if_empty(uid, db)
    items = await db.zonas_planodiretor.find(
        {"user_id": uid, "ativo": True}
    ).sort([("municipio", 1), ("codigo", 1)]).to_list(1000)
    return [ZonaPlanoDiretor(**_serialize(i)) for i in items]


@router.post("/zonas", response_model=ZonaPlanoDiretor, status_code=201)
async def criar_zona(data: ZonaPlanoDiretorCreate, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    codigo_upper = data.codigo.upper()
    # Validar duplicata codigo + municipio + user_id
    existente = await db.zonas_planodiretor.find_one({
        "user_id": uid,
        "codigo": codigo_upper,
        "municipio": data.municipio or "",
        "ativo": True,
    })
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Zona '{codigo_upper}' já existe para o município '{data.municipio or 'geral'}'"
        )
    zona = ZonaPlanoDiretor(
        user_id=uid,
        codigo=codigo_upper,
        nome=data.nome,
        descricao=data.descricao or "",
        municipio=data.municipio or "",
        uf=data.uf or "",
    )
    await db.zonas_planodiretor.insert_one(zona.model_dump())
    return zona


@router.put("/zonas/{zid}", response_model=ZonaPlanoDiretor)
async def atualizar_zona(
    zid: str,
    data: ZonaPlanoDiretorUpdate,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.zonas_planodiretor.find_one({"id": zid, "user_id": uid, "ativo": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Zona não encontrada")

    update_fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if "codigo" in update_fields:
        update_fields["codigo"] = update_fields["codigo"].upper()
    update_fields["updated_at"] = datetime.utcnow()

    await db.zonas_planodiretor.update_one({"id": zid}, {"$set": update_fields})
    new_doc = await db.zonas_planodiretor.find_one({"id": zid})
    return ZonaPlanoDiretor(**_serialize(new_doc))


@router.delete("/zonas/{zid}")
async def excluir_zona(zid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.zonas_planodiretor.find_one({"id": zid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Zona não encontrada")
    await db.zonas_planodiretor.update_one(
        {"id": zid},
        {"$set": {"ativo": False, "updated_at": datetime.utcnow()}}
    )
    return {"ok": True}
