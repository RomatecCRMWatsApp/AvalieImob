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


# ── Serviço de log de acesso ────────────────────────────────────────────────
import asyncio

from services import acesso_log


class _FakeColl:
    def __init__(self):
        self.docs = []
    async def insert_one(self, doc):
        self.docs.append(doc)
        return type("R", (), {"inserted_id": len(self.docs)})()
    async def update_one(self, flt, upd, **kw):
        self.ultima_update = (flt, upd)
        return type("R", (), {"modified_count": 1})()


class _FakeDB:
    def __init__(self):
        self.user_access_log = _FakeColl()
        self.users = _FakeColl()


def test_login_grava_evento_e_incrementa_contador():
    db = _FakeDB()
    acesso_log.limpar_cache_throttle()
    asyncio.run(acesso_log.registrar_login(db, "u1", ip="1.2.3.4", user_agent="UA"))

    assert len(db.user_access_log.docs) == 1
    ev = db.user_access_log.docs[0]
    assert ev["user_id"] == "u1"
    assert ev["event"] == "login"
    assert ev["ip"] == "1.2.3.4"
    assert "expira_em" not in ev, "evento de login deve ser permanente (sem TTL)"

    flt, upd = db.users.ultima_update
    assert flt == {"id": "u1"}
    assert upd["$inc"] == {"login_count": 1}
    assert "last_login_at" in upd["$set"]


def test_heartbeat_grava_com_ttl_e_nao_incrementa_contador():
    db = _FakeDB()
    acesso_log.limpar_cache_throttle()
    asyncio.run(acesso_log.registrar_heartbeat(db, "u2"))

    ev = db.user_access_log.docs[0]
    assert ev["event"] == "session_heartbeat"
    assert "expira_em" in ev, "heartbeat precisa de TTL"

    flt, upd = db.users.ultima_update
    assert "$inc" not in upd, "heartbeat nao conta como acesso"
    assert "last_login_at" in upd["$set"]


def test_heartbeat_throttled_em_15_minutos():
    db = _FakeDB()
    acesso_log.limpar_cache_throttle()
    asyncio.run(acesso_log.registrar_heartbeat(db, "u3"))
    asyncio.run(acesso_log.registrar_heartbeat(db, "u3"))
    asyncio.run(acesso_log.registrar_heartbeat(db, "u3"))
    assert len(db.user_access_log.docs) == 1, "so o primeiro heartbeat grava"


def test_heartbeat_de_usuarios_distintos_nao_se_bloqueiam():
    db = _FakeDB()
    acesso_log.limpar_cache_throttle()
    asyncio.run(acesso_log.registrar_heartbeat(db, "a"))
    asyncio.run(acesso_log.registrar_heartbeat(db, "b"))
    assert len(db.user_access_log.docs) == 2


def test_falha_no_banco_nao_propaga():
    """Auditoria nunca pode derrubar a request do usuario."""
    class _Explode:
        async def insert_one(self, doc):
            raise RuntimeError("mongo caiu")
        async def update_one(self, *a, **kw):
            raise RuntimeError("mongo caiu")

    db = _FakeDB()
    db.user_access_log = _Explode()
    acesso_log.limpar_cache_throttle()
    asyncio.run(acesso_log.registrar_login(db, "u9"))  # nao deve levantar
