# @module services.testemunha_service — orquestração da assinatura de TESTEMUNHAS.
#
# Camada ADITIVA (append-only) aplicada DEPOIS de o documento já estar assinado pelas
# partes. Reusa: Z-API (link tokenizado), carimbo do traço, R2 e o núcleo cripto
# (services.testemunha_signing.carimbar_incremental — NÃO reescreve o PDF). Compartilhado
# por Documentos Externos e Contratos via `modulo`.
import asyncio
import base64
import hashlib
import logging
from datetime import datetime, timedelta

from fastapi import HTTPException

from services import r2_storage

logger = logging.getLogger("romatec")

MODULO_COL = {"documentos-externos": "documentos_externos", "contratos": "contratos"}
_COLS = list(MODULO_COL.values())


def _col(modulo: str) -> str:
    col = MODULO_COL.get(modulo)
    if not col:
        raise HTTPException(status_code=404, detail="Módulo inválido.")
    return col


def _mask_cpf(cpf: str) -> str:
    d = "".join(filter(str.isdigit, cpf or ""))
    return f"***.{d[3:6]}.{d[6:9]}-**" if len(d) == 11 else (cpf or "")


def _app_url() -> str:
    from routes.assinatura_cliente import APP_URL
    return APP_URL


async def carregar_doc(db, modulo: str, doc_id: str, uid: str) -> dict:
    doc = await db[_col(modulo)].find_one({"id": doc_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return doc


def _pdf_key_vigente(doc: dict) -> str:
    """A testemunha SEMPRE assina a revisão vigente (a mais assinada disponível)."""
    return (doc.get("pdf_key_testemunhas") or doc.get("pdf_key_final")
            or doc.get("pdf_key_intermediario") or doc.get("pdf_key"))


async def _reconstruir_vigente(doc: dict):
    """Reconstrói a revisão vigente = revisão das PARTES + carimbo das testemunhas
    ASSINADAS (na posição) + PÁGINA de testemunhas (todas; assinadas mostram a firma,
    pendentes mostram 'aguardando'). Tudo APPEND-ONLY (idempotente, a partir da revisão
    das partes). Já no CADASTRO os dados entram no documento. Retorna (key_out, hash)."""
    base_key = doc.get("pdf_key_partes") or _pdf_key_vigente(doc)
    if not base_key:
        return None, None
    base = await asyncio.to_thread(r2_storage.download_bytes, base_key)
    from services.testemunha_signing import anexar_pagina_incremental, carimbar_incremental
    from services.testemunha_pagina import pagina_testemunhas_pdf
    from services.assinatura_cliente_carimbo import _trim_png
    testemunhas = doc.get("testemunhas") or []
    novo = base
    for w in testemunhas:
        if w.get("status") != "assinado" or not w.get("traco_b64") or not (w.get("posicoes") or []):
            continue
        try:
            wpng = _trim_png(base64.b64decode(w["traco_b64"]))
        except Exception:  # noqa: BLE001
            continue
        leg = f"Testemunha: {w.get('nome')} — CPF {_mask_cpf(w.get('cpf'))}"
        for pos in w["posicoes"]:
            x, y = float(pos.get("x_pt", 72)), float(pos.get("y_pt", 90))
            wd, ht = float(pos.get("larg_pt", 160)), float(pos.get("alt_pt", 60))
            novo = await asyncio.to_thread(carimbar_incremental, novo, int(pos.get("pagina", 0)),
                                           (x, y, x + wd, y + ht), wpng, leg)
    pagina = await asyncio.to_thread(pagina_testemunhas_pdf, doc, testemunhas)
    novo = await asyncio.to_thread(anexar_pagina_incremental, novo, pagina)
    # anexa CNH/RG de cada testemunha que enviou (vai JUNTO no documento p/ análise) —
    # PDF (CNH-e) entra com suas páginas; foto entra renderizada numa página A4.
    from services.testemunha_pagina import pagina_documentos_pdf, pagina_rotulo_anexo
    docs_itens = []
    for w in testemunhas:
        d = w.get("documento") or {}
        if not d.get("anexar_ao_pdf", True):
            continue
        if d.get("pdf_key"):
            try:
                pdf_raw = await asyncio.to_thread(r2_storage.download_bytes, d["pdf_key"])
                rot = await asyncio.to_thread(
                    pagina_rotulo_anexo, "ANEXO — DOCUMENTO DE IDENTIDADE DA TESTEMUNHA",
                    f"{w.get('nome')} — {d.get('tipo') or 'CNH'}")
                novo = await asyncio.to_thread(anexar_pagina_incremental, novo, rot)
                novo = await asyncio.to_thread(anexar_pagina_incremental, novo, pdf_raw)
            except Exception:  # noqa: BLE001
                logger.warning("Testemunha: falha ao anexar CNH (PDF).", exc_info=True)
        for face, fk in (("frente", d.get("frente_key")), ("verso", d.get("verso_key"))):
            if fk:
                try:
                    img = await asyncio.to_thread(r2_storage.download_bytes, fk)
                    docs_itens.append((f"{w.get('nome')} — {d.get('tipo') or 'CNH'} ({face})", img))
                except Exception:  # noqa: BLE001
                    pass
    if docs_itens:
        docpag = await asyncio.to_thread(pagina_documentos_pdf, docs_itens)
        novo = await asyncio.to_thread(anexar_pagina_incremental, novo, docpag)
    key_out = f"testemunhas/{doc['user_id']}/{doc['id']}_testemunhas.pdf"
    await asyncio.to_thread(r2_storage.upload_bytes, novo, key_out, "application/pdf")
    return key_out, hashlib.sha256(novo).hexdigest()


async def cadastrar(db, modulo: str, doc_id: str, uid: str, lista: list) -> list:
    from models.documento_externo import nova_testemunha
    doc = await carregar_doc(db, modulo, doc_id, uid)
    existentes = {t.get("vinculo"): t for t in (doc.get("testemunhas") or [])}
    out = []
    for item in lista:
        t = nova_testemunha(item)
        # idempotência por vínculo: atualiza a existente em vez de duplicar
        old = existentes.get(t["vinculo"])
        if old and old.get("status") != "assinado":
            t["id"] = old["id"]
            t["token"] = old.get("token") or t["token"]
        existentes[t["vinculo"]] = t
        out.append(t)
    testemunhas = list(existentes.values())
    # NÃO sobrescreve o `status` do doc-ext (a UI dele só conhece o enum próprio); a fase
    # de testemunhas é derivada do array. Marca a flag + preserva a revisão das partes.
    sets = {"testemunhas": testemunhas, "testemunhas_habilitadas": True,
            "fase_testemunhas": "coletando", "updated_at": datetime.utcnow()}
    if not doc.get("pdf_key_partes"):
        sets["pdf_key_partes"] = _pdf_key_vigente(doc)
        sets["hash_partes"] = doc.get("hash_documento")
    # já INSERE os dados das testemunhas no documento (página) p/ posicionar/enviar
    doc_at = {**doc, **sets}
    try:
        key_out, h = await _reconstruir_vigente(doc_at)
        if key_out:
            sets["pdf_key_testemunhas"] = key_out
            sets["pdf_key_final"] = key_out
            sets["hash_documento"] = h
    except Exception:  # noqa: BLE001
        logger.warning("Testemunha: reconstrução no cadastro falhou.", exc_info=True)
    await db[_col(modulo)].update_one({"id": doc_id, "user_id": uid}, {"$set": sets})
    return out


async def posicionar(db, modulo: str, doc_id: str, uid: str, posicoes: dict) -> dict:
    """Salva os retângulos (posições) por testemunha — {tid: [{pagina,x_pt,y_pt,larg_pt,alt_pt}]}."""
    doc = await carregar_doc(db, modulo, doc_id, uid)
    testemunhas = doc.get("testemunhas") or []
    for t in testemunhas:
        if t["id"] in (posicoes or {}):
            t["posicoes"] = posicoes[t["id"]] or []
    await db[_col(modulo)].update_one({"id": doc_id, "user_id": uid},
                                      {"$set": {"testemunhas": testemunhas, "updated_at": datetime.utcnow()}})
    return {"ok": True}


async def _aplicar_e_reconstruir(db, modulo, doc_id, uid, doc, testemunhas, extra=None):
    """$set das testemunhas + reconstrói a revisão vigente (página atualizada)."""
    sets = {"testemunhas": testemunhas, "updated_at": datetime.utcnow(), **(extra or {})}
    if testemunhas:
        try:
            key_out, h = await _reconstruir_vigente({**doc, **sets})
            if key_out:
                sets["pdf_key_testemunhas"] = key_out
                sets["pdf_key_final"] = key_out
                sets["hash_documento"] = h
        except Exception:  # noqa: BLE001
            logger.warning("Testemunha: reconstrução falhou.", exc_info=True)
    else:  # sem testemunhas → volta à revisão das PARTES
        sets["pdf_key_testemunhas"] = None
        sets["pdf_key_final"] = doc.get("pdf_key_partes")
        sets["fase_testemunhas"] = None
    await db[_col(modulo)].update_one({"id": doc_id, "user_id": uid}, {"$set": sets})


async def editar_testemunha(db, modulo: str, doc_id: str, uid: str, tid: str, patch: dict) -> dict:
    from models.documento_externo import _so_dig
    doc = await carregar_doc(db, modulo, doc_id, uid)
    testemunhas = doc.get("testemunhas") or []
    alvo = next((t for t in testemunhas if t.get("id") == tid), None)
    if not alvo:
        raise HTTPException(status_code=404, detail="Testemunha não encontrada.")
    if alvo.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Testemunha já assinou — não pode ser alterada.")
    for campo in ("nome", "email", "vinculo", "parte_vinculada_id", "parte_vinculada_nome"):
        if patch.get(campo) is not None:
            alvo[campo] = patch[campo]
    if patch.get("cpf") is not None:
        alvo["cpf"] = _so_dig(patch["cpf"])
    if patch.get("telefone") is not None:
        alvo["telefone"] = _so_dig(patch["telefone"] or patch.get("whatsapp"))
    await _aplicar_e_reconstruir(db, modulo, doc_id, uid, doc, testemunhas)
    return {"ok": True}


async def _salvar_doc_na_testemunha(uid, doc_id, t, frente_b64, verso_b64, pdf_b64, tipo):
    """Sobe a CNH/RG (foto frente/verso OU PDF) no R2 e devolve o dict `documento`."""
    atual = t.get("documento") or {}
    meta = {"tipo": (tipo or "CNH"), "enviado_em": datetime.utcnow(), "anexar_ao_pdf": True,
            "frente_key": atual.get("frente_key"), "verso_key": atual.get("verso_key"),
            "pdf_key": atual.get("pdf_key")}

    async def _up_img(b64, face):
        raw = base64.b64decode(str(b64).split(",")[-1])
        if len(raw) > 12 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Imagem muito grande (máx 12MB).")
        key = f"testemunhas/{uid}/{doc_id}/{t['id']}_{face}.jpg"
        await asyncio.to_thread(r2_storage.upload_bytes, raw, key, "image/jpeg")
        return key

    if pdf_b64:
        raw = base64.b64decode(str(pdf_b64).split(",")[-1])
        if raw[:4] != b"%PDF":
            raise HTTPException(status_code=422, detail="Arquivo não é um PDF válido.")
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="PDF muito grande (máx 20MB).")
        key = f"testemunhas/{uid}/{doc_id}/{t['id']}_cnh.pdf"
        await asyncio.to_thread(r2_storage.upload_bytes, raw, key, "application/pdf")
        meta["pdf_key"] = key
    if frente_b64:
        meta["frente_key"] = await _up_img(frente_b64, "frente")
    if verso_b64:
        meta["verso_key"] = await _up_img(verso_b64, "verso")
    if not (meta["pdf_key"] or meta["frente_key"] or meta["verso_key"]):
        raise HTTPException(status_code=422, detail="Envie a foto (frente) ou o PDF do documento.")
    return meta


async def salvar_documento_operador(db, modulo: str, doc_id: str, uid: str, tid: str,
                                    frente_b64: str = "", verso_b64: str = "",
                                    pdf_b64: str = "", tipo: str = "CNH") -> dict:
    """O OPERADOR anexa a CNH/RG (foto ou PDF) de uma testemunha. Sobe no R2, vincula e
    reconstrói a revisão (o documento já vai anexado nas páginas seguintes)."""
    doc = await carregar_doc(db, modulo, doc_id, uid)
    testemunhas = doc.get("testemunhas") or []
    t = next((x for x in testemunhas if x.get("id") == tid), None)
    if not t:
        raise HTTPException(status_code=404, detail="Testemunha não encontrada.")
    t["documento"] = await _salvar_doc_na_testemunha(uid, doc_id, t, frente_b64, verso_b64, pdf_b64, tipo)
    await _aplicar_e_reconstruir(db, modulo, doc_id, uid, doc, testemunhas)
    return {"ok": True, "pdf": bool(t["documento"].get("pdf_key")),
            "frente": bool(t["documento"].get("frente_key")), "verso": bool(t["documento"].get("verso_key"))}


async def excluir_testemunha(db, modulo: str, doc_id: str, uid: str, tid: str) -> dict:
    doc = await carregar_doc(db, modulo, doc_id, uid)
    testemunhas = doc.get("testemunhas") or []
    alvo = next((t for t in testemunhas if t.get("id") == tid), None)
    if not alvo:
        raise HTTPException(status_code=404, detail="Testemunha não encontrada.")
    if alvo.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Testemunha já assinou — não pode ser excluída.")
    restantes = [t for t in testemunhas if t.get("id") != tid]
    await _aplicar_e_reconstruir(db, modulo, doc_id, uid, doc, restantes)
    return {"ok": True, "restantes": len(restantes)}


async def paginas_vigentes(db, modulo: str, doc_id: str, uid: str) -> dict:
    """Páginas renderizadas do PDF vigente + as testemunhas cadastradas (p/ posicionar)."""
    doc = await carregar_doc(db, modulo, doc_id, uid)
    from services.pdf_preview import renderizar_paginas
    key = _pdf_key_vigente(doc)
    paginas = []
    if key:
        raw = await asyncio.to_thread(r2_storage.download_bytes, key)
        paginas = await asyncio.to_thread(renderizar_paginas, raw)
    return {"paginas": paginas,
            "testemunhas": [{"id": t["id"], "nome": t["nome"], "vinculo": t.get("vinculo"),
                             "parte_vinculada_nome": t.get("parte_vinculada_nome"),
                             "posicoes": t.get("posicoes") or []} for t in (doc.get("testemunhas") or [])]}


def _link(token: str) -> str:
    return f"{_app_url()}/assinar/testemunha/{token}"


async def enviar(db, modulo: str, doc_id: str, uid: str, tid: str = None,
                 telefone_teste: str = None) -> dict:
    """Envia o link da testemunha por WhatsApp. `telefone_teste` (modo teste): envia
    TODOS os links para esse número (não para o da testemunha) — p/ conferir antes de
    mandar ao cliente real."""
    from services.documento_externo_service import zapi_cfg, enviar_texto
    doc = await carregar_doc(db, modulo, doc_id, uid)
    cfg = await zapi_cfg(db, uid)
    titulo = doc.get("titulo") or doc.get("numero_contrato") or "documento"
    teste = "".join(filter(str.isdigit, str(telefone_teste or "")))
    alvos = [t for t in (doc.get("testemunhas") or [])
             if (tid is None and t.get("status") in ("pendente", "enviado")) or t.get("id") == tid]
    if not alvos:
        raise HTTPException(status_code=422, detail="Nenhuma testemunha pendente para enviar.")
    enviadas, falhas = 0, []
    for t in alvos:
        destino = teste or t.get("telefone")
        if not destino:
            falhas.append({"id": t["id"], "erro": "sem WhatsApp"})
            continue
        msg = (f"Olá, {t['nome']}. Você foi indicado(a) como *testemunha*"
               f"{(' (' + t['vinculo'] + ')') if t.get('vinculo') else ''} no documento "
               f"\"{titulo}\" da Romatec Consultoria Total.\n\n"
               f"Leia o documento e assine pelo link abaixo (válido por 7 dias):\n{_link(t['token'])}\n\n"
               f"A assinatura é autenticada por este número de WhatsApp.")
        try:
            r = await enviar_texto(cfg, destino, msg)
            t["status"] = "enviado"
            t["enviado_em"] = datetime.utcnow()
            t["zaap_message_id"] = (r or {}).get("messageId") or (r or {}).get("id")
            enviadas += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("Testemunha: envio Z-API falhou: %s", e)
            falhas.append({"id": t["id"], "erro": str(e)})
    await db[_col(modulo)].update_one({"id": doc_id, "user_id": uid},
                                      {"$set": {"testemunhas": doc["testemunhas"], "updated_at": datetime.utcnow()}})
    return {"enviadas": enviadas, "falhas": falhas}


async def localizar_por_token(db, token: str):
    """(modulo, doc, testemunha) pelo token — busca nas coleções suportadas."""
    for modulo, col in MODULO_COL.items():
        doc = await db[col].find_one({"testemunhas.token": token})
        if doc:
            t = next((x for x in doc.get("testemunhas") or [] if x.get("token") == token), None)
            if t:
                return modulo, doc, t
    raise HTTPException(status_code=404, detail="Link inválido.")


async def assinar(db, token: str, traco_b64: str, ip: str = "", ua: str = "") -> dict:
    modulo, doc, t = await localizar_por_token(db, token)
    if t.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Esta testemunha já assinou.")
    if t.get("expira_em") and _parse(t["expira_em"]) and _parse(t["expira_em"]) < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Link expirado.")
    if not (traco_b64 or "").startswith("data:image/png;base64,"):
        raise HTTPException(status_code=422, detail="Assinatura inválida.")
    agora = datetime.utcnow()
    # marca ESTA testemunha (t é referência ao item em doc['testemunhas'])
    t["status"] = "assinado"
    t["assinado_em"] = agora
    t["ip"] = (ip or "")[:64]
    t["user_agent"] = (ua or "")[:255]
    t["traco_b64"] = traco_b64.split(",", 1)[1]
    t["hash_validacao"] = hashlib.sha256(f"{token}{t.get('cpf')}{agora.isoformat()}".encode()).hexdigest()

    # reconstrói a revisão vigente (carimbo nas posições + página) a partir da revisão
    # das PARTES — APPEND-ONLY, preserva as assinaturas das partes (idempotente)
    if not (doc.get("pdf_key_partes") or _pdf_key_vigente(doc)):
        raise HTTPException(status_code=422, detail="Documento sem PDF para assinar.")
    col = MODULO_COL[modulo]
    testemunhas = doc.get("testemunhas") or []
    key_out, hash_doc = await _reconstruir_vigente(doc)

    exigidas = [x for x in testemunhas if not x.get("opcional")]
    todas = exigidas and all(x.get("status") == "assinado" for x in exigidas)
    # a revisão com a(s) testemunha(s) + a PÁGINA de qualificação vira a vigente/final
    # já a CADA assinatura (não só no fim) — assim "Ver final" mostra a página na hora.
    sets = {"testemunhas": testemunhas, "pdf_key_testemunhas": key_out, "pdf_key_final": key_out,
            "updated_at": agora, "hash_documento": hash_doc,
            "fase_testemunhas": ("concluido" if todas else "coletando")}
    # NÃO mexe no `status` do doc-ext (já é 'finalizado' das partes)
    await db[col].update_one({"id": doc["id"]}, {"$set": sets})
    return {"ok": True, "documento_finalizado": bool(todas)}


async def salvar_documento(db, token: str, frente_b64: str = "", verso_b64: str = "",
                           pdf_b64: str = "", tipo: str = "CNH") -> dict:
    """A testemunha envia a CNH/RG (foto frente/verso OU PDF) — sobe no R2 e vincula à
    testemunha. Anexada ao documento na próxima reconstrução (ao assinar)."""
    modulo, doc, t = await localizar_por_token(db, token)
    col = MODULO_COL[modulo]
    t["documento"] = await _salvar_doc_na_testemunha(doc["user_id"], doc["id"], t,
                                                     frente_b64, verso_b64, pdf_b64, tipo)
    testemunhas = doc.get("testemunhas") or []
    for i, x in enumerate(testemunhas):
        if x.get("id") == t["id"]:
            testemunhas[i] = t
    await db[col].update_one({"id": doc["id"]},
                             {"$set": {"testemunhas": testemunhas, "updated_at": datetime.utcnow()}})
    return {"ok": True, "pdf": bool(t["documento"].get("pdf_key")),
            "frente": bool(t["documento"].get("frente_key"))}


def _parse(v):
    try:
        return v if isinstance(v, datetime) else datetime.fromisoformat(str(v))
    except Exception:  # noqa: BLE001
        return None


async def marcar_visualizado(db, token: str, ip: str = "", ua: str = ""):
    modulo, doc, t = await localizar_por_token(db, token)
    if t.get("status") == "enviado":
        t["status"] = "visualizado" if False else t["status"]  # mantém 'enviado' como status oficial
    if not t.get("visualizado_em"):
        t["visualizado_em"] = datetime.utcnow()
        t["ip"] = (ip or "")[:64]
        t["user_agent"] = (ua or "")[:255]
        await db[MODULO_COL[modulo]].update_one({"id": doc["id"]}, {"$set": {"testemunhas": doc["testemunhas"]}})
    return modulo, doc, t
