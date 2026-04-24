# @module routes.cub – Endpoints CUB (Custo Unitário Básico) SINDUSCON
"""
GET  /cub?estado=SP          – retorna CUB atual (sem auth, dado público)
POST /cub/calcular           – executa cálculo do Método Evolutivo
GET  /cub/tipos              – lista tipos CUB disponíveis
POST /cub/atualizar-cache    – força refresh do cache (requer auth admin)
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from dependencies import get_active_subscriber, get_admin_user
from db import get_db
from services.cub_service import (
    get_cub,
    calcular_metodo_evolutivo,
    CUB_FALLBACK,
    CUB_TIPOS_DESCRICAO,
    _chave_cache,
    _memoria_cache,
)

router = APIRouter(prefix="/cub", tags=["cub"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CalcularEvolutivoRequest(BaseModel):
    estado: Optional[str] = "SP"
    tipo_cub: Optional[str] = "R1-N"
    cub_valor_manual: Optional[float] = None   # se informado, ignora scraping
    area_construida: float
    valor_terreno: float
    fator_obsolescencia: Optional[float] = 0.0   # 0–80%
    fator_adequacao: Optional[float] = 1.0
    benfeitoria_extra: Optional[float] = 0.0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def obter_cub(
    estado: str = Query("SP", min_length=2, max_length=2, description="Sigla do estado (UF)"),
    db=Depends(get_db),
):
    """
    Retorna o CUB atual para o estado informado.
    Nunca falha: usa fallback hardcoded se scraping indisponível.
    """
    data = await get_cub(estado.upper(), db)
    return {
        "ok": True,
        "estado": data["estado"],
        "mes_referencia": data["mes_referencia"],
        "fonte": data["fonte"],
        "is_fallback": data["is_fallback"],
        "valores": data["valores"],
        "atualizado_em": data["atualizado_em"],
    }


@router.post("/calcular")
async def calcular_evolutivo(
    payload: CalcularEvolutivoRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """
    Executa o cálculo do Método Evolutivo (NBR 14.653-2:2011, item 8.2.1.2).
    Usa CUB do estado informado ou valor manual fornecido.
    """
    cub_data = await get_cub(payload.estado or "SP", db)

    # Determinar valor CUB
    if payload.cub_valor_manual and payload.cub_valor_manual > 0:
        cub_valor = payload.cub_valor_manual
        fonte_cub = f"Manual – {payload.tipo_cub or 'informado pelo usuário'}"
        is_fallback = False
    else:
        tipo = payload.tipo_cub or "R1-N"
        cub_valor = cub_data["valores"].get(tipo)
        if not cub_valor:
            cub_valor = CUB_FALLBACK.get(tipo, CUB_FALLBACK["R1-N"])
        fonte_cub = cub_data["fonte"]
        is_fallback = cub_data["is_fallback"]

    resultado = calcular_metodo_evolutivo(
        cub_valor=cub_valor,
        area_construida=payload.area_construida,
        valor_terreno=payload.valor_terreno,
        fator_obsolescencia=payload.fator_obsolescencia or 0.0,
        fator_adequacao=payload.fator_adequacao or 1.0,
        benfeitoria_extra=payload.benfeitoria_extra or 0.0,
        tipo_cub=payload.tipo_cub or "R1-N",
        fonte_cub=fonte_cub,
    )

    return {
        "ok": True,
        "estado": payload.estado,
        "is_fallback": is_fallback,
        "resultado": resultado,
    }


@router.get("/tipos")
async def listar_tipos_cub():
    """Lista todos os tipos CUB disponíveis com valores de referência."""
    tipos = []
    for codigo, descricao in CUB_TIPOS_DESCRICAO.items():
        tipos.append({
            "codigo": codigo,
            "descricao": descricao,
            "valor_referencia": CUB_FALLBACK.get(codigo, 0),
        })
    return {"ok": True, "tipos": tipos}


@router.post("/atualizar-cache")
async def atualizar_cache_cub(
    estado: str = Query("SP", min_length=2, max_length=2),
    uid: str = Depends(get_admin_user),
    db=Depends(get_db),
):
    """
    Força o refresh do cache CUB para o estado informado.
    Remove cache em memória e MongoDB para forçar novo scraping.
    """
    estado = estado.upper()
    chave = _chave_cache(estado)

    # Remove cache memória
    _memoria_cache.pop(chave, None)

    # Remove cache MongoDB
    if db is not None:
        try:
            await db.cub_cache.delete_one({"chave": chave})
        except Exception:
            pass

    # Força novo scraping
    data = await get_cub(estado, db)
    return {
        "ok": True,
        "mensagem": f"Cache atualizado para {estado}",
        "estado": data["estado"],
        "mes_referencia": data["mes_referencia"],
        "fonte": data["fonte"],
        "is_fallback": data["is_fallback"],
        "tipos_carregados": len(data["valores"]),
    }
