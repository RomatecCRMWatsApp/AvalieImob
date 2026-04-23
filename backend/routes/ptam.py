# @module routes.ptam — CRUD PTAM, versionamento com diff/lacre/SHA-256, download PDF/DOCX; envio por e-mail
import base64
import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from services.auth_service import get_current_user_id
from services.ptam_share import enviar_ptam_email
from models import PtamBase, Ptam, PtamVersion, PtamVersionDiff
from pdf.ptam_pdf import generate_ptam_pdf

router = APIRouter(tags=["ptam"])
logger = logging.getLogger("romatec")


class PtamEmailRequest(BaseModel):
    destinatario: str
    nome_cliente: Optional[str] = ""
    mensagem_extra: Optional[str] = ""


class LacrarVersaoRequest(BaseModel):
    observacao: Optional[str] = ""


# Campos ignorados no diff (metadados)
IGNORED_DIFF_FIELDS = {"id", "_id", "user_id", "created_at", "updated_at", "numero_ptam"}


def _calculate_hash(data: dict) -> str:
    """Calcula SHA-256 do JSON do PTAM."""
    conteudo = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(conteudo.encode()).hexdigest()


def _deep_diff(old: Any, new: Any, path: str = "") -> List[PtamVersionDiff]:
    """Compara dois objetos profundamente e retorna lista de diffs."""
    diffs = []
    
    if isinstance(old, dict) and isinstance(new, dict):
        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            if key in IGNORED_DIFF_FIELDS:
                continue
            full_path = f"{path}.{key}" if path else key
            old_val = old.get(key)
            new_val = new.get(key)
            diffs.extend(_deep_diff(old_val, new_val, full_path))
    elif isinstance(old, list) and isinstance(new, list):
        # Para listas, comparar por índice
        max_len = max(len(old), len(new))
        for i in range(max_len):
            full_path = f"{path}[{i}]"
            old_val = old[i] if i < len(old) else None
            new_val = new[i] if i < len(new) else None
            diffs.extend(_deep_diff(old_val, new_val, full_path))
    else:
        # Valores primitivos
        if old != new:
            # Simplificar valores grandes (fotos, base64)
            old_display = old
            new_display = new
            if isinstance(old, str) and len(old) > 100:
                old_display = "[alterado]"
            if isinstance(new, str) and len(new) > 100:
                new_display = "[alterado]"
            diffs.append(PtamVersionDiff(
                campo=path,
                valor_anterior=old_display if old != "" and old is not None else None,
                valor_novo=new_display if new != "" and new is not None else None
            ))
    
    return diffs


async def _create_version(
    db,
    ptam_id: str,
    user_id: str,
    old_doc: dict,
    new_data: dict,
    tipo: str = "auto",
    ip: str = None,
    user_agent: str = None,
    numero_lacre: str = None,
    observacao: str = None,
    snapshot: dict = None
) -> Optional[PtamVersion]:
    """Cria uma nova versão se houver mudanças."""
    
    # Calcular diffs
    diffs = _deep_diff(old_doc, new_data)
    
    # Se não há diffs e não é lacre, não criar versão
    if not diffs and tipo == "auto":
        return None
    
    # Buscar última versão para número
    last_version = await db.ptam_versions.find_one(
        {"ptam_id": ptam_id},
        sort=[("numero_versao", -1)]
    )
    numero_versao = (last_version["numero_versao"] + 1) if last_version else 1
    
    # Calcular hash
    hash_sha256 = _calculate_hash(new_data)
    
    # Verificar se hash é igual à última versão (evitar duplicatas)
    if last_version and last_version.get("hash_sha256") == hash_sha256:
        return None
    
    version = PtamVersion(
        ptam_id=ptam_id,
        user_id=user_id,
        numero_versao=numero_versao,
        tipo=tipo,
        hash_sha256=hash_sha256,
        diffs=diffs,
        snapshot=snapshot,
        ip=ip,
        user_agent=user_agent,
        numero_lacre=numero_lacre,
        observacao=observacao
    )
    
    await db.ptam_versions.insert_one(version.model_dump())
    return version


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
async def update_ptam(
    pid: str,
    data: PtamBase,
    request: Request,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db)
):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    
    # Preparar novos dados
    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()
    
    # Criar versão automática
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")
    
    await _create_version(
        db=db,
        ptam_id=pid,
        user_id=uid,
        old_doc=doc,
        new_data={**doc, **updates},
        tipo="auto",
        ip=ip,
        user_agent=user_agent
    )
    
    # Atualizar documento
    await db.ptam_documents.update_one({"id": pid}, {"$set": updates})
    new_doc = await db.ptam_documents.find_one({"id": pid})
    return Ptam(**serialize_doc(new_doc))


