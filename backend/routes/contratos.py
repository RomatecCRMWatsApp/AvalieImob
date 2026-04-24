# @module routes.contratos — CRUD Contratos Imobiliarios, versionamento com diff/SHA-256
import hashlib
import io
import json
import logging
import uuid as _uuid_module
from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pymongo import ReturnDocument
from pydantic import BaseModel

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.contrato import (
    ContratoBase, Contrato, ContratoVersion, ContratoVersionDiff,
    TIPOS_CONTRATO,
)
from services.contrato_ia_service import (
    gerar_clausulas_contrato,
    gerar_clausulas_corretor,
    validar_alertas_juridicos,
    calcular_penalidades,
    gerar_checklist,
)

router = APIRouter(tags=["contratos"])
logger = logging.getLogger("romatec")


# ============================================================
# CAMPOS IGNORADOS NO DIFF (metadados)
# ============================================================
IGNORED_DIFF_FIELDS = {"id", "_id", "user_id", "created_at", "updated_at", "numero_contrato"}


# ============================================================
# HELPERS
# ============================================================

def _calculate_hash(data: dict) -> str:
    conteudo = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(conteudo.encode()).hexdigest()


def _deep_diff(old: Any, new: Any, path: str = "") -> List[ContratoVersionDiff]:
    diffs = []
    if isinstance(old, dict) and isinstance(new, dict):
        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            if key in IGNORED_DIFF_FIELDS:
                continue
            full_path = f"{path}.{key}" if path else key
            diffs.extend(_deep_diff(old.get(key), new.get(key), full_path))
    elif isinstance(old, list) and isinstance(new, list):
        max_len = max(len(old), len(new))
        for i in range(max_len):
            full_path = f"{path}[{i}]"
            old_val = old[i] if i < len(old) else None
            new_val = new[i] if i < len(new) else None
            diffs.extend(_deep_diff(old_val, new_val, full_path))
    else:
        if old != new:
            old_display = "[alterado]" if isinstance(old, str) and len(old) > 100 else old
            new_display = "[alterado]" if isinstance(new, str) and len(new) > 100 else new
            diffs.append(ContratoVersionDiff(
                campo=path,
                valor_anterior=old_display if old not in ("", None) else None,
                valor_novo=new_display if new not in ("", None) else None,
            ))
    return diffs


async def _create_version(
    db,
    contrato_id: str,
    user_id: str,
    old_doc: dict,
    new_data: dict,
    ip: str = None,
    user_agent: str = None,
    observacao: str = None,
    snapshot: dict = None,
) -> Optional[ContratoVersion]:
    diffs = _deep_diff(old_doc, new_data)
    if not diffs:
        return None

    last_version = await db.contrato_versions.find_one(
        {"contrato_id": contrato_id},
        sort=[("numero_versao", -1)],
    )
    numero_versao = (last_version["numero_versao"] + 1) if last_version else 1

    hash_sha256 = _calculate_hash(new_data)
    if last_version and last_version.get("hash_sha256") == hash_sha256:
        return None

    version = ContratoVersion(
        contrato_id=contrato_id,
        user_id=user_id,
        numero_versao=numero_versao,
        hash_sha256=hash_sha256,
        diffs=diffs,
        snapshot=snapshot,
        ip=ip,
        user_agent=user_agent,
        observacao=observacao,
    )
    await db.contrato_versions.insert_one(version.model_dump())
    return version


