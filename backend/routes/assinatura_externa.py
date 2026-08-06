# @module routes.assinatura_externa — Assinatura Digital Externa BYOK (PR1: credenciais).
# Prefixo montado sob /api → /api/assinatura-externa/* (convenção do repo; sem /v1).
# Adapters/envio/webhook/polling entram nas PRs seguintes.
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from db import get_db
from dependencies import get_active_subscriber
from models.assinatura_externa import CredencialInput, EnvioInput
from services.assinatura import credenciais as CRED
from services.assinatura import envios as ENV
from services.assinatura import factory, origem_pdf
from services.assinatura.base import CredencialNaoConfigurada, OpcoesEnvio, ProviderError, SignatarioEnvio
from services.assinatura.catalogo import catalogo_publico
from services.ratelimit import pub_limiter

logger = logging.getLogger("romatec")
router = APIRouter(tags=["assinatura-externa"], prefix="/assinatura-externa")
router_publico = APIRouter(tags=["assinatura-externa"], prefix="/assinatura-externa")


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


# ── Envios ────────────────────────────────────────────────────────────────────
@router.post("/envios", status_code=201)
async def criar_envio(body: EnvioInput, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    provider = body.provider
    if not provider:                       # usa o provedor padrão do usuário
        creds = await CRED.listar(db, uid)
        pad = next((c for c in creds if c.get("padrao")), None) or (creds[0] if creds else None)
        if not pad:
            raise HTTPException(status_code=409, detail={"codigo": "PROVIDER_NAO_CONFIGURADO",
                                                         "mensagem": "nenhum provedor configurado"})
        provider = pad["provider"]
    try:
        pdf_bytes, nome = await origem_pdf.resolver(db, uid, body.origem_tipo, body.origem_id)
    except origem_pdf.OrigemNaoSuportada as e:
        raise HTTPException(status_code=422, detail=str(e))
    sigs = [SignatarioEnvio(nome=s.get("nome", ""), email=s.get("email"), whatsapp=s.get("whatsapp"),
                            cpf_cnpj=s.get("cpf_cnpj"), papel=s.get("papel", "signatario"),
                            autenticacao=s.get("autenticacao") or ["email"], ordem=s.get("ordem"))
            for s in (body.signatarios or [])]
    if not sigs:
        raise HTTPException(status_code=422, detail="informe ao menos 1 signatário")
    o = body.opcoes or {}
    opc = OpcoesEnvio(mensagem=o.get("mensagem"), prazo_dias=o.get("prazo_dias"),
                      lembrete_automatico=o.get("lembrete_automatico", True),
                      ordem_sequencial=o.get("ordem_sequencial", False),
                      pasta_destino=o.get("pasta_destino"))
    try:
        return await ENV.criar_envio(db, uid, provider, body.origem_tipo, body.origem_id, pdf_bytes, nome, sigs, opc)
    except CredencialNaoConfigurada as e:
        raise HTTPException(status_code=409, detail={"codigo": e.codigo, "mensagem": str(e)})
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/envios")
async def listar_envios(status: str = None, provider: str = None, origem_tipo: str = None,
                        uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await ENV.listar_envios(db, uid, status, provider, origem_tipo)


@router.get("/envios/{envio_id}")
async def obter_envio(envio_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    envio = await ENV.obter_raw(db, uid, envio_id)
    if not envio:
        raise HTTPException(status_code=404, detail="envio não encontrado")
    return ENV._slim(envio)


@router.post("/envios/{envio_id}/sincronizar")
async def sincronizar_envio(envio_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    envio = await ENV.obter_raw(db, uid, envio_id)
    if not envio:
        raise HTTPException(status_code=404, detail="envio não encontrado")
    try:
        return {"status": await ENV.sincronizar(db, uid, envio)}
    except (CredencialNaoConfigurada, ProviderError) as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/envios/{envio_id}/cancelar")
async def cancelar_envio(envio_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    envio = await ENV.obter_raw(db, uid, envio_id)
    if not envio:
        raise HTTPException(status_code=404, detail="envio não encontrado")
    try:
        await ENV.cancelar(db, uid, envio, "cancelado pelo usuário")
        return {"ok": True}
    except (CredencialNaoConfigurada, ProviderError) as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/envios/{envio_id}/arquivo-assinado")
async def arquivo_assinado(envio_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    envio = await ENV.obter_raw(db, uid, envio_id)
    if not envio:
        raise HTTPException(status_code=404, detail="envio não encontrado")
    try:
        pdf = await ENV.baixar_assinado(db, uid, envio)
    except (CredencialNaoConfigurada, ProviderError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    nome = envio.get("nome_documento") or "assinado.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nome}"', "Cache-Control": "no-store"})


# ── Webhook (PÚBLICO, sem JWT — validado por HMAC/envio_id) ────────────────────
@router_publico.post("/webhook/{provider}/{envio_id}")
@pub_limiter.limit("240/minute")
async def webhook(provider: str, envio_id: str, request: Request, db=Depends(get_db)):
    raw = await request.body()
    try:
        body = json.loads(raw or b"{}")
        if not isinstance(body, dict):
            body = {}
    except Exception:  # noqa: BLE001
        body = {}
    try:
        return await ENV.processar_webhook(db, provider, envio_id, dict(request.headers), raw, body)
    except ENV.WebhookInvalido:
        raise HTTPException(status_code=401, detail="assinatura inválida")
    except Exception as e:  # noqa: BLE001 — sempre 200 rápido; o polling recupera
        logger.warning("webhook assinatura falhou: %s", e)
        return {"ok": True}
