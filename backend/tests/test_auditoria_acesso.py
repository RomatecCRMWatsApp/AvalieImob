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


# ── Serviço de eventos de pagamento ─────────────────────────────────────────
from services import payment_events


class _FakeEventos:
    def __init__(self):
        self.docs = []
    async def find_one(self, flt, **kw):
        for d in reversed(self.docs):
            if all(d.get(k) == v for k, v in flt.items()):
                return d
        return None
    async def insert_one(self, doc):
        self.docs.append(doc)
        return type("R", (), {"inserted_id": len(self.docs)})()


class _FakeDBPag:
    def __init__(self):
        self.payment_events = _FakeEventos()


def test_registra_evento_com_payload_bruto():
    db = _FakeDBPag()
    pago = {"id": 123, "status": "approved", "status_detail": "accredited",
            "transaction_amount": 89.9}
    novo = asyncio.run(payment_events.registrar(db, "u1", pago, "mensal"))

    assert novo is True
    ev = db.payment_events.docs[0]
    assert ev["user_id"] == "u1"
    assert ev["mp_payment_id"] == "123"
    assert ev["status"] == "approved"
    assert ev["status_detail"] == "accredited"
    assert ev["transaction_amount"] == 89.9
    assert ev["raw_payload"] == pago, "payload bruto e a fonte de auditoria"


def test_evento_repetido_com_mesmo_status_e_ignorado():
    db = _FakeDBPag()
    pago = {"id": 1, "status": "approved"}
    assert asyncio.run(payment_events.registrar(db, "u1", pago, "mensal")) is True
    assert asyncio.run(payment_events.registrar(db, "u1", pago, "mensal")) is False
    assert len(db.payment_events.docs) == 1


def test_transicao_de_status_do_mesmo_pagamento_e_registrada():
    """append-only: pending -> approved sao DOIS eventos do mesmo mp_payment_id."""
    db = _FakeDBPag()
    asyncio.run(payment_events.registrar(db, "u1", {"id": 7, "status": "pending"}, "mensal"))
    asyncio.run(payment_events.registrar(db, "u1", {"id": 7, "status": "approved"}, "mensal"))
    assert len(db.payment_events.docs) == 2


def test_evento_sem_usuario_ainda_e_gravado_para_auditoria():
    """external_reference invalido nao pode sumir sem rastro."""
    db = _FakeDBPag()
    asyncio.run(payment_events.registrar(db, None, {"id": 9, "status": "approved"}, None))
    assert db.payment_events.docs[0]["user_id"] is None


def test_falha_ao_registrar_nao_propaga():
    class _Explode:
        async def find_one(self, *a, **kw):
            raise RuntimeError("mongo caiu")
        async def insert_one(self, *a, **kw):
            raise RuntimeError("mongo caiu")

    db = _FakeDBPag()
    db.payment_events = _Explode()
    assert asyncio.run(payment_events.registrar(db, "u1", {"id": 1, "status": "approved"}, "mensal")) is False


# ── Regressão: PIX/boleto (pending -> approved) precisa ativar o plano ──────
# Exercita o HANDLER REAL `routes.payments.payment_webhook`. O único ponto
# falsificado é o SDK do Mercado Pago — todo o resto é o código de produção.
import routes.payments as pay


async def _anoop(*a, **kw):
    """Stub assíncrono: o webhook usa asyncio.create_task, que exige corrotina."""
    return None


class _FakeQueryParams:
    def get(self, k, default=None):
        return default          # sem token na query


class _FakeRequest:
    def __init__(self, body, headers=None):
        self._body = body
        self.query_params = _FakeQueryParams()
        self.headers = headers or {}   # x-signature / x-request-id

    async def json(self):
        return self._body


def _casa(doc, flt):
    """Match mínimo de filtro Mongo: igualdade + $ne + $gt (usados pelo webhook)."""
    for k, v in flt.items():
        atual = doc.get(k)
        if isinstance(v, dict):
            if "$ne" in v and atual == v["$ne"]:
                return False
            if "$gt" in v and not (atual is not None and atual > v["$gt"]):
                return False
        elif atual != v:
            return False
    return True


class _CollTxn:
    def __init__(self):
        self.docs = []
    async def find_one(self, flt, **kw):
        for d in self.docs:
            if _casa(d, flt):
                return d
        return None
    async def insert_one(self, doc):
        self.docs.append(doc)


class _CollUsers:
    def __init__(self, doc):
        self.doc = doc
    async def find_one(self, flt, **kw):
        return self.doc if self.doc.get("id") == flt.get("id") else None
    async def update_one(self, flt, upd, **kw):
        self.doc.update(upd.get("$set", {}))


class _DBWebhook:
    def __init__(self, user_doc):
        self.transactions = _CollTxn()
        self.users = _CollUsers(user_doc)
        self.payment_events = _FakeEventos()


