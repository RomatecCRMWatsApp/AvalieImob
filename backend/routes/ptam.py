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
from utils.ptam_status import calcular_status_ptam
from ptam_docx import generate_ptam_docx
from services.ptam_pdf_v2 import generate_ptam_pdf_v2
from services.integracoes_util import carregar_integracoes

router = APIRouter(tags=["ptam"])
logger = logging.getLogger("romatec")


async def _inject_brand(db, uid, doc):
    """Injeta o white-label do usuário no doc do PTAM antes de gerar o PDF:
      - _brand_logo_bytes: logo próprio (None = mantém o logo padrão AvalieImob)
      - _brand_primary/_brand_secondary: cores do tema, SÓ quando o usuário tem
        marca própria (use_default=False). Sem isso, o PDF sai no verde/dourado padrão.
    Nunca propaga erro (branding é opcional)."""
    try:
        from services import branding_repository as repo
        from services.branding_context import BrandContext
        branding = await repo.get_branding(db, uid)
        brand = BrandContext.from_branding(branding)
        doc["_brand_logo_bytes"] = brand.custom_logo_bytes()
        if not branding.use_default:
            r = branding.resolved()
            doc["_brand_primary"] = r.color_primary
            doc["_brand_secondary"] = r.color_secondary
    except Exception:
        logger.warning("Falha ao resolver marca (uid=%s)", uid, exc_info=False)
    return doc


class PtamEmailRequest(BaseModel):
    destinatario: str
    nome_cliente: Optional[str] = ""
    mensagem_extra: Optional[str] = ""


class LacrarVersaoRequest(BaseModel):
    observacao: Optional[str] = ""


# Campos ignorados no diff (metadados)
IGNORED_DIFF_FIELDS = {"id", "_id", "user_id", "created_at", "updated_at", "numero_ptam", "status_calculado"}


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


def _with_status_calculado(doc: dict) -> dict:
    """Serializa o doc e injeta o status automático (rascunho|concluido|assinado)."""
    d = serialize_doc(doc)
    d["status_calculado"] = calcular_status_ptam(d)
    return d


