# @module services.conformidade_service — Verificações de conformidade COFECI/CNAI.
# Adaptado às convenções do projeto: user_id, db.ptam_documents, art_rrt_numero,
# Telegram via carregar_integracoes() (telegram_bot_token/telegram_chat_id_default).
import logging
from datetime import date, datetime, timedelta
from typing import List

from models.conformidade import AlertaConformidade
from services.integracoes_util import carregar_integracoes

logger = logging.getLogger("romatec")

_CANCELADOS = ["cancelado", "Cancelado", "CANCELADO"]
_SEM_ART = [None, "", "nao_informado", "não informado", "N/A"]


def _parse_validade(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


async def verificar_credenciais(db, uid: str) -> List[AlertaConformidade]:
    alertas: List[AlertaConformidade] = []
    hoje = date.today()
    creds = await db.credenciais.find({"user_id": uid, "ativo": True}).to_list(50)

    for cred in creds:
        try:
            validade = _parse_validade(cred["validade"])
        except Exception:
            continue
        dias = (validade - hoje).days
        alerta_dias = int(cred.get("alerta_dias", 60))
        tipo_up = str(cred.get("tipo", "")).upper()
        numero = cred.get("numero", "")
        orgao = cred.get("orgao_emissor", "")

        if dias < 0:
            alertas.append(AlertaConformidade(
                user_id=uid, tipo="credencial_vencida",
                titulo=f"🔴 {tipo_up} VENCIDA",
                descricao=(
                    f"Sua credencial {tipo_up} {numero} ({orgao}) venceu há {abs(dias)} dias. "
                    f"Renove imediatamente para continuar emitindo documentos com validade jurídica."
                ),
                severidade="urgente", referencia_id=cred["id"],
            ))
        elif dias <= alerta_dias:
            alertas.append(AlertaConformidade(
                user_id=uid, tipo="credencial_vencendo",
                titulo=f"⚠️ {tipo_up} vence em {dias} dias",
                descricao=(
                    f"Credencial {tipo_up} {numero} ({orgao}) válida até "
                    f"{validade.strftime('%d/%m/%Y')}. Providencie a renovação com antecedência."
                ),
                severidade="urgente" if dias <= 15 else "aviso",
                referencia_id=cred["id"],
            ))
    return alertas


async def verificar_ptams_sem_art(db, uid: str, prazo_dias: int = 30) -> List[AlertaConformidade]:
    alertas: List[AlertaConformidade] = []
    limite = datetime.utcnow() - timedelta(days=prazo_dias)
    cursor = db.ptam_documents.find(
        {
            "user_id": uid,
            "art_rrt_numero": {"$in": _SEM_ART},
            "created_at": {"$lte": limite},
            "status": {"$nin": _CANCELADOS},
        },
        {"_id": 0, "id": 1, "numero_ptam": 1, "created_at": 1, "imovel_endereco": 1},
    )
    ptams = await cursor.to_list(50)
    for p in ptams:
        ca = p.get("created_at")
        dias = (datetime.utcnow() - ca).days if isinstance(ca, datetime) else prazo_dias
        ident = p.get("numero_ptam") or p.get("imovel_endereco") or p["id"]
        alertas.append(AlertaConformidade(
            user_id=uid, tipo="ptam_sem_art",
            titulo=f"📋 PTAM sem ART há {dias} dias",
            descricao=(
                f'O documento "{ident}" foi emitido há {dias} dias e não possui ART/TRT '
                f"vinculada. Documentos sem ART podem ter validade jurídica questionada."
            ),
            severidade="aviso", referencia_id=p["id"],
        ))
    return alertas


async def verificar_meta_mensal(db, uid: str, config: dict) -> List[AlertaConformidade]:
    alertas: List[AlertaConformidade] = []
    meta = int(config.get("meta_ptams_mes", 0) or 0)
    if meta <= 0:
        return alertas

    hoje = datetime.utcnow()
    inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count = await db.ptam_documents.count_documents({
        "user_id": uid,
        "created_at": {"$gte": inicio_mes},
        "status": {"$nin": _CANCELADOS},
    })

    progresso = (count / meta) * 100 if meta else 0
    dia = hoje.day
    dias_no_mes = 30
    progresso_esperado = (dia / dias_no_mes) * 100

    if progresso < progresso_esperado - 20:
        projecao = int(count * (dias_no_mes / dia)) if dia else count
        alertas.append(AlertaConformidade(
            user_id=uid, tipo="meta_mensal",
            titulo=f"📊 Meta mensal: {count}/{meta} PTAMs ({progresso:.0f}%)",
            descricao=(
                f"Você emitiu {count} de {meta} PTAMs este mês. "
                f"No ritmo atual, projeção de {projecao} ao final do mês."
            ),
            severidade="info",
        ))
    return alertas


async def rodar_verificacao_completa(db, uid: str) -> int:
    """Roda todas as verificações ativas e persiste alertas novos (1x/dia por chave)."""
    config = await db.config_conformidade.find_one({"user_id": uid}) or {}
    prazo_art = int(config.get("prazo_art_dias", 30) or 30)

    todos: List[AlertaConformidade] = []
    if config.get("alerta_credencial", True):
        todos += await verificar_credenciais(db, uid)
    if config.get("alerta_ptam_sem_art", True):
        todos += await verificar_ptams_sem_art(db, uid, prazo_art)
    if config.get("alerta_metas", True):
        todos += await verificar_meta_mensal(db, uid, config)

    inicio_dia = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    gerados = 0
    for alerta in todos:
        existe = await db.alertas_conformidade.find_one({
            "user_id": uid,
            "tipo": alerta.tipo,
            "referencia_id": alerta.referencia_id,
            "created_at": {"$gte": inicio_dia},
        })
        if existe:
            continue
        await db.alertas_conformidade.insert_one(alerta.model_dump())
        gerados += 1
        if config.get("notificar_telegram", True):
            try:
                await notificar_telegram(db, uid, alerta)
            except Exception as e:  # noqa: BLE001
                logger.warning("Falha ao notificar Telegram (conformidade): %s", e)
    return gerados


async def notificar_telegram(db, uid: str, alerta: AlertaConformidade):
    """Envia o alerta via bot Telegram do usuário (reusa integrações já existentes)."""
    import httpx

    cfg = await carregar_integracoes(db, uid)
    bot_token = (cfg or {}).get("telegram_bot_token")
    chat_id = (cfg or {}).get("telegram_chat_id_default")
    if not bot_token or not chat_id:
        return

    texto = f"*AvalieImob — {alerta.titulo}*\n\n{alerta.descricao}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json={
            "chat_id": chat_id, "text": texto, "parse_mode": "Markdown",
        })
    if r.status_code == 200:
        await db.alertas_conformidade.update_one(
            {"id": alerta.id}, {"$set": {"notificado_telegram": True}}
        )
