# @module services.assinatura.envios — Ciclo de vida do envio BYOK (envio/status/webhook/polling).
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta

from services.assinatura import factory
from services.assinatura.base import OpcoesEnvio, ProviderError, SignatarioEnvio

logger = logging.getLogger("romatec")
COLL = "assinatura_envios"
COLL_EVT = "assinatura_eventos_processados"


def _now() -> datetime:
    return datetime.utcnow()


def webhook_base_url() -> str:
    base = (os.getenv("ASSINATURA_WEBHOOK_BASE_URL") or os.getenv("APP_URL")
            or "https://www.romatecavalieimob.com.br")
    return base.rstrip("/")


def _sig_dict(s: SignatarioEnvio) -> dict:
    return {"nome": s.nome, "email": s.email, "whatsapp": s.whatsapp, "cpf_cnpj": s.cpf_cnpj,
            "papel": s.papel, "autenticacao": list(s.autenticacao or []), "ordem": s.ordem,
            "status": "pendente", "assinado_em": None}


def _slim(doc: dict) -> dict:
    """Nunca expõe o webhook_secret nas respostas de API."""
    if not doc:
        return doc
    return {k: v for k, v in doc.items() if k != "webhook_secret"}


# ── Envio ─────────────────────────────────────────────────────────────────────
async def criar_envio(db, user_id, provider, origem_tipo, origem_id, pdf_bytes, nome,
                      signatarios, opcoes: OpcoesEnvio):
    prov = await factory.get_provider(db, user_id, provider)   # CredencialNaoConfigurada
    envio_id = str(uuid.uuid4())
    webhook_secret = secrets.token_urlsafe(32)
    opc = opcoes or OpcoesEnvio()
    opc.webhook_url = f"{webhook_base_url()}/api/assinatura-externa/webhook/{provider}/{envio_id}"
    res = await prov.enviar_documento(pdf_bytes, nome, signatarios, opc)
    doc = {
        "id": envio_id, "user_id": user_id, "provider": provider, "ambiente": prov.ambiente,
        "origem_tipo": origem_tipo, "origem_id": origem_id,
        "provider_doc_id": res.provider_doc_id, "nome_documento": nome, "status": "enviado",
        "signatarios": [_sig_dict(s) for s in signatarios],
        "url_assinatura_embed": res.url_assinatura_embed, "arquivo_assinado_url": None,
        "hash_arquivo_original": hashlib.sha256(pdf_bytes).hexdigest(),
        "webhook_secret": webhook_secret,
        "eventos": [{"tipo": "enviado", "em": _now().isoformat()}],
        "erro_msg": None, "created_at": _now(), "updated_at": _now(),
    }
    await db[COLL].insert_one(doc)
    return _slim(doc)


async def listar_envios(db, user_id, status=None, provider=None, origem_tipo=None):
    flt = {"user_id": user_id}
    if status:
        flt["status"] = status
    if provider:
        flt["provider"] = provider
    if origem_tipo:
        flt["origem_tipo"] = origem_tipo
    docs = await db[COLL].find(flt).sort("created_at", -1).to_list(length=200)
    return [_slim(d) for d in docs]


async def obter_raw(db, user_id, envio_id):
    """Doc completo (com webhook_secret) p/ operações internas; filtra por user_id."""
    return await db[COLL].find_one({"id": envio_id, "user_id": user_id})


async def _aplicar_status(db, envio, novo_status, signatarios_status=None, evento=None):
    upd = {"status": novo_status, "updated_at": _now()}
    if signatarios_status:
        by_key = {(s.get("signatario") or "").lower(): s.get("status") for s in signatarios_status}
        sig = envio.get("signatarios") or []
        for s in sig:
            k = (s.get("email") or s.get("whatsapp") or "").lower()
            if by_key.get(k):
                s["status"] = by_key[k]
                if by_key[k] == "assinado" and not s.get("assinado_em"):
                    s["assinado_em"] = _now().isoformat()
        upd["signatarios"] = sig
    q = {"$set": upd}
    if evento:
        q["$push"] = {"eventos": evento}
    await db[COLL].update_one({"id": envio["id"], "user_id": envio["user_id"]}, q)


async def sincronizar(db, user_id, envio):
    prov = await factory.get_provider(db, user_id, envio["provider"])
    st = await prov.consultar_status(envio["provider_doc_id"])
    await _aplicar_status(db, envio, st.status, st.signatarios,
                          evento={"tipo": "sincronizado", "status": st.status, "em": _now().isoformat()})
    return st.status


async def cancelar(db, user_id, envio, motivo=""):
    prov = await factory.get_provider(db, user_id, envio["provider"])
    await prov.cancelar(envio["provider_doc_id"], motivo)
    await _aplicar_status(db, envio, "cancelado",
                          evento={"tipo": "cancelado", "motivo": motivo, "em": _now().isoformat()})
    return True


