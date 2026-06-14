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
import asyncio
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

_APP_RAW = os.environ.get("APP_PUBLIC_URL", "https://www.romatecavalieimob.com.br").rstrip("/")
# FORÇA www no domínio apex: o sem-www (romatecavalieimob.com.br) NÃO resolve p/ conexões
# NOVAS (celular do cliente abrindo o link fresco) → ERR_CONNECTION_TIMED_OUT, mesmo com o
# servidor saudável. O www.romatecavalieimob.com.br é o domínio CANÔNICO do Railway e sempre
# resolve. Garante que TODO link de assinatura abra de primeira em qualquer dispositivo.
APP_URL = _APP_RAW.replace("://romatecavalieimob.com.br", "://www.romatecavalieimob.com.br")
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
    """Gera o PDF do contrato (template Prime, SEM ICP). A geração (ReportLab) é pesada e
    SÍNCRONA — roda em thread (asyncio.to_thread) p/ NÃO travar o event loop (senão o
    servidor fica sem responder durante o envio, dando ERR_CONNECTION_TIMED_OUT)."""
    from pdf.templates.registry import gerar_pdf_contrato
    user = await db.users.find_one({"id": uid}, {"company": 1, "name": 1}) or {}
    empresa = user.get("company") or user.get("name") or "AvalieImob"
    try:
        from routes.contratos import _preload_anexos_imovel, _preload_avaliador
        await _preload_anexos_imovel(db, doc)
        doc["_avaliador"] = await _preload_avaliador(db, uid)  # CONTRATADO completo (fallback)
    except Exception:
        logger.warning("Falha ao pré-carregar anexos/avaliador (assinatura cliente).", exc_info=True)
    return await asyncio.to_thread(gerar_pdf_contrato, doc, uid or "", empresa)


def _tem_procuracao(doc: dict) -> bool:
    """Contrato gera procuração? (toggle 'Gerar procuração?' do Wizard + tem outorgantes)."""
    p = doc.get("procuracao") or {}
    return bool(p.get("gerar")) and bool(doc.get("vendedores"))


async def _gerar_procuracao_pdf(db, doc: dict, uid: str) -> bytes:
    """Gera o PDF da PROCURAÇÃO vinculada (reusa o gerador existente em routes.contratos)."""
    from routes.contratos import _generate_procuracao_pdf_bytes, _preload_avaliador
    user = await db.users.find_one({"id": uid}, {"company": 1, "name": 1}) or {}
    empresa = user.get("company") or user.get("name") or "Romatec Consultoria Total"
    doc["_avaliador"] = await _preload_avaliador(db, uid)  # qualificação completa do outorgado
    # síncrono/pesado (ReportLab) → thread p/ não travar o event loop
    return await asyncio.to_thread(_generate_procuracao_pdf_bytes, doc, uid, empresa)


async def _gerar_doc_pdf(db, doc: dict, uid: str, tipo: str) -> bytes:
    return await (_gerar_procuracao_pdf(db, doc, uid) if tipo == "procuracao"
                  else _gerar_contrato_pdf(db, doc, uid))


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


async def _carregar_minutas(db, sessao_id: str) -> list:
    """Baixa (1x) as MINUTAS (rascunho c/ marca d'água) da sessão p/ enviar junto com o link."""
    sessao = await db[COL].find_one({"id": sessao_id}) or {}
    minutas = []
    for d in sessao.get("documentos", []):
        key = d.get("pdf_key_minuta")
        if not key:
            continue
        try:
            data = await asyncio.to_thread(r2_storage.download_bytes, key)
            if data and data.startswith(b"%PDF-"):
                minutas.append({"titulo": d.get("titulo") or d.get("tipo", "Documento"),
                                "tipo": d.get("tipo"), "bytes": data})
        except Exception:
            logger.warning("Falha ao baixar minuta %s", key, exc_info=True)
    return minutas


