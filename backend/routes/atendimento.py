# @module routes.atendimento — Robô de atendimento do site + painel admin.
# NÃO usar `from __future__ import annotations` aqui: com o wrapper do slowapi o
# FastAPI passaria a tratar o body Pydantic como query param (ver v1.4.980).
"""Visitante sem login conversa com a Roma_IA no site; o robô explica a
plataforma e os serviços, qualifica o lead (curioso → interessado → qualificado
→ convertido) e encaminha ao dono pelo WhatsApp/e-mail quando ele quer fechar.

Coleção `atendimento_conversas` (1 documento por sessão do navegador).
"""
import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from db import get_db
from dependencies import get_admin_user
from services.atendimento import conhecimento as KB
from services.atendimento import qualificacao as Q
from services.ratelimit import pub_limiter, real_ip

logger = logging.getLogger("romatec")

router = APIRouter(prefix="/atendimento", tags=["Atendimento · Robô do site"])
admin_router = APIRouter(prefix="/admin/atendimento", tags=["Admin · Robô de atendimento"],
                         dependencies=[Depends(get_admin_user)])

COL = "atendimento_conversas"
_SESSAO_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
MAX_MSGS_CLIENTE = 40
MAX_HISTORICO_IA = 14
SAUDACAO = (
    "Olá! 👋 Sou a Roma_IA, atendente do AvalieImob. Posso explicar PTAM e laudos, perícia, "
    "georreferenciamento, usucapião, Arquivo ONR, contratos com assinatura pelo WhatsApp e os planos. "
    "Você é profissional da área ou precisa de um serviço?"
)


def _agora():
    return datetime.now(timezone.utc)


def _valida_sessao(sid: str) -> str:
    if not _SESSAO_RE.match(sid or ""):
        raise HTTPException(422, "Sessão inválida.")
    return sid


def _iso(v):
    return v.isoformat() if isinstance(v, datetime) else v


# ── Modelos ──────────────────────────────────────────────────────────────────
class MensagemIn(BaseModel):
    sessao_id: str
    mensagem: str = Field(..., min_length=1, max_length=800)
    pagina: Optional[str] = Field(None, max_length=300)
    referrer: Optional[str] = Field(None, max_length=500)
    utm_source: Optional[str] = Field(None, max_length=80)
    utm_medium: Optional[str] = Field(None, max_length=80)
    utm_campaign: Optional[str] = Field(None, max_length=120)


class ContatoIn(BaseModel):
    sessao_id: str
    nome: str = Field(..., min_length=2, max_length=120)
    whatsapp: str = Field(..., min_length=8, max_length=30)
    email: Optional[str] = Field(None, max_length=160)
    consentimento: bool = False
    website: Optional[str] = None  # honeypot


class EventoIn(BaseModel):
    sessao_id: str
    evento: str = Field(..., max_length=40)


_EVENTOS = {"clique_cadastro": "cadastro", "clique_planos": "planos",
            "clique_whatsapp": "whatsapp", "aberto": "aberto"}


# ── Conversa ─────────────────────────────────────────────────────────────────
async def _obter_ou_criar(db, sid: str, request: Request, origem: Optional[dict] = None) -> dict:
    doc = await db[COL].find_one({"id": sid})
    if doc:
        return doc
    agora = _agora()
    ip = real_ip(request)
    doc = {
        "id": sid, "criado_em": agora, "atualizado_em": agora,
        "mensagens": [{"role": "assistant", "content": SAUDACAO, "ts": agora}],
        "n_msgs_cliente": 0, "estagio": "curioso", "perfil": "indefinido", "assuntos": [],
        "nome": None, "whatsapp": None, "email": None, "pediu_humano": False,
        "notificado_em": None, "cliques": {}, "status_admin": "novo", "nota": "",
        "origem": {k: v for k, v in (origem or {}).items() if v},
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
        "user_agent": (request.headers.get("user-agent") or "")[:200],
    }
    try:
        await db[COL].insert_one(dict(doc))
    except Exception:  # noqa: BLE001 — corrida entre 2 requisições: lê a que venceu
        doc = await db[COL].find_one({"id": sid}) or doc
    return doc


