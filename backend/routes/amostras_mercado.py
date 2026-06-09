# @module routes.amostras_mercado — Banco Global de Amostras de Mercado v2.
#
# Repositório de paradigmas (elementos comparativos) isolado por user_id. Alimentado:
#   1) Manualmente pelos modais Urbano/Rural (frontend).
#   2) Automaticamente pela sincronização dos PTAMs (market_samples -> amostras_mercado).
#
# Convenções respeitadas:
#   - DB via `from db import get_db` (injeção FastAPI: db=Depends(get_db)).
#   - Auth/assinatura via `get_active_subscriber` (mesmo middleware do resto do app).
#   - Isolamento multi-tenant: TODA query/insert/upsert inclui {"user_id": uid}.
#   - id = uuid str (igual a Ptam/Evaluation); NÃO ObjectId.
#   - Áreas em m²; R$/m² e R$/ha derivados em calcular_metricas().
from typing import Optional, List
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query

from db import get_db
from dependencies import get_active_subscriber
from models.common import _id as _new_id, _now

router = APIRouter(prefix="/amostras-mercado", tags=["Amostras de Mercado"])

M2_PER_HA = 10000.0
M2_PER_ALQ = 48400.0  # alqueire mineiro (4,84 ha)

_RURAL_PROPERTY_TYPES = {
    "rural", "fazenda", "sitio", "chacara", "terreno_rural", "gleba", "area_rural",
}

# Mapa property_type (PTAM) -> tipo_imovel canônico (amostra urbana).
_TIPO_URBANO_MAP = {
    "casa": "Casa",
    "apartamento": "Apartamento",
    "terreno": "Terreno",
    "comercial": "Sala Comercial",
    "sala_comercial": "Sala Comercial",
    "galpao": "Galpão",
    "industrial": "Galpão",
    "loja": "Loja",
}

# Mapa property_type (PTAM) -> tipo_imovel canônico (amostra rural).
_TIPO_RURAL_MAP = {
    "fazenda": "Fazenda",
    "sitio": "Sítio",
    "chacara": "Chácara Rural",
    "gleba": "Gleba",
    "terreno_rural": "Terra Nua",
    "area_rural": "Área de Preservação",
    "rural": "Fazenda",
}

# Mapa tipo_amostra do PTAM (market_samples) -> rótulo canônico.
_TIPO_AMOSTRA_MAP = {
    "oferta": "Oferta de Mercado",
    "oferta de mercado": "Oferta de Mercado",
    "consolidada": "Consolidada / Comercializada",
    "comercializada": "Consolidada / Comercializada",
    "transacao": "Consolidada / Comercializada",
    "aluguel": "Aluguel",
    "locacao": "Aluguel",
}


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def calcular_metricas(doc: dict) -> dict:
    """Calcula R$/m² (urbano) ou R$/ha + conversões de área (rural). Idempotente."""
    categoria = doc.get("categoria", "urbano")
    valor = _f(doc.get("valor_rs"))

    if categoria == "rural":
        area_m2 = _f(doc.get("area_m2"))
        if area_m2 > 0:
            doc["area_hectares"] = round(area_m2 / M2_PER_HA, 4)
            doc["area_alqueires_mineiros"] = round(area_m2 / M2_PER_ALQ, 4)
            doc["rs_ha_calculado"] = round(valor / (area_m2 / M2_PER_HA), 2) if valor else 0.0
    else:
        area = _f(doc.get("area_total_m2"))
        doc["rs_m2_calculado"] = round(valor / area, 2) if (area > 0 and valor) else 0.0

    return doc


