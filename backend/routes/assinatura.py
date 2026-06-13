# @module routes.assinatura — Endpoints de assinatura digital com validade juridica
# Suporta D4Sign (assinatura eletrônica via e-mail) E ICP-Brasil A1/PAdES (cert local).
# Lei 14.063/2020 + MP 2.200-2/2001
import os
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from services.auth_service import get_current_user_id

logger = logging.getLogger("romatec")

router = APIRouter(tags=["assinatura"], prefix="/assinatura")

# Mapeamento tipo -> colecao MongoDB e funcao de geracao de PDF
_TIPO_COLECAO = {
    "ptam": "ptam_documents",
    "tvi": "vistorias",
    "garantia": "garantias",
    "recibo": "recibos",
    "contrato": "contratos",
}


# ── Request / Response models ────────────────────────────────────────────────

class SignatarioInput(BaseModel):
    email: str
    nome: str
    tipo: str = "1"   # 1=assinar, 2=aprovar, 3=reconhecer, 4=testemunha


class IniciarAssinaturaRequest(BaseModel):
    signatarios: List[SignatarioInput]
    mensagem: Optional[str] = ""


class WebhookD4SignBody(BaseModel):
    uuid: Optional[str] = None
    type: Optional[str] = None


# ── Helper: verificar D4Sign configurado ─────────────────────────────────────

def _assert_d4sign():
    if not os.environ.get("D4SIGN_TOKEN", ""):
        raise HTTPException(
            status_code=503,
            detail="Assinatura digital nao configurada. Configure D4SIGN_TOKEN no painel de administracao.",
        )


# ── Helper: buscar documento em qualquer colecao ─────────────────────────────

