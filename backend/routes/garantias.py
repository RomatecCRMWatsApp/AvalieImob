# @module routes.garantias — Avaliação de Garantias (NBR 14.653 · Res. CMN 4.676/2018)
# CRUD + TODAS as ações do card do PTAM: visualizar/baixar PDF, DOCX, clonar, e-mail,
# WhatsApp (PDF e link), Telegram, link público com auditoria (views/envios/histórico)
# e recibo de honorários. A assinatura ICP-Brasil (assinar/posicionar/zerar/baixar
# assinado) usa o módulo genérico routes/assinatura com tipo="garantia".
import io
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models import GarantiaBase, Garantia
from services import garantia_assets, link_tracking
from services.integracoes_util import carregar_integracoes
from services.ratelimit import pub_limiter

logger = logging.getLogger("romatec")
router = APIRouter(tags=["garantias"])

COL = "garantias"
_PDF = "application/pdf"
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_BOTS = ("whatsapp", "facebookexternalhit", "telegrambot", "twitterbot", "slackbot",
         "linkedinbot", "discordbot", "googlebot", "bingbot")
# Campos que NÃO podem ir para o clone (estado de assinatura/link/recibo do original).
_NAO_CLONAR = (
    "_id", "id", "numero", "created_at", "updated_at",
    "icp_status", "icp_signed_at", "icp_hash", "icp_titular", "icp_cert_id", "icp_documento",
    "icp_emissor", "icp_layouts", "icp_pdf_url", "icp_verificacao_url", "pdf_assinatura_key",
    "d4sign_document_uuid", "d4sign_status", "d4sign_enviado_em", "d4sign_assinado_em",
    "d4sign_signatarios", "d4sign_pdf_assinado_url",
    "link_publico_token", "link_publico_ativo", "link_publico_criado_em", "link_gerado_em",
    "link_views", "link_views_first", "link_views_last", "link_sends", "link_last_sent",
    "link_last_canal", "link_last_destinatario",
    "honorarios", "recibo_emitido", "recibo_emitido_em", "recibo_id", "recibo_assinado",
    "recibo_assinado_em",
)


def _base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "https://www.romatecavalieimob.com.br").rstrip("/")


def _link_publico(token: str) -> str:
    return f"{_base_url()}/api/garantias/publico/{token}"