async def _responder_ia(conversa: dict) -> tuple:
    """Chama a cascata de IA (Groq → Gemini → Claude → OpenAI) com a base de conhecimento."""
    from routes.ai import _roma_ia_cascata
    historico = [m for m in conversa.get("mensagens", []) if m.get("role") in ("user", "assistant")]
    msgs = [{"role": "system", "content": KB.system_prompt()}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in historico[-MAX_HISTORICO_IA:]]
    contexto = (f"[Contexto interno: estágio atual={conversa.get('estagio')}, perfil={conversa.get('perfil')}, "
                f"contato já informado={'sim' if (conversa.get('whatsapp') or conversa.get('email')) else 'não'}]")
    msgs.insert(1, {"role": "system", "content": contexto})
    reply, provedor = await _roma_ia_cascata(msgs, max_tokens=700, origem="atendimento_site")
    return reply, provedor


# ── Encaminhamento ao dono ───────────────────────────────────────────────────
PERFIL_TXT = {"profissional": "Profissional (quer usar a plataforma)",
              "cliente_servico": "Cliente (quer o serviço feito)", "indefinido": "Não identificado"}


def montar_aviso(c: dict) -> str:
    ultimas = [m["content"] for m in c.get("mensagens", []) if m.get("role") == "user"][-4:]
    assuntos = ", ".join(Q.ROTULO_ASSUNTO.get(a, a) for a in c.get("assuntos") or []) or "—"
    fone = c.get("whatsapp") or ""
    linhas = [
        "🤖 *Lead qualificado pelo robô do site*",
        f"Nome: {c.get('nome') or '—'}",
        f"WhatsApp: {('wa.me/' + fone) if fone else '—'}",
        f"E-mail: {c.get('email') or '—'}",
        f"Perfil: {PERFIL_TXT.get(c.get('perfil'), '—')}",
        f"Interesse: {assuntos}",
    ]
    if c.get("pediu_humano"):
        linhas.append("⚠️ Pediu para falar com uma pessoa.")
    if ultimas:
        linhas.append("\nO que ele disse:")
        linhas += [f"• {u[:200]}" for u in ultimas]
    linhas.append(f"\nPainel: {KB.SITE}/dashboard/admin/leads")
    return "\n".join(linhas)


async def _encaminhar(db, c: dict) -> None:
    """Avisa o dono (WhatsApp Z-API + e-mail). Best-effort, 1x por conversa."""
    agora = _agora()
    # Teto global anti-flood: 20 avisos/hora.
    recentes = await db[COL].count_documents({"notificado_em": {"$gte": agora - timedelta(hours=1)}})
    res = await db[COL].find_one_and_update(
        {"id": c["id"], "notificado_em": None}, {"$set": {"notificado_em": agora}})
    if not res:
        return  # outra requisição já avisou
    if recentes >= 20:
        logger.warning("atendimento: teto de avisos/hora atingido — lead %s gravado sem aviso.", c["id"])
        return
    texto = montar_aviso(c)
    try:
        from routes.avaliacao_publica import _notificar_avaliador
        await _notificar_avaliador(db, texto)
    except Exception as e:  # noqa: BLE001
        logger.error("atendimento: falha no WhatsApp ao dono: %s", e)
    try:
        from services import notificacao_lead as NL
        cfg = await NL.carregar_config(db)
        if cfg.get("email_lead_ativo"):
            para = await NL.destino(db, cfg)
            if para:
                from email_service import _base_template, _send_in_background
                corpo = "<br>".join(texto.replace("*", "").split("\n"))
                html = _base_template("Lead qualificado pelo robô do site", f"<p>{corpo}</p>")
                await _send_in_background(para, f"🤖 Lead qualificado: {c.get('nome') or 'visitante do site'}", html)
    except Exception as e:  # noqa: BLE001
        logger.error("atendimento: falha no e-mail ao dono: %s", e)


async def _aplicar_avaliacao(db, sid: str, av: dict, extra_set: Optional[dict] = None) -> dict:
    s = {"estagio": av["estagio"], "perfil": av["perfil"], "assuntos": av["assuntos"],
         "pediu_humano": av["pediu_humano"], "atualizado_em": _agora()}
    for k, v in (av.get("contato") or {}).items():
        if v:
            s[k] = v
    s.update(extra_set or {})
    await db[COL].update_one({"id": sid}, {"$set": s})
    if av["estagio"] == "qualificado":
        await db[COL].update_one({"id": sid, "qualificado_em": None}, {"$set": {"qualificado_em": _agora()}})
    return await db[COL].find_one({"id": sid})