async def _disparar_links(db, cfg, sessao_id: str, signatarios: list, enviar_minuta: bool = True) -> list:
    """Envia (ou reenvia) o link de assinatura por WhatsApp a cada signatário da lista.
    Reutiliza o MESMO token/link de cada um. Marca status 'enviado'. Quando `enviar_minuta`,
    envia também a MINUTA (rascunho c/ marca d'água) p/ leitura ANTES de assinar."""
    minutas = await _carregar_minutas(db, sessao_id) if enviar_minuta else []
    links = []
    for s in signatarios:
        url = f"{APP_URL}/assinar-cliente/{s['token']}"
        primeiro = str(s.get("nome") or "").split(" ")[0]
        msg = (f"Olá, {primeiro}! A *Romatec Consultoria Total* enviou um documento para sua "
               f"assinatura eletrônica.\n\nEnviamos abaixo a *MINUTA (rascunho)* para sua leitura. "
               f"Após ler, assine com segurança neste link:\n{url}\n\n"
               f"O link é pessoal e tem validade limitada (Lei 14.063/2020).")
        try:
            await _enviar_texto(cfg, s["telefone"], msg)
            for m in minutas:
                try:
                    await _enviar_pdf(cfg, s["telefone"], m["bytes"], f"minuta_{m['tipo']}",
                                      f"MINUTA ({m['titulo']}) — para leitura. A versão final será gerada após as assinaturas.")
                except Exception:
                    logger.warning("Falha ao enviar minuta p/ %s", s.get("telefone"), exc_info=True)
            await db[COL].update_one({"id": sessao_id, "signatarios.token": s["token"]},
                                     {"$set": {"signatarios.$.status": "enviado"}})
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao enviar WhatsApp p/ %s: %s", s.get("telefone"), e)
        links.append({"role": s.get("role"), "nome": s.get("nome"), "url": url})
    return links


# ───────────────────────── rotas autenticadas ─────────────────────────

