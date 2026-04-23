# @module routes.search — Busca global em todas as colecoes do usuario
import asyncio
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from db import get_db
from dependencies import get_active_subscriber, serialize_doc

router = APIRouter(prefix="/search", tags=["search"])


def _fmt_valor(doc: dict, *campos) -> Optional[str]:
    """Tenta formatar um valor monetario de varios campos possiveis."""
    for campo in campos:
        v = doc.get(campo)
        if v is not None:
            try:
                return f"R$ {float(v):_.2f}".replace(".", ",").replace("_", ".")
            except (TypeError, ValueError):
                return str(v)
    return None


def _fmt_updated(doc: dict) -> Optional[str]:
    v = doc.get("updated_at") or doc.get("created_at")
    if not v:
        return None
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    return str(v)[:10]


def _highlight_noop(titulo: str) -> str:
    return titulo


async def _buscar_ptam(db, uid: str, regex) -> list:
    campos = ["numero_ptam", "solicitante_nome", "property_address",
              "property_neighborhood", "property_city", "property_owner"]
    query = {"user_id": uid, "$or": [{c: regex} for c in campos]}
    cursor = db.ptam_documents.find(query).sort("updated_at", -1).limit(5)
    results = []
    async for doc in cursor:
        doc = serialize_doc(doc)
        num = doc.get("numero_ptam", "")
        sol = doc.get("solicitante_nome", "") or doc.get("property_owner", "")
        titulo = f"PTAM {num} — {sol}".strip(" — ")
        addr = doc.get("property_address", "")
        city = doc.get("property_city", "")
        subtitulo = f"{addr} — {city}".strip(" — ") if (addr or city) else ""
        results.append({
            "id": doc.get("id", ""),
            "tipo": "ptam",
            "titulo": titulo,
            "subtitulo": subtitulo,
            "valor": _fmt_valor(doc, "valor_avaliacao", "valor_total"),
            "status": doc.get("status"),
            "updated_at": _fmt_updated(doc),
            "rota": f"/dashboard/ptam/{doc.get('id', '')}",
        })
    return results


async def _buscar_tvi(db, uid: str, regex) -> list:
    campos = ["numero_tvi", "cliente_nome", "imovel_endereco", "imovel_cidade", "modelo_nome"]
    query = {"user_id": uid, "$or": [{c: regex} for c in campos]}
    cursor = db.vistorias.find(query).sort("updated_at", -1).limit(5)
    results = []
    async for doc in cursor:
        doc = serialize_doc(doc)
        num = doc.get("numero_tvi", "")
        cliente = doc.get("cliente_nome", "")
        titulo = f"TVI {num} — {cliente}".strip(" — ")
        addr = doc.get("imovel_endereco", "")
        city = doc.get("imovel_cidade", "")
        subtitulo = f"{addr} — {city}".strip(" — ") if (addr or city) else ""
        results.append({
            "id": doc.get("id", ""),
            "tipo": "tvi",
            "titulo": titulo,
            "subtitulo": subtitulo,
            "valor": None,
            "status": doc.get("status"),
            "updated_at": _fmt_updated(doc),
            "rota": f"/dashboard/tvi/{doc.get('id', '')}",
        })
    return results


async def _buscar_garantias(db, uid: str, regex) -> list:
    campos = ["numero", "mutuario_nome", "imovel_endereco", "instituicao_financeira"]
    query = {"user_id": uid, "$or": [{c: regex} for c in campos]}
    cursor = db.garantias.find(query).sort("updated_at", -1).limit(5)
    results = []
    async for doc in cursor:
        doc = serialize_doc(doc)
        num = doc.get("numero", "")
        mutuario = doc.get("mutuario_nome", "")
        titulo = f"Garantia {num} — {mutuario}".strip(" — ")
        addr = doc.get("imovel_endereco", "")
        inst = doc.get("instituicao_financeira", "")
        subtitulo = f"{addr} — {inst}".strip(" — ") if (addr or inst) else ""
        results.append({
            "id": doc.get("id", ""),
            "tipo": "garantia",
            "titulo": titulo,
            "subtitulo": subtitulo,
            "valor": _fmt_valor(doc, "valor_avaliacao", "valor_total"),
            "status": doc.get("status"),
            "updated_at": _fmt_updated(doc),
            "rota": f"/dashboard/garantias/{doc.get('id', '')}",
        })
    return results


