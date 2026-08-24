# @module routes.onr_sigri — Arquivo ONR (SIG-RI) STANDALONE.
#
# Fluxo próprio, SEPARADO dos procedimentos do Geo Urbano: o RT sobe o MAPA +
# MEMORIAL + ART/TRT + CERTIDÃO já prontos → /extrair lê a poligonal do memorial
# → /validar (motor §7) → /shapefile gera o pacote SIG-RI para o mapa.onr.org.br.
# REUTILIZA (sem alterar) geo_urbano.geo_export/validacao_onr/schema_onr e os
# parsers de extração. NÃO usa `from __future__ import annotations` (bodies).
import asyncio
import base64
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.onr_sigri import (
    OnrJob, CriarOnrBody, AtualizarOnrBody, JustificarOnrBody, AnexoBody, OrdemBody,
    ComposicaoOnrBody,
)
from services import r2_storage
from services.geo_urbano import geo_export as GEXP
from services.geo_urbano import validacao_onr as VALID
from services.geo_urbano import extractor as EX
from services.onr_sigri import extractor_onr as OX
from services.onr_sigri import satelite as SAT
from services.onr_sigri import composicao as COMP
from services.onr_sigri import dossie as DOSSIE

logger = logging.getLogger("romatec")
router = APIRouter(prefix="/topografia/onr-sigri", tags=["topografia-onr-sigri"])

_PDF = "application/pdf"
_MAX_UPLOAD = 30 * 1024 * 1024
# 4 obrigatórios (geram o pacote + informações geodésicas do Prov. 195) + 3
# opcionais (BCI/CND-IPTU/documento do proprietário) que enriquecem a descrição.
_TIPOS_UPLOAD = {"mapa", "memorial", "art_trt", "certidao",
                 "bci", "cnd_iptu", "doc_proprietario"}
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
    "trt_numero", "obs_onr", "concluido", "concluido_em")
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
# Anexos do processo — classificáveis / renomeáveis / reordenáveis / visualizáveis
# ──────────────────────────────────────────────────────────────────────────────
TIPOS_ANEXO = [
    "Certidão de Matrícula", "Escritura", "Documento Pessoal (RG/CPF/CNH)",
    "CND (Certidão Negativa)", "IPTU / BCI", "Mapa / Planta", "Memorial Descritivo",
    "ART / TRT", "Procuração", "Comprovante", "Outro",
]


@router.get("/tipos-anexo")
async def tipos_anexo(uid: str = Depends(get_active_subscriber)):
    return TIPOS_ANEXO


@router.post("/jobs/{jid}/anexo")
async def upload_anexo(jid: str, file: UploadFile = File(...), tipo: str = Form("Outro"),
                       nome: str = Form(None), uid: str = Depends(get_active_subscriber),
                       db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Arquivo vazio")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx. 30 MB)")
    ext = _ext(file.filename, file.content_type)
    aid = str(uuid.uuid4())
    key = f"onr-sigri/{uid}/{jid}/anexos/{aid}.{ext}"
    ct = _PDF if ext == "pdf" else f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
    await asyncio.to_thread(r2_storage.upload_bytes, data, key, ct)
    anexos = list(doc.get("anexos") or [])
    anexos.append({"id": aid, "key": key, "tipo": tipo or "Outro",
                   "nome": (nome or "").strip() or file.filename, "filename": file.filename,
                   "mime": ct, "ordem": len(anexos), "enviado_em": _agora().isoformat()})
    await db.onr_sigri_jobs.update_one(
        {"id": jid, "user_id": uid}, {"$set": {"anexos": anexos, "updated_at": _agora().isoformat()}})
    return {"ok": True, "anexos": anexos}