async def _get_doc(db, tipo: str, doc_id: str, user_id: str) -> dict:
    colecao = _TIPO_COLECAO.get(tipo)
    if not colecao:
        raise HTTPException(status_code=400, detail=f"Tipo invalido: {tipo}")
    doc = await db[colecao].find_one({"id": doc_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"{tipo.upper()} nao encontrado")
    return doc


async def _get_doc_by_uuid(db, document_uuid: str):
    """Busca documento em todas as colecoes pelo d4sign_document_uuid (para webhook)."""
    for colecao in _TIPO_COLECAO.values():
        doc = await db[colecao].find_one({"d4sign_document_uuid": document_uuid})
        if doc:
            return colecao, doc
    return None, None


def _validate_d4sign_webhook(request: Request):
    expected_token = os.environ.get("D4SIGN_WEBHOOK_TOKEN", "").strip()
    if not expected_token:
        return

    provided_token = (
        request.query_params.get("token")
        or request.headers.get("X-D4Sign-Webhook-Token")
        or request.headers.get("X-Webhook-Token")
    )
    if provided_token != expected_token:
        raise HTTPException(status_code=403, detail="Webhook token inválido")


async def _resolve_ptam_assets(db, doc: dict) -> None:
    """Resolve IDs de imagens -> bytes para o gerador v2 (fotos do imovel,
    fotos das amostras e documentos digitalizados). Espelha o endpoint /pdf-v2.
    Reamostra as imagens (downscale) para reduzir memoria na assinatura."""
    import base64
    from services.img_util import downscale_image
    fotos_norm = []
    for i, foto in enumerate(doc.get("fotos_imovel") or [], 1):
        if isinstance(foto, dict):
            if not foto.get("legenda"):
                foto["legenda"] = foto.get("description") or foto.get("caption") or f"Foto {i}"
            if isinstance(foto.get("_image_bytes"), (bytes, bytearray)):
                foto["_image_bytes"] = downscale_image(bytes(foto["_image_bytes"]))
            else:
                # Foto-objeto {image_id, legenda}: resolve os bytes em db.images.
                _fid = str(foto.get("image_id") or foto.get("url") or "").replace('/api/upload/image/', '').split('/')[-1]
                if len(_fid) > 30 and '-' in _fid:
                    _img = await db.images.find_one({"id": _fid})
                    if _img and _img.get("data_b64"):
                        foto["_image_bytes"] = downscale_image(base64.b64decode(_img["data_b64"]))
                        if not foto.get("gps") and _img.get("meta_gps"):
                            foto["gps"] = _img["meta_gps"]
                        if not foto.get("data_hora") and _img.get("meta_data_hora"):
                            foto["data_hora"] = _img["meta_data_hora"]
            fotos_norm.append(foto)
            continue
        image_id = str(foto).replace('/api/upload/image/', '').split('/')[-1]
        entry = {"legenda": f"Foto {i}", "description": f"Foto {i}"}
        if len(image_id) > 30 and '-' in image_id:
            img = await db.images.find_one({"id": image_id})
            if img and img.get("data_b64"):
                entry["_image_bytes"] = downscale_image(base64.b64decode(img["data_b64"]))
                if img.get("filename"):
                    entry["legenda"] = img["filename"]
                if img.get("meta_gps"):
                    entry["gps"] = img["meta_gps"]
                if img.get("meta_data_hora"):
                    entry["data_hora"] = img["meta_data_hora"]
        fotos_norm.append(entry)
    doc["fotos_imovel"] = fotos_norm

    for s in (doc.get("market_samples") or []):
        fu = s.get("foto") or s.get("foto_url") or ""
        sid = str(fu).replace('/api/upload/image/', '').split('/')[-1]
        if len(sid) > 30 and '-' in sid:
            simg = await db.images.find_one({"id": sid})
            if simg and simg.get("data_b64"):
                s["_image_bytes"] = downscale_image(base64.b64decode(simg["data_b64"]))
        # Planta baixa (mapa SIGEF) da amostra — Anexo II mostra foto + planta lado a lado.
        if not s.get("_planta_baixa_bytes"):
            pb = s.get("planta_baixa") or s.get("planta_baixa_url") or ""
            pid_pb = str(pb).replace('/api/upload/image/', '').split('/')[-1]
            if len(pid_pb) > 30 and '-' in pid_pb:
                pimg = await db.images.find_one({"id": pid_pb})
                if pimg and pimg.get("data_b64"):
                    s["_planta_baixa_bytes"] = downscale_image(base64.b64decode(pimg["data_b64"]))

    docs_res = []
    for kd, di in enumerate(doc.get("fotos_documentos") or [], 1):
        du = (di.get("url") or di.get("doc_id") or di.get("image_id", "")) if isinstance(di, dict) else str(di)
        dn = (di.get("name") or di.get("tipo")) if isinstance(di, dict) else None
        did = str(du).replace('/api/upload/image/', '').split('/')[-1]
        if len(did) > 30 and '-' in did:
            dimg = await db.images.find_one({"id": did})
            if dimg and dimg.get("data_b64"):
                _ct = dimg.get("content_type", "image/jpeg")
                _raw = base64.b64decode(dimg["data_b64"])
                if str(_ct).startswith("image/"):
                    _raw = downscale_image(_raw, max_side=1800)
                docs_res.append({
                    "name": dn or dimg.get("filename") or f"Documento {kd}",
                    "_doc_bytes": _raw,
                    "content_type": _ct,
                })
    doc["documentos_resolvidos"] = docs_res

    # COMPLETUDE: o assinado deve ser idêntico ao /pdf. Anexa documentos rurais
    # (SIGEF, Memorial, CCIR, ITR, CAR), tabela INCRA e consultas CND vinculadas.
    try:
        from routes.ptam import _merge_docs_rurais, _attach_incra
        await _merge_docs_rurais(db, doc, doc["documentos_resolvidos"])
        await _attach_incra(db, doc)
    except Exception:
        pass
    try:
        cnd = []
        raw = await db.cnd_consultas.find({"ptam_id": doc.get("id")}).to_list(20)
        for c in raw:
            cs = await db.cnd_certidoes.find({"consulta_id": c.get("id", "")}).to_list(10)
            cnd.append({"consulta": c, "certidoes": cs})
        doc["cnd_consultas"] = cnd
    except Exception:
        pass


async def _gerar_pdf(tipo: str, doc: dict, db=None, perfil: dict | None = None) -> bytes:
    """Gera PDF do documento conforme tipo. PTAM usa o layout v2 (aprovado)."""
    if tipo == "ptam":
        from services.ptam_pdf_v2 import generate_ptam_pdf_v2
        if db is not None:
            await _resolve_ptam_assets(db, doc)
        return generate_ptam_pdf_v2(doc, perfil)
    elif tipo == "tvi":
        try:
            from pdf.tvi_pdf import generate_tvi_pdf
            return generate_tvi_pdf(doc)
        except ImportError:
            from services.ptam_pdf_v2 import generate_ptam_pdf_v2
            return generate_ptam_pdf_v2(doc, perfil)
    elif tipo == "garantia":
        try:
            from pdf.garantia_pdf import generate_garantia_pdf
            return generate_garantia_pdf(doc)
        except ImportError:
            from services.ptam_pdf_v2 import generate_ptam_pdf_v2
            return generate_ptam_pdf_v2(doc, perfil)
    elif tipo == "recibo":
        from pdf.recibo_pdf import gerar_recibo_pdf
        u = {}
        logo = None
        if db is not None:
            u = await db.users.find_one({"id": doc.get("user_id")}) or {}
            logo_id = doc.get("emitente_logo_id") or u.get("company_logo")
            if logo_id:
                limg = await db.images.find_one({"id": logo_id})
                if limg and limg.get("data_b64"):
                    import base64 as _b64
                    logo = _b64.b64decode(limg["data_b64"])
        pdf_bytes = gerar_recibo_pdf(recibo=doc, user=u, perfil=perfil or {}, logo_bytes=logo)
        # Anexa os documentos do recibo ANTES de assinar — assim o PDF assinado
        # (e as páginas do posicionador) já incluem os anexos.
        if db is not None:
            from services.recibo_anexos import anexar_anexos_ao_pdf
            pdf_bytes = await anexar_anexos_ao_pdf(db, doc, pdf_bytes)
        return pdf_bytes
    elif tipo == "contrato":
        # Usa o MESMO renderer do card (registry → template_pdf ou Prime II por
        # padrão), para o documento ASSINADO sair no layout Prime que o usuário vê.
        # Antes chamava _generate_contrato_pdf_bytes (tradicional) direto, então a
        # tela de Assinar/ICP saía "sem formatação". O tradicional segue como
        # rede de segurança (fallback dentro de gerar_pdf_contrato).
        from pdf.templates.registry import gerar_pdf_contrato
        uid = doc.get("user_id")
        empresa = "AvalieImob"
        if db is not None and uid:
            u = await db.users.find_one({"id": uid}, {"company": 1, "name": 1}) or {}
            empresa = u.get("company") or u.get("name") or "AvalieImob"
        if db is not None:
            try:
                from routes.contratos import _preload_anexos_imovel
                await _preload_anexos_imovel(db, doc)
            except Exception:
                logger.warning("Falha ao pré-carregar anexos do imóvel (assinatura).", exc_info=True)
        return gerar_pdf_contrato(doc=doc, uid=uid or "", empresa=empresa)
    raise HTTPException(status_code=400, detail=f"Geracao de PDF nao suportada para tipo: {tipo}")


async def _render_ptam_layout(db, doc: dict, uid: str, layout: str) -> bytes:
    """Gera bytes do PDF do PTAM no layout pedido.
    'v2' = completo/aprovado (espelha /pdf-v2); 'v1' = classico (espelha /pdf)."""
    import base64 as _b64
    user = await db.users.find_one({"id": uid}) or {}
    perfil = await db.perfil_avaliador.find_one({"user_id": uid})
    if perfil:
        perfil.pop("_id", None)

    if False:  # layout v1 descontinuado — modelo canônico único é o v2
        from pdf.ptam_pdf import generate_ptam_pdf
        # Logo da empresa
        company_logo_id = user.get("company_logo")
        if company_logo_id:
            logo_doc = await db.images.find_one({"id": company_logo_id, "user_id": uid})
            if logo_doc and logo_doc.get("data_b64"):
                user["_company_logo_bytes"] = _b64.b64decode(logo_doc["data_b64"])
        # Fotos do imovel
        fotos_imovel = doc.get("fotos_imovel") or []
        for i, foto in enumerate(fotos_imovel):
            if isinstance(foto, str):
                url = foto
            elif isinstance(foto, dict):
                url = foto.get("url") or foto.get("image_id", "")
            else:
                continue
            image_id = str(url).replace('/api/upload/image/', '').split('/')[-1]
            if len(image_id) > 30 and '-' in image_id:
                img_doc = await db.images.find_one({"id": image_id})
                if img_doc and img_doc.get("data_b64"):
                    fotos_imovel[i] = {
                        "image_id": image_id,
                        "url": url,
                        "_image_bytes": _b64.b64decode(img_doc["data_b64"]),
                        "description": (foto.get("description") or foto.get("descricao") or f"Foto {i+1}") if isinstance(foto, dict) else f"Foto {i+1}",
                    }
        doc["fotos_imovel"] = fotos_imovel
        # Documentos digitalizados
        docs_processados = []
        for i, doc_item in enumerate(doc.get("fotos_documentos") or []):
            if isinstance(doc_item, str):
                url = doc_item
            elif isinstance(doc_item, dict):
                url = doc_item.get("url") or doc_item.get("doc_id") or doc_item.get("image_id", "")
            else:
                continue
            doc_id = str(url).replace('/api/upload/image/', '').split('/')[-1]
            if len(doc_id) > 30 and '-' in doc_id:
                doc_db = await db.images.find_one({"id": doc_id})
                if doc_db and doc_db.get("data_b64"):
                    docs_processados.append({
                        "doc_id": doc_id,
                        "url": url,
                        "_doc_bytes": _b64.b64decode(doc_db["data_b64"]),
                        "name": doc_db.get("filename") or (doc_item.get("name") if isinstance(doc_item, dict) else None) or f"Documento {i+1}",
                        "content_type": doc_db.get("content_type", "application/pdf"),
                    })
                else:
                    docs_processados.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
            else:
                docs_processados.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
        doc["fotos_documentos"] = docs_processados
        # Amostras de mercado
        market_samples = doc.get("market_samples") or []
        for j, sample in enumerate(market_samples):
            foto_url = sample.get("foto") or sample.get("foto_url") or ""
            sid = str(foto_url).replace('/api/upload/image/', '').split('/')[-1]
            if len(sid) > 30 and '-' in sid:
                simg = await db.images.find_one({"id": sid})
                if simg and simg.get("data_b64"):
                    market_samples[j] = {**sample, "_image_bytes": _b64.b64decode(simg["data_b64"])}
        doc["market_samples"] = market_samples
        # Consultas CND vinculadas
        cnd_consultas = []
        raw_consultas = await db.cnd_consultas.find({"ptam_id": doc.get("id"), "user_id": uid}).to_list(20)
        for c in raw_consultas:
            certs = await db.cnd_certidoes.find({"consulta_id": c.get("id", "")}).to_list(10)
            cnd_consultas.append({"consulta": c, "certidoes": certs})
        return generate_ptam_pdf(doc, user, cnd_consultas=cnd_consultas, perfil_avaliador=perfil)

    # Default: v2 (completo / aprovado)
    from services.ptam_pdf_v2 import generate_ptam_pdf_v2
    await _resolve_ptam_assets(db, doc)
    return generate_ptam_pdf_v2(doc, perfil)


# ── POST /assinatura/{tipo}/{id}/iniciar ─────────────────────────────────────

@router.post("/{tipo}/{id}/iniciar")
async def iniciar_assinatura(
    tipo: str,
    id: str,
    body: IniciarAssinaturaRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    _assert_d4sign()
    from services import d4sign_service as d4

    doc = await _get_doc(db, tipo, id, uid)

    # Gerar PDF (layout v2 aprovado)
    perfil_pdf = await db.perfil_avaliador.find_one({"user_id": uid})
    if perfil_pdf:
        perfil_pdf.pop("_id", None)
    try:
        pdf_bytes = await _gerar_pdf(tipo, doc, db=db, perfil=perfil_pdf)
    except Exception as e:
        logger.error("Erro ao gerar PDF para assinatura: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {e}")

    numero = doc.get("numero_ptam") or doc.get("numero_tvi") or doc.get("numero") or id
    nome_arquivo = f"{tipo.upper()}_{numero}.pdf"

    # Upload para D4Sign
    try:
        doc_uuid = await d4.upload_documento(pdf_bytes, nome_arquivo)
    except Exception as e:
        logger.error("Erro no upload D4Sign: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro no upload D4Sign: {e}")

    # Adicionar signatarios
    signer_uuids = []
    signatarios_salvos = []
    for sig in body.signatarios:
        try:
            signer_uuid = await d4.adicionar_signatario(doc_uuid, sig.email, sig.nome, sig.tipo)
            signer_uuids.append(signer_uuid)
            signatarios_salvos.append({
                "email": sig.email,
                "nome": sig.nome,
                "tipo": sig.tipo,
                "signer_uuid": signer_uuid,
                "assinado": False,
                "assinado_em": None,
            })
        except Exception as e:
            logger.error("Erro ao adicionar signatario %s: %s", sig.email, e)
            raise HTTPException(status_code=502, detail=f"Erro ao adicionar signatario {sig.email}: {e}")

    # Enviar para assinatura
    try:
        await d4.enviar_para_assinatura(doc_uuid, body.mensagem or "")
    except Exception as e:
        logger.error("Erro ao enviar para assinatura D4Sign: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro ao enviar para assinatura: {e}")

    # Atualizar documento no MongoDB
    now = datetime.utcnow()
    colecao = _TIPO_COLECAO[tipo]
    await db[colecao].update_one(
        {"id": id},
        {"$set": {
            "d4sign_document_uuid": doc_uuid,
            "d4sign_status": "aguardando",
            "d4sign_enviado_em": now,
            "d4sign_signatarios": signatarios_salvos,
            "updated_at": now,
        }},
    )

    return {
        "document_uuid": doc_uuid,
        "status": "aguardando",
        "signatarios": signatarios_salvos,
    }


# ── GET /assinatura/{tipo}/{id}/status ───────────────────────────────────────

@router.get("/{tipo}/{id}/status")
async def status_assinatura(
    tipo: str,
    id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    _assert_d4sign()
    from services import d4sign_service as d4

    doc = await _get_doc(db, tipo, id, uid)
    doc_uuid = doc.get("d4sign_document_uuid")
    if not doc_uuid:
        raise HTTPException(status_code=404, detail="Assinatura nao iniciada para este documento")

    try:
        info = await d4.status_documento(doc_uuid)
    except Exception as e:
        logger.error("Erro ao consultar status D4Sign: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro ao consultar D4Sign: {e}")

    colecao = _TIPO_COLECAO[tipo]
    update_fields = {
        "d4sign_status": info["status"],
        "d4sign_signatarios": info["signatarios"],
        "updated_at": datetime.utcnow(),
    }

    # Se passou para assinado, baixar PDF assinado
    if info["status"] == "assinado" and doc.get("d4sign_status") != "assinado":
        try:
            pdf_bytes = await d4.download_documento_assinado(doc_uuid)
            # Salvar via upload interno (gridfs-like via colecao uploads)
            import uuid as _uuid
            file_id = str(_uuid.uuid4())
            await db["assinaturas_pdf"].insert_one({
                "id": file_id,
                "doc_tipo": tipo,
                "doc_id": id,
                "d4sign_document_uuid": doc_uuid,
                "content": pdf_bytes,
                "created_at": datetime.utcnow(),
            })
            update_fields["d4sign_pdf_assinado_url"] = f"/api/assinatura/{tipo}/{id}/download"
            update_fields["d4sign_assinado_em"] = datetime.utcnow()
            logger.info("PDF assinado salvo para %s/%s", tipo, id)
        except Exception as e:
            logger.error("Erro ao baixar PDF assinado: %s", e)

    await db[colecao].update_one({"id": id}, {"$set": update_fields})

    return {
        "status": info["status"],
        "signatarios": info["signatarios"],
        "d4sign_document_uuid": doc_uuid,
        "d4sign_pdf_assinado_url": update_fields.get("d4sign_pdf_assinado_url") or doc.get("d4sign_pdf_assinado_url"),
    }


# ── GET /assinatura/{tipo}/{id}/download ─────────────────────────────────────

@router.get("/{tipo}/{id}/download")
async def download_assinado(
    tipo: str,
    id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    _assert_d4sign()

    doc = await _get_doc(db, tipo, id, uid)
    if doc.get("d4sign_status") != "assinado":
        raise HTTPException(status_code=404, detail="Documento ainda nao assinado")

    # Buscar PDF salvo
    assinatura = await db["assinaturas_pdf"].find_one({"doc_tipo": tipo, "doc_id": id})
    if not assinatura or not assinatura.get("content"):
        # Tentar baixar novamente da D4Sign
        from services import d4sign_service as d4
        doc_uuid = doc.get("d4sign_document_uuid")
        if not doc_uuid:
            raise HTTPException(status_code=404, detail="PDF assinado nao disponivel")
        try:
            pdf_bytes = await d4.download_documento_assinado(doc_uuid)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erro ao baixar PDF: {e}")
    else:
        pdf_bytes = assinatura["content"]

    numero = doc.get("numero_ptam") or doc.get("numero_tvi") or doc.get("numero") or id
    filename = f"{tipo.upper()}_{numero}_ASSINADO.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── DELETE /assinatura/{tipo}/{id}/cancelar ──────────────────────────────────

@router.delete("/{tipo}/{id}/cancelar")
async def cancelar_assinatura(
    tipo: str,
    id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    _assert_d4sign()
    from services import d4sign_service as d4

    doc = await _get_doc(db, tipo, id, uid)
    doc_uuid = doc.get("d4sign_document_uuid")
    if not doc_uuid:
        raise HTTPException(status_code=404, detail="Assinatura nao iniciada")

    try:
        await d4.cancelar_documento(doc_uuid)
    except Exception as e:
        logger.error("Erro ao cancelar documento D4Sign: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro ao cancelar: {e}")

    colecao = _TIPO_COLECAO[tipo]
    await db[colecao].update_one(
        {"id": id},
        {"$set": {"d4sign_status": "cancelado", "updated_at": datetime.utcnow()}},
    )

    return {"status": "cancelado"}


# ── POST /assinatura/webhook (SEM autenticacao) ──────────────────────────────

@router.post("/webhook")
async def webhook_d4sign(request: Request, db=Depends(get_db)):
    """Recebe notificacoes D4Sign e atualiza status. Responde < 2s."""
    _validate_d4sign_webhook(request)

    try:
        body = await request.json()
    except Exception:
        return {"ok": True}

    doc_uuid = body.get("uuid") or body.get("uuid_doc")
    event_type = body.get("type", "")

    if not doc_uuid:
        return {"ok": True}

    logger.info("D4Sign webhook: uuid=%s type=%s", doc_uuid, event_type)

    colecao, doc = await _get_doc_by_uuid(db, doc_uuid)
    if not doc:
        logger.warning("D4Sign webhook: document not found for uuid=%s", doc_uuid)
        return {"ok": True}

    update_fields = {"updated_at": datetime.utcnow()}

    if event_type in ("signed", "finished", "3"):
        update_fields["d4sign_status"] = "assinado"
        update_fields["d4sign_assinado_em"] = datetime.utcnow()
        # Tentar baixar PDF assinado em background
        try:
            from services import d4sign_service as d4
            pdf_bytes = await d4.download_documento_assinado(doc_uuid)
            tipo = [k for k, v in _TIPO_COLECAO.items() if v == colecao][0]
            doc_id = doc.get("id", "")
            existing_pdf = await db["assinaturas_pdf"].find_one({"doc_tipo": tipo, "doc_id": doc_id})
            if existing_pdf:
                await db["assinaturas_pdf"].update_one(
                    {"id": existing_pdf.get("id")},
                    {"$set": {"content": pdf_bytes, "d4sign_document_uuid": doc_uuid, "updated_at": datetime.utcnow()}},
                )
            else:
                import uuid as _uuid
                file_id = str(_uuid.uuid4())
                await db["assinaturas_pdf"].insert_one({
                    "id": file_id,
                    "doc_tipo": tipo,
                    "doc_id": doc_id,
                    "d4sign_document_uuid": doc_uuid,
                    "content": pdf_bytes,
                    "created_at": datetime.utcnow(),
                })
            update_fields["d4sign_pdf_assinado_url"] = f"/api/assinatura/{tipo}/{doc_id}/download"
        except Exception as e:
            logger.error("Webhook: erro ao baixar PDF assinado: %s", e)

    elif event_type in ("canceled", "4"):
        update_fields["d4sign_status"] = "cancelado"

    await db[colecao].update_one({"id": doc.get("id")}, {"$set": update_fields})
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
# ICP-BRASIL (PAdES) — Assinatura local com certificado A1 do avaliador
# ════════════════════════════════════════════════════════════════════════════

class AssinarIcpRequest(BaseModel):
    cert_id: str   # id do certificado cadastrado pelo usuário em /api/certificados
    layouts: list[str] = ["v2"]   # PTAM: quais layouts assinar — "v2" (completo) e/ou "v1" (classico)


@router.post("/icp/{tipo}/{id}/assinar")
async def assinar_icp_brasil(
    tipo: str,
    id: str,
    body: AssinarIcpRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Assina o documento com certificado ICP-Brasil A1 (.pfx) via PAdES.

    Anexa página visual padrão Romatec ao final do PDF e aplica assinatura
    digital com a cadeia ICP-Brasil. Resultado é equivalente ao que o
    gov.br/validar e Adobe Reader reconhecem como ICP-Brasil válido.
    """
    from services.cert_crypto import decrypt_bytes
    from services.pades_service import assinar_pdf_icp

    doc = await _get_doc(db, tipo, id, uid)

    # Buscar certificado e descriptografar
    cert = await db.certificados.find_one({"id": body.cert_id, "user_id": uid})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    if not cert.get("ativo", True):
        raise HTTPException(status_code=400, detail="Certificado desativado")

    # Validade do cert
    valido_ate = cert.get("valido_ate")
    if valido_ate and isinstance(valido_ate, datetime) and valido_ate < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail=f"Certificado expirado em {valido_ate.strftime('%d/%m/%Y')}",
        )

    try:
        pfx_bytes = decrypt_bytes(cert["pfx_encrypted"], cert["nonce_pfx"])
        pfx_password = decrypt_bytes(cert["password_encrypted"], cert["nonce_password"]).decode("utf-8")
    except Exception as e:
        logger.exception("Falha ao descriptografar certificado")
        raise HTTPException(status_code=500, detail=f"Falha ao acessar certificado: {e}")

    # Dados do avaliador (perfil + user) — layout v2 e carimbo visual da assinatura
    user = await db.users.find_one({"id": uid}) or {}
    perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}

    cidade_uf = ""
    if perfil.get("cidade") and perfil.get("uf"):
        cidade_uf = f"{perfil['cidade']}/{perfil['uf']}"
    elif doc.get("conclusion_city"):
        cidade_uf = doc["conclusion_city"]

    registros = perfil.get("registros") or []
    registro_str = ""
    if registros:
        r0 = registros[0]
        registro_str = f"{r0.get('tipo','')} {r0.get('numero','')}".strip()

    # Linhas do carimbo de assinatura (dados Romatec, vindos do perfil)
    regs_fmt = " / ".join(
        f"{(r.get('tipo') or '').strip()} nº {(r.get('numero') or '').strip()}".strip()
        for r in registros if (r.get('numero') or '').strip()
    )
    registro_full = ("Avaliador " + regs_fmt).strip() if regs_fmt else (
        ("Avaliador " + registro_str).strip() if registro_str else ""
    )
    _tel = (perfil.get("telefone") or "").strip()
    _end = (perfil.get("endereco_escritorio") or "").strip()
    if _end:
        endereco_linha = _end + (f" / Fone: {_tel}" if _tel else "")
    else:
        endereco_linha = f"Fone: {_tel}" if _tel else ""
    _email = (perfil.get("email_profissional") or user.get("email") or "").strip()
    _site = (perfil.get("site") or "").strip()
    contato_linha = " / ".join(
        x for x in [f"E-mail: {_email}" if _email else "", f"Site: {_site}" if _site else ""] if x
    )

    # Layouts a assinar. Para PTAM o usuario escolhe v2 (completo) e/ou v1 (classico);
    # demais tipos tem layout unico.
    # Modelo único consolidado: sempre v2 (layout clássico v1 descontinuado).
    layouts = ["v2"]

    import uuid as _uuid
    import copy as _copy
    assinados = []

    for layout in layouts:
        doc_layout = _copy.deepcopy(doc)
        # 1) Gera o PDF do layout
        try:
            if tipo == "ptam":
                pdf_bytes = await _render_ptam_layout(db, doc_layout, uid, layout)
            else:
                pdf_bytes = await _gerar_pdf(tipo, doc_layout, db=db, perfil=perfil)
        except Exception as e:
            logger.error("Erro ao gerar PDF (%s) para assinatura ICP: %s", layout, e)
            raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF {layout}: {e}")

        # 2) Assina com ICP-Brasil (PAdES).
        #    Roda em thread: o pyhanko (sign_pdf) chama asyncio.run() internamente,
        #    o que estoura se executado dentro do event loop do FastAPI.
        try:
            pdf_assinado, hash_final, data_assinatura = await asyncio.to_thread(
                assinar_pdf_icp,
                pdf_bytes=pdf_bytes,
                pfx_bytes=pfx_bytes,
                pfx_password=pfx_password,
                titular=cert.get("titular") or perfil.get("nome_completo") or user.get("name") or "Avaliador",
                documento=cert.get("documento") or perfil.get("cpf") or "",
                cargo=user.get("role") or perfil.get("nome_completo") and "" or "",
                registro=registro_str,
                cidade_uf=cidade_uf,
                emissor=cert.get("emissor") or "",
                valido_ate=cert.get("valido_ate"),
                registro_full=registro_full,
                endereco=endereco_linha,
                contato=contato_linha,
            )
        except Exception as e:
            logger.exception("Falha ao assinar PDF ICP-Brasil (%s)", layout)
            raise HTTPException(status_code=500, detail=f"Falha ao assinar {layout}: {e}")

        # 3) Salva o PDF assinado deste layout (no R2; só a chave no Mongo)
        await _persist_assinatura(db, tipo, id, layout, body.cert_id, pdf_assinado, hash_final)

        assinados.append({"layout": layout, "hash": hash_final, "assinado_em": data_assinatura.isoformat()})

    # Campos do documento: usa o v2 como principal (ou o primeiro assinado)
    principal = next((a for a in assinados if a["layout"] == "v2"), assinados[0])
    hash_principal = principal["hash"]
    data_principal = datetime.fromisoformat(principal["assinado_em"])

    colecao = _TIPO_COLECAO[tipo]
    await db[colecao].update_one(
        {"id": id},
        {"$set": {
            "icp_status": "assinado",
            "icp_signed_at": data_principal,
            "icp_cert_id": body.cert_id,
            "icp_titular": cert.get("titular"),
            "icp_documento": cert.get("documento"),
            "icp_emissor": cert.get("emissor"),
            "icp_hash": hash_principal,
            "icp_layouts": [a["layout"] for a in assinados],
            "icp_pdf_url": f"/api/assinatura/icp/{tipo}/{id}/download",
            "icp_verificacao_url": f"/v/laudo/v/{hash_principal}",
            "updated_at": datetime.utcnow(),
        }},
    )

    # Recibo assinado → reflete no card do PTAM vinculado.
    await _propagar_recibo_assinado(db, tipo, doc, data_principal)

    return {
        "ok": True,
        "status": "assinado",
        "metodo": "icp",
        "hash": hash_principal,
        "assinado_em": principal["assinado_em"],
        "layouts": [a["layout"] for a in assinados],
        "assinados": assinados,
        "download_url": f"/api/assinatura/icp/{tipo}/{id}/download",
        "verificacao_url": f"/v/laudo/v/{hash_principal}",
    }


async def _propagar_recibo_assinado(db, tipo: str, doc: dict, quando=None) -> None:
    """Quando um RECIBO vinculado a um PTAM/Contrato é assinado, marca
       recibo_assinado=True no documento de origem — o card passa a mostrar o
       botão verde 'Recibo Assinado'."""
    if tipo != "recibo":
        return
    quando = quando or datetime.utcnow()
    pid = (doc or {}).get("ptam_id")
    if pid:
        try:
            await db.ptam_documents.update_one(
                {"id": pid},
                {"$set": {
                    "recibo_assinado": True,
                    "recibo_assinado_em": quando,
                    "updated_at": datetime.utcnow(),
                }},
            )
        except Exception as e:
            logger.warning("Falha ao propagar recibo_assinado ao PTAM %s: %s", pid, e)
    cid = (doc or {}).get("contrato_id")
    if cid:
        try:
            await db.contratos.update_one(
                {"id": cid},
                {"$set": {
                    "recibo_assinado": True,
                    "recibo_assinado_em": quando,
                    "updated_at": datetime.utcnow(),
                }},
            )
        except Exception as e:
            logger.warning("Falha ao propagar recibo_assinado ao Contrato %s: %s", cid, e)


async def _persist_assinatura(db, tipo, doc_id, layout, cert_id, pdf_bytes, hash_final, posicionado=False):
    """Salva o PDF assinado. PDFs completos passam de 16MB (limite do Mongo),
    então gravamos no R2 e guardamos só a chave; inline só como fallback pequeno."""
    import uuid as _uuid
    r2_key = None
    try:
        from services import r2_storage
        r2_key = f"assinados/{tipo}/{doc_id}_{layout}.pdf"
        await asyncio.to_thread(
            r2_storage.upload_bytes, pdf_bytes, r2_key, "application/pdf", "private, max-age=0"
        )
    except Exception as e:
        logger.warning("Falha ao subir PDF assinado ao R2: %s", e)
        r2_key = None
    if r2_key is None and len(pdf_bytes) >= 15_000_000:
        raise HTTPException(
            status_code=500,
            detail="PDF assinado grande demais para o banco e R2 indisponível. Verifique R2_ENDPOINT/R2_BUCKET.",
        )
    base = {
        "doc_tipo": tipo, "doc_id": doc_id, "metodo": "icp", "layout": layout,
        "cert_id": cert_id, "hash_sha256": hash_final, "posicionado": posicionado,
        "r2_key": r2_key, "size_bytes": len(pdf_bytes), "updated_at": datetime.utcnow(),
    }
    if not r2_key:
        base["content"] = pdf_bytes
    existing = await db["assinaturas_pdf"].find_one(
        {"doc_tipo": tipo, "doc_id": doc_id, "metodo": "icp", "layout": layout}
    )
    if existing:
        upd = {"$set": base}
        if r2_key:
            upd["$unset"] = {"content": ""}   # remove conteúdo inline antigo (foi pro R2)
        await db["assinaturas_pdf"].update_one({"id": existing["id"]}, upd)
    else:
        await db["assinaturas_pdf"].insert_one(
            {**base, "id": str(_uuid.uuid4()), "created_at": datetime.utcnow()}
        )


async def _load_assinatura_bytes(db, tipo, doc_id, layout="v2"):
    """Retorna (pdf_bytes, assinatura_doc) do PDF assinado — do R2 ou inline."""
    a = await db["assinaturas_pdf"].find_one(
        {"doc_tipo": tipo, "doc_id": doc_id, "metodo": "icp", "layout": layout}
    )
    if not a:
        a = await db["assinaturas_pdf"].find_one(
            {"doc_tipo": tipo, "doc_id": doc_id, "metodo": "icp"}
        )
    if not a:
        return None, None
    if isinstance(a.get("content"), (bytes, bytearray)):
        return bytes(a["content"]), a
    if a.get("r2_key"):
        try:
            from services import r2_storage
            return await asyncio.to_thread(r2_storage.download_bytes, a["r2_key"]), a
        except Exception as e:
            logger.warning("Falha ao baixar PDF assinado do R2: %s", e)
            return None, a
    return None, a


# ── Assinatura POSICIONADA (usuário arrasta o retângulo) ─────────────────────

class PrepararPosicionadoRequest(BaseModel):
    layout: str = "v2"


class AssinarPosicionadoRequest(BaseModel):
    cert_id: str
    pagina: int                 # 0-indexed
    x_pt: float                 # coords em PONTOS PDF (origem bottom-left)
    y_pt: float
    largura_pt: float
    altura_pt: float


def _dados_carimbo(cert: dict, perfil: dict, user: dict):
    """(titular, documento, emissor, registro_full) para o carimbo posicionado."""
    registros = perfil.get("registros") or []
    regs_fmt = " / ".join(
        f"{(r.get('tipo') or '').strip()} nº {(r.get('numero') or '').strip()}".strip()
        for r in registros if (r.get('numero') or '').strip()
    )
    registro_full = ("Avaliador " + regs_fmt).strip() if regs_fmt else ""
    titular = cert.get("titular") or perfil.get("nome_completo") or user.get("name") or "Avaliador"
    documento = cert.get("documento") or perfil.get("cpf") or ""
    emissor = cert.get("emissor") or ""
    return titular, documento, emissor, registro_full


@router.post("/icp/{tipo}/{id}/preparar")
async def preparar_assinatura_posicionada(
    tipo: str,
    id: str,
    body: PrepararPosicionadoRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera o PDF (layout completo v2), guarda no R2 e devolve as páginas
    renderizadas para o usuário posicionar a assinatura. Preview e assinatura
    usam EXATAMENTE este arquivo."""
    from services import r2_storage
    from services.pdf_preview import renderizar_paginas

    doc = await _get_doc(db, tipo, id, uid)
    try:
        if tipo == "ptam":
            pdf_bytes = await _render_ptam_layout(db, doc, uid, "v2")
        else:
            perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}
            pdf_bytes = await _gerar_pdf(tipo, doc, db=db, perfil=perfil)
    except Exception as e:
        logger.exception("Erro ao gerar PDF para assinatura posicionada")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {e}")

    key = f"assinatura_tmp/{uid}/{tipo}_{id}.pdf"
    try:
        await asyncio.to_thread(
            r2_storage.upload_bytes, pdf_bytes, key, "application/pdf", "private, max-age=0"
        )
    except Exception as e:
        logger.exception("Falha ao subir PDF temporário ao R2")
        raise HTTPException(status_code=502, detail=f"Falha ao preparar PDF: {e}")

    await db[_TIPO_COLECAO[tipo]].update_one(
        {"id": id, "user_id": uid},
        {"$set": {"pdf_assinatura_key": key, "pdf_assinatura_prep_em": datetime.utcnow()}},
    )

    try:
        paginas = await asyncio.to_thread(renderizar_paginas, pdf_bytes)
    except Exception as e:
        logger.exception("Erro ao renderizar páginas do PDF")
        raise HTTPException(status_code=500, detail=f"Erro ao renderizar páginas: {e}")

    return {"paginas": paginas, "total": len(paginas)}


@router.post("/icp/{tipo}/{id}/posicionado")
async def assinar_posicionado(
    tipo: str,
    id: str,
    body: AssinarPosicionadoRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Assina o PDF preparado, posicionando o carimbo ICP-Brasil na página/caixa
    escolhidas. Salva em assinaturas_pdf e atualiza os campos icp_* do documento."""
    import uuid as _uuid
    from services.cert_crypto import decrypt_bytes
    from services.pades_service import assinar_pdf_icp_posicionado
    from services import r2_storage

    doc = await _get_doc(db, tipo, id, uid)
    key = doc.get("pdf_assinatura_key")
    if not key:
        raise HTTPException(status_code=400, detail="Documento não preparado. Reabra o assinador.")

    cert = await db.certificados.find_one({"id": body.cert_id, "user_id": uid})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    if not cert.get("ativo", True):
        raise HTTPException(status_code=400, detail="Certificado desativado")
    valido_ate = cert.get("valido_ate")
    if valido_ate and isinstance(valido_ate, datetime) and valido_ate < datetime.utcnow():
        raise HTTPException(status_code=400, detail=f"Certificado expirado em {valido_ate.strftime('%d/%m/%Y')}")

    try:
        pfx_bytes = decrypt_bytes(cert["pfx_encrypted"], cert["nonce_pfx"])
        pfx_password = decrypt_bytes(cert["password_encrypted"], cert["nonce_password"]).decode("utf-8")
    except Exception as e:
        logger.exception("Falha ao descriptografar certificado")
        raise HTTPException(status_code=500, detail=f"Falha ao acessar certificado: {e}")

    try:
        pdf_bytes = await asyncio.to_thread(r2_storage.download_bytes, key)
    except Exception as e:
        logger.exception("Falha ao baixar PDF preparado do R2")
        raise HTTPException(status_code=410, detail="PDF preparado expirou. Reabra o assinador.")

    user = await db.users.find_one({"id": uid}) or {}
    perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}
    titular, documento, emissor, registro_full = _dados_carimbo(cert, perfil, user)

    try:
        pdf_assinado, hash_final, data_assinatura = await asyncio.to_thread(
            assinar_pdf_icp_posicionado,
            pdf_bytes=pdf_bytes,
            pfx_bytes=pfx_bytes,
            pfx_password=pfx_password,
            pagina=body.pagina,
            x=body.x_pt,
            y=body.y_pt,
            largura=body.largura_pt,
            altura=body.altura_pt,
            titular=titular,
            documento=documento,
            emissor=emissor,
            valido_ate=cert.get("valido_ate"),
            registro_full=registro_full,
        )
    except Exception as e:
        logger.exception("Falha ao assinar PDF posicionado")
        raise HTTPException(status_code=500, detail=f"Falha ao assinar: {e}")

    layout = "v2"
    await _persist_assinatura(db, tipo, id, layout, body.cert_id, pdf_assinado, hash_final, posicionado=True)

    await db[_TIPO_COLECAO[tipo]].update_one(
        {"id": id},
        {"$set": {
            "icp_status": "assinado",
            "icp_signed_at": data_assinatura,
            "icp_cert_id": body.cert_id,
            "icp_titular": cert.get("titular"),
            "icp_documento": cert.get("documento"),
            "icp_emissor": cert.get("emissor"),
            "icp_hash": hash_final,
            "icp_layouts": [layout],
            "icp_pdf_url": f"/api/assinatura/icp/{tipo}/{id}/download",
            "icp_verificacao_url": f"/v/laudo/v/{hash_final}",
            "updated_at": datetime.utcnow(),
        }, "$unset": {"pdf_assinatura_key": ""}},
    )

    # Recibo assinado → reflete no card do PTAM vinculado.
    await _propagar_recibo_assinado(db, tipo, doc, data_assinatura)

    try:
        await asyncio.to_thread(r2_storage.delete_object, key)
    except Exception:
        pass

    return {
        "ok": True,
        "status": "assinado",
        "hash": hash_final,
        "assinado_em": data_assinatura.isoformat(),
        "download_url": f"/api/assinatura/icp/{tipo}/{id}/download",
        "verificacao_url": f"/v/laudo/v/{hash_final}",
    }


@router.post("/icp/{tipo}/{id}/resetar")
async def resetar_assinatura(
    tipo: str,
    id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Zera a assinatura ICP do documento: remove o(s) PDF(s) assinado(s) (R2 +
    Mongo) e limpa os campos icp_*, voltando o laudo a 'não assinado' para re-assinar."""
    await _get_doc(db, tipo, id, uid)  # valida posse

    removidos = 0
    cursor = db["assinaturas_pdf"].find({"doc_tipo": tipo, "doc_id": id, "metodo": "icp"})
    async for a in cursor:
        if a.get("r2_key"):
            try:
                from services import r2_storage
                await asyncio.to_thread(r2_storage.delete_object, a["r2_key"])
            except Exception:
                pass
        removidos += 1
    await db["assinaturas_pdf"].delete_many({"doc_tipo": tipo, "doc_id": id, "metodo": "icp"})

    await db[_TIPO_COLECAO[tipo]].update_one(
        {"id": id, "user_id": uid},
        {"$unset": {
            "icp_status": "", "icp_signed_at": "", "icp_cert_id": "", "icp_titular": "",
            "icp_documento": "", "icp_emissor": "", "icp_hash": "", "icp_layouts": "",
            "icp_pdf_url": "", "icp_verificacao_url": "", "pdf_assinatura_key": "",
        }, "$set": {"updated_at": datetime.utcnow()}},
    )
    return {"ok": True, "status": "nao_assinado", "removidos": removidos}


@router.get("/icp/{tipo}/{id}/download")
async def download_icp(
    tipo: str,
    id: str,
    layout: str = "v2",
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await _get_doc(db, tipo, id, uid)
    if doc.get("icp_status") != "assinado":
        raise HTTPException(status_code=404, detail="Documento ainda não assinado com ICP-Brasil")

    # Lê o PDF assinado (do R2 ou inline legado)
    pdf_bytes, assinatura = await _load_assinatura_bytes(db, tipo, id, layout)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="PDF assinado não disponível")

    numero = doc.get("numero_ptam") or doc.get("numero_tvi") or doc.get("numero") or id
    _lay = (assinatura or {}).get("layout")
    suffix = f"_{_lay}" if (_lay and _lay != "v2") else ""
    filename = f"{tipo.upper()}_{numero}_ASSINADO_ICP{suffix}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ════════════════════════════════════════════════════════════════════════════
# Verificação pública (NÃO autenticada) — alvo do QR Code
# ════════════════════════════════════════════════════════════════════════════

@router.get("/v/laudo/v/{hash_id}", include_in_schema=True)
async def verificar_publico(hash_id: str, db=Depends(get_db)):
    """Endpoint público pra validar autenticidade de um laudo assinado.
    Retorna metadados (sem .pfx, sem PDF) — chamado pelo QR Code do bloco visual.
    """
    assinatura = await db["assinaturas_pdf"].find_one(
        {"hash_sha256": hash_id, "metodo": "icp"}
    )
    if not assinatura:
        raise HTTPException(status_code=404, detail="Hash não encontrado")

    tipo = assinatura.get("doc_tipo")
    doc_id = assinatura.get("doc_id")
    colecao = _TIPO_COLECAO.get(tipo)
    if not colecao:
        raise HTTPException(status_code=400, detail="Tipo inválido")

    doc = await db[colecao].find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    return {
        "autentico": True,
        "tipo": tipo,
        "numero": doc.get("numero_ptam") or doc.get("number") or doc_id,
        "titular": doc.get("icp_titular"),
        "documento": doc.get("icp_documento"),
        "emissor": doc.get("icp_emissor"),
        "assinado_em": doc.get("icp_signed_at").isoformat() if doc.get("icp_signed_at") else None,
        "imovel": doc.get("property_label") or doc.get("property_address"),
        "hash": hash_id,
    }
