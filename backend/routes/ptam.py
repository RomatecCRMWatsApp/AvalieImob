# @module routes.ptam — CRUD PTAM e download de PDF/DOCX; envio por e-mail
import base64
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from services.auth_service import get_current_user_id
from services.ptam_share import enviar_ptam_email
from models import PtamBase, Ptam
from ptam_docx import generate_ptam_docx
from pdf.ptam_pdf import generate_ptam_pdf

router = APIRouter(tags=["ptam"])
logger = logging.getLogger("romatec")


class PtamEmailRequest(BaseModel):
    destinatario: str
    nome_cliente: Optional[str] = ""
    mensagem_extra: Optional[str] = ""


async def _next_ptam_numero(db) -> str:
    ano = datetime.utcnow().year
    result = await db.counters.find_one_and_update(
        {"_id": "ptam_numero"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"{result['seq']:04d}/{ano}"


@router.get("/ptam", response_model=List[Ptam])
async def list_ptam(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    items = await db.ptam_documents.find({"user_id": uid}).sort("updated_at", -1).to_list(1000)
    return [Ptam(**serialize_doc(i)) for i in items]


@router.get("/ptam/{pid}", response_model=Ptam)
async def get_ptam(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    return Ptam(**serialize_doc(doc))


@router.post("/ptam", response_model=Ptam)
async def create_ptam(data: PtamBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    numero_ptam = await _next_ptam_numero(db)
    number = data.number or numero_ptam
    payload = data.model_dump()
    payload["numero_ptam"] = numero_ptam
    payload["number"] = number
    p = Ptam(user_id=uid, **payload)
    await db.ptam_documents.insert_one(p.model_dump())
    return p


@router.put("/ptam/{pid}", response_model=Ptam)
async def update_ptam(pid: str, data: PtamBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    await db.ptam_documents.update_one({"id": pid}, {"$set": updates})
    new_doc = await db.ptam_documents.find_one({"id": pid})
    return Ptam(**serialize_doc(new_doc))


@router.delete("/ptam/{pid}")
async def delete_ptam(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.ptam_documents.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    return {"ok": True}


@router.get("/ptam/{pid}/docx")
async def download_ptam_docx(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    user = await db.users.find_one({"id": uid})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Logo da empresa
    company_logo_id = user.get("company_logo")
    if company_logo_id:
        logo_doc = await db.images.find_one({"id": company_logo_id, "user_id": uid})
        if logo_doc:
            import base64 as _b64
            user["_company_logo_bytes"] = _b64.b64decode(logo_doc["data_b64"])

    try:
        # ── Buscar fotos do imóvel ─────────────────────────────────────────
        fotos_imovel = doc.get("fotos_imovel") or []
        for i, foto in enumerate(fotos_imovel):
            if isinstance(foto, str):
                url = foto
            elif isinstance(foto, dict):
                url = foto.get("url") or foto.get("image_id", "")
            else:
                continue
            parts = str(url).replace('/api/upload/image/', '').split('/')
            image_id = parts[-1] if parts else str(url)
            if len(image_id) > 30 and '-' in image_id:
                img_doc = await db.images.find_one({"id": image_id})
                if img_doc and img_doc.get("data_b64"):
                    fotos_imovel[i] = {
                        "image_id": image_id,
                        "url": url,
                        "_image_bytes": base64.b64decode(img_doc["data_b64"]),
                        "description": (foto.get("description") or foto.get("descricao") or f"Foto {i+1}") if isinstance(foto, dict) else f"Foto {i+1}",
                    }
        doc["fotos_imovel"] = fotos_imovel

        # ── Buscar documentos digitalizados ───────────────────────────────
        docs_list = doc.get("fotos_documentos") or []
        docs_processados = []
        for i, doc_item in enumerate(docs_list):
            if isinstance(doc_item, str):
                url = doc_item
            elif isinstance(doc_item, dict):
                url = doc_item.get("url") or doc_item.get("doc_id") or doc_item.get("image_id", "")
            else:
                continue
            parts = str(url).replace('/api/upload/image/', '').split('/')
            doc_id = parts[-1] if parts else str(url)
            if len(doc_id) > 30 and '-' in doc_id:
                doc_db = await db.images.find_one({"id": doc_id})
                if doc_db and doc_db.get("data_b64"):
                    docs_processados.append({
                        "doc_id": doc_id,
                        "url": url,
                        "_doc_bytes": base64.b64decode(doc_db["data_b64"]),
                        "name": doc_db.get("filename") or (doc_item.get("name") if isinstance(doc_item, dict) else None) or f"Documento {i+1}",
                        "content_type": doc_db.get("content_type", "application/pdf"),
                    })
                else:
                    docs_processados.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
            else:
                docs_processados.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
        doc["fotos_documentos"] = docs_processados

        # ── Buscar imagens das amostras de mercado ────────────────────────
        market_samples = doc.get("market_samples") or []
        for j, sample in enumerate(market_samples):
            foto_url = sample.get("foto_url") or ""
            if not foto_url:
                continue
            parts = str(foto_url).replace('/api/upload/image/', '').split('/')
            sample_image_id = parts[-1] if parts else str(foto_url)
            if len(sample_image_id) > 30 and '-' in sample_image_id:
                sample_img_doc = await db.images.find_one({"id": sample_image_id})
                if sample_img_doc and sample_img_doc.get("data_b64"):
                    market_samples[j] = {
                        **sample,
                        "_image_bytes": base64.b64decode(sample_img_doc["data_b64"]),
                    }
        doc["market_samples"] = market_samples

        # ── Buscar consultas CND vinculadas ao PTAM ────────────────────────
        cnd_consultas = []
        raw_consultas = await db.cnd_consultas.find({"ptam_id": pid, "user_id": uid}).to_list(20)
        for c in raw_consultas:
            certs = await db.cnd_certidoes.find({"consulta_id": c.get("id", "")}).to_list(10)
            cnd_consultas.append({"consulta": c, "certidoes": certs})

        data = generate_ptam_docx(doc, user, cnd_consultas=cnd_consultas)
    except Exception as e:
        logger.exception("DOCX generation error")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar DOCX: {str(e)[:200]}")
    if not data:
        raise HTTPException(status_code=500, detail="Falha ao gerar documento")
    filename = f"PTAM_{doc.get('number', 'sem-numero').replace('/', '-')}.docx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/ptam/{pid}/pdf")
async def download_ptam_pdf(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    user = await db.users.find_one({"id": uid})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    company_logo_id = user.get("company_logo")
    if company_logo_id:
        logo_doc = await db.images.find_one({"id": company_logo_id, "user_id": uid})
        if logo_doc:
            import base64 as _b64
            user["_company_logo_bytes"] = _b64.b64decode(logo_doc["data_b64"])
    try:
        # ── Buscar fotos do imóvel ─────────────────────────────────────────
        fotos_imovel = doc.get("fotos_imovel") or []
        for i, foto in enumerate(fotos_imovel):
            if isinstance(foto, str):
                url = foto
            elif isinstance(foto, dict):
                url = foto.get("url") or foto.get("image_id", "")
            else:
                continue
            parts = str(url).replace('/api/upload/image/', '').split('/')
            image_id = parts[-1] if parts else str(url)
            if len(image_id) > 30 and '-' in image_id:
                img_doc = await db.images.find_one({"id": image_id})
                if img_doc and img_doc.get("data_b64"):
                    fotos_imovel[i] = {
                        "image_id": image_id,
                        "url": url,
                        "_image_bytes": base64.b64decode(img_doc["data_b64"]),
                        "description": (foto.get("description") or foto.get("descricao") or f"Foto {i+1}") if isinstance(foto, dict) else f"Foto {i+1}",
                    }
        doc["fotos_imovel"] = fotos_imovel

        # ── Buscar documentos digitalizados ───────────────────────────────
        docs_list = doc.get("fotos_documentos") or []
        docs_processados = []
        for i, doc_item in enumerate(docs_list):
            if isinstance(doc_item, str):
                url = doc_item
            elif isinstance(doc_item, dict):
                url = doc_item.get("url") or doc_item.get("doc_id") or doc_item.get("image_id", "")
            else:
                continue
            parts = str(url).replace('/api/upload/image/', '').split('/')
            doc_id = parts[-1] if parts else str(url)
            if len(doc_id) > 30 and '-' in doc_id:
                doc_db = await db.images.find_one({"id": doc_id})
                if doc_db and doc_db.get("data_b64"):
                    docs_processados.append({
                        "doc_id": doc_id,
                        "url": url,
                        "_doc_bytes": base64.b64decode(doc_db["data_b64"]),
                        "name": doc_db.get("filename") or (doc_item.get("name") if isinstance(doc_item, dict) else None) or f"Documento {i+1}",
                        "content_type": doc_db.get("content_type", "application/pdf"),
                    })
                else:
                    docs_processados.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
            else:
                docs_processados.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
        doc["fotos_documentos"] = docs_processados

        # ── Buscar imagens das amostras de mercado ────────────────────────
        market_samples = doc.get("market_samples") or []
        for j, sample in enumerate(market_samples):
            foto_url = sample.get("foto_url") or ""
            if not foto_url:
                continue
            parts = str(foto_url).replace('/api/upload/image/', '').split('/')
            sample_image_id = parts[-1] if parts else str(foto_url)
            if len(sample_image_id) > 30 and '-' in sample_image_id:
                sample_img_doc = await db.images.find_one({"id": sample_image_id})
                if sample_img_doc and sample_img_doc.get("data_b64"):
                    market_samples[j] = {
                        **sample,
                        "_image_bytes": base64.b64decode(sample_img_doc["data_b64"]),
                    }
        doc["market_samples"] = market_samples

        # Busca consultas CND vinculadas ao PTAM para incluir no PDF
        cnd_consultas = []
        raw_consultas = await db.cnd_consultas.find({"ptam_id": pid, "user_id": uid}).to_list(20)
        for c in raw_consultas:
            certs = await db.cnd_certidoes.find({"consulta_id": c.get("id", "")}).to_list(10)
            cnd_consultas.append({"consulta": c, "certidoes": certs})
        data = generate_ptam_pdf(doc, user, cnd_consultas=cnd_consultas)
    except Exception as e:
        logger.exception("PDF generation error")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)[:200]}")
    if not data or len(data) < 100:
        raise HTTPException(status_code=500, detail="PDF gerado vazio ou corrompido")
    if not data.startswith(b'%PDF-'):
        raise HTTPException(status_code=500, detail="PDF inválido — não começa com %PDF-")
    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename = f"PTAM_{doc.get('number', 'sem-numero').replace('/', '-')}_{date_str}.pdf"
    logger.info(f"PTAM {pid}: PDF gerado — {len(data)} bytes")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
            "Content-Transfer-Encoding": "binary",
            "Cache-Control": "no-store",
        },
    )


@router.post("/ptam/{pid}/email")
async def send_ptam_email(
    pid: str,
    body: PtamEmailRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera o PTAM em PDF e envia por e-mail ao destinatário informado."""
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")

    user = await db.users.find_one({"id": uid})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Inclui logo se disponível
    company_logo_id = user.get("company_logo")
    if company_logo_id:
        logo_doc = await db.images.find_one({"id": company_logo_id, "user_id": uid})
        if logo_doc:
            import base64 as _b64
            user["_company_logo_bytes"] = _b64.b64decode(logo_doc["data_b64"])

    try:
        # ── Buscar fotos do imóvel ─────────────────────────────────────────
        fotos_imovel_e = doc.get("fotos_imovel") or []
        for i, foto in enumerate(fotos_imovel_e):
            if isinstance(foto, str):
                url = foto
            elif isinstance(foto, dict):
                url = foto.get("url") or foto.get("image_id", "")
            else:
                continue
            parts = str(url).replace('/api/upload/image/', '').split('/')
            image_id = parts[-1] if parts else str(url)
            if len(image_id) > 30 and '-' in image_id:
                img_doc = await db.images.find_one({"id": image_id})
                if img_doc and img_doc.get("data_b64"):
                    fotos_imovel_e[i] = {
                        "image_id": image_id,
                        "url": url,
                        "_image_bytes": base64.b64decode(img_doc["data_b64"]),
                        "description": (foto.get("description") or foto.get("descricao") or f"Foto {i+1}") if isinstance(foto, dict) else f"Foto {i+1}",
                    }
        doc["fotos_imovel"] = fotos_imovel_e

        # ── Buscar documentos digitalizados ───────────────────────────────
        docs_list_e = doc.get("fotos_documentos") or []
        docs_proc_e = []
        for i, doc_item in enumerate(docs_list_e):
            if isinstance(doc_item, str):
                url = doc_item
            elif isinstance(doc_item, dict):
                url = doc_item.get("url") or doc_item.get("doc_id") or doc_item.get("image_id", "")
            else:
                continue
            parts = str(url).replace('/api/upload/image/', '').split('/')
            doc_id = parts[-1] if parts else str(url)
            if len(doc_id) > 30 and '-' in doc_id:
                doc_db = await db.images.find_one({"id": doc_id})
                if doc_db and doc_db.get("data_b64"):
                    docs_proc_e.append({
                        "doc_id": doc_id,
                        "url": url,
                        "_doc_bytes": base64.b64decode(doc_db["data_b64"]),
                        "name": doc_db.get("filename") or (doc_item.get("name") if isinstance(doc_item, dict) else None) or f"Documento {i+1}",
                        "content_type": doc_db.get("content_type", "application/pdf"),
                    })
                else:
                    docs_proc_e.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
            else:
                docs_proc_e.append(doc_item if isinstance(doc_item, dict) else {"url": doc_item, "name": f"Documento {i+1}"})
        doc["fotos_documentos"] = docs_proc_e

        # ── Buscar imagens das amostras de mercado ────────────────────────
        market_samples_e = doc.get("market_samples") or []
        for j, sample in enumerate(market_samples_e):
            foto_url = sample.get("foto_url") or ""
            if not foto_url:
                continue
            parts = str(foto_url).replace('/api/upload/image/', '').split('/')
            sample_image_id = parts[-1] if parts else str(foto_url)
            if len(sample_image_id) > 30 and '-' in sample_image_id:
                sample_img_doc = await db.images.find_one({"id": sample_image_id})
                if sample_img_doc and sample_img_doc.get("data_b64"):
                    market_samples_e[j] = {
                        **sample,
                        "_image_bytes": base64.b64decode(sample_img_doc["data_b64"]),
                    }
        doc["market_samples"] = market_samples_e

        # Busca consultas CND vinculadas para incluir no PDF enviado por email
        cnd_consultas_email = []
        raw_c = await db.cnd_consultas.find({"ptam_id": pid, "user_id": uid}).to_list(20)
        for c in raw_c:
            certs = await db.cnd_certidoes.find({"consulta_id": c.get("id", "")}).to_list(10)
            cnd_consultas_email.append({"consulta": c, "certidoes": certs})
        pdf_bytes = generate_ptam_pdf(doc, user, cnd_consultas=cnd_consultas_email)
    except Exception as e:
        logger.exception("Erro ao gerar PDF para envio por email")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)[:200]}")

    # Dados do avaliador para o template do email
    perfil = await db.perfil_avaliador.find_one({"user_id": uid})
    nome_avaliador = ""
    registro_profissional = ""
    if perfil:
        nome_avaliador = perfil.get("nome_completo", "")
        registros = perfil.get("registros", [])
        if registros:
            r = registros[0]
            registro_profissional = f"{r.get('tipo', '')} {r.get('numero', '')} {r.get('uf', '')}".strip()

    numero = doc.get("number") or doc.get("numero_ptam") or pid
    endereco = doc.get("property_address") or doc.get("property_label") or ""

    await enviar_ptam_email(
        to_email=body.destinatario,
        numero=numero,
        endereco=endereco,
        pdf_bytes=pdf_bytes,
        nome_dest=body.nome_cliente or "",
        nome_avaliador=nome_avaliador,
        registro_profissional=registro_profissional,
        mensagem_extra=body.mensagem_extra or "",
    )

    # Registra envio em email_logs
    log = {
        "tipo": "ptam",
        "doc_id": pid,
        "numero": numero,
        "destinatario": body.destinatario,
        "nome_cliente": body.nome_cliente or "",
        "user_id": uid,
        "enviado_em": datetime.utcnow(),
    }
    await db.email_logs.insert_one(log)

    logger.info("PTAM %s enviado por email para %s", numero, body.destinatario)
    return {"ok": True, "mensagem": f"E-mail enviado para {body.destinatario}"}