@router.delete("/ptam/{pid}")
async def delete_ptam(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.ptam_documents.delete_one({"id": pid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    # Também deletar versões
    await db.ptam_versions.delete_many({"ptam_id": pid})
    return {"ok": True}


# ============ ENDPOINTS DE VERSIONAMENTO ============

@router.get("/ptam/{pid}/versoes")
async def list_versoes(
    pid: str,
    limit: int = 100,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db)
):
    """Lista histórico de versões de um PTAM (sem snapshots)."""
    # Verificar se PTAM existe e pertence ao usuário
    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    
    versoes = await db.ptam_versions.find(
        {"ptam_id": pid},
        {"snapshot": 0}  # Excluir snapshot para economizar banda
    ).sort("numero_versao", -1).limit(limit).to_list(limit)
    
    return [serialize_doc(v) for v in versoes]


@router.post("/ptam/{pid}/lacrar")
async def lacrar_versao(
    pid: str,
    body: LacrarVersaoRequest,
    request: Request,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db)
):
    """Lacra uma versão do PTAM (torna imutável com snapshot completo)."""
    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    
    # Buscar última versão
    last_version = await db.ptam_versions.find_one(
        {"ptam_id": pid},
        sort=[("numero_versao", -1)]
    )
    numero_versao = (last_version["numero_versao"] + 1) if last_version else 1
    
    # Gerar número de lacre
    ano = datetime.utcnow().year
    numero_ptam = ptam.get("numero_ptam", "0000")
    numero_lacre = f"PTAM-{ano}-{numero_ptam}-v{numero_versao}"
    
    # Criar snapshot completo (cópia do PTAM)
    snapshot = {k: v for k, v in ptam.items() if not k.startswith("_")}
    
    # Calcular hash do snapshot
    hash_sha256 = _calculate_hash(snapshot)
    
    # Calcular diffs vs versão anterior
    diffs = []
    if last_version:
        old_snapshot = last_version.get("snapshot") or {}
        diffs = _deep_diff(old_snapshot, snapshot)
    
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")
    
    version = PtamVersion(
        ptam_id=pid,
        user_id=uid,
        numero_versao=numero_versao,
        tipo="lacrado",
        hash_sha256=hash_sha256,
        diffs=diffs,
        snapshot=snapshot,
        ip=ip,
        user_agent=user_agent,
        numero_lacre=numero_lacre,
        observacao=body.observacao
    )
    
    await db.ptam_versions.insert_one(version.model_dump())
    
    # Atualizar PTAM com info do lacre
    await db.ptam_documents.update_one(
        {"id": pid},
        {
            "$set": {
                "lacrado": True,
                "versao_lacrada": numero_lacre,
                "hash_lacrado": hash_sha256,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "ok": True,
        "versao": serialize_doc(version.model_dump()),
        "numero_lacre": numero_lacre,
        "hash_sha256": hash_sha256
    }


@router.get("/ptam/{pid}/versoes/{vid}")
async def get_versao(
    pid: str,
    vid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db)
):
    """Busca uma versão específica (incluindo snapshot se lacrada)."""
    # Verificar se PTAM existe e pertence ao usuário
    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    
    versao = await db.ptam_versions.find_one({"id": vid, "ptam_id": pid})
    if not versao:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    
    return serialize_doc(versao)


@router.get("/ptam/{pid}/verificar/{vid}")
async def verificar_integridade(
    pid: str,
    vid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db)
):
    """Verifica integridade de uma versão lacrada recalculando o hash."""
    # Verificar se PTAM existe e pertence ao usuário
    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    
    versao = await db.ptam_versions.find_one({"id": vid, "ptam_id": pid})
    if not versao:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    
    if versao.get("tipo") != "lacrado":
        raise HTTPException(status_code=400, detail="Apenas versões lacradas podem ser verificadas")
    
    snapshot = versao.get("snapshot")
    if not snapshot:
        raise HTTPException(status_code=400, detail="Versão lacrada sem snapshot")
    
    hash_armazenado = versao.get("hash_sha256", "")
    hash_calculado = _calculate_hash(snapshot)
    
    return {
        "integro": hash_armazenado == hash_calculado,
        "hash_armazenado": hash_armazenado,
        "hash_calculado": hash_calculado,
        "numero_lacre": versao.get("numero_lacre"),
        "numero_versao": versao.get("numero_versao")
    }


# ============ DOWNLOAD DOCX/PDF ============

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
            foto_url = sample.get("foto") or sample.get("foto_url") or ""
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

        # ── Buscar perfil do avaliador (currículo) ─────────────────────────
        perfil_avaliador = await db.perfil_avaliador.find_one({"user_id": uid})
        if perfil_avaliador:
            perfil_avaliador.pop("_id", None)

        data = generate_ptam_docx(doc, user, cnd_consultas=cnd_consultas, perfil_avaliador=perfil_avaliador)
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
            foto_url = sample.get("foto") or sample.get("foto_url") or ""
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

        # ── Buscar perfil do avaliador (currículo) ─────────────────────────
        perfil_avaliador = await db.perfil_avaliador.find_one({"user_id": uid})
        if perfil_avaliador:
            perfil_avaliador.pop("_id", None)

        data = generate_ptam_pdf(doc, user, cnd_consultas=cnd_consultas, perfil_avaliador=perfil_avaliador)
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
            foto_url = sample.get("foto") or sample.get("foto_url") or ""
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

        # ── Buscar perfil do avaliador (currículo) ─────────────────────────
        perfil_avaliador_email = await db.perfil_avaliador.find_one({"user_id": uid})
        if perfil_avaliador_email:
            perfil_avaliador_email.pop("_id", None)

        pdf_bytes = generate_ptam_pdf(doc, user, cnd_consultas=cnd_consultas_email, perfil_avaliador=perfil_avaliador_email)
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


# ============ PORTAL PÚBLICO DO CLIENTE ============

@router.post("/ptam/{pid}/compartilhar")
async def compartilhar_ptam(
    pid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db)
):
    """Gera token de compartilhamento público para um PTAM."""
    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    
    # Gerar token único
    token = str(uuid.uuid4()).replace('-', '')
    
    await db.ptam_documents.update_one(
        {"id": pid},
        {
            "$set": {
                "link_publico_token": token,
                "link_publico_ativo": True,
                "link_publico_criado_em": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    platform_url = "https://avalieimob-production.up.railway.app"  # Ajustar conforme variável de ambiente
    return {
        "ok": True,
        "token": token,
        "url": f"{platform_url}/laudo/{token}",
        "message": "Link de compartilhamento gerado com sucesso"
    }


@router.delete("/ptam/{pid}/compartilhar")
async def desativar_compartilhamento(
    pid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db)
):
    """Desativa o link de compartilhamento público."""
    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    
    await db.ptam_documents.update_one(
        {"id": pid},
        {
            "$set": {
                "link_publico_ativo": False,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"ok": True, "message": "Link de compartilhamento desativado"}


@router.get("/ptam/public/{token}")
async def get_ptam_publico(token: str, db=Depends(get_db)):
    """Retorna dados públicos de um PTAM para o portal do cliente (SEM autenticação)."""
    ptam = await db.ptam_documents.find_one({
        "link_publico_token": token,
        "link_publico_ativo": True
    })
    
    if not ptam:
        raise HTTPException(status_code=404, detail="Laudo não encontrado ou link inativo")
    
    # Incrementar contador de visualizações
    await db.ptam_documents.update_one(
        {"id": ptam["id"]},
        {"$inc": {"visualizacoes": 1}}
    )
    
    # Buscar perfil do avaliador
    perfil_avaliador = await db.perfil_avaliador.find_one({"user_id": ptam.get("user_id")})
    if perfil_avaliador:
        perfil_avaliador.pop("_id", None)
        perfil_avaliador.pop("user_id", None)
    
    # Dados públicos (NUNCA expor campos sensíveis)
    public_data = {
        "numero_ptam": ptam.get("numero_ptam"),
        "number": ptam.get("number"),
        "solicitante_nome": ptam.get("solicitante_nome"),
        "solicitante": ptam.get("solicitante"),
        "property_address": ptam.get("property_address"),
        "property_neighborhood": ptam.get("property_neighborhood"),
        "property_city": ptam.get("property_city"),
        "property_state": ptam.get("property_state"),
        "property_cep": ptam.get("property_cep"),
        "property_type": ptam.get("property_type"),
        "property_label": ptam.get("property_label"),
        "property_matricula": ptam.get("property_matricula"),
        "property_cartorio": ptam.get("property_cartorio"),
        "property_area_sqm": ptam.get("property_area_sqm"),
        "property_area_ha": ptam.get("property_area_ha"),
        "property_area_terreno": ptam.get("property_area_terreno"),
        "property_area_construida": ptam.get("property_area_construida"),
        "resultado_valor_total": ptam.get("resultado_valor_total"),
        "resultado_valor_unitario": ptam.get("resultado_valor_unitario"),
        "resultado_intervalo_inf": ptam.get("resultado_intervalo_inf"),
        "resultado_intervalo_sup": ptam.get("resultado_intervalo_sup"),
        "resultado_data_referencia": ptam.get("resultado_data_referencia"),
        "fundamentacao_grau": ptam.get("fundamentacao_grau"),
        "precisao_grau": ptam.get("precisao_grau"),
        "methodology": ptam.get("methodology"),
        "responsavel_nome": ptam.get("responsavel_nome"),
        "responsavel_creci": ptam.get("responsavel_creci"),
        "responsavel_cnai": ptam.get("responsavel_cnai"),
        "registro_profissional": ptam.get("registro_profissional"),
        "market_samples": ptam.get("market_samples", []),
        "calc_media_final": ptam.get("calc_media"),
        "calc_coef_variacao": ptam.get("calc_coef_variacao"),
        "calc_n_validas": ptam.get("calc_n_validas"),
        "created_at": ptam.get("created_at"),
        "updated_at": ptam.get("updated_at"),
        "lacrado": ptam.get("lacrado", False),
        "versao_lacrada": ptam.get("versao_lacrada"),
        "hash_lacrado": ptam.get("hash_lacrado"),
        "visualizacoes": (ptam.get("visualizacoes") or 0) + 1,
        "perfil_avaliador": perfil_avaliador,
        "conclusion_date": ptam.get("conclusion_date"),
        "conclusion_city": ptam.get("conclusion_city"),
        "total_indemnity": ptam.get("total_indemnity"),
        "total_indemnity_words": ptam.get("total_indemnity_words"),
    }
    
    return public_data


@router.get("/ptam/public/{token}/pdf")
async def download_ptam_publico_pdf(token: str, db=Depends(get_db)):
    """Gera e retorna PDF de um PTAM público (SEM autenticação)."""
    ptam = await db.ptam_documents.find_one({
        "link_publico_token": token,
        "link_publico_ativo": True
    })
    
    if not ptam:
        raise HTTPException(status_code=404, detail="Laudo não encontrado ou link inativo")
    
    user = await db.users.find_one({"id": ptam.get("user_id")})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Logo da empresa
    company_logo_id = user.get("company_logo")
    if company_logo_id:
        logo_doc = await db.images.find_one({"id": company_logo_id, "user_id": ptam.get("user_id")})
        if logo_doc:
            import base64 as _b64
            user["_company_logo_bytes"] = _b64.b64decode(logo_doc["data_b64"])
    
    try:
        # Buscar fotos do imóvel
        fotos_imovel = ptam.get("fotos_imovel") or []
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
        ptam["fotos_imovel"] = fotos_imovel
        
        # Buscar imagens das amostras
        market_samples = ptam.get("market_samples") or []
        for j, sample in enumerate(market_samples):
            foto_url = sample.get("foto") or sample.get("foto_url") or ""
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
        ptam["market_samples"] = market_samples
        
        # Buscar consultas CND
        cnd_consultas = []
        raw_consultas = await db.cnd_consultas.find({"ptam_id": ptam["id"]}).to_list(20)
        for c in raw_consultas:
            certs = await db.cnd_certidoes.find({"consulta_id": c.get("id", "")}).to_list(10)
            cnd_consultas.append({"consulta": c, "certidoes": certs})
        
        # Buscar perfil do avaliador
        perfil_avaliador = await db.perfil_avaliador.find_one({"user_id": ptam.get("user_id")})
        if perfil_avaliador:
            perfil_avaliador.pop("_id", None)
        
        pdf_bytes = generate_ptam_pdf(ptam, user, cnd_consultas=cnd_consultas, perfil_avaliador=perfil_avaliador)
    except Exception as e:
        logger.exception("PDF generation error (public)")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)[:200]}")
    
    if not pdf_bytes or len(pdf_bytes) < 100:
        raise HTTPException(status_code=500, detail="PDF gerado vazio ou corrompido")
    
    filename = f"PTAM_{ptam.get('number', 'sem-numero').replace('/', '-')}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/ptam/public/{token}/verificar")
async def verificar_integridade_publico(token: str, db=Depends(get_db)):
    """Verifica integridade de um laudo lacrado via token público."""
    ptam = await db.ptam_documents.find_one({
        "link_publico_token": token,
        "link_publico_ativo": True
    })
    
    if not ptam:
        raise HTTPException(status_code=404, detail="Laudo não encontrado ou link inativo")
    
    if not ptam.get("lacrado"):
        raise HTTPException(status_code=400, detail="Este laudo não possui versão lacrada")
    
    # Buscar versão lacrada mais recente
    versao_lacrada = await db.ptam_versions.find_one(
        {"ptam_id": ptam["id"], "tipo": "lacrado"},
        sort=[("numero_versao", -1)]
    )
    
    if not versao_lacrada or not versao_lacrada.get("snapshot"):
        raise HTTPException(status_code=400, detail="Versão lacrada não encontrada")
    
    hash_armazenado = versao_lacrada.get("hash_sha256", "")
    hash_calculado = _calculate_hash(versao_lacrada["snapshot"])
    
    return {
        "integro": hash_armazenado == hash_calculado,
        "hash_armazenado": hash_armazenado,
        "hash_calculado": hash_calculado,
        "numero_lacre": versao_lacrada.get("numero_lacre"),
        "data_lacre": versao_lacrada.get("created_at"),
        "versao_lacrada": ptam.get("versao_lacrada")
    }