async def _next_contrato_numero(db) -> str:
    ano = datetime.utcnow().year
    result = await db.counters.find_one_and_update(
        {"_id": f"contrato_numero_{ano}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"CV-{ano}-{result['seq']:04d}"


# ============================================================
# ENDPOINT PUBLICO — sem autenticacao
# ============================================================

@router.get("/contratos/tipos")
async def listar_tipos_contrato():
    """Retorna lista de todos os tipos de contrato suportados."""
    return {"tipos": TIPOS_CONTRATO}


# ============================================================
# ENDPOINTS CRUD
# ============================================================

@router.post("/contratos", response_model=Contrato)
async def criar_contrato(
    data: ContratoBase,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    numero_contrato = await _next_contrato_numero(db)
    payload = data.model_dump()
    payload["numero_contrato"] = numero_contrato
    contrato = Contrato(user_id=uid, **payload)
    await db.contratos.insert_one(contrato.model_dump())
    logger.info("Contrato criado: %s por user %s", numero_contrato, uid)
    return contrato


@router.get("/contratos", response_model=List[dict])
async def listar_contratos(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    tipo_contrato: Optional[str] = Query(None, description="Filtrar por tipo de contrato"),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    filtro: dict = {"user_id": uid}
    if status:
        filtro["status"] = status
    if tipo_contrato:
        filtro["tipo_contrato"] = tipo_contrato

    cursor = db.contratos.find(
        filtro,
        # Projetar apenas metadados — excluir clausulas para economizar banda
        {
            "clausulas": 0,
            "partes": 0,
            "objeto": 0,
            "condicoes_pagamento": 0,
            "alertas_juridicos": 0,
            "d4sign_signatarios": 0,
        },
    ).sort("updated_at", -1)

    items = await cursor.to_list(1000)
    return [serialize_doc(i) for i in items]


@router.get("/contratos/{cid}")
async def buscar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return serialize_doc(doc)


@router.put("/contratos/{cid}")
async def atualizar_contrato(
    cid: str,
    data: ContratoBase,
    request: Request,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    updates = data.model_dump()
    updates["updated_at"] = datetime.utcnow()

    ip = request.headers.get("x-forwarded-for") or (
        request.client.host if request.client else None
    )
    user_agent = request.headers.get("user-agent")

    merged = {**doc, **updates}
    await _create_version(
        db=db,
        contrato_id=cid,
        user_id=uid,
        old_doc=doc,
        new_data=merged,
        ip=ip,
        user_agent=user_agent,
        snapshot={k: v for k, v in doc.items() if not k.startswith("_")},
    )

    await db.contratos.update_one({"id": cid}, {"$set": updates})
    new_doc = await db.contratos.find_one({"id": cid})
    return serialize_doc(new_doc)


@router.delete("/contratos/{cid}")
async def arquivar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    await db.contratos.update_one(
        {"id": cid},
        {"$set": {"status": "arquivado", "updated_at": datetime.utcnow()}},
    )
    logger.info("Contrato %s arquivado por user %s", cid, uid)
    return {"ok": True, "status": "arquivado"}


# ============================================================
# ENDPOINTS DE IA — Roma_IA aplicada a Contratos
# ============================================================

class GerarClausulasRequest(BaseModel):
    tipo: Optional[str] = None  # sobreescreve o tipo do contrato se fornecido


@router.post("/contratos/{cid}/gerar-clausulas")
async def gerar_clausulas(
    cid: str,
    body: Optional[GerarClausulasRequest] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera clausulas juridicas para o contrato usando Roma_IA.

    Retorna lista de clausulas sugeridas. As clausulas NAO sao salvas automaticamente
    — o front-end deve confirmar e chamar PUT /contratos/{cid} para persistir.
    """
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    tipo = (body.tipo if body and body.tipo else None) or doc.get("tipo_contrato") or ""
    if not tipo:
        raise HTTPException(status_code=400, detail="Tipo de contrato não definido")

    clausulas = await gerar_clausulas_contrato(tipo=tipo, dados=doc)

    # Gera clausulas de corretagem se houver corretor
    corretor = doc.get("corretor")
    clausulas_corretor = []
    if corretor and (corretor.get("nome") or corretor.get("creci")):
        clausulas_corretor = await gerar_clausulas_corretor(corretor=corretor, tipo_contrato=tipo)

    return {
        "clausulas": clausulas,
        "clausulas_corretagem": clausulas_corretor,
        "total": len(clausulas) + len(clausulas_corretor),
        "tipo_contrato": tipo,
    }


@router.post("/contratos/{cid}/validar-juridico")
async def validar_juridico(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Valida o contrato e retorna alertas juridicos via Roma_IA.

    Salva os alertas no banco e retorna a lista completa.
    """
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    alertas = await validar_alertas_juridicos(contrato=doc)

    # Persiste alertas no contrato
    await db.contratos.update_one(
        {"id": cid},
        {"$set": {
            "alertas_juridicos": alertas,
            "updated_at": datetime.utcnow(),
        }},
    )

    criticos = [a for a in alertas if a.get("nivel") == "critico"]
    avisos = [a for a in alertas if a.get("nivel") == "aviso"]
    infos = [a for a in alertas if a.get("nivel") == "info"]

    return {
        "alertas": alertas,
        "resumo": {
            "total": len(alertas),
            "criticos": len(criticos),
            "avisos": len(avisos),
            "infos": len(infos),
        },
    }


class SimuladorRequest(BaseModel):
    dias_atraso: Optional[int] = 30


@router.post("/contratos/{cid}/simulador-penalidades")
async def simulador_penalidades(
    cid: str,
    body: Optional[SimuladorRequest] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Simula penalidades por inadimplemento contratual.

    Calcula multa, juros de mora e correcao monetaria estimada.
    """
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    dias = (body.dias_atraso if body else None) or 30

    resultado = calcular_penalidades(contrato=doc, dias_atraso=dias)
    return resultado


@router.get("/contratos/{cid}/checklist")
async def checklist_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Retorna checklist de verificacao do contrato antes da assinatura.

    Verifica qualificacao das partes, objeto, valor, clausulas, testemunhas e corretor.
    """
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    resultado = gerar_checklist(contrato=doc)
    return resultado


# ============================================================
# ENDPOINTS DE EXPORTACAO — DOCX e PDF
# ============================================================

@router.get("/contratos/{cid}/docx")
async def exportar_docx(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Exporta o contrato em formato DOCX (Word) com layout juridico premium.

    Times New Roman 12pt, margens 3/2/3cm, clausulas em romano, texto justificado.
    """
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    user_doc = await db.users.find_one({"id": uid}) or {}

    # Busca logo da empresa se existir
    if user_doc.get("company_logo_id"):
        try:
            logo_file = await db.fs.files.find_one({"_id": user_doc["company_logo_id"]})
            if logo_file:
                import gridfs
                from motor.motor_asyncio import AsyncIOMotorGridFSBucket
                bucket = AsyncIOMotorGridFSBucket(db)
                buf = io.BytesIO()
                await bucket.download_to_stream(user_doc["company_logo_id"], buf)
                user_doc["_company_logo_bytes"] = buf.getvalue()
        except Exception:
            pass

    from contrato_docx import generate_contrato_docx

    perfil = None
    if user_doc.get("perfil_avaliador_id"):
        try:
            perfil = await db.perfil_avaliador.find_one({"user_id": uid})
        except Exception:
            pass

    docx_bytes = generate_contrato_docx(contrato=doc, user=user_doc, perfil=perfil)

    numero = doc.get("numero_contrato") or cid[:8]
    filename = f"Contrato_{numero}.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/contratos/{cid}/pdf")
async def exportar_pdf(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Exporta o contrato em formato PDF via conversao do DOCX.

    Utiliza docx2pdf quando disponivel; fallback para DOCX com cabecalho PDF.
    """
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    user_doc = await db.users.find_one({"id": uid}) or {}

    # Tenta logo
    if user_doc.get("company_logo_id"):
        try:
            from motor.motor_asyncio import AsyncIOMotorGridFSBucket
            bucket = AsyncIOMotorGridFSBucket(db)
            buf = io.BytesIO()
            await bucket.download_to_stream(user_doc["company_logo_id"], buf)
            user_doc["_company_logo_bytes"] = buf.getvalue()
        except Exception:
            pass

    from contrato_docx import generate_contrato_docx

    perfil = None
    if user_doc.get("perfil_avaliador_id"):
        try:
            perfil = await db.perfil_avaliador.find_one({"user_id": uid})
        except Exception:
            pass

    docx_bytes = generate_contrato_docx(contrato=doc, user=user_doc, perfil=perfil)

    numero = doc.get("numero_contrato") or cid[:8]

    # Tenta converter para PDF com docx2pdf
    try:
        import subprocess
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_docx:
            tmp_docx.write(docx_bytes)
            tmp_docx_path = tmp_docx.name

        tmp_pdf_path = tmp_docx_path.replace(".docx", ".pdf")

        try:
            result = subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir",
                 os.path.dirname(tmp_docx_path), tmp_docx_path],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and os.path.exists(tmp_pdf_path):
                with open(tmp_pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                return StreamingResponse(
                    io.BytesIO(pdf_bytes),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="Contrato_{numero}.pdf"'},
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        finally:
            for p in [tmp_docx_path, tmp_pdf_path]:
                try:
                    os.unlink(p)
                except Exception:
                    pass
    except Exception:
        pass

    # Fallback: retorna DOCX com Content-Type PDF (para conversao no cliente)
    logger.warning("PDF conversion unavailable for contrato %s, returning DOCX", cid)
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="Contrato_{numero}.docx"'},
    )


@router.get("/contratos/{cid}/recibo-arras/docx")
async def exportar_recibo_arras_docx(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Exporta recibo de sinal/arras em formato DOCX.

    Gera documento simples de recibo com dados das partes, valor e tipo de arras.
    """
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    user_doc = await db.users.find_one({"id": uid}) or {}
    cond = doc.get("condicoes_pagamento") or {}
    sinal = float(cond.get("sinal_valor") or 0)

    if sinal <= 0:
        raise HTTPException(
            status_code=400,
            detail="Contrato não possui sinal/arras definido. Informe o valor do sinal antes de gerar o recibo.",
        )

    from contrato_docx import generate_recibo_arras_docx

    docx_bytes = generate_recibo_arras_docx(contrato=doc, user=user_doc)

    numero = doc.get("numero_contrato") or cid[:8]
    filename = f"Recibo_Arras_{numero}.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================
# FASE 3 — LACRE, COMPARTILHAMENTO, PORTAL PUBLICO, D4SIGN, VERSOES
# ============================================================

# ── Helpers internos ─────────────────────────────────────────

async def _next_lacre_versao(db, contrato_id: str) -> int:
    """Retorna o proximo numero de versao de lacre para o contrato."""
    last = await db.contrato_versions.find_one(
        {"contrato_id": contrato_id, "tipo": "lacrado"},
        sort=[("numero_versao", -1)],
    )
    return (last["numero_versao"] + 1) if last else 1


# ── POST /contratos/{cid}/lacrar ─────────────────────────────

@router.post("/contratos/{cid}/lacrar")
async def lacrar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lacra o contrato: gera hash SHA-256, numero de lacre e salva versao imutavel."""
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato nao encontrado")

    if doc.get("lacrado"):
        raise HTTPException(
            status_code=400,
            detail=f"Contrato ja lacrado como {doc.get('versao_lacrada')}",
        )

    # Calcula hash do conteudo atual
    payload_para_hash = {
        k: v for k, v in doc.items()
        if k not in ("_id", "lacrado", "versao_lacrada", "hash_lacrado",
                     "link_publico_token", "link_publico_ativo", "link_publico_criado_em",
                     "d4sign_document_uuid", "d4sign_status", "d4sign_enviado_em",
                     "d4sign_assinado_em", "d4sign_signatarios", "d4sign_pdf_assinado_url")
    }
    hash_sha256 = _calculate_hash(payload_para_hash)

    # Numero do lacre: {numero_contrato}-v{n}
    n_versao = await _next_lacre_versao(db, cid)
    versao_lacrada = f"{doc.get('numero_contrato', cid[:8])}-v{n_versao}"

    now = datetime.utcnow()

    # Salva versao lacrada em contrato_versions
    version_doc = {
        "id": str(_uuid_module.uuid4()),
        "contrato_id": cid,
        "user_id": uid,
        "numero_versao": n_versao,
        "hash_sha256": hash_sha256,
        "tipo": "lacrado",
        "versao_lacrada": versao_lacrada,
        "snapshot": {k: v for k, v in doc.items() if not k.startswith("_")},
        "diffs": [],
        "observacao": f"Lacre {versao_lacrada}",
        "created_at": now,
    }
    await db.contrato_versions.insert_one(version_doc)

    # Atualiza contrato
    await db.contratos.update_one(
        {"id": cid},
        {"$set": {
            "lacrado": True,
            "versao_lacrada": versao_lacrada,
            "hash_lacrado": hash_sha256,
            "updated_at": now,
        }},
    )

    logger.info("Contrato %s lacrado como %s por user %s", cid, versao_lacrada, uid)
    return {
        "ok": True,
        "versao_lacrada": versao_lacrada,
        "hash_sha256": hash_sha256,
        "lacrado_em": now.isoformat(),
        "numero_versao": n_versao,
    }


# ── POST /contratos/{cid}/compartilhar ───────────────────────

@router.post("/contratos/{cid}/compartilhar")
async def compartilhar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera link publico UUID para visualizacao do contrato sem autenticacao."""
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato nao encontrado")

    # Reusar token existente ou gerar novo
    token = doc.get("link_publico_token") or str(_uuid_module.uuid4())
    now = datetime.utcnow()

    await db.contratos.update_one(
        {"id": cid},
        {"$set": {
            "link_publico_token": token,
            "link_publico_ativo": True,
            "link_publico_criado_em": now,
            "updated_at": now,
        }},
    )

    url_publica = f"/contratos/public/{token}"
    logger.info("Contrato %s compartilhado via token %s", cid, token)
    return {
        "ok": True,
        "token": token,
        "url_publica": url_publica,
        "compartilhado_em": now.isoformat(),
        "link_ativo": True,
    }


# ── GET /contratos/public/{token} — SEM autenticacao ─────────

@router.get("/contratos/public/{token}")
async def portal_publico_contrato(
    token: str,
    db=Depends(get_db),
):
    """Retorna dados limitados do contrato para visualizacao publica (sem autenticacao).

    Expoe apenas: numero, tipo, status, nomes das partes, objeto resumido e data de criacao.
    Nao retorna clausulas, CPF, RG, historico nem dados sensiveis.
    """
    doc = await db.contratos.find_one(
        {"link_publico_token": token, "link_publico_ativo": True}
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Link invalido, expirado ou contrato nao disponivel para visualizacao publica.",
        )

    # Monta objeto resumido sem dados sensiveis
    objeto = doc.get("objeto") or {}
    objeto_resumido = None
    if objeto:
        partes_end = [
            objeto.get("endereco", ""),
            objeto.get("bairro", ""),
            objeto.get("cidade", ""),
            objeto.get("uf", ""),
        ]
        objeto_resumido = ", ".join(p for p in partes_end if p) or None
        if not objeto_resumido and objeto.get("veiculo_marca"):
            objeto_resumido = f"{objeto.get('veiculo_marca', '')} {objeto.get('veiculo_modelo', '')}".strip()

    # Extrai apenas nomes das partes (sem CPF, RG, etc.)
    partes_publicas = []
    for parte in (doc.get("partes") or []):
        qualificacao = parte.get("qualificacao", "")
        if parte.get("tipo") == "pj":
            pj = parte.get("pj") or {}
            nome = pj.get("razao_social", "")
        else:
            pf = parte.get("pf") or {}
            nome = pf.get("nome", "")
        if nome:
            partes_publicas.append({"qualificacao": qualificacao, "nome": nome})

    return {
        "numero_contrato": doc.get("numero_contrato"),
        "tipo_contrato": doc.get("tipo_contrato"),
        "status": doc.get("status"),
        "partes": partes_publicas,
        "objeto": objeto_resumido,
        "data_criacao": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "lacrado": doc.get("lacrado", False),
        "versao_lacrada": doc.get("versao_lacrada") if doc.get("lacrado") else None,
    }


# ── Request model para assinar-d4sign ─────────────────────────

class AssinarD4SignRequest(BaseModel):
    mensagem: Optional[str] = ""
    incluir_corretor: Optional[bool] = True
    signatarios_extras: Optional[List[dict]] = []


# ── POST /contratos/{cid}/assinar-d4sign ─────────────────────

@router.post("/contratos/{cid}/assinar-d4sign")
async def assinar_d4sign(
    cid: str,
    body: Optional[AssinarD4SignRequest] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Envia contrato para assinatura digital via D4Sign.

    Monta automaticamente a lista de signatarios a partir das partes do contrato:
    vendedores/locadores (tipo=1), compradores/locatarios (tipo=1),
    corretor opcional (tipo=1), testemunhas (tipo=4).
    """
    import os
    if not os.environ.get("D4SIGN_TOKEN", ""):
        raise HTTPException(
            status_code=503,
            detail="Assinatura digital nao configurada. Configure D4SIGN_TOKEN no painel de administracao.",
        )

    from services import d4sign_service as d4

    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato nao encontrado")

    if doc.get("d4sign_status") == "aguardando":
        raise HTTPException(
            status_code=400,
            detail="Contrato ja enviado para assinatura D4Sign. Aguardando signatarios.",
        )

    # Monta lista de signatarios automaticamente a partir das partes
    signatarios = []

    for parte in (doc.get("partes") or []):
        if parte.get("tipo") == "pj":
            pj = parte.get("pj") or {}
            email = pj.get("email", "")
            nome = pj.get("razao_social", "") or pj.get("representante_nome", "")
        else:
            pf = parte.get("pf") or {}
            email = pf.get("email", "")
            nome = pf.get("nome", "")

        if email and nome:
            signatarios.append({"email": email, "nome": nome, "tipo": "1"})

    # Corretor (se solicitado e tiver email)
    if (body is None or body.incluir_corretor) and doc.get("corretor"):
        corretor = doc["corretor"]
        if corretor.get("email") and corretor.get("nome"):
            signatarios.append({
                "email": corretor["email"],
                "nome": corretor["nome"],
                "tipo": "1",
            })

    # Testemunhas
    for t in (doc.get("testemunhas") or []):
        if t.get("email") and t.get("nome"):
            signatarios.append({"email": t["email"], "nome": t["nome"], "tipo": "4"})

    # Signatarios extras informados no body
    if body and body.signatarios_extras:
        for s in body.signatarios_extras:
            if s.get("email") and s.get("nome"):
                signatarios.append({
                    "email": s["email"],
                    "nome": s["nome"],
                    "tipo": str(s.get("tipo", "1")),
                })

    if not signatarios:
        raise HTTPException(
            status_code=400,
            detail="Nenhum signatario com e-mail encontrado nas partes do contrato.",
        )

    # Gera DOCX do contrato
    user_doc = await db.users.find_one({"id": uid}) or {}
    perfil = None
    if user_doc.get("perfil_avaliador_id"):
        try:
            perfil = await db.perfil_avaliador.find_one({"user_id": uid})
        except Exception:
            pass

    try:
        from contrato_docx import generate_contrato_docx
        docx_bytes = generate_contrato_docx(contrato=doc, user=user_doc, perfil=perfil)
    except Exception as e:
        logger.error("Erro ao gerar DOCX para D4Sign contrato %s: %s", cid, e)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar documento: {e}")

    numero = doc.get("numero_contrato") or cid[:8]
    nome_arquivo = f"Contrato_{numero}.docx"

    # Upload DOCX para D4Sign
    try:
        doc_uuid = await d4.upload_documento(docx_bytes, nome_arquivo)
    except Exception as e:
        logger.error("Erro no upload D4Sign contrato %s: %s", cid, e)
        raise HTTPException(status_code=502, detail=f"Erro no upload D4Sign: {e}")

    # Adiciona signatarios
    signatarios_salvos = []
    for sig in signatarios:
        try:
            signer_uuid = await d4.adicionar_signatario(
                doc_uuid, sig["email"], sig["nome"], sig["tipo"]
            )
            signatarios_salvos.append({
                "email": sig["email"],
                "nome": sig["nome"],
                "tipo": sig["tipo"],
                "signer_uuid": signer_uuid,
                "assinado": False,
                "assinado_em": None,
            })
        except Exception as e:
            logger.error("Erro ao adicionar signatario %s: %s", sig["email"], e)
            raise HTTPException(
                status_code=502,
                detail=f"Erro ao adicionar signatario {sig['email']}: {e}",
            )

    # Envia para assinatura
    mensagem = (body.mensagem if body else None) or ""
    try:
        await d4.enviar_para_assinatura(doc_uuid, mensagem)
    except Exception as e:
        logger.error("Erro ao enviar para assinatura D4Sign contrato %s: %s", cid, e)
        raise HTTPException(status_code=502, detail=f"Erro ao enviar para assinatura: {e}")

    now = datetime.utcnow()
    await db.contratos.update_one(
        {"id": cid},
        {"$set": {
            "d4sign_document_uuid": doc_uuid,
            "d4sign_status": "enviado",
            "d4sign_enviado_em": now,
            "d4sign_signatarios": signatarios_salvos,
            "updated_at": now,
        }},
    )

    logger.info("Contrato %s enviado para D4Sign doc_uuid=%s por user %s", cid, doc_uuid, uid)
    return {
        "ok": True,
        "d4sign_document_uuid": doc_uuid,
        "d4sign_status": "enviado",
        "d4sign_enviado_em": now.isoformat(),
        "signatarios": signatarios_salvos,
        "total_signatarios": len(signatarios_salvos),
    }


# ── GET /contratos/{cid}/versoes ─────────────────────────────

@router.get("/contratos/{cid}/versoes")
async def listar_versoes_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Retorna historico de versoes do contrato, ordenado por numero_versao desc."""
    doc = await db.contratos.find_one({"id": cid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato nao encontrado")

    cursor = db.contrato_versions.find(
        {"contrato_id": cid},
        {"snapshot": 0, "_id": 0},
    ).sort("numero_versao", -1)

    versoes = await cursor.to_list(200)
    versoes_serializadas = [serialize_doc(v) for v in versoes]

    return {
        "contrato_id": cid,
        "numero_contrato": doc.get("numero_contrato"),
        "total_versoes": len(versoes_serializadas),
        "versoes": versoes_serializadas,
    }
