# @module routes.galeria — Galeria de fotos própria do AvalieImob (com overlay GPS/UTM).
"""
Galeria de fotos do AvalieImob (clone do padrão ZAYRA): a foto já vem com o
overlay técnico (GPS/UTM/endereço/data/logo) renderizado no canvas do frontend.
Aqui só persistimos a imagem final + metadados, listamos e removemos.

Storage: db.images com flag galeria=True (mesma collection das fotos do laudo,
servidas por /api/upload/image/{id}). Numeração sequencial por usuário.
"""
import base64
import logging
import uuid as _uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber
from services import image_store
from services.upload_security import detect_content_type

router = APIRouter(prefix="/galeria", tags=["galeria"])
logger = logging.getLogger("romatec")

_MAX_BYTES = 12 * 1024 * 1024  # 12 MB (foto com overlay)


async def _next_numero(db, uid: str) -> int:
    res = await db.counters.find_one_and_update(
        {"_id": f"galeria_{uid}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(res["seq"])


@router.get("")
async def listar_galeria(
    limit: int = 200,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lista as fotos da galeria do usuário (mais recentes primeiro)."""
    cur = db.images.find(
        {"user_id": uid, "galeria": True},
        {"data_b64": 0},  # não trafega o base64 na listagem
    ).sort("created_at", -1).limit(min(int(limit or 200), 500))
    fotos = []
    async for d in cur:
        fotos.append({
            "id": d.get("id"),
            "numero": d.get("numero"),
            "url": f"/api/upload/image/{d.get('id')}",
            "latitude": d.get("latitude"),
            "longitude": d.get("longitude"),
            "altitude": d.get("altitude"),
            "utm": d.get("utm"),
            "endereco": d.get("endereco"),
            "data_hora": d.get("meta_data_hora") or (d.get("created_at").isoformat() if d.get("created_at") else None),
            "legenda": d.get("legenda") or "",
        })
    return {"fotos": fotos, "total": len(fotos)}


@router.post("/foto")
async def salvar_foto(
    file: UploadFile = File(...),
    latitude: str = Form(""),
    longitude: str = Form(""),
    altitude: str = Form(""),
    utm: str = Form(""),
    endereco: str = Form(""),
    legenda: str = Form(""),
    data_hora: str = Form(""),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Salva uma foto da galeria (já com overlay aplicado no frontend)."""
    raw = await file.read()
    if not raw:
        raise HTTPException(422, "Arquivo vazio.")
    if len(raw) > _MAX_BYTES:
        raise HTTPException(422, f"Foto excede {_MAX_BYTES // (1024*1024)} MB.")

    ctype = detect_content_type(raw)
    if ctype not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(422, f"Tipo inválido ({ctype}). Envie JPG/PNG/WebP.")

    def _f(v):
        try:
            return float(str(v).replace(",", ".")) if str(v).strip() != "" else None
        except ValueError:
            return None

    numero = await _next_numero(db, uid)
    image_id = str(_uuid.uuid4())
    gps_str = ""
    lat_f, lon_f = _f(latitude), _f(longitude)
    if lat_f is not None and lon_f is not None:
        gps_str = f"{lat_f:.6f}, {lon_f:.6f}"

    await image_store.salvar_imagem(
        db, uid, raw, ctype, f"galeria_{numero}.jpg", image_id=image_id,
        extra={
            "galeria": True,
            "numero": numero,
            "latitude": lat_f,
            "longitude": lon_f,
            "altitude": _f(altitude),
            "utm": utm.strip() or None,
            "endereco": endereco.strip() or None,
            "legenda": legenda.strip() or None,
            "meta_gps": gps_str,
            "meta_data_hora": data_hora.strip() or datetime.utcnow().isoformat(),
            "meta_ocr_done": True,
            "origem": "galeria_avalieimob",
        },
    )

    return {
        "id": image_id,
        "numero": numero,
        "url": f"/api/upload/image/{image_id}",
    }


@router.delete("/foto/{image_id}")
async def remover_foto(
    image_id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    res = await db.images.delete_one({"id": image_id, "user_id": uid, "galeria": True})
    if res.deleted_count == 0:
        raise HTTPException(404, "Foto não encontrada")
    return {"ok": True}


# ── Envio de foto da galeria via WhatsApp (Z-API) / Telegram ────────────────

class EnvioWppBody(BaseModel):
    phone: str


class EnvioTgBody(BaseModel):
    chat_id: str = ""


async def _carregar_foto(db, image_id: str, uid: str):
    doc = await image_store.find_one(db, {"id": image_id, "user_id": uid, "galeria": True})
    if not doc:
        raise HTTPException(404, "Foto não encontrada")
    return doc, base64.b64decode(doc["data_b64"])


@router.post("/foto/{image_id}/whatsapp")
async def enviar_foto_whatsapp(
    image_id: str, body: EnvioWppBody,
    uid: str = Depends(get_active_subscriber), db=Depends(get_db),
):
    from services.integracoes_util import carregar_integracoes
    from services import zapi_service
    cfg = await carregar_integracoes(db, uid)
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(400, "Z-API não configurada. Cadastre em Configurações → Integrações.")
    doc, raw = await _carregar_foto(db, image_id, uid)
    try:
        resp = await zapi_service.send_document(
            instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"), phone=body.phone,
            file_bytes=raw, filename=doc.get("filename") or f"foto_{doc.get('numero')}.jpg",
            content_type=doc.get("content_type", "image/jpeg"),
            caption=f"Foto #{doc.get('numero')} — Romatec/AvalieImob",
        )
        return {"ok": True, "provider": "zapi", "response": resp}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("Erro Z-API (galeria): %s", e)
        raise HTTPException(502, f"Erro Z-API: {e}")


@router.post("/foto/{image_id}/telegram")
async def enviar_foto_telegram(
    image_id: str, body: EnvioTgBody,
    uid: str = Depends(get_active_subscriber), db=Depends(get_db),
):
    import httpx
    from services.integracoes_util import carregar_integracoes
    cfg = await carregar_integracoes(db, uid)
    bot_token = (cfg or {}).get("telegram_bot_token")
    if not bot_token:
        raise HTTPException(400, "Telegram não configurado. Cadastre o bot_token em Configurações → Integrações.")
    chat_id = (body.chat_id or "").strip() or (cfg or {}).get("telegram_chat_id_default")
    if not chat_id:
        raise HTTPException(400, "Informe um chat_id ou configure um padrão.")
    doc, raw = await _carregar_foto(db, image_id, uid)
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            files = {"photo": (doc.get("filename") or "foto.jpg", raw, doc.get("content_type", "image/jpeg"))}
            data = {"chat_id": chat_id, "caption": f"Foto #{doc.get('numero')} — Romatec/AvalieImob"}
            r = await client.post(url, data=data, files=files)
            if r.status_code != 200:
                raise HTTPException(502, f"Telegram erro {r.status_code}: {r.text[:200]}")
            return {"ok": True, "telegram_response": r.json()}
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Erro de rede ao enviar Telegram: {e}")
