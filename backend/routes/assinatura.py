# @module routes.assinatura — Endpoints de assinatura digital com validade juridica via D4Sign
# Lei 14.063/2020 + MP 2.200-2/2001
import os
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


async def _gerar_pdf(tipo: str, doc: dict) -> bytes:
    """Gera PDF do documento conforme tipo."""
    if tipo == "ptam":
        from pdf.ptam_pdf import generate_ptam_pdf
        return generate_ptam_pdf(doc)
    elif tipo == "tvi":
        # TVI usa exportacao similar — fallback para PDF simples se nao implementado
        try:
            from pdf.tvi_pdf import generate_tvi_pdf
            return generate_tvi_pdf(doc)
        except ImportError:
            from pdf.ptam_pdf import generate_ptam_pdf
            return generate_ptam_pdf(doc)
    elif tipo == "garantia":
        try:
            from pdf.garantia_pdf import generate_garantia_pdf
            return generate_garantia_pdf(doc)
        except ImportError:
            from pdf.ptam_pdf import generate_ptam_pdf
            return generate_ptam_pdf(doc)
    raise HTTPException(status_code=400, detail=f"Geracao de PDF nao suportada para tipo: {tipo}")


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

    # Gerar PDF
    try:
        pdf_bytes = await _gerar_pdf(tipo, doc)
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
            import uuid as _uuid
            file_id = str(_uuid.uuid4())
            tipo = [k for k, v in _TIPO_COLECAO.items() if v == colecao][0]
            doc_id = doc.get("id", "")
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
