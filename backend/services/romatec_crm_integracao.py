# @module services.romatec_crm_integracao — Integração Romatec CRM → AvalieImob
# (provisionamento servidor-a-servidor + SSO por link de uso único).
#
# PROTOCOLO FIXO (o lado do CRM é escrito contra exatamente isto — não alterar):
#   - Segredo compartilhado em ROMATEC_CRM_INTEGRACAO_SECRET. Vazio → 503.
#   - Provisionamento: HMAC-SHA256(segredo, f"{timestamp}.{corpo_bruto}") em hex
#     minúsculo no header X-Romatec-Signature; X-Romatec-Timestamp em segundos
#     unix; janela de ±300 s.
#   - SSO: JWT HS256 assinado com o MESMO segredo, iss="romatec-crm",
#     aud="avalieimob", sub=str(crm_usuario_id), jti de uso único, exp=iat+60.
#
# NUNCA registrar em log o segredo, tokens ou assinaturas.
import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Literal, Optional

import jwt
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("romatec")

ENV_SEGREDO = "ROMATEC_CRM_INTEGRACAO_SECRET"
JANELA_TIMESTAMP_S = 300          # tolerância do X-Romatec-Timestamp
SSO_ISSUER = "romatec-crm"
SSO_AUDIENCE = "avalieimob"
SSO_LEEWAY_S = 10
# Blindagem extra: o CRM emite exp = iat + 60. Um token com vida maior que isto
# sobreviveria à limpeza do TTL de `sso_jti_usados` e poderia ser reapresentado.
SSO_VIDA_MAXIMA_S = 300

PLANO_CRM = "romatec_crm"
ORIGEM_CRM = "romatec_crm"
ATE_SEM_DATA = datetime(2099, 12, 31, tzinfo=timezone.utc)
_PAPEIS_ADMIN = {"admin", "owner", "ceo"}


class IntegracaoNaoConfigurada(Exception):
    """ROMATEC_CRM_INTEGRACAO_SECRET ausente/vazio → a rota responde 503."""


class TokenSSOInvalido(Exception):
    """JWT do SSO inválido, expirado ou fora do protocolo → 401."""


class ProvisionarPayload(BaseModel):
    evento: Literal["ativar", "suspender", "reativar"]
    crm_usuario_id: int
    email: EmailStr
    nome: str
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    plano: str
    ate: Optional[datetime] = None


# ── Segredo ──────────────────────────────────────────────────────────────────
def obter_segredo() -> str:
    """Lido a cada request (não em import) — permite configurar sem reiniciar
    o módulo e facilita os testes."""
    segredo = (os.environ.get(ENV_SEGREDO) or "").strip()
    if not segredo:
        raise IntegracaoNaoConfigurada()
    return segredo


# ── Datas ────────────────────────────────────────────────────────────────────
def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Mongo devolve datetime naive (em UTC) — normaliza para aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def plano_vigente(u: dict, agora: Optional[datetime] = None) -> bool:
    """Mesma regra do `dependencies.get_active_subscriber`: admin/owner/ceo
    passam; os demais precisam de plan_status "active" e plan_expires não vencido."""
    if str(u.get("role") or "").lower() in _PAPEIS_ADMIN:
        return True
    if u.get("plan_status") != "active":
        return False
    expira = _utc(u.get("plan_expires"))
    agora = agora or datetime.now(timezone.utc)
    return not (expira and expira < agora)


