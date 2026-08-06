# @module routes.assinatura_externa — Assinatura Digital Externa BYOK (PR1: credenciais).
# Prefixo montado sob /api → /api/assinatura-externa/* (convenção do repo; sem /v1).
# Adapters/envio/webhook/polling entram nas PRs seguintes.
import logging

from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from dependencies import get_active_subscriber
from models.assinatura_externa import CredencialInput
from services.assinatura import credenciais as CRED
from services.assinatura import factory
from services.assinatura.base import CredencialNaoConfigurada
from services.assinatura.catalogo import catalogo_publico

logger = logging.getLogger("romatec")
router = APIRouter(tags=["assinatura-externa"], prefix="/assinatura-externa")


@router.get("/provedores")
async def provedores(uid: str = Depends(get_active_subscriber)):
    """Catálogo estático dos provedores (campos, capacidades, ajuda) — sem segredos."""
    return {"provedores": catalogo_publico()}


@router.get("/credenciais")
async def listar_credenciais(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Credenciais do usuário, com os valores MASCARADOS."""
    return await CRED.listar(db, uid)


@router.post("/credenciais")
async def salvar_credencial(body: CredencialInput,
                            uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Cria/atualiza (upsert por user_id+provider). Cifra as credenciais."""
    try:
        return await CRED.salvar(db, uid, body.provider, body.ambiente, body.credenciais, body.padrao)
    except CRED.CredencialInvalida as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/credenciais/{provider}/padrao")
async def definir_padrao(provider: str,
                         uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    ok = await CRED.definir_padrao(db, uid, provider)
    if not ok:
        raise HTTPException(status_code=404, detail="credencial não encontrada")
    return {"ok": True, "provider": provider}


@router.delete("/credenciais/{provider}")
async def remover_credencial(provider: str,
                             uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    ok = await CRED.remover(db, uid, provider)
    if not ok:
        raise HTTPException(status_code=404, detail="credencial não encontrada")
    return {"ok": True}


@router.post("/credenciais/{provider}/testar")
async def testar_conexao(provider: str,
                         uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Testa a conexão com o provedor usando a credencial do usuário e grava o resultado."""
    try:
        prov = await factory.get_provider(db, uid, provider)
    except CredencialNaoConfigurada as e:
        raise HTTPException(status_code=409, detail={"codigo": e.codigo, "mensagem": str(e)})
    res = await prov.testar_conexao()
    await CRED.registrar_teste(db, uid, provider, res.ok, res.mensagem)
    return {"ok": res.ok, "mensagem": res.mensagem, "dados": res.dados}


@router.get("/d4sign/cofres")
async def d4sign_cofres(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Lista os cofres do D4Sign p/ o usuário escolher no wizard (após o teste OK)."""
    try:
        prov = await factory.get_provider(db, uid, "d4sign")
    except CredencialNaoConfigurada as e:
        raise HTTPException(status_code=409, detail={"codigo": e.codigo, "mensagem": str(e)})
    try:
        return {"cofres": await prov.listar_cofres()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Falha ao listar cofres: {e}")
