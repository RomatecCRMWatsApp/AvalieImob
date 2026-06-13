# @module routes.assinatura_cliente — Coleta de assinatura DESENHADA do cliente via WhatsApp.
"""
Fluxo (decisões fechadas com o usuário):
  1. Corretor gera o contrato (sem ICP) e POSICIONA 1 caixa por signatário no PDF
     renderizado (reusa pdf_preview + a mecânica do "Posicionar"). NÃO usa âncora fixa.
  2. Links pessoais são enviados por WhatsApp (Z-API) a cada cliente (Contratante + Cônjuge).
  3. Na página pública o cliente DESENHA a assinatura (canvas) → PNG.
  4. Quando todos assinam, o traço é carimbado nos rects (pypdf) + folha de autoria.
  5. O ICP do corretor é aplicado DEPOIS, pelo botão "Assinar" já existente (ordem correta
     p/ não invalidar o PAdES). A procuração é tratada à parte (fora deste v1).

Convenções: auth get_active_subscriber->uid; db Depends(get_db); Z-API via
services.zapi_service + carregar_integracoes; storage r2_storage; público SEM auth + rate-limit.
"""
import base64
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from dependencies import get_active_subscriber
from services.contrato_exclusividade_assinatura import gerar_token

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/assinatura-cliente", tags=["Assinatura Cliente"])
router_publico = APIRouter(prefix="/publico/assinatura-cliente", tags=["Assinatura Cliente Pública"])

APP_URL = os.environ.get("APP_PUBLIC_URL", "https://romatecavalieimob.com.br").rstrip("/")
EXPIRA_HORAS = int(os.environ.get("ASSINATURA_CLIENTE_EXPIRA_HORAS", "72"))
COL = "assinatura_cliente_sessoes"


# ───────────────────────── helpers ─────────────────────────

def _so_dig(v) -> str:
    return "".join(filter(str.isdigit, str(v or "")))


async def _zapi_cfg(db, uid: str) -> dict:
    from services.integracoes_util import carregar_integracoes
    cfg = await carregar_integracoes(db, uid)
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(status_code=400, detail="Z-API não configurada em Integrações.")
    return cfg


async def _enviar_texto(cfg: dict, phone: str, message: str):
    from services import zapi_service
    return await zapi_service.send_text(
        instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
        security_token=cfg.get("zapi_security_token"), phone=phone, message=message)


async def _enviar_pdf(cfg: dict, phone: str, pdf_bytes: bytes, filename: str, caption: str = ""):
    from services import zapi_service
    return await zapi_service.send_document_pdf(
        instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
        security_token=cfg.get("zapi_security_token"), phone=phone,
        pdf_bytes=pdf_bytes, filename=filename, caption=caption)


async def _carregar_contrato(db, cid: str, uid: str) -> dict:
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return doc


async def _gerar_contrato_pdf(db, doc: dict, uid: str) -> bytes:
    """Gera o PDF do contrato (template Prime, SEM ICP) reusando o dispatcher existente."""
    from routes.assinatura import _gerar_pdf
    perfil = await db.perfil_avaliador.find_one({"user_id": uid})
    return await _gerar_pdf("contrato", doc, db=db, perfil=perfil)


def _signatarios_sugeridos(doc: dict) -> list:
    """Contratante (1º vendedor) + Cônjuge anuente (se casado), com telefone se houver."""
    vend = (doc.get("vendedores") or [])
    out = []
    if vend:
        v = vend[0] if isinstance(vend[0], dict) else {}
        out.append({"role": "contratante", "nome": v.get("nome") or "Contratante",
                    "cpf": v.get("cpf") or "", "telefone": _so_dig(v.get("telefone") or v.get("whatsapp") or "")})
        conj = (v.get("conjuge_nome") or (v.get("conjuge") or {}).get("nome") or "").strip()
        if conj:
            out.append({"role": "conjuge_anuente", "nome": conj,
                        "cpf": v.get("conjuge_cpf") or "",
                        "telefone": _so_dig(v.get("conjuge_telefone") or v.get("conjuge_whatsapp") or "")})
    return out


# ───────────────────────── rotas autenticadas ─────────────────────────