async def _get(db, gid: str, uid: str) -> dict:
    doc = await db.garantias.find_one({"id": gid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Avaliação de garantia não encontrada")
    return doc


async def _proximo_numero(db, uid: str) -> str:
    """GAR-AAAA-NNNN atômico via counters (count_documents duplicava após excluir/clonar)."""
    from pymongo import ReturnDocument
    year = datetime.utcnow().year
    key = f"garantia_{uid}_{year}"
    existentes = await db.garantias.count_documents({"user_id": uid, "numero": {"$regex": f"^GAR-{year}-"}})
    for _ in range(50):
        c = await db.counters.find_one_and_update(
            {"_id": key}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
        seq = int(c.get("seq") or 1)
        if seq <= existentes:
            await db.counters.update_one({"_id": key}, {"$max": {"seq": existentes}})
            continue
        numero = f"GAR-{year}-{str(seq).zfill(4)}"
        if not await db.garantias.find_one({"user_id": uid, "numero": numero}, {"_id": 1}):
            return numero
    return f"GAR-{year}-{uuid.uuid4().hex[:6].upper()}"


async def _gerar_pdf(db, doc: dict) -> bytes:
    import asyncio
    from pdf.garantia_pdf import generate_garantia_pdf
    await garantia_assets.preparar(db, doc)
    try:
        data = await asyncio.to_thread(generate_garantia_pdf, doc)
    except Exception as e:  # noqa: BLE001
        logger.exception("Erro ao gerar PDF da garantia %s", doc.get("id"))
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)[:200]}")
    if not data or data[:5] != b"%PDF-":
        raise HTTPException(status_code=500, detail="PDF gerado vazio ou corrompido")
    return data


async def _melhor_pdf(db, doc: dict) -> tuple[bytes, str]:
    """Versão ASSINADA (ICP) quando existir; senão o laudo atual."""
    if doc.get("icp_status") == "assinado":
        try:
            from routes.assinatura import _load_assinatura_bytes
            b, _a = await _load_assinatura_bytes(db, "garantia", doc["id"])
            if b and b[:5] == b"%PDF-":
                return b, garantia_assets.nome_arquivo(doc, "_ASSINADO_ICP")
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao carregar garantia assinada %s: %s", doc.get("id"), e)
    return await _gerar_pdf(db, doc), garantia_assets.nome_arquivo(doc)


def _resp(data: bytes, nome: str, media: str, inline: bool = False) -> Response:
    disp = "inline" if inline else "attachment"
    return Response(content=data, media_type=media, headers={
        "Content-Disposition": f'{disp}; filename="{nome}"',
        "Content-Length": str(len(data)), "Cache-Control": "no-store"})


# ════════════════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════════════════

@router.get("/garantias", response_model=List[Garantia])
async def list_garantias(tipo: Optional[str] = None, status: Optional[str] = None, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    q: dict = {"user_id": uid}
    if tipo:
        q["tipo_garantia"] = tipo
    if status:
        q["status"] = status
    items = await db.garantias.find(q).sort("updated_at", -1).to_list(1000)
    return [Garantia(**serialize_doc(i)) for i in items]


@router.get("/garantias/{gid}", response_model=Garantia)
async def get_garantia(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return Garantia(**serialize_doc(await _get(db, gid, uid)))


@router.post("/garantias", response_model=Garantia)
async def create_garantia(data: GarantiaBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    payload = data.model_dump()
    payload["numero"] = data.numero or await _proximo_numero(db, uid)
    g = Garantia(user_id=uid, **payload)
    await db.garantias.insert_one(g.model_dump())
    return g


@router.put("/garantias/{gid}", response_model=Garantia)
async def update_garantia(gid: str, data: GarantiaBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _get(db, gid, uid)
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    await db.garantias.update_one({"id": gid, "user_id": uid}, {"$set": updates})
    return Garantia(**serialize_doc(await db.garantias.find_one({"id": gid})))


@router.delete("/garantias/{gid}")
async def delete_garantia(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.garantias.delete_one({"id": gid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Avaliação de garantia não encontrada")
    return {"ok": True}


@router.post("/garantias/{gid}/clonar", response_model=Garantia)
async def clonar_garantia(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    src = await _get(db, gid, uid)
    novo = {k: v for k, v in src.items() if k not in _NAO_CLONAR}
    novo["status"] = "rascunho"
    novo["numero"] = await _proximo_numero(db, uid)
    novo["user_id"] = uid
    g = Garantia(**novo)
    await db.garantias.insert_one(g.model_dump())
    return g


# ════════════════════════════════════════════════════════════════════════════
# PDF / DOCX
# ════════════════════════════════════════════════════════════════════════════

@router.get("/garantias/{gid}/pdf")
async def baixar_pdf(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, gid, uid)
    data = await _gerar_pdf(db, doc)
    return _resp(data, garantia_assets.nome_arquivo(doc), _PDF)


@router.get("/garantias/{gid}/docx")
async def baixar_docx(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    import asyncio
    from docx_gen.garantia_docx import generate_garantia_docx
    doc = await _get(db, gid, uid)
    await garantia_assets.preparar(db, doc)
    try:
        data = await asyncio.to_thread(generate_garantia_docx, doc)
    except Exception as e:  # noqa: BLE001
        logger.exception("Erro ao gerar DOCX da garantia %s", gid)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar DOCX: {str(e)[:200]}")
    return _resp(data, garantia_assets.nome_arquivo(doc, ext="docx"), _DOCX)


# ════════════════════════════════════════════════════════════════════════════
# ENVIOS — e-mail, WhatsApp (PDF e link), Telegram
# ════════════════════════════════════════════════════════════════════════════

class EmailBody(BaseModel):
    destinatario: str
    nome_cliente: Optional[str] = ""
    mensagem_extra: Optional[str] = ""


class WhatsAppBody(BaseModel):
    phone: str
    legenda: Optional[str] = ""


class TelegramBody(BaseModel):
    chat_id: Optional[str] = None
    legenda: Optional[str] = ""


def _legenda(doc: dict) -> str:
    from services.garantia_conteudo import subtitulo
    return f"Segue o Laudo de Avaliação de Garantia {doc.get('numero') or ''} — {subtitulo(doc)}".strip()


@router.post("/garantias/{gid}/email")
async def enviar_email(gid: str, body: EmailBody, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services.ptam_share import enviar_ptam_email
    from services.garantia_conteudo import dados_rt
    doc = await _get(db, gid, uid)
    pdf, _nome = await _melhor_pdf(db, doc)
    rt = dados_rt(doc)
    endereco = " — ".join([x for x in [doc.get("endereco"), " / ".join(
        [y for y in [doc.get("municipio"), doc.get("uf")] if y])] if x]) or (doc.get("descricao_bem") or "")[:120]
    await enviar_ptam_email(
        to_email=body.destinatario, numero=doc.get("numero") or gid, endereco=endereco,
        pdf_bytes=pdf, nome_dest=body.nome_cliente or "", nome_avaliador=rt.get("nome") or "",
        registro_profissional=" · ".join(rt.get("registros_linhas") or [])[:120],
        mensagem_extra=body.mensagem_extra or "",
    )
    await db.email_logs.insert_one({
        "tipo": "garantia", "doc_id": gid, "numero": doc.get("numero"),
        "destinatario": body.destinatario, "nome_cliente": body.nome_cliente or "",
        "user_id": uid, "enviado_em": datetime.utcnow()})
    await link_tracking.registrar_evento(db, doc, "enviado", canal="email",
                                         destinatario=body.destinatario, colecao=COL)
    return {"ok": True, "mensagem": f"E-mail enviado para {body.destinatario}"}


@router.post("/garantias/{gid}/whatsapp")
async def enviar_whatsapp(gid: str, body: WhatsAppBody, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services import zapi_service
    from services import meta_whatsapp_service as meta
    cfg = await carregar_integracoes(db, uid)
    if not cfg:
        raise HTTPException(status_code=400, detail="Nenhum provedor WhatsApp configurado. Cadastre Z-API ou Meta em Configurações → Integrações.")
    doc = await _get(db, gid, uid)
    pdf, nome = await _melhor_pdf(db, doc)
    legenda = body.legenda or _legenda(doc)
    provider = (cfg.get("whatsapp_provider") or "zapi").lower()
    try:
        if provider == "meta":
            if not cfg.get("meta_phone_number_id") or not cfg.get("meta_access_token"):
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada. Cadastre em Configurações → Integrações.")
            resp = await meta.send_pdf(phone_number_id=cfg["meta_phone_number_id"], access_token=cfg["meta_access_token"],
                                       phone=body.phone, pdf_bytes=pdf, filename=nome, caption=legenda)
        else:
            if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
                raise HTTPException(status_code=400, detail="Z-API não configurada. Cadastre em Configurações → Integrações.")
            resp = await zapi_service.send_document_pdf(
                instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
                security_token=cfg.get("zapi_security_token"), phone=body.phone,
                pdf_bytes=pdf, filename=nome, caption=legenda)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error("Erro WhatsApp (garantia): %s", e)
        raise HTTPException(status_code=502, detail=f"Erro ao enviar WhatsApp: {e}")
    await link_tracking.registrar_evento(db, doc, "enviado", canal="whatsapp", destinatario=body.phone, colecao=COL)
    return {"ok": True, "provider": provider, "response": resp}


@router.post("/garantias/{gid}/whatsapp-link")
async def enviar_whatsapp_link(gid: str, body: WhatsAppBody, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services import zapi_service
    cfg = await carregar_integracoes(db, uid)
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(status_code=400, detail="Z-API não configurada. Cadastre em Configurações → Integrações.")
    doc = await _get(db, gid, uid)
    if not (doc.get("link_publico_token") and doc.get("link_publico_ativo")):
        raise HTTPException(status_code=400, detail="Gere/ative o link público do laudo antes de enviar.")
    link = _link_publico(doc["link_publico_token"])
    msg = body.legenda or f"Olá! {_legenda(doc)}.\n\nAcesse o laudo pelo link:\n{link}"
    try:
        resp = await zapi_service.send_text(
            instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"), phone=body.phone, message=msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Erro Z-API: {e}")
    await link_tracking.registrar_evento(db, doc, "enviado", canal="whatsapp", destinatario=body.phone, colecao=COL)
    return {"ok": True, "provider": "zapi", "response": resp}


@router.post("/garantias/{gid}/telegram")
async def enviar_telegram(gid: str, body: TelegramBody, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    import httpx
    cfg = await carregar_integracoes(db, uid)
    bot_token = (cfg or {}).get("telegram_bot_token")
    if not bot_token:
        raise HTTPException(status_code=400, detail="Telegram não configurado. Cadastre seu bot_token em Configurações → Integrações.")
    chat_id = (body.chat_id or "").strip() or (cfg or {}).get("telegram_chat_id_default")
    if not chat_id:
        raise HTTPException(status_code=400, detail="Informe um chat_id ou configure um padrão em Configurações → Integrações.")
    doc = await _get(db, gid, uid)
    pdf, nome = await _melhor_pdf(db, doc)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"https://api.telegram.org/bot{bot_token}/sendDocument",
                                  data={"chat_id": chat_id, "caption": body.legenda or _legenda(doc)},
                                  files={"document": (nome, pdf, _PDF)})
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Erro de rede ao enviar Telegram: {e}")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Telegram erro {r.status_code}: {r.text[:200]}")
    await link_tracking.registrar_evento(db, doc, "enviado", canal="telegram", destinatario=str(chat_id), colecao=COL)
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
# LINK PÚBLICO + AUDITORIA
# ════════════════════════════════════════════════════════════════════════════

@router.post("/garantias/{gid}/compartilhar")
async def compartilhar(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, gid, uid)
    token = doc.get("link_publico_token") or uuid.uuid4().hex
    agora = datetime.utcnow()
    await db.garantias.update_one({"id": gid, "user_id": uid}, {"$set": {
        "link_publico_token": token, "link_publico_ativo": True,
        "link_publico_criado_em": doc.get("link_publico_criado_em") or agora}})
    await link_tracking.registrar_evento(db, doc, "gerado", canal="link", colecao=COL)
    return {"ok": True, "token": token, "url": _link_publico(token)}


@router.delete("/garantias/{gid}/compartilhar")
async def desativar_compartilhamento(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, gid, uid)
    await db.garantias.update_one({"id": gid, "user_id": uid}, {"$set": {"link_publico_ativo": False}})
    await link_tracking.registrar_evento(db, doc, "desativado", canal="link", colecao=COL)
    return {"ok": True}


@router.get("/garantias/{gid}/link-eventos")
async def link_eventos(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    dados = await link_tracking.listar_eventos(db, gid, uid, colecao=COL)
    if not dados.get("encontrado"):
        raise HTTPException(status_code=404, detail="Avaliação de garantia não encontrada")
    return dados


def _pagina_publica(doc: dict, token: str) -> str:
    from html import escape
    from services.garantia_conteudo import brl, descricao_curta, subtitulo, valor_principal
    base = _base_url()
    titulo = f"Laudo de Avaliação de Garantia {doc.get('numero') or ''}".strip()
    desc = " · ".join([x for x in [subtitulo(doc), descricao_curta(doc)] if x])
    valor = brl(valor_principal(doc))
    local = " / ".join([x for x in [doc.get("municipio"), doc.get("uf")] if x])
    pdf_url = f"{base}/api/garantias/publico/{token}/pdf"
    img = f"{base}/brand/og-banner.png"
    e = escape
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titulo)}</title>
<meta property="og:title" content="{e(titulo)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{img}"><meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image"><meta name="robots" content="noindex">
<style>body{{margin:0;font-family:Inter,Arial,sans-serif;background:#0C3320;color:#f3f1e6;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px}}
.c{{max-width:460px;width:100%;background:#123f29;border:1px solid rgba(201,168,76,.35);border-radius:16px;padding:28px 22px;text-align:center}}
h1{{font-size:20px;margin:0 0 6px;color:#C9A84C}}p{{margin:4px 0;color:#d9e2db;font-size:14px}}
.v{{font-size:26px;font-weight:700;color:#fff;margin:18px 0 6px}}
a.b{{display:block;margin-top:22px;background:#C9A84C;color:#0C3320;font-weight:700;text-decoration:none;padding:14px;border-radius:10px}}
small{{display:block;margin-top:18px;color:#9fb3a6;font-size:11px}}</style></head>
<body><div class="c"><h1>{e(titulo)}</h1><p>{e(subtitulo(doc))}</p>
<p>{e(descricao_curta(doc))}</p><p>{e(local)}</p>
{f'<div class="v">{e(valor)}</div><p>Valor de mercado</p>' if valor else ''}
<a class="b" href="{pdf_url}">📄 Abrir o Laudo (PDF)</a>
<small>Res. CMN 4.676/2018 · ABNT NBR 14.653 — emitido pelo AvalieImob</small></div></body></html>"""


@router.get("/garantias/publico/{token}", response_class=HTMLResponse)
@pub_limiter.limit("30/minute")
async def pagina_publica(token: str, request: Request, db=Depends(get_db)):
    doc = await db.garantias.find_one({"link_publico_token": token, "link_publico_ativo": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Laudo não encontrado ou link inativo")
    ua = (request.headers.get("user-agent") or "").lower()
    if not any(b in ua for b in _BOTS):
        await link_tracking.registrar_evento(db, doc, "visualizado", ip=link_tracking.client_ip(request),
                                             user_agent=ua, colecao=COL)
    return HTMLResponse(_pagina_publica(doc, token), headers={"Cache-Control": "no-store"})


@router.get("/garantias/publico/{token}/pdf")
@pub_limiter.limit("30/minute")
async def pdf_publico(token: str, request: Request, db=Depends(get_db)):
    doc = await db.garantias.find_one({"link_publico_token": token, "link_publico_ativo": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Laudo não encontrado ou link inativo")
    data, nome = await _melhor_pdf(db, doc)
    return _resp(data, nome, _PDF, inline=True)


# ════════════════════════════════════════════════════════════════════════════
# RECIBO DE HONORÁRIOS
# ════════════════════════════════════════════════════════════════════════════

class ReciboBody(BaseModel):
    valor_honorarios: float
    forma_pagamento: Optional[str] = "PIX"
    data_pagamento: Optional[str] = None


def _como_ptam(doc: dict) -> dict:
    """Mapeia a Garantia para as chaves que o gerador de recibo espera."""
    from services.garantia_conteudo import TIPOS
    sol = doc.get("solicitante") or {}
    endereco = ", ".join([x for x in [doc.get("endereco"), " / ".join(
        [y for y in [doc.get("municipio"), doc.get("uf")] if y])] if x])
    return {
        "numero_ptam": (doc.get("numero") or "").replace("GAR-", ""),
        "solicitante_nome": sol.get("nome") or doc.get("mutuario_nome") or "Cliente",
        "solicitante_cpf_cnpj": sol.get("cpf_cnpj") or doc.get("mutuario_cpf_cnpj") or "",
        "solicitante_telefone": sol.get("telefone") or "",
        "property_label": TIPOS.get(doc.get("tipo_garantia"), "bem"),
        "property_address": endereco,
    }


@router.post("/garantias/{gid}/recibo")
async def gerar_recibo(gid: str, body: ReciboBody, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    if body.valor_honorarios <= 0:
        raise HTTPException(status_code=400, detail="Valor de honorários deve ser positivo")
    from models import Recibo
    from routes.recibos import _hidratar_emitente, _next_recibo_numero
    from services.recibo_zayra import gerar_recibo_pdf
    from services.garantia_conteudo import TIPOS

    doc = await _get(db, gid, uid)
    user = await db.users.find_one({"id": uid}) or {}
    perfil = await db.perfis_avaliador.find_one({"user_id": uid}) or {}
    pt = _como_ptam(doc)
    agora = datetime.utcnow()
    tipo = TIPOS.get(doc.get("tipo_garantia"), "bem")
    descricao = (
        f"Honorários técnicos referentes ao Laudo de Avaliação de Garantia nº {doc.get('numero') or ''} "
        f"({tipo}" + (f", {pt['property_address']}" if pt["property_address"] else "")
        + "), elaborado em conformidade com a Res. CMN 4.676/2018 e a ABNT NBR 14.653."
    )
    pdf = gerar_recibo_pdf(ptam=pt, user=user, perfil=perfil, valor=body.valor_honorarios,
                           forma_pagamento=body.forma_pagamento or "PIX",
                           data_pagamento=body.data_pagamento, referente=descricao, prefixo="REC-GAR")
    await db.recibos_garantia.insert_one({
        "id": str(uuid.uuid4()), "garantia_id": gid, "user_id": uid,
        "valor": body.valor_honorarios, "forma_pagamento": body.forma_pagamento,
        "content": pdf, "created_at": agora})

    # Também na aba Recibos (editar/assinar), upsert por garantia_id.
    token = doc.get("link_publico_token")
    if not (token and doc.get("link_publico_ativo")):
        token = token or uuid.uuid4().hex
        await db.garantias.update_one({"id": gid}, {"$set": {
            "link_publico_token": token, "link_publico_ativo": True, "link_publico_criado_em": agora}})
        await link_tracking.registrar_evento(db, doc, "gerado", canal="link", colecao=COL)
    link = _link_publico(token)
    data_pag = body.data_pagamento or agora.date().isoformat()
    existente = await db.recibos.find_one({"garantia_id": gid, "user_id": uid})
    if existente:
        upd = {"valor": body.valor_honorarios, "forma_pagamento": body.forma_pagamento or "PIX",
               "data_pagamento": data_pag, "descricao": descricao, "ptam_link": link, "updated_at": agora}
        if not existente.get("numero"):
            numero, seq = await _next_recibo_numero(db, "honorarios")
            upd.update({"numero": numero, "sequencia": seq, "status": "emitido"})
        await db.recibos.update_one({"id": existente["id"]}, {"$set": upd})
        recibo_id = existente["id"]
    else:
        emit = await _hidratar_emitente({}, user, perfil)
        numero, seq = await _next_recibo_numero(db, "honorarios")
        novo = Recibo(
            user_id=uid, tipo="honorarios", garantia_id=gid, ptam_link=link,
            destinatario_nome=pt["solicitante_nome"], destinatario_cpf_cnpj=pt["solicitante_cpf_cnpj"],
            destinatario_whatsapp=pt["solicitante_telefone"], valor=body.valor_honorarios,
            forma_pagamento=body.forma_pagamento or "PIX", data_pagamento=data_pag,
            descricao=descricao, status="emitido", numero=numero, sequencia=seq, **emit)
        await db.recibos.insert_one(novo.model_dump())
        recibo_id = novo.id
    await db.garantias.update_one({"id": gid}, {"$set": {
        "honorarios": body.valor_honorarios, "recibo_emitido": True,
        "recibo_emitido_em": agora, "recibo_id": recibo_id, "updated_at": agora}})
    return {"ok": True, "recibo_doc_id": recibo_id, "download_url": f"/api/garantias/{gid}/recibo"}


@router.get("/garantias/{gid}/recibo")
async def baixar_recibo(gid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, gid, uid)
    r = await db.recibos_garantia.find_one({"garantia_id": gid, "user_id": uid}, sort=[("created_at", -1)])
    if not r or not r.get("content"):
        raise HTTPException(status_code=404, detail="Recibo ainda não gerado")
    nome = f"RECIBO_GARANTIA_{(doc.get('numero') or gid).replace('/', '-')}.pdf"
    return _resp(bytes(r["content"]), nome, _PDF)
