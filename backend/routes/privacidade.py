# @module routes.privacidade — canal de titulares (LGPD art. 18) e exportação da conta.
# SEM `from __future__ import annotations`: com o wrapper do slowapi o FastAPI deixa de
# reconhecer o corpo Pydantic e responde 422 (ver v1.4.980).
import json
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from db import get_db
from dependencies import get_admin_user, get_current_user_id
from services import privacidade as PV
from services.ratelimit import pub_limiter

router = APIRouter(prefix="/privacidade", tags=["Privacidade"])
admin_router = APIRouter(prefix="/admin/privacidade", tags=["Privacidade · Admin"])


class PedidoIn(BaseModel):
    tipo: str = Field(max_length=40)
    nome: str = Field(max_length=120)
    email: str = Field(max_length=160)
    telefone: str = Field(default="", max_length=30)
    relacao: Literal["titular", "representante"] = "titular"
    descricao: str = Field(max_length=2000)
    website: str = Field(default="", max_length=200)  # honeypot: humano não vê esse campo


class PedidoContaIn(BaseModel):
    tipo: str = Field(max_length=40)
    descricao: str = Field(max_length=2000)


class AtualizarPedidoIn(BaseModel):
    status: Optional[str] = None
    nota: str = Field(default="", max_length=1000)
    responsavel: Optional[str] = Field(default=None, max_length=120)


async def _prazos(db) -> dict:
    cfg = await db.sys_config.find_one({"_id": "privacidade_prazos"}) or {}
    return {**PV.PRAZOS_PADRAO, **{k: v for k, v in cfg.items() if k in PV.PRAZOS_PADRAO}}


def _publico(p: dict) -> dict:
    """O que o titular pode ver do próprio pedido (sem notas internas de outros)."""
    return {
        "protocolo": p.get("protocolo"), "tipo": p.get("tipo"), "tipo_label": p.get("tipo_label"),
        "status": p.get("status"), "recebida_em": p.get("recebida_em"),
        "prazo_referencia": p.get("prazo_referencia"), "concluida_em": p.get("concluida_em"),
    }


@router.get("/tipos")
async def tipos():
    return {"tipos": PV.TIPOS}


@router.post("/solicitacao")
@pub_limiter.limit("5/minute")
async def criar_solicitacao(dados: PedidoIn, request: Request, db=Depends(get_db)):
    """Pedido de titular SEM conta. Não executa nada: registra e devolve o protocolo."""
    if dados.website:
        return {"ok": True, "protocolo": None}  # robô: descarta em silêncio
    if dados.tipo == "exclusao_conta":
        raise HTTPException(422, "Para encerrar uma conta, entre no painel ou descreva o pedido em 'Eliminação'.")
    erro = PV.validar_pedido(dados.model_dump())
    if erro:
        raise HTTPException(422, erro)
    pedido = PV.montar_pedido(dados.model_dump(), prazos=await _prazos(db))
    await db[PV.COL_PEDIDOS].insert_one(pedido)
    return {"ok": True, "protocolo": pedido["protocolo"], "prazo_referencia": pedido["prazo_referencia"]}


@router.get("/meus-dados")
@pub_limiter.limit("3/minute")
async def exportar_meus_dados(request: Request, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    """Download dos dados da própria conta (JSON). Gerado na hora, não fica guardado em link."""
    dados = await PV.exportar_dados_usuario(db, uid)
    corpo = json.dumps(dados, ensure_ascii=False, indent=2, default=str)
    nome = f"avalieimob-meus-dados-{datetime.utcnow():%Y%m%d}.json"
    return Response(
        content=corpo.encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"', "Cache-Control": "no-store"},
    )


@router.post("/minhas-solicitacoes")
async def criar_minha_solicitacao(dados: PedidoContaIn, uid: str = Depends(get_current_user_id),
                                  db=Depends(get_db)):
    user = await db.users.find_one({"id": uid}) or {}
    corpo = {"tipo": dados.tipo, "descricao": dados.descricao, "nome": user.get("name") or "",
             "email": user.get("email") or "", "telefone": user.get("phone") or "", "relacao": "titular"}
    erro = PV.validar_pedido(corpo)
    if erro:
        raise HTTPException(422, erro)
    pedido = PV.montar_pedido(corpo, user_id=uid, prazos=await _prazos(db))
    await db[PV.COL_PEDIDOS].insert_one(pedido)
    return _publico(pedido)


@router.get("/minhas-solicitacoes")
async def listar_minhas(uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    docs = await db[PV.COL_PEDIDOS].find({"user_id": uid}).sort("recebida_em", -1).to_list(100)
    return {"solicitacoes": [_publico(d) for d in docs]}


@admin_router.get("/solicitacoes")
async def admin_listar(status: Optional[str] = None, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    filtro = {"status": status} if status else {}
    docs = await db[PV.COL_PEDIDOS].find(filtro).sort("recebida_em", -1).to_list(500)
    for d in docs:
        d.pop("_id", None)
    return {"solicitacoes": docs, "status": PV.STATUS, "tipos": PV.TIPOS}


@admin_router.patch("/solicitacoes/{protocolo}")
async def admin_atualizar(protocolo: str, dados: AtualizarPedidoIn, uid: str = Depends(get_admin_user),
                          db=Depends(get_db)):
    pedido = await db[PV.COL_PEDIDOS].find_one({"protocolo": protocolo})
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado.")
    try:
        upd = PV.aplicar_atualizacao(pedido, dados.status, dados.nota, por=uid, responsavel=dados.responsavel)
    except ValueError as e:
        raise HTTPException(422, str(e))
    await db[PV.COL_PEDIDOS].update_one({"protocolo": protocolo}, upd)
    return {"ok": True}
