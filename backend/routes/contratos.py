# @module routes.contratos — CRUD Contratos Imobiliarios, versionamento com diff/SHA-256
import hashlib
import io
import json
import logging
import uuid as _uuid_module
from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pymongo import ReturnDocument
from pydantic import BaseModel
from bson import ObjectId
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from db import get_db
from dependencies import get_active_subscriber, get_authenticated_user, serialize_doc
from models.contrato import (
    ContratoBase, Contrato, ContratoVersion, ContratoVersionDiff,
    TIPOS_CONTRATO,
)
from services.contrato_ia_service import (
    gerar_clausulas_contrato,
    gerar_clausulas_corretor,
    gerar_clausulas_exclusividade,
    validar_alertas_juridicos,
    calcular_penalidades,
    gerar_checklist,
)

router = APIRouter(tags=["contratos"])
logger = logging.getLogger("romatec")


# ──────────────────────────────────────────────────────────────────────────────
# Schemas auxiliares
# ──────────────────────────────────────────────────────────────────────────────

class ContratoCreate(BaseModel):
    tipo_contrato: str
    numero_contrato: Optional[str] = None
    cidade_assinatura: Optional[str] = None
    data_assinatura: Optional[str] = None
    foro_eleito: Optional[str] = None
    vendedores: Optional[List[Any]] = None
    compradores: Optional[List[Any]] = None
    corretor: Optional[Any] = None
    objeto: Optional[Any] = None
    pagamento: Optional[Any] = None
    config: Optional[Any] = None


class ContratoUpdate(BaseModel):
    tipo_contrato: Optional[str] = None
    status: Optional[str] = None
    cidade_assinatura: Optional[str] = None
    data_assinatura: Optional[str] = None
    foro_eleito: Optional[str] = None
    vendedores: Optional[List[Any]] = None
    compradores: Optional[List[Any]] = None
    corretor: Optional[Any] = None
    objeto: Optional[Any] = None
    pagamento: Optional[Any] = None
    clausulas: Optional[List[Any]] = None
    alertas_juridicos: Optional[List[Any]] = None
    testemunha_1: Optional[Any] = None
    testemunha_2: Optional[Any] = None
    incluir_logo: Optional[bool] = None
    incluir_recibo_arras: Optional[bool] = None
    incluir_checklist: Optional[bool] = None


class GerarClausulasRequest(BaseModel):
    tipo: Optional[str] = None  # sobreescreve o tipo do contrato se fornecido


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _calculate_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _deep_diff(old: dict, new: dict, path: str = "") -> List[dict]:
    diffs = []
    all_keys = set(old.keys()) | set(new.keys())
    for key in all_keys:
        old_val = old.get(key)
        new_val = new.get(key)
        current_path = f"{path}.{key}" if path else key
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            diffs.extend(_deep_diff(old_val, new_val, current_path))
        elif isinstance(old_val, list) and isinstance(new_val, list):
            if old_val != new_val:
                diffs.append({"campo": current_path, "de": old_val, "para": new_val})
        elif old_val != new_val:
            diffs.append({"campo": current_path, "de": old_val, "para": new_val})
    return diffs


def _create_version(
    contrato_id: str,
    user_id: str,
    numero_versao: int,
    tipo: str,
    hash_sha256: str,
    diffs: List[dict],
    snapshot: Optional[dict] = None,
    numero_lacre: Optional[str] = None,
) -> dict:
    return {
        "id": str(_uuid_module.uuid4()),
        "contrato_id": contrato_id,
        "user_id": user_id,
        "numero_versao": numero_versao,
        "tipo": tipo,
        "hash_sha256": hash_sha256,
        "diffs": diffs,
        "snapshot": snapshot,
        "numero_lacre": numero_lacre,
        "created_at": datetime.utcnow(),
    }


def _contrato_query_by_cid(cid: str, uid: str) -> dict:
    query = {"user_id": uid}
    if ObjectId.is_valid(cid):
        query["$or"] = [{"id": cid}, {"_id": ObjectId(cid)}]
    else:
        query["id"] = cid
    return query


