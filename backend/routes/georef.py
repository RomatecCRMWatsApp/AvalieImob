# @module routes.georef — Topografia & Geo (Georreferenciamento / Requerimentos Cartoriais).
#
# Fluxo: cria projeto -> upload (Memorial/Mapa/CCIR/Certidão/doc cliente) -> /extrair
# (pdfplumber popula imóvel/vértices/confrontantes/cadeia) -> conferência (PATCH) ->
# /gerar -> downloads (Requerimento, Laudo, Memorial, DRLs, Shapefile, Dossiê) em
# PDF/DOCX. Geração pesada (ReportLab/pdfplumber/R2) roda fora do event loop.
import asyncio
import io
import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.georef import (
    GeorefProjeto, Parcela, CriarProjetoBody, AtualizarProjetoBody, GerarDocumentosBody,
    AdicionarParcelaBody, AssinarPecaBody, calcular_completude,
)
from services import r2_storage
from services.georef import extractor as EX
from services.georef import geo as GEO
from services.georef.parcelas import parcelas_do_projeto, projeto_da_parcela, tem_multiparcela
from services.georef.cadeia_dominial import parse_cadeia_dominial
from services.georef.generators import textos as TX
from services.georef.generators import pdf as PDF
from services.georef.generators import docx as DOCX
from services.georef.generators import dossie as DOSSIE

logger = logging.getLogger("romatec")
router = APIRouter(prefix="/topografia/georef", tags=["topografia-geo"])

_TIPOS_UPLOAD = {"memorial", "mapa", "ccir", "certidao", "art_trt", "car", "itr", "doc_cliente"}
# Tipos que aceitam VÁRIOS arquivos (lista) — ITR: últimos 5 exercícios.
_TIPOS_MULTI = {"itr"}
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

    for grupo in ("vertices", "confrontantes", "parcelas"):
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
    item_id = str(uuid.uuid4())
    multi = tipo in _TIPOS_MULTI
    key = (f"topografia/{uid}/{pid}/{tipo}/{item_id}.{ext}" if multi
           else f"topografia/{uid}/{pid}/{tipo}.{ext}")
    ct = file.content_type or _MIME.get(ext, "application/octet-stream")
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, data, key, ct)
    except Exception as e:  # noqa: BLE001
        logger.error("Topografia: falha no upload R2 (%s)", e)
        raise HTTPException(status_code=502, detail="Falha ao armazenar o arquivo")

    info = {"id": item_id, "key": key, "filename": file.filename, "content_type": ct,
            "ext": ext, "uploaded_at": _agora().isoformat()}
    uploads = dict(doc.get("uploads") or {})
    if multi:
        atual = uploads.get(tipo)
        if isinstance(atual, dict):       # legado (era 1 só)
            atual = [atual]
        atual = list(atual or [])
        atual.append(info)
        uploads[tipo] = atual
    else:
        uploads[tipo] = info
    await db.georef_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"uploads": uploads, "updated_at": _agora().isoformat()}},
    )
    return {"ok": True, "tipo": tipo, "item": info, "uploads": list(uploads.keys())}


