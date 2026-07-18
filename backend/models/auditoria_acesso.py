# @module models.auditoria_acesso — funil de acesso/pagamento (DIAGNÓSTICO).
# IMPORTANTE: nada aqui gateia acesso. A autoridade continua sendo `plan_status`,
# lido por dependencies.get_active_subscriber. Este módulo só DESCREVE o estado.
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel

EventoAcesso = Literal["login", "logout", "session_heartbeat"]

StatusFunil = Literal[
    "never_started", "checkout_started", "payment_pending",
    "active", "expired", "blocked_no_payment",
]

# Status do Mercado Pago que indicam pagamento ainda em curso.
MP_PENDENTES = {"pending", "in_process", "authorized"}
# Status do MP que indicam falha/reversão.
MP_FALHOS = {"rejected", "cancelled", "refunded", "charged_back"}

DIAS_RETENCAO_HEARTBEAT = 90
MINUTOS_THROTTLE_HEARTBEAT = 15


def _plano_vigente(user: Dict[str, Any]) -> bool:
    """True se plan_status=='active' E não venceu. Espelha dependencies.py:23."""
    if (user.get("plan_status") or "").lower() != "active":
        return False
    exp = user.get("plan_expires")
    if isinstance(exp, datetime) and exp < datetime.utcnow():
        return False
    return True


def derivar_status_funil(
    user: Dict[str, Any], ultimo_evento_pagamento: Optional[Dict[str, Any]]
) -> str:
    """Deriva o estágio de funil. Função PURA — sem I/O, sem efeito colateral.

    Ordem de precedência (a primeira que casar vence):
      1. Plano vigente        -> active          (nunca é rebaixado por recusa)
      2. plan_status expired  -> expired
      3. Último evento MP     -> payment_pending | blocked_no_payment
      4. Checkout iniciado    -> checkout_started
      5. Nada                 -> never_started
    """
    if _plano_vigente(user):
        return "active"

    plan_status = (user.get("plan_status") or "").lower()
    if plan_status in ("active", "expired"):
        # 'active' aqui só chega se a data venceu (item 1 já retornou caso contrário).
        return "expired"

    if ultimo_evento_pagamento:
        st = (ultimo_evento_pagamento.get("status") or "").lower()
        if st in MP_PENDENTES:
            return "payment_pending"
        if st in MP_FALHOS:
            return "blocked_no_payment"

    if user.get("checkout_started_at"):
        return "checkout_started"

    return "never_started"


class EventoPagamentoResumo(BaseModel):
    status: Optional[str] = None
    status_detail: Optional[str] = None
    em: Optional[datetime] = None


class AuditoriaUsuarioOut(BaseModel):
    id: str
    name: str = ""
    email: str = ""
    role: str = ""
    cadastrado_em: Optional[datetime] = None
    ultimo_acesso: Optional[datetime] = None
    total_acessos: int = 0
    nunca_acessou: bool = True
    plan: str = ""
    plan_status: str = ""
    plan_expires: Optional[datetime] = None
    status_funil: str = "never_started"
    checkout_iniciado_em: Optional[datetime] = None
    ultimo_evento_pagamento: Optional[EventoPagamentoResumo] = None


class TimelineOut(BaseModel):
    acessos: List[Dict[str, Any]] = []
    pagamentos: List[Dict[str, Any]] = []