def _view_publica(c: dict, extra: Optional[dict] = None) -> dict:
    out = {
        "sessao_id": c["id"],
        "estagio": c.get("estagio"),
        "perfil": c.get("perfil"),
        "acoes": Q.acoes(c),
        "tem_contato": bool(c.get("whatsapp") or c.get("email")),
    }
    out.update(extra or {})
    return out


# ── Endpoints públicos ───────────────────────────────────────────────────────
@router.get("/sessao/{sessao_id}")
@pub_limiter.limit("30/minute")
async def obter_sessao(sessao_id: str, request: Request, db=Depends(get_db)):
    _valida_sessao(sessao_id)
    c = await db[COL].find_one({"id": sessao_id})
    if not c:
        return {"sessao_id": sessao_id, "mensagens": [{"role": "assistant", "content": SAUDACAO}],
                "acoes": [], "estagio": "curioso", "tem_contato": False}
    msgs = [{"role": m["role"], "content": m["content"]} for m in c.get("mensagens", [])][-30:]
    return _view_publica(c, {"mensagens": msgs})


@router.post("/mensagem")
@pub_limiter.limit("15/minute")
async def mensagem(dados: MensagemIn, request: Request, db=Depends(get_db)):
    sid = _valida_sessao(dados.sessao_id)
    texto = dados.mensagem.strip()
    if not texto:
        raise HTTPException(422, "Mensagem vazia.")
    origem = {"pagina": dados.pagina, "referrer": dados.referrer, "utm_source": dados.utm_source,
              "utm_medium": dados.utm_medium, "utm_campaign": dados.utm_campaign}
    c = await _obter_ou_criar(db, sid, request, origem)
    if (c.get("n_msgs_cliente") or 0) >= MAX_MSGS_CLIENTE:
        return _view_publica(c, {"resposta": (
            "Já conversamos bastante por aqui 🙂 Para continuar, fale direto com o José pelo WhatsApp "
            "ou crie sua conta grátis."), "provedor": "limite"})

    agora = _agora()
    await db[COL].update_one({"id": sid}, {
        "$push": {"mensagens": {"role": "user", "content": texto, "ts": agora}},
        "$inc": {"n_msgs_cliente": 1}, "$set": {"atualizado_em": agora}})
    c = await db[COL].find_one({"id": sid})

    provedor = "offline"
    meta = {}
    try:
        bruto, provedor = await _responder_ia(c)
        resposta, meta = Q.separar_meta(bruto)
    except Exception as e:  # noqa: BLE001 — sem IA, responde pela base fixa
        logger.warning("atendimento: IA indisponível (%s) — resposta offline.", type(e).__name__)
        resposta = ""
    av = Q.avaliar(c, texto, meta)
    if not resposta:
        resposta = Q.resposta_offline(av["assuntos"], av["estagio"])
        provedor = "offline"

    c = await _aplicar_avaliacao(db, sid, av)
    await db[COL].update_one({"id": sid}, {"$push": {"mensagens": {
        "role": "assistant", "content": resposta, "ts": _agora(), "provedor": provedor}}})
    if Q.deve_encaminhar(c):
        await _encaminhar(db, c)
    return _view_publica(c, {"resposta": resposta, "provedor": provedor,
                             "pedir_contato": av["pedir_contato"]})


@router.post("/contato")
@pub_limiter.limit("6/minute")
async def contato(dados: ContatoIn, request: Request, db=Depends(get_db)):
    sid = _valida_sessao(dados.sessao_id)
    if (dados.website or "").strip():
        return {"ok": True}
    if not dados.consentimento:
        raise HTTPException(422, "É necessário autorizar o contato (LGPD).")
    fone = Q.normalizar_fone(dados.whatsapp)
    if not fone:
        raise HTTPException(422, "WhatsApp inválido. Use DDD + número.")
    c = await _obter_ou_criar(db, sid, request)
    agora = _agora()
    s = {"nome": dados.nome.strip().title(), "whatsapp": fone, "consentimento_em": agora,
         "atualizado_em": agora, "estagio": Q.subir_estagio(c.get("estagio"), "qualificado")}
    if dados.email and "@" in dados.email:
        s["email"] = dados.email.strip().lower()
    await db[COL].update_one({"id": sid}, {"$set": s})
    await db[COL].update_one({"id": sid, "qualificado_em": None}, {"$set": {"qualificado_em": agora}})
    resposta = (f"Obrigado, {s['nome'].split()[0]}! ✅ O José já foi avisado e vai te chamar no WhatsApp. "
                f"Se for usar a plataforma, você já pode testar {KB.TRIAL_DIAS} dias grátis pelo botão abaixo.")
    await db[COL].update_one({"id": sid}, {"$push": {"mensagens": {
        "role": "assistant", "content": resposta, "ts": agora, "provedor": "sistema"}}})
    c = await db[COL].find_one({"id": sid})
    if Q.deve_encaminhar(c):
        await _encaminhar(db, c)
    return _view_publica(c, {"resposta": resposta})


