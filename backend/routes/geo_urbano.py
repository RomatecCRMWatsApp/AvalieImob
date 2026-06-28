# @module routes.geo_urbano — Topografia & Geo / Geo Urbano (Remembramento — Fase 1).
#
# Fluxo: cria projeto → upload (mapas/BCI/certidões/IPTU/proprietário/TRT) →
# conferência/reconciliação (matrícula ↔ BCI ↔ IPTU) → /gerar → downloads
# (Requerimento 2 vias, Memorial, Cadeia, Dossiê). Geração pesada (ReportLab/
# pypdf/R2) roda fora do event loop. NÃO usa `from __future__ import annotations`
# (mantém as anotações de body resolvidas pelo FastAPI).
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.geo_urbano import (
    GeoUrbanoProjeto, CriarProjetoBody, AtualizarProjetoBody, GerarDocumentosBody,
    AprovacaoSuperintendenciaBody, CamposAssinaturaBody, AssinarPecaBody, calcular_completude,
)
from services import r2_storage
from services.geo_urbano import reconcile as RECONCILE
from services.geo_urbano import geometria as GEOM
from services.geo_urbano import aprovacao as APROVACAO
from services.geo_urbano import extractor as EX
from services.geo_urbano import assinatura_proprietario as PROP
from services.geo_urbano import retificacao as RET
from services.geo_urbano.lotes import projeto_do_lote
from services.geo_urbano.seed import build_seed
from services.geo_urbano.generators import pdf as PDF
from services.geo_urbano.generators import dossie as DOSSIE
from services.geo_urbano.generators import capa as CAPA

logger = logging.getLogger("romatec")
router = APIRouter(prefix="/topografia/geo-urbano", tags=["topografia-geo-urbano"])

# Tipos de upload aceitos (§4). Todos multi-arquivo (lista por tipo).
_TIPOS_UPLOAD = {
    "imagem_imovel",  # foto aérea/satélite com o perímetro (vai p/ a Capa "Lupa Geo")
    "mapa_desdobro",  # desdobro: 1 mapa por lote resultante (vincula lote_id)
    "mapa_retificado",  # retificação: mapa "como está"
    "mapa_atual", "mapa_remembramento", "bci", "certidao_inteiro_teor",
    "cnd_iptu", "guia_iptu", "comprovante_pagamento_iptu",
    "contrato_social", "doc_socio", "doc_proprietario", "cnh", "certidao_casamento",
    "art_trt", "art_trt_boleto", "comprovante_pagamento_trt",
}
_MAX_UPLOAD = 30 * 1024 * 1024
_PDF = "application/pdf"

# Mapeia as seções do dossiê (§9) para os tipos de upload que as compõem.
_DOSSIE_UPLOADS = {
    "mapa_atual": ["mapa_atual"],
    "mapa_remembramento": ["mapa_remembramento"],
    "mapa_desdobro": ["mapa_desdobro"],
    "mapa_retificado": ["mapa_retificado"],
    "art_trt": ["art_trt"],
    "boleto_trt": ["art_trt_boleto"],
    "comprovante_pagamento_trt": ["comprovante_pagamento_trt"],
    "certidoes_inteiro_teor": ["certidao_inteiro_teor"],
    "iptu": ["cnd_iptu", "guia_iptu", "comprovante_pagamento_iptu"],
    "bci": ["bci"],
    "documentos_proprietario": ["contrato_social", "doc_socio", "doc_proprietario",
                                 "cnh", "certidao_casamento"],
}
_DOCS_GERAVEIS = {"requerimento_cartorio", "requerimento_superintendencia",
                  "memorial_descritivo", "cadeia_dominical", "oficio_aprovacao",
                  "quadro_retificacao"}


def _agora():
    return datetime.now(timezone.utc)


