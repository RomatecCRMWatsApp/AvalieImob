# @module routes.documentos_externos — Documentos Externos (doc-ext): upload de PDF arbitrário,
# N signatários, posicionar, enviar por WhatsApp, ICP opcional do RT. Isolado por user_id.
import asyncio
import hashlib
import io
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.documento_externo import novo_signatario, recalcular_status
from services import r2_storage
from services.documento_externo_service import COL, proximo_codigo
from services.upload_security import detect_content_type, normalize_filename

router = APIRouter(prefix="/documentos-externos", tags=["documentos-externos"])
logger = logging.getLogger("romatec")
_MAX_BYTES = 25 * 1024 * 1024


def _contar_paginas(pdf_bytes: bytes) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception:
        return 0


async def _carregar(db, doc_id: str, uid: str) -> dict:
    doc = await db[COL].find_one({"id": doc_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    # self-heal: um bug breve gravou status='coletando_testemunhas' (não é status do
    # doc-ext). Testemunhas só entram em doc já finalizado → restaura p/ 'finalizado'.
    if doc.get("status") == "coletando_testemunhas":
        doc["status"] = "finalizado"
        await db[COL].update_one({"id": doc_id, "user_id": uid}, {"$set": {"status": "finalizado"}})
    return doc


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    titulo: str = Form(...),
    descricao: str = Form(""),
    requer_icp_rt: bool = Form(True),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    conteudo = await file.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(conteudo) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo excede 25 MB ({len(conteudo)/1024/1024:.1f} MB).")
    if detect_content_type(conteudo) != "application/pdf" or not conteudo.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF válido.")

    doc_id = uuid.uuid4().hex
    nome = normalize_filename(file.filename, fallback="documento")
    if not nome.lower().endswith(".pdf"):
        nome = f"{nome}.pdf"
    pdf_key = f"documentos-externos/{uid}/{doc_id}.pdf"
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, conteudo, pdf_key, "application/pdf", "private, max-age=0")
    except Exception as e:  # noqa: BLE001
        logger.error("Falha ao subir doc-ext ao R2: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao armazenar o documento.")

    reg = {
        "id": doc_id, "user_id": uid, "codigo": await proximo_codigo(db),
        "titulo": titulo.strip() or nome, "descricao": (descricao or "").strip() or None,
        "requer_icp_rt": bool(requer_icp_rt),
        "pdf_key": pdf_key, "pdf_hash_sha256": hashlib.sha256(conteudo).hexdigest(),
        "nome_arquivo": nome, "paginas": _contar_paginas(conteudo), "tamanho": len(conteudo),
        "signatarios": [], "pdf_key_intermediario": None, "pdf_key_final": None,
        "status": "rascunho", "historico": [{"em": datetime.utcnow(), "tipo": "criado"}],
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    }
    await db[COL].insert_one(reg)
    return serialize_doc(reg)


def _slim_card(d: dict) -> dict:
    """Versão leve p/ a lista/card: signatários só com o essencial (sem o traço base64,
    token, IP/UA) e sem o histórico — para o card não trafegar dados pesados."""
    out = serialize_doc(d)
    out["signatarios"] = [
        {"id": s.get("id"), "nome": s.get("nome"), "papel": s.get("papel"),
         "status": s.get("status"), "whatsapp": s.get("whatsapp"),
         "assinado_em": (s.get("assinado_em").isoformat()
                         if hasattr(s.get("assinado_em"), "isoformat") else s.get("assinado_em"))}
        for s in (d.get("signatarios") or [])]
    if out.get("status") == "coletando_testemunhas":
        out["status"] = "finalizado"   # status legado inválido (ver _carregar)
    out["testemunhas"] = [
        {"id": t.get("id"), "nome": t.get("nome"), "status": t.get("status"),
         "vinculo": t.get("vinculo"), "parte_vinculada_nome": t.get("parte_vinculada_nome"),
         "assinado_em": (t.get("assinado_em").isoformat()
                         if hasattr(t.get("assinado_em"), "isoformat") else t.get("assinado_em"))}
        for t in (d.get("testemunhas") or [])]
    out.pop("historico", None)
    return out


@router.get("")
async def listar(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    docs = await db[COL].find({"user_id": uid}).sort("created_at", -1).to_list(length=500)
    return [_slim_card(d) for d in docs]


@router.get("/{doc_id}")
async def obter(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return serialize_doc(await _carregar(db, doc_id, uid))


@router.patch("/{doc_id}")
async def editar(doc_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _carregar(db, doc_id, uid)
    campos = {k: payload[k] for k in ("titulo", "descricao", "requer_icp_rt", "valor_referencia") if k in payload}
    campos["updated_at"] = datetime.utcnow()
    await db[COL].update_one({"id": doc_id, "user_id": uid}, {"$set": campos})
    return serialize_doc(await _carregar(db, doc_id, uid))


@router.delete("/{doc_id}")
async def excluir(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    for key in (doc.get("pdf_key"), doc.get("pdf_key_intermediario"), doc.get("pdf_key_final")):
        if key:
            try:
                await asyncio.to_thread(r2_storage.delete_object, key)
            except Exception:
                pass
    await db[COL].delete_one({"id": doc_id, "user_id": uid})
    try:
        await db["assinaturas_pdf"].delete_many({"doc_tipo": "doc-ext", "doc_id": doc_id})
    except Exception:
        pass
    return {"ok": True}


# ── PDFs ──────────────────────────────────────────────────────────────────────
async def _servir_pdf(db, doc_id: str, uid: str, campo: str, nome: str):
    doc = await _carregar(db, doc_id, uid)
    key = doc.get(campo) or doc.get("pdf_key")
    try:
        pdf = await asyncio.to_thread(r2_storage.download_bytes, key)
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo indisponível.")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nome}"', "Cache-Control": "no-store"})


@router.get("/{doc_id}/pdf-original")
async def pdf_original(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await _servir_pdf(db, doc_id, uid, "pdf_key", "documento.pdf")


@router.get("/{doc_id}/pdf-intermediario")
async def pdf_intermediario(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await _servir_pdf(db, doc_id, uid, "pdf_key_intermediario", "documento_clientes.pdf")


@router.get("/{doc_id}/pdf-final")
async def pdf_final(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Serve o PDF ASSINADO ICP se houver; senão o intermediário; senão o original."""
    from routes.assinatura import _load_assinatura_bytes
    assinado, _ = await _load_assinatura_bytes(db, "doc-ext", doc_id)
    if assinado:
        return Response(content=assinado, media_type="application/pdf",
                        headers={"Content-Disposition": 'inline; filename="documento_final.pdf"', "Cache-Control": "no-store"})
    return await _servir_pdf(db, doc_id, uid, "pdf_key_intermediario", "documento_final.pdf")


# ── Signatários ─────────────────────────────────────────────────────────────────
@router.post("/{doc_id}/signatarios")
async def add_signatario(doc_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _carregar(db, doc_id, uid)
    sig = novo_signatario(payload)
    await db[COL].update_one({"id": doc_id, "user_id": uid},
                             {"$push": {"signatarios": sig}, "$set": {"updated_at": datetime.utcnow()}})
    return sig


@router.patch("/{doc_id}/signatarios/{sid}")
async def edit_signatario(doc_id: str, sid: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    sig = next((s for s in doc.get("signatarios", []) if s.get("id") == sid), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Signatário não encontrado.")
    if sig.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Signatário já assinou — não pode editar.")
    upd = {}
    for k in ("nome", "papel"):
        if k in payload:
            upd[f"signatarios.$.{k}"] = str(payload[k] or "")
    for k in ("cpf_cnpj", "whatsapp"):
        if k in payload:
            upd[f"signatarios.$.{k}"] = "".join(filter(str.isdigit, str(payload[k] or "")))
    if "email" in payload:
        upd["signatarios.$.email"] = payload["email"] or None
    upd["updated_at"] = datetime.utcnow()
    await db[COL].update_one({"id": doc_id, "user_id": uid, "signatarios.id": sid}, {"$set": upd})
    return {"ok": True}


@router.delete("/{doc_id}/signatarios/{sid}")
async def del_signatario(doc_id: str, sid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    sig = next((s for s in doc.get("signatarios", []) if s.get("id") == sid), None)
    if sig and sig.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Signatário já assinou — não pode remover.")
    await db[COL].update_one({"id": doc_id, "user_id": uid},
                             {"$pull": {"signatarios": {"id": sid}}, "$set": {"updated_at": datetime.utcnow()}})
    return {"ok": True}


# ── Preparar / Posicionar / Enviar ───────────────────────────────────────────────
@router.post("/{doc_id}/preparar")
async def preparar(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Renderiza as páginas do PDF original p/ o RT posicionar as caixas, e pré-carrega a
    assinatura visual salva do RT (ou gera uma cursiva do nome)."""
    doc = await _carregar(db, doc_id, uid)
    pdf = await asyncio.to_thread(r2_storage.download_bytes, doc["pdf_key"])
    from services.pdf_preview import renderizar_paginas
    paginas = await asyncio.to_thread(renderizar_paginas, pdf)
    perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}
    rt_nome = perfil.get("nome") or "Responsável Técnico"
    rt_b64 = perfil.get("assinatura_visual_b64")
    rt_padrao = False
    if not rt_b64:
        from services.assinatura_default import gerar_assinatura_nome_b64
        rt_b64 = await asyncio.to_thread(gerar_assinatura_nome_b64, rt_nome)
        rt_padrao = bool(rt_b64)
    sigs = [{"id": s["id"], "nome": s.get("nome"), "papel": s.get("papel"),
             "whatsapp": s.get("whatsapp")} for s in doc.get("signatarios", [])]
    return {"ok": True, "paginas": paginas, "signatarios": sigs,
            "rt": {"nome": rt_nome, "assinatura_b64": rt_b64, "assinatura_padrao": rt_padrao}}


@router.post("/{doc_id}/posicionar")
async def posicionar(doc_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Salva as posições por signatário, carimba o traço do RT na base (opção A), gera/dispara
    os links por WhatsApp. payload: {posicoes: {sid: [{pagina,x_pt,y_pt,larg_pt,alt_pt,tipo}]},
    rt_traco: 'data:image/png;base64,...', rt_ancora: {pagina,x_pt,...}}."""
    import base64
    from services.documento_externo_service import zapi_cfg, enviar_texto, enviar_pdf
    doc = await _carregar(db, doc_id, uid)
    sigs = doc.get("signatarios", [])
    if not sigs:
        raise HTTPException(status_code=422, detail="Cadastre ao menos um signatário.")
    pos_map = payload.get("posicoes") or {}
    faltam_pos = [s["nome"] for s in sigs if not (pos_map.get(s["id"]) or [])]
    if faltam_pos:
        raise HTTPException(status_code=422, detail=f"Posicione a assinatura de: {', '.join(faltam_pos)}")
    faltam_fone = [s["nome"] for s in sigs if not "".join(filter(str.isdigit, str(s.get("whatsapp") or "")))]
    if faltam_fone:
        raise HTTPException(status_code=422, detail=f"Informe o WhatsApp de: {', '.join(faltam_fone)}")

    # FALHA RÁPIDA: se a Z-API não estiver configurada, aborta ANTES de mexer no estado
    # (em vez de marcar tudo como 'enviado' e os envios falharem em silêncio).
    cfg = await zapi_cfg(db, uid)

    # grava posições em cada signatário
    for s in sigs:
        s["posicoes"] = pos_map.get(s["id"], [])
        s["status"] = "enviado"

    # RT desenha + posiciona: carimba o traço do RT na base ANTES de enviar (opção A)
    rt_traco = payload.get("rt_traco") or ""
    rt_anc = payload.get("rt_ancora") or {}
    if rt_traco.startswith("data:image/png;base64,") and rt_anc:
        try:
            png = base64.b64decode(rt_traco.split(",", 1)[1])
            await db.perfil_avaliador.update_one(
                {"user_id": uid}, {"$set": {"assinatura_visual_b64": rt_traco.split(",", 1)[1]}}, upsert=True)
            base = await asyncio.to_thread(r2_storage.download_bytes, doc["pdf_key"])
            from services.assinatura_cliente_carimbo import carimbar_traco_em_pagina
            x = float(rt_anc.get("x_pt", 0)); y = float(rt_anc.get("y_pt", 0))
            w = float(rt_anc.get("larg_pt", 0)); h = float(rt_anc.get("alt_pt", 0))
            base = await asyncio.to_thread(carimbar_traco_em_pagina, base, int(rt_anc.get("pagina", 0)),
                                           (x, y, x + w, y + h), png, "Responsável Técnico")
            await asyncio.to_thread(r2_storage.upload_bytes, base, doc["pdf_key"], "application/pdf")
        except Exception:
            logger.warning("Falha ao carimbar assinatura do RT (doc-ext).", exc_info=True)

    await db[COL].update_one({"id": doc_id, "user_id": uid},
                             {"$set": {"signatarios": sigs, "updated_at": datetime.utcnow()}})
    await db[COL].update_one({"id": doc_id}, {"$set": {"status": recalcular_status({**doc, "signatarios": sigs})}})

    # minuta (marca d'água) p/ leitura + link por signatário
    from services.marca_dagua import aplicar_marca_dagua
    base_atual = await asyncio.to_thread(r2_storage.download_bytes, doc["pdf_key"])
    try:
        minuta = await asyncio.to_thread(aplicar_marca_dagua, base_atual, "MINUTA")
    except Exception:
        logger.warning("Falha ao gerar minuta (doc-ext) — segue sem ela.", exc_info=True)
        minuta = None
    from routes.assinatura_cliente import APP_URL
    links, enviados, falhas = [], 0, []
    for s in sigs:
        url = f"{APP_URL}/assinar-doc/{s['token']}"
        primeiro = str(s.get("nome") or "").split(" ")[0]
        fone = "".join(filter(str.isdigit, str(s.get("whatsapp") or "")))
        msg = (f"Olá, {primeiro}! A *Romatec Consultoria Total* enviou um documento para sua "
               f"assinatura eletrônica.\n\nLeia a *MINUTA* abaixo e assine com segurança neste link:\n{url}\n\n"
               f"Link pessoal, validade limitada (Lei 14.063/2020).")
        try:
            await enviar_texto(cfg, fone, msg)          # o LINK é o essencial
            enviados += 1
            if minuta and minuta.startswith(b"%PDF-"):
                try:
                    await enviar_pdf(cfg, fone, minuta, "minuta", "MINUTA (rascunho) — para leitura.")
                except Exception:                       # minuta falhar não invalida o link já enviado
                    logger.warning("Falha ao enviar minuta doc-ext p/ %s", fone, exc_info=True)
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao enviar link doc-ext p/ %s: %s", fone, e, exc_info=True)
            falhas.append({"nome": s["nome"], "telefone": fone, "erro": str(e) or e.__class__.__name__})
        links.append({"sid": s["id"], "nome": s["nome"], "url": url})
    return {"ok": True, "links": links, "enviados": enviados, "falhas": falhas, "total": len(sigs)}


@router.post("/{doc_id}/reenviar")
async def reenviar(doc_id: str, payload: dict = None, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Reenvia o link aos pendentes (telefones editáveis em payload.signatarios=[{id,whatsapp}])."""
    from services.documento_externo_service import zapi_cfg, enviar_texto
    doc = await _carregar(db, doc_id, uid)
    novos = {s.get("id"): "".join(filter(str.isdigit, str(s.get("whatsapp") or "")))
             for s in (payload or {}).get("signatarios", []) if s.get("id")}
    pendentes = [s for s in doc.get("signatarios", []) if s.get("status") != "assinado"]
    if not pendentes:
        raise HTTPException(status_code=400, detail="Nenhum signatário pendente.")
    cfg = await zapi_cfg(db, uid)
    from routes.assinatura_cliente import APP_URL
    enviados, falhas = 0, []
    for s in pendentes:
        fone = novos.get(s["id"]) or "".join(filter(str.isdigit, str(s.get("whatsapp") or "")))
        if not fone:
            continue
        if novos.get(s["id"]):
            await db[COL].update_one({"id": doc_id, "signatarios.id": s["id"]},
                                     {"$set": {"signatarios.$.whatsapp": fone}})
        url = f"{APP_URL}/assinar-doc/{s['token']}"
        try:
            await enviar_texto(cfg, fone, f"Olá! Reenvio do link para assinar:\n{url}")
            enviados += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao reenviar doc-ext p/ %s: %s", fone, e, exc_info=True)
            falhas.append({"nome": s["nome"], "telefone": fone, "erro": str(e) or e.__class__.__name__})
    return {"ok": True, "reenviados": enviados, "falhas": falhas}


@router.get("/{doc_id}/sessao-status")
async def sessao_status(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    sigs = [{"id": s["id"], "nome": s.get("nome"), "papel": s.get("papel"),
             "whatsapp": s.get("whatsapp"), "status": s.get("status"),
             "assinado_em": (s.get("assinado_em").isoformat() if hasattr(s.get("assinado_em"), "isoformat") else s.get("assinado_em"))}
            for s in doc.get("signatarios", [])]
    assinados = sum(1 for s in sigs if s["status"] == "assinado")
    return {"ok": True, "status": doc.get("status"), "signatarios": sigs,
            "assinados": assinados, "total": len(sigs), "requer_icp_rt": doc.get("requer_icp_rt")}


def _dig(v) -> str:
    return "".join(filter(str.isdigit, str(v or "")))


async def _via_final_bytes(db, doc: dict, doc_id: str):
    """(bytes, via) da VIA FINAL: o PDF assinado por ICP se houver; senão o intermediário
    carimbado (assinaturas dos clientes + folha de auditoria). (None, None) se ainda não há."""
    from routes.assinatura import _load_assinatura_bytes
    assinado, _ = await _load_assinatura_bytes(db, "doc-ext", doc_id)
    if assinado and assinado.startswith(b"%PDF-"):
        return assinado, "final (ICP-Brasil)"
    key = doc.get("pdf_key_intermediario")
    if key:
        try:
            b = await asyncio.to_thread(r2_storage.download_bytes, key)
            if b and b.startswith(b"%PDF-"):
                return b, "assinada pelos signatários"
        except Exception:
            pass
    return None, None


@router.post("/{doc_id}/distribuir-final")
async def distribuir_final(doc_id: str, payload: dict = None,
                           uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Envia a VIA FINALIZADA por WhatsApp ao número de CADA signatário. Funciona tanto após o
    ICP do RT (via=ICP) quanto sem ICP (via=intermediário carimbado). Aceita números editáveis
    em payload.signatarios=[{id, whatsapp}] (default = o número salvo de cada um) e retorna o
    resultado por destinatário (enviados/falhas)."""
    from services.documento_externo_service import enviar_pdf, zapi_cfg
    doc = await _carregar(db, doc_id, uid)
    pdf, via = await _via_final_bytes(db, doc, doc_id)
    if not pdf:
        raise HTTPException(status_code=400,
                            detail="Ainda não há via finalizada — faltam assinaturas dos signatários (ou o ICP do RT).")
    # se a via veio do ICP, marca finalizado
    if via and via.startswith("final"):
        await db[COL].update_one({"id": doc_id, "user_id": uid},
                                 {"$set": {"status": "finalizado", "pdf_final_assinado_em": datetime.utcnow()}})
    # números editáveis por signatário (default = o salvo)
    novos = {s.get("id"): _dig(s.get("whatsapp")) for s in (payload or {}).get("signatarios", []) if s.get("id")}
    # seleção de quais signatários enviar (None = TODOS [1º envio]; lista = só esses [reenvio])
    sel_ids = (payload or {}).get("enviar_ids")
    sel_set = set(sel_ids) if isinstance(sel_ids, list) else None
    cfg = await zapi_cfg(db, uid)
    caption = (f"Segue a *via FINALIZADA* ({via}) do documento *{doc.get('titulo', '')}*. "
               f"Obrigado! — Romatec Consultoria Total")
    nome_arq = f"{doc.get('codigo', 'documento')}_final"
    enviados, falhas, vistos = 0, [], set()
    for s in doc.get("signatarios", []):
        if sel_set is not None and s.get("id") not in sel_set:
            continue  # reenvio seletivo: pula quem não foi marcado
        fone = novos.get(s["id"]) or _dig(s.get("whatsapp"))
        if not fone:
            falhas.append({"nome": s.get("nome"), "telefone": "", "erro": "sem WhatsApp"})
            continue
        if novos.get(s["id"]) and novos[s["id"]] != _dig(s.get("whatsapp")):
            await db[COL].update_one({"id": doc_id, "signatarios.id": s["id"]},
                                     {"$set": {"signatarios.$.whatsapp": fone}})
        try:
            await enviar_pdf(cfg, fone, pdf, nome_arq, caption)
            enviados += 1
            vistos.add(fone)
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao enviar via final doc-ext p/ %s: %s", fone, e, exc_info=True)
            falhas.append({"nome": s.get("nome"), "telefone": fone, "erro": str(e) or e.__class__.__name__})

    # DESTINATÁRIOS EXTRAS (outros números, fora dos signatários) — não duplica os já enviados
    for fone_raw in (payload or {}).get("extras", []) or []:
        fone = _dig(fone_raw)
        if not fone or fone in vistos:
            continue
        vistos.add(fone)
        try:
            await enviar_pdf(cfg, fone, pdf, nome_arq, caption)
            enviados += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao enviar via final (extra) p/ %s: %s", fone, e, exc_info=True)
            falhas.append({"nome": f"Outro ({fone})", "telefone": fone, "erro": str(e) or e.__class__.__name__})
    # marca que a via final já foi distribuída ao menos uma vez (habilita o reenvio seletivo)
    if enviados:
        await db[COL].update_one({"id": doc_id, "user_id": uid},
                                 {"$set": {"via_final_enviada_em": datetime.utcnow()}})
    return {"ok": True, "enviados": enviados, "falhas": falhas, "total": len(doc.get("signatarios", [])), "via": via}
