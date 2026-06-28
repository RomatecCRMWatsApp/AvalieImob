# @module routes.testemunha_assinatura — gestão + assinatura pública de TESTEMUNHAS.
# Camada aditiva, append-only (não reescreve o PDF — ver services.testemunha_signing).
# Distinto de routes.testemunhas (CRUD de testemunhas SALVAS p/ autofill nos contratos).
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from dependencies import get_active_subscriber
from services import testemunha_service as TS

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/testemunhas-assinatura", tags=["Testemunhas (assinatura)"])
router_publico = APIRouter(prefix="/publico/testemunha", tags=["Testemunhas Público"])


@router.post("/{modulo}/{doc_id}")
async def cadastrar(modulo: str, doc_id: str, payload: dict,
                    uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    lista = (payload or {}).get("testemunhas") or []
    if not lista:
        raise HTTPException(status_code=422, detail="Informe ao menos uma testemunha.")
    out = await TS.cadastrar(db, modulo, doc_id, uid, lista)
    return {"testemunhas": [{"id": t["id"], "nome": t["nome"], "vinculo": t.get("vinculo"),
                             "status": t["status"], "link": TS._link(t["token"])} for t in out]}


@router.get("/{modulo}/{doc_id}/preparar")
async def preparar(modulo: str, doc_id: str,
                   uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await TS.paginas_vigentes(db, modulo, doc_id, uid)


@router.post("/{modulo}/{doc_id}/posicionar")
async def posicionar(modulo: str, doc_id: str, payload: dict,
                     uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await TS.posicionar(db, modulo, doc_id, uid, (payload or {}).get("posicoes") or {})


@router.post("/{modulo}/{doc_id}/enviar")
async def enviar_todas(modulo: str, doc_id: str, payload: dict = None,
                       uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    teste = (payload or {}).get("telefone_teste")
    return await TS.enviar(db, modulo, doc_id, uid, None, telefone_teste=teste)


@router.post("/{modulo}/{doc_id}/{tid}/reenviar")
async def reenviar(modulo: str, doc_id: str, tid: str,
                   uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await TS.enviar(db, modulo, doc_id, uid, tid)


@router.put("/{modulo}/{doc_id}/{tid}")
async def editar(modulo: str, doc_id: str, tid: str, payload: dict,
                 uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await TS.editar_testemunha(db, modulo, doc_id, uid, tid, payload or {})


@router.post("/{modulo}/{doc_id}/{tid}/documento")
async def documento_operador(modulo: str, doc_id: str, tid: str, payload: dict,
                             uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await TS.salvar_documento_operador(db, modulo, doc_id, uid, tid,
                                              (payload or {}).get("frente_base64") or "",
                                              (payload or {}).get("verso_base64") or "",
                                              (payload or {}).get("tipo") or "CNH")


@router.delete("/{modulo}/{doc_id}/{tid}")
async def excluir(modulo: str, doc_id: str, tid: str,
                  uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await TS.excluir_testemunha(db, modulo, doc_id, uid, tid)


@router.get("/{modulo}/{doc_id}/status")
async def status(modulo: str, doc_id: str,
                 uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await TS.carregar_doc(db, modulo, doc_id, uid)
    return {"status_documento": doc.get("status"),
            "testemunhas_habilitadas": doc.get("testemunhas_habilitadas", False),
            "testemunhas": [{"id": t["id"], "nome": t["nome"], "cpf": t.get("cpf"),
                             "telefone": t.get("telefone"), "email": t.get("email"),
                             "vinculo": t.get("vinculo"), "parte_vinculada_id": t.get("parte_vinculada_id"),
                             "parte_vinculada_nome": t.get("parte_vinculada_nome"), "status": t["status"],
                             "documento_enviado": bool((t.get("documento") or {}).get("frente_key")),
                             "enviado_em": t.get("enviado_em"), "visualizado_em": t.get("visualizado_em"),
                             "assinado_em": t.get("assinado_em"), "link": TS._link(t["token"])}
                            for t in (doc.get("testemunhas") or [])]}


# ── Público ──────────────────────────────────────────────────────────────────
@router_publico.get("/{token}")
@limiter.limit("40/minute")
async def obter(token: str, request: Request, db=Depends(get_db)):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "") or "").split(",")[0].strip()
    ua = request.headers.get("user-agent") or ""
    modulo, doc, t = await TS.marcar_visualizado(db, token, ip, ua)
    if t.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Esta testemunha já assinou.")
    from services.pdf_preview import renderizar_paginas
    key = TS._pdf_key_vigente(doc)
    paginas = []
    if key:
        try:
            from services import r2_storage
            raw = await asyncio.to_thread(r2_storage.download_bytes, key)
            paginas = await asyncio.to_thread(renderizar_paginas, raw)
        except Exception:  # noqa: BLE001
            paginas = []
    titulo = doc.get("titulo") or doc.get("numero_contrato") or "Documento"
    doc_id_face = (t.get("documento") or {})
    return {"ok": True, "documento": {"titulo": titulo, "modulo": modulo},
            "testemunha": {"nome": t.get("nome"), "vinculo": t.get("vinculo"),
                           "parte_vinculada_nome": t.get("parte_vinculada_nome")},
            "paginas": paginas, "posicoes": t.get("posicoes") or [],
            "documento_enviado": bool(doc_id_face.get("frente_key")),
            "ja_assinado": t.get("status") == "assinado"}


@router_publico.post("/{token}/documento")
@limiter.limit("10/minute")
async def enviar_documento(token: str, payload: dict, request: Request, db=Depends(get_db)):
    return await TS.salvar_documento(db, token,
                                     (payload or {}).get("frente_base64") or "",
                                     (payload or {}).get("verso_base64") or "",
                                     (payload or {}).get("tipo") or "CNH")


@router_publico.get("/{token}/pdf")
@limiter.limit("40/minute")
async def pdf(token: str, request: Request, db=Depends(get_db)):
    _modulo, doc, _t = await TS.localizar_por_token(db, token)
    key = TS._pdf_key_vigente(doc)
    if not key:
        raise HTTPException(status_code=404, detail="PDF não disponível.")
    from services import r2_storage
    raw = await asyncio.to_thread(r2_storage.download_bytes, key)
    return Response(content=raw, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="documento.pdf"'})


@router_publico.post("/{token}/assinar")
@limiter.limit("10/minute")
async def assinar(token: str, payload: dict, request: Request, db=Depends(get_db)):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "") or "").split(",")[0].strip()
    ua = request.headers.get("user-agent") or ""
    if not (payload or {}).get("concordo"):
        raise HTTPException(status_code=422, detail="É necessário concordar para assinar.")
    traco = (payload or {}).get("assinatura_base64") or (payload or {}).get("traco_base64") or ""
    return await TS.assinar(db, token, traco, ip, ua)
