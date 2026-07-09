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
        _rx = {"$regex": f"^{municipio.strip()}$", "$options": "i"}
        # casa o município principal OU a lista de municípios cobertos pelo polo
        candidatos.append({"ativo": True, "$or": [{"municipio": _rx}, {"municipios": _rx}]})
    if regiao:
        candidatos.append({"ativo": True, "regiao": {"$regex": f"^{regiao.strip()}$", "$options": "i"}})
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


@router.get("/incra/tabela/{tid}")
async def buscar_tabela(tid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Busca uma tabela INCRA específica pelo id."""
    doc = await db.incra_tabelas.find_one({"id": tid})
    if not doc:
        raise HTTPException(status_code=404, detail="Tabela não encontrada")
    return serialize_doc(doc)


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
    # Blindagem multi-inquilino: só o DONO edita a própria tabela (ninguém altera a
    # de outro assinante nem a semente oficial). A leitura segue compartilhada.
    res = await db.incra_tabelas.update_one({"id": tid, "user_id": uid}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tabela não encontrada ou sem permissão")
    doc = await db.incra_tabelas.find_one({"id": tid})
    return serialize_doc(doc)


@router.delete("/incra/tabela/{tid}")
async def remover_tabela(tid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Exclui definitivamente uma tabela INCRA."""
    # Só o DONO exclui a própria tabela (não a de outro assinante nem a semente).
    res = await db.incra_tabelas.delete_one({"id": tid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tabela não encontrada ou sem permissão")
    return {"ok": True, "id": tid}


# ── Dados oficiais RAMT-MA 2022 (INCRA/SR-21-MA) — fonte da carga padrão ──────
_FATORES_RAMT = [
    {"fator": "Localização / acesso", "variavel": "Distância BR/MA, proximidade polo", "faixa_ajuste": "0,70 – 1,30"},
    {"fator": "Aptidão agrícola", "variavel": "Classe I–VI (Ramalho Filho & Beek)", "faixa_ajuste": "0,60 – 1,40"},
    {"fator": "Topografia / relevo", "variavel": "Plano a suave-ondulado / acidentado", "faixa_ajuste": "0,80 – 1,20"},
    {"fator": "Dimensão do imóvel", "variavel": "Área total em ha (fator escala)", "faixa_ajuste": "0,80 – 1,10"},
    {"fator": "Disponibilidade hídrica", "variavel": "Presença de cursos d'água, açude", "faixa_ajuste": "0,90 – 1,15"},
    {"fator": "Contemporaneidade", "variavel": "Atualização IPCA (base: jul/2022)", "faixa_ajuste": "Ver IPCA acumulado"},
]
_NOTAS_RAMT = (
    "(1) VTI = Valor Total do Imóvel (inclui benfeitorias); para obter VTN deduzir benfeitorias "
    "conforme laudo de vistoria. (2) Faixas mín/máx estimadas pelo perito aplicando ±30% sobre a "
    "média amostral, conforme metodologia INCRA PPR. (3) Atualização monetária obrigatória via "
    "IPCA-E entre data-base jul/2022 e data da avaliação (NBR 14653-3, item 8.2.1). (4) Dados de "
    "pesquisa primária do avaliador devem complementar e prevalecer sobre os referenciais do RAMT "
    "quando disponíveis (NBR 14653-3, item 8.1). (5) Fonte: INCRA/SR-21-MA — RAMT-MA 2022, "
    "SEI n.º 15897588 / PPR SR(MA) 15854957."
)


def _tabelas_ramt_ma_2022(uid=None):
    """As duas tabelas RAMT-MA 2022 (polos Imperatriz e Buriticupu) prontas para inserção."""
    import uuid as _uuid
    base = dict(regiao="MRT Pré-Amazônico", norma="NBR 14653-3:2019", ano=2022, mes=7,
                vigencia="RAMT-MA 2022", fonte="INCRA/SR-21-MA — RAMT-MA 2022",
                fatores=_FATORES_RAMT, notas=_NOTAS_RAMT, ativo=True)
    imperatriz = {
        **base, "id": str(_uuid.uuid4()), "municipio": "Açailândia",
        "municipios": ["Açailândia", "Cidelândia", "Itinga", "Imperatriz", "São Francisco do Brejão",
                       "Buritirana", "Amarante do Maranhão", "Montes Altos"],
        "polo_regional": "Imperatriz / Açailândia",
        "faixas": [
            {"faixa": "Pastagem formada — cap. alta (pecuária bovina)", "vr_min": 11230.0, "vr_max": 20857.0, "vr_medio": 16044.0, "n_amostras": 32},
            {"faixa": "Pastagem nativa/formada — cap. baixa (pecuária extensiva)", "vr_min": 6961.0, "vr_max": 12927.0, "vr_medio": 9944.0, "n_amostras": 11},
            {"faixa": "Vegetação nativa — floresta amazônica / transição / capoeira", "vr_min": 2640.0, "vr_max": 4903.0, "vr_medio": 3771.0, "n_amostras": 3},
            {"faixa": "Uso indefinido / misto (geral MRT-1)", "vr_min": 1800.0, "vr_max": 250000.0, "vr_medio": 11360.0, "n_amostras": 131},
        ],
        "user_id": uid, "created_at": datetime.utcnow(),
    }
    buriticupu = {
        **base, "id": str(_uuid.uuid4()), "municipio": "Buriticupu",
        "municipios": ["Buriticupu", "Santa Luzia", "Bom Jardim", "Bom Jesus das Selvas"],
        "polo_regional": "Buriticupu",
        "faixas": [
            {"faixa": "Agrícola — grãos diversos — cap. alta (soja/milho/algodão)", "vr_min": 29674.0, "vr_max": 55110.0, "vr_medio": 42392.0, "n_amostras": 3},
            {"faixa": "Agrícola — grãos diversos — cap. média", "vr_min": 13812.0, "vr_max": 25651.0, "vr_medio": 19732.0, "n_amostras": 11},
            {"faixa": "Pastagem formada — cap. alta", "vr_min": 8834.0, "vr_max": 16406.0, "vr_medio": 12620.0, "n_amostras": 16},
            {"faixa": "Pastagem nativa/formada — cap. baixa", "vr_min": 4811.0, "vr_max": 8934.0, "vr_medio": 6872.0, "n_amostras": 24},
            {"faixa": "Vegetação nativa — floresta amazônica / capoeira", "vr_min": 1505.0, "vr_max": 2795.0, "vr_medio": 2150.0, "n_amostras": 2},
        ],
        "user_id": uid, "created_at": datetime.utcnow(),
    }
    return [imperatriz, buriticupu]


async def seed_incra_default(db):
    """Carga padrão das tabelas RAMT-MA 2022 (idempotente) — chamada na inicialização."""
    inseridas = 0
    for tab in _tabelas_ramt_ma_2022(uid=None):
        existe = await db.incra_tabelas.find_one(
            {"regiao": tab["regiao"], "polo_regional": tab["polo_regional"], "vigencia": tab["vigencia"]}
        )
        if not existe:
            await db.incra_tabelas.insert_one(dict(tab))
            inseridas += 1
    if inseridas:
        logger.info("INCRA: carga padrão RAMT-MA 2022 — %d tabela(s) inserida(s)", inseridas)
    return inseridas


@router.post("/incra/seed-exemplo")
async def seed_exemplo(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Insere as tabelas RAMT-MA 2022 (polos Imperatriz e Buriticupu) com tipologias,
    fatores de homogeneização e notas técnicas. Idempotente."""
    inseridas = 0
    ids = []
    for tab in _tabelas_ramt_ma_2022(uid=uid):
        existe = await db.incra_tabelas.find_one(
            {"regiao": tab["regiao"], "polo_regional": tab["polo_regional"], "vigencia": tab["vigencia"], "ativo": True}
        )
        if existe:
            ids.append(existe.get("id"))
            continue
        await db.incra_tabelas.insert_one(dict(tab))
        ids.append(tab["id"])
        inseridas += 1
    return {"ok": True, "inseridas": inseridas, "ja_existia": inseridas == 0, "ids": ids}
