# @module services.notificacao_lead — avisos de lead/cadastro por E-MAIL.
#
# Complementa o WhatsApp (Z-API) que já existia:
#   1. e-mail IMEDIATO a cada lead da calculadora;
#   2. RESUMO periódico (diário ou semanal) com cadastros, canais de origem,
#      leads e assinaturas do período — o mesmo espírito do resumo da ZAYRA,
#      só que dentro do sistema e no e-mail do dono.
#
# Config em `sys_config._id="notificacoes_lead"`. Envio é best-effort: nunca
# derruba o registro do lead nem o scheduler.
import logging
from datetime import datetime, timedelta
from typing import Optional

from services import origem_trafego as OT

logger = logging.getLogger("romatec")

CONFIG_ID = "notificacoes_lead"
# Fortaleza/Açailândia = UTC-3 (mesmo offset usado no scheduler da prospecção).
_OFFSET_BR = timedelta(hours=3)

DEFAULTS = {
    "email_lead_ativo": True,      # e-mail a cada lead novo da calculadora
    "email_destino": "",           # vazio = e-mail da conta dona
    "resumo_ativo": True,
    "resumo_freq": "semanal",      # diario | semanal
    "resumo_hora": 17,             # hora local (0-23)
    "resumo_dia_semana": 4,        # 0=segunda … 6=domingo (só p/ semanal) — 4 = sexta
    "resumo_ultimo": None,         # "YYYY-MM-DD" do último envio
}


def normalizar_config(doc: Optional[dict]) -> dict:
    cfg = dict(DEFAULTS)
    for k, v in (doc or {}).items():
        if k in cfg and v is not None:
            cfg[k] = v
    cfg["email_lead_ativo"] = bool(cfg["email_lead_ativo"])
    cfg["resumo_ativo"] = bool(cfg["resumo_ativo"])
    cfg["resumo_freq"] = "diario" if str(cfg["resumo_freq"]) == "diario" else "semanal"
    # Valor absurdo cai no DEFAULT (não no extremo do intervalo): um "99" digitado
    # por engano vira 17h, não 23h.
    try:
        hora = int(cfg["resumo_hora"])
        cfg["resumo_hora"] = hora if 0 <= hora <= 23 else DEFAULTS["resumo_hora"]
    except (TypeError, ValueError):
        cfg["resumo_hora"] = DEFAULTS["resumo_hora"]
    try:
        dia = int(cfg["resumo_dia_semana"])
        cfg["resumo_dia_semana"] = dia if 0 <= dia <= 6 else DEFAULTS["resumo_dia_semana"]
    except (TypeError, ValueError):
        cfg["resumo_dia_semana"] = DEFAULTS["resumo_dia_semana"]
    cfg["email_destino"] = str(cfg["email_destino"] or "").strip().lower()
    return cfg


async def carregar_config(db) -> dict:
    return normalizar_config(await db.sys_config.find_one({"_id": CONFIG_ID}))


async def salvar_config(db, dados: dict) -> dict:
    cfg = normalizar_config({**(await carregar_config(db)), **(dados or {})})
    await db.sys_config.update_one({"_id": CONFIG_ID}, {"$set": cfg}, upsert=True)
    return cfg


async def destino(db, cfg: Optional[dict] = None) -> str:
    """E-mail que recebe os avisos: o configurado ou o da conta dona."""
    cfg = cfg or await carregar_config(db)
    if cfg.get("email_destino"):
        return cfg["email_destino"]
    import os
    owner_email = (os.environ.get("OWNER_EMAIL") or "romateccrm@gmail.com").lower()
    owner = await db.users.find_one({"email": owner_email})
    return (owner or {}).get("email") or owner_email