def _normalize_contrato_doc(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return doc
    raw_id = doc.get("_id")
    payload = serialize_doc(doc)
    if not payload.get("id") and raw_id is not None:
        payload["id"] = str(raw_id)
    return payload


def _fmt_brl(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "R$ 0,00"
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def _fmt_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str) and value:
        return value
    return "-"


def _nome_parte(parte: dict) -> str:
    if not isinstance(parte, dict):
        return ""
    return (
        parte.get("nome")
        or parte.get("razao_social")
        or (parte.get("pf") or {}).get("nome")
        or (parte.get("pj") or {}).get("razao_social")
        or (parte.get("pj") or {}).get("nome_fantasia")
        or ""
    )


def _extract_corpo_contrato(doc: dict) -> List[str]:
    # Prioridade: cláusulas estruturadas, depois campos textuais livres.
    clausulas = doc.get("clausulas")
    linhas: List[str] = []

    if isinstance(clausulas, list) and clausulas:
        for i, item in enumerate(clausulas, 1):
            if isinstance(item, dict):
                titulo = item.get("titulo") or item.get("nome") or f"Cláusula {i}"
                texto = item.get("texto") or item.get("conteudo") or ""
                if texto:
                    linhas.append(f"{titulo}: {texto}")
                else:
                    linhas.append(str(titulo))
            elif isinstance(item, str) and item.strip():
                linhas.append(item.strip())

    for key in ("corpo", "texto", "texto_contrato", "clausulas_texto"):
        value = doc.get(key)
        if isinstance(value, str) and value.strip():
            linhas.extend([p.strip() for p in value.split("\n") if p.strip()])

    if not linhas:
        linhas.append("Contrato sem cláusulas textuais cadastradas.")

    return linhas


def _draw_multiline(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, line_height: float = 14.0) -> float:
    words = text.split()
    if not words:
        return y - line_height

    current = words[0]
    for w in words[1:]:
        candidate = f"{current} {w}"
        if c.stringWidth(candidate, "Helvetica", 10) <= max_width:
            current = candidate
        else:
            c.drawString(x, y, current)
            y -= line_height
            current = w
    c.drawString(x, y, current)
    return y - line_height


def _generate_contrato_pdf_bytes(doc: dict, uid: str, empresa: str) -> bytes:
    contrato_id = str(doc.get("id") or doc.get("_id") or "-")
    numero = doc.get("numero_contrato") or contrato_id
    tipo = doc.get("tipo_contrato") or "-"
    status = doc.get("status") or "-"

    vendedores = [n for n in (_nome_parte(p) for p in doc.get("vendedores", [])) if n]
    compradores = [n for n in (_nome_parte(p) for p in doc.get("compradores", [])) if n]
    partes = ", ".join(vendedores + compradores) or "-"

    pagamento = doc.get("pagamento") if isinstance(doc.get("pagamento"), dict) else {}
    valor = (
        pagamento.get("valor_total")
        or pagamento.get("valor")
        or (doc.get("objeto") or {}).get("valor")
        or 0
    )

    created_at = _fmt_date(doc.get("created_at"))
    corpo_linhas = _extract_corpo_contrato(doc)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    margin_x = 40
    y = h - 50

    c.setTitle(f"contrato_{contrato_id}")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin_x, y, empresa or "AvalieImob")
    y -= 22

    c.setFont("Helvetica", 10)
    y = _draw_multiline(c, f"Número/ID: {numero}", margin_x, y, w - 2 * margin_x)
    y = _draw_multiline(c, f"Tipo do contrato: {tipo}", margin_x, y, w - 2 * margin_x)
    y = _draw_multiline(c, f"Partes envolvidas: {partes}", margin_x, y, w - 2 * margin_x)
    y = _draw_multiline(c, f"Valor: {_fmt_brl(valor)}", margin_x, y, w - 2 * margin_x)
    y = _draw_multiline(c, f"Data de criação: {created_at}", margin_x, y, w - 2 * margin_x)
    y = _draw_multiline(c, f"Status atual: {status}", margin_x, y, w - 2 * margin_x)

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_x, y, "Corpo do contrato")
    y -= 16
    c.setFont("Helvetica", 10)

    max_width = w - 2 * margin_x
    for linha in corpo_linhas:
        if y < 80:
            c.showPage()
            y = h - 50
            c.setFont("Helvetica", 10)
        y = _draw_multiline(c, linha, margin_x, y, max_width)

    if y < 70:
        c.showPage()
        y = h - 50
        c.setFont("Helvetica", 10)

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(
        margin_x,
        40,
        f"Gerado em {datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')} | Gerado por AvalieImob / Romatec | usuário {uid}",
    )

    c.save()
    buffer.seek(0)
    return buffer.read()


