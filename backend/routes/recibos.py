# @module routes.recibos — CRUD de Recibos + PDF + envio WhatsApp/Telegram
"""
Rotas:
  GET    /api/recibos                         lista do usuário
  GET    /api/recibos/{id}                    detalhe
  POST   /api/recibos                         cria (numera ao emitir)
  PUT    /api/recibos/{id}                    atualiza
  DELETE /api/recibos/{id}                    remove
  POST   /api/recibos/{id}/emitir             gera número e marca status=emitido
  GET    /api/recibos/{id}/pdf                baixa PDF (gera on-demand)
  POST   /api/recibos/preview                 preview de PDF sem salvar (live)
  POST   /api/recibos/{id}/enviar-whatsapp    envia via Z-API/Meta
  GET    /api/recibos/tipos                   lista os tipos disponíveis
"""
import io
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models import (
    Recibo, ReciboCreate, ReciboUpdate, TIPOS_RECIBO, FORMAS_PAGAMENTO,
)

logger = logging.getLogger("romatec")
router = APIRouter(tags=["recibos"], prefix="/recibos")


async def _next_recibo_numero(db, tipo: str) -> tuple[str, int]:
    """Gera número sequencial REC-{ABREV}-{ANO}-{SEQ:04d} por tipo+ano."""
    abrev = TIPOS_RECIBO.get(tipo, {}).get("abrev", "GEN")
    ano = datetime.utcnow().year
    counter_id = f"recibo_{tipo}_{ano}"
    result = await db.counters.find_one_and_update(
        {"_id": counter_id},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = result["seq"]
    return f"REC-{abrev}-{ano}-{seq:04d}", seq


# Caminho do logo padrão do AvalieImob (servido junto com o backend)
import os as _os
_DEFAULT_LOGO_PATH = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
    "assets", "avalieimob_logo.png"
)
_DEFAULT_LOGO_BYTES_CACHE = None


def _get_default_logo_bytes() -> Optional[bytes]:
    """Carrega o logo padrão Romatec AvalieImob (cacheado em memória)."""
    global _DEFAULT_LOGO_BYTES_CACHE
    if _DEFAULT_LOGO_BYTES_CACHE is not None:
        return _DEFAULT_LOGO_BYTES_CACHE
    try:
        with open(_DEFAULT_LOGO_PATH, "rb") as fh:
            _DEFAULT_LOGO_BYTES_CACHE = fh.read()
        return _DEFAULT_LOGO_BYTES_CACHE
    except Exception as e:
        logger.warning("Logo padrão não encontrado em %s: %s", _DEFAULT_LOGO_PATH, e)
        return None


async def _carregar_logo_bytes(db, image_id: Optional[str]) -> Optional[bytes]:
    """Hierarquia de logo:
       1. Logo customizado do usuário (uploads collection)
       2. Logo padrão Romatec AvalieImob (backend/assets/avalieimob_logo.png)
    """
    if image_id:
        try:
            doc = await db.uploads.find_one({"id": image_id})
            if doc and doc.get("content"):
                return doc["content"]
        except Exception as e:
            logger.debug("Erro ao buscar logo %s: %s", image_id, e)
    # Fallback — logo padrão AvalieImob
    return _get_default_logo_bytes()


async def _hidratar_emitente(recibo_dict: dict, user: dict, perfil: dict) -> dict:
    """Preenche campos do emitente a partir do user/perfil se não vieram no payload."""
    out = dict(recibo_dict)
    if not out.get("emitente_nome"):
        out["emitente_nome"] = (
            perfil.get("empresa_nome")
            or perfil.get("nome_completo")
            or user.get("name", "")
        )
    if not out.get("emitente_documento"):
        out["emitente_documento"] = (
            perfil.get("empresa_cnpj")
            or perfil.get("cpf")
            or ""
        )
    if not out.get("emitente_endereco"):
        out["emitente_endereco"] = perfil.get("endereco_escritorio", "")
    if not out.get("emitente_telefone"):
        out["emitente_telefone"] = perfil.get("telefone") or user.get("phone", "")
    if not out.get("emitente_email"):
        out["emitente_email"] = perfil.get("email_profissional") or user.get("email", "")
    if not out.get("emitente_logo_id"):
        out["emitente_logo_id"] = user.get("company_logo")
    return out


# ── GET /recibos/tipos ──────────────────────────────────────────────────────