def _sdk_com_status(status, pid=55):
    """SDK falso que devolve o pagamento `pid` no status pedido."""
    class _SDK:
        def payment(self):
            return self
        def get(self, rid):
            return {"response": {
                "id": pid, "status": status, "status_detail": "ok",
                "external_reference": "u1|mensal", "transaction_amount": 89.9,
            }}
    return _SDK()


def test_pix_pago_ativa_o_plano_no_segundo_webhook(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_TOKEN", "")
    monkeypatch.setattr(pay, "send_payment_email", _anoop)
    monkeypatch.setattr("services.zayra_webhook.notify_lead", _anoop)

    user = {"id": "u1", "name": "Fulano", "email": "f@x.com", "plan_status": "inactive"}
    db = _DBWebhook(user)
    body = {"type": "payment", "data": {"id": 55}}

    # Webhook 1 — PIX gerado, ainda não pago.
    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("pending"))
    asyncio.run(pay.payment_webhook(_FakeRequest(body), db))
    assert user["plan_status"] == "inactive", "pendente nao pode ativar"

    # Webhook 2 — cliente pagou o PIX.
    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("approved"))
    asyncio.run(pay.payment_webhook(_FakeRequest(body), db))
    assert user["plan_status"] == "active", (
        "REGRESSAO: pagamento aprovado apos pending nao ativou o plano"
    )
    assert user.get("plan_expires") is not None


def test_webhook_identico_repetido_nao_duplica(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_TOKEN", "")
    monkeypatch.setattr(pay, "send_payment_email", _anoop)
    monkeypatch.setattr("services.zayra_webhook.notify_lead", _anoop)

    user = {"id": "u1", "name": "F", "email": "f@x.com", "plan_status": "inactive"}
    db = _DBWebhook(user)
    body = {"type": "payment", "data": {"id": 55}}
    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("approved"))

    asyncio.run(pay.payment_webhook(_FakeRequest(body), db))
    asyncio.run(pay.payment_webhook(_FakeRequest(body), db))
    assert len(db.transactions.docs) == 1, "mesmo evento nao pode duplicar"


# ── Estorno / chargeback: revoga acesso, mas respeita renovação ─────────────
def _prep(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_TOKEN", "")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "")
    monkeypatch.setattr(pay, "send_payment_email", _anoop)
    monkeypatch.setattr("services.zayra_webhook.notify_lead", _anoop)


def test_estorno_revoga_o_acesso(monkeypatch):
    _prep(monkeypatch)
    user = {"id": "u1", "name": "F", "email": "f@x.com", "plan_status": "inactive"}
    db = _DBWebhook(user)

    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("approved"))
    asyncio.run(pay.payment_webhook(_FakeRequest({"type": "payment", "data": {"id": 55}}), db))
    assert user["plan_status"] == "active"

    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("refunded"))
    asyncio.run(pay.payment_webhook(_FakeRequest({"type": "payment", "data": {"id": 55}}), db))
    assert user["plan_status"] == "expired", "estorno precisa derrubar o plano"


def test_estorno_de_pagamento_antigo_nao_derruba_renovacao(monkeypatch):
    """Cliente renovou; o estorno da cobranca ANTIGA nao pode cortar o acesso."""
    _prep(monkeypatch)
    user = {"id": "u1", "name": "F", "email": "f@x.com", "plan_status": "inactive"}
    db = _DBWebhook(user)

    # Cobrança antiga (55), aprovada há 60 dias.
    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("approved", 55))
    asyncio.run(pay.payment_webhook(_FakeRequest({"type": "payment", "data": {"id": 55}}), db))
    db.transactions.docs[0]["created_at"] = datetime.utcnow() - timedelta(days=60)

    # Renovação (66), aprovada agora.
    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("approved", 66))
    asyncio.run(pay.payment_webhook(_FakeRequest({"type": "payment", "data": {"id": 66}}), db))
    assert user["plan_status"] == "active"

    # Estorno da cobrança ANTIGA.
    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("refunded", 55))
    asyncio.run(pay.payment_webhook(_FakeRequest({"type": "payment", "data": {"id": 55}}), db))
    assert user["plan_status"] == "active", (
        "REGRESSAO: estorno antigo derrubou plano sustentado por renovacao"
    )


def test_webhook_com_segredo_configurado_exige_assinatura(monkeypatch):
    """Com MERCADOPAGO_WEBHOOK_SECRET setado, webhook sem x-signature e 403."""
    from fastapi import HTTPException
    _prep(monkeypatch)
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "segredo")
    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("approved"))

    user = {"id": "u1", "name": "F", "email": "f@x.com", "plan_status": "inactive"}
    db = _DBWebhook(user)
    try:
        asyncio.run(pay.payment_webhook(_FakeRequest({"type": "payment", "data": {"id": 55}}), db))
        assert False, "deveria ter recusado sem assinatura"
    except HTTPException as e:
        assert e.status_code == 403
    assert user["plan_status"] == "inactive", "nao pode ativar sem assinatura valida"