async def _next_contrato_numero(db, ano: int) -> str:
    seq = await db.counters.find_one_and_update(
        {"_id": f"contrato_numero_{ano}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    n = seq.get("seq", 1) if seq else 1
    return f"CV-{ano}-{n:04d}"


async def _next_lacre_versao(db, contrato_id: str, ano: int) -> str:
    seq = await db.counters.find_one_and_update(
        {"_id": f"lacre_{contrato_id}_{ano}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    n = seq.get("seq", 1) if seq else 1
    contrato_lookup = {"id": contrato_id}
    if ObjectId.is_valid(contrato_id):
        contrato_lookup = {"$or": [{"id": contrato_id}, {"_id": ObjectId(contrato_id)}]}
    doc = await db.contratos.find_one(contrato_lookup)
    numero_base = doc.get("numero_contrato", f"CV-{ano}") if doc else f"CV-{ano}"
    return f"{numero_base}-v{n}"


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/contratos/tipos")
async def listar_tipos():
    """Lista todos os tipos de contrato disponíveis (público)."""
    return TIPOS_CONTRATO


@router.post("/contratos", response_model=Contrato)
async def criar_contrato(
    body: ContratoCreate,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Cria um novo contrato com número automático."""
    ano = datetime.utcnow().year
    numero = await _next_contrato_numero(db, ano)
    
    # Monta o documento com todos os campos opcionais
    contrato_data = {
        "id": str(_uuid_module.uuid4()),
        "user_id": uid,
        "tipo_contrato": body.tipo_contrato,
        "numero_contrato": numero,
        "status": "minuta",
        "cidade_assinatura": body.cidade_assinatura or "",
        "data_assinatura": body.data_assinatura or "",
        "foro_eleito": body.foro_eleito or "",
        "vendedores": body.vendedores or [],
        "compradores": body.compradores or [],
        "corretor": body.corretor or {"incluir": False},
        "objeto": body.objeto or {},
        "pagamento": body.pagamento or {},
        "config": body.config or {"incluir_logo": True, "incluir_recibo_arras": True, "incluir_checklist": True},
        "clausulas": [],
        "alertas_juridicos": [],
        "versao_atual": 1,
        "lacrado": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await db.contratos.insert_one(contrato_data)
    return _normalize_contrato_doc(contrato_data)


@router.get("/contratos")
async def listar_contratos(
    status: Optional[str] = None,
    tipo_contrato: Optional[str] = None,
    busca: Optional[str] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lista contratos do usuário com filtros opcionais."""
    filtros = {"user_id": uid}
    if status:
        filtros["status"] = status
    if tipo_contrato:
        filtros["tipo_contrato"] = tipo_contrato
    
    cursor = db.contratos.find(filtros).sort("updated_at", -1)
    docs = await cursor.to_list(length=1000)
    
    # Busca por nome das partes (simplificada)
    if busca:
        docs = [
            d for d in docs
            if busca.lower() in json.dumps(d.get("vendedores", []), ensure_ascii=False).lower()
            or busca.lower() in json.dumps(d.get("compradores", []), ensure_ascii=False).lower()
        ]
    
    return [_normalize_contrato_doc(d) for d in docs]


@router.get("/contratos/{cid}")
async def buscar_contrato(
    cid: str,
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Busca um contrato completo pelo ID. Permite acesso mesmo com plano expirado."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return _normalize_contrato_doc(doc)


@router.get("/contratos/{cid}/pdf")
async def baixar_contrato_pdf(
    cid: str,
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Gera e retorna PDF binário válido do contrato do usuário autenticado."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    user = await db.users.find_one({"id": uid}, {"company": 1, "name": 1})
    empresa = (user or {}).get("company") or (user or {}).get("name") or "AvalieImob"

    pdf_bytes = _generate_contrato_pdf_bytes(doc=doc, uid=uid, empresa=empresa)
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF válido")

    filename_id = str(doc.get("id") or doc.get("_id") or cid)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="contrato_{filename_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.put("/contratos/{cid}")
async def atualizar_contrato(
    cid: str,
    body: ContratoUpdate,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Atualiza contrato e salva versão anterior."""
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    contrato_id_ref = doc.get("id") or str(doc.get("_id"))
    
    # Salvar versão anterior
    versao_atual = doc.get("versao_atual", 1)
    snapshot_anterior = {k: v for k, v in doc.items() if not k.startswith("_")}
    hash_anterior = _calculate_hash(json.dumps(snapshot_anterior, sort_keys=True, default=str).encode())
    
    diffs = _deep_diff(snapshot_anterior, body.dict(exclude_unset=True))
    if diffs:
        version_doc = _create_version(
            contrato_id=contrato_id_ref,
            user_id=uid,
            numero_versao=versao_atual,
            tipo="auto",
            hash_sha256=hash_anterior,
            diffs=diffs,
            snapshot=snapshot_anterior,
        )
        await db.contrato_versions.insert_one(version_doc)
        versao_atual += 1
    
    # Atualizar
    update_data = body.dict(exclude_unset=True)
    if not doc.get("id"):
        update_data["id"] = contrato_id_ref
    update_data["versao_atual"] = versao_atual
    update_data["updated_at"] = datetime.utcnow()
    
    await db.contratos.update_one(
        query,
        {"$set": update_data}
    )
    
    doc_atualizado = await db.contratos.find_one(query)
    return _normalize_contrato_doc(doc_atualizado)


@router.delete("/contratos/{cid}")
async def deletar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Soft delete do contrato (status = arquivado)."""
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    
    await db.contratos.update_one(
        query,
        {"$set": {"status": "arquivado", "updated_at": datetime.utcnow()}}
    )
    return {"message": "Contrato arquivado com sucesso"}


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
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    tipo = (body.tipo if body and body.tipo else None) or doc.get("tipo_contrato") or ""
    if not tipo:
        raise HTTPException(status_code=400, detail="Tipo de contrato não definido")

    # Usa função específica para contrato de exclusividade
    if tipo == "exclusividade":
        dados_exclusividade = {
            "corretor_nome": doc.get("corretor", {}).get("nome", ""),
            "corretor_creci": doc.get("corretor", {}).get("creci", ""),
            "prazo_dias": doc.get("corretor", {}).get("prazo_exclusividade_dias", 90),
            "data_inicio": doc.get("data_assinatura", ""),
            "data_fim": doc.get("data_fim_exclusividade", ""),
            "comissao_percentual": doc.get("corretor", {}).get("percentual_comissao", 6),
            "imovel_endereco": doc.get("objeto", {}).get("endereco", ""),
            "proprietario_nome": doc.get("vendedores", [{}])[0].get("pf", {}).get("nome", "") if doc.get("vendedores") else "",
        }
        clausulas = await gerar_clausulas_exclusividade(dados=dados_exclusividade)
        clausulas_corretor = []  # Já incluído nas cláusulas de exclusividade
    else:
        clausulas = await gerar_clausulas_contrato(tipo=tipo, dados=doc)
        
        # Gera cláusulas de corretagem se houver corretor
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
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    alertas = await validar_alertas_juridicos(contrato=doc)
    
    # Salvar alertas no contrato
    await db.contratos.update_one(
        query,
        {"$set": {"alertas_juridicos": alertas, "updated_at": datetime.utcnow()}}
    )
    
    return {"alertas": alertas, "total": len(alertas)}


@router.post("/contratos/{cid}/simulador-penalidades")
async def simulador_penalidades(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Calcula penalidades do contrato (multas, juros, correção)."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    resultado = calcular_penalidades(contrato=doc)
    return resultado


@router.get("/contratos/{cid}/checklist")
async def checklist_documental(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera checklist de documentos necessários para o contrato."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    checklist = gerar_checklist(contrato=doc)
    return {"checklist": checklist, "total": len(checklist)}


@router.get("/contratos/{cid}/versoes")
async def listar_versoes(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lista histórico de versões do contrato."""
    cursor = db.contrato_versions.find(
        {"contrato_id": cid, "user_id": uid}
    ).sort("numero_versao", -1)
    
    docs = await cursor.to_list(length=100)
    return [serialize_doc(d) for d in docs]


@router.post("/contratos/{cid}/lacrar")
async def lacrar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lacra a versão atual do contrato com hash SHA-256."""
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    contrato_id_ref = doc.get("id") or str(doc.get("_id"))
    
    if doc.get("lacrado"):
        raise HTTPException(status_code=400, detail="Contrato já está lacrado")
    
    # Calcular hash
    snapshot = {k: v for k, v in doc.items() if not k.startswith("_")}
    hash_sha256 = _calculate_hash(json.dumps(snapshot, sort_keys=True, default=str).encode())
    
    # Gerar número de lacre
    ano = datetime.utcnow().year
    numero_lacre = await _next_lacre_versao(db, contrato_id_ref, ano)
    
    # Criar versão lacrada
    version_doc = _create_version(
        contrato_id=contrato_id_ref,
        user_id=uid,
        numero_versao=doc.get("versao_atual", 1),
        tipo="lacrado",
        hash_sha256=hash_sha256,
        diffs=[],
        snapshot=snapshot,
        numero_lacre=numero_lacre,
    )
    await db.contrato_versions.insert_one(version_doc)
    
    # Atualizar contrato
    await db.contratos.update_one(
        query,
        {
            "$set": {
                "id": contrato_id_ref,
                "lacrado": True,
                "versao_lacrada": numero_lacre,
                "hash_lacrado": hash_sha256,
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    return {
        "message": "Contrato lacrado com sucesso",
        "numero_lacre": numero_lacre,
        "hash_sha256": hash_sha256,
    }


@router.post("/contratos/{cid}/compartilhar")
async def compartilhar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera link público para visualização do contrato."""
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    
    # Gerar token único
    token = str(_uuid_module.uuid4())
    
    await db.contratos.update_one(
        query,
        {
            "$set": {
                "link_publico_token": token,
                "link_publico_ativo": True,
                "link_publico_criado_em": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    return {
        "token": token,
        "url": f"/contrato/public/{token}",
    }


@router.get("/contratos/public/{token}")
async def portal_publico(
    token: str,
    db=Depends(get_db),
):
    """Portal público para visualização de contrato (sem autenticação)."""
    doc = await db.contratos.find_one({
        "link_publico_token": token,
        "link_publico_ativo": True,
    })
    
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado ou link inválido")
    
    # Retornar apenas dados não sensíveis
    return {
        "numero_contrato": doc.get("numero_contrato"),
        "tipo_contrato": doc.get("tipo_contrato"),
        "status": doc.get("status"),
        "data_assinatura": doc.get("data_assinatura"),
        "cidade_assinatura": doc.get("cidade_assinatura"),
        "vendedores": [
            {"nome": v.get("pf", {}).get("nome") or v.get("pj", {}).get("razao_social", "")}
            for v in doc.get("vendedores", [])
        ],
        "compradores": [
            {"nome": c.get("pf", {}).get("nome") or c.get("pj", {}).get("razao_social", "")}
            for c in doc.get("compradores", [])
        ],
        "objeto": {
            "endereco": doc.get("objeto", {}).get("endereco", ""),
            "cidade": doc.get("objeto", {}).get("cidade", ""),
            "uf": doc.get("objeto", {}).get("uf", ""),
        },
    }
