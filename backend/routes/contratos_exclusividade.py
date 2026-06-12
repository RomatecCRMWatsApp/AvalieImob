# @module routes.contratos_exclusividade — Exclusividade com aceite eletrônico via WhatsApp
"""
Fluxo leve de Exclusividade de Corretagem com ACEITE ELETRÔNICO (link/WhatsApp,
token por signatário). Collection própria `contratos_exclusividade`, distinta do
módulo `contratos` (ICP-Brasil/D4Sign).

Convenções do projeto:
  - auth: get_active_subscriber -> uid (str); ownership por user_id em toda query
  - db:   Depends(get_db) -> Motor; id = uuid string (campo "id")
  - Z-API: services.zapi_service + credenciais via services.integracoes_util.carregar_integracoes
  - storage: services.r2_storage.upload_bytes
  - rotas públicas (aceite/verificar): SEM auth, COM rate limit (slowapi)
"""
import logging
import os
import uuid as _uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from dependencies import get_active_subscriber
from models.contrato_exclusividade import (
    AceiteInput, ContratoExclusividadeCreate, StatusContrato, StatusSignatario, exige_conjuge,
)
from services.contrato_exclusividade_assinatura import (
    agora_utc, gerar_hash_documento, gerar_token,
)
from services.contrato_exclusividade_pdf import (
    gerar_pdf_final, gerar_pdf_rascunho, montar_texto_contrato,
)

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/contratos-exclusividade", tags=["Contratos de Exclusividade"])
router_publico = APIRouter(prefix="/publico/contratos-exclusividade", tags=["Aceite Público"])

APP_URL = os.environ.get("APP_PUBLIC_URL", "https://romatecavalieimob.com.br").rstrip("/")
EXPIRACAO_DIAS = int(os.environ.get("CONTRATO_EXPIRACAO_DIAS", "7"))
COL = "contratos_exclusividade"


# ───────────────────────── helpers ─────────────────────────

def _montar_signatarios(payload: ContratoExclusividadeCreate) -> list:
    sigs = [{
        "papel": "proprietario",
        "nome": payload.proprietario.nome,
        "cpf": payload.proprietario.cpf,
        "whatsapp": payload.proprietario.whatsapp,
        "token": gerar_token(),
        "status": StatusSignatario.PENDENTE.value,
        "aceite": None,
    }]
    if payload.conjuge and exige_conjuge(payload.estado_civil, payload.regime_bens):
        sigs.append({
            "papel": "conjuge",
            "nome": payload.conjuge.nome,
            "cpf": payload.conjuge.cpf,
            "whatsapp": payload.conjuge.whatsapp,
            "token": gerar_token(),
            "status": StatusSignatario.PENDENTE.value,
            "aceite": None,
        })
    return sigs


def _publico_view(contrato: dict, signatario: dict) -> dict:
    return {
        "signatario": {"nome": signatario["nome"], "papel": signatario["papel"],
                       "status": signatario["status"]},
        "imovel": contrato["imovel"],
        "proprietario_nome": contrato["proprietario"]["nome"],
        "conjuge_nome": contrato["conjuge"]["nome"] if contrato.get("conjuge") else None,
        "comissao_percentual": contrato["comissao_percentual"],
        "prazo_meses": contrato["prazo_meses"],
        "hash_documento": contrato["hash_documento"],
        "texto_contrato": montar_texto_contrato(contrato),
    }


async def _zapi_cfg(db, uid: str) -> dict:
    from services.integracoes_util import carregar_integracoes
    cfg = await carregar_integracoes(db, uid)
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(
            status_code=400,
            detail="Z-API não configurada em Configurações → Integrações.")
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


# ───────────────────────── rotas autenticadas ─────────────────────────

