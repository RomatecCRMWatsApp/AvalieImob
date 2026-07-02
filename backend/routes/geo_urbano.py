# @module routes.geo_urbano — Topografia & Geo / Geo Urbano (Remembramento — Fase 1).
#
# Fluxo: cria projeto → upload (mapas/BCI/certidões/IPTU/proprietário/TRT) →
# conferência/reconciliação (matrícula ↔ BCI ↔ IPTU) → /gerar → downloads
# (Requerimento 2 vias, Memorial, Cadeia, Dossiê). Geração pesada (ReportLab/
# pypdf/R2) roda fora do event loop. NÃO usa `from __future__ import annotations`
# (mantém as anotações de body resolvidas pelo FastAPI).
import asyncio
import logging
import re
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
from services.geo_urbano import geo_export as GEXP
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
    # Aprovação (devolvidos pela Superintendência, já assinados/carimbados):
    "oficio_assinado",      # Ofício de Aprovação EXPEDIDO e ASSINADO pela Superintendência
    "memorial_aprovado",    # Memorial aprovado/assinado (volta do órgão)
    "mapa_aprovado",        # Mapa aprovado/assinado (volta do órgão)
    "mapa_desdobro",  # desdobro: 1 mapa por lote resultante (vincula lote_id)
    "mapa_retificado",  # retificação: mapa "como está"
    "mapa_atual", "mapa_remembramento", "bci", "certidao_inteiro_teor",
    "cnd_iptu", "guia_iptu", "comprovante_pagamento_iptu",
    "contrato_social", "doc_socio", "doc_proprietario", "cnh", "certidao_casamento",
    "art_trt", "art_trt_boleto", "comprovante_pagamento_trt",
    # usucapião
    "planta_usucapiao", "memorial_usucapiao", "ata_notarial_assinada", "certidao_matricula", "negativa_propriedade",
    "certidao_confrontante", "certidao_negativa", "iptu_usucapiao", "justo_titulo",
    "certidao_obito", "formal_partilha", "certidao_estado_civil", "procuracao_oab",
    "certidao_distribuidor", "prova_posse", "doc_requerente", "foto_imovel",
    "doc_advogado", "carteira_oab",   # identidade + carteira da OAB do advogado (art. 216-A)
}
_MAX_UPLOAD = 30 * 1024 * 1024
_PDF = "application/pdf"

# Mapeia as seções do dossiê (§9) para os tipos de upload que as compõem.
_DOSSIE_UPLOADS = {
    "oficio_aprovacao": ["oficio_assinado"],   # Ofício EXPEDIDO pela Superintendência (upload)
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
                  "quadro_retificacao",
                  # usucapião
                  "requerimento_usucapiao", "ata_notarial", "edital_usucapiao"}


def _agora():
    return datetime.now(timezone.utc)


