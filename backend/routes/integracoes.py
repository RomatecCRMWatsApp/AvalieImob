# @module routes.integracoes — Credenciais por usuário (Z-API, Telegram)
"""
Rotas:
  GET   /api/integracoes                         retorna config (com tokens mascarados)
  PUT   /api/integracoes                         salva/atualiza credenciais
  POST  /api/integracoes/zapi/testar             valida conexão Z-API
  POST  /api/integracoes/telegram/testar         envia msg de teste pro chat_id
"""
import logging
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db
from dependencies import get_active_subscriber
from models import Integracoes, IntegracoesBase, IntegracoesPublic, mascarar_token

logger = logging.getLogger("romatec")
router = APIRouter(tags=["integracoes"], prefix="/integracoes")


def _to_public(doc: Optional[dict]) -> dict:
    """Mascara tokens antes de retornar ao frontend."""
    if not doc:
        return IntegracoesPublic(
            has_zapi=False,
            has_meta=False,
            has_telegram=False,
            zapi_ativo=False,
            meta_ativo=False,
            telegram_ativo=False,
            whatsapp_provider="zapi",
        ).model_dump()
    return {
        "id": doc.get("id"),
        "user_id": doc.get("user_id"),
        "whatsapp_provider": doc.get("whatsapp_provider") or "zapi",
        # Z-API (mascarados)
        "zapi_instance_id": doc.get("zapi_instance_id"),
        "zapi_token": mascarar_token(doc.get("zapi_token")),
        "zapi_security_token": mascarar_token(doc.get("zapi_security_token")),
        "zapi_ativo": doc.get("zapi_ativo", False),
        # Meta (mascarados)
        "meta_phone_number_id": doc.get("meta_phone_number_id"),
        "meta_access_token": mascarar_token(doc.get("meta_access_token")),
        "meta_business_account_id": doc.get("meta_business_account_id"),
        "meta_ativo": doc.get("meta_ativo", False),
        # Telegram
        "telegram_bot_token": mascarar_token(doc.get("telegram_bot_token")),
        "telegram_chat_id_default": doc.get("telegram_chat_id_default"),
        "telegram_ativo": doc.get("telegram_ativo", False),
        # Indicadores
        "has_zapi": bool(doc.get("zapi_instance_id") and doc.get("zapi_token")),
        "has_meta": bool(doc.get("meta_phone_number_id") and doc.get("meta_access_token")),
        "has_telegram": bool(doc.get("telegram_bot_token")),
    }


class IntegracoesUpdate(BaseModel):
    whatsapp_provider: Optional[str] = None  # "zapi" | "meta"
    # Z-API
    zapi_instance_id: Optional[str] = None
    zapi_token: Optional[str] = None
    zapi_security_token: Optional[str] = None
    zapi_ativo: Optional[bool] = None
    # Meta
    meta_phone_number_id: Optional[str] = None
    meta_access_token: Optional[str] = None
    meta_business_account_id: Optional[str] = None
    meta_ativo: Optional[bool] = None
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id_default: Optional[str] = None
    telegram_ativo: Optional[bool] = None


# ── GET /integracoes ────────────────────────────────────────────────────────

