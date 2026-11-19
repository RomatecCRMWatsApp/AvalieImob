# @module routes.blog_metricas — rota PÚBLICA que conta leituras e cliques nos artigos.
# SEM `from __future__ import annotations`: com o wrapper do slowapi, o FastAPI deixa de
# reconhecer o corpo Pydantic e responde 422 (ver v1.4.980).
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from db import get_db
from services import blog_metricas as BM
from services.ratelimit import pub_limiter

router = APIRouter(prefix="/blog", tags=["Blog · Métricas"])


class EventoBlogIn(BaseModel):
    slug: str = Field(max_length=120)
    tipo: str = Field(max_length=20)
    posicao: str = Field(default="pagina", max_length=20)


@router.post("/evento")
@pub_limiter.limit("60/minute")
async def registrar_evento(dados: EventoBlogIn, request: Request, db=Depends(get_db)):
    erro = BM.valida(dados.slug, dados.tipo, dados.posicao)
    if erro:
        raise HTTPException(422, erro)
    dia = BM.dia_hoje()
    await db[BM.COL].update_one(
        {"_id": BM.chave(dia, dados.slug, dados.tipo, dados.posicao)},
        {"$inc": {"n": 1},
         "$set": {"dia": dia, "slug": dados.slug, "tipo": dados.tipo,
                  "posicao": dados.posicao, "atualizado_em": datetime.utcnow()}},
        upsert=True,
    )
    return {"ok": True}
