# @module tests.test_auditoria_acesso — funil de acesso/pagamento (regras puras + serviços)
from datetime import datetime, timedelta

from models.auditoria_acesso import derivar_status_funil


def _user(**kw):
    base = {"id": "u1", "name": "Fulano", "email": "f@x.com", "plan_status": "inactive"}
    base.update(kw)
    return base


def test_nunca_iniciou_checkout():
    assert derivar_status_funil(_user(), None) == "never_started"


def test_checkout_iniciado_sem_evento_de_pagamento():
    u = _user(checkout_started_at=datetime.utcnow())
    assert derivar_status_funil(u, None) == "checkout_started"


def test_pagamento_pendente():
    u = _user(checkout_started_at=datetime.utcnow())
    assert derivar_status_funil(u, {"status": "pending"}) == "payment_pending"
    assert derivar_status_funil(u, {"status": "in_process"}) == "payment_pending"


def test_pagamento_recusado_sem_plano_vira_bloqueado():
    u = _user(checkout_started_at=datetime.utcnow())
    assert derivar_status_funil(u, {"status": "rejected"}) == "blocked_no_payment"


def test_plano_ativo_vence_pagamento_recusado():
    """REGRA CRÍTICA: recusa num upgrade não pode derrubar quem já pagou."""
    u = _user(plan_status="active", plan_expires=datetime.utcnow() + timedelta(days=20))
    assert derivar_status_funil(u, {"status": "rejected"}) == "active"


def test_plano_expirado():
    u = _user(plan_status="expired")
    assert derivar_status_funil(u, None) == "expired"


def test_plano_active_com_data_vencida_conta_como_expirado():
    """Espelha get_active_subscriber, que expira preguiçosamente na próxima chamada."""
    u = _user(plan_status="active", plan_expires=datetime.utcnow() - timedelta(days=1))
    assert derivar_status_funil(u, None) == "expired"