@router.delete("/projetos/{pid}/uploads/{tipo}/{item_id}")
async def remover_upload_item(pid: str, tipo: str, item_id: str,
                             uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Remove UM arquivo de um upload multi (ex.: um exercício do ITR)."""
    doc = await _get_projeto(db, pid, uid)
    uploads = dict(doc.get("uploads") or {})
    atual = uploads.get(tipo)
    if isinstance(atual, dict):
        atual = [atual]
    atual = [x for x in (atual or []) if x.get("id") != item_id and x.get("key") != item_id]
    uploads[tipo] = atual
    await db.georef_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"uploads": uploads, "updated_at": _agora().isoformat()}})
    return {"ok": True}


_ROMANOS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


@router.post("/projetos/{pid}/parcelas", status_code=201)
async def adicionar_parcela(pid: str, body: AdicionarParcelaBody,
                           uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    parcelas = list(doc.get("parcelas") or [])
    n = len(parcelas) + 2  # +1 (principal é Parte I) +1 (1-based)
    rotulo = body.rotulo or f"Parte {_ROMANOS[n - 1] if n <= len(_ROMANOS) else n}"
    nova = Parcela(rotulo=rotulo).model_dump(mode="json")
    parcelas.append(nova)
    await db.georef_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"parcelas": parcelas, "updated_at": _agora().isoformat()}})
    return nova


@router.delete("/projetos/{pid}/parcelas/{parcela_id}")
async def remover_parcela(pid: str, parcela_id: str,
                         uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    parcelas = [p for p in (doc.get("parcelas") or []) if p.get("id") != parcela_id]
    await db.georef_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"parcelas": parcelas, "updated_at": _agora().isoformat()}})
    return {"ok": True}


@router.post("/projetos/{pid}/parcelas/{parcela_id}/upload")
async def upload_parcela(pid: str, parcela_id: str, tipo: str = Form(...),
                        file: UploadFile = File(...),
                        uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    if tipo not in ("memorial", "mapa"):
        raise HTTPException(status_code=422, detail="Tipo inválido. Use: memorial, mapa")
    doc = await _get_projeto(db, pid, uid)
    parcelas = list(doc.get("parcelas") or [])
    idx = next((i for i, p in enumerate(parcelas) if p.get("id") == parcela_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Arquivo vazio")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx. 30 MB)")
    ext = _ext_arquivo(file.filename, file.content_type)
    key = f"topografia/{uid}/{pid}/parcela_{parcela_id}/{tipo}.{ext}"
    ct = file.content_type or _MIME.get(ext, "application/octet-stream")
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, data, key, ct)
    except Exception as e:  # noqa: BLE001
        logger.error("Topografia: upload R2 da parcela falhou (%s)", e)
        raise HTTPException(status_code=502, detail="Falha ao armazenar o arquivo")
    uploads = dict(parcelas[idx].get("uploads") or {})
    uploads[tipo] = {"key": key, "filename": file.filename, "content_type": ct,
                     "ext": ext, "uploaded_at": _agora().isoformat()}
    parcelas[idx]["uploads"] = uploads
    extraido = False
    # Memorial da parcela: extrai os dados (vértices/área/denominação) JÁ NO UPLOAD,
    # direto dos bytes — não depende de clicar "Extrair" de novo nem do R2.
    if tipo == "memorial":
        try:
            resp = await asyncio.to_thread(EX.parse_memorial, data)
            ph = resp.get("imovel") or {}
            for k in ("denominacao", "natureza_area", "area_ha", "perimetro_m",
                      "sistema_geodesico", "certificacao_sigef"):
                if ph.get(k) not in (None, ""):
                    parcelas[idx][k] = ph.get(k)
            if resp.get("vertices"):
                parcelas[idx]["vertices"] = resp["vertices"]
                mat = (doc.get("imovel") or {}).get("matricula")
                parcelas[idx]["confrontantes"] = EX.agrupar_confrontantes(
                    resp["vertices"], matricula_imovel=mat)
                extraido = True
        except Exception as e:  # noqa: BLE001
            logger.warning("Topografia: parse do memorial da parcela %s falhou (%s)", parcela_id, e)
    await db.georef_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"parcelas": parcelas, "updated_at": _agora().isoformat()}})
    return {"ok": True, "parcela_id": parcela_id, "tipo": tipo,
            "extraido": extraido, "parcela": parcelas[idx]}


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

    # Cartório: resolve nome/comarca/UF pelo CNS (tabela oficial de serventias)
    try:
        from services.georef.serventias import enriquecer_cartorio
        enriquecer_cartorio(imovel, editados)
    except Exception as e:  # noqa: BLE001
        avisos.append(f"Serventia não resolvida pelo CNS ({e}).")

    if not editados.get("confrontantes"):
        confrontantes = EX.agrupar_confrontantes(vertices, matricula_imovel=imovel.get("matricula"))
    else:
        confrontantes = doc.get("confrontantes") or []

    val = GEO.validar_geometria(vertices, area_ha_sigef=imovel.get("area_ha"))
    avisos.extend(val.get("avisos") or [])

    # Parcelas adicionais (desmembramento): parseia o memorial de cada uma
    parcelas = [dict(p) for p in (doc.get("parcelas") or [])]
    for parc in parcelas:
        raw_p = _download_upload(parc.get("uploads") or {}, "memorial")
        if not raw_p:
            continue
        resp = EX.parse_memorial(raw_p)
        ph = resp.get("imovel") or {}
        for k in ("denominacao", "natureza_area", "area_ha", "perimetro_m",
                  "sistema_geodesico", "certificacao_sigef"):
            if ph.get(k) not in (None, ""):
                parc[k] = ph.get(k)
        if resp.get("vertices"):
            parc["vertices"] = resp["vertices"]
            parc["confrontantes"] = EX.agrupar_confrontantes(
                resp["vertices"], matricula_imovel=imovel.get("matricula"))

    novo = {**doc, "imovel": imovel, "responsavel_tecnico": rt,
            "vertices": vertices, "confrontantes": confrontantes, "parcelas": parcelas}
    return {
        "imovel": imovel, "responsavel_tecnico": rt,
        "vertices": vertices, "confrontantes": confrontantes, "parcelas": parcelas,
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


@router.get("/serventias")
async def buscar_serventia(cns: str = Query(...), uid: str = Depends(get_active_subscriber)):
    """Resolve o cartório (serventia + comarca/UF) pelo CNS (tabela oficial CNJ)."""
    from services.georef.serventias import buscar_serventia as _busca
    s = _busca(cns)
    if not s:
        raise HTTPException(status_code=404, detail="CNS não encontrado na tabela de serventias.")
    return s


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


def _doc_para_memorial(doc: dict, parcela_id: str) -> dict:
    """Sub-projeto da parcela pedida (ou o principal quando vazio/'principal')."""
    if not parcela_id or parcela_id == "principal":
        return doc
    pv = next((p for p in parcelas_do_projeto(doc) if p.get("id") == parcela_id), None)
    return projeto_da_parcela(doc, pv) if pv else doc


@router.get("/projetos/{pid}/documentos/{tipo}")
async def baixar_documento(pid: str, tipo: str, fmt: str = Query("pdf"),
                          tema: str = Query(None), parcela: str = Query(None),
                          uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    tema = tema or doc.get("tema_pdf") or "prime_i"
    nb = _nome_base(doc)

    if tipo == "dossie":
        assinados = await _carregar_pecas_assinadas(db, pid, uid)
        data = await asyncio.to_thread(_montar_dossie, doc, tema, assinados)
        return _resp(data, "pdf", f"Dossie_{nb}.pdf", inline=(fmt != "download"))

    if tipo not in ("requerimento", "memorial", "laudo_tecnico"):
        raise HTTPException(status_code=404, detail="Documento desconhecido")

    # Memorial pode ser de uma parcela específica (?parcela=<id>)
    alvo = _doc_para_memorial(doc, parcela) if tipo == "memorial" else doc
    sufixo = f"_p{parcela[:6]}" if (tipo == "memorial" and parcela and parcela != "principal") else ""

    if fmt == "docx":
        data = await asyncio.to_thread(DOCX.gerar_docx, tipo, alvo)
        return _resp(data, "docx", f"{tipo}{sufixo}_{nb}.docx")
    data = await asyncio.to_thread(PDF.gerar_pdf, tipo, alvo, tema)
    return _resp(data, "pdf", f"{tipo}{sufixo}_{nb}.pdf", inline=True)


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


def _memoriais_combinados(doc: dict, tema: str, assinados: dict = None) -> bytes:
    """Memorial do principal + de cada parcela adicional, mesclados em 1 PDF.
    Se a peça já foi assinada (ICP), usa a versão ASSINADA em vez de regerar."""
    import io as _io
    from pypdf import PdfReader, PdfWriter
    assinados = assinados or {}

    def _mem(alvo: dict, parc_key: str) -> bytes:
        b = assinados.get(("memorial", parc_key))
        return b if b else PDF.gerar_pdf("memorial", alvo, tema)

    pdfs = [_mem(doc, "principal")]
    if tem_multiparcela(doc):
        for pv in parcelas_do_projeto(doc):
            if pv.get("principal"):
                continue
            pdfs.append(_mem(projeto_da_parcela(doc, pv), pv.get("id")))
    if len(pdfs) == 1:
        return pdfs[0]
    w = PdfWriter()
    for raw in pdfs:
        for pg in PdfReader(_io.BytesIO(raw)).pages:
            w.add_page(pg)
    buf = _io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _itr_por_exercicio(itens: list) -> list:
    """Ordena os ITR pelo ano (exercício) presente no nome do arquivo (2021→2025)."""
    import re as _re

    def _chave(it):
        m = _re.search(r"(19|20)\d{2}", it.get("filename") or "")
        return (int(m.group(0)) if m else 0, it.get("filename") or "", it.get("uploaded_at") or "")
    return sorted(itens, key=_chave)


def _montar_dossie(doc: dict, tema: str, assinados: dict = None) -> bytes:
    """`assinados`: {(doc, parcela): bytes} das peças JÁ assinadas (ICP) — usadas
    no lugar das geradas, para o Dossiê sair com as assinaturas."""
    assinados = assinados or {}

    def _peca(kind, gen):
        b = assinados.get((kind, None))
        return b if b else gen()

    partes = {
        "requerimento": _peca("requerimento", lambda: PDF.gerar_pdf("requerimento", doc, tema)),
        "laudo_tecnico": _peca("laudo", lambda: PDF.gerar_pdf("laudo_tecnico", doc, tema)),
        "memorial": _memoriais_combinados(doc, tema, assinados),
        "drl": [PDF.gerar_pdf("drl", doc, tema, c) for c in TX.confrontantes_para_drl(doc)],
    }
    uploads = doc.get("uploads") or {}
    # ART/TRT: versão assinada se houver; senão o arquivo enviado
    art_assinado = assinados.get(("art_trt", None))
    loop_items = [("ccir", "ccir"), ("car", "car"),
                  ("certidao_matricula", "certidao"), ("doc_cliente", "doc_cliente")]
    if art_assinado:
        partes["art_trt"] = art_assinado
    else:
        loop_items.insert(0, ("art_trt", "art_trt"))
    for chave, tipo_up in loop_items:
        raw = _download_upload(uploads, tipo_up)
        if raw:
            partes[chave] = raw
    # ITR: vários exercícios (lista) — ordena por ano e baixa todos
    itr_itens = uploads.get("itr")
    if isinstance(itr_itens, dict):
        itr_itens = [itr_itens]
    itr_bytes = []
    for it in _itr_por_exercicio(list(itr_itens or [])):
        if it.get("key"):
            try:
                itr_bytes.append(r2_storage.download_bytes(it["key"]))
            except Exception:  # noqa: BLE001
                pass
    if itr_bytes:
        partes["itr"] = itr_bytes
    return DOSSIE.gerar_dossie(doc, partes, tema)


async def _carregar_pecas_assinadas(db, pid: str, uid: str) -> dict:
    """{(doc, parcela_norm): bytes} das peças já assinadas (ICP) deste projeto.
    parcela_norm: para memorial 'principal' ou id da parcela; senão None."""
    from routes.assinatura import _load_assinatura_bytes
    out: dict = {}
    recs = await db.georef_assinaturas.find(
        {"user_id": uid, "projeto_id": pid, "icp_status": "assinado"}).to_list(300)
    for r in recs:
        try:
            b, _ = await _load_assinatura_bytes(db, "georef", r["id"])
        except Exception:  # noqa: BLE001
            b = None
        if not b or b[:5] != b"%PDF-":
            continue
        dock = r.get("doc")
        parc = (r.get("parcela") or "principal") if dock == "memorial" else None
        out[(dock, parc)] = b
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Preparar peça para assinatura ICP-Brasil (reusa o módulo de assinatura, tipo="georef")
# ──────────────────────────────────────────────────────────────────────────────
_DOC_NOMES = {
    "memorial": "Memorial Descritivo",
    "laudo": "Laudo Técnico de Agrimensura",
    "requerimento": "Requerimento ao Cartório",
    "dossie": "Dossiê Consolidado",
    "art_trt": "ART/TRT",
}


def _pdf_para_assinatura(doc: dict, tipo_doc: str, parcela: str, tema: str,
                         assinados: dict = None) -> bytes:
    if tipo_doc == "memorial":
        return PDF.gerar_pdf("memorial", _doc_para_memorial(doc, parcela), tema)
    if tipo_doc == "laudo":
        return PDF.gerar_pdf("laudo_tecnico", doc, tema)
    if tipo_doc == "requerimento":
        return PDF.gerar_pdf("requerimento", doc, tema)
    if tipo_doc == "dossie":
        return _montar_dossie(doc, tema, assinados)
    if tipo_doc == "art_trt":
        raw = _download_upload(doc.get("uploads") or {}, "art_trt")
        if not raw:
            raise ValueError("ART/TRT não enviada (suba na etapa Upload).")
        if raw[:5] == b"%PDF-":
            return raw
        from services.georef.generators.dossie import _img_para_pdf
        return _img_para_pdf(raw)
    raise ValueError(f"Documento desconhecido para assinatura: {tipo_doc}")


@router.post("/projetos/{pid}/assinar")
async def preparar_assinatura(pid: str, body: AssinarPecaBody,
                             uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Gera a peça pedida, guarda no R2 e cria o registro `georef_assinaturas`.
    O front então abre o assinador ICP com tipo='georef' e este id."""
    doc = await _get_projeto(db, pid, uid)
    if body.doc not in _DOC_NOMES:
        raise HTTPException(status_code=422, detail="Documento inválido para assinatura.")
    tema = body.tema or doc.get("tema_pdf") or "prime_i"
    # Dossiê assinado deve EMBUTIR as peças que já foram assinadas individualmente.
    assinados = await _carregar_pecas_assinadas(db, pid, uid) if body.doc == "dossie" else None
    try:
        pdf_bytes = await asyncio.to_thread(
            _pdf_para_assinatura, doc, body.doc, body.parcela, tema, assinados)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not pdf_bytes or pdf_bytes[:5] != b"%PDF-":
        raise HTTPException(status_code=500, detail="Falha ao gerar o PDF para assinatura.")

    # Registro ESTÁVEL por (projeto, doc, parcela) — reusa o mesmo id (não duplica;
    # preserva o status de assinado entre preparações/reassinaturas).
    filtro = {"user_id": uid, "projeto_id": pid, "doc": body.doc, "parcela": body.parcela}
    existente = await db.georef_assinaturas.find_one(filtro)
    aid = existente["id"] if existente else str(uuid.uuid4())
    key = f"georef/{uid}/{pid}/assinar/{body.doc}_{aid[:8]}.pdf"
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, pdf_bytes, key, "application/pdf")
    except Exception as e:  # noqa: BLE001
        logger.error("Topografia: upload R2 da peça p/ assinatura falhou (%s)", e)
        raise HTTPException(status_code=502, detail="Falha ao preparar o documento.")
    try:
        from pypdf import PdfReader
        paginas = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception:  # noqa: BLE001
        paginas = 0

    rotulo = ""
    if body.doc == "memorial" and body.parcela and body.parcela != "principal":
        pv = next((p for p in parcelas_do_projeto(doc) if p.get("id") == body.parcela), None)
        rotulo = f" ({pv.get('rotulo')})" if pv else ""
    elif body.doc == "memorial":
        rotulo = " (Parte I)" if tem_multiparcela(doc) else ""
    nome = f"{_DOC_NOMES[body.doc]}{rotulo} — {_nome_base(doc)}"
    if existente:
        await db.georef_assinaturas.update_one(
            {"id": aid},
            {"$set": {"nome": nome, "pdf_key": key, "paginas": paginas, "tema": tema,
                      "updated_at": _agora().isoformat()}})
    else:
        rec = {"id": aid, "user_id": uid, "projeto_id": pid, "doc": body.doc, "parcela": body.parcela,
               "nome": nome, "pdf_key": key, "paginas": paginas, "icp_status": None,
               "tema": tema, "created_at": _agora().isoformat()}
        await db.georef_assinaturas.insert_one(rec)
    return {"id": aid, "nome": nome, "paginas": paginas,
            "assinado": (existente or {}).get("icp_status") == "assinado"}


@router.get("/projetos/{pid}/assinaturas")
async def listar_assinaturas(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Status de assinatura ICP de cada peça do projeto (persiste — não some)."""
    await _get_projeto(db, pid, uid)   # valida posse
    recs = await db.georef_assinaturas.find(
        {"user_id": uid, "projeto_id": pid}).to_list(300)
    return [{"id": r["id"], "doc": r.get("doc"), "parcela": r.get("parcela"),
             "assinado": r.get("icp_status") == "assinado",
             "assinado_em": r.get("icp_assinado_em") or r.get("updated_at"),
             "nome": r.get("nome"), "paginas": r.get("paginas")} for r in recs]