async def _numero(db):
    ano = _agora().year
    res = await db.counters.find_one_and_update(
        {"_id": f"geo_urbano_{ano}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=ReturnDocument.AFTER,
    )
    return f"URB-{ano}-{res['seq']:04d}"


async def _autoalinhar_vertices(db, doc):
    """Self-heal: projetos anteriores ao fix v1.4.1085 têm a coordenada de cada linha
    apontando para o vértice PARA (deslocada em 1). Re-alinha UMA vez (flag
    coords_alinhadas), persiste e atualiza o doc em memória. Idempotente."""
    if doc.get("coords_alinhadas") or not doc.get("vertices"):
        return
    try:
        from services.geo_urbano.extractor import alinhar_coords_aos_vertices
        antes = [(v.get("coord_e"), v.get("coord_n")) for v in doc["vertices"]]
        alinhar_coords_aos_vertices(doc["vertices"])
        depois = [(v.get("coord_e"), v.get("coord_n")) for v in doc["vertices"]]
        sets = {"coords_alinhadas": True}
        if antes != depois:
            sets["vertices"] = doc["vertices"]
            if doc.get("vertices"):
                from services.geo_urbano import geometria as _G
                doc["area_calculada_m2"] = _G.area_m2(doc["vertices"])
                sets["area_calculada_m2"] = doc["area_calculada_m2"]
        await db.geo_urbano_projetos.update_one({"id": doc["id"]}, {"$set": sets})
        doc["coords_alinhadas"] = True
    except Exception:  # noqa: BLE001
        pass


def _auto_orientar_inmemory(doc):
    """Preenche `lado` (calculado) em cada vértice p/ exibição no quadro/Memorial,
    respeitando `frente_idx` e overrides manuais (`lado_manual`). NÃO persiste — o
    Memorial recalcula na geração e o autosave grava quando o usuário edita. Assim
    os lados já aparecem ao ABRIR o projeto, sem precisar clicar em 'Orientar lados'."""
    try:
        if len(doc.get("vertices") or []) >= 3:
            from services.geo_urbano.orientacao import aplicar_lados
            aplicar_lados(doc)   # escreve `lado` in-place (honra lado_manual/frente_idx)
    except Exception:  # noqa: BLE001
        pass


async def _get(db, pid, uid):
    doc = await db.geo_urbano_projetos.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    await _autoalinhar_vertices(db, doc)
    _auto_orientar_inmemory(doc)
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
    docs = [serialize_doc(d) async for d in cur]
    ids = [d["id"] for d in docs]
    # enriquece o card com o status da assinatura do proprietário (sessão por projeto)
    sess = {}
    if ids:
        async for s in db.geo_urbano_assinatura_sessoes.find({"projeto_id": {"$in": ids}, "user_id": uid}):
            sigs = s.get("signatarios") or []
            sess[s["projeto_id"]] = {
                "existe": True, "status": s.get("status"),
                "assinados": sum(1 for x in sigs if x.get("status") == "assinado"),
                "total": len(sigs),
                "signatarios": [{"nome": x.get("nome"), "papel": x.get("papel"),
                                 "status": x.get("status")} for x in sigs],
            }
    # assinaturas ICP do TÉCNICO (Memorial/Mapa/ART) por projeto
    tec = {}
    if ids:
        async for r in db.geo_urbano_assinaturas.find({"projeto_id": {"$in": ids}, "user_id": uid}):
            tec.setdefault(r["projeto_id"], []).append({
                "doc": r.get("doc"), "nome": _PECAS_ASSINAVEIS.get(r.get("doc"), r.get("doc")),
                "assinado": r.get("icp_status") == "assinado"})
    for d in docs:
        d["assinatura_prop"] = sess.get(d["id"])
        peças = tec.get(d["id"]) or []
        d["assinatura_tecnico"] = {
            "existe": bool(peças),
            "assinados": sum(1 for x in peças if x["assinado"]),
            "total": len(peças), "pecas": peças,
        } if peças else None
        # % do card = MAIOR entre a heurística de dados e as ETAPAS marcadas concluídas
        total_etapas = 9 if (d.get("tipo_servico") == "usucapiao") else 8
        n_etapas = sum(1 for v in (d.get("etapas_concluidas") or {}).values() if v)
        andamento = int(round(100 * n_etapas / total_etapas)) if total_etapas else 0
        d["completude"] = max(int(d.get("completude") or 0), andamento)
    return docs


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
                 "cmi_resultante", "cmi_controle", "cadastro_novo", "cadastro_antigo",
                 "area_declarada_m2", "perimetro_m", "trt_numero", "frente_idx",
                 # desdobro
                 "matricula_mae_id", "area_mae_m2", "qtd_lotes_resultantes", "area_via_doacao_m2",
                 "lote_minimo_municipal_m2", "testada_minima_m",
                 # retificação
                 "retificacao_tipo",
                 # usucapião
                 "modalidade_usucapiao", "fundamento_legal", "valor_atribuido",
                 "situacao_registral", "matricula_usucapienda_id")
    for c in escalares:
        if c in dados:
            sets[c] = dados[c]
            editados[c] = True
    if "retificacao_analise" in dados and isinstance(dados["retificacao_analise"], dict):
        sets["retificacao_analise"] = dados["retificacao_analise"]
    # auditoria por etapa (dicts) — precisa ser gravado explicitamente
    for campo in ("etapas_concluidas", "etapas_concluidas_em"):
        if campo in dados and isinstance(dados[campo], dict):
            sets[campo] = dados[campo]
    for grupo in ("cartorio", "superintendencia", "responsavel_tecnico", "posse"):
        if grupo in dados and isinstance(dados[grupo], dict):
            atual = dict(doc.get(grupo) or {})
            atual.update(dados[grupo])
            sets[grupo] = atual
    for grupo in ("matriculas", "bci", "vertices", "partes", "iptu", "lotes_resultantes",
                  "vertices_atual", "confrontantes",
                  "soma_posses", "provas_posse", "anuentes", "checklist"):
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
_TIPOS_EXTRACAO = ["mapa_remembramento", "planta_usucapiao", "memorial_usucapiao",
                   "certidao_inteiro_teor", "bci", "cnd_iptu", "guia_iptu"]


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
    # Usucapião usa UM único mapa (planta_usucapiao) — o extractor lê a chave
    # "mapa_remembramento", então a planta entra por ela quando não há mapa de remembramento.
    if not ups_bytes.get("mapa_remembramento") and ups_bytes.get("planta_usucapiao"):
        ups_bytes["mapa_remembramento"] = ups_bytes["planta_usucapiao"]
    if not ups_bytes:
        raise HTTPException(status_code=422, detail="Envie ao menos a Planta/Mapa (e Certidão/BCI/IPTU) para extrair.")

    res = await asyncio.to_thread(EX.extrair_tudo, ups_bytes)
    # DIAGNÓSTICO (temporário): SEMPRE dispara na usucapião sem vértices — mostra o que
    # está no BANCO vs o que foi COLETADO (revela se o memorial chega na extração).
    if doc.get("tipo_servico") == "usucapiao" and not res.get("vertices"):
        try:
            up = doc.get("uploads") or {}
            mem_items = up.get("memorial_usucapiao") or []
            diag = (f"diag · DB={[k for k, v in up.items() if v]}"
                    f" · mem-itens={len(mem_items)},keys={sum(1 for i in mem_items if i.get('key'))}"
                    f" · coletados={list(ups_bytes.keys())}")
            if ups_bytes.get("memorial_usucapiao"):
                mb = ups_bytes["memorial_usucapiao"][0]
                textos = await asyncio.to_thread(EX._textos_candidatos, mb)
                diag += f" · mem={len(mb)}B,motores={len(textos)}"
                for i, txt in enumerate(textos):
                    tn = re.sub(r"\s+", " ", txt)
                    diag += f",m{i}={len(tn)}c/seg={len(re.findall(r'at[ée] o v', tn))}"
            res.setdefault("avisos", []).append(diag[:500])
        except Exception as _e:  # noqa: BLE001
            res.setdefault("avisos", []).append(f"diag-erro: {type(_e).__name__}: {str(_e)[:140]}")
    editados = doc.get("campos_editados") or {}
    sets = {}
    # Persiste o extraído quando o campo NÃO foi editado À MÃO, OU quando está VAZIO no
    # projeto (o autosave do wizard marca 'vertices' como editado mesmo vazio — não pode
    # bloquear a extração de popular um campo que não tem nada).
    for campo in ("matriculas", "bci", "vertices", "iptu"):
        if campo in res and res[campo] and (not editados.get(campo) or not (doc.get(campo) or [])):
            sets[campo] = res[campo]
    # área/perímetro são valores DO DOCUMENTO — a re-extração os ATUALIZA (o documento é a
    # autoridade; o usuário re-extrai justamente para refletir o memorial/mapa).
    for campo in ("area_declarada_m2", "perimetro_m"):
        if res.get(campo) is not None:
            sets[campo] = res[campo]
    for campo in ("cmi_resultante", "cadastro_novo", "cadastro_antigo"):
        if res.get(campo) is not None and (not editados.get(campo) or not doc.get(campo)):
            sets[campo] = res[campo]
    # PRESERVA o confrontante_lado já preenchido (a planilha do mapa não o traz) —
    # não apaga o que o usuário editou ao reextrair.
    if "vertices" in sets:
        antigos = {v.get("de"): v for v in (doc.get("vertices") or [])}
        for v in sets["vertices"]:
            if not v.get("confrontante_lado"):
                ant = antigos.get(v.get("de"))
                if ant and ant.get("confrontante_lado"):
                    v["confrontante_lado"] = ant["confrontante_lado"]
    # TRT/ART automática do upload art_trt → preenche trt_numero do projeto
    if not editados.get("trt_numero") and not doc.get("trt_numero"):
        art = uploads.get("art_trt") or []
        if art and art[0].get("key"):
            try:
                raw = await asyncio.to_thread(r2_storage.download_bytes, art[0]["key"])
                trt = await asyncio.to_thread(EX.parse_art_trt, raw, art[0].get("nome") or "")
                if trt:
                    sets["trt_numero"] = trt
            except Exception:  # noqa: BLE001
                pass
    base = {**doc, **sets}
    if base.get("vertices"):
        sets["area_calculada_m2"] = GEOM.area_m2(base["vertices"])
    sets["status"] = "conferencia"
    sets["extracao_em"] = _agora().isoformat()   # auditoria: carimbo da extração
    sets["extracao_por"] = uid
    sets["completude"] = calcular_completude(base)
    sets["updated_at"] = _agora().isoformat()
    await db.geo_urbano_projetos.update_one({"id": pid, "user_id": uid}, {"$set": sets})
    novo = {**doc, **sets}
    return {
        "ok": True, "avisos": res.get("avisos", []),
        "extracao_em": sets["extracao_em"],
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


@router.post("/projetos/{pid}/orientar")
async def orientar_lados(pid: str, frente_idx: int = Query(None),
                         uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Classifica os segmentos da poligonal em FRENTE/LATERAL DIREITA/ESQUERDA/FUNDO
    (convenção: rua = frente; direita/esquerda de quem está no lote olhando a rua) e
    grava o `lado` em cada vértice. `frente_idx` (opcional) força a testada quando os
    confrontantes não trazem logradouro. Retorna `frente_indefinida` p/ a UI pedir a
    marcação manual da frente quando não houver rua nas confrontações."""
    from services.geo_urbano.orientacao import aplicar_lados
    doc = await _get(db, pid, uid)
    if frente_idx is not None:
        doc["frente_idx"] = frente_idx
    cls = aplicar_lados(doc)   # escreve `lado` nos vértices (in-place)
    sets = {"vertices": doc.get("vertices") or [], "updated_at": _agora().isoformat()}
    if frente_idx is not None:
        sets["frente_idx"] = frente_idx
    await db.geo_urbano_projetos.update_one({"id": pid, "user_id": uid}, {"$set": sets})
    return {"frente_indefinida": cls["frente_indefinida"], "lados": cls["lados"],
            "vertices": doc.get("vertices") or []}


# ──────────────────────────────────────────────────────────────────────────────
# Usucapião Extrajudicial — validação, checklist, anuências, seed
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/projetos/{pid}/usucapiao/validacao")
async def usucapiao_validacao(pid: str, ano_ref: int = Query(None),
                              uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services.geo_urbano import usucapiao as USU
    doc = await _get(db, pid, uid)
    return USU.validar_posse(doc, ano_ref)


@router.get("/projetos/{pid}/usucapiao/checklist")
async def usucapiao_checklist(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services.geo_urbano import usucapiao as USU
    doc = await _get(db, pid, uid)
    return {"checklist": USU.checklist_para(doc), "anuentes": USU.anuentes_de(doc)}


@router.post("/projetos/{pid}/usucapiao/seed-juridico")
async def usucapiao_seed_juridico(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Pré-preenche o bloco jurídico a partir do técnico (provas←uploads, confrontantes←
    vértices, checklist marca planta/ART). Idempotente: não sobrescreve o que já existe."""
    from services.geo_urbano import usucapiao as USU
    doc = await _get(db, pid, uid)
    sets = USU.seed_juridico(doc)
    if sets:
        sets["updated_at"] = _agora().isoformat()
        await db.geo_urbano_projetos.update_one({"id": pid, "user_id": uid}, {"$set": sets})
    return serialize_doc({**doc, **sets})


@router.get("/projetos/{pid}/usucapiao/anuencia/{aid}")
async def usucapiao_anuencia_pdf(pid: str, aid: str, modo: str = Query("declaracao"),
                                 tema: str = Query(None),
                                 uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services.geo_urbano import usucapiao as USU
    doc = await _get(db, pid, uid)
    await _injetar_logo(db, uid, doc)
    logo = doc.get("_brand_logo_bytes")
    tema = tema or doc.get("tema") or "prime_i"
    anuente = next((a for a in USU.anuentes_de(doc) if a.get("id") == aid or a.get("nome") == aid), None)
    if not anuente:
        raise HTTPException(status_code=404, detail="Anuente não encontrado.")
    fn = PDF.notificacao if modo == "notificacao" else PDF.declaracao_anuencia
    data = await asyncio.to_thread(fn, doc, anuente, tema, logo)
    nome = f"{modo}_{(anuente.get('nome') or aid)}.pdf"
    return Response(content=data, media_type=_PDF,
                    headers={"Content-Disposition": f'inline; filename="{nome}"'})


@router.post("/projetos/seed-usucapiao")
async def criar_seed_usucapiao(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services.geo_urbano.seed import build_seed_usucapiao
    doc = build_seed_usucapiao(uid)
    doc["numero"] = await _numero(db)
    await db.geo_urbano_projetos.insert_one(doc)
    return serialize_doc(doc)


@router.get("/projetos/{pid}/drls")
async def listar_drls(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Confrontantes que geram DRL (particulares) + status da anuência."""
    doc = await _get(db, pid, uid)
    return [{"id": c["id"], "confrontante": c.get("confrontante"), "lado": c.get("lado"),
             "medida_m": c.get("medida_m"), "tipo": c.get("tipo"),
             "anuencia": (c.get("anuencia") or {}).get("status", "pendente")}
            for c in PDF.confrontantes_para_drl(doc)]


@router.get("/projetos/{pid}/drl/{cid}")
async def baixar_drl(pid: str, cid: str, tema: str = Query(None),
                     uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    conf = next((c for c in (doc.get("confrontantes") or []) if c.get("id") == cid), None)
    if not conf:
        raise HTTPException(status_code=404, detail="Confrontante não encontrado.")
    if (conf.get("tipo") or "particular") != "particular":
        raise HTTPException(status_code=422, detail="Confrontante de via/área pública dispensa DRL.")
    tema = tema or doc.get("tema") or "prime_i"
    data = await asyncio.to_thread(PDF.drl, doc, conf, tema)
    nome = f"drl_{(conf.get('confrontante') or cid)}.pdf"
    return Response(content=data, media_type=_PDF,
                    headers={"Content-Disposition": f'inline; filename="{nome}"'})


@router.post("/projetos/{pid}/drl/{cid}/anuencia")
async def drl_anuencia(pid: str, cid: str, body: dict,
                       uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Registra a anuência do confrontante (assinada/recusada/notificado)."""
    doc = await _get(db, pid, uid)
    confs = [dict(c) for c in (doc.get("confrontantes") or [])]
    alvo = next((c for c in confs if c.get("id") == cid), None)
    if not alvo:
        raise HTTPException(status_code=404, detail="Confrontante não encontrado.")
    status = (body or {}).get("status") or "assinada"
    if status not in ("pendente", "assinada", "recusada", "notificado"):
        raise HTTPException(status_code=422, detail="Status de anuência inválido.")
    alvo["anuencia"] = {"status": status, "em": _agora().isoformat(),
                        "assinatura_id": (body or {}).get("assinatura_id")}
    await db.geo_urbano_projetos.update_one(
        {"id": pid, "user_id": uid}, {"$set": {"confrontantes": confs, "updated_at": _agora().isoformat()}})
    return {"ok": True, "status": status}


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


async def _injetar_logo(db, uid: str, doc: dict):
    """Carrega o logo white-label do usuário em doc['_brand_logo_bytes'] (best-effort)."""
    try:
        from services.branding_context import BrandContext
        brand = await BrandContext.for_user(db, uid)
        logo = await asyncio.to_thread(brand.custom_logo_bytes)
        if logo:
            doc["_brand_logo_bytes"] = logo
    except Exception:  # noqa: BLE001
        pass


async def _firma_tecnico_bytes(db, uid: str):
    """Bytes do PNG da firma gráfica do RT (assinatura_tecnico_b64 → assinatura_visual_b64)."""
    try:
        import base64
        perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}
        b64 = perfil.get("assinatura_tecnico_b64") or perfil.get("assinatura_visual_b64")
        return base64.b64decode(str(b64).split(",")[-1]) if b64 else None
    except Exception:  # noqa: BLE001
        return None


async def _injetar_assinatura_tecnico(db, uid: str, doc: dict):
    """Carrega a firma gráfica do RT em doc['_tecnico_assinatura_bytes'] + a posição/dimensão
    em doc['_tecnico_assinatura_pos'] — carimbada no Memorial ao gerar/enviar."""
    firma = await _firma_tecnico_bytes(db, uid)
    if firma:
        doc["_tecnico_assinatura_bytes"] = firma
    try:
        perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}
        if perfil.get("assinatura_tecnico_pos"):
            doc["_tecnico_assinatura_pos"] = perfil["assinatura_tecnico_pos"]
    except Exception:  # noqa: BLE001
        pass


@router.get("/projetos/{pid}/documentos/{tipo}")
async def baixar_documento(pid: str, tipo: str, tema: str = Query(None), lote: str = Query(None),
                           uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    await _injetar_logo(db, uid, doc)
    await _injetar_assinatura_tecnico(db, uid, doc)
    logo = doc.get("_brand_logo_bytes")
    tema = tema or doc.get("tema") or "prime_i"
    # Memorial de UM lote resultante (desdobro)
    if tipo == "memorial_descritivo" and lote:
        lt = next((x for x in (doc.get("lotes_resultantes") or []) if x.get("id") == lote), None)
        if not lt:
            raise HTTPException(status_code=404, detail="Lote resultante não encontrado.")
        data = await asyncio.to_thread(PDF.gerar_pdf, "memorial_descritivo", projeto_do_lote(doc, lt), tema, logo)
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
        data = await asyncio.to_thread(PDF.gerar_pdf, tipo, doc, tema, logo)
        nome = f"{tipo}_{(doc.get('numero') or pid)}.pdf"
    else:
        raise HTTPException(status_code=422, detail=f"Documento inválido: {tipo}")
    return Response(content=data, media_type=_PDF,
                    headers={"Content-Disposition": f'inline; filename="{nome}"'})


_PECA_LABEL = {
    "dossie": "Dossiê consolidado", "requerimento_cartorio": "Requerimento (Cartório de RI)",
    "requerimento_superintendencia": "Requerimento (Superintendência)",
    "memorial_descritivo": "Memorial Descritivo", "cadeia_dominical": "Cadeia Dominical",
    # usucapião
    "requerimento_usucapiao": "Requerimento de Usucapião", "ata_notarial": "Minuta da Ata Notarial",
    "edital_usucapiao": "Edital de Usucapião", "art_trt": "ART / TRT",
}


async def _peca_pdf_bytes(db, doc, tipo, tema):
    """Bytes do PDF de uma peça — versão ASSINADA quando houver (Dossiê via merge)."""
    if tipo == "dossie":
        return await _montar_dossie(db, doc, tema)
    assinadas = await _pecas_assinadas(db, doc)
    if assinadas.get(tipo):
        return assinadas[tipo]
    if tipo == "art_trt":
        # ART/TRT é UPLOAD (não gerável) — envia o arquivo enviado (imagem→PDF)
        ups = await _ub(doc, "art_trt")
        if ups:
            return ups[0]
        raise HTTPException(status_code=422, detail="ART/TRT ainda não foi enviada.")
    if tipo in _DOCS_GERAVEIS:
        return await asyncio.to_thread(PDF.gerar_pdf, tipo, doc, tema, doc.get("_brand_logo_bytes"))
    raise HTTPException(status_code=422, detail=f"Peça inválida: {tipo}")


@router.post("/projetos/{pid}/enviar-whatsapp")
async def enviar_whatsapp(pid: str, body: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Envia o PDF de uma peça (Dossiê/Requerimento/Memorial/Cadeia) por WhatsApp a um contato."""
    telefone = re.sub(r"\D", "", str((body or {}).get("telefone") or ""))
    if len(telefone) < 10:
        raise HTTPException(status_code=422, detail="Informe um WhatsApp válido (55 + DDD + número).")
    doc = await _get(db, pid, uid)
    await _injetar_logo(db, uid, doc)
    await _injetar_assinatura_tecnico(db, uid, doc)
    tema = doc.get("tema") or "prime_i"
    peca = (body or {}).get("peca") or "dossie"
    pdf_bytes = await _peca_pdf_bytes(db, doc, peca, tema)
    if not pdf_bytes or pdf_bytes[:5] != b"%PDF-":
        raise HTTPException(status_code=500, detail="Falha ao gerar o PDF da peça.")
    cfg = await PROP.zapi_cfg(db, uid)
    if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(status_code=422, detail="Configure a integração Z-API (WhatsApp) antes de enviar.")
    label = _PECA_LABEL.get(peca, "Documento")
    caption = ((body or {}).get("legenda")
               or f"{label} — {doc.get('denominacao_imovel') or ''} ({doc.get('numero') or ''})").strip()
    fname = f"{peca}_{(doc.get('numero') or pid)}.pdf".replace("/", "-")
    from services import zapi_service
    try:
        await zapi_service.send_document_pdf(
            instance_id=cfg.get("zapi_instance_id"), token=cfg.get("zapi_token"),
            security_token=cfg.get("zapi_security_token"), phone=telefone,
            pdf_bytes=pdf_bytes, filename=fname, caption=caption)
    except Exception as e:  # noqa: BLE001
        logger.error("Geo Urbano: envio WhatsApp falhou: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Falha ao enviar pelo WhatsApp: {e}")
    return {"ok": True, "enviado": telefone, "peca": peca}


# ──────────────────────────────────────────────────────────────────────────────
# SIG-RI (Prov. CNJ 195/2025) — Shapefile + KML + GeoJSON (malha fundiária do RI)
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/projetos/{pid}/shapefile")
async def baixar_shapefile(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    try:
        data = await asyncio.to_thread(GEXP.gerar_shapefile_bytes, doc)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    nome = f"SIGRI_{(doc.get('numero') or pid)}.zip"
    return Response(content=data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@router.get("/projetos/{pid}/kml")
async def baixar_kml(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    kml = await asyncio.to_thread(GEXP.gerar_kml, doc)
    nome = f"{(doc.get('numero') or pid)}.kml"
    return Response(content=kml.encode("utf-8"), media_type="application/vnd.google-earth.kml+xml",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@router.get("/projetos/{pid}/geojson")
async def baixar_geojson(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _get(db, pid, uid)
    return GEXP.gerar_geojson(doc)


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


async def _ub(doc, tipo):
    """Bytes de TODOS os arquivos de um tipo de upload (na ordem enviada)."""
    out = []
    for it in (doc.get("uploads") or {}).get(tipo) or []:
        if it.get("key"):
            try:
                out.append(await asyncio.to_thread(r2_storage.download_bytes, it["key"]))
            except Exception:  # noqa: BLE001
                continue
    return out


# Rótulo amigável de cada tipo de upload — vira o TÍTULO da página do anexo no Dossiê.
_TITULO_UPLOAD = {
    "planta_usucapiao": "Planta / Mapa Georreferenciado", "mapa_remembramento": "Mapa",
    "mapa_atual": "Mapa Atual", "mapa_desdobro": "Mapa de Desdobro", "mapa_retificado": "Mapa Retificado",
    "art_trt": "ART / TRT / RRT", "art_trt_boleto": "Boleto da TRT",
    "certidao_inteiro_teor": "Certidão de Inteiro Teor", "certidao_matricula": "Certidão da Matrícula",
    "negativa_propriedade": "Negativa de Propriedade", "certidao_confrontante": "Certidão do Confrontante",
    "certidao_negativa": "Certidão Negativa (ônus/ações reais)", "certidao_distribuidor": "Certidão do Distribuidor",
    "certidao_obito": "Certidão de Óbito", "formal_partilha": "Formal de Partilha",
    "certidao_estado_civil": "Certidão de Estado Civil", "certidao_casamento": "Certidão de Casamento",
    "prova_posse": "Prova de Posse", "justo_titulo": "Justo Título", "foto_imovel": "Relatório Fotográfico",
    "iptu_usucapiao": "IPTU / Valor Venal", "cnd_iptu": "CND de IPTU", "guia_iptu": "Guia de IPTU (DAM)",
    "comprovante_pagamento_iptu": "Comprovante de Pagamento do IPTU", "bci": "BCI — Boletim de Cadastro Imobiliário",
    "doc_advogado": "Documento de Identidade do Advogado(a)", "carteira_oab": "Carteira da OAB",
    "procuracao_oab": "Procuração (OAB)", "doc_requerente": "Documento de Identidade do Requerente",
    "doc_proprietario": "Documento do Proprietário", "cnh": "CNH",
}


async def _ub_titulado(doc, tipo):
    """Como `_ub`, mas cada arquivo vira um PDF com o TÍTULO do documento no topo
    (imagem) ou uma página de rótulo (PDF). O subtítulo é o nome do arquivo enviado —
    útil p/ distinguir frente/verso etc. Assim cada anexo sai em página própria e
    identificada no Dossiê."""
    base = _TITULO_UPLOAD.get(tipo, tipo.replace("_", " ").title())
    out = []
    for it in (doc.get("uploads") or {}).get(tipo) or []:
        if not it.get("key"):
            continue
        try:
            raw = await asyncio.to_thread(r2_storage.download_bytes, it["key"])
        except Exception:  # noqa: BLE001
            continue
        sub = (it.get("nome") or "").rsplit(".", 1)[0].strip() or None
        pdf = await asyncio.to_thread(DOSSIE.pagina_documento, raw, base, sub)
        if pdf:
            out.append(pdf)
    return out


async def _pecas_assinadas(db, doc):
    """{tipo_peça: bytes} das peças ASSINADAS que devem entrar no Dossiê:
    (1) carimbo DESENHADO do proprietário (Requerimento + ART/TRT da sessão CONCLUÍDA) —
        traz os traços das partes/advogado; PREVALECE;
    (2) selo ICP-Brasil do TÉCNICO (Memorial/Mapa/ART/TRT/Requerimento) de
        `geo_urbano_assinaturas` (icp_status=assinado) — PREENCHE as peças que o
        proprietário não assina (Memorial/Mapa) e serve de fallback nas demais.
    Assim as peças que o RT assinou por ICP vão ao Dossiê final."""
    out = {}
    pid, uid = doc.get("id"), doc.get("user_id")
    # 1) carimbo desenhado do proprietário (sessão concluída) — prevalece
    try:
        s = await db.geo_urbano_assinatura_sessoes.find_one(
            {"projeto_id": pid, "user_id": uid, "status": "concluido"})
        for d, key in ((s or {}).get("pdf_keys_final") or {}).items():
            try:
                data = await asyncio.to_thread(r2_storage.download_bytes, key)
                if data and data[:5] == b"%PDF-":
                    out[d] = data   # versão que as partes receberam e assinaram
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        logger.warning("Geo Urbano: falha ao carregar peças carimbadas do proprietário.", exc_info=True)
    # 2) selo ICP-Brasil do técnico — preenche as peças ainda sem carimbo do proprietário
    try:
        from routes.assinatura import _load_assinatura_bytes
        recs = await db.geo_urbano_assinaturas.find(
            {"user_id": uid, "projeto_id": pid, "icp_status": "assinado"}).to_list(50)
        for r in recs:
            d = r.get("doc")
            if not d or d in out:   # carimbo do proprietário prevalece
                continue
            try:
                data, _a = await _load_assinatura_bytes(db, "geo_urbano", r["id"])
                if data and data[:5] == b"%PDF-":
                    out[d] = data
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        logger.warning("Geo Urbano: falha ao carregar peças ICP do técnico.", exc_info=True)
    return out


async def _montar_dossie(db, doc, tema):
    logo = doc.get("_brand_logo_bytes")
    assinadas = await _pecas_assinadas(db, doc)
    capa_pdf = None
    img = await _imagem_imovel_bytes(doc)
    if img:
        capa_pdf = await asyncio.to_thread(CAPA.gerar_capa_pdf, doc, img)
    tipo = doc.get("tipo_servico")
    uploads = doc.get("uploads") or {}

    # ── Remembramento / Desdobro: ordem por VIA (cada protocolo um conjunto completo)
    if tipo in ("remembramento", "desdobro"):
        # peça assinada (ICP/carimbo) PREVALECE sobre a regerada em branco
        req_cart = assinadas.get("requerimento_cartorio") \
            or await asyncio.to_thread(PDF.gerar_pdf, "requerimento_cartorio", doc, tema, logo)
        req_super = assinadas.get("requerimento_superintendencia") \
            or await asyncio.to_thread(PDF.gerar_pdf, "requerimento_superintendencia", doc, tema, logo)
        # Memorial(is) — aprovado (upload do órgão) > por lote/remembramento (regerado FRESCO,
        # já com logo atual + firma gráfica do RT carimbada)
        if uploads.get("memorial_aprovado"):
            memoriais = await _ub(doc, "memorial_aprovado")
        elif tipo == "desdobro" and (doc.get("lotes_resultantes") or []):
            memoriais = [await asyncio.to_thread(PDF.gerar_pdf, "memorial_descritivo", projeto_do_lote(doc, lt), tema, logo)
                         for lt in sorted(doc["lotes_resultantes"], key=lambda x: x.get("ordem", 0))]
        else:
            memoriais = [await asyncio.to_thread(PDF.gerar_pdf, "memorial_descritivo", doc, tema, logo)]
        mapa_atual = await _ub(doc, "mapa_atual")
        # Mapa do ato — aprovado (upload) > upload do ato (já traz a assinatura do RT)
        if uploads.get("mapa_aprovado"):
            mapa_ato = await _ub(doc, "mapa_aprovado")
        else:
            mapa_ato = (await _ub(doc, "mapa_desdobro")) if tipo == "desdobro" else (await _ub(doc, "mapa_remembramento"))
        art = ([assinadas["art_trt"]] if assinadas.get("art_trt") else await _ub(doc, "art_trt"))
        boleto = await _ub(doc, "art_trt_boleto")
        mapa_ato_titulo = "Mapa de Desdobro" if tipo == "desdobro" else "Mapa de Remembramento"

        def via(req_bytes, titulo_req):
            return [(titulo_req, [req_bytes]), ("Mapa Atual", mapa_atual),
                    (mapa_ato_titulo, mapa_ato), ("Memorial Descritivo", memoriais),
                    ("ART / TRT", art), ("Boleto da TRT", boleto)]

        secoes = via(req_cart, "Requerimento — Via Cartório de RI")
        secoes += via(req_super, "Requerimento — Via Superintendência (SHRF)")
        secoes.append(("Ofício de Aprovação (Superintendência)", await _ub(doc, "oficio_assinado")))
        secoes += [
            ("Certidões de Inteiro Teor", await _ub(doc, "certidao_inteiro_teor")),
            ("Regularidade de IPTU (CND / guias / boletos)",
             (await _ub(doc, "cnd_iptu")) + (await _ub(doc, "guia_iptu")) + (await _ub(doc, "comprovante_pagamento_iptu"))),
            ("Boletins de Cadastro Imobiliário (BCI)", await _ub(doc, "bci")),
            ("Documentos do Proprietário",
             (await _ub(doc, "contrato_social")) + (await _ub(doc, "doc_socio"))
             + (await _ub(doc, "doc_proprietario")) + (await _ub(doc, "cnh")) + (await _ub(doc, "certidao_casamento"))),
        ]
        return await asyncio.to_thread(DOSSIE.gerar_dossie_ordenado, doc, secoes, capa_pdf)

    # ── Usucapião Extrajudicial: ordem de protocolo do art. 216-A LRP
    if tipo == "usucapiao":
        from services.geo_urbano import usucapiao as USU
        req = assinadas.get("requerimento_usucapiao") \
            or await asyncio.to_thread(PDF.gerar_pdf, "requerimento_usucapiao", doc, tema, logo)
        # Memorial: ICP-assinado pelo RT PREVALECE (é a peça que o técnico assinou) >
        # enviado pela agrimensura (memorial_usucapiao) > gerado fresco
        memorial_up = await _ub(doc, "memorial_usucapiao")
        memorial = assinadas.get("memorial_descritivo") \
            or (memorial_up[0] if memorial_up else None) \
            or await asyncio.to_thread(PDF.gerar_pdf, "memorial_descritivo", doc, tema, logo)
        ata = await asyncio.to_thread(PDF.gerar_pdf, "ata_notarial", doc, tema, logo)
        edital = await asyncio.to_thread(PDF.gerar_pdf, "edital_usucapiao", doc, tema, logo)
        # Anuência/notificação: só p/ confrontantes/titulares que ASSINAM — exclui via
        # pública (dispensada, art. 216-A) e o titular registral FALECIDO (já fora de anuentes_de).
        anuentes = [a for a in USU.anuentes_de(doc)
                    if a.get("nome") and a.get("tipo") != "via_publica"]
        decls = [await asyncio.to_thread(PDF.declaracao_anuencia, doc, a, tema, logo) for a in anuentes]
        notifs = [await asyncio.to_thread(PDF.notificacao, doc, a, tema, logo) for a in anuentes]
        # Conteúdo por seção (chaves de DOSSIE.ORDEM_DOSSIE_USUCAPIAO) → a ordem e os
        # títulos vêm da constante (fonte única; nunca diverge da ORDEM_DOSSIE_USUCAPIAO).
        conteudo = {
            "requerimento_usucapiao": [req],
            "ata_notarial": (await _ub(doc, "ata_notarial_assinada")) or [ata],
            # Mapa — ICP-assinado pelo RT PREVALECE; senão a planta dedicada/mapas reusados das abas técnicas
            "planta_mapa": ([await asyncio.to_thread(DOSSIE.pagina_documento, assinadas["mapa"], "Planta / Mapa Georreferenciado", None)]
                            if assinadas.get("mapa")
                            else (await _ub_titulado(doc, "planta_usucapiao")) + (await _ub_titulado(doc, "mapa_remembramento")) + (await _ub_titulado(doc, "mapa_atual"))),
            "memorial_descritivo": [memorial],
            # ART/TRT — versão ASSINADA (carimbo do proprietário/ICP) prevalece sobre o upload
            "art_trt": ([await asyncio.to_thread(DOSSIE.pagina_documento, assinadas["art_trt"], "ART / TRT / RRT", None)]
                        if assinadas.get("art_trt") else await _ub_titulado(doc, "art_trt"))
                       + (await _ub_titulado(doc, "art_trt_boleto")),
            # certidão — tipo dedicado OU a "certidão de inteiro teor" reusada das abas técnicas
            "certidao_matricula": (await _ub_titulado(doc, "certidao_matricula")) + (await _ub_titulado(doc, "negativa_propriedade"))
                                  + (await _ub_titulado(doc, "certidao_inteiro_teor")),
            "declaracoes_anuencia": decls,
            "certidoes_confrontantes": await _ub_titulado(doc, "certidao_confrontante"),
            "certidoes_negativas": await _ub_titulado(doc, "certidao_negativa"),
            "iptu_valor_venal": (await _ub_titulado(doc, "iptu_usucapiao")) + (await _ub_titulado(doc, "cnd_iptu"))
                                + (await _ub_titulado(doc, "guia_iptu")) + (await _ub_titulado(doc, "comprovante_pagamento_iptu")),
            "provas_posse": await _ub_titulado(doc, "prova_posse"),
            "relatorio_fotografico": await _ub_titulado(doc, "foto_imovel"),
            "docs_herdeiro": (await _ub_titulado(doc, "certidao_obito")) + (await _ub_titulado(doc, "formal_partilha")),
            "justo_titulo": await _ub_titulado(doc, "justo_titulo"),
            "certidoes_distribuidores": await _ub_titulado(doc, "certidao_distribuidor"),
            "notificacoes_edital": notifs + [edital],
            "docs_advogado": (await _ub_titulado(doc, "doc_advogado")) + (await _ub_titulado(doc, "carteira_oab"))
                             + (await _ub_titulado(doc, "procuracao_oab")),
            "docs_requerente": (await _ub_titulado(doc, "doc_requerente")) + (await _ub_titulado(doc, "certidao_estado_civil"))
                               + (await _ub_titulado(doc, "doc_proprietario"))
                               + (await _ub_titulado(doc, "cnh")) + (await _ub_titulado(doc, "certidao_casamento")),
        }
        secoes = [(titulo, conteudo.get(key)) for key, titulo in DOSSIE.ORDEM_DOSSIE_USUCAPIAO]
        return await asyncio.to_thread(DOSSIE.gerar_dossie_ordenado, doc, secoes, capa_pdf)

    # ── Retificação (e demais): ORDEM_DOSSIE padrão (Quadro + DRL + uploads)
    partes = {}
    for t in ("requerimento_cartorio", "requerimento_superintendencia", "memorial_descritivo", "cadeia_dominical"):
        partes[t] = assinadas.get(t) or await asyncio.to_thread(PDF.gerar_pdf, t, doc, tema, logo)
    if not assinadas.get("memorial_descritivo") and uploads.get("memorial_aprovado"):
        partes["memorial_descritivo"] = await _ub(doc, "memorial_aprovado")
    if tipo == "retificacao":
        if not (doc.get("retificacao_analise") or {}).get("cadastral_diffs"):
            doc = {**doc, "retificacao_analise": RET.analisar(doc)}
        partes["quadro_retificacao"] = await asyncio.to_thread(PDF.gerar_pdf, "quadro_retificacao", doc, tema, logo)
        drls = [await asyncio.to_thread(PDF.drl, doc, conf, tema, logo) for conf in PDF.confrontantes_para_drl(doc)]
        if drls:
            partes["drl"] = drls
    for secao, tipos in _DOSSIE_UPLOADS.items():
        bs = []
        for tp in tipos:
            bs += await _ub(doc, tp)
        if bs:
            partes[secao] = bs
    return await asyncio.to_thread(DOSSIE.gerar_dossie, doc, partes, capa_pdf)


# ──────────────────────────────────────────────────────────────────────────────
# Assinatura ICP do TÉCNICO (Memorial + Mapa) — reusa o módulo de assinatura
# ──────────────────────────────────────────────────────────────────────────────
_PECAS_ASSINAVEIS = {
    "memorial_descritivo": "Memorial Descritivo",
    "mapa": "Planta / Mapa Georreferenciado",
    "requerimento_cartorio": "Requerimento — Via Cartório",
    "requerimento_superintendencia": "Requerimento — Via Superintendência",
    "requerimento_usucapiao": "Requerimento de Usucapião",
    "art_trt": "ART / TRT",
}
# Peça "mapa" — o UPLOAD e o RÓTULO variam por serviço (cada módulo tem sua peça):
# usucapião = Planta georreferenciada; remembramento/desdobro/retificação = seu mapa.
_MAPA_UPLOADS_POR_SERVICO = {
    "usucapiao": ["planta_usucapiao", "mapa_remembramento", "mapa_atual"],
    "desdobro": ["mapa_desdobro", "mapa_atual"],
    "retificacao": ["mapa_retificado", "mapa_atual"],
    "remembramento": ["mapa_remembramento", "mapa_atual"],
    "desmembramento": ["mapa_remembramento", "mapa_atual"],
}
_MAPA_LABEL_POR_SERVICO = {
    "usucapiao": "Planta / Mapa Georreferenciado (área usucapienda)",
    "desdobro": "Mapa de Desdobro", "retificacao": "Mapa Retificado",
    "remembramento": "Mapa de Remembramento", "desmembramento": "Mapa de Desmembramento",
}
# Peças (não-mapa) que vêm de um UPLOAD (PDF/imagem). doc → tipo de upload.
_PECA_UPLOAD = {"art_trt": "art_trt"}


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
    await _injetar_logo(db, uid, doc)
    await _injetar_assinatura_tecnico(db, uid, doc)
    peca = body.doc
    if peca not in _PECAS_ASSINAVEIS:
        raise HTTPException(status_code=422, detail="Peça inválida para assinatura.")
    tema = body.tema or doc.get("tema") or "prime_i"
    servico = doc.get("tipo_servico") or "remembramento"
    if peca == "mapa":
        # cada serviço tem sua peça de mapa — tenta os uploads na ordem de prioridade
        tipos = _MAPA_UPLOADS_POR_SERVICO.get(servico, ["mapa_remembramento", "mapa_atual"])
        raw = None
        for tp in tipos:
            raw = await _bytes_upload(doc, tp)
            if raw:
                break
        if not raw:
            label = _MAPA_LABEL_POR_SERVICO.get(servico, "Mapa / Planta")
            raise HTTPException(status_code=422, detail=f"{label} não enviado (etapa Uploads).")
        if raw[:5] == b"%PDF-":
            pdf_bytes = raw
        else:
            from services.georef.generators.dossie import _img_para_pdf
            pdf_bytes = await asyncio.to_thread(_img_para_pdf, raw)
    elif peca in _PECA_UPLOAD:
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
    for nome, titulo in PROP.pecas_proprietario(doc):
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
    firma = await _firma_tecnico_bytes(db, uid)
    return {"documentos": documentos, "signatarios": PROP.signatarios_de(doc),
            "tecnico": {"tem_assinatura": bool(firma),
                        "nome": (doc.get("responsavel_tecnico") or {}).get("nome") or "Responsável Técnico"}}


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
    tecnico_pos = body.get("tecnico_pos") or {}      # {doc: [rects]} — opção A (firma do RT)
    if any(not s.get("telefone") for s in sig_in):
        raise HTTPException(status_code=422, detail="Informe o WhatsApp de todos os signatários.")
    docs_com_pos = {dn for mp in posicoes.values() for dn, r in (mp or {}).items() if r}
    docs_com_pos |= {dn for dn, r in tecnico_pos.items() if r}   # peça só com firma do RT também vai
    if not docs_com_pos:
        raise HTTPException(status_code=422, detail="Posicione ao menos uma assinatura.")
    # opção A: a firma gráfica do técnico já vai CARIMBADA nas peças antes do envio
    firma = await _firma_tecnico_bytes(db, uid)
    pecas = await _pecas_proprietario_bytes(doc, tema)
    documentos = []
    for p in pecas:
        if p["doc"] not in docs_com_pos:
            continue
        pbytes = p["bytes"]
        if firma and tecnico_pos.get(p["doc"]):
            from services.assinatura_cliente_carimbo import carimbar_traco_em_pagina
            for rect in tecnico_pos[p["doc"]]:
                try:
                    x, y = float(rect.get("x_pt", 0)), float(rect.get("y_pt", 0))
                    w, h = float(rect.get("larg_pt", 0)), float(rect.get("alt_pt", 0))
                    pbytes = await asyncio.to_thread(
                        carimbar_traco_em_pagina, pbytes, int(rect.get("pagina", 0)),
                        (x, y, x + w, y + h), firma, "")
                except Exception:  # noqa: BLE001
                    logger.warning("Geo Urbano: falha ao carimbar a firma do técnico.", exc_info=True)
        key = f"geo-urbano/{uid}/{pid}/assin-prop/{p['doc']}_base.pdf"
        await asyncio.to_thread(r2_storage.upload_bytes, pbytes, key, _PDF)
        try:
            from pypdf import PdfReader
            import io as _io
            paginas = len(PdfReader(_io.BytesIO(pbytes)).pages)
        except Exception:  # noqa: BLE001
            paginas = 0
        # RENDERIZA as páginas UMA vez aqui (no envio) e guarda — a página pública do
        # signatário deixa de rerenderizar a cada carregamento (evita ~75s de "Carregando…").
        try:
            from services.pdf_preview import renderizar_paginas
            paginas_render = await asyncio.to_thread(renderizar_paginas, pbytes, 110, 30)
        except Exception:  # noqa: BLE001
            paginas_render = []
        documentos.append({"doc": p["doc"], "titulo": p["titulo"], "pdf_key_base": key,
                           "paginas": paginas, "paginas_render": paginas_render})

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


@router.post("/projetos/{pid}/proprietario/reset")
async def prop_reset(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """ZERA as assinaturas já coletadas (mantém tokens e posições) e REENVIA os links —
    para todos reassinarem (ex.: usar a nova modalidade digitada). Não reposiciona."""
    s = await db.geo_urbano_assinatura_sessoes.find_one({"projeto_id": pid, "user_id": uid})
    if not s:
        raise HTTPException(status_code=404, detail="Nenhuma sessão de assinatura para resetar.")
    novos = [{**x, "status": "pendente", "assinado_em": None, "ip": None, "user_agent": None,
              "geo_lat": None, "geo_lng": None, "traco_b64": None, "tipo_assinatura": None,
              "cpf_assinante": None, "fonte_assinatura": None}
             for x in (s.get("signatarios") or [])]
    await db.geo_urbano_assinatura_sessoes.update_one(
        {"id": s["id"]},
        {"$set": {"signatarios": novos, "status": "aguardando", "pdf_keys_final": {},
                  "updated_at": _agora().isoformat()}})
    s["signatarios"] = novos
    proj = await _get(db, pid, uid)
    res = await _disparar_links_prop(db, uid, proj, s)
    return {"ok": True, "reset": len(novos), **res}


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
