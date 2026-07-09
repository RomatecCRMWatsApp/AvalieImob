# @module routes.cupons — Kit Promocional de Captação: cupons + link único + disparo Z-API.
#
# Adaptado às convenções do projeto:
#   - DB via get_db; admin via get_admin_user (role == "admin").
#   - Z-API reaproveitada (config por usuário) via carregar_integracoes + zapi_service.
#   - id = uuid str (não ObjectId). Endpoints /publico/* SEM auth (usados no cadastro).
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from db import get_db
from dependencies import get_admin_user
from models.cupom import Cupom, gerar_codigo
from services.ratelimit import pub_limiter

logger = logging.getLogger("romatec")
router = APIRouter(prefix="/cupons", tags=["Cupons Promocionais"])


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _app_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "https://www.romatecavalieimob.com.br").rstrip("/")


def serialize_cupom(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    for campo in ("criado_em", "atualizado_em", "validade", "whatsapp_enviado_em", "usado_em"):
        v = doc.get(campo)
        if isinstance(v, datetime):
            doc[campo] = v.isoformat()
    return doc


def _parse_validade(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00").replace("+00:00", ""))
    except ValueError:
        try:
            return datetime.fromisoformat(str(v)[:10])
        except ValueError:
            return None


def montar_mensagem_whatsapp(cupom: dict) -> str:
    nome = (cupom.get("nome_destinatario") or "").strip()
    saudacao = f"Olá, {nome}! 👋\n\n" if nome else "Olá! 👋\n\n"
    link = f"{_app_url()}/cadastro?promo={cupom['slug_unico']}"

    validade_str = ""
    val = _parse_validade(cupom.get("validade"))
    if val:
        validade_str = f"\n⏰ *Oferta válida até:* {val.strftime('%d/%m/%Y')}"

    # Dica: usar o e-mail (já informado no cupom) no cadastro.
    email = (cupom.get("email_destinatario") or "").strip()
    email_str = f"📧 *No cadastro, use o seu e-mail:* {email}\n\n" if email else ""

    msg_custom = (cupom.get("mensagem_customizada") or "").strip()
    if msg_custom:
        return f"{saudacao}{msg_custom}\n\n🔗 *Acesse agora:*\n{link}"

    vnorm = float(cupom.get("valor_plano_normal", 89.90))
    vdesc = float(cupom.get("valor_com_desconto", 60.00))
    return (
        f"{saudacao}"
        f"🎉 *Promoção especial AvalieImob!*\n\n"
        f"Temos uma oferta exclusiva para você:\n\n"
        f"✅ Sistema profissional de avaliação de imóveis\n"
        f"✅ Geração de PTAM em PDF\n"
        f"✅ Banco de amostras de mercado\n"
        f"✅ Laudos, contratos e muito mais\n\n"
        f"💰 *Plano normal:* R$ {vnorm:.2f}/mês\n".replace(".", ",")
        + f"🏷️ *Sua 1ª mensalidade:* ~R$ {vnorm:.2f}~ *R$ {vdesc:.2f}*\n".replace(".", ",")
        + f"💚 *Economia de R$ {(vnorm - vdesc):.2f} na primeira cobrança!*\n".replace(".", ",")
        + f"(a partir do 2º mês volta ao valor normal){validade_str}\n\n"
        f"👇 *Cadastre-se agora com seu desconto garantido:*\n"
        f"{link}\n\n"
        f"{email_str}"
        f"_RomaTec Consultoria Total — Açailândia/MA_"
    )


async def verificar_cupom_valido(db, slug_ou_codigo: str) -> dict:
    cupom = await db.cupons.find_one(
        {"$or": [{"slug_unico": slug_ou_codigo}, {"codigo": slug_ou_codigo.upper()}]}
    )
    if not cupom:
        raise HTTPException(404, "Cupom não encontrado")
    if cupom.get("status") != "ativo":
        raise HTTPException(400, f"Cupom {cupom.get('status')}")
    val = _parse_validade(cupom.get("validade"))
    if val and val < datetime.utcnow():
        await db.cupons.update_one({"id": cupom["id"]}, {"$set": {"status": "expirado"}})
        raise HTTPException(400, "Cupom expirado")
    if cupom.get("usos_realizados", 0) >= cupom.get("limite_usos", 1):
        raise HTTPException(400, "Cupom já utilizado")
    return cupom


# ─── CRUD ADMIN ───────────────────────────────────────────────────────────────
@router.post("", status_code=201)
@router.post("/", status_code=201)
async def criar_cupom(payload: dict, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    base = dict(payload or {})
    codigo = (base.get("codigo") or "").upper().strip()
    if not codigo:
        codigo = gerar_codigo(base.get("prefixo_codigo") or "ROMATEC")
    if await db.cupons.find_one({"codigo": codigo}):
        raise HTTPException(400, f"Código {codigo} já existe")
    base["codigo"] = codigo

    plano = float(base.get("valor_plano_normal", 89.90) or 89.90)
    desconto = float(base.get("valor_desconto", 20.00) or 0)
    base["valor_com_desconto"] = round(plano - desconto, 2)
    base["validade"] = _parse_validade(base.get("validade"))

    cupom = Cupom(**{**base, "criado_por": uid})
    doc = cupom.model_dump()
    await db.cupons.insert_one(dict(doc))
    return serialize_cupom(doc)


@router.get("")
@router.get("/")
async def listar_cupons(
    status: Optional[str] = Query(None),
    busca: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
    uid: str = Depends(get_admin_user),
    db=Depends(get_db),
):
    # Expira cupons vencidos antes de listar.
    await db.cupons.update_many(
        {"status": "ativo", "validade": {"$lt": datetime.utcnow(), "$ne": None}},
        {"$set": {"status": "expirado", "atualizado_em": datetime.utcnow()}},
    )
    filtro: dict = {}
    if status:
        filtro["status"] = status
    if busca:
        filtro["$or"] = [
            {"codigo": {"$regex": busca, "$options": "i"}},
            {"nome_destinatario": {"$regex": busca, "$options": "i"}},
            {"telefone_destinatario": {"$regex": busca, "$options": "i"}},
        ]
    cursor = db.cupons.find(filtro).sort("criado_em", -1).skip(skip).limit(limit)
    cupons = await cursor.to_list(length=limit)
    total = await db.cupons.count_documents(filtro)
    return {"total": total, "cupons": [serialize_cupom(c) for c in cupons]}


@router.get("/estatisticas")
async def estatisticas_cupons(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    pipeline = [{"$group": {"_id": "$status", "total": {"$sum": 1}, "usos": {"$sum": "$usos_realizados"}}}]
    resultado = await db.cupons.aggregate(pipeline).to_list(None)
    stats = {"ativo": 0, "utilizado": 0, "expirado": 0, "cancelado": 0, "total_usos": 0}
    for r in resultado:
        s = r.get("_id")
        if s in stats:
            stats[s] = r.get("total", 0)
        stats["total_usos"] += r.get("usos", 0)
    utilizados = await db.cupons.find({"status": "utilizado"}).to_list(None)
    stats["economia_gerada_rs"] = round(sum(float(c.get("valor_desconto", 20.00) or 0) for c in utilizados), 2)
    return stats


@router.get("/{cupom_id}")
async def obter_cupom(cupom_id: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    doc = await db.cupons.find_one({"id": cupom_id})
    if not doc:
        raise HTTPException(404, "Cupom não encontrado")
    return serialize_cupom(doc)


@router.put("/{cupom_id}/cancelar")
async def cancelar_cupom(cupom_id: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    res = await db.cupons.update_one(
        {"id": cupom_id, "status": "ativo"},
        {"$set": {"status": "cancelado", "atualizado_em": datetime.utcnow()}},
    )
    if res.matched_count == 0:
        raise HTTPException(400, "Cupom não encontrado ou não está ativo")
    return {"ok": True}


def _parse_validade(v):
    """Converte 'YYYY-MM-DD' ou ISO em datetime (ou None)."""
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip().replace("Z", "")
    for fmt in (s, s[:19], s[:10]):
        try:
            return datetime.fromisoformat(fmt)
        except Exception:
            continue
    return None


@router.put("/{cupom_id}")
async def atualizar_cupom(cupom_id: str, payload: dict, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Edita um cupom existente (admin)."""
    doc = await db.cupons.find_one({"id": cupom_id})
    if not doc:
        raise HTTPException(404, "Cupom não encontrado")
    campos = ("codigo", "prefixo_codigo", "valor_desconto", "valor_plano_normal",
              "nome_destinatario", "telefone_destinatario", "email_destinatario",
              "limite_usos", "mensagem_customizada")
    update = {k: payload[k] for k in campos if k in payload}
    if update.get("codigo"):
        update["codigo"] = str(update["codigo"]).upper().strip()
    if "validade" in payload:
        update["validade"] = _parse_validade(payload.get("validade"))
    vn = float(update.get("valor_plano_normal", doc.get("valor_plano_normal", 89.90)) or 0)
    vd = float(update.get("valor_desconto", doc.get("valor_desconto", 20.0)) or 0)
    update["valor_com_desconto"] = round(max(0.0, vn - vd), 2)
    update["atualizado_em"] = datetime.utcnow()
    await db.cupons.update_one({"id": cupom_id}, {"$set": update})
    novo = await db.cupons.find_one({"id": cupom_id})
    return serialize_cupom(novo)


@router.put("/{cupom_id}/revalidar")
async def revalidar_cupom(cupom_id: str, payload: dict = None, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Reativa um cupom expirado/cancelado com nova validade (default +30 dias)."""
    payload = payload or {}
    doc = await db.cupons.find_one({"id": cupom_id})
    if not doc:
        raise HTTPException(404, "Cupom não encontrado")
    validade = _parse_validade(payload.get("validade")) or (datetime.utcnow() + timedelta(days=30))
    await db.cupons.update_one(
        {"id": cupom_id},
        {"$set": {"status": "ativo", "validade": validade, "atualizado_em": datetime.utcnow()}},
    )
    novo = await db.cupons.find_one({"id": cupom_id})
    return serialize_cupom(novo)


@router.delete("/{cupom_id}")
async def excluir_cupom(cupom_id: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Exclui o cupom definitivamente (admin)."""
    res = await db.cupons.delete_one({"id": cupom_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Cupom não encontrado")
    return {"ok": True}


# ─── DISPARO WHATSAPP (Z-API do admin) ────────────────────────────────────────
@router.post("/{cupom_id}/enviar-whatsapp")
async def enviar_whatsapp_cupom(
    cupom_id: str, payload: dict = None, uid: str = Depends(get_admin_user), db=Depends(get_db)
):
    from services.integracoes_util import carregar_integracoes
    from services import zapi_service

    payload = payload or {}
    doc = await db.cupons.find_one({"id": cupom_id})
    if not doc:
        raise HTTPException(404, "Cupom não encontrado")

    telefone = (payload.get("telefone") or doc.get("telefone_destinatario") or "").strip()
    if not telefone:
        raise HTTPException(400, "Telefone não informado")

    if payload.get("mensagem_customizada") is not None:
        doc["mensagem_customizada"] = payload["mensagem_customizada"]
        await db.cupons.update_one(
            {"id": cupom_id}, {"$set": {"mensagem_customizada": payload["mensagem_customizada"]}}
        )
    if payload.get("nome_destinatario"):
        doc["nome_destinatario"] = payload["nome_destinatario"]

    cfg = await carregar_integracoes(db, uid)
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        raise HTTPException(400, "Z-API não configurada. Cadastre em Configurações → Integrações.")

    mensagem = montar_mensagem_whatsapp(doc)
    try:
        resp = await zapi_service.send_text(
            instance_id=cfg["zapi_instance_id"],
            token=cfg["zapi_token"],
            security_token=cfg.get("zapi_security_token"),
            phone=telefone,
            message=mensagem,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001
        logger.error("Erro Z-API (cupom %s): %s", cupom_id, e)
        raise HTTPException(502, f"Erro Z-API: {e}")

    await db.cupons.update_one(
        {"id": cupom_id},
        {"$set": {
            "whatsapp_enviado": True,
            "whatsapp_enviado_em": datetime.utcnow(),
            "telefone_destinatario": telefone,
            "atualizado_em": datetime.utcnow(),
        }},
    )
    return {"ok": True, "telefone": telefone, "mensagem_enviada": mensagem, "zapi_response": resp}


# ─── PÚBLICO (sem auth — usado na página de cadastro) ─────────────────────────
@router.get("/publico/validar/{slug_ou_codigo}")
@pub_limiter.limit("30/minute")
async def validar_cupom_publico(request: Request, slug_ou_codigo: str, db=Depends(get_db)):
    try:
        cupom = await verificar_cupom_valido(db, slug_ou_codigo)
        return {
            "valido": True,
            "codigo": cupom["codigo"],
            "slug_unico": cupom["slug_unico"],
            "valor_plano_normal": cupom["valor_plano_normal"],
            "valor_desconto": cupom["valor_desconto"],
            "valor_com_desconto": cupom["valor_com_desconto"],
            "aplicar_em": cupom["aplicar_em"],
            "nome_destinatario": cupom.get("nome_destinatario"),
        }
    except HTTPException as e:
        return {"valido": False, "motivo": e.detail}


@router.post("/publico/resgatar/{slug_ou_codigo}")
@pub_limiter.limit("12/minute")
async def resgatar_cupom(request: Request, slug_ou_codigo: str, payload: dict = None, db=Depends(get_db)):
    payload = payload or {}
    cupom = await verificar_cupom_valido(db, slug_ou_codigo)
    novos_usos = cupom.get("usos_realizados", 0) + 1
    await db.cupons.update_one(
        {"id": cupom["id"]},
        {"$set": {
            "usos_realizados": novos_usos,
            "status": "utilizado" if novos_usos >= cupom.get("limite_usos", 1) else "ativo",
            "usado_por_usuario_id": payload.get("usuario_id"),
            "usado_em": datetime.utcnow(),
            "atualizado_em": datetime.utcnow(),
        }},
    )
    return {
        "ok": True,
        "valor_cobrar_agora": cupom["valor_com_desconto"],
        "valor_proximas_mensalidades": cupom["valor_plano_normal"],
        "desconto_aplicado": cupom["valor_desconto"],
    }