@router.post("/contratos/{cid}/preparar")
async def preparar(cid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Gera o PDF (sem ICP) e renderiza as páginas para o corretor POSICIONAR as caixas."""
    doc = await _carregar_contrato(db, cid, uid)
    from services.pdf_preview import renderizar_paginas
    documentos = []
    pdf_c = await _gerar_contrato_pdf(db, doc, uid)
    if not pdf_c or not pdf_c.startswith(b"%PDF-"):
        raise HTTPException(status_code=500, detail="Falha ao gerar o PDF do contrato")
    documentos.append({"tipo": "contrato", "titulo": "Contrato",
                       "paginas": await asyncio.to_thread(renderizar_paginas, pdf_c)})
    if _tem_procuracao(doc):
        try:
            pdf_p = await _gerar_procuracao_pdf(db, doc, uid)
            if pdf_p and pdf_p.startswith(b"%PDF-"):
                documentos.append({"tipo": "procuracao", "titulo": "Procuração",
                                   "paginas": await asyncio.to_thread(renderizar_paginas, pdf_p)})
        except Exception:
            logger.warning("Falha ao gerar/renderizar a procuração no preparar.", exc_info=True)
    # assinatura visual do corretor salva (p/ pré-carregar no canvas) + nome
    perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}
    corretor_nome = (doc.get("corretor") or {}).get("nome") or perfil.get("nome") or "Corretor"
    assin_b64 = perfil.get("assinatura_visual_b64")
    assin_padrao = False
    if not assin_b64:
        # NUNCA desenhou ainda: gera uma assinatura cursiva a partir do NOME COMPLETO
        from services.assinatura_default import gerar_assinatura_nome_b64
        nome_full = (doc.get("corretor") or {}).get("nome") or perfil.get("nome") or ""
        assin_b64 = await asyncio.to_thread(gerar_assinatura_nome_b64, nome_full)
        assin_padrao = bool(assin_b64)
    # compat: 'paginas' = páginas do contrato (caso algum cliente antigo leia)
    return {"ok": True, "documentos": documentos, "paginas": documentos[0]["paginas"],
            "signatarios": _signatarios_sugeridos(doc),
            "corretor": {"nome": corretor_nome, "assinatura_b64": assin_b64, "assinatura_padrao": assin_padrao}}


@router.post("/contratos/{cid}/posicionar")
async def posicionar(cid: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Cria a sessão: salva âncoras (1 por role), gera tokens, sobe o PDF-base no R2
    e dispara os links por WhatsApp. payload: {ancoras:[{role,pagina,x_pt,y_pt,larg_pt,alt_pt}],
    signatarios:[{role,nome,cpf,telefone}]}."""
    from services import r2_storage
    doc = await _carregar_contrato(db, cid, uid)
    signatarios_in = payload.get("signatarios") or _signatarios_sugeridos(doc)
    # documentos: [{tipo, ancoras:[{role,pagina,...}]}]. Compat: payload antigo {ancoras} → contrato.
    docs_in = payload.get("documentos")
    if not docs_in:
        docs_in = [{"tipo": "contrato", "ancoras": payload.get("ancoras") or []}]
    if not any((di.get("ancoras") or []) for di in docs_in):
        raise HTTPException(status_code=422, detail="Posicione ao menos uma caixa de assinatura.")
    faltam = [s for s in signatarios_in if not _so_dig(s.get("telefone"))]
    if faltam:
        raise HTTPException(status_code=422,
                            detail=f"Informe o WhatsApp de: {', '.join(s.get('nome', '?') for s in faltam)}")
    # NOTA: o mesmo WhatsApp PODE repetir entre signatários (casal que compartilha o
    # número, ou teste enviando tudo p/ o próprio número) — cada signatário tem token
    # próprio, então recebe um link distinto mesmo no mesmo telefone.

    # ASSINATURA VISUAL DO CORRETOR (opção A): carimbada AGORA, antes de enviar — o cliente
    # recebe o documento JÁ com a assinatura do corretor. O ICP (validade) sela por último.
    corretor_b64 = payload.get("corretor_traco") or ""
    corretor_png = None
    if corretor_b64.startswith("data:image/png;base64,"):
        try:
            corretor_png = base64.b64decode(corretor_b64.split(",", 1)[1])
        except Exception:
            corretor_png = None
    if corretor_png:  # salva p/ reutilizar nos próximos contratos
        try:
            await db.perfil_avaliador.update_one(
                {"user_id": uid}, {"$set": {"assinatura_visual_b64": corretor_b64.split(",", 1)[1]}}, upsert=True)
        except Exception:
            pass

    sessao_id = gerar_token()[:24]
    documentos_sessao = []
    for di in docs_in:
        tipo = "procuracao" if di.get("tipo") == "procuracao" else "contrato"
        ancoras = di.get("ancoras") or []
        anc_corretor = next((a for a in ancoras if a.get("role") == "corretor"), None)
        anc_clientes = [a for a in ancoras if a.get("role") != "corretor"]
        if not anc_clientes:
            continue
        pdf_bytes = await _gerar_doc_pdf(db, doc, uid, tipo)
        if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
            raise HTTPException(status_code=500, detail=f"Falha ao gerar o PDF ({tipo})")
        # carimba a assinatura do CORRETOR na base, ANTES do envio aos clientes
        if corretor_png and anc_corretor:
            try:
                from services.assinatura_cliente_carimbo import carimbar_traco_em_pagina
                x = float(anc_corretor.get("x_pt", 0)); y = float(anc_corretor.get("y_pt", 0))
                w = float(anc_corretor.get("larg_pt", 0)); h = float(anc_corretor.get("alt_pt", 0))
                pdf_bytes = await asyncio.to_thread(
                    carimbar_traco_em_pagina, pdf_bytes, int(anc_corretor.get("pagina", 0)),
                    (x, y, x + w, y + h), corretor_png, "Corretor")
            except Exception:
                logger.warning("Falha ao carimbar assinatura do corretor.", exc_info=True)
        pdf_key = f"assinatura-cliente/{sessao_id}/{tipo}_base.pdf"
        try:
            await asyncio.to_thread(r2_storage.upload_bytes, pdf_bytes, pdf_key, "application/pdf")
        except Exception as e:  # noqa: BLE001
            logger.error("Falha ao subir PDF-base no R2: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Falha ao armazenar o documento")
        # MINUTA (rascunho com marca d'água) p/ o cliente LER antes de assinar — vai junto com o link
        pdf_key_minuta = None
        try:
            from services.marca_dagua import aplicar_marca_dagua
            minuta = await asyncio.to_thread(aplicar_marca_dagua, pdf_bytes, "MINUTA")
            if minuta and minuta.startswith(b"%PDF-"):
                pdf_key_minuta = f"assinatura-cliente/{sessao_id}/{tipo}_minuta.pdf"
                await asyncio.to_thread(r2_storage.upload_bytes, minuta, pdf_key_minuta, "application/pdf")
        except Exception:
            logger.warning("Falha ao gerar/subir minuta (%s) — segue sem ela.", tipo, exc_info=True)
        documentos_sessao.append({"tipo": tipo, "titulo": di.get("titulo") or tipo.capitalize(),
                                  "pdf_key_base": pdf_key, "pdf_key_minuta": pdf_key_minuta,
                                  "ancoras": anc_clientes, "pdf_key_final": None})

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
        "documentos": documentos_sessao,
        "signatarios": signatarios,
    }
    await db[COL].insert_one(sessao)
    # denormaliza o status no contrato p/ o card mostrar sem chamada extra
    await db.contratos.update_one(
        {"id": cid, "user_id": uid},
        {"$set": {"assinatura_cliente_status": "enviado",
                  "assinatura_cliente_sessao_id": sessao_id,
                  "assinatura_cliente_enviado_em": datetime.utcnow(),
                  "assinatura_cliente_signatarios": [
                      {"nome": s.get("nome"), "role": s.get("role"), "status": s.get("status"),
                       "assinado_em": None} for s in signatarios],
                  "assinatura_cliente_assinados": 0,
                  "assinatura_cliente_total": len(signatarios)}})

    cfg = await _zapi_cfg(db, uid)
    links = await _disparar_links(db, cfg, sessao_id, signatarios)
    return {"ok": True, "sessao_id": sessao_id, "links": links}