async def baixar_assinado(db, user_id, envio) -> bytes:
    prov = await factory.get_provider(db, user_id, envio["provider"])
    return await prov.baixar_assinado(envio["provider_doc_id"])


# ── Webhook ───────────────────────────────────────────────────────────────────
def hmac_valido(raw_body: bytes, secret: str, headers: dict) -> bool:
    """HMAC-SHA256 do corpo bruto, comparado em tempo constante contra os headers candidatos."""
    if not secret:
        return False
    esperado = hmac.new(secret.encode(), raw_body or b"", hashlib.sha256).hexdigest()
    hl = {str(k).lower(): v for k, v in (headers or {}).items()}
    for h in ("x-hub-signature-256", "content-hmac", "x-signature", "signature", "x-clicksign-signature"):
        v = hl.get(h)
        if not v:
            continue
        v = v.split("=", 1)[1] if "=" in v else v
        if hmac.compare_digest(v.strip().lower(), esperado):
            return True
    return False


class WebhookInvalido(Exception):
    """Assinatura HMAC inválida (HTTP 401)."""


async def processar_webhook(db, provider, envio_id, headers, raw_body: bytes, body: dict):
    envio = await db[COLL].find_one({"id": envio_id, "provider": provider})
    if not envio:
        return {"ok": True, "ignorado": "envio inexistente"}   # não vaza existência

    # Validação: Clicksign/Autentique assinam (HMAC); D4Sign não → confirma via API.
    if provider in ("clicksign", "autentique"):
        if not hmac_valido(raw_body, envio.get("webhook_secret", ""), headers):
            raise WebhookInvalido("HMAC inválido")

    prov = await factory.get_provider(db, envio["user_id"], provider)
    ev = prov.parse_webhook(headers, body or {})

    # Idempotência: (provider_doc_id, tipo, signatário) com TTL 30 dias.
    chave = f"{envio.get('provider_doc_id')}:{ev.tipo}:{ev.signatario or ''}"
    if await db[COLL_EVT].find_one({"chave": chave}):
        return {"ok": True, "idempotente": True}
    await db[COLL_EVT].insert_one({"chave": chave, "envio_id": envio_id, "em": _now(),
                                   "expira_em": _now() + timedelta(days=30)})

    ref = {"id": envio_id, "user_id": envio["user_id"], "signatarios": envio.get("signatarios")}
    if provider == "d4sign":
        st = await prov.consultar_status(envio["provider_doc_id"])   # confirma antes de aplicar
        await _aplicar_status(db, ref, st.status, st.signatarios,
                              evento={"tipo": ev.tipo, "confirmado": True, "em": _now().isoformat()})
    else:
        await _aplicar_status(db, ref, ev.novo_status or "parcialmente_assinado", None,
                              evento={"tipo": ev.tipo, "em": _now().isoformat()})
    return {"ok": True}


# ── Polling (garantia; webhook é otimização) ──────────────────────────────────
async def rodar_polling(db, limite=20) -> int:
    corte = _now() - timedelta(hours=1)
    docs = await db[COLL].find(
        {"status": {"$in": ["enviado", "parcialmente_assinado"]}, "updated_at": {"$lt": corte}}
    ).sort("updated_at", 1).to_list(length=limite)
    n = 0
    for envio in docs:
        try:
            await sincronizar(db, envio["user_id"], envio)
            n += 1
        except Exception as e:  # noqa: BLE001 — best-effort; um envio ruim não trava o ciclo
            logger.warning("polling assinatura: falha no envio %s: %s", envio.get("id"), e)
    return n


def start_polling(db) -> None:
    """Task de startup: roda rodar_polling em intervalo, com lease em Mongo (1 worker só)."""
    if str(os.getenv("ASSINATURA_POLLING_ENABLED", "true")).lower() in ("0", "false", "no"):
        logger.info("Polling de assinatura desabilitado (ASSINATURA_POLLING_ENABLED=false)")
        return
    intervalo = max(5, int(os.getenv("ASSINATURA_POLLING_INTERVAL_MIN", "30"))) * 60

    async def _loop():
        while True:
            await asyncio.sleep(intervalo)
            try:
                # lease: só 1 worker processa por ciclo
                from pymongo import ReturnDocument
                agora = _now()
                lease = await db.sys_leases.find_one_and_update(
                    {"_id": "assinatura_polling", "$or": [
                        {"expira_em": {"$lt": agora}}, {"expira_em": None}]},
                    {"$set": {"expira_em": agora + timedelta(minutes=5)}},
                    upsert=True, return_document=ReturnDocument.AFTER)
                if lease:
                    await rodar_polling(db)
            except Exception as e:  # noqa: BLE001
                logger.warning("Ciclo de polling de assinatura falhou: %s", e)

    try:
        asyncio.get_event_loop().create_task(_loop())
        logger.info("Polling de assinatura agendado a cada %d min", intervalo // 60)
    except Exception as e:  # noqa: BLE001
        logger.error("Falha ao agendar polling de assinatura: %s", e)
