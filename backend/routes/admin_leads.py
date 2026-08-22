# @module routes.admin_leads — Painel admin dos leads da Calculadora pública.
"""Gestão dos leads capturados em `leads_avaliacao` (calculadora "Quanto vale meu
imóvel?"): listagem com filtro/busca/paginação, stats (cards + taxa de conversão),
troca de status, nota e exclusão.

Adaptado do spec (que usava ADMIN_API_TOKEN) p/ a auth real do AvalieImob:
auth via `get_admin_user` (JWT; roles admin/owner/ceo) + db Depends(get_db).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from db import get_db
from dependencies import get_admin_user

logger = logging.getLogger("romatec")

router = APIRouter(
    prefix="/admin/leads",
    tags=["Admin · Leads"],
    dependencies=[Depends(get_admin_user)],
)

StatusLead = Literal["novo", "em_contato", "convertido", "descartado"]
COL = "leads_avaliacao"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    for campo in ("criado_em", "atualizado_em"):
        v = doc.get(campo)
        if isinstance(v, datetime):
            doc[campo] = v.isoformat()
    return doc


class AtualizarLead(BaseModel):
    status: Optional[StatusLead] = None
    nota: Optional[str] = Field(default=None, max_length=2000)


@router.get("")
async def listar_leads(
    status: Optional[StatusLead] = None,
    q: Optional[str] = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db=Depends(get_db),
):
    filtro: dict = {}
    if status:
        filtro["status"] = status
    if q:
        regex = {"$regex": q.strip(), "$options": "i"}
        filtro["$or"] = [{"nome": regex}, {"whatsapp": regex}, {"email": regex}]

    try:
        total = await db[COL].count_documents(filtro)
        cursor = db[COL].find(filtro).sort("criado_em", -1).skip((page - 1) * limit).limit(limit)
        itens = [_serialize(d) async for d in cursor]
    except Exception as e:  # noqa: BLE001
        logger.exception("admin_leads: erro ao listar")
        raise HTTPException(500, "Falha ao listar leads.") from e

    return {"total": total, "page": page, "limit": limit, "items": itens}


@router.get("/stats")
async def stats(db=Depends(get_db)):
    try:
        cursor = db[COL].aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}])
        por_status = {d["_id"]: d["n"] async for d in cursor}
        desde = datetime.now(timezone.utc) - timedelta(days=30)
        ultimos_30 = await db[COL].count_documents({"criado_em": {"$gte": desde}})
        # Conversão por origem (A/B das 3 calculadoras)
        cursor_o = db[COL].aggregate([{"$group": {
            "_id": "$origem", "total": {"$sum": 1},
            "convertidos": {"$sum": {"$cond": [{"$eq": ["$status", "convertido"]}, 1, 0]}},
        }}])
        por_origem = [{
            "origem": (d["_id"] or "calculadora_publica"),
            "total": d["total"], "convertidos": d["convertidos"],
            "taxa_conversao": round((d["convertidos"] / d["total"]) * 100, 1) if d["total"] else 0.0,
        } async for d in cursor_o]
        por_origem.sort(key=lambda x: x["total"], reverse=True)
    except Exception as e:  # noqa: BLE001
        logger.exception("admin_leads: erro nas stats")
        raise HTTPException(500, "Falha ao calcular estatísticas.") from e

    total = sum(por_status.values())
    convertidos = por_status.get("convertido", 0)
    taxa = round((convertidos / total) * 100, 1) if total else 0.0
    return {
        "total": total,
        "novos": por_status.get("novo", 0),
        "em_contato": por_status.get("em_contato", 0),
        "convertidos": convertidos,
        "descartados": por_status.get("descartado", 0),
        "ultimos_30_dias": ultimos_30,
        "taxa_conversao": taxa,
        "por_origem": por_origem,
    }


# ── Cadastros por origem (Google, Bing, direto…) ────────────────────────────
# O dado já vem do cadastro (routes/auth grava utm_* + referrer); aqui só
# classificamos e agregamos. Serve a aba "Cadastros" do painel de Leads.
@router.get("/cadastros")
async def listar_cadastros(
    dias: int = Query(default=30, ge=1, le=3650),
    canal: Optional[str] = Query(default=None, max_length=40),
    q: Optional[str] = Query(default=None, max_length=80),
    db=Depends(get_db),
):
    from services import origem_trafego as OT

    usuarios = await db.users.find({}).sort("created_at", -1).to_list(5000)
    resumo = OT.resumo_por_canal(usuarios, dias=dias)
    resumo_geral = OT.resumo_por_canal(usuarios)

    linhas = [OT.view_cadastro(u) for u in usuarios]
    corte = datetime.utcnow() - timedelta(days=dias)
    no_periodo = [c for c in linhas
                  if c["cadastrado_em"] and datetime.fromisoformat(c["cadastrado_em"]) >= corte]
    if canal:
        no_periodo = [c for c in no_periodo if c["canal"] == canal]
    if q:
        alvo = q.lower()
        no_periodo = [c for c in no_periodo
                      if alvo in (c["nome"] or "").lower() or alvo in (c["email"] or "").lower()]

    totais = {
        "cadastros": len(no_periodo),
        "assinantes": sum(1 for c in no_periodo if c["situacao"] == "assinante"),
        "em_teste": sum(1 for c in no_periodo if c["situacao"] == "em_teste"),
        "nunca_acessaram": sum(1 for c in no_periodo if c["nunca_acessou"]),
        "total_base": len(linhas),
    }
    totais["conversao"] = (round(100.0 * totais["assinantes"] / totais["cadastros"], 1)
                           if totais["cadastros"] else 0.0)
    return {"dias": dias, "totais": totais, "canais": resumo,
            "canais_geral": resumo_geral, "cadastros": no_periodo}


# ── Notificações por e-mail (lead imediato + resumo periódico) ──────────────
class NotificacoesBody(BaseModel):
    email_lead_ativo: Optional[bool] = None
    email_destino: Optional[str] = Field(default=None, max_length=120)
    resumo_ativo: Optional[bool] = None
    resumo_freq: Optional[Literal["diario", "semanal"]] = None
    resumo_hora: Optional[int] = Field(default=None, ge=0, le=23)
    resumo_dia_semana: Optional[int] = Field(default=None, ge=0, le=6)


@router.get("/notificacoes")
async def obter_notificacoes(db=Depends(get_db)):
    from services import notificacao_lead as NL
    cfg = await NL.carregar_config(db)
    return {**cfg, "destino_efetivo": await NL.destino(db, cfg)}


@router.post("/notificacoes")
async def salvar_notificacoes(body: NotificacoesBody, db=Depends(get_db)):
    from services import notificacao_lead as NL
    cfg = await NL.salvar_config(db, body.model_dump(exclude_none=True))
    return {"ok": True, **cfg, "destino_efetivo": await NL.destino(db, cfg)}


@router.post("/notificacoes/testar")
async def testar_notificacoes(body: dict = None, db=Depends(get_db)):
    """Manda um e-mail de TESTE agora: `tipo` = "lead" (exemplo) ou "resumo" (real)."""
    from services import notificacao_lead as NL
    body = body or {}
    tipo = str(body.get("tipo") or "resumo").lower()
    para = str(body.get("email") or "").strip().lower() or await NL.destino(db)
    if not para:
        raise HTTPException(422, "Sem e-mail de destino. Informe um e-mail.")
    if tipo == "lead":
        exemplo = {
            "nome": "Maria (exemplo)", "whatsapp": "5599991811246",
            "email": "maria@exemplo.com", "origem": "teste",
            "imovel": {"tipo": "casa", "area": 120, "cidade": "Açailândia", "uf": "MA",
                       "padrao": "medio", "conservacao": "bom", "vagas": 1},
            "estimativa": {"faixa_texto": "R$ 288.000 a R$ 366.000"},
        }
        from email_service import send_lead_email
        try:
            await send_lead_email(para, exemplo)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "erro": f"{type(e).__name__}: {e}", "para": para}
        return {"ok": True, "tipo": "lead", "para": para}
    r = await NL.enviar_resumo(db, dias=int(body.get("dias") or 7), para=para)
    return {**r, "tipo": "resumo"}


@router.patch("/{lead_id}")
async def atualizar_lead(lead_id: str, dados: AtualizarLead, db=Depends(get_db)):
    try:
        oid = ObjectId(lead_id)
    except InvalidId:
        raise HTTPException(422, "ID inválido.")

    update: dict = {"atualizado_em": datetime.now(timezone.utc)}
    if dados.status is not None:
        update["status"] = dados.status
    if dados.nota is not None:
        update["nota"] = dados.nota.strip()

    try:
        doc = await db[COL].find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    except Exception as e:  # noqa: BLE001
        logger.exception("admin_leads: erro ao atualizar")
        raise HTTPException(500, "Falha ao atualizar lead.") from e

    if not doc:
        raise HTTPException(404, "Lead não encontrado.")
    return _serialize(doc)


@router.delete("/{lead_id}")
async def excluir_lead(lead_id: str, db=Depends(get_db)):
    try:
        oid = ObjectId(lead_id)
    except InvalidId:
        raise HTTPException(422, "ID inválido.")
    res = await db[COL].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Lead não encontrado.")
    return {"ok": True}