@router.get("/contratos/{cid}/sessao")
async def obter_sessao(cid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Status da ÚLTIMA sessão de assinatura do cliente (p/ o card). Retorna sessão=null se nunca enviou."""
    sessao = await db[COL].find_one({"contrato_id": cid, "user_id": uid}, sort=[("created_at", -1)])
    if not sessao:
        return {"ok": True, "sessao": None}
    # default do telefone = o salvo na sessão; se vazio, cai no número do CADASTRO (vendedores)
    contrato = await db.contratos.find_one({"id": cid, "user_id": uid})
    sug = {s["role"]: s.get("telefone") for s in _signatarios_sugeridos(contrato or {})}
    sigs = [{"role": s.get("role"), "nome": s.get("nome"),
             "telefone": s.get("telefone") or sug.get(s.get("role"), ""),
             "status": s.get("status"), "assinado_em": s.get("assinado_em")}
            for s in sessao.get("signatarios", [])]
    assinados = sum(1 for s in sigs if s["status"] == "assinado")
    return {"ok": True, "sessao": {
        "id": sessao["id"], "status": sessao.get("status"),
        "expira_em": sessao.get("expira_em"), "created_at": sessao.get("created_at"),
        "signatarios": sigs, "assinados": assinados, "total": len(sigs),
        "tem_procuracao": any(d.get("tipo") == "procuracao" for d in sessao.get("documentos", [])),
        "pdf_final_url": (await db.contratos.find_one({"id": cid}, {"assinatura_cliente_pdf_url": 1}) or {}).get("assinatura_cliente_pdf_url"),
    }}


@router.post("/contratos/{cid}/reenviar")
async def reenviar(cid: str, payload: dict = None, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """REENVIA os links da última sessão (sem reposicionar). Aceita telefones EDITADOS em
    payload.signatarios=[{role,telefone}] (default = os números já salvos / do cadastro).
    Só reenvia p/ quem ainda não assinou."""
    sessao = await db[COL].find_one({"contrato_id": cid, "user_id": uid}, sort=[("created_at", -1)])
    if not sessao:
        raise HTTPException(status_code=404, detail="Nenhum envio encontrado — posicione e envie a primeira vez.")
    if sessao.get("status") == "concluida":
        raise HTTPException(status_code=400, detail="Todos os signatários já assinaram — nada a reenviar.")
    # aplica telefones editados (por role), se vierem
    novos = {}
    for s in (payload or {}).get("signatarios", []) or []:
        fone = _so_dig(s.get("telefone"))
        if s.get("role") and fone:
            novos[s["role"]] = fone
    for s in sessao.get("signatarios", []):
        if novos.get(s.get("role")) and novos[s["role"]] != s.get("telefone"):
            s["telefone"] = novos[s["role"]]
            await db[COL].update_one({"id": sessao["id"], "signatarios.token": s["token"]},
                                     {"$set": {"signatarios.$.telefone": novos[s["role"]]}})
    cfg = await _zapi_cfg(db, uid)
    pendentes = [s for s in sessao.get("signatarios", []) if s.get("status") != "assinado"]
    faltam = [s for s in pendentes if not _so_dig(s.get("telefone"))]
    if faltam:
        raise HTTPException(status_code=422,
                            detail=f"Informe o WhatsApp de: {', '.join(s.get('nome', '?') for s in faltam)}")
    if not pendentes:
        raise HTTPException(status_code=400, detail="Nenhum signatário pendente.")
    links = await _disparar_links(db, cfg, sessao["id"], pendentes)
    return {"ok": True, "reenviados": len(links), "links": links}


@router.post("/contratos/{cid}/minuta/enviar")
async def enviar_minuta_avulsa(cid: str, payload: dict = None,
                               uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Envia a MINUTA/RASCUNHO (com marca d'água) do contrato (+ procuração) por WhatsApp,
    AVULSO — sem criar sessão de assinatura — só para o cliente LER antecipadamente.
    Body: {telefones:[...], marca:'MINUTA'|'RASCUNHO'}. Sem telefones → usa o cadastro."""
    doc = await _carregar_contrato(db, cid, uid)
    payload = payload or {}
    marca = (payload.get("marca") or "MINUTA").upper()
    if marca not in ("MINUTA", "RASCUNHO"):
        marca = "MINUTA"
    fones = [_so_dig(t) for t in (payload.get("telefones") or []) if _so_dig(t)]
    if not fones:
        fones = [_so_dig(s.get("telefone")) for s in _signatarios_sugeridos(doc) if _so_dig(s.get("telefone"))]
    fones = list(dict.fromkeys(fones))
    if not fones:
        raise HTTPException(status_code=422, detail="Informe ao menos um WhatsApp para enviar a minuta.")
    from services.marca_dagua import aplicar_marca_dagua
    docs = []
    pdf_c = await _gerar_contrato_pdf(db, doc, uid)
    if pdf_c and pdf_c.startswith(b"%PDF-"):
        docs.append(("contrato", "Contrato", await asyncio.to_thread(aplicar_marca_dagua, pdf_c, marca)))
    if _tem_procuracao(doc):
        try:
            pdf_p = await _gerar_procuracao_pdf(db, doc, uid)
            if pdf_p and pdf_p.startswith(b"%PDF-"):
                docs.append(("procuracao", "Procuração", await asyncio.to_thread(aplicar_marca_dagua, pdf_p, marca)))
        except Exception:
            logger.warning("Falha ao gerar procuração p/ minuta avulsa.", exc_info=True)
    if not docs:
        raise HTTPException(status_code=500, detail="Falha ao gerar a minuta.")
    cfg = await _zapi_cfg(db, uid)
    enviados = 0
    for fone in fones:
        try:
            await _enviar_texto(cfg, fone, f"Olá! Segue a *{marca} (rascunho)* do(s) documento(s) "
                                           f"para sua leitura prévia. A versão para assinatura será enviada na sequência.")
            for tipo, titulo, b in docs:
                await _enviar_pdf(cfg, fone, b, f"minuta_{tipo}", f"{marca} ({titulo}) — para leitura.")
            enviados += 1
        except Exception:
            logger.warning("Falha ao enviar minuta avulsa p/ %s", fone, exc_info=True)
    return {"ok": True, "enviados": enviados, "marca": marca, "documentos": [t for t, _, _ in docs]}


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
    # denormaliza nomes+status no contrato p/ o card mostrar a caixa de confirmação
    resumo_sig = [{"nome": s.get("nome"), "role": s.get("role"), "status": s.get("status"),
                   "assinado_em": (s.get("assinado_em").isoformat() if s.get("assinado_em") else None)}
                  for s in sessao["signatarios"]]
    assinados_n = sum(1 for s in sessao["signatarios"] if s.get("status") == "assinado")
    await db.contratos.update_one(
        {"id": sessao["contrato_id"]},
        {"$set": {"assinatura_cliente_status": "assinado_cliente" if todos else "parcial_cliente",
                  "assinatura_cliente_signatarios": resumo_sig,
                  "assinatura_cliente_assinados": assinados_n,
                  "assinatura_cliente_total": len(sessao["signatarios"])}})
    # AGRADECIMENTO ao signatário que acabou de assinar (WhatsApp)
    try:
        cfg = await _zapi_cfg(db, sessao.get("user_id"))
        fone = _so_dig(sig.get("telefone"))
        if cfg and fone:
            primeiro = str(sig.get("nome") or "").split(" ")[0]
            if todos:
                msg = (f"✅ {primeiro}, recebemos a sua assinatura — e TODOS os signatários já assinaram! "
                       f"O documento final, com todas as assinaturas, será enviado a você em instantes. "
                       f"Muito obrigado pela confiança. — *Romatec Consultoria Total*")
            else:
                msg = (f"✅ {primeiro}, recebemos a sua assinatura. Muito obrigado! "
                       f"Assim que os demais assinarem, você receberá o documento final. "
                       f"— *Romatec Consultoria Total*")
            await _enviar_texto(cfg, fone, msg)
    except Exception:  # noqa: BLE001
        logger.warning("Falha ao enviar agradecimento ao signatário.", exc_info=True)
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
            base_bytes = await asyncio.to_thread(r2_storage.download_bytes, d["pdf_key_base"])
        except Exception as e:  # noqa: BLE001
            logger.error("Falha ao baixar PDF-base: %s", e)
            continue
        tipo = d.get("tipo", "contrato")
        # carimbo (pypdf) é CPU-pesado → thread p/ não travar o event loop
        final, _h = await asyncio.to_thread(carimbar_documento, base_bytes, d.get("ancoras") or [], assinaturas)
        key_final = d["pdf_key_base"].replace("_base.pdf", "_clientes.pdf")
        url = await asyncio.to_thread(r2_storage.upload_bytes, final, key_final, "application/pdf")
        await db[COL].update_one(
            {"id": sessao["id"], "documentos.pdf_key_base": d["pdf_key_base"]},
            {"$set": {"documentos.$.pdf_key_final": key_final}})
        # marca no contrato p/ o card mostrar (sem mexer no fluxo ICP)
        campo = "procuracao_cliente_pdf_url" if tipo == "procuracao" else "assinatura_cliente_pdf_url"
        await db.contratos.update_one(
            {"id": sessao["contrato_id"]},
            {"$set": {campo: url, "assinatura_cliente_em": datetime.utcnow(),
                      "assinatura_cliente_status": "assinado_cliente"}})
        if cfg:
            nome_arq = "procuracao_assinada" if tipo == "procuracao" else "contrato_assinado"
            rotulo = "Procuração" if tipo == "procuracao" else "Contrato"
            for s in sessao["signatarios"]:
                try:
                    await _enviar_pdf(cfg, s["telefone"], final, nome_arq,
                                      f"{rotulo} assinado por todas as partes. Obrigado!")
                except Exception as e:  # noqa: BLE001
                    logger.warning("Falha ao reenviar PDF final p/ %s: %s", s.get("telefone"), e)
