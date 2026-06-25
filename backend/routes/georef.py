# @module routes.georef — Topografia & Geo (Georreferenciamento / Requerimentos Cartoriais).
#
# Fluxo: cria projeto -> upload (Memorial/Mapa/CCIR/Certidão/doc cliente) -> /extrair
# (pdfplumber popula imóvel/vértices/confrontantes/cadeia) -> conferência (PATCH) ->
# /gerar -> downloads (Requerimento, Laudo, Memorial, DRLs, Shapefile, Dossiê) em
# PDF/DOCX. Geração pesada (ReportLab/pdfplumber/R2) roda fora do event loop.
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.georef import (
    GeorefProjeto, CriarProjetoBody, AtualizarProjetoBody, GerarDocumentosBody,
    calcular_completude,
)
from services import r2_storage
from services.georef import extractor as EX
from services.georef import geo as GEO
from services.georef.cadeia_dominial import parse_cadeia_dominial
from services.georef.generators import textos as TX
from services.georef.generators import pdf as PDF
from services.georef.generators import docx as DOCX
from services.georef.generators import dossie as DOSSIE

logger = logging.getLogger("romatec")
router = APIRouter(prefix="/topografia/georef", tags=["topografia-geo"])

_TIPOS_UPLOAD = {"memorial", "mapa", "ccir", "certidao", "art_trt", "car", "itr", "doc_cliente"}
_MAX_UPLOAD = 30 * 1024 * 1024  # 30 MB
_MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "zip": "application/zip",
    "geojson": "application/geo+json",
    "kml": "application/vnd.google-earth.kml+xml",
}


def _agora():
    return datetime.now(timezone.utc)


async def _numero(db) -> str:
    ano = _agora().year
    res = await db.counters.find_one_and_update(
        {"_id": f"georef_{ano}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=ReturnDocument.AFTER,
    )
    return f"GEO-{ano}-{res['seq']:04d}"


async def _get_projeto(db, pid: str, uid: str) -> dict:
    doc = await db.georef_projetos.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return doc


def _ext_arquivo(filename: str, content_type: str) -> str:
    fn = (filename or "").lower()
    if fn.endswith(".pdf") or "pdf" in (content_type or ""):
        return "pdf"
    for e in ("png", "jpg", "jpeg", "webp", "zip"):
        if fn.endswith("." + e):
            return e
    if "image" in (content_type or ""):
        return "jpg"
    return "bin"


# ──────────────────────────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/projetos", status_code=201)
async def criar_projeto(body: CriarProjetoBody, uid: str = Depends(get_active_subscriber),
                        db=Depends(get_db)):
    proj = GeorefProjeto(user_id=uid, nome_projeto=body.nome_projeto,
                         tipo_servico=body.tipo_servico, tema_pdf=body.tema_pdf)
    doc = proj.model_dump(mode="json")
    doc["numero"] = await _numero(db)
    await db.georef_projetos.insert_one(doc)
    return serialize_doc(doc)


@router.get("/projetos")
async def listar_projetos(status: str = Query(None), uid: str = Depends(get_active_subscriber),
                         db=Depends(get_db)):
    q = {"user_id": uid}
    if status:
        q["status"] = status
    cur = db.georef_projetos.find(q).sort("created_at", -1)
    return [serialize_doc(d) async for d in cur]


@router.get("/projetos/{pid}")
async def detalhe_projeto(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return serialize_doc(await _get_projeto(db, pid, uid))


@router.patch("/projetos/{pid}")
async def atualizar_projeto(pid: str, body: AtualizarProjetoBody,
                           uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    dados = body.model_dump(exclude_unset=True)
    editados = dict(doc.get("campos_editados") or {})
    sets = {}

    for campo in ("nome_projeto", "tipo_servico", "tema_pdf", "status"):
        if campo in dados:
            sets[campo] = dados[campo]

    for grupo in ("imovel", "responsavel_tecnico"):
        if grupo in dados and isinstance(dados[grupo], dict):
            atual = dict(doc.get(grupo) or {})
            for k, v in dados[grupo].items():
                atual[k] = v
                editados[f"{grupo}.{k}"] = True
            sets[grupo] = atual

    for grupo in ("vertices", "confrontantes"):
        if grupo in dados and dados[grupo] is not None:
            sets[grupo] = dados[grupo]
            editados[grupo] = True

    base = {**doc, **sets}
    sets["campos_editados"] = editados
    sets["completude"] = calcular_completude(base)
    sets["updated_at"] = _agora().isoformat()
    await db.georef_projetos.update_one({"id": pid, "user_id": uid}, {"$set": sets})
    return serialize_doc({**doc, **sets})


@router.delete("/projetos/{pid}")
async def excluir_projeto(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.georef_projetos.delete_one({"id": pid, "user_id": uid})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# Upload + Extração
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/projetos/{pid}/upload")
async def upload_documento(pid: str, tipo: str = Form(...), file: UploadFile = File(...),
                          uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    if tipo not in _TIPOS_UPLOAD:
        raise HTTPException(status_code=422, detail=f"Tipo inválido. Use: {sorted(_TIPOS_UPLOAD)}")
    doc = await _get_projeto(db, pid, uid)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Arquivo vazio")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx. 30 MB)")

    ext = _ext_arquivo(file.filename, file.content_type)
    key = f"topografia/{uid}/{pid}/{tipo}.{ext}"
    ct = file.content_type or _MIME.get(ext, "application/octet-stream")
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, data, key, ct)
    except Exception as e:  # noqa: BLE001
        logger.error("Topografia: falha no upload R2 (%s)", e)
        raise HTTPException(status_code=502, detail="Falha ao armazenar o arquivo")

    uploads = dict(doc.get("uploads") or {})
    uploads[tipo] = {"key": key, "filename": file.filename, "content_type": ct,
                     "ext": ext, "uploaded_at": _agora().isoformat()}
    await db.georef_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"uploads": uploads, "updated_at": _agora().isoformat()}},
    )
    return {"ok": True, "tipo": tipo, "uploads": list(uploads.keys())}


