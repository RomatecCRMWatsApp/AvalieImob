# @module routes.georef — Topografia & Geo (Georreferenciamento / Requerimentos Cartoriais).
#
# Fluxo: cria projeto -> upload (Memorial/Mapa/CCIR/Certidão/doc cliente) -> /extrair
# (pdfplumber popula imóvel/vértices/confrontantes/cadeia) -> conferência (PATCH) ->
# /gerar -> downloads (Requerimento, Laudo, Memorial, DRLs, Shapefile, Dossiê) em
# PDF/DOCX. Geração pesada (ReportLab/pdfplumber/R2) roda fora do event loop.
import asyncio
import hashlib
import io
import logging
import os
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

    for campo in ("nome_projeto", "tipo_servico", "tema_pdf", "status",
                  "laudo_modo", "normalizar_denominacao"):
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
        atual = [x for x in (atual or []) if isinstance(x, dict)]
        for x in atual:                   # legado sem id → atribui um (p/ poder remover)
            if not x.get("id"):
                x["id"] = str(uuid.uuid4())
        atual.append(info)
        uploads[tipo] = atual
    else:
        uploads[tipo] = info
    await db.georef_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"uploads": uploads, "updated_at": _agora().isoformat()}},
    )
    return {"ok": True, "tipo": tipo, "item": info, "uploads": list(uploads.keys())}


