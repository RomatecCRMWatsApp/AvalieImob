# @module routes.onr_sigri — Arquivo ONR (SIG-RI) STANDALONE.
#
# Fluxo próprio, SEPARADO dos procedimentos do Geo Urbano: o RT sobe o MAPA +
# MEMORIAL + ART/TRT + CERTIDÃO já prontos → /extrair lê a poligonal do memorial
# → /validar (motor §7) → /shapefile gera o pacote SIG-RI para o mapa.onr.org.br.
# REUTILIZA (sem alterar) geo_urbano.geo_export/validacao_onr/schema_onr e os
# parsers de extração. NÃO usa `from __future__ import annotations` (bodies).
import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.onr_sigri import OnrJob, CriarOnrBody, AtualizarOnrBody, JustificarOnrBody
from services import r2_storage
from services.geo_urbano import geo_export as GEXP
from services.geo_urbano import validacao_onr as VALID
from services.geo_urbano import extractor as EX
from services.onr_sigri import extractor_onr as OX

logger = logging.getLogger("romatec")
router = APIRouter(prefix="/topografia/onr-sigri", tags=["topografia-onr-sigri"])

_PDF = "application/pdf"
_MAX_UPLOAD = 30 * 1024 * 1024
_TIPOS_UPLOAD = {"mapa", "memorial", "art_trt", "certidao"}
_EXT_OK = {"pdf", "png", "jpg", "jpeg", "webp"}


def _agora():
    return datetime.now(timezone.utc)


def _ext(nome, ct):
    m = re.search(r"\.([A-Za-z0-9]+)$", nome or "")
    ext = (m.group(1).lower() if m else "") or ("pdf" if (ct or "").endswith("pdf") else "bin")
    return ext if ext in _EXT_OK else ("pdf" if ext == "bin" else ext)


