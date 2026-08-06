# @module services.novidades — Central de Novidades: pendentes, visualizações, admin, seed.
from __future__ import annotations

import uuid
from datetime import datetime

C_NOV = "novidades"
C_VIS = "novidades_visualizacoes"

_CAMPOS = ("slug", "versao", "titulo", "resumo", "conteudo_md", "tag", "imagem_url",
           "cta_label", "cta_rota", "bloqueante", "expira_em", "publico_alvo")
_LISTA = ("id", "slug", "versao", "titulo", "resumo", "tag", "imagem_url",
          "cta_label", "cta_rota", "bloqueante", "publicada_em")


def _now() -> datetime:
    return datetime.utcnow()


def _full(n: dict) -> dict:
    if not n:
        return n
    return {k: v for k, v in n.items() if k != "_id"}


def _slim(n: dict) -> dict:
    """Projeção enxuta p/ o sino/histórico (SEM conteudo_md)."""
    return {k: n.get(k) for k in _LISTA}


def _publico_ok(n: dict, user_created) -> bool:
    alvo = n.get("publico_alvo", "todos")
    if alvo == "todos":
        return True
    pub = n.get("publicada_em")
    if not pub or not user_created:
        return True  # sem base de comparação → mostra
    novo = user_created > pub
    return novo if alvo == "novos" else (not novo)


async def _user_created(db, user_id):
    u = await db.users.find_one({"id": user_id})
    return (u or {}).get("created_at")


# ── Consumo (usuário) ─────────────────────────────────────────────────────────
async def listar_pendentes(db, user_id) -> list:
    """Publicadas, não expiradas, público-alvo compatível e NÃO dispensadas."""
    created = await _user_created(db, user_id)
    agora = _now()
    novidades = await db[C_NOV].find({"publicada": True}).sort("publicada_em", -1).to_list(length=100)
    vis = await db[C_VIS].find({"user_id": user_id}).to_list(length=1000)
    dispensadas = {v["novidade_id"] for v in vis if v.get("dispensado_em")}
    out = []
    for n in novidades:
        if n["id"] in dispensadas:
            continue
        if n.get("expira_em") and n["expira_em"] < agora:
            continue
        if not _publico_ok(n, created):
            continue
        out.append(_full(n))
    return out


async def listar_historico(db, user_id) -> list:
    created = await _user_created(db, user_id)
    novidades = await db[C_NOV].find({"publicada": True}).sort("publicada_em", -1).to_list(length=200)
    vis = {v["novidade_id"]: v for v in await db[C_VIS].find({"user_id": user_id}).to_list(length=1000)}
    out = []
    for n in novidades:
        if not _publico_ok(n, created):
            continue
        d = _full(n)          # timeline (/novidades) expande o conteudo_md completo
        v = vis.get(n["id"])
        d["lida"] = bool(v and (v.get("visto_em") or v.get("dispensado_em")))
        d["dispensada"] = bool(v and v.get("dispensado_em"))
        out.append(d)
    return out


async def _upsert_vis(db, user_id, novidade_id, updates: dict) -> None:
    await db[C_VIS].update_one(
        {"user_id": user_id, "novidade_id": novidade_id},
        {"$set": updates,
         "$setOnInsert": {"id": str(uuid.uuid4()), "user_id": user_id, "novidade_id": novidade_id}},
        upsert=True,
    )


async def marcar_visualizada(db, user_id, novidade_id):
    await _upsert_vis(db, user_id, novidade_id, {"visto_em": _now()})


async def dispensar(db, user_id, novidade_id):
    await _upsert_vis(db, user_id, novidade_id, {"dispensado_em": _now()})


async def registrar_cta(db, user_id, novidade_id):
    await _upsert_vis(db, user_id, novidade_id, {"cta_clicado_em": _now()})


# ── Admin ─────────────────────────────────────────────────────────────────────
async def criar(db, data: dict) -> dict:
    doc = {c: data.get(c) for c in _CAMPOS}
    if not str(doc.get("slug") or "").strip():
        raise ValueError("slug obrigatório")
    if await db[C_NOV].find_one({"slug": doc["slug"]}):
        raise ValueError(f"slug já existe: {doc['slug']}")
    doc.update({"id": str(uuid.uuid4()), "publicada": False, "publicada_em": None,
                "created_at": _now(), "updated_at": _now()})
    await db[C_NOV].insert_one(doc)
    return _full(doc)


async def editar(db, novidade_id, data: dict) -> dict:
    upd = {c: data[c] for c in _CAMPOS if c in data and data[c] is not None}
    upd["updated_at"] = _now()
    await db[C_NOV].update_one({"id": novidade_id}, {"$set": upd})
    return _full(await db[C_NOV].find_one({"id": novidade_id}))


async def publicar(db, novidade_id) -> dict:
    await db[C_NOV].update_one({"id": novidade_id},
                               {"$set": {"publicada": True, "publicada_em": _now(), "updated_at": _now()}})
    return _full(await db[C_NOV].find_one({"id": novidade_id}))


async def listar_admin(db) -> list:
    return [_full(n) for n in await db[C_NOV].find({}).sort("created_at", -1).to_list(length=300)]


async def metricas(db, novidade_id) -> dict:
    vis = await db[C_VIS].find({"novidade_id": novidade_id}).to_list(length=100000)
    total = await db.users.count_documents({})
    return {
        "destinatarios": total,
        "vistos": sum(1 for v in vis if v.get("visto_em")),
        "dispensados": sum(1 for v in vis if v.get("dispensado_em")),
        "cta_clicados": sum(1 for v in vis if v.get("cta_clicado_em")),
    }


# ── Seed do 1º release (BYOK) — publicada=False; publicar depois pelo painel ────
SEED_BYOK = {
    "slug": "assinatura-digital-byok",
    "versao": "1.12.0",
    "titulo": "Agora você assina com a sua própria plataforma de assinatura digital",
    "resumo": "Conecte sua conta D4Sign, Clicksign ou Autentique e envie documentos para assinatura sem sair do AvalieImob.",
    "tag": "novidade",
    "bloqueante": True,
    "publico_alvo": "todos",
    "cta_label": "Configurar agora",
    "cta_rota": "/dashboard/assinatura-digital",
    "conteudo_md": (
        "### O que mudou\n\n"
        "Você já pode enviar seus PTAMs, contratos e demais documentos direto para assinatura "
        "eletrônica, usando a **sua própria conta** nas plataformas que já utiliza:\n\n"
        "- **D4Sign**\n- **Clicksign**\n- **Autentique**\n\n"
        "### Como funciona\n\n"
        "1. Vá em **Configurações → Assinatura Digital**.\n"
        "2. Escolha a plataforma, informe suas credenciais de API e clique em **Testar conexão**.\n"
        "3. Pronto: nos seus documentos aparece o botão **Enviar para assinatura**.\n"
        "4. Acompanhe quem já assinou na nova aba **Assinaturas** e baixe o arquivo final assinado.\n\n"
        "### Importante\n\n"
        "As assinaturas são processadas na **sua conta** da plataforma escolhida e consomem os "
        "créditos do plano que você já contrata com ela. O AvalieImob **não cobra nada por documento "
        "assinado** — a integração está inclusa no seu plano."
    ),
}


async def seed_inicial(db) -> None:
    """Semeia as novidades iniciais (idempotente por slug). Nasce publicada=False."""
    for s in (SEED_BYOK,):
        if not await db[C_NOV].find_one({"slug": s["slug"]}):
            await criar(db, s)