def _assinatura_amostra(d: dict) -> str:
    """Assinatura de conteúdo para deduplicação. Duas amostras com a mesma assinatura
    são consideradas a MESMA amostra (independente da referência ou do PTAM de origem)."""
    cat = d.get("categoria", "urbano")
    if cat == "rural":
        area = d.get("area_m2")
        local = d.get("bairro_localidade") or d.get("denominacao") or ""
    else:
        area = d.get("area_total_m2")
        local = d.get("bairro") or ""
    return "|".join([
        cat,
        str(d.get("tipo_imovel") or "").strip().lower(),
        f"{_f(area):.2f}",
        f"{_f(d.get('valor_rs')):.2f}",
        str(d.get("municipio") or "").strip().lower(),
        str(local).strip().lower(),
        str(d.get("fonte") or "").strip().lower(),
        str(d.get("data_coleta") or "")[:10],
    ])


def serialize_amostra(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    for k in ("criado_em", "atualizado_em"):
        v = doc.get(k)
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    dc = doc.get("data_coleta")
    if isinstance(dc, (datetime, date)):
        doc["data_coleta"] = dc.isoformat()[:10]
    return doc


def _normalizar_entrada(payload: dict, uid: str) -> dict:
    """Sanitiza o payload recebido do form: categoria, números e metadados base."""
    doc = dict(payload or {})
    doc.pop("_id", None)
    doc["user_id"] = uid
    categoria = doc.get("categoria") or "urbano"
    doc["categoria"] = "rural" if categoria == "rural" else "urbano"
    doc.setdefault("municipio", "Açailândia")
    doc.setdefault("uf", "MA")
    doc.setdefault("ativo", True)
    doc.setdefault("origem", doc.get("origem") or "manual")
    return doc


# ─── CRUD ─────────────────────────────────────────────────────────────────────
@router.post("", status_code=201)
@router.post("/", status_code=201)
async def criar_amostra(payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Cria nova amostra de mercado (urbana ou rural)."""
    doc = _normalizar_entrada(payload, uid)
    if not str(doc.get("referencia") or "").strip():
        raise HTTPException(400, "Referência é obrigatória")
    doc = calcular_metricas(doc)
    doc["assinatura"] = _assinatura_amostra(doc)

    # Regra anti-duplicata: se já existe uma amostra com o mesmo conteúdo, devolve a
    # existente em vez de criar outra (evita lixo no banco).
    existente = await db.amostras_mercado.find_one(
        {"user_id": uid, "assinatura": doc["assinatura"], "ativo": True}
    )
    if existente:
        return serialize_amostra(existente)

    doc["id"] = _new_id()
    doc["criado_em"] = _now()
    doc["atualizado_em"] = _now()
    await db.amostras_mercado.insert_one(dict(doc))
    return serialize_amostra(doc)


@router.get("")
@router.get("/")
async def listar_amostras(
    categoria: Optional[str] = Query(None, enum=["urbano", "rural"]),
    tipo_imovel: Optional[str] = Query(None),
    municipio: Optional[str] = Query(None),
    bairro: Optional[str] = Query(None),
    tipo_amostra: Optional[str] = Query(None),
    ptam_id: Optional[str] = Query(None),
    data_de: Optional[str] = Query(None),
    data_ate: Optional[str] = Query(None),
    ativo: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    order_by: str = Query("data_coleta"),
    order_dir: int = Query(-1, enum=[-1, 1]),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lista amostras do usuário com filtros."""
    filtro: dict = {"user_id": uid, "ativo": ativo}
    if categoria:
        filtro["categoria"] = categoria
    if tipo_imovel:
        filtro["tipo_imovel"] = tipo_imovel
    if tipo_amostra:
        filtro["tipo_amostra"] = tipo_amostra
    if municipio:
        filtro["municipio"] = {"$regex": municipio, "$options": "i"}
    if bairro:
        filtro["$or"] = [
            {"bairro": {"$regex": bairro, "$options": "i"}},
            {"bairro_localidade": {"$regex": bairro, "$options": "i"}},
        ]
    if ptam_id:
        filtro["ptam_origem_id"] = ptam_id
    if data_de or data_ate:
        rng: dict = {}
        if data_de:
            rng["$gte"] = data_de
        if data_ate:
            rng["$lte"] = data_ate
        filtro["data_coleta"] = rng

    allowed_order = {"data_coleta", "criado_em", "valor_rs", "rs_m2_calculado", "rs_ha_calculado", "referencia"}
    if order_by not in allowed_order:
        order_by = "data_coleta"

    cursor = db.amostras_mercado.find(filtro).sort(order_by, order_dir).skip(skip).limit(limit)
    amostras = await cursor.to_list(length=limit)
    total = await db.amostras_mercado.count_documents(filtro)

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "amostras": [serialize_amostra(a) for a in amostras],
    }


@router.get("/estatisticas")
async def estatisticas_amostras(
    categoria: Optional[str] = Query(None, enum=["urbano", "rural"]),
    municipio: Optional[str] = Query(None),
    tipo_imovel: Optional[str] = Query(None),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Preço médio, mínimo e máximo do R$/m² (urbano) ou R$/ha (rural)."""
    filtro: dict = {"user_id": uid, "ativo": True}
    if categoria:
        filtro["categoria"] = categoria
    if municipio:
        filtro["municipio"] = {"$regex": municipio, "$options": "i"}
    if tipo_imovel:
        filtro["tipo_imovel"] = tipo_imovel

    is_rural = categoria == "rural"
    campo_preco = "rs_ha_calculado" if is_rural else "rs_m2_calculado"
    unidade = "R$/ha" if is_rural else "R$/m²"

    pipeline = [
        {"$match": {**filtro, campo_preco: {"$gt": 0}}},
        {"$group": {
            "_id": None,
            "media": {"$avg": f"${campo_preco}"},
            "minimo": {"$min": f"${campo_preco}"},
            "maximo": {"$max": f"${campo_preco}"},
            "total": {"$sum": 1},
        }},
    ]
    resultado = await db.amostras_mercado.aggregate(pipeline).to_list(1)
    if not resultado:
        return {"media": 0, "minimo": 0, "maximo": 0, "total": 0, "unidade": unidade}

    r = resultado[0]
    return {
        "media": round(_f(r.get("media")), 2),
        "minimo": round(_f(r.get("minimo")), 2),
        "maximo": round(_f(r.get("maximo")), 2),
        "total": r.get("total", 0),
        "unidade": unidade,
    }


@router.get("/meta/proxima-referencia")
async def proxima_referencia(
    categoria: str = Query("urbano", enum=["urbano", "rural"]),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Próxima referência disponível do usuário: AM-001... (urbano) / RM-001... (rural)."""
    prefixo = "RM" if categoria == "rural" else "AM"
    ultima = await db.amostras_mercado.find_one(
        {"user_id": uid, "categoria": categoria, "referencia": {"$regex": f"^{prefixo}-"}},
        sort=[("referencia", -1)],
    )
    numero = 1
    if ultima:
        try:
            numero = int(str(ultima.get("referencia", f"{prefixo}-000")).split("-")[1]) + 1
        except (IndexError, ValueError):
            numero = 1
    return {"referencia": f"{prefixo}-{numero:03d}"}


@router.get("/{amostra_id}")
async def obter_amostra(amostra_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await db.amostras_mercado.find_one({"id": amostra_id, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Amostra não encontrada")
    return serialize_amostra(doc)


@router.put("/{amostra_id}")
async def atualizar_amostra(
    amostra_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)
):
    existente = await db.amostras_mercado.find_one({"id": amostra_id, "user_id": uid})
    if not existente:
        raise HTTPException(404, "Amostra não encontrada")

    doc = _normalizar_entrada(payload, uid)
    doc = calcular_metricas(doc)
    doc["atualizado_em"] = _now()
    # Campos imutáveis na atualização.
    for k in ("id", "_id", "criado_em", "ptam_origem_id", "origem"):
        doc.pop(k, None)

    await db.amostras_mercado.update_one({"id": amostra_id, "user_id": uid}, {"$set": doc})
    novo = await db.amostras_mercado.find_one({"id": amostra_id, "user_id": uid})
    return serialize_amostra(novo)


@router.delete("/{amostra_id}")
async def deletar_amostra(amostra_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Soft delete (ativo=False)."""
    result = await db.amostras_mercado.update_one(
        {"id": amostra_id, "user_id": uid},
        {"$set": {"ativo": False, "atualizado_em": _now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Amostra não encontrada")
    return {"ok": True, "message": "Amostra removida"}


# ─── SINCRONIZAÇÃO COM PTAM ───────────────────────────────────────────────────
def _is_rural_ptam(ptam: dict) -> bool:
    return str((ptam or {}).get("property_type") or "").strip().lower() in _RURAL_PROPERTY_TYPES


def _mapear_sample(sample: dict, ptam: dict, categoria: str, indice: int) -> dict:
    """Mapeia uma entrada de ptam.market_samples para o documento canônico da amostra global.

    Os nomes em market_samples diferem do banco global (address/area/value/value_per_sqm/source...
    -> endereco/area_*/valor_rs/rs_*/fonte...). Esta função normaliza esse mapeamento.
    """
    s = dict(sample or {})
    prefixo = "RM" if categoria == "rural" else "AM"
    referencia = str(s.get("referencia") or s.get("ref") or "").strip() or f"{prefixo}-{indice + 1:03d}"

    tipo_amostra = _TIPO_AMOSTRA_MAP.get(str(s.get("tipo_amostra") or "oferta").strip().lower(), "Oferta de Mercado")
    municipio = s.get("municipio") or ptam.get("property_city") or ptam.get("municipio_incra") or "Açailândia"
    uf = s.get("uf") or ptam.get("property_state") or ptam.get("uf_incra") or "MA"
    property_type = str(ptam.get("property_type") or "").strip().lower()

    doc: dict = {
        "referencia": referencia,
        "categoria": categoria,
        "municipio": municipio,
        "uf": uf,
        "valor_rs": _f(s.get("value") or s.get("valor_rs") or s.get("valor")),
        "tipo_amostra": tipo_amostra,
        "fonte": s.get("source") or s.get("fonte") or "",
        "data_coleta": s.get("collection_date") or s.get("data_coleta") or "",
        "telefone_fonte": s.get("contact_phone") or s.get("telefone_fonte") or "",
        "foto_url": s.get("foto") or s.get("foto_url") or s.get("thumbnail") or None,
        "link_anuncio": s.get("source_url") or s.get("link_anuncio") or None,
    }

    if categoria == "rural":
        doc["tipo_imovel"] = _TIPO_RURAL_MAP.get(property_type, "Fazenda")
        doc["area_m2"] = _f(s.get("area") or s.get("area_m2"))
        doc["denominacao"] = s.get("denominacao") or ptam.get("denominacao") or None
        doc["endereco_logradouro"] = s.get("address") or s.get("endereco_logradouro") or None
        doc["bairro_localidade"] = s.get("neighborhood") or s.get("bairro_localidade") or ""
        doc["topografia"] = s.get("topografia") or None
        doc["solo"] = s.get("solo") or None
        doc["recursos_hidricos"] = s.get("recursos_hidricos") or None
        doc["vegetacao"] = s.get("vegetacao") or None
        doc["atividade_principal"] = s.get("atividade_principal") or s.get("atividade") or None
        doc["lotacao_ua_ha"] = _f(s.get("lotacao_ua_ha")) or None
        doc["benfeitorias"] = s.get("benfeitorias") or None
        doc["sede_casa"] = s.get("sede_casa") or s.get("sede") or None
    else:
        doc["tipo_imovel"] = _TIPO_URBANO_MAP.get(property_type, "Casa")
        doc["area_total_m2"] = _f(s.get("area") or s.get("area_total_m2"))
        doc["area_construida_m2"] = _f(s.get("area_construida_m2")) or None
        doc["area_terreno_m2"] = _f(s.get("area_terreno_m2")) or None
        doc["endereco"] = s.get("address") or s.get("endereco") or None
        doc["bairro"] = s.get("neighborhood") or s.get("bairro") or ""
        doc["idade_anos"] = int(_f(s.get("idade_anos"))) or None
        rps = _f(s.get("value_per_sqm"))
        if rps:
            doc["rs_m2_calculado"] = round(rps, 2)

    return calcular_metricas(doc)


async def sincronizar_amostras_ptam(ptam_id: str, uid: str, db) -> dict:
    """Lê ptam_documents.{ptam_id}.market_samples e faz upsert no banco global.

    Idempotente: upsert por (user_id, ptam_origem_id, referencia). Best-effort —
    nunca deve derrubar o save do PTAM (o chamador encapsula em try/except).
    """
    ptam = await db.ptam_documents.find_one({"id": ptam_id, "user_id": uid})
    if not ptam:
        return {"sincronizadas": 0, "message": "PTAM não encontrado"}

    samples = ptam.get("market_samples") or []
    if not samples:
        return {"sincronizadas": 0, "message": "Nenhuma amostra no PTAM"}

    categoria = "rural" if _is_rural_ptam(ptam) else "urbano"
    numero_ptam = ptam.get("numero_ptam") or ptam.get("number") or ""

    sincronizadas = 0
    erros: List[dict] = []
    for idx, sample in enumerate(samples):
        try:
            # Ignora amostras vazias (sem valor e sem área).
            if not _f((sample or {}).get("value")) and not _f((sample or {}).get("area")):
                continue
            doc = _mapear_sample(sample, ptam, categoria, idx)
            doc["user_id"] = uid
            doc["ativo"] = True
            doc["atualizado_em"] = _now()
            doc["assinatura"] = _assinatura_amostra(doc)

            # Dedup por CONTEÚDO: a mesma amostra reaproveitada em vários PTAMs vira UM
            # único registro no banco global. A origem (PTAM/ref) fica a do 1º que gravou.
            await db.amostras_mercado.update_one(
                {"user_id": uid, "assinatura": doc["assinatura"]},
                {
                    "$set": doc,
                    "$setOnInsert": {
                        "id": _new_id(),
                        "criado_em": _now(),
                        "origem": "ptam",
                        "ptam_origem_id": ptam_id,
                        "ptam_origem_numero": numero_ptam,
                    },
                },
                upsert=True,
            )
            sincronizadas += 1
        except Exception as e:  # noqa: BLE001 — best-effort, registra mas não interrompe
            erros.append({"referencia": (sample or {}).get("referencia"), "erro": str(e)})

    return {
        "sincronizadas": sincronizadas,
        "erros": erros,
        "ptam_id": ptam_id,
        "categoria": categoria,
    }


@router.post("/sync/ptam/{ptam_id}")
async def sync_ptam_endpoint(ptam_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Dispara manualmente a sincronização das amostras de um PTAM para o banco global."""
    return await sincronizar_amostras_ptam(ptam_id, uid, db)


@router.post("/dedupe")
async def remover_duplicadas(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Remove amostras duplicadas do usuário (mesmo conteúdo), mantendo 1 de cada.

    Critério de preferência ao manter: amostra MANUAL antes de PTAM, e a mais antiga.
    Remove fisicamente as demais para liberar espaço. Idempotente.
    """
    docs = await db.amostras_mercado.find({"user_id": uid}).to_list(100000)

    def _prio(d):
        return (0 if d.get("origem") == "manual" else 1, str(d.get("criado_em") or ""))

    vistos: dict = {}
    remover_ids: list = []
    for d in sorted(docs, key=_prio):
        sig = d.get("assinatura") or _assinatura_amostra(d)
        if sig in vistos:
            if d.get("id"):
                remover_ids.append(d["id"])
        else:
            vistos[sig] = d.get("id")
            # Backfill da assinatura nos registros antigos que não tinham.
            if not d.get("assinatura") and d.get("id"):
                await db.amostras_mercado.update_one({"id": d["id"], "user_id": uid}, {"$set": {"assinatura": sig}})

    if remover_ids:
        await db.amostras_mercado.delete_many({"user_id": uid, "id": {"$in": remover_ids}})

    return {"removidas": len(remover_ids), "mantidas": len(vistos)}