async def _buscar_semoventes(db, uid: str, regex) -> list:
    campos = ["numero_laudo", "devedor_nome", "propriedade_nome", "propriedade_municipio"]
    query = {"user_id": uid, "$or": [{c: regex} for c in campos]}
    cursor = db.semoventes.find(query).sort("updated_at", -1).limit(5)
    results = []
    async for doc in cursor:
        doc = serialize_doc(doc)
        num = doc.get("numero_laudo", "")
        devedor = doc.get("devedor_nome", "")
        titulo = f"Semovente {num} — {devedor}".strip(" — ")
        prop = doc.get("propriedade_nome", "")
        mun = doc.get("propriedade_municipio", "")
        subtitulo = f"{prop} — {mun}".strip(" — ") if (prop or mun) else ""
        results.append({
            "id": doc.get("id", ""),
            "tipo": "semovente",
            "titulo": titulo,
            "subtitulo": subtitulo,
            "valor": _fmt_valor(doc, "valor_total", "valor_avaliacao"),
            "status": doc.get("status"),
            "updated_at": _fmt_updated(doc),
            "rota": f"/dashboard/semoventes/{doc.get('id', '')}",
        })
    return results


async def _buscar_locacao(db, uid: str, regex) -> list:
    campos = ["numero_locacao", "solicitante_nome", "imovel_endereco", "imovel_cidade"]
    query = {"user_id": uid, "$or": [{c: regex} for c in campos]}
    cursor = db.locacao_documents.find(query).sort("updated_at", -1).limit(5)
    results = []
    async for doc in cursor:
        doc = serialize_doc(doc)
        num = doc.get("numero_locacao", "")
        sol = doc.get("solicitante_nome", "")
        titulo = f"Locacao {num} — {sol}".strip(" — ")
        addr = doc.get("imovel_endereco", "")
        city = doc.get("imovel_cidade", "")
        subtitulo = f"{addr} — {city}".strip(" — ") if (addr or city) else ""
        results.append({
            "id": doc.get("id", ""),
            "tipo": "locacao",
            "titulo": titulo,
            "subtitulo": subtitulo,
            "valor": _fmt_valor(doc, "valor_locacao", "valor_total"),
            "status": doc.get("status"),
            "updated_at": _fmt_updated(doc),
            "rota": f"/dashboard/locacao/{doc.get('id', '')}",
        })
    return results


async def _buscar_clients(db, uid: str, regex) -> list:
    campos = ["nome", "cpf_cnpj", "email", "telefone"]
    query = {"user_id": uid, "$or": [{c: regex} for c in campos]}
    cursor = db.clients.find(query).limit(5)
    results = []
    async for doc in cursor:
        doc = serialize_doc(doc)
        nome = doc.get("nome", "")
        cpf = doc.get("cpf_cnpj", "")
        titulo = nome
        subtitulo = f"{cpf} — {doc.get('email', '')}".strip(" — ") if cpf or doc.get("email") else ""
        results.append({
            "id": doc.get("id", ""),
            "tipo": "cliente",
            "titulo": titulo,
            "subtitulo": subtitulo,
            "valor": None,
            "status": None,
            "updated_at": _fmt_updated(doc),
            "rota": "/dashboard/clientes",
        })
    return results


async def _buscar_properties(db, uid: str, regex) -> list:
    campos = ["address", "neighborhood", "city", "owner"]
    query = {"user_id": uid, "$or": [{c: regex} for c in campos]}
    cursor = db.properties.find(query).limit(5)
    results = []
    async for doc in cursor:
        doc = serialize_doc(doc)
        addr = doc.get("address", "")
        owner = doc.get("owner", "")
        titulo = addr if addr else owner
        city = doc.get("city", "")
        neighborhood = doc.get("neighborhood", "")
        subtitulo = f"{neighborhood} — {city}".strip(" — ") if (neighborhood or city) else ""
        results.append({
            "id": doc.get("id", ""),
            "tipo": "imovel",
            "titulo": titulo,
            "subtitulo": subtitulo,
            "valor": None,
            "status": None,
            "updated_at": _fmt_updated(doc),
            "rota": "/dashboard/imoveis",
        })
    return results


@router.get("")
async def global_search(
    q: str = Query(default="", min_length=0),
    limit: int = Query(default=20, ge=1, le=100),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Busca global em todas as colecoes do usuario. Minimo 2 caracteres."""
    if len(q.strip()) < 2:
        return {"results": []}

    termo = q.strip()
    regex = {"$regex": re.escape(termo), "$options": "i"}

    (
        ptams, tvis, garantias, semoventes, locacoes, clients, properties
    ) = await asyncio.gather(
        _buscar_ptam(db, uid, regex),
        _buscar_tvi(db, uid, regex),
        _buscar_garantias(db, uid, regex),
        _buscar_semoventes(db, uid, regex),
        _buscar_locacao(db, uid, regex),
        _buscar_clients(db, uid, regex),
        _buscar_properties(db, uid, regex),
    )

    # Clientes e imoveis primeiro, depois laudos por updated_at desc
    results = clients + properties + ptams + tvis + garantias + semoventes + locacoes

    # Limitar ao total maximo
    results = results[:limit]

    return {"results": results}