# ── Assinatura HMAC (provisionamento) ────────────────────────────────────────
def assinar(segredo: str, timestamp: str, corpo: bytes) -> str:
    """HMAC-SHA256(segredo, f"{timestamp}.{corpo}") em hex minúsculo."""
    msg = f"{timestamp}.".encode("utf-8") + corpo
    return hmac.new(segredo.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def assinatura_valida(segredo: str, timestamp: Optional[str], assinatura: Optional[str],
                      corpo: bytes, agora: Optional[float] = None) -> bool:
    """Valida headers + janela de tempo + HMAC sobre o corpo BRUTO."""
    if not timestamp or not assinatura:
        return False
    try:
        ts = int(timestamp.strip())
    except (ValueError, AttributeError):
        return False
    agora = time.time() if agora is None else agora
    if abs(agora - ts) > JANELA_TIMESTAMP_S:
        return False
    esperado = assinar(segredo, timestamp.strip(), corpo)
    return hmac.compare_digest(esperado, assinatura.strip().lower())


# ── Localização do usuário ───────────────────────────────────────────────────
async def localizar_usuario(db, crm_usuario_id: int, email: Optional[str],
                            vincular: bool = False) -> Optional[dict]:
    """Por `romatec_crm_id`; senão pelo e-mail (minúsculo). Com `vincular`, o
    match por e-mail grava o `romatec_crm_id` (provisionamento)."""
    u = await db.users.find_one({"romatec_crm_id": crm_usuario_id})
    if u:
        return u
    if not email:
        return None
    u = await db.users.find_one({"email": email.strip().lower()})
    if u and vincular:
        await db.users.update_one({"id": u["id"]}, {"$set": {"romatec_crm_id": crm_usuario_id}})
        u["romatec_crm_id"] = crm_usuario_id
    return u


# ── Provisionamento ──────────────────────────────────────────────────────────
async def provisionar(db, p: ProvisionarPayload) -> dict:
    """Aplica o evento do CRM. Idempotente.

    Resposta: {"ok": True, "acao": criado|ativado|suspenso|ignorado_plano_proprio|
    inexistente, "user_id": <id AvalieImob ou None>}."""
    email = str(p.email).strip().lower()
    u = await localizar_usuario(db, p.crm_usuario_id, email, vincular=True)
    agora = datetime.now(timezone.utc)

    if p.evento == "suspender":
        if not u:
            return {"ok": True, "acao": "inexistente", "user_id": None}
        papel = str(u.get("role") or "").lower()
        if u.get("plan_origem") != ORIGEM_CRM or papel in _PAPEIS_ADMIN:
            # Plano próprio do AvalieImob (ou conta administrativa): não mexe.
            return {"ok": True, "acao": "ignorado_plano_proprio", "user_id": u["id"]}
        await db.users.update_one({"id": u["id"]}, {"$set": {
            "plan_status": "expired", "romatec_crm_atualizado_em": agora}})
        logger.info("Romatec CRM: acesso suspenso user=%s crm=%s", u["id"], p.crm_usuario_id)
        return {"ok": True, "acao": "suspenso", "user_id": u["id"]}

    # ativar / reativar
    novo_ate = _utc(p.ate) or ATE_SEM_DATA

    if not u:
        from models import User          # import tardio: evita ciclo models↔services
        from services.auth_service import hash_password
        nome = (p.nome or "").strip() or email.split("@")[0]
        user = User(name=nome, email=email, role="user")
        doc = user.model_dump()
        doc.update({
            # Senha inutilizável — o acesso é pelo SSO; se quiser senha própria,
            # o usuário usa "Esqueci a senha".
            "password_hash": hash_password(secrets.token_urlsafe(32)),
            "plan": PLANO_CRM,
            "plan_status": "active",
            "plan_expires": novo_ate,
            "plan_origem": ORIGEM_CRM,
            "romatec_crm_id": p.crm_usuario_id,
            "romatec_crm_atualizado_em": agora,
        })
        if p.telefone and p.telefone.strip():
            doc["phone"] = p.telefone.strip()
        await db.users.insert_one(doc)
        logger.info("Romatec CRM: usuário criado user=%s crm=%s", doc["id"], p.crm_usuario_id)
        return {"ok": True, "acao": "criado", "user_id": doc["id"]}

    # Usuário existente: NUNCA encurtar um acesso já vigente.
    atual = _utc(u.get("plan_expires")) if u.get("plan_status") == "active" else None
    plan_expires = max(atual, novo_ate) if atual else novo_ate
    upd = {
        "plan": PLANO_CRM,
        "plan_status": "active",
        "plan_expires": plan_expires,
        "plan_origem": ORIGEM_CRM,
        "romatec_crm_id": p.crm_usuario_id,
        "romatec_crm_atualizado_em": agora,
    }
    if p.telefone and p.telefone.strip() and not (u.get("phone") or "").strip():
        upd["phone"] = p.telefone.strip()
    await db.users.update_one({"id": u["id"]}, {"$set": upd})
    logger.info("Romatec CRM: acesso ativado user=%s crm=%s evento=%s",
                u["id"], p.crm_usuario_id, p.evento)
    return {"ok": True, "acao": "ativado", "user_id": u["id"]}


# ── SSO ──────────────────────────────────────────────────────────────────────
def decodificar_sso(segredo: str, token: str) -> dict:
    """Valida o JWT do SSO (HS256, iss/aud, exp/iat/jti obrigatórios, leeway 10 s)."""
    if not token or not isinstance(token, str):
        raise TokenSSOInvalido()
    try:
        claims = jwt.decode(
            token, segredo, algorithms=["HS256"],
            audience=SSO_AUDIENCE, issuer=SSO_ISSUER, leeway=SSO_LEEWAY_S,
            options={"require": ["exp", "iat", "jti", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError:
        raise TokenSSOInvalido()
    try:
        crm_id = int(str(claims.get("sub")))
        vida = float(claims["exp"]) - float(claims["iat"])
    except (TypeError, ValueError, KeyError):
        raise TokenSSOInvalido()
    jti = str(claims.get("jti") or "").strip()
    if not jti or vida > SSO_VIDA_MAXIMA_S:
        raise TokenSSOInvalido()
    claims["_crm_id"] = crm_id
    claims["jti"] = jti
    return claims


async def consumir_jti(db, jti: str) -> bool:
    """Marca o jti como usado. False se já tinha sido usado (link reaproveitado).

    A garantia forte é o índice ÚNICO em `sso_jti_usados.jti` (db._INDICES); a
    checagem prévia cobre o caso de o índice ainda não existir."""
    from pymongo.errors import DuplicateKeyError
    if await db.sso_jti_usados.find_one({"jti": jti}):
        return False
    try:
        await db.sso_jti_usados.insert_one({"jti": jti, "usado_em": datetime.now(timezone.utc)})
    except DuplicateKeyError:
        return False
    return True