@router.post("/evento")
@pub_limiter.limit("30/minute")
async def evento(dados: EventoIn, request: Request, db=Depends(get_db)):
    sid = _valida_sessao(dados.sessao_id)
    chave = _EVENTOS.get(dados.evento)
    if not chave:
        raise HTTPException(422, "Evento desconhecido.")
    await db[COL].update_one({"id": sid}, {"$inc": {f"cliques.{chave}": 1},
                                           "$set": {"atualizado_em": _agora()}})
    if chave in ("cadastro", "whatsapp"):
        c = await db[COL].find_one({"id": sid})
        if c:
            await _aplicar_avaliacao(db, sid, {
                "estagio": Q.subir_estagio(c.get("estagio"), "interessado"), "perfil": c.get("perfil") or "indefinido",
                "assuntos": c.get("assuntos") or [], "pediu_humano": bool(c.get("pediu_humano")), "contato": {}})
    return {"ok": True}


async def marcar_conversao(db, sessao_id: Optional[str], user_id: str, email: str) -> None:
    """Chamado no cadastro: liga a conta nova à conversa do robô (best-effort)."""
    if not sessao_id or not _SESSAO_RE.match(sessao_id):
        return
    try:
        await db[COL].update_one({"id": sessao_id}, {"$set": {
            "estagio": "convertido", "convertido_em": _agora(), "user_id": user_id,
            "email": email, "atualizado_em": _agora()}})
    except Exception as e:  # noqa: BLE001
        logger.warning("atendimento: falha ao marcar conversão: %s", e)


# ── Painel admin ─────────────────────────────────────────────────────────────
STATUS_ADMIN = {"novo", "em_contato", "fechado", "descartado"}


def _resumo_lista(c: dict) -> dict:
    ult = [m for m in c.get("mensagens", []) if m.get("role") == "user"]
    return {
        "id": c["id"], "criado_em": _iso(c.get("criado_em")), "atualizado_em": _iso(c.get("atualizado_em")),
        "estagio": c.get("estagio"), "perfil": c.get("perfil"), "assuntos": c.get("assuntos") or [],
        "nome": c.get("nome"), "whatsapp": c.get("whatsapp"), "email": c.get("email"),
        "n_msgs_cliente": c.get("n_msgs_cliente") or 0, "pediu_humano": bool(c.get("pediu_humano")),
        "notificado_em": _iso(c.get("notificado_em")), "convertido_em": _iso(c.get("convertido_em")),
        "cliques": c.get("cliques") or {}, "status_admin": c.get("status_admin") or "novo",
        "nota": c.get("nota") or "", "origem": c.get("origem") or {},
        "ultima_pergunta": (ult[-1]["content"][:160] if ult else ""),
    }


def _filtro_periodo(dias: int) -> dict:
    return {"criado_em": {"$gte": _agora() - timedelta(days=dias)}} if dias and dias > 0 else {}