@router.delete("/projetos/{pid}/uploads/{tipo}/{item_id:path}")
async def remover_upload_item(pid: str, tipo: str, item_id: str,
                             uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Remove UM arquivo de um upload multi (ex.: um exercício do ITR).
    `item_id` aceita o id OU a key (que tem barras — por isso o conversor :path)."""
    doc = await _get_projeto(db, pid, uid)
    uploads = dict(doc.get("uploads") or {})
    atual = uploads.get(tipo)
    if isinstance(atual, dict):
        atual = [atual]
    atual = [x for x in (atual or []) if isinstance(x, dict)]
    restantes = [x for x in atual if x.get("id") != item_id and x.get("key") != item_id]
    removeu = len(restantes) != len(atual)
    uploads[tipo] = restantes
    await db.georef_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"uploads": uploads, "updated_at": _agora().isoformat()}})
    return {"ok": True, "removido": removeu, "restantes": len(restantes)}


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
    cert_fields = {}
    if raw_cert:
        # Dados REGISTRAIS do imóvel de ORIGEM (área/perímetro/denominação da matrícula)
        # + serventia/comarca (fonte autoritativa, prioritária sobre o CNS).
        try:
            cert_fields = EX.parse_matricula(raw_cert)
            _set_imovel(cert_fields)
        except Exception as e:  # noqa: BLE001
            avisos.append(f"Dados da matrícula não extraídos ({e}).")
        if not editados.get("imovel.cadeia_dominial"):
            try:
                cadeia = parse_cadeia_dominial(raw_cert)
                if cadeia:
                    imovel["cadeia_dominial"] = cadeia
            except Exception as e:  # noqa: BLE001
                avisos.append(f"Cadeia dominial não extraída ({e}).")

    # CAR (Cadastro Ambiental Rural): o nº de registro vem no NOME do arquivo (UF-IBGE-HASH).
    car_nome = (uploads.get("car") or {}).get("filename") or ""
    if car_nome and not editados.get("imovel.car"):
        import re as _re
        mcar = _re.search(r"([A-Z]{2}-\d{5,8}-[A-F0-9]{20,})", car_nome.upper())
        if mcar:
            imovel["car"] = mcar.group(1)

    # Cartório: resolve nome/comarca/UF pelo CNS (tabela oficial de serventias).
    # A CERTIDÃO é autoritativa — trava os campos que ela já forneceu p/ o CNS não
    # sobrescrever (ex.: serventia de São Francisco do Brejão vs. cidade do CNS).
    try:
        from services.georef.serventias import enriquecer_cartorio
        locked = dict(editados)
        for k in ("cartorio_nome", "cartorio_municipio", "cartorio_uf"):
            if cert_fields.get(k):
                locked[f"imovel.{k}"] = True
        enriquecer_cartorio(imovel, locked)
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


async def _injetar_logo(db, uid: str, doc: dict) -> dict:
    """Carrega o logo PRÓPRIO do usuário (white-label) e injeta em `doc` p/ sair
    no cabeçalho de TODAS as peças técnicas. Sem logo próprio → usa o padrão."""
    try:
        from services.branding_context import BrandContext
        brand = await BrandContext.for_user(db, uid)
        logo = await asyncio.to_thread(brand.custom_logo_bytes)
        if logo:
            doc["_brand_logo_bytes"] = logo
    except Exception as e:  # noqa: BLE001
        logger.warning("Topografia: logo white-label indisponível (%s)", e)
    return doc


_APP_URL = os.environ.get("APP_PUBLIC_URL", "https://www.romatecavalieimob.com.br").rstrip("/") \
    .replace("://romatecavalieimob.com.br", "://www.romatecavalieimob.com.br")


def _seal_code(pid: str, kind: str, parcela: str = None) -> str:
    """Código de verificação determinístico (SHA-256) por peça."""
    raw = f"GEO:{pid}:{kind}:{parcela or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24].upper()


def _verify_url(code: str) -> str:
    return f"{_APP_URL}/api/topografia/georef/verificar/{code}"


async def _aplicar_selo(db, uid: str, doc: dict, kind: str, parcela: str = None) -> str:
    """Registra a verificação (upsert) e injeta o código/URL no doc p/ o selo no PDF."""
    code = _seal_code(doc["id"], kind, parcela)
    doc["_seal_code"] = code
    doc["_verify_url"] = _verify_url(code)
    im = doc.get("imovel") or {}
    rt = doc.get("responsavel_tecnico") or {}
    try:
        await db.georef_verificacoes.update_one(
            {"code": code, "user_id": uid},
            {"$set": {
                "code": code, "user_id": uid, "projeto_id": doc["id"], "doc": kind,
                "parcela": parcela, "tipo_servico": doc.get("tipo_servico"),
                "denominacao": im.get("denominacao_matricula") or im.get("denominacao"),
                "matricula": im.get("matricula"), "rt_nome": rt.get("nome"),
                "rt_conselho": rt.get("conselho"), "atualizado_em": _agora().isoformat()},
             "$setOnInsert": {"criado_em": _agora().isoformat()}},
            upsert=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("Topografia: registro de verificação falhou (%s)", e)
    return code


def _laudo_modo(doc: dict, override: str = None) -> str:
    m = (override or doc.get("laudo_modo") or "unificado").lower()
    return m if m in ("unificado", "separado") else "unificado"


async def _registrar_selo_parte(db, uid: str, doc: dict, kind: str,
                                parcela_rotulo: str, parcela_denom: str = None) -> dict:
    """Registra a verificação de UMA peça por-parcela (laudo separado) → {code, url}."""
    code = _seal_code(doc["id"], kind, parcela_rotulo)
    im = doc.get("imovel") or {}
    rt = doc.get("responsavel_tecnico") or {}
    try:
        await db.georef_verificacoes.update_one(
            {"code": code, "user_id": uid},
            {"$set": {
                "code": code, "user_id": uid, "projeto_id": doc["id"], "doc": kind,
                "parcela": parcela_rotulo, "tipo_servico": doc.get("tipo_servico"),
                "denominacao": parcela_denom or im.get("denominacao_matricula") or im.get("denominacao"),
                "matricula": im.get("matricula"), "rt_nome": rt.get("nome"),
                "rt_conselho": rt.get("conselho"), "atualizado_em": _agora().isoformat()},
             "$setOnInsert": {"criado_em": _agora().isoformat()}},
            upsert=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("Topografia: selo de parcela falhou (%s)", e)
    return {"code": code, "url": _verify_url(code)}


async def _selos_laudos_separados(db, uid: str, doc: dict) -> dict:
    """{rotulo: {code,url}} — um selo SHA-256/QR por laudo separado (por parcela)."""
    seals = {}
    for pv in parcelas_do_projeto(doc):
        seals[pv.get("rotulo")] = await _registrar_selo_parte(
            db, uid, doc, "laudo", pv.get("rotulo"), pv.get("denominacao"))
    return seals


@router.get("/verificar/{code}")
async def verificar_documento(code: str, db=Depends(get_db)):
    """Página PÚBLICA de verificação de autenticidade (QR do selo aponta aqui)."""
    rec = await db.georef_verificacoes.find_one({"code": code})
    nomes = {"requerimento": "Requerimento de Georreferenciamento",
             "laudo": "Laudo Técnico de Agrimensura"}
    if not rec:
        corpo = ('<h1>Documento não localizado</h1><p>O código informado não consta na base de '
                 'verificação da AvalieImob. Confira o código do selo.</p>')
        status = 404
    else:
        peca = nomes.get(rec.get("doc"), rec.get("doc") or "Documento")
        corpo = (
            f'<h1>✓ Documento autêntico</h1>'
            f'<p>Este selo confirma que o documento foi emitido pelo sistema '
            f'<b>AvalieImob — Topografia &amp; Geo</b>.</p>'
            f'<table>'
            f'<tr><td>Peça</td><td><b>{peca}</b></td></tr>'
            f'<tr><td>Imóvel</td><td>{rec.get("denominacao") or "—"}</td></tr>'
            f'<tr><td>Matrícula</td><td>{rec.get("matricula") or "—"}</td></tr>'
            f'<tr><td>Serviço</td><td>{rec.get("tipo_servico") or "—"}</td></tr>'
            f'<tr><td>Responsável Técnico</td><td>{rec.get("rt_nome") or "—"} '
            f'({rec.get("rt_conselho") or "—"})</td></tr>'
            f'<tr><td>Código (SHA-256)</td><td><code>{code}</code></td></tr>'
            f'<tr><td>Emitido em</td><td>{(rec.get("criado_em") or "")[:10]}</td></tr>'
            f'</table>'
            f'<p class="nota">A integridade jurídica plena é assegurada pela assinatura '
            f'ICP-Brasil (PAdES) aposta na peça, quando houver.</p>')
        status = 200
    html = (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Verificação — AvalieImob</title><style>'
        'body{font-family:Inter,Arial,sans-serif;background:#0C3320;color:#0C3320;margin:0;padding:24px}'
        '.card{max-width:560px;margin:24px auto;background:#fff;border-radius:14px;padding:24px;'
        'box-shadow:0 10px 40px rgba(0,0,0,.3);border-top:5px solid #C9A84C}'
        'h1{font-size:20px;margin:0 0 12px}table{width:100%;border-collapse:collapse;margin-top:8px}'
        'td{padding:7px 4px;border-bottom:1px solid #eee;font-size:14px;vertical-align:top}'
        'td:first-child{color:#666;width:42%}code{font-size:12px;word-break:break-all}'
        '.nota{font-size:12px;color:#888;margin-top:14px}</style></head>'
        f'<body><div class="card">{corpo}</div></body></html>')
    return Response(content=html, media_type="text/html; charset=utf-8", status_code=status)


def _plantas_laudo(doc: dict) -> list:
    """[{legenda, raw}] das plantas/mapas SIGEF (principal + cada parcela) p/ o Laudo."""
    out = []
    uploads = doc.get("uploads") or {}
    raw = _download_upload(uploads, "mapa")
    if raw:
        rot = "Parte I" if tem_multiparcela(doc) else "imóvel"
        out.append({"legenda": f"Planta / Mapa SIGEF — {rot}", "raw": raw})
    for pc in (doc.get("parcelas") or []):
        k = ((pc.get("uploads") or {}).get("mapa") or {}).get("key")
        if k:
            try:
                out.append({"legenda": f"Planta / Mapa SIGEF — {pc.get('rotulo') or 'parcela'}",
                            "raw": r2_storage.download_bytes(k)})
            except Exception:  # noqa: BLE001
                pass
    return out


@router.get("/projetos/{pid}/documentos/{tipo}")
async def baixar_documento(pid: str, tipo: str, fmt: str = Query("pdf"),
                          tema: str = Query(None), parcela: str = Query(None),
                          modo: str = Query(None),
                          uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get_projeto(db, pid, uid)
    await _injetar_logo(db, uid, doc)
    if tipo in ("laudo_tecnico", "dossie"):
        doc["_plantas_laudo"] = await asyncio.to_thread(_plantas_laudo, doc)
    laudo_modo = _laudo_modo(doc, modo)
    laudo_separado = laudo_modo == "separado" and tem_multiparcela(doc)
    tema = tema or doc.get("tema_pdf") or "prime_i"
    nb = _nome_base(doc)

    # Selo de autenticidade (QR + código SHA-256) no requerimento/laudo.
    if tipo == "requerimento":
        await _aplicar_selo(db, uid, doc, "requerimento")
    elif tipo == "laudo_tecnico" and not laudo_separado:
        await _aplicar_selo(db, uid, doc, "laudo")
    elif tipo == "dossie":               # registra as peças; o selo é por-peça no _montar_dossie
        await _aplicar_selo(db, uid, doc, "requerimento")
        await _aplicar_selo(db, uid, doc, "laudo")
        doc.pop("_seal_code", None)
        doc.pop("_verify_url", None)

    if tipo == "dossie":
        assinados = await _carregar_pecas_assinadas(db, pid, uid)
        laudo_seals = await _selos_laudos_separados(db, uid, doc) if laudo_separado else None
        data = await asyncio.to_thread(_montar_dossie, doc, tema, assinados, laudo_modo, laudo_seals)
        return _resp(data, "pdf", f"Dossie_{nb}.pdf", inline=(fmt != "download"))

    if tipo not in ("requerimento", "memorial", "laudo_tecnico"):
        raise HTTPException(status_code=404, detail="Documento desconhecido")

    # Laudo SEPARADO (desmembramento multi-parcela): N laudos concatenados num PDF.
    if tipo == "laudo_tecnico" and laudo_separado and fmt != "docx":
        seals = await _selos_laudos_separados(db, uid, doc)
        laudos = await asyncio.to_thread(PDF.pdf_laudos_separados, doc, tema, seals)
        data = await asyncio.to_thread(DOSSIE._concat_pdfs, [lp["bytes"] for lp in laudos])
        return _resp(data, "pdf", f"laudos_separados_{nb}.pdf", inline=True)

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
    await _injetar_logo(db, uid, doc)
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


def _montar_dossie(doc: dict, tema: str, assinados: dict = None,
                   laudo_modo: str = "unificado", laudo_seals: dict = None) -> bytes:
    """`assinados`: {(doc, parcela): bytes} das peças JÁ assinadas (ICP) — usadas
    no lugar das geradas, para o Dossiê sair com as assinaturas.
    `laudo_modo`: 'unificado' (1 laudo) ou 'separado' (1 laudo por parcela)."""
    assinados = assinados or {}
    if "_plantas_laudo" not in doc:           # plantas SIGEF embutidas no Laudo
        doc["_plantas_laudo"] = _plantas_laudo(doc)
    laudo_separado = laudo_modo == "separado" and tem_multiparcela(doc)

    def _peca(kind, gen):
        b = assinados.get((kind, None))
        return b if b else gen()

    def _seal(kind):                       # selo por-peça (códigos já registrados pelo caller)
        c = _seal_code(doc["id"], kind)
        doc["_seal_code"] = c
        doc["_verify_url"] = _verify_url(c)

    def _gen_req():
        _seal("requerimento")
        return PDF.gerar_pdf("requerimento", doc, tema)

    def _gen_laudo():
        _seal("laudo")
        return PDF.gerar_pdf("laudo_tecnico", doc, tema)

    if laudo_separado:                     # 1 laudo por parcela → 1 seção de sumário cada
        laudos = PDF.pdf_laudos_separados(doc, tema, seals=laudo_seals)
        laudo_secao = [{"titulo": f"Laudo Técnico de Agrimensura — {lp['rotulo']}",
                        "bytes": lp["bytes"]} for lp in laudos if lp.get("bytes")]
    else:
        laudo_secao = _peca("laudo", _gen_laudo)

    partes = {
        "requerimento": _peca("requerimento", _gen_req),
        "laudo_tecnico": laudo_secao,
        "memorial": _memoriais_combinados(doc, tema, assinados),   # Memorial do SISTEMA (gerado)
        "drl": [PDF.gerar_pdf("drl", doc, tema, c) for c in TX.confrontantes_para_drl(doc)],
    }
    doc.pop("_seal_code", None)
    doc.pop("_verify_url", None)
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

    # Mapa / Planta SIGEF (upload) e Memorial SIGEF ORIGINAL (upload) — principal +
    # cada parcela, usando a versão ASSINADA quando houver.
    def _anexo_assinado_ou_upload(sign_kind, up_tipo):
        out = []
        b = assinados.get((sign_kind, "principal")) or _download_upload(uploads, up_tipo)
        if b:
            out.append(b)
        for pc in (doc.get("parcelas") or []):
            pb = assinados.get((sign_kind, pc.get("id")))
            if not pb:
                k = ((pc.get("uploads") or {}).get(up_tipo) or {}).get("key")
                if k:
                    try:
                        pb = r2_storage.download_bytes(k)
                    except Exception:  # noqa: BLE001
                        pb = None
            if pb:
                out.append(pb)
        return out

    mapa_list = _anexo_assinado_ou_upload("mapa", "mapa")
    if mapa_list:
        partes["mapa"] = mapa_list
    memsig_list = _anexo_assinado_ou_upload("memorial_sigef", "memorial")
    if memsig_list:
        partes["memorial_sigef"] = memsig_list

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
        # memorial/mapa/memorial_sigef são por-parcela (None → principal); demais = None
        if dock in ("memorial", "mapa", "memorial_sigef"):
            parc = r.get("parcela") or "principal"
        else:
            parc = None
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
    "mapa": "Mapa / Planta (SIGEF)",
    "memorial_sigef": "Memorial Descritivo SIGEF (enviado)",
}
# Peças que vêm de um UPLOAD (PDF/imagem) — assináveis direto. doc_tipo -> upload_tipo.
_DOC_UPLOAD = {"art_trt": "art_trt", "mapa": "mapa", "memorial_sigef": "memorial"}


def _upload_da_parcela_ou_principal(doc: dict, up_tipo: str, parcela: str):
    """Retorna o dict do upload `up_tipo` da parcela (se `parcela`) ou do principal."""
    if parcela and parcela != "principal":
        pc = next((p for p in (doc.get("parcelas") or []) if p.get("id") == parcela), None)
        return ((pc or {}).get("uploads") or {}).get(up_tipo)
    return (doc.get("uploads") or {}).get(up_tipo)


def _pdf_para_assinatura(doc: dict, tipo_doc: str, parcela: str, tema: str,
                         assinados: dict = None) -> bytes:
    if tipo_doc in _DOC_UPLOAD:
        up = _upload_da_parcela_ou_principal(doc, _DOC_UPLOAD[tipo_doc], parcela)
        key = (up or {}).get("key")
        if not key:
            raise ValueError(f"{_DOC_NOMES[tipo_doc]} não enviado (suba na etapa Upload).")
        raw = r2_storage.download_bytes(key)
        if raw[:5] == b"%PDF-":
            return raw
        from services.georef.generators.dossie import _img_para_pdf
        return _img_para_pdf(raw)
    if tipo_doc == "memorial":
        return PDF.gerar_pdf("memorial", _doc_para_memorial(doc, parcela), tema)
    if tipo_doc == "laudo":
        return PDF.gerar_pdf("laudo_tecnico", doc, tema)
    if tipo_doc == "requerimento":
        return PDF.gerar_pdf("requerimento", doc, tema)
    if tipo_doc == "dossie":
        return _montar_dossie(doc, tema, assinados)
    raise ValueError(f"Documento desconhecido para assinatura: {tipo_doc}")


@router.post("/projetos/{pid}/assinar")
async def preparar_assinatura(pid: str, body: AssinarPecaBody,
                             uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Gera a peça pedida, guarda no R2 e cria o registro `georef_assinaturas`.
    O front então abre o assinador ICP com tipo='georef' e este id."""
    doc = await _get_projeto(db, pid, uid)
    await _injetar_logo(db, uid, doc)
    if body.doc in ("laudo", "dossie"):
        doc["_plantas_laudo"] = await asyncio.to_thread(_plantas_laudo, doc)
    if body.doc in ("requerimento", "laudo"):
        await _aplicar_selo(db, uid, doc, body.doc)
    elif body.doc == "dossie":
        await _aplicar_selo(db, uid, doc, "requerimento")
        await _aplicar_selo(db, uid, doc, "laudo")
        doc.pop("_seal_code", None)
        doc.pop("_verify_url", None)
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
    if body.parcela and body.parcela != "principal":
        pv = next((p for p in parcelas_do_projeto(doc) if p.get("id") == body.parcela), None)
        rotulo = f" ({pv.get('rotulo')})" if pv else ""
    elif body.doc in ("memorial", "memorial_sigef", "mapa"):
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