def _download_upload(uploads: dict, tipo: str):
    info = (uploads or {}).get(tipo)
    if not info or not info.get("key"):
        return None
    try:
        return r2_storage.download_bytes(info["key"])
    except Exception as e:  # noqa: BLE001
        logger.warning("Topografia: download R2 falhou p/ %s (%s)", tipo, e)
        return None


def _executar_extracao(doc: dict) -> dict:
    """Roda o pipeline (síncrono — chamado via to_thread) e devolve o $set."""
    uploads = doc.get("uploads") or {}
    editados = doc.get("campos_editados") or {}
    imovel = dict(doc.get("imovel") or {})
    rt = dict(doc.get("responsavel_tecnico") or {})

    def _set_imovel(fonte: dict):
        for k, v in (fonte or {}).items():
            if v in (None, ""):
                continue
            if editados.get(f"imovel.{k}"):
                continue
            imovel[k] = v

    vertices = doc.get("vertices") or []
    avisos = []

    raw_mem = _download_upload(uploads, "memorial")
    if raw_mem:
        res = EX.parse_memorial(raw_mem)
        _set_imovel(res.get("imovel"))
        for k, v in (res.get("responsavel_tecnico") or {}).items():
            if v and not editados.get(f"responsavel_tecnico.{k}"):
                rt[k] = v
        if res.get("vertices") and not editados.get("vertices"):
            vertices = res["vertices"]
    else:
        avisos.append("Memorial Descritivo não enviado — vértices não extraídos.")

    raw_ccir = _download_upload(uploads, "ccir")
    if raw_ccir:
        _set_imovel(EX.parse_ccir(raw_ccir))

    raw_cert = _download_upload(uploads, "certidao")
    if raw_cert and not editados.get("imovel.cadeia_dominial"):
        try:
            cadeia = parse_cadeia_dominial(raw_cert)
            if cadeia:
                imovel["cadeia_dominial"] = cadeia
        except Exception as e:  # noqa: BLE001
            avisos.append(f"Cadeia dominial não extraída ({e}).")

    if not editados.get("confrontantes"):
        confrontantes = EX.agrupar_confrontantes(vertices, matricula_imovel=imovel.get("matricula"))
    else:
        confrontantes = doc.get("confrontantes") or []

    val = GEO.validar_geometria(vertices, area_ha_sigef=imovel.get("area_ha"))
    avisos.extend(val.get("avisos") or [])

    novo = {**doc, "imovel": imovel, "responsavel_tecnico": rt,
            "vertices": vertices, "confrontantes": confrontantes}
    return {
        "imovel": imovel, "responsavel_tecnico": rt,
        "vertices": vertices, "confrontantes": confrontantes,
        "status": "extraido", "completude": calcular_completude(novo),
        "updated_at": _agora().isoformat(),
        "_validacao": val, "_avisos": avisos,
    }