@router.get("")
async def get_integracoes(
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.integracoes.find_one({"user_id": uid})
    return _to_public(doc)


# ── PUT /integracoes ────────────────────────────────────────────────────────

@router.put("")
async def update_integracoes(
    body: IntegracoesUpdate,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Atualiza credenciais. Tokens mascarados (com **** no início) são ignorados
    pra preservar o valor antigo — frontend manda o token cru só quando o
    usuário acabou de digitar."""
    update = {}
    for field, value in body.model_dump(exclude_unset=True).items():
        if isinstance(value, str) and value.startswith("****"):
            continue  # mascarado, ignora
        update[field] = value

    if not update:
        raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")

    update["updated_at"] = datetime.utcnow()

    existing = await db.integracoes.find_one({"user_id": uid})
    if existing:
        await db.integracoes.update_one({"user_id": uid}, {"$set": update})
    else:
        novo = Integracoes(user_id=uid, **{k: v for k, v in update.items() if k != "updated_at"})
        await db.integracoes.insert_one(novo.model_dump())

    doc = await db.integracoes.find_one({"user_id": uid})
    return _to_public(doc)


# ── POST /integracoes/zapi/testar ───────────────────────────────────────────

@router.post("/zapi/testar")
async def testar_zapi(
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    from services import zapi_service
    cfg = await db.integracoes.find_one({"user_id": uid})
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(status_code=400, detail="Z-API não configurado")
    try:
        info = await zapi_service.status_instance(
            cfg["zapi_instance_id"],
            cfg["zapi_token"],
            cfg.get("zapi_security_token"),
        )
        return {"ok": True, "status": info}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha no teste Z-API: {e}")


# ── POST /integracoes/meta/testar ───────────────────────────────────────────

@router.post("/meta/testar")
async def testar_meta(
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    from services import meta_whatsapp_service as meta
    cfg = await db.integracoes.find_one({"user_id": uid})
    if not cfg or not cfg.get("meta_phone_number_id") or not cfg.get("meta_access_token"):
        raise HTTPException(status_code=400, detail="Meta WhatsApp não configurado")
    try:
        info = await meta.status_check(
            phone_number_id=cfg["meta_phone_number_id"],
            access_token=cfg["meta_access_token"],
        )
        return {"ok": True, "status": info}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha no teste Meta: {e}")


# ── POST /integracoes/whatsapp/enviar-teste ─────────────────────────────────

class WhatsAppTestRequest(BaseModel):
    phone: str  # com DDI+DDD, só dígitos
    mensagem: Optional[str] = "Teste de integração WhatsApp — Romatec AvalieImob ✓"


@router.post("/whatsapp/enviar-teste")
async def whatsapp_enviar_teste(
    body: WhatsAppTestRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Envia uma mensagem de TEXTO de teste pro número informado.
    Usa o provedor configurado em whatsapp_provider (zapi ou meta).
    """
    from services import zapi_service
    from services import meta_whatsapp_service as meta_svc

    cfg = await db.integracoes.find_one({"user_id": uid})
    if not cfg:
        raise HTTPException(status_code=400, detail="Integração não configurada")
    provider = (cfg.get("whatsapp_provider") or "zapi").lower()

    if provider == "meta":
        if not cfg.get("meta_phone_number_id") or not cfg.get("meta_access_token"):
            raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada")
        url = f"{meta_svc.META_BASE}/{cfg['meta_phone_number_id']}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": meta_svc._normalize_phone(body.phone),
            "type": "text",
            "text": {"body": body.mensagem},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {cfg['meta_access_token']}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Meta erro {r.status_code}: {r.text[:200]}")
            return {"ok": True, "provider": "meta", "response": r.json()}

    # Z-API
    if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(status_code=400, detail="Z-API não configurada")
    try:
        resp = await zapi_service.send_text(
            instance_id=cfg["zapi_instance_id"],
            token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"),
            phone=body.phone,
            message=body.mensagem,
        )
        return {"ok": True, "provider": "zapi", "response": resp}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro Z-API: {e}")


# ── POST /integracoes/telegram/testar ───────────────────────────────────────

class TelegramTestRequest(BaseModel):
    chat_id: Optional[str] = None
    mensagem: Optional[str] = "Teste de integração — Romatec AvalieImob ✓"


@router.post("/telegram/testar")
async def testar_telegram(
    body: TelegramTestRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    cfg = await db.integracoes.find_one({"user_id": uid})
    if not cfg or not cfg.get("telegram_bot_token"):
        raise HTTPException(status_code=400, detail="Telegram não configurado")
    chat_id = body.chat_id or cfg.get("telegram_chat_id_default")
    if not chat_id:
        raise HTTPException(status_code=400, detail="Informe um chat_id ou configure um padrão")
    url = f"https://api.telegram.org/bot{cfg['telegram_bot_token']}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": body.mensagem})
            if r.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Telegram erro {r.status_code}: {r.text[:200]}",
                )
            return {"ok": True, "telegram_response": r.json()}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Erro de rede Telegram: {e}")