# ── 1. E-mail imediato de lead ───────────────────────────────────────────────
async def enviar_email_lead(db, lead: dict) -> dict:
    """Avisa o dono, por e-mail, que entrou um lead na calculadora."""
    try:
        cfg = await carregar_config(db)
        if not cfg["email_lead_ativo"]:
            return {"ok": False, "erro": "desativado"}
        para = await destino(db, cfg)
        if not para:
            return {"ok": False, "erro": "sem e-mail de destino"}
        from email_service import send_lead_email
        await send_lead_email(para, lead)
        return {"ok": True, "para": para}
    except Exception as e:  # noqa: BLE001 — o lead já está salvo; aviso é acessório
        logger.error("notificacao_lead: falha no e-mail de lead: %s", e)
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}


# ── 2. Resumo periódico ──────────────────────────────────────────────────────
async def montar_resumo(db, dias: int = 7, agora: Optional[datetime] = None) -> dict:
    """Números do período: cadastros (por canal), leads, testes e assinaturas."""
    agora = agora or datetime.utcnow()
    corte = agora - timedelta(days=max(1, int(dias)))

    usuarios = await db.users.find({}).to_list(5000)
    novos = [u for u in usuarios
             if isinstance(OT._naive(u.get("created_at")), datetime)
             and OT._naive(u.get("created_at")) >= corte]

    leads = await db.leads_avaliacao.find({"criado_em": {"$gte": corte}}).to_list(1000)

    trials = [u for u in usuarios
              if isinstance(OT._naive(u.get("trial_inicio")), datetime)
              and OT._naive(u.get("trial_inicio")) >= corte]

    # Assinaturas do período: pagamentos aprovados (fonte de verdade do webhook MP).
    assinaturas = 0
    try:
        aprovados = await db.payment_events.find(
            {"status": "approved", "received_at": {"$gte": corte}}).to_list(1000)
        assinaturas = len({a.get("user_id") for a in aprovados if a.get("user_id")})
    except Exception:  # noqa: BLE001 — coleção pode não existir ainda
        assinaturas = 0

    return {
        "dias": int(dias),
        "de": corte.isoformat(),
        "ate": agora.isoformat(),
        "cadastros": len(novos),
        "leads_calculadora": len(leads),
        "testes_liberados": len(trials),
        "assinaturas": assinaturas,
        "canais": OT.resumo_por_canal(novos),
        "canais_geral": OT.resumo_por_canal(usuarios),
        "total_usuarios": len(usuarios),
    }


async def enviar_resumo(db, dias: Optional[int] = None, para: Optional[str] = None) -> dict:
    """Monta e envia o resumo por e-mail. Usado pelo scheduler e pelo botão de teste."""
    try:
        cfg = await carregar_config(db)
        if dias is None:
            dias = 1 if cfg["resumo_freq"] == "diario" else 7
        alvo = (para or await destino(db, cfg)).strip()
        if not alvo:
            return {"ok": False, "erro": "sem e-mail de destino"}
        dados = await montar_resumo(db, dias)
        from email_service import send_resumo_email
        await send_resumo_email(alvo, dados)
        return {"ok": True, "para": alvo, "resumo": dados}
    except Exception as e:  # noqa: BLE001
        logger.error("notificacao_lead: falha no resumo: %s", e)
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}


def deve_enviar_resumo(cfg: dict, agora_utc: datetime) -> bool:
    """Chegou a hora do resumo? (idempotente por dia — `resumo_ultimo`).

    Função PURA: o scheduler decide com ela e só então dispara o envio.
    """
    cfg = normalizar_config(cfg)
    if not cfg["resumo_ativo"]:
        return False
    local = agora_utc - _OFFSET_BR
    if local.hour < cfg["resumo_hora"]:
        return False
    if cfg["resumo_freq"] == "semanal" and local.weekday() != cfg["resumo_dia_semana"]:
        return False
    return cfg.get("resumo_ultimo") != local.strftime("%Y-%m-%d")


async def marcar_resumo_enviado(db, agora_utc: Optional[datetime] = None) -> str:
    dia = ((agora_utc or datetime.utcnow()) - _OFFSET_BR).strftime("%Y-%m-%d")
    await db.sys_config.update_one({"_id": CONFIG_ID}, {"$set": {"resumo_ultimo": dia}},
                                   upsert=True)
    return dia