@router.post("/contratos/{cid}/preparar")
async def preparar(cid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Gera o PDF (sem ICP) e renderiza as páginas para o corretor POSICIONAR as caixas."""
    doc = await _carregar_contrato(db, cid, uid)
    pdf_bytes = await _gerar_contrato_pdf(db, doc, uid)
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=500, detail="Falha ao gerar o PDF do contrato")
    from services.pdf_preview import renderizar_paginas
    paginas = renderizar_paginas(pdf_bytes)
    return {"ok": True, "paginas": paginas, "signatarios": _signatarios_sugeridos(doc)}


@router.post("/contratos/{cid}/posicionar")
async def posicionar(cid: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Cria a sessão: salva âncoras (1 por role), gera tokens, sobe o PDF-base no R2
    e dispara os links por WhatsApp. payload: {ancoras:[{role,pagina,x_pt,y_pt,larg_pt,alt_pt}],
    signatarios:[{role,nome,cpf,telefone}]}."""
    from services import r2_storage
    doc = await _carregar_contrato(db, cid, uid)
    ancoras = payload.get("ancoras") or []
    signatarios_in = payload.get("signatarios") or _signatarios_sugeridos(doc)
    if not ancoras:
        raise HTTPException(status_code=422, detail="Posicione ao menos uma caixa de assinatura.")
    faltam = [s for s in signatarios_in if not _so_dig(s.get("telefone"))]
    if faltam:
        raise HTTPException(status_code=422,
                            detail=f"Informe o WhatsApp de: {', '.join(s.get('nome', '?') for s in faltam)}")
    # WhatsApp distinto entre signatários
    fones = [_so_dig(s.get("telefone")) for s in signatarios_in]
    if len(set(fones)) != len(fones):
        raise HTTPException(status_code=422, detail="Cada signatário precisa de um WhatsApp distinto.")

    pdf_bytes = await _gerar_contrato_pdf(db, doc, uid)
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=500, detail="Falha ao gerar o PDF do contrato")

    sessao_id = gerar_token()[:24]
    pdf_key = f"assinatura-cliente/{sessao_id}/contrato_base.pdf"
    try:
        r2_storage.upload_bytes(pdf_bytes, pdf_key, "application/pdf")
    except Exception as e:  # noqa: BLE001
        logger.error("Falha ao subir PDF-base no R2: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Falha ao armazenar o documento")

    expira = datetime.utcnow() + timedelta(hours=EXPIRA_HORAS)
    signatarios = []
    for s in signatarios_in:
        signatarios.append({
            "role": s.get("role"), "nome": s.get("nome"), "cpf": s.get("cpf") or "",
            "telefone": _so_dig(s.get("telefone")), "token": gerar_token(),
            "status": "pendente", "assinado_em": None, "ip": None,
            "geo_lat": None, "geo_lng": None, "user_agent": None, "traco_b64": None,
        })
    sessao = {
        "id": sessao_id, "user_id": uid, "contrato_id": cid, "status": "pendente",
        "expira_em": expira, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
        "documentos": [{"tipo": "contrato", "pdf_key_base": pdf_key,
                        "ancoras": ancoras, "pdf_key_final": None}],
        "signatarios": signatarios,
    }
    await db[COL].insert_one(sessao)

    cfg = await _zapi_cfg(db, uid)
    links = []
    for s in signatarios:
        url = f"{APP_URL}/assinar-cliente/{s['token']}"
        primeiro = str(s["nome"]).split(" ")[0]
        msg = (f"Olá, {primeiro}! A *Romatec Consultoria Total* enviou um documento para sua "
               f"assinatura eletrônica.\n\nAssine com segurança neste link:\n{url}\n\n"
               f"O link é pessoal e tem validade limitada (Lei 14.063/2020).")
        try:
            await _enviar_texto(cfg, s["telefone"], msg)
            await db[COL].update_one({"id": sessao_id, "signatarios.token": s["token"]},
                                     {"$set": {"signatarios.$.status": "enviado"}})
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao enviar WhatsApp p/ %s: %s", s["telefone"], e)
        links.append({"role": s["role"], "nome": s["nome"], "url": url})
    return {"ok": True, "sessao_id": sessao_id, "links": links}


# ───────────────────────── rotas públicas ─────────────────────────