@router.get("/ptam", response_model=List[Ptam])
async def list_ptam(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    items = await db.ptam_documents.find({"user_id": uid}).sort("updated_at", -1).to_list(1000)
    return [Ptam(**_with_status_calculado(i)) for i in items]


@router.get("/ptam/{pid}", response_model=Ptam)
async def get_ptam(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    return Ptam(**_with_status_calculado(doc))


@router.post("/ptam", response_model=Ptam)
async def create_ptam(data: PtamBase, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    numero_ptam = await _next_ptam_numero(db)
    number = data.number or numero_ptam
    payload = data.model_dump()
    payload["numero_ptam"] = numero_ptam
    payload["number"] = number
    p = Ptam(user_id=uid, **payload)
    p.status_calculado = calcular_status_ptam(p.model_dump())
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

    # ── REGRA: editar um PTAM assinado invalida a assinatura ──────────────────
    # O PDF assinado deixa de corresponder ao conteúdo, então a assinatura é
    # removida, o status volta para Concluído/Rascunho e o botão volta a "Assinar".
    # Vale para qualquer tipo de imóvel (urbano ou rural).
    _was_signed = doc.get("icp_status") == "assinado" or doc.get("d4sign_status") == "assinado"
    if _was_signed:
        _SIG_FIELDS = {
            "d4sign_document_uuid", "d4sign_status", "d4sign_enviado_em", "d4sign_assinado_em",
            "d4sign_signatarios", "d4sign_pdf_assinado_url",
            "icp_status", "icp_signed_at", "icp_cert_id", "icp_titular", "icp_documento",
            "icp_emissor", "icp_hash", "icp_pdf_url", "icp_verificacao_url",
        }
        _META_FIELDS = {
            "updated_at", "created_at", "status_calculado", "concluido_em",
            "concluido_manual", "etapas_concluidas", "etapas_concluidas_em", "assinatura_invalidada_em",
            "link_publico_token", "link_publico_ativo", "link_publico_criado_em",
            "visualizacoes", "numero_versao", "versao_lacrada", "lacrado", "id",
            "impact_areas",  # estrutura recomputada no autosave — não é sinal de edição
        }

        def _norm(v):
            if v is None:
                return None
            if isinstance(v, str):
                s = v.strip()
                return s or None
            return v

        _conteudo_mudou = any(
            _norm(nv) != _norm(doc.get(k))
            for k, nv in updates.items()
            if k not in _SIG_FIELDS and k not in _META_FIELDS
        )
        if _conteudo_mudou:
            for _k in _SIG_FIELDS:
                updates[_k] = None
            updates["d4sign_signatarios"] = []
            updates["assinatura_invalidada_em"] = datetime.utcnow()
            logger.info("PTAM %s: assinatura invalidada por edição de conteúdo", pid)

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
    
    # Recalcula e persiste o status automático sobre o estado final mesclado.
    updates["status_calculado"] = calcular_status_ptam({**doc, **updates})

    # Atualizar documento
    await db.ptam_documents.update_one({"id": pid}, {"$set": updates})
    new_doc = await db.ptam_documents.find_one({"id": pid})
    return Ptam(**_with_status_calculado(new_doc))


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
                    _raw = base64.b64decode(img_doc["data_b64"])
                    # FIX 1: GPS + Data/Hora (cache > EXIF > OCR) — nunca omite no card.
                    try:
                        _gps, _dh = await _gps_data_foto(db, img_doc, _raw)
                    except Exception:
                        _gps, _dh = "", ""
                    _gps_prev = (foto.get("gps") if isinstance(foto, dict) else "") or ""
                    _dh_prev = (foto.get("data_hora") if isinstance(foto, dict) else "") or ""
                    fotos_imovel[i] = {
                        "image_id": image_id,
                        "url": url,
                        "_image_bytes": _raw,
                        "gps": _gps or _gps_prev,
                        "data_hora": _dh or _dh_prev,
                        "legenda": (foto.get("legenda") if isinstance(foto, dict) else "") or "",
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
        await _resolve_plantas_amostras(db, doc.get("market_samples"))

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
                    _raw = base64.b64decode(img_doc["data_b64"])
                    # FIX 1: GPS + Data/Hora (cache > EXIF > OCR) — nunca omite no card.
                    try:
                        _gps, _dh = await _gps_data_foto(db, img_doc, _raw)
                    except Exception:
                        _gps, _dh = "", ""
                    _gps_prev = (foto.get("gps") if isinstance(foto, dict) else "") or ""
                    _dh_prev = (foto.get("data_hora") if isinstance(foto, dict) else "") or ""
                    fotos_imovel[i] = {
                        "image_id": image_id,
                        "url": url,
                        "_image_bytes": _raw,
                        "gps": _gps or _gps_prev,
                        "data_hora": _dh or _dh_prev,
                        "legenda": (foto.get("legenda") if isinstance(foto, dict) else "") or "",
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
        await _resolve_plantas_amostras(db, doc.get("market_samples"))

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

        # ── Normalização para o layout v2 (sumário clicável + numeração real) ──
        # Documentos digitalizados: v2 lê "documentos_resolvidos".
        doc["documentos_resolvidos"] = [
            {
                "name": d.get("name") or d.get("tipo") or d.get("descricao") or "Documento",
                "_doc_bytes": d.get("_doc_bytes"),
                "content_type": d.get("content_type", "image/jpeg"),
            }
            for d in (doc.get("fotos_documentos") or [])
            if isinstance(d, dict) and d.get("_doc_bytes")
        ]
        # Documentos rurais (SIGEF, Memorial, CCIR, ITR, CAR) → "Documentos do Imóvel".
        await _merge_docs_rurais(db, doc, doc["documentos_resolvidos"])
        # Fotos do imóvel: garante dicts com legenda (v2 espera dict, não string).
        fotos_fix = []
        for i, f in enumerate(doc.get("fotos_imovel") or [], 1):
            if isinstance(f, dict):
                if not f.get("legenda"):
                    f["legenda"] = f.get("description") or f.get("descricao") or f"Foto {i}"
                fotos_fix.append(f)
            else:
                fotos_fix.append({"legenda": f"Foto {i}", "description": f"Foto {i}"})
        doc["fotos_imovel"] = fotos_fix
        doc["cnd_consultas"] = cnd_consultas  # disponível ao v2 (forward-compat)

        # Downscale das imagens (reduz drasticamente o tamanho do PDF).
        # PDFs e arquivos não-imagem passam intactos (downscale_image faz fallback).
        from services.img_util import downscale_image as _downscale

        def _ds(b):
            try:
                return _downscale(b) if b else b
            except Exception:
                return b

        for _f in (doc.get("fotos_imovel") or []):
            if isinstance(_f, dict) and _f.get("_image_bytes"):
                _f["_image_bytes"] = _ds(_f["_image_bytes"])
        for _s in (doc.get("market_samples") or []):
            if isinstance(_s, dict) and _s.get("_image_bytes"):
                _s["_image_bytes"] = _ds(_s["_image_bytes"])
        for _d in (doc.get("documentos_resolvidos") or []):
            if isinstance(_d, dict) and _d.get("_doc_bytes") and \
                    'pdf' not in (_d.get("content_type") or '').lower():
                _d["_doc_bytes"] = _ds(_d["_doc_bytes"])

        # Gerador v2: layout aprovado, com sumário numerado e clicável.
        await _attach_incra(db, doc)
        await _inject_brand(db, uid, doc)
        data = generate_ptam_pdf_v2(doc, perfil_avaliador)
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


def _map_ptam_to_spec_v2(doc: dict, perfil: dict | None) -> dict:
    """Traduz o documento real (ptam_documents) para o schema do gerador v2 (best-effort).
    Campos ausentes no banco viram placeholders no PDF (o gerador e defensivo)."""
    perfil = perfil or {}
    ptype = (doc.get("property_type") or "").upper() or None

    amostras = []
    for s in (doc.get("market_samples") or []):
        amostras.append({
            "endereco": s.get("address"),
            "tipo": "Consolidada" if s.get("tipo_amostra") == "consolidada" else "Oferta de Mercado",
            "tipo_tag": ptype,
            "area_terreno": s.get("area"),
            "valor_ofertado": s.get("value"),
            "valor_unitario_oferta": s.get("value_per_sqm"),
            "valor_unitario_tratado": s.get("value_per_sqm"),
            "fator_oferta": "",
            "fonte": s.get("source"),
            "data_coleta": s.get("collection_date"),
            "foto_url": s.get("_image_bytes"),
        })

    fotos = []
    for i, f in enumerate(doc.get("fotos_imovel") or [], 1):
        if isinstance(f, dict):
            fotos.append({
                "url": f.get("_image_bytes"),
                "legenda": f.get("description") or f.get("descricao") or f"Foto {i}",
                "ordem": i,
            })

    return {
        "id": doc.get("id"),
        "id_curto": str(doc.get("number") or ""),
        "data_laudo": doc.get("conclusion_date") or doc.get("vistoria_date"),
        "data_vistoria": doc.get("vistoria_date"),
        "finalidade": doc.get("finalidade") or "",
        "finalidade_texto": doc.get("finalidade_outros"),
        "grau_fundamentacao": doc.get("calc_grau_fundamentacao"),
        "grau_precisao": doc.get("grau_precisao"),
        "solicitante": {
            "nome": doc.get("solicitante_nome") or doc.get("solicitante"),
            "cpf_cnpj": doc.get("solicitante_cpf_cnpj"),
            "endereco": doc.get("solicitante_endereco"),
            "telefone": doc.get("solicitante_telefone"),
            "email": doc.get("solicitante_email"),
        },
        "imovel": {
            "endereco": doc.get("property_address"),
            "bairro": doc.get("property_neighborhood"),
            "municipio": doc.get("property_city"),
            "uf": doc.get("property_state"),
            "cep": doc.get("property_cep"),
            "matricula": doc.get("property_matricula"),
            "cartorio": doc.get("property_cartorio"),
            "tipo": doc.get("property_type"),
            "uso": doc.get("property_label"),
            "area_terreno": doc.get("imovel_area_terreno") or doc.get("property_area_sqm"),
            "area_construida": doc.get("imovel_area_construida"),
            "area_total": doc.get("imovel_area_a_considerar") or doc.get("area_total"),
        },
        "avaliador": {
            "nome": perfil.get("nome") or perfil.get("nome_completo"),
            "cnai": perfil.get("cnai"),
            "creci": perfil.get("creci"),
            "cft": perfil.get("cft"),
            "crea": perfil.get("crea"),
            "incra": perfil.get("incra"),
            "formacao": perfil.get("formacao"),
            "especializacao": perfil.get("especializacao"),
            "empresa": perfil.get("empresa"),
            "cnpj_empresa": perfil.get("cnpj_empresa"),
            "endereco": perfil.get("endereco"),
            "cep": perfil.get("cep"),
            "telefone": perfil.get("telefone"),
            "email": perfil.get("email"),
            "site": perfil.get("site"),
            "curriculo": perfil.get("curriculo"),
        },
        "metodologia": {"metodo_principal": doc.get("metodo_avaliacao")},
        "amostras": amostras,
        "resultado": {
            "metodo": doc.get("metodo_avaliacao"),
            "valor_unitario": doc.get("resultado_valor_unitario"),
            "area": doc.get("imovel_area_a_considerar") or doc.get("imovel_area_construida"),
            "valor_final": doc.get("resultado_valor_total"),
            "valor_extenso": doc.get("resultado_valor_extenso"),
            "data_base": doc.get("resultado_data_referencia") or doc.get("vistoria_date"),
        },
        "conclusao": {
            "texto": doc.get("conclusion_text"),
            "texto_conclusao": doc.get("conclusion_text"),
        },
        "fotos_imovel": fotos,
    }


async def _resolve_plantas_amostras(db, samples):
    """Resolve a planta baixa de cada amostra (id/URL -> bytes) in-place,
    gravando _planta_baixa_bytes. Mesma origem das fotos (db.images), então
    PDF (PNG 300 DPI convertido no upload) e imagens diretas funcionam igual."""
    for s in (samples or []):
        if not isinstance(s, dict):
            continue
        pb = s.get("planta_baixa") or s.get("planta_baixa_url") or ""
        if not pb:
            continue
        pid = str(pb).replace('/api/upload/image/', '').split('/')[-1]
        if len(pid) > 30 and '-' in pid:
            pimg = await db.images.find_one({"id": pid})
            if pimg and pimg.get("data_b64"):
                s["_planta_baixa_bytes"] = base64.b64decode(pimg["data_b64"])


async def _gps_data_foto(db, img_doc, raw_bytes):
    """(gps, data_hora) da foto: cache em db.images > EXIF > OCR.
    PERF: cacheia SEMPRE (mesmo sem achar GPS) e marca meta_ocr_done, para o OCR
    (lento) NÃO reprocessar a cada geração de PDF. Era o gargalo do Visualizar/PDF."""
    g = (img_doc.get("meta_gps") or "").strip()
    d = (img_doc.get("meta_data_hora") or "").strip()
    if g or d:
        return g, d
    # Já processado antes (inclusive sem GPS) → não reexecuta EXIF/OCR.
    if img_doc.get("meta_ocr_done"):
        return g, d
    try:
        from services.ptam_pdf_v2 import _exif_gps_data
        g, d = _exif_gps_data(raw_bytes)
    except Exception:
        g, d = "", ""
    if not g and not d:
        try:
            import asyncio as _aio
            from services.foto_ocr import extrair_gps_data_ocr
            g, d = await _aio.to_thread(extrair_gps_data_ocr, raw_bytes)
        except Exception:
            g, d = "", ""
    # Cacheia o resultado (inclusive vazio) + marca como processado.
    try:
        await db.images.update_one(
            {"id": img_doc.get("id")},
            {"$set": {"meta_gps": g, "meta_data_hora": d, "meta_ocr_done": True}},
        )
    except Exception:
        pass
    return g, d


# Grupos de documentos rurais que SEMPRE entram em "Documentos do Imóvel" (Anexo I.B).
# Centralizado: todas as rotas de PDF/preview chamam _merge_docs_rurais — não duplicar.
GRUPOS_DOCS_RURAIS = [
    ("doc_mapa_sigef", "Mapa Georreferenciado / Certificado SIGEF"),
    ("doc_memorial_descritivo", "Memorial Descritivo Topográfico / SIGEF"),
    ("doc_ccir", "CCIR — Certificado de Cadastro de Imóvel Rural"),
    ("doc_itr", "ITR — Imposto Territorial Rural"),
    ("doc_car", "CAR — Cadastro Ambiental Rural"),
]


_RURAL_TYPES_PTAM = {'rural', 'fazenda', 'sitio', 'chacara', 'terreno_rural', 'gleba', 'area_rural'}


async def _attach_incra(db, doc):
    """Injeta a tabela INCRA em doc['incra_tabela'] quando o imóvel é rural.
    Preferência: (1) snapshot salvo no PTAM → (2) tabela escolhida por id →
    (3) automática por município (property_city) → região (regiao_incra) → mais recente."""
    if str((doc or {}).get('property_type') or '').strip().lower() not in _RURAL_TYPES_PTAM:
        return
    # (1) Snapshot explícito salvo no PTAM (vigência congelada na data da avaliação).
    snap = doc.get('tabela_incra_snapshot')
    if isinstance(snap, dict) and snap.get('faixas'):
        doc['incra_tabela'] = snap
        return
    # (2) Tabela escolhida pelo avaliador (por id) — busca atual no banco.
    tab_id = doc.get('tabela_incra_id')
    if tab_id:
        try:
            tab = await db.incra_tabelas.find_one({"id": tab_id})
        except Exception:
            tab = None
        if tab:
            tab.pop("_id", None)
            doc['incra_tabela'] = tab
            return
    # (3) Seleção automática (comportamento legado).
    municipio = str(doc.get('property_city') or '').strip()
    regiao = str(doc.get('regiao_incra') or '').strip()
    queries = []
    if municipio:
        _rx = {"$regex": f"^{municipio}$", "$options": "i"}
        queries.append({"ativo": True, "$or": [{"municipio": _rx}, {"municipios": _rx}]})
    if regiao:
        queries.append({"ativo": True, "regiao": {"$regex": f"^{regiao}$", "$options": "i"}})
    queries.append({"ativo": True})
    for q in queries:
        try:
            tab = await db.incra_tabelas.find_one(q, sort=[("ano", -1), ("mes", -1)])
        except Exception:
            tab = None
        if tab:
            tab.pop("_id", None)
            doc['incra_tabela'] = tab
            return


def _incra_match_faixa(faixas: list, media_ha: float):
    """Índice da faixa que contém media_ha (vr_min..vr_max); senão a mais próxima.
    Retorna (idx, dentro). Espelha utils/incraFaixa.js do frontend e o PDF."""
    lista = faixas or []
    m = float(media_ha or 0)
    melhor_idx, melhor_dist = 0, float("inf")
    for i, f in enumerate(lista):
        vmin = float((f or {}).get("vr_min") or 0)
        vmax = float((f or {}).get("vr_max") or 0)
        if vmin <= m <= vmax:
            return i, True
        dist = min(abs(m - vmin), abs(m - vmax))
        if dist < melhor_dist:
            melhor_dist, melhor_idx = dist, i
    return melhor_idx, False


def _build_incra_snapshot(tab: dict, media_ha: float) -> dict:
    """Monta o snapshot da tabela INCRA congelando vigência/valores + tipologia aplicada."""
    faixas = tab.get("faixas") or []
    idx, dentro = _incra_match_faixa(faixas, media_ha)
    faixa_sel = faixas[idx] if faixas else {}
    return {
        "tabela_id": tab.get("id"),
        "regiao": tab.get("regiao"),
        "municipio": tab.get("municipio"),
        "municipios": tab.get("municipios") or [],
        "polo_regional": tab.get("polo_regional"),
        "fonte": tab.get("fonte"),
        "norma": tab.get("norma"),
        "vigencia": tab.get("vigencia"),
        "ano": tab.get("ano"),
        "mes": tab.get("mes"),
        "faixas": faixas,
        "fatores": tab.get("fatores") or [],
        "notas": tab.get("notas"),
        "tipologia_aplicada": (faixa_sel or {}).get("faixa"),
        "valor_referencia_ha": (faixa_sel or {}).get("vr_medio"),
        "media_avaliacao_ha": round(float(media_ha or 0), 2),
        "dentro_faixa": dentro,
        "snapshot_em": datetime.utcnow().isoformat(),
    }


class VincularTabelaIncraBody(BaseModel):
    tabela_incra_id: str
    usar_no_laudo: bool = True


@router.patch("/ptam/{pid}/tabela-incra")
async def vincular_tabela_incra(
    pid: str,
    body: VincularTabelaIncraBody,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Vincula uma tabela INCRA ao PTAM e congela um snapshot dos valores.
    O valor de referência usa a média ponderada do laudo (R$/m² → R$/ha)."""
    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")

    tab = await db.incra_tabelas.find_one({"id": body.tabela_incra_id})
    if not tab:
        raise HTTPException(status_code=404, detail="Tabela INCRA não encontrada")
    tab.pop("_id", None)

    try:
        media_m2 = float(ptam.get("resultado_valor_unitario") or ptam.get("ponderancia_media") or 0)
    except (TypeError, ValueError):
        media_m2 = 0.0
    media_ha = media_m2 * 10000.0

    snapshot = _build_incra_snapshot(tab, media_ha)
    updates = {
        "tabela_incra_id": body.tabela_incra_id,
        "tabela_incra_snapshot": snapshot,
        "incra_incluir_laudo": bool(body.usar_no_laudo),
        "updated_at": datetime.utcnow(),
    }
    await db.ptam_documents.update_one({"id": pid}, {"$set": updates})
    return {"ok": True, "tabela_incra_id": body.tabela_incra_id, "snapshot": snapshot}


async def _merge_docs_rurais(db, doc, docs_res):
    """Anexa os documentos rurais (SIGEF, Memorial, CCIR, ITR, CAR) à lista
    'Documentos do Imóvel' do laudo. Fonte única — chamada por toda rota que
    monta documentos_resolvidos, para a regra nunca mais divergir/sumir."""
    for campo, rotulo in GRUPOS_DOCS_RURAIS:
        arquivos = doc.get(campo) or []
        total = len(arquivos)
        for k, item in enumerate(arquivos, 1):
            if isinstance(item, dict):
                url = item.get("url") or item.get("image_id") or item.get("id", "")
            else:
                url = str(item)
            rid = str(url).replace("/api/upload/image/", "").strip("/").split("/")[-1]
            if len(rid) <= 30 or "-" not in rid:
                continue
            rimg = await db.images.find_one({"id": rid})
            if rimg and rimg.get("data_b64"):
                nome = rotulo if total <= 1 else f"{rotulo} ({k}/{total})"
                docs_res.append({
                    "name": nome,
                    "_doc_bytes": base64.b64decode(rimg["data_b64"]),
                    "content_type": rimg.get("content_type", "image/jpeg"),
                })
    return docs_res


@router.get("/ptam/{pid}/pdf-v2")
async def download_ptam_pdf_v2(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Gera o PDF do PTAM no novo layout (spec 1.0). Rota paralela — nao substitui /pdf."""
    doc = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    try:
        # Resolve fotos do imovel (IDs -> bytes)
        for foto in (doc.get("fotos_imovel") or []):
            if isinstance(foto, dict):
                url = foto.get("url") or foto.get("image_id", "")
            else:
                url = str(foto)
            image_id = str(url).replace('/api/upload/image/', '').split('/')[-1]
            if len(image_id) > 30 and '-' in image_id:
                img_doc = await db.images.find_one({"id": image_id})
                if img_doc and img_doc.get("data_b64"):
                    if isinstance(foto, dict):
                        foto["_image_bytes"] = base64.b64decode(img_doc["data_b64"])
        # Normaliza fotos_imovel que sao strings para dicts com bytes
        fotos_norm = []
        for i, foto in enumerate(doc.get("fotos_imovel") or [], 1):
            if isinstance(foto, dict):
                if not foto.get("legenda"):
                    foto["legenda"] = foto.get("description") or foto.get("caption") or f"Foto {i}"
                fotos_norm.append(foto)
            else:
                image_id = str(foto).replace('/api/upload/image/', '').split('/')[-1]
                entry = {"legenda": f"Foto {i}", "description": f"Foto {i}"}
                if len(image_id) > 30 and '-' in image_id:
                    img_doc = await db.images.find_one({"id": image_id})
                    if img_doc and img_doc.get("data_b64"):
                        raw = base64.b64decode(img_doc["data_b64"])
                        if img_doc.get("filename"):
                            entry["legenda"] = img_doc["filename"]
                        g, d = await _gps_data_foto(db, img_doc, raw)
                        if g:
                            entry["gps"] = g
                        if d:
                            entry["data_hora"] = d
                        from services.img_util import downscale_image
                        entry["_image_bytes"] = downscale_image(raw)
                fotos_norm.append(entry)
        doc["fotos_imovel"] = fotos_norm
        # Resolve fotos das amostras (IDs -> bytes)
        for sample in (doc.get("market_samples") or []):
            foto_url = sample.get("foto") or sample.get("foto_url") or ""
            sample_image_id = str(foto_url).replace('/api/upload/image/', '').split('/')[-1]
            if len(sample_image_id) > 30 and '-' in sample_image_id:
                simg = await db.images.find_one({"id": sample_image_id})
                if simg and simg.get("data_b64"):
                    sample["_image_bytes"] = base64.b64decode(simg["data_b64"])
        await _resolve_plantas_amostras(db, doc.get("market_samples"))
        # Resolve documentos digitalizados (fotos_documentos: IDs -> bytes + nome)
        docs_resolvidos = []
        for kdoc, ditem in enumerate(doc.get("fotos_documentos") or [], 1):
            if isinstance(ditem, dict):
                durl = ditem.get("url") or ditem.get("doc_id") or ditem.get("image_id", "")
                dnome = ditem.get("name") or ditem.get("tipo") or ditem.get("descricao")
            else:
                durl = str(ditem)
                dnome = None
            did = str(durl).replace('/api/upload/image/', '').split('/')[-1]
            if len(did) > 30 and '-' in did:
                dimg = await db.images.find_one({"id": did})
                if dimg and dimg.get("data_b64"):
                    docs_resolvidos.append({
                        "name": dnome or dimg.get("filename") or f"Documento {kdoc}",
                        "_doc_bytes": base64.b64decode(dimg["data_b64"]),
                        "content_type": dimg.get("content_type", "image/jpeg"),
                    })
        # Documentos rurais (SIGEF, Memorial, CCIR, ITR, CAR) → "Documentos do Imóvel".
        await _merge_docs_rurais(db, doc, docs_resolvidos)
        doc["documentos_resolvidos"] = docs_resolvidos
        perfil = await db.perfil_avaliador.find_one({"user_id": uid})
        if perfil:
            perfil.pop("_id", None)
        await _attach_incra(db, doc)
        await _inject_brand(db, uid, doc)
        data = generate_ptam_pdf_v2(doc, perfil)
    except Exception as e:
        logger.exception("PDF v2 generation error")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF v2: {str(e)[:200]}")
    if not data or not data.startswith(b'%PDF-'):
        raise HTTPException(status_code=500, detail="PDF v2 inválido")
    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename = f"PTAM_{doc.get('number', 'sem-numero')}_v2_{date_str}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


@router.post("/ptam/preview-pdf")
async def preview_ptam_pdf(body: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Gera PDF de preview (layout v2) a partir de dados parciais do formulario.
    NAO salva nada no banco — apenas renderiza e devolve inline."""
    doc = dict(body or {})
    try:
        # Fotos do imovel (IDs -> bytes + legenda)
        fotos_norm = []
        for i, foto in enumerate(doc.get("fotos_imovel") or [], 1):
            if isinstance(foto, dict):
                # Objeto {image_id, legenda} (PhotoGrid): resolve os bytes da imagem.
                if not foto.get("_image_bytes"):
                    _fid = str(foto.get("image_id") or foto.get("url") or "").replace('/api/upload/image/', '').split('/')[-1]
                    if len(_fid) > 30 and '-' in _fid:
                        _fimg = await db.images.find_one({"id": _fid})
                        if _fimg and _fimg.get("data_b64"):
                            foto["_image_bytes"] = base64.b64decode(_fimg["data_b64"])
                if not foto.get("legenda"):
                    foto["legenda"] = foto.get("description") or foto.get("caption") or f"Foto {i}"
                fotos_norm.append(foto)
                continue
            image_id = str(foto).replace('/api/upload/image/', '').split('/')[-1]
            entry = {"legenda": f"Foto {i}", "description": f"Foto {i}"}
            if len(image_id) > 30 and '-' in image_id:
                img = await db.images.find_one({"id": image_id})
                if img and img.get("data_b64"):
                    entry["_image_bytes"] = base64.b64decode(img["data_b64"])
                    if img.get("filename"):
                        entry["legenda"] = img["filename"]
            fotos_norm.append(entry)
        doc["fotos_imovel"] = fotos_norm
        # Fotos das amostras
        for s in (doc.get("market_samples") or []):
            fu = s.get("foto") or s.get("foto_url") or ""
            sid = str(fu).replace('/api/upload/image/', '').split('/')[-1]
            if len(sid) > 30 and '-' in sid:
                simg = await db.images.find_one({"id": sid})
                if simg and simg.get("data_b64"):
                    s["_image_bytes"] = base64.b64decode(simg["data_b64"])
        await _resolve_plantas_amostras(db, doc.get("market_samples"))
        # Documentos digitalizados
        docs_res = []
        for kd, di in enumerate(doc.get("fotos_documentos") or [], 1):
            du = (di.get("url") or di.get("doc_id") or di.get("image_id", "")) if isinstance(di, dict) else str(di)
            dn = (di.get("name") or di.get("tipo")) if isinstance(di, dict) else None
            did = str(du).replace('/api/upload/image/', '').split('/')[-1]
            if len(did) > 30 and '-' in did:
                dimg = await db.images.find_one({"id": did})
                if dimg and dimg.get("data_b64"):
                    docs_res.append({
                        "name": dn or dimg.get("filename") or f"Documento {kd}",
                        "_doc_bytes": base64.b64decode(dimg["data_b64"]),
                        "content_type": dimg.get("content_type", "image/jpeg"),
                    })
        await _merge_docs_rurais(db, doc, docs_res)
        doc["documentos_resolvidos"] = docs_res
        perfil = await db.perfil_avaliador.find_one({"user_id": uid})
        if perfil:
            perfil.pop("_id", None)
        await _attach_incra(db, doc)
        await _inject_brand(db, uid, doc)
        data = generate_ptam_pdf_v2(doc, perfil)
    except Exception as e:
        logger.exception("PTAM preview error")
        raise HTTPException(status_code=500, detail=f"Erro no preview: {str(e)[:200]}")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=preview.pdf", "Cache-Control": "no-store"},
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

        # Modelo único: e-mail também usa o gerador canônico v2.
        from routes.assinatura import _resolve_ptam_assets
        await _attach_incra(db, doc)
        await _resolve_ptam_assets(db, doc)
        await _inject_brand(db, uid, doc)
        pdf_bytes = generate_ptam_pdf_v2(doc, perfil_avaliador_email)
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

    # Se o laudo está assinado com ICP-Brasil, o link público serve o PDF
    # ASSINADO (completo, com carimbo) em vez de regerar a versão sem assinatura.
    if ptam.get("icp_status") == "assinado":
        try:
            from routes.assinatura import _load_assinatura_bytes
            _signed, _ = await _load_assinatura_bytes(db, "ptam", ptam.get("id"), "v2")
        except Exception:
            _signed = None
        if _signed and len(_signed) > 100:
            _fn = f"PTAM_{ptam.get('number', 'sem-numero').replace('/', '-')}_ASSINADO.pdf"
            return Response(
                content=_signed,
                media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="{_fn}"', "Cache-Control": "no-store"},
            )

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
        
        # Modelo único: link público também usa o gerador canônico v2.
        from routes.assinatura import _resolve_ptam_assets
        await _attach_incra(db, ptam)
        await _resolve_ptam_assets(db, ptam)
        await _inject_brand(db, ptam.get("user_id"), ptam)
        pdf_bytes = generate_ptam_pdf_v2(ptam, perfil_avaliador)
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


# ════════════════════════════════════════════════════════════════════════════
# CLONAR PTAM — duplica laudo com novo número e status Rascunho
# ════════════════════════════════════════════════════════════════════════════

@router.post("/ptam/{pid}/clonar", response_model=Ptam)
async def clonar_ptam(
    pid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Duplica um PTAM mantendo todos os dados, com novo número e status Rascunho.
    Limpa campos de assinatura, lacre e link público — o clone começa do zero
    nessas dimensões.
    """
    original = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not original:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")

    # Novo número
    novo_numero = await _next_ptam_numero(db)

    # Copia limpando metadados e estados de assinatura/lacre/link
    clone = {k: v for k, v in original.items() if not k.startswith("_")}
    clone.pop("id", None)
    clone["id"] = str(uuid.uuid4())
    clone["numero_ptam"] = novo_numero
    clone["number"] = novo_numero
    clone["status"] = "Rascunho"
    clone["created_at"] = datetime.utcnow()
    clone["updated_at"] = datetime.utcnow()

    # Limpar campos de assinatura/lacre/link (clone começa "limpo")
    campos_a_limpar = [
        "lacrado", "versao_lacrada", "hash_lacrado",
        "link_publico", "link_publico_token", "link_publico_ativo",
        "link_publico_criado_em", "visualizacoes",
        "d4sign_document_uuid", "d4sign_status", "d4sign_enviado_em",
        "d4sign_assinado_em", "d4sign_signatarios", "d4sign_pdf_assinado_url",
        "icp_status", "icp_signed_at", "icp_cert_id", "icp_titular",
        "icp_documento", "icp_emissor", "icp_hash", "icp_pdf_url",
        "icp_verificacao_url",
        "recibo_emitido", "recibo_emitido_em", "recibo_pdf_url",
    ]
    for campo in campos_a_limpar:
        clone.pop(campo, None)

    await db.ptam_documents.insert_one(clone)
    return Ptam(**serialize_doc(clone))


# ════════════════════════════════════════════════════════════════════════════
# RECIBO DE HONORÁRIOS — geração e download
# ════════════════════════════════════════════════════════════════════════════

class GerarReciboRequest(BaseModel):
    valor_honorarios: float
    forma_pagamento: Optional[str] = "PIX"
    data_pagamento: Optional[str] = None  # ISO date


@router.post("/ptam/{pid}/recibo")
async def gerar_recibo_ptam(
    pid: str,
    body: GerarReciboRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera recibo de honorários do laudo (PDF) e marca como emitido."""
    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")

    if body.valor_honorarios <= 0:
        raise HTTPException(status_code=400, detail="Valor de honorários deve ser positivo")

    # Gerador de recibo — usa o inline (assinatura ptam=/valor=/forma_pagamento=/data_pagamento=).
    # NAO usar pdf.recibo_pdf aqui: ele tem assinatura diferente (recibo=dict) e causava TypeError.
    from services.recibo_zayra import gerar_recibo_pdf

    user = await db.users.find_one({"id": uid}) or {}
    perfil = await db.perfis_avaliador.find_one({"user_id": uid}) or {}

    pdf_bytes = gerar_recibo_pdf(
        ptam=ptam,
        user=user,
        perfil=perfil,
        valor=body.valor_honorarios,
        forma_pagamento=body.forma_pagamento or "PIX",
        data_pagamento=body.data_pagamento,
    )

    # Salvar
    import uuid as _uuid
    recibo_id = str(_uuid.uuid4())
    await db.recibos_ptam.insert_one({
        "id": recibo_id,
        "ptam_id": pid,
        "user_id": uid,
        "valor": body.valor_honorarios,
        "forma_pagamento": body.forma_pagamento,
        "content": pdf_bytes,
        "created_at": datetime.utcnow(),
    })

    # Marcar PTAM
    await db.ptam_documents.update_one(
        {"id": pid},
        {"$set": {
            "honorarios": body.valor_honorarios,
            "recibo_emitido": True,
            "recibo_emitido_em": datetime.utcnow(),
            "recibo_pdf_url": f"/api/ptam/{pid}/recibo",
            "updated_at": datetime.utcnow(),
        }},
    )

    return {
        "ok": True,
        "recibo_id": recibo_id,
        "download_url": f"/api/ptam/{pid}/recibo",
    }


@router.get("/ptam/{pid}/recibo")
async def download_recibo(
    pid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")
    recibo = await db.recibos_ptam.find_one(
        {"ptam_id": pid, "user_id": uid},
        sort=[("created_at", -1)],
    )
    if not recibo or not recibo.get("content"):
        raise HTTPException(status_code=404, detail="Recibo ainda não gerado")

    numero = ptam.get("numero_ptam") or pid
    filename = f"RECIBO_PTAM_{numero}.pdf"
    return Response(
        content=recibo["content"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ════════════════════════════════════════════════════════════════════════════
# TELEGRAM — envio do PDF do laudo via bot configurado
# ════════════════════════════════════════════════════════════════════════════

class TelegramSendRequest(BaseModel):
    chat_id: Optional[str] = None  # se vazio, usa o chat_id_default do perfil
    legenda: Optional[str] = ""


async def _melhor_pdf_ptam(db, ptam: dict) -> tuple[bytes, str]:
    """Retorna (pdf_bytes, nome_arquivo) preferindo a versão assinada mais
    recente: ICP > D4Sign > PDF original."""
    pid = ptam["id"]
    nome_arquivo = f"PTAM_{ptam.get('numero_ptam', pid)}.pdf"

    if ptam.get("icp_status") == "assinado":
        ass = await db["assinaturas_pdf"].find_one(
            {"doc_tipo": "ptam", "doc_id": pid, "metodo": "icp"}
        )
        if ass and ass.get("content"):
            return ass["content"], nome_arquivo.replace(".pdf", "_ASSINADO_ICP.pdf")

    if ptam.get("d4sign_status") == "assinado":
        ass = await db["assinaturas_pdf"].find_one({"doc_tipo": "ptam", "doc_id": pid})
        if ass and ass.get("content"):
            return ass["content"], nome_arquivo.replace(".pdf", "_ASSINADO.pdf")

    try:
        # Resolve assets (fotos do imovel, amostras, documentos) e usa layout v2 aprovado
        fotos_norm = []
        for i, foto in enumerate(ptam.get("fotos_imovel") or [], 1):
            if isinstance(foto, dict):
                if not foto.get("legenda"):
                    foto["legenda"] = foto.get("description") or foto.get("caption") or f"Foto {i}"
                fotos_norm.append(foto)
                continue
            image_id = str(foto).replace('/api/upload/image/', '').split('/')[-1]
            entry = {"legenda": f"Foto {i}", "description": f"Foto {i}"}
            if len(image_id) > 30 and '-' in image_id:
                img = await db.images.find_one({"id": image_id})
                if img and img.get("data_b64"):
                    entry["_image_bytes"] = base64.b64decode(img["data_b64"])
                    if img.get("filename"):
                        entry["legenda"] = img["filename"]
            fotos_norm.append(entry)
        ptam["fotos_imovel"] = fotos_norm
        for s in (ptam.get("market_samples") or []):
            fu = s.get("foto") or s.get("foto_url") or ""
            sid = str(fu).replace('/api/upload/image/', '').split('/')[-1]
            if len(sid) > 30 and '-' in sid:
                simg = await db.images.find_one({"id": sid})
                if simg and simg.get("data_b64"):
                    s["_image_bytes"] = base64.b64decode(simg["data_b64"])
        await _resolve_plantas_amostras(db, ptam.get("market_samples"))
        docs_res = []
        for kd, di in enumerate(ptam.get("fotos_documentos") or [], 1):
            du = (di.get("url") or di.get("doc_id") or di.get("image_id", "")) if isinstance(di, dict) else str(di)
            dn = (di.get("name") or di.get("tipo")) if isinstance(di, dict) else None
            did = str(du).replace('/api/upload/image/', '').split('/')[-1]
            if len(did) > 30 and '-' in did:
                dimg = await db.images.find_one({"id": did})
                if dimg and dimg.get("data_b64"):
                    docs_res.append({
                        "name": dn or dimg.get("filename") or f"Documento {kd}",
                        "_doc_bytes": base64.b64decode(dimg["data_b64"]),
                        "content_type": dimg.get("content_type", "image/jpeg"),
                    })
        await _merge_docs_rurais(db, ptam, docs_res)
        ptam["documentos_resolvidos"] = docs_res
        perfil = await db.perfil_avaliador.find_one({"user_id": ptam.get("user_id")})
        if perfil:
            perfil.pop("_id", None)
        await _attach_incra(db, ptam)
        pdf_bytes = generate_ptam_pdf_v2(ptam, perfil)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {e}")
    return pdf_bytes, nome_arquivo


@router.post("/ptam/{pid}/telegram")
async def enviar_telegram(
    pid: str,
    body: TelegramSendRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Envia o PDF do PTAM via bot Telegram do USUÁRIO (multi-tenant).
    Requer que o usuário tenha telegram_bot_token configurado em /api/integracoes.
    Se chat_id vazio, usa o telegram_chat_id_default do perfil.
    """
    import httpx as _httpx

    cfg = await carregar_integracoes(db, uid)
    bot_token = (cfg or {}).get("telegram_bot_token")
    if not bot_token:
        raise HTTPException(
            status_code=400,
            detail="Telegram não configurado. Cadastre seu bot_token em Configurações → Integrações.",
        )

    chat_id = (body.chat_id or "").strip() or (cfg or {}).get("telegram_chat_id_default")
    if not chat_id:
        raise HTTPException(
            status_code=400,
            detail="Informe um chat_id ou configure um padrão em Configurações → Integrações.",
        )

    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")

    pdf_bytes, nome_arquivo = await _melhor_pdf_ptam(db, ptam)
    legenda = body.legenda or f"Segue o laudo PTAM {ptam.get('numero_ptam', '')}"

    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    try:
        async with _httpx.AsyncClient(timeout=60) as client:
            files = {"document": (nome_arquivo, pdf_bytes, "application/pdf")}
            data = {"chat_id": chat_id, "caption": legenda}
            r = await client.post(url, data=data, files=files)
            if r.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Telegram erro {r.status_code}: {r.text[:200]}",
                )
            return {"ok": True, "telegram_response": r.json()}
    except _httpx.HTTPError as e:
        logger.error("Erro ao enviar Telegram: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro de rede ao enviar Telegram: {e}")


# ════════════════════════════════════════════════════════════════════════════
# WHATSAPP via Z-API — usa credenciais do usuário (multi-tenant SaaS)
# ════════════════════════════════════════════════════════════════════════════

class WhatsAppSendRequest(BaseModel):
    phone: str  # com DDI+DDD (ex: 5599991234567 ou 99991234567)
    legenda: Optional[str] = ""


@router.post("/ptam/{pid}/whatsapp")
async def enviar_whatsapp(
    pid: str,
    body: WhatsAppSendRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Envia o PDF do PTAM via WhatsApp do USUÁRIO (multi-tenant).
    Roteia automaticamente entre Z-API e Meta Cloud API conforme a preferência
    'whatsapp_provider' configurada em /api/integracoes.
    """
    from services import zapi_service
    from services import meta_whatsapp_service as meta

    cfg = await carregar_integracoes(db, uid)
    if not cfg:
        raise HTTPException(
            status_code=400,
            detail="Nenhum provedor WhatsApp configurado. Cadastre Z-API ou Meta em Configurações → Integrações.",
        )

    provider = (cfg.get("whatsapp_provider") or "zapi").lower()

    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")

    pdf_bytes, nome_arquivo = await _melhor_pdf_ptam(db, ptam)
    legenda = body.legenda or f"Segue o laudo PTAM {ptam.get('numero_ptam', '')}"

    if provider == "meta":
        if not cfg.get("meta_phone_number_id") or not cfg.get("meta_access_token"):
            raise HTTPException(
                status_code=400,
                detail="Meta WhatsApp não configurada. Cadastre em Configurações → Integrações.",
            )
        try:
            resp = await meta.send_pdf(
                phone_number_id=cfg["meta_phone_number_id"],
                access_token=cfg["meta_access_token"],
                phone=body.phone,
                pdf_bytes=pdf_bytes,
                filename=nome_arquivo,
                caption=legenda,
            )
            return {"ok": True, "provider": "meta", "response": resp}
        except Exception as e:
            logger.error("Erro Meta WhatsApp: %s", e)
            raise HTTPException(status_code=502, detail=f"Erro Meta WhatsApp: {e}")

    # Default: Z-API
    if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(
            status_code=400,
            detail="Z-API não configurada. Cadastre em Configurações → Integrações.",
        )
    try:
        resp = await zapi_service.send_document_pdf(
            instance_id=cfg["zapi_instance_id"],
            token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"),
            phone=body.phone,
            pdf_bytes=pdf_bytes,
            filename=nome_arquivo,
            caption=legenda,
        )
        return {"ok": True, "provider": "zapi", "response": resp}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Erro Z-API: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro Z-API: {e}")


@router.post("/ptam/{pid}/whatsapp-link")
async def enviar_whatsapp_link(
    pid: str,
    body: WhatsAppSendRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Envia uma MENSAGEM DE TEXTO com o link público do laudo via Z-API
    (não anexa o PDF — manda só a mensagem com o link)."""
    import os as _os
    from services import zapi_service

    cfg = await carregar_integracoes(db, uid)
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(status_code=400, detail="Z-API não configurada. Cadastre em Configurações → Integrações.")

    ptam = await db.ptam_documents.find_one({"id": pid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")

    token = ptam.get("link_publico_token")
    if not token or not ptam.get("link_publico_ativo"):
        raise HTTPException(status_code=400, detail="Gere/ative o link público do laudo antes de enviar.")

    base = _os.getenv("PUBLIC_BASE_URL", "https://www.romatecavalieimob.com.br").rstrip("/")
    link = f"{base}/laudo/{token}"
    numero = ptam.get("numero_ptam") or ptam.get("number") or ""
    denom = ptam.get("property_label") or ptam.get("denominacao") or ptam.get("property_address") or "Imóvel"
    msg = body.legenda or (
        f"Prezado(a),\n\n"
        f"É com satisfação que comunicamos a *conclusão do Laudo de Avaliação — PTAM nº {numero}*, "
        f"referente ao imóvel *{denom}*, elaborado em conformidade com a ABNT NBR 14.653.\n\n"
        f"O documento completo está disponível para consulta no link abaixo:\n{link}\n\n"
        f"Agradecemos a confiança e a preferência por nossos serviços e permanecemos à "
        f"disposição para quaisquer esclarecimentos.\n\n"
        f"Atenciosamente,\n*Romatec Consultoria Total — AvalieImob*"
    )
    try:
        resp = await zapi_service.send_text(
            instance_id=cfg["zapi_instance_id"],
            token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"),
            phone=body.phone,
            message=msg,
        )
        return {"ok": True, "provider": "zapi", "response": resp}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Erro Z-API (link): %s", e)
        raise HTTPException(status_code=502, detail=f"Erro Z-API: {e}")
