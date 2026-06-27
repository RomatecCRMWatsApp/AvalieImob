# @module services.documento_externo_service — orquestração do módulo Documentos Externos.
# Reusa o motor existente: carimbo (carimbar_multi), preview, Z-API, R2. NÃO toca contratos.
import asyncio
import base64
import logging
from datetime import datetime

from pymongo import ReturnDocument

from models.documento_externo import recalcular_status

logger = logging.getLogger("romatec")

COL = "documentos_externos"


def formatar_codigo(ano: int, seq: int) -> str:
    return f"DOCEXT-{ano}-{seq:04d}"


async def proximo_codigo(db) -> str:
    ano = datetime.utcnow().year
    res = await db.counters.find_one_and_update(
        {"_id": f"docext_{ano}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=ReturnDocument.AFTER)
    return formatar_codigo(ano, res["seq"])


# ── Z-API (reusa a config do owner via assinatura_cliente helpers) ───────────────
async def zapi_cfg(db, uid: str) -> dict:
    from services.integracoes_util import carregar_integracoes
    cfg = await carregar_integracoes(db, uid)
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Z-API não configurada em Integrações.")
    return cfg


async def enviar_texto(cfg: dict, phone: str, message: str):
    from services import zapi_service
    return await zapi_service.send_text(
        instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
        security_token=cfg.get("zapi_security_token"), phone=phone, message=message)


async def enviar_pdf(cfg: dict, phone: str, pdf_bytes: bytes, filename: str, caption: str = ""):
    from services import zapi_service
    return await zapi_service.send_document_pdf(
        instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
        security_token=cfg.get("zapi_security_token"), phone=phone,
        pdf_bytes=pdf_bytes, filename=filename, caption=caption)


async def atualizar_status(db, doc_id: str):
    doc = await db[COL].find_one({"id": doc_id})
    if not doc:
        return None
    novo = recalcular_status(doc)
    await db[COL].update_one({"id": doc_id},
                             {"$set": {"status": novo, "updated_at": datetime.utcnow()}})
    return novo


async def processar_carimbo(db, doc: dict):
    """Quando TODOS os signatários assinaram: baixa o PDF-base do R2, carimba os traços +
    folha de autoria via carimbar_multi, sobe o intermediário, e distribui se NÃO exigir ICP."""
    from services import r2_storage
    from services.assinatura_cliente_carimbo import carimbar_multi
    base = await asyncio.to_thread(r2_storage.download_bytes, doc["pdf_key"])
    sigs = []
    for s in doc.get("signatarios", []):
        if not s.get("traco_b64"):
            continue
        try:
            png = base64.b64decode(s["traco_b64"])
        except Exception:
            continue
        sigs.append({
            "nome": s.get("nome"), "cpf": s.get("cpf_cnpj"), "role": s.get("papel"),
            "traco_png": png, "ip": s.get("ip"), "geo_lat": s.get("geo_lat"),
            "geo_lng": s.get("geo_lng"), "user_agent": s.get("user_agent"),
            "assinado_em": s.get("assinado_em"), "posicoes": s.get("posicoes") or [],
        })
    final, _h = await asyncio.to_thread(carimbar_multi, base, sigs)
    key_inter = f"documentos-externos/{doc['user_id']}/{doc['id']}_intermediario.pdf"
    await asyncio.to_thread(r2_storage.upload_bytes, final, key_inter, "application/pdf")
    await db[COL].update_one({"id": doc["id"]}, {"$set": {"pdf_key_intermediario": key_inter}})
    doc["pdf_key_intermediario"] = key_inter
    await atualizar_status(db, doc["id"])
    if not doc.get("requer_icp_rt"):
        await distribuir(db, doc, final, "clientes")
    return key_inter


async def distribuir(db, doc: dict, pdf_bytes: bytes, etapa: str):
    """Envia o PDF (intermediário ou final) a todos os signatários por WhatsApp."""
    try:
        cfg = await zapi_cfg(db, doc["user_id"])
    except Exception:
        logger.warning("Z-API indisponível p/ distribuir doc-ext %s", doc.get("id"))
        return
    rotulo = "documento FINAL assinado (todas as assinaturas + ICP)" if etapa == "final" \
        else "documento assinado por todas as partes"
    for s in doc.get("signatarios", []):
        fone = "".join(filter(str.isdigit, str(s.get("whatsapp") or "")))
        if not fone:
            continue
        try:
            await enviar_pdf(cfg, fone, pdf_bytes, f"{doc.get('codigo', 'documento')}_assinado",
                             f"Segue o {rotulo}. Obrigado! — Romatec Consultoria Total")
        except Exception:
            logger.warning("Falha ao distribuir doc-ext p/ %s", fone, exc_info=True)
