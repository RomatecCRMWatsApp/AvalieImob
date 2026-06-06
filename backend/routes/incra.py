# @module routes.incra — Tabelas de referência INCRA (Valores de Terra Nua) para laudos rurais
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.incra import IncraTabela, IncraTabelaBase

router = APIRouter(tags=["incra"])
logger = logging.getLogger("romatec")


def _normaliza_faixas(faixas: list) -> list:
    """Garante vr_medio quando não informado: (min+max)/2."""
    out = []
    for f in faixas or []:
        d = f.model_dump() if hasattr(f, "model_dump") else dict(f)
        vmin = float(d.get("vr_min") or 0)
        vmax = float(d.get("vr_max") or 0)
        if not d.get("vr_medio"):
            d["vr_medio"] = round((vmin + vmax) / 2, 2) if (vmin or vmax) else 0.0
        out.append(d)
    return out


@router.get("/incra/tabela-vigente")
async def get_tabela_vigente(
    municipio: Optional[str] = None,
    regiao: Optional[str] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Última tabela INCRA vigente. Preferência: município → região → qualquer.
    Ordena por ano/mês desc. 404 se não houver nenhuma cadastrada."""
    candidatos = []
    if municipio:
        candidatos.append({"ativo": True, "municipio": {"$regex": f"^{municipio}$", "$options": "i"}})
    if regiao:
        candidatos.append({"ativo": True, "regiao": {"$regex": f"^{regiao}$", "$options": "i"}})
    candidatos.append({"ativo": True})  # fallback: tabela mais recente de qualquer região

    for q in candidatos:
        doc = await db.incra_tabelas.find_one(q, sort=[("ano", -1), ("mes", -1)])
        if doc:
            return serialize_doc(doc)
    raise HTTPException(status_code=404, detail="Nenhuma tabela INCRA cadastrada")


@router.get("/incra/tabelas", response_model=List[dict])
async def listar_tabelas(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Lista todas as tabelas INCRA cadastradas (mais recentes primeiro)."""
    docs = await db.incra_tabelas.find({}).sort([("ano", -1), ("mes", -1)]).to_list(2000)
    return [serialize_doc(d) for d in docs]


@router.post("/incra/tabela")
async def criar_tabela(data: IncraTabelaBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Cadastra nova tabela INCRA."""
    if not data.faixas:
        raise HTTPException(status_code=400, detail="Informe ao menos uma faixa de valor")
    tabela = IncraTabela(**data.model_dump(), user_id=uid)
    doc = tabela.model_dump(mode="json")
    doc["faixas"] = _normaliza_faixas(data.faixas)
    await db.incra_tabelas.insert_one(doc)
    logger.info("INCRA: %s cadastrou tabela %s/%s (%s-%s)", uid, data.regiao,
                data.municipio or "—", data.ano, data.mes)
    return serialize_doc(doc)


@router.put("/incra/tabela/{tid}")
async def editar_tabela(tid: str, data: IncraTabelaBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Edita uma tabela INCRA existente."""
    if not data.faixas:
        raise HTTPException(status_code=400, detail="Informe ao menos uma faixa de valor")
    upd = data.model_dump()
    upd["faixas"] = _normaliza_faixas(data.faixas)
    upd["updated_at"] = datetime.utcnow()
    res = await db.incra_tabelas.update_one({"id": tid}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tabela não encontrada")
    doc = await db.incra_tabelas.find_one({"id": tid})
    return serialize_doc(doc)


@router.delete("/incra/tabela/{tid}")
async def remover_tabela(tid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Exclui definitivamente uma tabela INCRA."""
    res = await db.incra_tabelas.delete_one({"id": tid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tabela não encontrada")
    return {"ok": True, "id": tid}


@router.post("/incra/seed-exemplo")
async def seed_exemplo(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Insere uma tabela INCRA de EXEMPLO (para testar o visual). Idempotente.
    Valores fictícios — substituir pela tabela oficial depois."""
    import uuid as _uuid
    regiao = "MRT Pré-Amazônico — Polo Imperatriz/Açailândia"
    vigencia = "RAMT-MA 2022"
    existe = await db.incra_tabelas.find_one({"regiao": regiao, "vigencia": vigencia, "ativo": True})
    if existe:
        return {"ok": True, "ja_existia": True, "id": existe.get("id")}
    tabela = {
        "id": str(_uuid.uuid4()),
        "regiao": regiao,
        "municipio": "Açailândia",
        "ano": 2022,
        "mes": 7,
        "vigencia": vigencia,
        "fonte": "INCRA/SR-21-MA — RAMT-MA 2022 (VTI R$/ha — atualizar por IPCA-E)",
        "faixas": [
            {"faixa": "Pastagem formada — cap. alta (pecuária bovina)", "vr_min": 11230.0, "vr_max": 20857.0, "vr_medio": 16044.0},
            {"faixa": "Pastagem nativa/formada — cap. baixa (pecuária extensiva)", "vr_min": 6961.0, "vr_max": 12927.0, "vr_medio": 9944.0},
            {"faixa": "Vegetação nativa — floresta amazônica/transição/capoeira", "vr_min": 2640.0, "vr_max": 4903.0, "vr_medio": 3771.0},
            {"faixa": "Uso indefinido / misto (geral MRT-1)", "vr_min": 1800.0, "vr_max": 250000.0, "vr_medio": 11360.0},
        ],
        "user_id": uid,
        "ativo": True,
        "created_at": datetime.utcnow(),
    }
    await db.incra_tabelas.insert_one(tabela)
    return serialize_doc(tabela)