async def _numero(db):
    ano = _agora().year
    res = await db.counters.find_one_and_update(
        {"_id": f"onr_sigri_{ano}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=ReturnDocument.AFTER)
    return f"ONR-{ano}-{res['seq']:04d}"


async def _get(db, jid, uid):
    doc = await db.onr_sigri_jobs.find_one({"id": jid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Arquivo ONR não encontrado")
    return doc


def _projeto_view(job: dict) -> dict:
    """Shape do job para o motor SIG-RI (geo_export/schema_onr/validacao_onr):
    o campo `tipo_servico` alimenta o NAT_ATO do DBF a partir da natureza."""
    return {**job, "tipo_servico": (job.get("natureza") or "georreferenciamento")}


def _nome_arquivo(job: dict) -> str:
    """Nome do arquivo com vínculo da matrícula: SIGRI_<numero>_Matricula-<mat>."""
    base = f"SIGRI_{(job.get('numero') or job.get('id'))}"
    mats = job.get("matriculas") or []
    mat = (mats[0] or {}).get("matricula") if mats else None
    if mat:
        base += "_Matricula-" + re.sub(r"[^0-9A-Za-z.]", "", str(mat))
    return base


async def _ub(job, tipo):
    """Bytes dos uploads de um tipo (best-effort)."""
    out = []
    for it in (job.get("uploads") or {}).get(tipo, []) or []:
        if it.get("key"):
            try:
                out.append(await asyncio.to_thread(r2_storage.download_bytes, it["key"]))
            except Exception:  # noqa: BLE001
                pass
    return out


# ──────────────────────────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/jobs")
async def criar_job(body: CriarOnrBody, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    job = OnrJob(user_id=uid, nome=body.nome, natureza=body.natureza,
                 denominacao_imovel=body.nome, municipio=body.municipio, uf=body.uf,
                 numero=await _numero(db)).model_dump(mode="json")
    await db.onr_sigri_jobs.insert_one(job)
    return serialize_doc(job)


@router.get("/jobs")
async def listar_jobs(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    cur = db.onr_sigri_jobs.find({"user_id": uid}).sort("created_at", -1)
    return [serialize_doc(d) async for d in cur]


@router.get("/jobs/{jid}")
async def obter_job(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return serialize_doc(await _get(db, jid, uid))


_ESCALARES = (
    "nome", "status", "natureza", "denominacao_imovel", "municipio", "uf", "bairro",
    "loteamento", "quadra", "lote_resultante", "endereco", "numero_imovel", "cep", "unidade",
    "codigo_ibge", "cib", "inscricao_municipal", "zoneamento", "precisao_posicional_m",
    "data_levantamento", "area_declarada_m2", "perimetro_m", "fuso", "hemisferio",
    "trt_numero", "obs_onr")
_LISTAS = ("vertices", "matriculas", "partes", "confrontantes")
_DICTS = ("cartorio", "responsavel_tecnico")


@router.patch("/jobs/{jid}")
async def atualizar_job(jid: str, body: AtualizarOnrBody,
                        uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    dados = body.model_dump(exclude_unset=True)
    editados = dict(doc.get("campos_editados") or {})
    sets = {}
    for c in _ESCALARES:
        if c in dados:
            sets[c] = dados[c]
            editados[c] = True
    for c in _LISTAS:
        if c in dados and dados[c] is not None:
            sets[c] = dados[c]
            editados[c] = True
    for g in _DICTS:
        if g in dados and isinstance(dados[g], dict):
            sets[g] = {**(doc.get(g) or {}), **dados[g]}
    sets["campos_editados"] = editados
    sets["updated_at"] = _agora().isoformat()
    await db.onr_sigri_jobs.update_one({"id": jid, "user_id": uid}, {"$set": sets})
    return serialize_doc({**doc, **sets})


@router.delete("/jobs/{jid}")
async def excluir_job(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.onr_sigri_jobs.delete_one({"id": jid, "user_id": uid})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Arquivo ONR não encontrado")
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# Uploads (mapa / memorial / art_trt / certidao)
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/jobs/{jid}/upload")
async def upload_documento(jid: str, tipo: str = Form(...), file: UploadFile = File(...),
                           uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    if tipo not in _TIPOS_UPLOAD:
        raise HTTPException(status_code=422, detail=f"Tipo inválido. Use: {sorted(_TIPOS_UPLOAD)}")
    doc = await _get(db, jid, uid)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Arquivo vazio")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx. 30 MB)")
    ext = _ext(file.filename, file.content_type)
    item_id = str(uuid.uuid4())
    key = f"onr-sigri/{uid}/{jid}/{tipo}/{item_id}.{ext}"
    ct = _PDF if ext == "pdf" else f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
    await asyncio.to_thread(r2_storage.upload_bytes, data, key, ct)
    item = {"id": item_id, "key": key, "nome": file.filename, "mime": ct,
            "enviado_em": _agora().isoformat()}
    uploads = dict(doc.get("uploads") or {})
    uploads[tipo] = [item]  # 1 arquivo por tipo (substitui)
    await db.onr_sigri_jobs.update_one(
        {"id": jid, "user_id": uid}, {"$set": {"uploads": uploads, "updated_at": _agora().isoformat()}})
    return {"ok": True, "tipo": tipo, "item": item}


@router.delete("/jobs/{jid}/uploads/{tipo}/{item_id}")
async def remover_upload(jid: str, tipo: str, item_id: str,
                         uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    uploads = dict(doc.get("uploads") or {})
    uploads[tipo] = [it for it in (uploads.get(tipo) or []) if it.get("id") != item_id]
    await db.onr_sigri_jobs.update_one(
        {"id": jid, "user_id": uid}, {"$set": {"uploads": uploads, "updated_at": _agora().isoformat()}})
    return {"ok": True, "restantes": len(uploads.get(tipo) or [])}


# ──────────────────────────────────────────────────────────────────────────────
# Extração (memorial → poligonal + dados) — mapa é anexo, certidão OCR opcional
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/jobs/{jid}/extrair")
async def extrair(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    mems = await _ub(doc, "memorial")
    if not mems:
        raise HTTPException(status_code=422, detail="Envie o Memorial Descritivo (PDF) antes de extrair.")
    ext = await asyncio.to_thread(OX.parse_memorial_onr, mems[0])

    sets = {}
    for c in ("denominacao_imovel", "municipio", "uf", "area_declarada_m2", "perimetro_m",
              "fuso", "hemisferio"):
        if ext.get(c) is not None:
            sets[c] = ext[c]
    if ext.get("vertices"):
        sets["vertices"] = ext["vertices"]
        # confrontantes derivados dos lados (dedup) para a UI/DBF
        vistos, conf = set(), []
        for v in ext["vertices"]:
            c = v.get("confrontante_lado")
            if c and c not in vistos:
                vistos.add(c)
                conf.append({"lado": "", "confrontante": c, "tipo": "particular"})
        sets["confrontantes"] = conf
    prop = ext.get("proprietario") or {}
    if prop.get("nome"):
        sets["partes"] = [{"id": str(uuid.uuid4()), "papel": "requerente", "tipo_pessoa": "fisica",
                           "nome": prop.get("nome"), "cpf": prop.get("doc")}]
    mat = ext.get("matricula") or {}
    if mat.get("matricula"):
        sets["matriculas"] = [{"id": str(uuid.uuid4()), "matricula": mat.get("matricula"),
                               "livro": mat.get("livro"), "folhas": mat.get("folhas"),
                               "cri": mat.get("cri"), "area_m2": ext.get("area_declarada_m2")}]
        sets["cartorio"] = {**(doc.get("cartorio") or {}),
                            "nome": (doc.get("cartorio") or {}).get("nome")
                            or f"Registro de Imóveis de {mat.get('cri') or ''}".strip(),
                            "cns": mat.get("cns"), "comarca": mat.get("cri")}
    rt = ext.get("responsavel_tecnico") or {}
    if rt:
        sets["responsavel_tecnico"] = {**(doc.get("responsavel_tecnico") or {}), **rt}
    # ART/TRT → número (best-effort do arquivo enviado)
    if not doc.get("trt_numero"):
        arts = (doc.get("uploads") or {}).get("art_trt") or []
        art_bytes = await _ub(doc, "art_trt")
        if art_bytes:
            num = await asyncio.to_thread(EX.parse_art_trt, art_bytes[0], (arts[0] or {}).get("nome", ""))
            if num:
                sets["trt_numero"] = num

    sets.update(status="extraido", extracao_em=_agora().isoformat(), extracao_por=uid,
                extracao_confianca=ext.get("_confianca"), extracao_avisos=ext.get("_avisos") or [],
                updated_at=_agora().isoformat())
    await db.onr_sigri_jobs.update_one({"id": jid, "user_id": uid}, {"$set": sets})
    return {"ok": True, "confianca": ext.get("_confianca"), "avisos": ext.get("_avisos") or [],
            "job": serialize_doc({**doc, **sets})}


# ──────────────────────────────────────────────────────────────────────────────
# Validação SIG-RI/ONR (motor §7 reusado)
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/jobs/{jid}/validar")
async def validar_job(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    res = await asyncio.to_thread(VALID.validar, _projeto_view(doc))
    await db.onr_sigri_jobs.update_one(
        {"id": jid, "user_id": uid},
        {"$set": {"onr_validacao": {**res, "em": _agora().isoformat()},
                  "status": "validado" if res.get("pode_gerar") else doc.get("status", "extraido")}})
    return res


@router.post("/jobs/{jid}/justificar")
async def justificar_job(jid: str, body: JustificarOnrBody,
                         uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    if not (body.codigo or "").strip() or not (body.texto or "").strip():
        raise HTTPException(status_code=422, detail="Informe o código do alerta e a justificativa.")
    just = [j for j in (doc.get("onr_justificativas") or []) if j.get("codigo") != body.codigo]
    just.append({"codigo": body.codigo.strip(), "texto": body.texto.strip(),
                 "por": uid, "em": _agora().isoformat()})
    doc["onr_justificativas"] = just
    res = await asyncio.to_thread(VALID.validar, _projeto_view(doc))
    await db.onr_sigri_jobs.update_one(
        {"id": jid, "user_id": uid},
        {"$set": {"onr_justificativas": just, "onr_validacao": {**res, "em": _agora().isoformat()}}})
    return res


# ──────────────────────────────────────────────────────────────────────────────
# Geração — pacote SIG-RI (.zip) + KML + GeoJSON (motor reusado)
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/jobs/{jid}/shapefile")
async def baixar_shapefile(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    try:
        data = await asyncio.to_thread(GEXP.gerar_shapefile_bytes, _projeto_view(doc))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.onr_sigri_jobs.update_one({"id": jid, "user_id": uid}, {"$set": {"status": "gerado"}})
    nome = f"{_nome_arquivo(doc)}.zip"
    return Response(content=data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@router.get("/jobs/{jid}/kml")
async def baixar_kml(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    kml = await asyncio.to_thread(GEXP.gerar_kml, _projeto_view(doc))
    nome = f"{_nome_arquivo(doc)}.kml"
    return Response(content=kml.encode("utf-8"), media_type="application/vnd.google-earth.kml+xml",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@router.get("/jobs/{jid}/geojson")
async def baixar_geojson(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    return GEXP.gerar_geojson(_projeto_view(doc))
