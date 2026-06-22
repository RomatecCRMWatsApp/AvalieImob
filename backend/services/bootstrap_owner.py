# @module services.bootstrap_owner — Bootstrap one-time da conta de DONO (login definitivo).
"""Permite definir o login definitivo do dono SEM acesso direto ao banco (que só existe no
Railway). Controlado por variável de ambiente:

  BOOTSTRAP_OWNER_PASSWORD  (obrigatório p/ rodar)  — senha do dono (NUNCA versionada)
  BOOTSTRAP_OWNER_EMAIL     (opcional)  — e-mail destino; default = OWNER_EMAIL_PADRAO
  BOOTSTRAP_OWNER_FROM      (opcional)  — e-mail atual do dono; default romateccrm@gmail.com

No startup: se BOOTSTRAP_OWNER_PASSWORD estiver setada e ainda não tiver rodado p/ aquele
e-mail (flag em db.system_flags), o sistema:
  • acha a conta de dono (pelo e-mail destino, senão pelo FROM, senão pela role privilegiada);
  • RENOMEIA o e-mail dela p/ o destino (preserva TODOS os dados — mesmo user_id);
  • define a senha (bcrypt, mesmo hash do login), role privilegiada e plano ativo.
Idempotente (flag impede repetir). Depois é só REMOVER a env var no Railway.
"""
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("romatec")

OWNER_EMAIL_PADRAO = "admin@romatecavalieimob.com.br"
_ROLES_PRIV = ["owner", "ceo", "admin", "Owner", "CEO", "Admin"]


async def bootstrap_owner(db) -> None:
    senha = (os.getenv("BOOTSTRAP_OWNER_PASSWORD") or "").strip()
    if not senha:
        return  # nada a fazer (uso normal)

    novo = (os.getenv("BOOTSTRAP_OWNER_EMAIL") or OWNER_EMAIL_PADRAO).strip().lower()
    flag_id = f"bootstrap_owner:{novo}:v1"
    if await db.system_flags.find_one({"_id": flag_id}):
        logger.info("bootstrap_owner: já aplicado p/ %s — REMOVA BOOTSTRAP_OWNER_PASSWORD do Railway.", novo)
        return

    from services.auth_service import hash_password

    # 1) conta destino já existe com esse e-mail? então só (re)define senha/role/plano.
    alvo = await db.users.find_one({"email": novo})
    origem_email = alvo.get("email") if alvo else None

    # 2) senão, acha a conta de dono atual p/ RENOMEAR (preserva dados).
    if not alvo:
        origem = (os.getenv("BOOTSTRAP_OWNER_FROM") or "romateccrm@gmail.com").strip().lower()
        alvo = await db.users.find_one({"email": origem})
        if not alvo:
            alvo = await db.users.find_one({"role": {"$in": _ROLES_PRIV}})
        if not alvo:
            logger.error("bootstrap_owner: nenhuma conta de dono encontrada (origem=%s).", origem)
            return
        origem_email = alvo.get("email")
        conflito = await db.users.find_one({"email": novo})
        if conflito and conflito.get("id") != alvo.get("id"):
            logger.error("bootstrap_owner: e-mail %s já pertence a OUTRA conta — abortando.", novo)
            return

    role_atual = (alvo.get("role") or "").lower()
    novo_role = alvo.get("role") if role_atual in ("owner", "ceo", "admin") else "owner"

    await db.users.update_one({"id": alvo["id"]}, {"$set": {
        "email": novo,
        "password_hash": hash_password(senha),
        "role": novo_role,
        "plan_status": "active",
        "updated_at": datetime.now(timezone.utc),
    }})
    await db.system_flags.insert_one({
        "_id": flag_id, "done_at": datetime.now(timezone.utc),
        "from_email": origem_email, "user_id": alvo.get("id"),
    })
    logger.warning(
        "bootstrap_owner: conta '%s' -> '%s' (role=%s, plano ativo). "
        "LOGIN PRONTO. Agora REMOVA BOOTSTRAP_OWNER_PASSWORD das Variables do Railway.",
        origem_email, novo, novo_role,
    )
