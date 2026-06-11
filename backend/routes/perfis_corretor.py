# @module routes.perfis_corretor — Perfis de Corretor do usuário (autofill "Usar meus dados")
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.perfil_corretor import PerfilCorretor, PerfilCorretorBase

router = APIRouter(tags=["perfis_corretor"])


async def _desmarcar_padrao(db, uid: str, exceto_id: str = None):
    q = {"user_id": uid, "padrao": True}
    if exceto_id:
        q["id"] = {"$ne": exceto_id}
    await db.perfis_corretor.update_many(q, {"$set": {"padrao": False}})


@router.get("/perfis-corretor", response_model=List[PerfilCorretor])
async def listar_perfis(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Lista os perfis de corretor do usuário (padrão primeiro)."""
    itens = await db.perfis_corretor.find({"user_id": uid}).sort("created_at", -1).to_list(100)
    perfis = [PerfilCorretor(**serialize_doc(i)) for i in itens]
    perfis.sort(key=lambda p: not p.padrao)  # padrão no topo
    return perfis


@router.post("/perfis-corretor", response_model=PerfilCorretor)
async def criar_perfil(
    data: PerfilCorretorBase,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Cria um perfil. Se marcado como padrão, desmarca os demais."""
    perfil = PerfilCorretor(user_id=uid, **data.model_dump())
    # Primeiro perfil do usuário vira padrão automaticamente
    total = await db.perfis_corretor.count_documents({"user_id": uid})
    if total == 0:
        perfil.padrao = True
    if perfil.padrao:
        await _desmarcar_padrao(db, uid)
    await db.perfis_corretor.insert_one(perfil.model_dump())
    return perfil


@router.put("/perfis-corretor/{pid}", response_model=PerfilCorretor)
async def atualizar_perfil(
    pid: str,
    data: PerfilCorretorBase,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.perfis_corretor.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    if updates.get("padrao"):
        await _desmarcar_padrao(db, uid, exceto_id=pid)
    await db.perfis_corretor.update_one({"id": pid, "user_id": uid}, {"$set": updates})
    novo = await db.perfis_corretor.find_one({"id": pid})
    return PerfilCorretor(**serialize_doc(novo))


@router.put("/perfis-corretor/{pid}/padrao", response_model=PerfilCorretor)
async def marcar_padrao(
    pid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Marca o perfil como padrão (desmarca os demais)."""
    doc = await db.perfis_corretor.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    await _desmarcar_padrao(db, uid, exceto_id=pid)
    await db.perfis_corretor.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"padrao": True, "updated_at": datetime.utcnow()}},
    )
    novo = await db.perfis_corretor.find_one({"id": pid})
    return PerfilCorretor(**serialize_doc(novo))


@router.delete("/perfis-corretor/{pid}")
async def excluir_perfil(
    pid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    res = await db.perfis_corretor.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    # Se sobrou algum perfil e nenhum é padrão, promove o mais recente
    if not await db.perfis_corretor.find_one({"user_id": uid, "padrao": True}):
        prox = await db.perfis_corretor.find({"user_id": uid}).sort("created_at", -1).to_list(1)
        if prox:
            await db.perfis_corretor.update_one(
                {"id": prox[0]["id"]}, {"$set": {"padrao": True}}
            )
    return {"ok": True}


@router.post("/perfis-corretor/seed-romario", response_model=List[PerfilCorretor])
async def seed_perfil_romario(
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Cria (idempotente) os perfis do José Romário — PF + PJ Romatec — para o
    usuário logado, com os dados/credenciais já conhecidos. Não duplica por CPF/CNPJ."""
    criados = []

    pf_existe = await db.perfis_corretor.find_one({"user_id": uid, "tipo_pessoa": "fisica"})
    if not pf_existe:
        pf = PerfilCorretor(
            user_id=uid, tipo_pessoa="fisica", apelido="José Romário (PF)", padrao=True,
            nome="José Romário", cpf="012.091.853-69", rg="143685920001",
            orgao_emissor="SSP/MA", data_nascimento="1987-04-22", estado_civil="casado(a)",
            profissao="Técnico em Transações Imobiliárias", nacionalidade="brasileiro(a)",
            creci="CRECI/MA 4.705", cnai="031161", cft="CFT/MA 01209185369",
            email="romateccrm@gmail.com", telefone="99991811246",
            endereco="Rua São Raimundo, nº 10", cidade="Açailândia", uf="MA", cep="65930-000",
            regime_bens="comunhão parcial de bens",
            conjuge={
                "nome": "Giegilla Barros Santos Bezerra", "cpf": "037.703.693-51",
                "rg": "0150614520002", "data_nascimento": "1989-10-07",
                "profissao": "Fisioterapeuta", "nacionalidade": "brasileira",
            },
        )
        await _desmarcar_padrao(db, uid)
        await db.perfis_corretor.insert_one(pf.model_dump())
        criados.append(pf)

    pj_existe = await db.perfis_corretor.find_one({"user_id": uid, "tipo_pessoa": "juridica"})
    if not pj_existe:
        pj = PerfilCorretor(
            user_id=uid, tipo_pessoa="juridica", apelido="Romatec (PJ)", padrao=False,
            razao_social="Romatec Consultoria Total", cnpj="17.261.987/0001-09",
            representante="José Romário", creci="CRECI/MA 4.705", cnai="031161",
            cft="CFT/MA 01209185369", email="romateccrm@gmail.com", telefone="99991811246",
            endereco="Rua São Raimundo, nº 10", cidade="Açailândia", uf="MA", cep="65930-000",
        )
        await db.perfis_corretor.insert_one(pj.model_dump())
        criados.append(pj)

    return criados