@admin_router.get("/stats")
async def stats(dias: int = Query(30, ge=0, le=3650), db=Depends(get_db)):
    base = _filtro_periodo(dias)
    base_real = {**base, "n_msgs_cliente": {"$gt": 0}}  # quem só abriu o chat não conta
    total = await db[COL].count_documents(base_real)
    por_estagio = {e: await db[COL].count_documents({**base_real, "estagio": e}) for e in Q.ESTAGIOS}
    com_contato = await db[COL].count_documents({**base_real, "$or": [
        {"whatsapp": {"$nin": [None, ""]}}, {"email": {"$nin": [None, ""]}}]})
    encaminhados = await db[COL].count_documents({**base, "notificado_em": {"$ne": None}})
    pediram_humano = await db[COL].count_documents({**base_real, "pediu_humano": True})
    abertos = await db[COL].count_documents(base)
    msgs = 0
    cliques = {"cadastro": 0, "planos": 0, "whatsapp": 0}
    assuntos: dict = {}
    perfis: dict = {}
    async for c in db[COL].find(base_real, {"n_msgs_cliente": 1, "cliques": 1, "assuntos": 1, "perfil": 1}):
        msgs += c.get("n_msgs_cliente") or 0
        for k in cliques:
            cliques[k] += int((c.get("cliques") or {}).get(k) or 0)
        for a in c.get("assuntos") or []:
            assuntos[a] = assuntos.get(a, 0) + 1
        p = c.get("perfil") or "indefinido"
        perfis[p] = perfis.get(p, 0) + 1
    qualif = por_estagio["qualificado"] + por_estagio["convertido"]
    return {
        "dias": dias, "conversas": total, "aberturas": abertos, "mensagens_recebidas": msgs,
        "por_estagio": por_estagio, "com_contato": com_contato, "encaminhados": encaminhados,
        "pediram_humano": pediram_humano, "cliques": cliques,
        "taxa_qualificacao": round(100 * qualif / total, 1) if total else 0.0,
        "taxa_conversao": round(100 * por_estagio["convertido"] / total, 1) if total else 0.0,
        "assuntos": sorted(({"assunto": a, "rotulo": Q.ROTULO_ASSUNTO.get(a, a), "total": n}
                            for a, n in assuntos.items()), key=lambda x: -x["total"])[:12],
        "perfis": perfis,
    }


@admin_router.get("/conversas")
async def listar(estagio: Optional[str] = None, status: Optional[str] = None,
                 q: Optional[str] = None, dias: int = Query(30, ge=0, le=3650),
                 page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db=Depends(get_db)):
    filtro = {**_filtro_periodo(dias), "n_msgs_cliente": {"$gt": 0}}
    if estagio in Q.ESTAGIOS:
        filtro["estagio"] = estagio
    elif estagio == "encaminhado":
        filtro["notificado_em"] = {"$ne": None}
    if status in STATUS_ADMIN:
        filtro["status_admin"] = status
    if q and q.strip():
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        filtro["$or"] = [{"nome": rx}, {"whatsapp": rx}, {"email": rx}, {"mensagens.content": rx}]
    total = await db[COL].count_documents(filtro)
    cur = db[COL].find(filtro).sort("atualizado_em", -1).skip((page - 1) * limit).limit(limit)
    itens = [_resumo_lista(c) async for c in cur]
    return {"items": itens, "total": total, "page": page, "limit": limit}


@admin_router.get("/conversas/{cid}")
async def detalhe(cid: str, db=Depends(get_db)):
    c = await db[COL].find_one({"id": cid})
    if not c:
        raise HTTPException(404, "Conversa não encontrada.")
    out = _resumo_lista(c)
    out["mensagens"] = [{"role": m.get("role"), "content": m.get("content"), "ts": _iso(m.get("ts")),
                         "provedor": m.get("provedor")} for m in c.get("mensagens", [])]
    out["aviso_whatsapp"] = montar_aviso(c)
    return out


class AtualizarConversa(BaseModel):
    status_admin: Optional[str] = None
    nota: Optional[str] = Field(None, max_length=2000)


@admin_router.patch("/conversas/{cid}")
async def atualizar(cid: str, body: AtualizarConversa, db=Depends(get_db)):
    s = {}
    if body.status_admin is not None:
        if body.status_admin not in STATUS_ADMIN:
            raise HTTPException(422, "Status inválido.")
        s["status_admin"] = body.status_admin
    if body.nota is not None:
        s["nota"] = body.nota
    if not s:
        raise HTTPException(422, "Nada para atualizar.")
    r = await db[COL].update_one({"id": cid}, {"$set": s})
    if not r.matched_count:
        raise HTTPException(404, "Conversa não encontrada.")
    return {"ok": True}


@admin_router.delete("/conversas/{cid}")
async def excluir(cid: str, db=Depends(get_db)):
    r = await db[COL].delete_one({"id": cid})
    if not r.deleted_count:
        raise HTTPException(404, "Conversa não encontrada.")
    return {"ok": True}