@router_publico.get("/{token}")
@limiter.limit("30/minute")
async def obter_por_token(token: str, request: Request, db=Depends(get_db)):
    sessao = await db[COL].find_one({"signatarios.token": token})
    if not sessao:
        raise HTTPException(status_code=404, detail="Link inválido")
    if sessao.get("expira_em") and sessao["expira_em"] < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Link expirado")
    sig = next((s for s in sessao["signatarios"] if s.get("token") == token), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Link inválido")
    return {"ok": True, "nome": sig.get("nome"), "role": sig.get("role"),
            "ja_assinado": sig.get("status") == "assinado"}


@router_publico.post("/{token}")
@limiter.limit("10/minute")
async def assinar(token: str, payload: dict, request: Request, db=Depends(get_db)):
    sessao = await db[COL].find_one({"signatarios.token": token})
    if not sessao:
        raise HTTPException(status_code=404, detail="Link inválido")
    if sessao.get("expira_em") and sessao["expira_em"] < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Link expirado")
    sig = next((s for s in sessao["signatarios"] if s.get("token") == token), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Link inválido")
    if sig.get("status") == "assinado":
        return {"ok": True, "ja_assinado": True}
    traco = payload.get("traco_base64") or ""
    if not traco.startswith("data:image/png;base64,"):
        raise HTTPException(status_code=400, detail="Assinatura (traço) inválida")
    if not payload.get("concordo"):
        raise HTTPException(status_code=400, detail="É necessário concordar para assinar")

    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "0.0.0.0")
    ua = (request.headers.get("user-agent") or "")[:255]
    await db[COL].update_one(
        {"id": sessao["id"], "signatarios.token": token},
        {"$set": {
            "signatarios.$.status": "assinado",
            "signatarios.$.assinado_em": datetime.utcnow(),
            "signatarios.$.ip": ip, "signatarios.$.user_agent": ua,
            "signatarios.$.geo_lat": payload.get("geo_lat"),
            "signatarios.$.geo_lng": payload.get("geo_lng"),
            "signatarios.$.traco_b64": traco.split(",", 1)[1],
            "updated_at": datetime.utcnow(),
        }})
    sessao = await db[COL].find_one({"id": sessao["id"]})
    todos = all(s.get("status") == "assinado" for s in sessao["signatarios"])
    await db[COL].update_one({"id": sessao["id"]},
                             {"$set": {"status": "concluida" if todos else "parcial"}})
    if todos:
        try:
            await _processar_carimbo(db, sessao)
        except Exception as e:  # noqa: BLE001
            logger.error("Falha ao carimbar sessão %s: %s", sessao["id"], e, exc_info=True)
    return {"ok": True, "concluida": todos}


async def _processar_carimbo(db, sessao: dict):
    """Carimba os traços nos rects, anexa folha de autoria, sobe o final no R2 e envia
    por WhatsApp. O ICP do corretor é aplicado DEPOIS, pelo fluxo existente."""
    from services import r2_storage
    from services.assinatura_cliente_carimbo import carimbar_documento

    assinaturas = []
    for s in sessao["signatarios"]:
        if not s.get("traco_b64"):
            continue
        try:
            png = base64.b64decode(s["traco_b64"])
        except Exception:
            continue
        assinaturas.append({
            "role": s.get("role"), "nome": s.get("nome"), "cpf": s.get("cpf"),
            "traco_png": png, "ip": s.get("ip"), "geo_lat": s.get("geo_lat"),
            "geo_lng": s.get("geo_lng"), "user_agent": s.get("user_agent"),
            "assinado_em": s.get("assinado_em"),
        })
    cfg = None
    try:
        cfg = await _zapi_cfg(db, sessao["user_id"])
    except Exception:
        cfg = None
    for d in sessao.get("documentos", []):
        try:
            base_bytes = r2_storage.download_bytes(d["pdf_key_base"])
        except Exception as e:  # noqa: BLE001
            logger.error("Falha ao baixar PDF-base: %s", e)
            continue
        final, _h = carimbar_documento(base_bytes, d.get("ancoras") or [], assinaturas)
        key_final = d["pdf_key_base"].replace("contrato_base.pdf", "contrato_clientes.pdf")
        url = r2_storage.upload_bytes(final, key_final, "application/pdf")
        await db[COL].update_one(
            {"id": sessao["id"], "documentos.pdf_key_base": d["pdf_key_base"]},
            {"$set": {"documentos.$.pdf_key_final": key_final}})
        # marca no contrato p/ o card mostrar (sem mexer no fluxo ICP)
        await db.contratos.update_one(
            {"id": sessao["contrato_id"]},
            {"$set": {"assinatura_cliente_pdf_url": url,
                      "assinatura_cliente_em": datetime.utcnow()}})
        if cfg:
            for s in sessao["signatarios"]:
                try:
                    await _enviar_pdf(cfg, s["telefone"], final, "contrato_assinado.pdf",
                                      "Documento assinado por todas as partes. Obrigado!")
                except Exception as e:  # noqa: BLE001
                    logger.warning("Falha ao reenviar PDF final p/ %s: %s", s.get("telefone"), e)