@router.post("", status_code=201)
async def criar_contrato(
    payload: ContratoExclusividadeCreate,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = payload.model_dump(mode="json")
    cid = str(_uuid.uuid4())
    doc.update({
        "id": cid,
        "user_id": uid,
        "tipo": "exclusividade",
        "status": StatusContrato.RASCUNHO.value,
        "signatarios": _montar_signatarios(payload),
        "criado_em": agora_utc(),
        "expira_em": agora_utc() + timedelta(days=EXPIRACAO_DIAS),
        "pdf_final_url": None,
    })
    doc["hash_documento"] = gerar_hash_documento(doc)
    await db[COL].insert_one(doc)
    return {"id": cid, "hash_documento": doc["hash_documento"],
            "total_signatarios": len(doc["signatarios"])}


@router.get("")
async def listar_contratos(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    out = []
    async for c in db[COL].find({"user_id": uid}).sort("criado_em", -1):
        c.pop("_id", None)
        for s in c.get("signatarios", []):
            s.pop("token", None)  # nunca vaza token na listagem
        out.append(c)
    return out


@router.get("/{cid}")
async def obter_contrato(cid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    c = await db[COL].find_one({"id": cid, "user_id": uid})
    if not c:
        raise HTTPException(404, "Contrato não encontrado")
    c.pop("_id", None)
    for s in c.get("signatarios", []):
        s.pop("token", None)  # token não precisa no client (reenvio é server-side)
    return c


@router.post("/{cid}/enviar")
async def enviar_contrato(cid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    contrato = await db[COL].find_one({"id": cid, "user_id": uid})
    if not contrato:
        raise HTTPException(404, "Contrato não encontrado")
    if contrato["status"] not in (StatusContrato.RASCUNHO.value, StatusContrato.ENVIADO.value):
        raise HTTPException(409, f"Contrato no status '{contrato['status']}' não pode ser enviado")

    cfg = await _zapi_cfg(db, uid)
    pdf_bytes = gerar_pdf_rascunho(contrato)
    notificados = 0
    for s in contrato["signatarios"]:
        if s["status"] == StatusSignatario.ACEITO.value:
            continue
        link = f"{APP_URL}/aceite/{s['token']}"
        papel = "proprietário(a)" if s["papel"] == "proprietario" else "cônjuge/companheiro(a)"
        msg = (
            f"Olá, *{s['nome']}*! 👋\n\n"
            f"A *Romatec Consultoria Total* enviou um *Contrato de Exclusividade de "
            f"Corretagem* para sua análise e aceite eletrônico, na condição de {papel}.\n\n"
            f"📍 Imóvel: {contrato['imovel']['descricao']}\n"
            f"💰 Valor anunciado: R$ {contrato['imovel']['valor_anunciado']:,.2f}\n"
            f"📆 Prazo de exclusividade: {contrato['prazo_meses']} meses\n\n"
            f"👉 Leia o contrato completo e confirme o aceite:\n{link}\n\n"
            f"🔒 Link individual e intransferível. Válido por {EXPIRACAO_DIAS} dias.\n"
            f"_Aceite eletrônico com validade jurídica (MP 2.200-2/2001 e Lei 14.063/2020)._"
        )
        try:
            await _enviar_texto(cfg, s["whatsapp"], msg)
            await _enviar_pdf(cfg, s["whatsapp"], pdf_bytes,
                              filename=f"contrato_exclusividade_{cid}_rascunho.pdf")
            notificados += 1
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Falha Z-API ao enviar contrato %s para %s", cid, s["nome"])
            raise HTTPException(502, f"Falha no envio Z-API para {s['nome']}: {exc}")

    await db[COL].update_one(
        {"id": cid, "user_id": uid},
        {"$set": {"status": StatusContrato.ENVIADO.value, "enviado_em": agora_utc()}})
    return {"ok": True, "signatarios_notificados": notificados}


@router.post("/{cid}/reenviar/{papel}")
async def reenviar(cid: str, papel: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    contrato = await db[COL].find_one({"id": cid, "user_id": uid})
    if not contrato:
        raise HTTPException(404, "Contrato não encontrado")
    alvo = next((s for s in contrato["signatarios"]
                 if s["papel"] == papel and s["status"] == StatusSignatario.PENDENTE.value), None)
    if not alvo:
        raise HTTPException(404, "Signatário pendente não encontrado para este papel")
    cfg = await _zapi_cfg(db, uid)
    link = f"{APP_URL}/aceite/{alvo['token']}"
    await _enviar_texto(cfg, alvo["whatsapp"],
                        f"🔔 Lembrete: o contrato de exclusividade aguarda seu aceite.\n{link}")
    return {"ok": True}


@router.post("/{cid}/cancelar")
async def cancelar(cid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    r = await db[COL].update_one(
        {"id": cid, "user_id": uid, "status": {"$ne": StatusContrato.ASSINADO.value}},
        {"$set": {"status": StatusContrato.CANCELADO.value, "cancelado_em": agora_utc()}})
    if r.matched_count == 0:
        raise HTTPException(404, "Contrato não encontrado ou já assinado")
    return {"ok": True}


# ───────────────────────── rotas públicas (sem auth, com rate limit) ─────────────────────────

@router_publico.get("/aceite/{token}")
@limiter.limit("20/minute")
async def obter_por_token(token: str, request: Request, db=Depends(get_db)):
    contrato = await db[COL].find_one({"signatarios.token": token})
    if not contrato:
        raise HTTPException(404, "Link inválido")
    if contrato["status"] in (StatusContrato.CANCELADO.value, StatusContrato.EXPIRADO.value):
        raise HTTPException(410, "Este contrato não está mais disponível para aceite")
    if agora_utc() > contrato["expira_em"]:
        await db[COL].update_one({"id": contrato["id"]},
                                 {"$set": {"status": StatusContrato.EXPIRADO.value}})
        raise HTTPException(410, "Link expirado — solicite reenvio ao corretor")
    signatario = next(s for s in contrato["signatarios"] if s["token"] == token)
    return _publico_view(contrato, signatario)


@router_publico.post("/aceite/{token}/confirmar")
@limiter.limit("10/minute")
async def confirmar_aceite(token: str, payload: AceiteInput, request: Request, db=Depends(get_db)):
    if not payload.concordo:
        raise HTTPException(400, "É necessário marcar a concordância com os termos")
    contrato = await db[COL].find_one({"signatarios.token": token})
    if not contrato:
        raise HTTPException(404, "Link inválido")
    if agora_utc() > contrato["expira_em"]:
        await db[COL].update_one({"id": contrato["id"]},
                                 {"$set": {"status": StatusContrato.EXPIRADO.value}})
        raise HTTPException(410, "Link expirado")

    signatario = next(s for s in contrato["signatarios"] if s["token"] == token)
    if signatario["status"] == StatusSignatario.ACEITO.value:
        raise HTTPException(409, "Aceite já registrado para este signatário")
    if payload.nome_digitado.strip().lower() != signatario["nome"].strip().lower():
        # registra tentativa divergente em audit log
        try:
            await db["audit_log"].insert_one({
                "modulo": "contrato_exclusividade", "evento": "aceite_nome_divergente",
                "contrato_id": contrato["id"], "papel": signatario["papel"],
                "nome_digitado": payload.nome_digitado.strip(), "criado_em": agora_utc(),
            })
        except Exception:
            pass
        raise HTTPException(422,
            "O nome digitado não confere com o nome do signatário. "
            "Digite o nome completo exatamente como consta no contrato.")

    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "0.0.0.0")
    ip = ip.split(",")[0].strip()
    aceite = {
        "data_hora_utc": agora_utc(),
        "ip": ip,
        "user_agent": request.headers.get("user-agent", ""),
        "whatsapp_vinculado": signatario["whatsapp"],
        "nome_digitado": payload.nome_digitado.strip(),
        "hash_documento_no_aceite": contrato["hash_documento"],
    }
    await db[COL].update_one(
        {"id": contrato["id"], "signatarios.token": token},
        {"$set": {"signatarios.$.status": StatusSignatario.ACEITO.value,
                  "signatarios.$.aceite": aceite}})

    contrato = await db[COL].find_one({"id": contrato["id"]})
    todos = all(s["status"] == StatusSignatario.ACEITO.value for s in contrato["signatarios"])

    if not todos:
        await db[COL].update_one({"id": contrato["id"]},
                                 {"$set": {"status": StatusContrato.PARCIALMENTE_ASSINADO.value}})
        return {"ok": True, "status": "parcialmente_assinado", "todos_assinaram": False,
                "mensagem": "Aceite registrado. Aguardando o(s) demais signatário(s)."}

    # Todos aceitaram → PDF final + envio
    pdf_final = gerar_pdf_final(contrato)
    pdf_url = None
    try:
        from services.r2_storage import upload_bytes
        key = f"contratos-exclusividade/{contrato['id']}/contrato_assinado.pdf"
        pdf_url = upload_bytes(pdf_final, key, "application/pdf")
    except Exception:
        logger.exception("Falha ao subir PDF final do contrato %s", contrato["id"])

    await db[COL].update_one(
        {"id": contrato["id"]},
        {"$set": {"status": StatusContrato.ASSINADO.value, "assinado_em": agora_utc(),
                  "pdf_final_url": pdf_url}})

    # Envio do PDF final p/ todos os signatários + corretor (via Z-API do corretor)
    try:
        cfg = await _zapi_cfg(db, contrato["user_id"])
        destinatarios = [s["whatsapp"] for s in contrato["signatarios"]]
        corretor = await db["users"].find_one({"id": contrato["user_id"]}) or {}
        if corretor.get("whatsapp"):
            destinatarios.append("".join(filter(str.isdigit, corretor["whatsapp"])))
        legenda = (f"✅ Contrato de Exclusividade assinado por todas as partes!\n"
                   f"🔐 Verifique: {APP_URL}/verificar/{contrato['hash_documento']}")
        for numero in set(destinatarios):
            try:
                await _enviar_pdf(cfg, numero, pdf_final,
                                  filename="contrato_exclusividade_assinado.pdf", caption=legenda)
            except Exception:
                logger.exception("Falha ao enviar PDF final para %s", numero)
    except HTTPException:
        logger.warning("Z-API não configurada — PDF final não enviado (contrato %s)", contrato["id"])

    return {"ok": True, "status": "assinado", "todos_assinaram": True}


@router_publico.get("/verificar/{hash_documento}")
@limiter.limit("30/minute")
async def verificar(hash_documento: str, request: Request, db=Depends(get_db)):
    contrato = await db[COL].find_one({"hash_documento": hash_documento})
    if not contrato:
        return {"valido": False, "mensagem": "Nenhum documento encontrado para este código"}
    return {
        "valido": True,
        "status": contrato["status"],
        "imovel": contrato["imovel"]["descricao"],
        "cidade": f"{contrato['imovel']['cidade']}/{contrato['imovel']['uf']}",
        "signatarios": [
            {"nome": s["nome"], "papel": s["papel"], "status": s["status"],
             "data_aceite": s["aceite"]["data_hora_utc"] if s.get("aceite") else None}
            for s in contrato["signatarios"]
        ],
        "hash_documento": hash_documento,
        "assinado_em": contrato.get("assinado_em"),
        "pdf_final_url": contrato.get("pdf_final_url"),
    }