@router.get("/tipos")
async def listar_tipos():
    """Tipos de recibo disponíveis e formas de pagamento (alimentação dos selects)."""
    return {
        "tipos": [
            {"value": k, "label": v["label"], "abrev": v["abrev"]}
            for k, v in TIPOS_RECIBO.items()
        ],
        "formas_pagamento": FORMAS_PAGAMENTO,
    }


# ── GET /recibos/catalogo ────────────────────────────────────────────────────

@router.get("/catalogo")
async def listar_catalogo():
    """Catálogo cascata Categoria → Serviço (com template de descrição e tipo sugerido)."""
    from services.recibo_catalogo import listar_catalogo as _listar
    return {"categorias": _listar()}


# ── GET /recibos ────────────────────────────────────────────────────────────

@router.get("")
async def listar_recibos(
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    query = {"user_id": uid}
    if status:
        query["status"] = status
    if tipo:
        query["tipo"] = tipo
    items = await db.recibos.find(query).sort("created_at", -1).to_list(500)
    return [serialize_doc(i) for i in items]


# ── GET /recibos/{id} ───────────────────────────────────────────────────────

@router.get("/{rid}")
async def buscar_recibo(
    rid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.recibos.find_one({"id": rid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")
    return serialize_doc(doc)


# ── POST /recibos ───────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def criar_recibo(
    body: ReciboCreate,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    user = await db.users.find_one({"id": uid}) or {}
    perfil = await db.perfis_avaliador.find_one({"user_id": uid}) or {}

    payload = body.model_dump()
    payload = await _hidratar_emitente(payload, user, perfil)

    recibo = Recibo(user_id=uid, **payload)
    # Se status já = emitido na criação, gera número
    if recibo.status == "emitido":
        numero, seq = await _next_recibo_numero(db, recibo.tipo)
        recibo.numero = numero
        recibo.sequencia = seq

    await db.recibos.insert_one(recibo.model_dump())
    return serialize_doc(recibo.model_dump())


# ── PUT /recibos/{id} ───────────────────────────────────────────────────────

@router.put("/{rid}")
async def atualizar_recibo(
    rid: str,
    body: ReciboUpdate,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.recibos.find_one({"id": rid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")

    update = body.model_dump(exclude_unset=True)
    # Se acabou de virar emitido e ainda não tem número, gera
    if update.get("status") == "emitido" and not doc.get("numero"):
        tipo = update.get("tipo") or doc.get("tipo", "personalizado")
        numero, seq = await _next_recibo_numero(db, tipo)
        update["numero"] = numero
        update["sequencia"] = seq

    update["updated_at"] = datetime.utcnow()
    await db.recibos.update_one({"id": rid}, {"$set": update})
    novo = await db.recibos.find_one({"id": rid})
    return serialize_doc(novo)


# ── DELETE /recibos/{id} ────────────────────────────────────────────────────

@router.delete("/{rid}")
async def deletar_recibo(
    rid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    res = await db.recibos.delete_one({"id": rid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")
    return {"ok": True}


# ── POST /recibos/{id}/emitir ───────────────────────────────────────────────

@router.post("/{rid}/emitir")
async def emitir_recibo(
    rid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera número e marca status=emitido (irreversível)."""
    doc = await db.recibos.find_one({"id": rid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")
    if doc.get("numero"):
        return {"ok": True, "numero": doc["numero"], "ja_emitido": True}
    tipo = doc.get("tipo", "personalizado")
    numero, seq = await _next_recibo_numero(db, tipo)
    _emit = datetime.utcnow()
    # Hash de validação (SHA-256, 16 hex) p/ a página pública /v/{hash}.
    import hashlib
    _base = f"{numero}|{doc.get('destinatario_cpf_cnpj') or ''}|{doc.get('valor') or 0}|{_emit.isoformat()}"
    _hash = hashlib.sha256(_base.encode("utf-8")).hexdigest()[:16]
    await db.recibos.update_one(
        {"id": rid},
        {"$set": {
            "numero": numero,
            "sequencia": seq,
            "status": "emitido",
            "hash_validacao": _hash,
            "updated_at": _emit,
        }},
    )
    return {"ok": True, "numero": numero, "hash_validacao": _hash}


# ── GET /recibos/{id}/pdf ───────────────────────────────────────────────────

@router.get("/{rid}/pdf")
async def baixar_pdf(
    rid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    from pdf.recibo_pdf import gerar_recibo_pdf

    doc = await db.recibos.find_one({"id": rid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")

    user = await db.users.find_one({"id": uid}) or {}
    perfil = await db.perfis_avaliador.find_one({"user_id": uid}) or {}
    logo_bytes = await _carregar_logo_bytes(db, doc.get("emitente_logo_id") or user.get("company_logo"))

    pdf_bytes = gerar_recibo_pdf(
        recibo=doc,
        user=user,
        perfil=perfil,
        logo_bytes=logo_bytes,
    )
    # Anexa os documentos do recibo (PDF/imagens) ao final do PDF baixado.
    from services.recibo_anexos import anexar_anexos_ao_pdf
    pdf_bytes = await anexar_anexos_ao_pdf(db, doc, pdf_bytes)
    filename = f"{doc.get('numero') or 'RECIBO_RASCUNHO'}.pdf".replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ── POST /recibos/preview ──────────────────────────────────────────────────

class PreviewRequest(ReciboCreate):
    """Mesmos campos do ReciboCreate, sem persistir."""
    pass


@router.post("/preview")
async def preview_pdf(
    body: PreviewRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera PDF preview (sem persistir) — usado no wizard pra atualização live."""
    from pdf.recibo_pdf import gerar_recibo_pdf

    user = await db.users.find_one({"id": uid}) or {}
    perfil = await db.perfis_avaliador.find_one({"user_id": uid}) or {}

    payload = body.model_dump()
    payload = await _hidratar_emitente(payload, user, perfil)
    payload["created_at"] = datetime.utcnow()
    # Numero placeholder pra mostrar formato
    abrev = TIPOS_RECIBO.get(payload.get("tipo", "personalizado"), {}).get("abrev", "GEN")
    payload["numero"] = f"REC-{abrev}-{datetime.utcnow().year}-####"

    logo_bytes = await _carregar_logo_bytes(db, payload.get("emitente_logo_id") or user.get("company_logo"))

    pdf_bytes = gerar_recibo_pdf(
        recibo=payload,
        user=user,
        perfil=perfil,
        logo_bytes=logo_bytes,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="recibo_preview.pdf"'},
    )


# ── POST /recibos/{id}/clonar ───────────────────────────────────────────────

@router.post("/{rid}/clonar", status_code=201)
async def clonar_recibo(
    rid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Cria uma cópia do recibo como novo rascunho (sem número/hash/envio)."""
    doc = await db.recibos.find_one({"id": rid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")

    base = ReciboBase(**{k: doc.get(k) for k in ReciboBase.model_fields if k in doc})
    novo = Recibo(user_id=uid, **base.model_dump())
    novo.status = "rascunho"
    novo.numero = None
    novo.sequencia = None
    novo.hash_validacao = None
    novo.enviado_em = None
    novo.enviado_via = None
    await db.recibos.insert_one(novo.model_dump())
    return serialize_doc(novo.model_dump())


# ── POST /recibos/{id}/anexos ───────────────────────────────────────────────

@router.post("/{rid}/anexos", status_code=201)
async def adicionar_anexo(
    rid: str,
    file: UploadFile = File(...),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Anexa um documento ao recibo (até 5; PDF/JPG/PNG/WebP, 10MB cada)."""
    from services.recibo_anexos import salvar_anexo, MAX_ANEXOS

    doc = await db.recibos.find_one({"id": rid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")

    anexos = doc.get("anexos") or []
    if len(anexos) >= MAX_ANEXOS:
        raise HTTPException(status_code=400, detail=f"Máximo de {MAX_ANEXOS} anexos por recibo")

    data = await file.read()
    try:
        meta = await salvar_anexo(
            db, uid=uid, filename=file.filename or "anexo",
            content_type=file.content_type or "", data=data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    anexos.append(meta)
    await db.recibos.update_one(
        {"id": rid}, {"$set": {"anexos": anexos, "updated_at": datetime.utcnow()}}
    )
    return {"ok": True, "anexo": meta, "total": len(anexos)}


# ── DELETE /recibos/{id}/anexos/{anexo_id} ──────────────────────────────────

@router.delete("/{rid}/anexos/{anexo_id}")
async def remover_anexo(
    rid: str,
    anexo_id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.recibos.find_one({"id": rid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")
    anexos = [a for a in (doc.get("anexos") or []) if a.get("id") != anexo_id]
    await db.recibos.update_one(
        {"id": rid}, {"$set": {"anexos": anexos, "updated_at": datetime.utcnow()}}
    )
    # Remove os bytes da coleção de imagens (best-effort)
    try:
        await db.images.delete_one({"id": anexo_id, "user_id": uid})
    except Exception:
        pass
    return {"ok": True, "total": len(anexos)}


# ── POST /recibos/{id}/enviar-whatsapp ──────────────────────────────────────

class EnviarWhatsAppRequest(BaseModel):
    phone: Optional[str] = None  # se vazio, usa destinatario_whatsapp
    legenda: Optional[str] = ""


@router.post("/{rid}/enviar-whatsapp")
async def enviar_whatsapp(
    rid: str,
    body: EnviarWhatsAppRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Envia o PDF do recibo via WhatsApp (Z-API ou Meta) do usuário."""
    from pdf.recibo_pdf import gerar_recibo_pdf
    from services import zapi_service
    from services import meta_whatsapp_service as meta
    from services.integracoes_util import carregar_integracoes

    doc = await db.recibos.find_one({"id": rid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")

    cfg = await carregar_integracoes(db, uid)
    if not cfg:
        raise HTTPException(
            status_code=400,
            detail="Nenhum provedor WhatsApp configurado em Configurações → Integrações.",
        )

    phone = (body.phone or doc.get("destinatario_whatsapp", "")).strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Informe o WhatsApp do destinatário")

    # Garante que tem número (emite se não tiver)
    if not doc.get("numero"):
        tipo = doc.get("tipo", "personalizado")
        numero, seq = await _next_recibo_numero(db, tipo)
        await db.recibos.update_one(
            {"id": rid},
            {"$set": {"numero": numero, "sequencia": seq, "status": "emitido"}},
        )
        doc["numero"] = numero

    user = await db.users.find_one({"id": uid}) or {}
    perfil = await db.perfis_avaliador.find_one({"user_id": uid}) or {}
    logo_bytes = await _carregar_logo_bytes(db, doc.get("emitente_logo_id") or user.get("company_logo"))

    pdf_bytes = gerar_recibo_pdf(recibo=doc, user=user, perfil=perfil, logo_bytes=logo_bytes)
    filename = f"{doc['numero']}.pdf".replace("/", "-")
    if body.legenda:
        legenda = body.legenda
    else:
        from services.recibo_whatsapp import legenda_recibo
        legenda = legenda_recibo(doc)

    provider = (cfg.get("whatsapp_provider") or "zapi").lower()
    try:
        if provider == "meta":
            if not cfg.get("meta_phone_number_id") or not cfg.get("meta_access_token"):
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada")
            resp = await meta.send_pdf(
                phone_number_id=cfg["meta_phone_number_id"],
                access_token=cfg["meta_access_token"],
                phone=phone, pdf_bytes=pdf_bytes, filename=filename, caption=legenda,
            )
        else:
            if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
                raise HTTPException(status_code=400, detail="Z-API não configurada")
            resp = await zapi_service.send_document_pdf(
                instance_id=cfg["zapi_instance_id"],
                token=cfg["zapi_token"],
                security_token=cfg.get("zapi_security_token"),
                phone=phone, pdf_bytes=pdf_bytes, filename=filename, caption=legenda,
            )

        # Envia os anexos logo após o recibo (best-effort; só via Z-API).
        anexos = doc.get("anexos") or []
        anexos_enviados = 0
        if anexos and provider != "meta" and cfg.get("zapi_instance_id"):
            from services.recibo_anexos import carregar_anexo_bytes
            for ax in anexos:
                carregado = await carregar_anexo_bytes(db, ax)
                if not carregado:
                    continue
                ax_bytes, ax_name, ax_ct = carregado
                try:
                    await zapi_service.send_document(
                        instance_id=cfg["zapi_instance_id"],
                        token=cfg["zapi_token"],
                        security_token=cfg.get("zapi_security_token"),
                        phone=phone, file_bytes=ax_bytes, filename=ax_name,
                        content_type=ax_ct, caption="",
                    )
                    anexos_enviados += 1
                except Exception as e:
                    logger.warning("Falha ao enviar anexo %s do recibo %s: %s", ax_name, rid, e)

        await db.recibos.update_one(
            {"id": rid},
            {"$set": {
                "status": "enviado",
                "enviado_em": datetime.utcnow(),
                "enviado_via": "whatsapp",
                "updated_at": datetime.utcnow(),
            }},
        )
        return {"ok": True, "provider": provider, "response": resp, "anexos_enviados": anexos_enviados}
    except HTTPException:
        raise
    except Exception as e:
        # str(e) pode vir vazio (ex.: timeout/conexão httpx) — loga tipo + traceback
        # e devolve um detalhe sempre informativo.
        msg = str(e).strip() or e.__class__.__name__
        logger.error("Erro ao enviar recibo WhatsApp: [%s] %r", e.__class__.__name__, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Erro ao enviar ({e.__class__.__name__}): {msg}")
