# @module routes.clients — CRUD de clientes
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from services.auth_service import get_current_user_id
from dependencies import get_active_subscriber, serialize_doc
from models import ClientBase, Client

router = APIRouter(tags=["clients"])


def _digits(s) -> str:
    return "".join(c for c in (s or "") if c.isdigit())

@router.get("/clients", response_model=List[Client])
async def list_clients(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    items = await db.clients.find({"user_id": uid}).sort("created_at", -1).to_list(1000)
    return [Client(**serialize_doc(i)) for i in items]


@router.get("/clients/busca")
async def buscar_clientes(
    q: str = "",
    limit: int = 20,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Busca incremental por nome / CPF-CNPJ / telefone (fonte do ClientePicker).
    Mínimo 2 caracteres; case-insensitive; escopo do usuário."""
    termo = (q or "").strip()
    if len(termo) < 2:
        return []
    import re
    rgx = re.compile(re.escape(termo), re.IGNORECASE)
    so_digitos = _digits(termo)
    ors = [{"name": rgx}, {"phone": rgx}, {"email": rgx}]
    if so_digitos:
        ors.append({"doc": re.compile(re.escape(so_digitos))})
    itens = await db.clients.find(
        {"user_id": uid, "$or": ors}
    ).sort("name", 1).to_list(max(1, min(limit, 50)))
    out = []
    for i in itens:
        c = serialize_doc(i)
        out.append({
            "id": c.get("id"),
            "name": c.get("name", ""),
            "type": c.get("type", ""),
            "doc": c.get("doc", ""),
            "phone": c.get("phone", ""),
            "email": c.get("email", ""),
            "estado_civil": c.get("estado_civil", ""),
            "origem": c.get("origem", ""),
            "foto_thumb_key": c.get("foto_thumb_key"),
            "tem_conjuge": bool(c.get("conjuge")),
            "qtd_documentos": len(c.get("documentos") or []),
        })
    return out


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
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    await db.clients.update_one({"id": cid}, {"$set": updates})
    new_doc = await db.clients.find_one({"id": cid})
    return Client(**serialize_doc(new_doc))


@router.post("/clients/importar-ptam")
async def importar_clientes_ptam(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Importa os solicitantes cadastrados nos PTAMs do usuário para a base de Clientes.

    Idempotente: dedupe por CPF/CNPJ (quando houver) ou por nome. Não sobrescreve
    clientes já existentes — apenas cria os que faltam.
    """
    ptams = await db.ptam_documents.find({"user_id": uid}).to_list(5000)
    existentes = await db.clients.find({"user_id": uid}).to_list(10000)

    docs_exist = {_digits(c.get("doc")) for c in existentes if _digits(c.get("doc"))}
    nomes_exist = {(c.get("name") or "").strip().lower() for c in existentes if c.get("name")}

    novos: List[dict] = []
    vistos_doc, vistos_nome = set(), set()
    for p in ptams:
        nome = (p.get("solicitante_nome") or p.get("solicitante") or "").strip()
        if not nome:
            continue
        doc_raw = (p.get("solicitante_cpf_cnpj") or "").strip()
        dd = _digits(doc_raw)
        chave_nome = nome.lower()

        if dd:
            if dd in docs_exist or dd in vistos_doc:
                continue
            vistos_doc.add(dd)
        else:
            if chave_nome in nomes_exist or chave_nome in vistos_nome:
                continue
            vistos_nome.add(chave_nome)

        tipo = "Pessoa Jurídica" if len(dd) == 14 else "Pessoa Física"
        c = Client(
            user_id=uid,
            name=nome,
            type=tipo,
            doc=doc_raw,
            phone=(p.get("solicitante_telefone") or ""),
            email=(p.get("solicitante_email") or ""),
            endereco=(p.get("solicitante_endereco") or ""),
            city=(p.get("property_city") or ""),
            uf=(p.get("property_state") or ""),
            origem="ptam",
        )
        novos.append(c.model_dump())

    if novos:
        await db.clients.insert_many(novos)

    return {"importados": len(novos), "total_ptams": len(ptams)}


@router.delete("/clients/{cid}")
async def delete_client(cid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.clients.delete_one({"id": cid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"ok": True}
