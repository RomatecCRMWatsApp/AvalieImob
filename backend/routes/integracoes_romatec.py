# @module routes.integracoes_romatec — Integração Romatec CRM → AvalieImob:
# provisionamento (servidor-a-servidor, HMAC) e SSO (link de uso único).
#
#   POST /api/integracoes/romatec/provisionar  — chamado pelo backend do CRM
#   POST /api/integracoes/romatec/sso          — chamado pela página /sso do frontend
#
# Regras e protocolo em services/romatec_crm_integracao.py.
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from models import AuthResponse, UserPublic
from services import acesso_log
from services import romatec_crm_integracao as RC
from services.auth_service import create_token

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/integracoes/romatec", tags=["Integração Romatec CRM"])

_MSG_NAO_CONFIGURADA = "Integração com o Romatec CRM não configurada"
_MSG_ASSINATURA = "Requisição não autenticada"
_MSG_LINK_INVALIDO = "Link de acesso inválido ou expirado"
_MSG_LINK_USADO = "Link de acesso já utilizado"
_MSG_NAO_LIBERADO = "Acesso ao AvalieImob ainda não liberado para sua conta do Romatec CRM"
# Sem a palavra "assinatura": o interceptor do axios redireciona p/ a tela de
# planos qualquer 403 que a contenha.
_MSG_SUSPENSO = ("Seu acesso ao AvalieImob pelo Romatec CRM está suspenso ou vencido. "
                 "Regularize no Romatec CRM para continuar")


def _segredo() -> str:
    try:
        return RC.obter_segredo()
    except RC.IntegracaoNaoConfigurada:
        raise HTTPException(status_code=503, detail=_MSG_NAO_CONFIGURADA)


@router.post("/provisionar")
@limiter.limit("120/minute")
async def provisionar(request: Request, db=Depends(get_db)):
    segredo = _segredo()
    # A assinatura é sobre o corpo BRUTO — validar ANTES de interpretar o JSON.
    corpo = await request.body()
    if not RC.assinatura_valida(
        segredo,
        request.headers.get("X-Romatec-Timestamp"),
        request.headers.get("X-Romatec-Signature"),
        corpo,
    ):
        logger.warning("Romatec CRM: provisionamento com assinatura inválida/expirada (ip=%s)",
                       request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail=_MSG_ASSINATURA)
    try:
        dados = json.loads(corpo.decode("utf-8"))
        payload = RC.ProvisionarPayload.model_validate(dados)
    except ValidationError as e:
        erros = [{"loc": list(x.get("loc", ())), "msg": x.get("msg"), "type": x.get("type")}
                 for x in e.errors()]
        raise HTTPException(status_code=422, detail=erros)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=422, detail="Corpo JSON inválido")
    return await RC.provisionar(db, payload)


class SSORequest(BaseModel):
    token: str


def _user_public(u: dict) -> UserPublic:
    # Mesmo preenchimento do /auth/login.
    defaults = {"crea": "", "role": "user", "plan": "mensal", "plan_status": "inactive", "plan_expires": None, "company": "", "bio": "", "company_logo": None}
    return UserPublic(**{k: u.get(k) if u.get(k) is not None else defaults.get(k, "") for k in UserPublic.model_fields})


@router.post("/sso", response_model=AuthResponse)
@limiter.limit("20/minute")
async def sso(request: Request, data: SSORequest, db=Depends(get_db)):
    segredo = _segredo()
    try:
        claims = RC.decodificar_sso(segredo, data.token)
    except RC.TokenSSOInvalido:
        raise HTTPException(status_code=401, detail=_MSG_LINK_INVALIDO)
    if not await RC.consumir_jti(db, claims["jti"]):
        logger.warning("Romatec CRM: SSO com link reaproveitado (crm=%s)", claims["_crm_id"])
        raise HTTPException(status_code=401, detail=_MSG_LINK_USADO)

    u = await RC.localizar_usuario(db, claims["_crm_id"], claims.get("email"))
    if not u:
        raise HTTPException(status_code=403, detail=_MSG_NAO_LIBERADO)
    if not RC.plano_vigente(u):
        raise HTTPException(status_code=403, detail=_MSG_SUSPENSO)

    token = create_token(u["id"])
    # Auditoria de acesso (best-effort — nunca bloqueia o login).
    await acesso_log.registrar_login(
        db, u["id"],
        ip=(request.client.host if request and request.client else None),
        user_agent=(request.headers.get("user-agent") if request else None),
    )
    logger.info("Romatec CRM: SSO concedido user=%s crm=%s", u["id"], claims["_crm_id"])
    return AuthResponse(user=_user_public(u), token=token)