async def _numero(db):
    ano = _agora().year
    res = await db.counters.find_one_and_update(
        {"_id": f"geo_urbano_{ano}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=ReturnDocument.AFTER,
    )
    return f"URB-{ano}-{res['seq']:04d}"


async def _get(db, pid, uid):
    doc = await db.geo_urbano_projetos.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return doc


def _ext(filename, content_type):
    fn = (filename or "").lower()
    if fn.endswith(".pdf") or "pdf" in (content_type or ""):
        return "pdf"
    for e in ("png", "jpg", "jpeg", "webp"):
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
    proj = GeoUrbanoProjeto(user_id=uid, denominacao_imovel=body.denominacao_imovel,
                            tipo_servico=body.tipo_servico, tema=body.tema,
                            municipio=body.municipio, uf=body.uf)
    doc = proj.model_dump(mode="json")
    doc["numero"] = await _numero(db)
    await db.geo_urbano_projetos.insert_one(doc)
    return serialize_doc(doc)


@router.post("/projetos/seed", status_code=201)
async def criar_seed(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Cria o projeto-teste oficial J&G (Quadra 41 · Parque das Nações)."""
    doc = build_seed(uid)
    doc["numero"] = await _numero(db)
    await db.geo_urbano_projetos.insert_one(doc)
    return serialize_doc(doc)


@router.get("/projetos")
async def listar_projetos(status: str = Query(None), uid: str = Depends(get_active_subscriber),
                          db=Depends(get_db)):
    q = {"user_id": uid}
    if status:
        q["status"] = status
    cur = db.geo_urbano_projetos.find(q).sort("created_at", -1)
    return [serialize_doc(d) async for d in cur]


@router.get("/projetos/{pid}")
async def detalhe_projeto(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return serialize_doc(await _get(db, pid, uid))


@router.patch("/projetos/{pid}")
async def atualizar_projeto(pid: str, body: AtualizarProjetoBody,
                            uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    dados = body.model_dump(exclude_unset=True)
    editados = dict(doc.get("campos_editados") or {})
    sets = {}
    escalares = ("denominacao_imovel", "tipo_servico", "tema", "status", "municipio", "uf",
                 "bairro", "loteamento", "quadra", "lote_resultante", "endereco",
                 "cmi_resultante", "cadastro_novo", "cadastro_antigo", "area_declarada_m2",
                 "perimetro_m", "trt_numero",
                 # desdobro
                 "matricula_mae_id", "area_mae_m2", "qtd_lotes_resultantes", "area_via_doacao_m2",
                 "lote_minimo_municipal_m2", "testada_minima_m",
                 # retificação
                 "retificacao_tipo")
    for c in escalares:
        if c in dados:
            sets[c] = dados[c]
            editados[c] = True
    if "retificacao_analise" in dados and isinstance(dados["retificacao_analise"], dict):
        sets["retificacao_analise"] = dados["retificacao_analise"]
    for grupo in ("cartorio", "superintendencia", "responsavel_tecnico"):
        if grupo in dados and isinstance(dados[grupo], dict):
            atual = dict(doc.get(grupo) or {})
            atual.update(dados[grupo])
            sets[grupo] = atual
    for grupo in ("matriculas", "bci", "vertices", "partes", "iptu", "lotes_resultantes", "vertices_atual"):
        if grupo in dados and dados[grupo] is not None:
            sets[grupo] = dados[grupo]
            editados[grupo] = True
    base = {**doc, **sets}
    # recalcula áreas a partir da poligonal (se houver vértices)
    if base.get("vertices"):
        sets["area_calculada_m2"] = GEOM.area_m2(base["vertices"])
        if not sets.get("perimetro_m") and not doc.get("perimetro_m"):
            sets["perimetro_m"] = GEOM.perimetro_m(base["vertices"])
    sets["campos_editados"] = editados
    sets["completude"] = calcular_completude(base)
    sets["updated_at"] = _agora().isoformat()
    await db.geo_urbano_projetos.update_one({"id": pid, "user_id": uid}, {"$set": sets})
    return serialize_doc({**doc, **sets})


@router.delete("/projetos/{pid}")
async def excluir_projeto(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    res = await db.geo_urbano_projetos.delete_one({"id": pid, "user_id": uid})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# Uploads
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/projetos/{pid}/upload")
async def upload_documento(pid: str, tipo: str = Form(...), file: UploadFile = File(...),
                           matricula_id: str = Form(None), parte_id: str = Form(None),
                           lote_id: str = Form(None),
                           uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    if tipo not in _TIPOS_UPLOAD:
        raise HTTPException(status_code=422, detail=f"Tipo inválido. Use: {sorted(_TIPOS_UPLOAD)}")
    doc = await _get(db, pid, uid)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Arquivo vazio")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx. 30 MB)")
    ext = _ext(file.filename, file.content_type)
    item_id = str(uuid.uuid4())
    key = f"geo-urbano/{uid}/{pid}/{tipo}/{item_id}.{ext}"
    ct = _PDF if ext == "pdf" else f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
    await asyncio.to_thread(r2_storage.upload_bytes, data, key, ct)
    item = {"id": item_id, "key": key, "nome": file.filename, "mime": ct,
            "vinculo": {"matricula_id": matricula_id, "parte_id": parte_id, "lote_resultante_id": lote_id},
            "enviado_em": _agora().isoformat()}
    uploads = dict(doc.get("uploads") or {})
    uploads.setdefault(tipo, [])
    uploads[tipo].append(item)
    await db.geo_urbano_projetos.update_one(
        {"id": pid, "user_id": uid}, {"$set": {"uploads": uploads, "updated_at": _agora().isoformat()}})
    return {"ok": True, "tipo": tipo, "item": item, "total": len(uploads[tipo])}


@router.delete("/projetos/{pid}/uploads/{tipo}/{item_id}")
async def remover_upload(pid: str, tipo: str, item_id: str,
                         uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    uploads = dict(doc.get("uploads") or {})
    lista = [x for x in (uploads.get(tipo) or [])]
    alvo = next((x for x in lista if x.get("id") == item_id), None)
    if not alvo:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    if alvo.get("key"):
        try:
            await asyncio.to_thread(r2_storage.delete_object, alvo["key"])
        except Exception:  # noqa: BLE001
            pass
    uploads[tipo] = [x for x in lista if x.get("id") != item_id]
    await db.geo_urbano_projetos.update_one(
        {"id": pid, "user_id": uid}, {"$set": {"uploads": uploads, "updated_at": _agora().isoformat()}})
    return {"ok": True, "restantes": len(uploads[tipo])}


# ──────────────────────────────────────────────────────────────────────────────
# Extração automática (parsers calibrados nos PDFs reais; OCR p/ matrículas)
# ──────────────────────────────────────────────────────────────────────────────
_TIPOS_EXTRACAO = ["mapa_remembramento", "certidao_inteiro_teor", "bci", "cnd_iptu", "guia_iptu"]


@router.post("/projetos/{pid}/extrair")
async def extrair(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    uploads = doc.get("uploads") or {}
    ups_bytes = {}
    for tp in _TIPOS_EXTRACAO:
        blobs = []
        for item in uploads.get(tp) or []:
            if item.get("key"):
                try:
                    blobs.append(await asyncio.to_thread(r2_storage.download_bytes, item["key"]))
                except Exception:  # noqa: BLE001
                    continue
        if blobs:
            ups_bytes[tp] = blobs
    if not ups_bytes:
        raise HTTPException(status_code=422, detail="Envie ao menos o Mapa de Remembramento (e BCIs/IPTU) para extrair.")

    res = await asyncio.to_thread(EX.extrair_tudo, ups_bytes)
    editados = doc.get("campos_editados") or {}
    sets = {}
    for campo in ("matriculas", "bci", "vertices", "iptu"):
        if campo in res and not editados.get(campo):
            sets[campo] = res[campo]
    for campo in ("area_declarada_m2", "perimetro_m", "cmi_resultante", "cadastro_novo", "cadastro_antigo"):
        if res.get(campo) is not None and not editados.get(campo):
            sets[campo] = res[campo]
    base = {**doc, **sets}
    if base.get("vertices"):
        sets["area_calculada_m2"] = GEOM.area_m2(base["vertices"])
    sets["status"] = "conferencia"
    sets["completude"] = calcular_completude(base)
    sets["updated_at"] = _agora().isoformat()
    await db.geo_urbano_projetos.update_one({"id": pid, "user_id": uid}, {"$set": sets})
    novo = {**doc, **sets}
    return {
        "ok": True, "avisos": res.get("avisos", []),
        "extraido": {c: len(novo.get(c) or []) for c in ("matriculas", "bci", "vertices", "iptu")},
        "reconciliacao": RECONCILE.reconciliar(novo)["resumo"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Reconciliação / geometria
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/projetos/{pid}/reconciliacao")
async def reconciliacao(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    out = RECONCILE.reconciliar(doc)
    out["areas"] = GEOM.conferencia_areas(doc.get("vertices") or [], doc.get("area_declarada_m2"))
    if doc.get("tipo_servico") == "desdobro":
        out["conservacao"] = GEOM.conservacao_area(doc)
        out["urbanisticas"] = GEOM.validacoes_urbanisticas(doc)
        if not out["conservacao"]["ok"]:
            out["resumo"]["bloqueantes"] = (out["resumo"].get("bloqueantes") or 0) + 1
            out["resumo"]["pode_protocolar"] = False
    return out


@router.get("/projetos/{pid}/conservacao-area")
async def conservacao_area(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    return {"conservacao": GEOM.conservacao_area(doc),
            "urbanisticas": GEOM.validacoes_urbanisticas(doc)}


@router.get("/projetos/{pid}/retificacao/analise")
async def retificacao_analise(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Executa a análise comparativa (cadastral matrícula×BCI + geométrico) sem persistir."""
    doc = await _get(db, pid, uid)
    return RET.analisar(doc)


@router.post("/projetos/{pid}/retificacao/confirmar")
async def retificacao_confirmar(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Trava o quadro de retificação (de → para) que alimenta o requerimento/memorial."""
    doc = await _get(db, pid, uid)
    analise = RET.analisar(doc)
    await db.geo_urbano_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"retificacao_analise": analise, "updated_at": _agora().isoformat()}})
    return analise


@router.get("/projetos/{pid}/preview-geojson")
async def preview_geojson(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    return GEOM.poligono_geojson(doc)


# ──────────────────────────────────────────────────────────────────────────────
# Geração / downloads
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/projetos/{pid}/gerar")
async def gerar(pid: str, body: GerarDocumentosBody, uid: str = Depends(get_active_subscriber),
                db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    if not doc.get("matriculas"):
        raise HTTPException(status_code=422, detail="Cadastre as matrículas antes de gerar os documentos.")
    rec = RECONCILE.reconciliar(doc)
    gerados = dict(doc.get("documentos_gerados") or {})
    for t in body.documentos:
        gerados[t] = {"gerado_em": _agora().isoformat()}
    await db.geo_urbano_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"documentos_gerados": gerados, "status": "assinatura",
                  "updated_at": _agora().isoformat()}})
    return {"ok": True, "reconciliacao": rec["resumo"]}


@router.get("/projetos/{pid}/documentos/{tipo}")
async def baixar_documento(pid: str, tipo: str, tema: str = Query(None), lote: str = Query(None),
                           uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    tema = tema or doc.get("tema") or "prime_i"
    # Memorial de UM lote resultante (desdobro)
    if tipo == "memorial_descritivo" and lote:
        lt = next((x for x in (doc.get("lotes_resultantes") or []) if x.get("id") == lote), None)
        if not lt:
            raise HTTPException(status_code=404, detail="Lote resultante não encontrado.")
        data = await asyncio.to_thread(PDF.gerar_pdf, "memorial_descritivo", projeto_do_lote(doc, lt), tema)
        nome = f"memorial_{(lt.get('denominacao') or lote)}.pdf"
        return Response(content=data, media_type=_PDF,
                        headers={"Content-Disposition": f'inline; filename="{nome}"'})
    if tipo == "capa":
        img = await _imagem_imovel_bytes(doc)
        if not img:
            raise HTTPException(status_code=422, detail="Envie a imagem do imóvel (aérea/satélite) para gerar a capa.")
        data = await asyncio.to_thread(CAPA.gerar_capa_pdf, doc, img)
        nome = f"capa_{(doc.get('numero') or pid)}.pdf"
    elif tipo == "dossie":
        data = await _montar_dossie(db, doc, tema)
        nome = f"dossie_{(doc.get('numero') or pid)}.pdf"
    elif tipo in _DOCS_GERAVEIS:
        data = await asyncio.to_thread(PDF.gerar_pdf, tipo, doc, tema)
        nome = f"{tipo}_{(doc.get('numero') or pid)}.pdf"
    else:
        raise HTTPException(status_code=422, detail=f"Documento inválido: {tipo}")
    return Response(content=data, media_type=_PDF,
                    headers={"Content-Disposition": f'inline; filename="{nome}"'})


async def _imagem_imovel_bytes(doc):
    itens = (doc.get("uploads") or {}).get("imagem_imovel") or []
    if not itens or not itens[0].get("key"):
        return None
    try:
        return await asyncio.to_thread(r2_storage.download_bytes, itens[0]["key"])
    except Exception:  # noqa: BLE001
        return None


@router.get("/projetos/{pid}/capa/preview")
async def capa_preview(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    img = await _imagem_imovel_bytes(doc)
    if not img:
        raise HTTPException(status_code=422, detail="Envie a imagem do imóvel (aérea/satélite) primeiro.")
    png = await asyncio.to_thread(CAPA.preview_png, doc, img)
    return Response(content=png, media_type="image/png")


async def _montar_dossie(db, doc, tema):
    # Capa "Lupa Geo" quando há imagem do imóvel; senão a capa textual padrão.
    capa_pdf = None
    img = await _imagem_imovel_bytes(doc)
    if img:
        capa_pdf = await asyncio.to_thread(CAPA.gerar_capa_pdf, doc, img)
    # peças geradas
    partes = {}
    for t in ("requerimento_cartorio", "requerimento_superintendencia", "cadeia_dominical"):
        partes[t] = await asyncio.to_thread(PDF.gerar_pdf, t, doc, tema)
    # Memorial: 1 (remembramento/retificação) ou N (desdobro — um por lote resultante)
    lotes = doc.get("lotes_resultantes") or []
    if doc.get("tipo_servico") == "desdobro" and lotes:
        mems = []
        for lt in sorted(lotes, key=lambda x: x.get("ordem", 0)):
            mems.append(await asyncio.to_thread(PDF.gerar_pdf, "memorial_descritivo", projeto_do_lote(doc, lt), tema))
        partes["memorial_descritivo"] = mems
    else:
        partes["memorial_descritivo"] = await asyncio.to_thread(PDF.gerar_pdf, "memorial_descritivo", doc, tema)
    # Ofício de aprovação — só entra quando emitido pela Superintendência
    if ((doc.get("aprovacao") or {}).get("superintendencia") or {}).get("oficio_emitido"):
        partes["oficio_aprovacao"] = await asyncio.to_thread(PDF.gerar_pdf, "oficio_aprovacao", doc, tema)
    # Quadro de Retificação (de → para) — peça própria da retificação
    if doc.get("tipo_servico") == "retificacao":
        if not (doc.get("retificacao_analise") or {}).get("cadastral_diffs"):
            doc = {**doc, "retificacao_analise": RET.analisar(doc)}
        partes["quadro_retificacao"] = await asyncio.to_thread(PDF.gerar_pdf, "quadro_retificacao", doc, tema)
    # uploads → seções do §9
    uploads = doc.get("uploads") or {}
    for secao, tipos in _DOSSIE_UPLOADS.items():
        bytes_list = []
        for tp in tipos:
            for item in (uploads.get(tp) or []):
                if item.get("key"):
                    try:
                        bytes_list.append(await asyncio.to_thread(r2_storage.download_bytes, item["key"]))
                    except Exception:  # noqa: BLE001
                        continue
        if bytes_list:
            partes[secao] = bytes_list
    return await asyncio.to_thread(DOSSIE.gerar_dossie, doc, partes, capa_pdf)


# ──────────────────────────────────────────────────────────────────────────────
# Assinatura ICP do TÉCNICO (Memorial + Mapa) — reusa o módulo de assinatura
# ──────────────────────────────────────────────────────────────────────────────
_PECAS_ASSINAVEIS = {
    "memorial_descritivo": "Memorial Descritivo",
    "mapa": "Mapa de Remembramento",
    "requerimento_cartorio": "Requerimento — Via Cartório",
    "requerimento_superintendencia": "Requerimento — Via Superintendência",
    "art_trt": "ART / TRT",
}
# Peças que vêm de um UPLOAD (PDF/imagem). doc → tipo de upload.
_PECA_UPLOAD = {"mapa": "mapa_remembramento", "art_trt": "art_trt"}


async def _bytes_upload(doc, tipo):
    itens = (doc.get("uploads") or {}).get(tipo) or []
    if not itens or not itens[0].get("key"):
        return None
    try:
        return await asyncio.to_thread(r2_storage.download_bytes, itens[0]["key"])
    except Exception:  # noqa: BLE001
        return None


@router.post("/projetos/{pid}/assinar")
async def preparar_assinatura(pid: str, body: AssinarPecaBody,
                              uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Gera/baixa a peça, guarda no R2 e cria o registro `geo_urbano_assinaturas`.
    O front abre o assinador ICP com tipo='geo_urbano' e este id."""
    doc = await _get(db, pid, uid)
    peca = body.doc
    if peca not in _PECAS_ASSINAVEIS:
        raise HTTPException(status_code=422, detail="Peça inválida para assinatura.")
    tema = body.tema or doc.get("tema") or "prime_i"
    if peca in _PECA_UPLOAD:
        raw = await _bytes_upload(doc, _PECA_UPLOAD[peca])
        if not raw:
            raise HTTPException(status_code=422, detail=f"{_PECAS_ASSINAVEIS[peca]} não enviado (etapa Uploads).")
        if raw[:5] == b"%PDF-":
            pdf_bytes = raw
        else:
            from services.georef.generators.dossie import _img_para_pdf
            pdf_bytes = await asyncio.to_thread(_img_para_pdf, raw)
    else:
        pdf_bytes = await asyncio.to_thread(PDF.gerar_pdf, peca, doc, tema)
    if not pdf_bytes or pdf_bytes[:5] != b"%PDF-":
        raise HTTPException(status_code=500, detail="Falha ao gerar o PDF para assinatura.")

    filtro = {"user_id": uid, "projeto_id": pid, "doc": peca}
    existente = await db.geo_urbano_assinaturas.find_one(filtro)
    aid = existente["id"] if existente else str(uuid.uuid4())
    key = f"geo-urbano/{uid}/{pid}/assinar/{peca}_{aid[:8]}.pdf"
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, pdf_bytes, key, _PDF)
    except Exception as e:  # noqa: BLE001
        logger.error("Geo Urbano: upload R2 da peça p/ assinatura falhou (%s)", e)
        raise HTTPException(status_code=502, detail="Falha ao preparar o documento.")
    try:
        from pypdf import PdfReader
        import io as _io
        paginas = len(PdfReader(_io.BytesIO(pdf_bytes)).pages)
    except Exception:  # noqa: BLE001
        paginas = 0
    nome = f"{_PECAS_ASSINAVEIS[peca]} — {doc.get('denominacao_imovel') or ''}"
    if existente:
        await db.geo_urbano_assinaturas.update_one(
            {"id": aid}, {"$set": {"nome": nome, "pdf_key": key, "paginas": paginas,
                                   "tema": tema, "updated_at": _agora().isoformat()}})
    else:
        await db.geo_urbano_assinaturas.insert_one({
            "id": aid, "user_id": uid, "projeto_id": pid, "doc": peca, "nome": nome,
            "pdf_key": key, "paginas": paginas, "icp_status": None, "tema": tema,
            "created_at": _agora().isoformat()})
    return {"id": aid, "nome": nome, "paginas": paginas,
            "assinado": (existente or {}).get("icp_status") == "assinado"}


@router.get("/projetos/{pid}/assinaturas")
async def listar_assinaturas(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _get(db, pid, uid)
    recs = await db.geo_urbano_assinaturas.find({"user_id": uid, "projeto_id": pid}).to_list(50)
    return [{"id": r["id"], "doc": r.get("doc"), "nome": r.get("nome"),
             "assinado": r.get("icp_status") == "assinado",
             "paginas": r.get("paginas")} for r in recs]


# ──────────────────────────────────────────────────────────────────────────────
# Assinatura DESENHADA do PROPRIETÁRIO (Requerimento 2 vias + ART/TRT) via WhatsApp
# ──────────────────────────────────────────────────────────────────────────────
async def _pecas_proprietario_bytes(doc, tema):
    """Lista [{doc,titulo,bytes}] das peças que o proprietário assina (art_trt só se enviado)."""
    pecas = []
    for nome, titulo in PROP.PECAS_PROPRIETARIO:
        if nome == "art_trt":
            raw = await _bytes_upload(doc, "art_trt")
            if not raw:
                continue
            if raw[:5] != b"%PDF-":
                from services.georef.generators.dossie import _img_para_pdf
                raw = await asyncio.to_thread(_img_para_pdf, raw)
            pecas.append({"doc": nome, "titulo": titulo, "bytes": raw})
        else:
            b = await asyncio.to_thread(PDF.gerar_pdf, nome, doc, tema)
            pecas.append({"doc": nome, "titulo": titulo, "bytes": b})
    return pecas


@router.post("/projetos/{pid}/proprietario/preparar")
async def prop_preparar(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Renderiza as páginas das peças p/ o operador posicionar as assinaturas."""
    doc = await _get(db, pid, uid)
    from services.pdf_preview import renderizar_paginas
    tema = doc.get("tema") or "prime_i"
    pecas = await _pecas_proprietario_bytes(doc, tema)
    documentos = []
    for p in pecas:
        paginas = await asyncio.to_thread(renderizar_paginas, p["bytes"], 120, 30)
        documentos.append({"doc": p["doc"], "titulo": p["titulo"], "paginas": paginas})
    return {"documentos": documentos, "signatarios": PROP.signatarios_de(doc)}


async def _disparar_links_prop(db, uid, proj, sessao, somente_pendentes=True):
    from routes.assinatura_cliente import APP_URL
    cfg = await PROP.zapi_cfg(db, proj.get("user_id") or uid)
    titulo = (proj.get("tipo_servico") or "remembramento")
    enviados, falhas, links = 0, 0, []
    for s in sessao["signatarios"]:
        if somente_pendentes and s.get("status") not in ("pendente", "enviado"):
            continue
        url = f"{APP_URL}/assinar-geo/{s['token']}"
        links.append({"nome": s["nome"], "url": url})
        try:
            await PROP.enviar_link(cfg, s["telefone"], s["nome"], titulo, url)
            s["status"] = "enviado"
            enviados += 1
        except Exception as e:  # noqa: BLE001
            falhas += 1
            logger.warning("Geo Urbano: envio do link ao proprietário falhou: %s", e)
    await db.geo_urbano_assinatura_sessoes.update_one(
        {"id": sessao["id"]}, {"$set": {"signatarios": sessao["signatarios"], "updated_at": _agora().isoformat()}})
    return {"links": links, "enviados": enviados, "falhas": falhas}


@router.post("/projetos/{pid}/proprietario/posicionar")
async def prop_posicionar(pid: str, body: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Salva os retângulos por signatário/peça, cria a sessão e dispara os links."""
    doc = await _get(db, pid, uid)
    tema = doc.get("tema") or "prime_i"
    sig_in = body.get("signatarios") or PROP.signatarios_de(doc)
    posicoes = body.get("posicoes") or {}            # {parte_id: {doc: [rects]}}
    if any(not s.get("telefone") for s in sig_in):
        raise HTTPException(status_code=422, detail="Informe o WhatsApp de todos os signatários.")
    docs_com_pos = {dn for mp in posicoes.values() for dn, r in (mp or {}).items() if r}
    if not docs_com_pos:
        raise HTTPException(status_code=422, detail="Posicione ao menos uma assinatura.")
    pecas = await _pecas_proprietario_bytes(doc, tema)
    documentos = []
    for p in pecas:
        if p["doc"] not in docs_com_pos:
            continue
        key = f"geo-urbano/{uid}/{pid}/assin-prop/{p['doc']}_base.pdf"
        await asyncio.to_thread(r2_storage.upload_bytes, p["bytes"], key, _PDF)
        try:
            from pypdf import PdfReader
            import io as _io
            paginas = len(PdfReader(_io.BytesIO(p["bytes"])).pages)
        except Exception:  # noqa: BLE001
            paginas = 0
        documentos.append({"doc": p["doc"], "titulo": p["titulo"], "pdf_key_base": key, "paginas": paginas})

    sigs = []
    for s in sig_in:
        sigs.append({
            "id": str(uuid.uuid4()), "parte_id": s.get("parte_id"), "nome": s.get("nome"),
            "papel": s.get("papel"), "cpf_cnpj": s.get("cpf_cnpj"), "telefone": s.get("telefone"),
            "token": PROP.gerar_token(), "status": "pendente", "assinado_em": None,
            "ip": None, "user_agent": None, "geo_lat": None, "geo_lng": None, "traco_b64": None,
            "posicoes": posicoes.get(s.get("parte_id")) or {},
        })
    sessao = {"id": str(uuid.uuid4()), "user_id": uid, "projeto_id": pid, "status": "aguardando",
              "documentos": documentos, "signatarios": sigs, "pdf_keys_final": {},
              "created_at": _agora().isoformat(), "updated_at": _agora().isoformat()}
    await db.geo_urbano_assinatura_sessoes.delete_many({"projeto_id": pid, "user_id": uid})
    await db.geo_urbano_assinatura_sessoes.insert_one(sessao)
    res = await _disparar_links_prop(db, uid, doc, sessao)
    return {"ok": True, **res}


@router.get("/projetos/{pid}/proprietario/sessao")
async def prop_sessao(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    s = await db.geo_urbano_assinatura_sessoes.find_one({"projeto_id": pid, "user_id": uid})
    if not s:
        return {"existe": False}
    return {"existe": True, "status": s.get("status"),
            "assinados": sum(1 for x in s["signatarios"] if x.get("status") == "assinado"),
            "total": len(s["signatarios"]),
            "documentos": [d["doc"] for d in s.get("documentos", [])],
            "signatarios": [{"nome": x["nome"], "papel": x.get("papel"), "status": x.get("status"),
                             "telefone": x.get("telefone")} for x in s["signatarios"]]}


@router.post("/projetos/{pid}/proprietario/reenviar")
async def prop_reenviar(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    s = await db.geo_urbano_assinatura_sessoes.find_one({"projeto_id": pid, "user_id": uid})
    if not s:
        raise HTTPException(status_code=404, detail="Nenhuma sessão de assinatura para reenviar.")
    proj = await _get(db, pid, uid)
    res = await _disparar_links_prop(db, uid, proj, s)
    return {"ok": True, **res}


# ──────────────────────────────────────────────────────────────────────────────
# Aprovação & Assinaturas (Addendum) — esqueleto do fluxo
# ──────────────────────────────────────────────────────────────────────────────
async def _oficio_numero(db):
    ano = _agora().year
    res = await db.counters.find_one_and_update(
        {"_id": f"geo_urbano_oficio_{ano}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=ReturnDocument.AFTER,
    )
    return f"OF-{ano}-{res['seq']:04d}"


async def _salvar_aprovacao(db, pid, uid, doc, aprov):
    aprov["status_geral"] = APROVACAO.status_geral(aprov)
    await db.geo_urbano_projetos.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"aprovacao": aprov, "updated_at": _agora().isoformat()}})
    return aprov


@router.get("/projetos/{pid}/aprovacao/status")
async def aprovacao_status(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    return APROVACAO.build_status(doc)


@router.post("/projetos/{pid}/assinatura/campos")
async def definir_campos(pid: str, body: CamposAssinaturaBody,
                         uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    aprov = dict(doc.get("aprovacao") or {})
    aprov["campos"] = body.campos
    await _salvar_aprovacao(db, pid, uid, doc, aprov)
    return {"ok": True, "campos": len(body.campos)}


@router.post("/projetos/{pid}/aprovacao/enviar")
async def aprovacao_enviar(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Envia o dossiê à Superintendência (marca o passo do fluxo)."""
    doc = await _get(db, pid, uid)
    aprov = dict(doc.get("aprovacao") or {})
    aprov["enviado_superintendencia"] = True
    sup = dict(aprov.get("superintendencia") or {})
    sup["enviado_em"] = _agora().isoformat()
    aprov["superintendencia"] = sup
    await _salvar_aprovacao(db, pid, uid, doc, aprov)
    return APROVACAO.build_status({**doc, "aprovacao": aprov})


@router.post("/projetos/{pid}/aprovacao/superintendencia")
async def aprovacao_superintendencia(pid: str, body: AprovacaoSuperintendenciaBody,
                                     uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Operador registra a aprovação do órgão (Memorial e/ou Mapa)."""
    doc = await _get(db, pid, uid)
    aprov = dict(doc.get("aprovacao") or {})
    sup = dict(aprov.get("superintendencia") or {})
    cfg = doc.get("superintendencia") or {}
    sup.setdefault("responsavel", cfg.get("responsavel"))
    sup.setdefault("portaria", cfg.get("portaria"))
    if body.memorial_aprovado is not None:
        sup["memorial_aprovado"] = body.memorial_aprovado
    if body.mapa_aprovado is not None:
        sup["mapa_aprovado"] = body.mapa_aprovado
    if sup.get("memorial_aprovado") and sup.get("mapa_aprovado") and not sup.get("aprovado_em"):
        sup["aprovado_em"] = _agora().isoformat()
    aprov["superintendencia"] = sup
    await _salvar_aprovacao(db, pid, uid, doc, aprov)
    return APROVACAO.build_status({**doc, "aprovacao": aprov})


@router.post("/projetos/{pid}/gerar/oficio")
async def gerar_oficio(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Emite o Ofício de Aprovação da Superintendência ao Cartório (numeração própria)."""
    doc = await _get(db, pid, uid)
    aprov = dict(doc.get("aprovacao") or {})
    sup = dict(aprov.get("superintendencia") or {})
    if not (sup.get("memorial_aprovado") and sup.get("mapa_aprovado")):
        raise HTTPException(status_code=422,
                            detail="Aprovação pendente: aprove o Memorial e o Mapa antes de emitir o Ofício.")
    if not sup.get("oficio_numero"):
        sup["oficio_numero"] = await _oficio_numero(db)
    sup["oficio_emitido"] = True
    sup["oficio_em"] = _agora().isoformat()
    aprov["superintendencia"] = sup
    await _salvar_aprovacao(db, pid, uid, doc, aprov)
    gerados = dict(doc.get("documentos_gerados") or {})
    gerados["oficio_aprovacao"] = {"gerado_em": _agora().isoformat(), "numero": sup["oficio_numero"]}
    await db.geo_urbano_projetos.update_one(
        {"id": pid, "user_id": uid}, {"$set": {"documentos_gerados": gerados}})
    return {"ok": True, "oficio_numero": sup["oficio_numero"],
            "status": APROVACAO.build_status({**doc, "aprovacao": aprov})}