@router.post("/projetos/{pid}/extrair")
async def extrair(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    if not (doc.get("uploads") or {}).get("memorial"):
        raise HTTPException(status_code=422,
                            detail="Envie ao menos o Memorial Descritivo antes de extrair.")
    sets = await asyncio.to_thread(_executar_extracao, doc)
    validacao = sets.pop("_validacao", {})
    avisos = sets.pop("_avisos", [])
    await db.georef_projetos.update_one({"id": pid, "user_id": uid}, {"$set": sets})
    return {"ok": True, "projeto": serialize_doc({**doc, **sets}),
            "validacao": validacao, "avisos": avisos}


@router.get("/projetos/{pid}/preview-geojson")
async def preview_geojson(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    return GEO.gerar_geojson(doc)


@router.get("/projetos/{pid}/validar")
async def validar(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    im = doc.get("imovel") or {}
    return GEO.validar_geometria(doc.get("vertices") or [], area_ha_sigef=im.get("area_ha"))


# ──────────────────────────────────────────────────────────────────────────────
# Geração + Downloads
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/projetos/{pid}/gerar")
async def gerar(pid: str, body: GerarDocumentosBody, uid: str = Depends(get_active_subscriber),
               db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    if not (doc.get("vertices")):
        raise HTTPException(status_code=422, detail="Sem vértices — rode a extração antes de gerar.")
    tema = body.tema or doc.get("tema_pdf") or "prime_i"
    val = GEO.validar_geometria(doc.get("vertices") or [],
                                area_ha_sigef=(doc.get("imovel") or {}).get("area_ha"))
    gerados = dict(doc.get("documentos_gerados") or {})
    for d in body.documentos:
        gerados[d] = {"gerado_em": _agora().isoformat(), "tema": tema}
    await db.georef_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"documentos_gerados": gerados, "status": "documentos_gerados",
                  "tema_pdf": tema, "updated_at": _agora().isoformat()}},
    )
    return {"ok": True, "documentos": body.documentos, "validacao": val}


def _resp(data: bytes, fmt: str, nome: str, inline=False) -> Response:
    disp = "inline" if inline else "attachment"
    headers = {"Content-Disposition": f'{disp}; filename="{quote(nome)}"'}
    return Response(content=data, media_type=_MIME.get(fmt, "application/octet-stream"),
                    headers=headers)


def _nome_base(doc: dict) -> str:
    im = doc.get("imovel") or {}
    base = (im.get("matricula") or doc.get("numero") or "projeto")
    return str(base).replace("/", "-")


@router.get("/projetos/{pid}/documentos/{tipo}")
async def baixar_documento(pid: str, tipo: str, fmt: str = Query("pdf"),
                          tema: str = Query(None), uid: str = Depends(get_active_subscriber),
                          db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    tema = tema or doc.get("tema_pdf") or "prime_i"
    nb = _nome_base(doc)

    if tipo == "dossie":
        data = await asyncio.to_thread(_montar_dossie, doc, tema)
        return _resp(data, "pdf", f"Dossie_{nb}.pdf", inline=(fmt != "download"))

    if tipo not in ("requerimento", "memorial", "laudo_tecnico"):
        raise HTTPException(status_code=404, detail="Documento desconhecido")

    if fmt == "docx":
        data = await asyncio.to_thread(DOCX.gerar_docx, tipo, doc)
        return _resp(data, "docx", f"{tipo}_{nb}.docx")
    data = await asyncio.to_thread(PDF.gerar_pdf, tipo, doc, tema)
    return _resp(data, "pdf", f"{tipo}_{nb}.pdf", inline=True)


@router.get("/projetos/{pid}/documentos/drl/{conf_key:path}")
async def baixar_drl(pid: str, conf_key: str, fmt: str = Query("pdf"), tema: str = Query(None),
                    uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    if not TX.requer_drl(doc.get("tipo_servico")):
        raise HTTPException(
            status_code=422,
            detail="DRL dispensada para este tipo de serviço (desmembramento/remembramento).")
    tema = tema or doc.get("tema_pdf") or "prime_i"
    conf = next((c for c in (doc.get("confrontantes") or []) if c.get("key") == conf_key), None)
    if not conf:
        raise HTTPException(status_code=404, detail="Confrontante não encontrado")
    nb = _nome_base(doc)
    rotulo = (conf.get("nome") or conf.get("descricao") or "confrontante")[:30].replace("/", "-")
    if fmt == "docx":
        data = await asyncio.to_thread(DOCX.gerar_docx, "drl", doc, conf)
        return _resp(data, "docx", f"DRL_{rotulo}_{nb}.docx")
    data = await asyncio.to_thread(PDF.gerar_pdf, "drl", doc, tema, conf)
    return _resp(data, "pdf", f"DRL_{rotulo}_{nb}.pdf", inline=True)


@router.get("/projetos/{pid}/shapefile")
async def baixar_shapefile(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    try:
        data = await asyncio.to_thread(GEO.gerar_shapefile_bytes, doc)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _resp(data, "zip", f"SIGRI_{_nome_base(doc)}.zip")


@router.get("/projetos/{pid}/kml")
async def baixar_kml(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    return _resp(GEO.gerar_kml(doc).encode("utf-8"), "kml", f"{_nome_base(doc)}.kml")


def _montar_dossie(doc: dict, tema: str) -> bytes:
    partes = {
        "requerimento": PDF.gerar_pdf("requerimento", doc, tema),
        "laudo_tecnico": PDF.gerar_pdf("laudo_tecnico", doc, tema),
        "memorial": PDF.gerar_pdf("memorial", doc, tema),
        "drl": [PDF.gerar_pdf("drl", doc, tema, c) for c in TX.confrontantes_para_drl(doc)],
    }
    uploads = doc.get("uploads") or {}
    for chave, tipo_up in (("art_trt", "art_trt"), ("ccir", "ccir"), ("car", "car"),
                           ("itr", "itr"), ("certidao_matricula", "certidao"),
                           ("doc_cliente", "doc_cliente")):
        raw = _download_upload(uploads, tipo_up)
        if raw:
            partes[chave] = raw
    return DOSSIE.gerar_dossie(doc, partes, tema)