@router.patch("/jobs/{jid}/anexo/{aid}")
async def atualizar_anexo(jid: str, aid: str, body: AnexoBody,
                          uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    anexos = list(doc.get("anexos") or [])
    for a in anexos:
        if a.get("id") == aid:
            if body.nome is not None:
                a["nome"] = body.nome.strip() or a.get("filename")
            if body.tipo is not None:
                a["tipo"] = body.tipo
    await db.onr_sigri_jobs.update_one({"id": jid, "user_id": uid}, {"$set": {"anexos": anexos}})
    return {"ok": True, "anexos": anexos}


@router.post("/jobs/{jid}/anexos/ordem")
async def reordenar_anexos(jid: str, body: OrdemBody,
                           uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    by_id = {a.get("id"): a for a in (doc.get("anexos") or [])}
    nova = [by_id[i] for i in body.ordem if i in by_id]
    nova += [a for a in (doc.get("anexos") or []) if a.get("id") not in set(body.ordem)]  # sobras
    for i, a in enumerate(nova):
        a["ordem"] = i
    await db.onr_sigri_jobs.update_one({"id": jid, "user_id": uid}, {"$set": {"anexos": nova}})
    return {"ok": True, "anexos": nova}


@router.delete("/jobs/{jid}/anexo/{aid}")
async def excluir_anexo(jid: str, aid: str,
                        uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    anexos = [a for a in (doc.get("anexos") or []) if a.get("id") != aid]
    for i, a in enumerate(anexos):
        a["ordem"] = i
    await db.onr_sigri_jobs.update_one({"id": jid, "user_id": uid}, {"$set": {"anexos": anexos}})
    return {"ok": True, "restantes": len(anexos)}


@router.get("/jobs/{jid}/anexo/{aid}")
async def ver_anexo(jid: str, aid: str,
                    uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    a = next((x for x in (doc.get("anexos") or []) if x.get("id") == aid), None)
    if not a or not a.get("key"):
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    data = await asyncio.to_thread(r2_storage.download_bytes, a["key"])
    return Response(content=data, media_type=a.get("mime") or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="{a.get("filename") or aid}"'})


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

    # BCI (opcional) — enriquece cadastro municipal (inscrição/CIB/situação)
    bci_bytes = await _ub(doc, "bci")
    if bci_bytes:
        try:
            bci = await asyncio.to_thread(EX.parse_bci, bci_bytes[0])
        except Exception:  # noqa: BLE001
            bci = {}
        if bci:
            sets["bci"] = bci
            if not doc.get("inscricao_municipal") and bci.get("inscricao_contribuinte"):
                sets["inscricao_municipal"] = bci["inscricao_contribuinte"]
    # Certidão Negativa de IPTU (opcional) — regularidade fiscal
    cnd_bytes = await _ub(doc, "cnd_iptu")
    if cnd_bytes:
        try:
            iptu = await asyncio.to_thread(EX.parse_cnd, cnd_bytes[0])
            if not iptu.get("cnd_numero"):
                iptu = await asyncio.to_thread(EX.parse_iptu, cnd_bytes[0])
        except Exception:  # noqa: BLE001
            iptu = {}
        if iptu:
            sets["iptu"] = iptu

    # CNH / documento do proprietário (opcional) — completa nome/CPF se faltar
    cnh_bytes = await _ub(doc, "doc_proprietario")
    if cnh_bytes and not (sets.get("partes") or doc.get("partes")):
        try:
            cnh = await asyncio.to_thread(OX.parse_cnh, cnh_bytes[0])
        except Exception:  # noqa: BLE001
            cnh = {}
        if cnh.get("nome"):
            sets["partes"] = [{"id": str(uuid.uuid4()), "papel": "requerente", "tipo_pessoa": "fisica",
                               "nome": cnh.get("nome"), "cpf": cnh.get("doc")}]

    # Miniatura de satélite p/ o card da lista (best-effort — não trava a extração)
    verts_prev = sets.get("vertices") or doc.get("vertices")
    if verts_prev:
        try:
            png = await asyncio.to_thread(SAT.render_satelite_png, verts_prev)
            if png:
                sets["preview_b64"] = "data:image/jpeg;base64," + base64.b64encode(png).decode()
        except Exception:  # noqa: BLE001
            pass

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


@router.post("/jobs/{jid}/preview")
async def gerar_preview(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """(Re)gera a miniatura de satélite com a poligonal e guarda no job (card da lista)."""
    doc = await _get(db, jid, uid)
    png = await asyncio.to_thread(SAT.render_satelite_png, doc.get("vertices") or [])
    b64 = ("data:image/jpeg;base64," + base64.b64encode(png).decode()) if png else None
    if b64:
        await db.onr_sigri_jobs.update_one({"id": jid, "user_id": uid}, {"$set": {"preview_b64": b64}})
    return {"ok": bool(b64), "preview_b64": b64}


# ──────────────────────────────────────────────────────────────────────────────
# Composição do Dossiê de protocolo (capa/descrição + anexos ON/OFF) + Dossiê PDF
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/composicao/opcoes")
async def composicao_opcoes(uid: str = Depends(get_active_subscriber)):
    return COMP.opcoes()


@router.get("/jobs/{jid}/composicao/preview")
async def composicao_preview(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return COMP.resolver_composicao(await _get(db, jid, uid))


@router.post("/jobs/{jid}/composicao")
async def salvar_composicao(jid: str, body: ComposicaoOnrBody,
                            uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, jid, uid)
    comp = dict(doc.get("composicao") or COMP.composicao_default())
    comp.setdefault("anexos_off", list(comp.get("anexos_off") or []))
    if body.preset is not None:
        comp["preset"] = body.preset
        comp["anexos_off"] = COMP.anexos_off_do_preset(doc, body.preset)
    if body.capa is not None:
        comp["capa"] = body.capa
    if body.descricao_poligono is not None:
        comp["descricao_poligono"] = body.descricao_poligono
    if body.anexo_id is not None:                       # toggle de um anexo → PERSONALIZADO
        off = set(comp.get("anexos_off") or [])
        if body.ligada:
            off.discard(body.anexo_id)
        else:
            off.add(body.anexo_id)
        comp["anexos_off"] = list(off)
        comp["preset"] = "PERSONALIZADO"
    await db.onr_sigri_jobs.update_one(
        {"id": jid, "user_id": uid}, {"$set": {"composicao": comp, "updated_at": _agora().isoformat()}})
    return COMP.resolver_composicao({**doc, "composicao": comp})


async def _dossie_bytes(doc: dict) -> bytes:
    """Monta o Dossiê de protocolo (capa + descrição + anexos ligados na composição).

    Fonte única: o download, o envio por WhatsApp e a assinatura ICP usam este
    mesmo PDF — nenhum deles pode divergir do que o RT protocola.
    """
    comp = doc.get("composicao") or COMP.composicao_default()
    anexos_meta = COMP.anexos_ligados(doc)
    anexos = []
    for a in anexos_meta:
        if not a.get("key"):
            continue
        try:
            raw = await asyncio.to_thread(r2_storage.download_bytes, a["key"])
        except Exception:  # noqa: BLE001
            raw = None
        if raw:
            anexos.append({"nome": a.get("nome"), "mime": a.get("mime"), "bytes": raw})
    return await asyncio.to_thread(
        DOSSIE.gerar_dossie, doc, bool(comp.get("capa", True)),
        bool(comp.get("descricao_poligono", True)), anexos)


@router.get("/jobs/{jid}/dossie")
async def baixar_dossie(jid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Dossiê de protocolo (PDF): capa + descrição + anexos selecionados na composição."""
    doc = await _get(db, jid, uid)
    data = await _dossie_bytes(doc)
    nome = f"{_nome_arquivo(doc)}_Dossie.pdf"
    return Response(content=data, media_type=_PDF,
                    headers={"Content-Disposition": f'inline; filename="{nome}"'})


@router.post("/jobs/{jid}/enviar-whatsapp")
async def enviar_whatsapp(jid: str, body: dict, uid: str = Depends(get_active_subscriber),
                          db=Depends(get_db)):
    """Envia o Dossiê de protocolo por WhatsApp — mesmo fluxo dos demais módulos."""
    telefone = re.sub(r"\D", "", str((body or {}).get("telefone") or ""))
    if len(telefone) < 10:
        raise HTTPException(status_code=422, detail="Informe um WhatsApp válido (55 + DDD + número).")
    doc = await _get(db, jid, uid)
    pdf_bytes = await _dossie_bytes(doc)
    if not pdf_bytes or pdf_bytes[:5] != b"%PDF-":
        raise HTTPException(status_code=500, detail="Falha ao gerar o Dossiê.")

    from services.integracoes_util import carregar_integracoes
    cfg = await carregar_integracoes(db, uid, fallback_zapi=True)
    if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(status_code=422,
                            detail="Configure a integração Z-API (WhatsApp) antes de enviar.")

    caption = ((body or {}).get("legenda")
               or f"Dossiê de protocolo (ONR/SIG-RI) — "
                  f"{doc.get('denominacao_imovel') or doc.get('nome') or ''} "
                  f"({doc.get('numero') or ''})").strip()
    fname = f"{_nome_arquivo(doc)}_Dossie.pdf".replace("/", "-")
    from services import zapi_service
    try:
        await zapi_service.send_document_pdf(
            instance_id=cfg.get("zapi_instance_id"), token=cfg.get("zapi_token"),
            security_token=cfg.get("zapi_security_token"), phone=telefone,
            pdf_bytes=pdf_bytes, filename=fname, caption=caption)
    except Exception as e:  # noqa: BLE001
        logger.error("ONR: envio WhatsApp falhou: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Falha ao enviar pelo WhatsApp: {e}")
    return {"ok": True, "enviado": telefone}


@router.post("/jobs/{jid}/assinar")
async def preparar_assinatura(jid: str, uid: str = Depends(get_active_subscriber),
                              db=Depends(get_db)):
    """Prepara o Dossiê para o ICP-Brasil e devolve o id do registro.

    O front abre o assinador com tipo='onr' e este id — mesmo motor dos outros
    módulos (routes/assinatura), que só baixa o PDF do R2 e carimba o selo.
    """
    doc = await _get(db, jid, uid)
    pdf_bytes = await _dossie_bytes(doc)
    if not pdf_bytes or pdf_bytes[:5] != b"%PDF-":
        raise HTTPException(status_code=500, detail="Falha ao gerar o Dossiê para assinatura.")

    filtro = {"user_id": uid, "job_id": jid, "doc": "dossie"}
    existente = await db.onr_assinaturas.find_one(filtro)
    aid = existente["id"] if existente else str(uuid.uuid4())
    key = f"onr-sigri/{uid}/{jid}/assinar/dossie_{aid[:8]}.pdf"
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, pdf_bytes, key, _PDF)
    except Exception as e:  # noqa: BLE001
        logger.error("ONR: upload R2 da peça p/ assinatura falhou (%s)", e)
        raise HTTPException(status_code=502, detail="Falha ao preparar o documento.")
    try:
        import io as _io

        from pypdf import PdfReader
        paginas = len(PdfReader(_io.BytesIO(pdf_bytes)).pages)
    except Exception:  # noqa: BLE001
        paginas = 0

    nome = f"Dossiê de protocolo — {doc.get('denominacao_imovel') or doc.get('nome') or ''}".strip()
    if existente:
        # Reassinar regenera o dossiê: o PDF muda, o registro (e o id) permanece.
        await db.onr_assinaturas.update_one(
            {"id": aid}, {"$set": {"nome": nome, "pdf_key": key, "paginas": paginas,
                                   "updated_at": _agora().isoformat()}})
    else:
        await db.onr_assinaturas.insert_one({
            "id": aid, "user_id": uid, "job_id": jid, "doc": "dossie", "nome": nome,
            "pdf_key": key, "paginas": paginas, "icp_status": None,
            "created_at": _agora().isoformat()})
    return {"id": aid, "nome": nome, "paginas": paginas,
            "assinado": (existente or {}).get("icp_status") == "assinado"}


@router.get("/jobs/{jid}/assinaturas")
async def listar_assinaturas(jid: str, uid: str = Depends(get_active_subscriber),
                             db=Depends(get_db)):
    await _get(db, jid, uid)
    recs = await db.onr_assinaturas.find({"user_id": uid, "job_id": jid}).to_list(20)
    return [{"id": r["id"], "doc": r.get("doc"), "nome": r.get("nome"),
             "paginas": r.get("paginas"),
             "assinado": r.get("icp_status") == "assinado"} for r in recs]
