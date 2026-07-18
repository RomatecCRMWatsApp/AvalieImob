# Auditoria de Acesso e Pagamento — Implementation Plan (Fase 1: Backend)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar visibilidade de comportamento (acessou? chegou ao checkout? pagou? o webhook ativou?) para cada usuário cadastrado, sem alterar quem tem ou não acesso ao sistema.

**Architecture:** Duas collections novas e append-only (`user_access_log`, `payment_events`) alimentadas por hooks nos pontos de estrangulamento já existentes (`auth.login`, `dependencies.get_active_subscriber`, `payments.create-preference`, `payments.webhook`). O status de funil (`subscription_status`) é **derivado e puramente diagnóstico** — `plan_status` continua sendo a única autoridade de acesso, intocada nos 371 pontos de gating. Toda a regra de derivação vive numa função pura, testável sem banco.

**Tech Stack:** FastAPI, Motor (MongoDB async), Pydantic v2, pytest (fakes à mão + `asyncio.run`, sem pytest-asyncio/mongomock).

---

## Decisões travadas (não reabrir durante a execução)

| Decisão | Escolha | Porquê |
|---|---|---|
| Autoridade de acesso | `plan_status` | `subscription_status` nunca gateia. Evita regressão nos 371 call sites de `get_active_subscriber`. |
| Pagamento recusado | **Nunca** revoga plano ativo | Assinante pagante que tem cartão recusado num upgrade não pode perder acesso. |
| `login_count` | Incrementa **só** no evento `login` | Heartbeat não é acesso; contá-lo transformaria a métrica em ruído. |
| Retenção heartbeat | TTL 90 dias | Eventos `login`/`logout` são permanentes (sem campo `expira_em`). |
| Throttle heartbeat | Cache em processo, 15 min | Zero leitura extra no Mongo por request. 4 workers ⇒ até 4 gravações/15min/usuário. Aceitável. |
| Webhook | **Estender**, nunca substituir | O atual manda e-mail, dispara `notify_lead` (ZAYRA) e calcula expiry. |

### Divergências da spec original corrigidas neste plano

1. **`ObjectId` → uuid string.** Users usam `{"id": uid}`. Nenhum `ObjectId` neste módulo.
2. **`nome` → `name`.** Campo real em `backend/models/user.py:44`.
3. **`get_current_user` → `get_admin_user`/`get_active_subscriber`**, que retornam **`str`**, não objeto.
4. **Índice único `mp_payment_id` → composto `(mp_payment_id, status)`.** A spec pede log append-only *e* unique em `mp_payment_id`; as duas coisas se contradizem (a segunda transição de status do mesmo pagamento falharia). O composto permite uma linha por transição e bloqueia duplicata real.
5. **`never_started` ≠ "nunca acessou".** A spec funde as duas coisas. Aqui são campos distintos: `status_funil == "never_started"` (nunca iniciou checkout) e `ultimo_acesso is None` (nunca logou). O card "Nunca acessaram" usa o segundo.
6. **Datetimes naive (`datetime.utcnow()`).** O repo grava naive (`models/common.py`). Misturar aware/naive quebra comparação com `plan_expires`.
7. **Heartbeat em dependency, não em middleware.** Middleware não conhece o uid sem redecodificar o JWT; `get_active_subscriber` já carregou o user doc.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `backend/models/auditoria_acesso.py` *(criar)* | Constantes, mapa MP→funil, **função pura** `derivar_status_funil`, modelos de saída. Sem I/O. |
| `backend/services/acesso_log.py` *(criar)* | Gravação de eventos de acesso + throttle em processo. |
| `backend/services/payment_events.py` *(criar)* | Gravação append-only e idempotente dos webhooks MP. |
| `backend/routes/auth.py` *(modificar)* | Hook de `login`. |
| `backend/dependencies.py` *(modificar)* | Hook de `session_heartbeat`. |
| `backend/routes/payments.py` *(modificar)* | `checkout_started_at` na preference; `payment_events` no webhook. |
| `backend/routes/admin.py` *(modificar)* | `GET /admin/users/audit`, `GET /admin/users/{id}/timeline`. |
| `backend/server.py` *(modificar)* | Índices (TTL, composto, único). |
| `backend/tests/test_auditoria_acesso.py` *(criar)* | Testes das regras puras + serviços com fake db. |

---

### Task 1: Modelos e regra pura de derivação do funil

**Files:**
- Create: `backend/models/auditoria_acesso.py`
- Test: `backend/tests/test_auditoria_acesso.py`

- [ ] **Step 1: Write the failing test**

Criar `backend/tests/test_auditoria_acesso.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && py -m pytest tests/test_auditoria_acesso.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'models.auditoria_acesso'`

- [ ] **Step 3: Write minimal implementation**

Criar `backend/models/auditoria_acesso.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && py -m pytest tests/test_auditoria_acesso.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/models/auditoria_acesso.py backend/tests/test_auditoria_acesso.py
git commit -m "feat(auditoria): modelo e regra pura de derivacao do funil de pagamento"
```

---

### Task 2: Serviço de log de acesso com throttle

**Files:**
- Create: `backend/services/acesso_log.py`
- Modify: `backend/tests/test_auditoria_acesso.py` (acrescentar testes ao final)

- [ ] **Step 1: Write the failing test**

Acrescentar ao final de `backend/tests/test_auditoria_acesso.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && py -m pytest tests/test_auditoria_acesso.py -v`
Expected: FAIL com `ImportError: cannot import name 'acesso_log' from 'services'`

- [ ] **Step 3: Write minimal implementation**

Criar `backend/services/acesso_log.py`:

```python
# @module services.acesso_log — registro de acesso dos usuários (append-only).
# Toda gravação é best-effort: auditoria JAMAIS derruba a request do usuário.
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from models.auditoria_acesso import (
    DIAS_RETENCAO_HEARTBEAT, MINUTOS_THROTTLE_HEARTBEAT,
)

logger = logging.getLogger(__name__)

# Cache em processo do último heartbeat por usuário. Evita uma leitura no Mongo
# a cada request autenticada. Com 4 workers uvicorn, o pior caso são 4 gravações
# por janela de throttle por usuário — irrelevante em volume.
_ultimo_heartbeat: Dict[str, datetime] = {}


def limpar_cache_throttle() -> None:
    """Zera o cache de throttle. Usado pelos testes."""
    _ultimo_heartbeat.clear()


async def _gravar(
    db, user_id: str, event: str, ip: Optional[str], user_agent: Optional[str],
    ttl: bool, incrementar: bool,
) -> None:
    agora = datetime.utcnow()
    doc: Dict[str, Any] = {
        "user_id": user_id,
        "event": event,
        "ip": ip,
        "user_agent": (user_agent or "")[:400],
        "created_at": agora,
    }
    # Só heartbeats recebem `expira_em`; o índice TTL ignora docs sem o campo,
    # então login/logout ficam permanentes.
    if ttl:
        doc["expira_em"] = agora + timedelta(days=DIAS_RETENCAO_HEARTBEAT)

    await db.user_access_log.insert_one(doc)

    update: Dict[str, Any] = {"$set": {"last_login_at": agora}}
    if incrementar:
        update["$inc"] = {"login_count": 1}
    await db.users.update_one({"id": user_id}, update)


async def registrar_login(
    db, user_id: str, ip: Optional[str] = None, user_agent: Optional[str] = None
) -> None:
    """Evento permanente. Só ele incrementa `login_count`."""
    try:
        _ultimo_heartbeat[user_id] = datetime.utcnow()
        await _gravar(db, user_id, "login", ip, user_agent, ttl=False, incrementar=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("acesso_log: falha ao registrar login de %s: %s", user_id, e)


async def registrar_heartbeat(
    db, user_id: str, ip: Optional[str] = None, user_agent: Optional[str] = None
) -> None:
    """Evento efêmero (TTL). Throttled em MINUTOS_THROTTLE_HEARTBEAT."""
    try:
        agora = datetime.utcnow()
        anterior = _ultimo_heartbeat.get(user_id)
        if anterior and (agora - anterior) < timedelta(minutes=MINUTOS_THROTTLE_HEARTBEAT):
            return
        _ultimo_heartbeat[user_id] = agora
        await _gravar(
            db, user_id, "session_heartbeat", ip, user_agent, ttl=True, incrementar=False
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("acesso_log: falha ao registrar heartbeat de %s: %s", user_id, e)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && py -m pytest tests/test_auditoria_acesso.py -v`
Expected: PASS (12 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/acesso_log.py backend/tests/test_auditoria_acesso.py
git commit -m "feat(auditoria): servico de log de acesso com throttle e TTL"
```

---

### Task 3: Serviço append-only de eventos de pagamento

**Files:**
- Create: `backend/services/payment_events.py`
- Modify: `backend/tests/test_auditoria_acesso.py` (acrescentar ao final)

- [ ] **Step 1: Write the failing test**

Acrescentar ao final de `backend/tests/test_auditoria_acesso.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && py -m pytest tests/test_auditoria_acesso.py -v`
Expected: FAIL com `ImportError: cannot import name 'payment_events' from 'services'`

- [ ] **Step 3: Write minimal implementation**

Criar `backend/services/payment_events.py`:

```python
# @module services.payment_events — log APPEND-ONLY dos webhooks do Mercado Pago.
# Nunca é editado. É a fonte de auditoria para reconstruir o funil e investigar
# "o cliente pagou e não ativou". Complementa (não substitui) `transactions`,
# que registra apenas compras aprovadas.
import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def registrar(
    db, user_id: Optional[str], pagamento: Dict[str, Any], plan_id: Optional[str]
) -> bool:
    """Grava um evento de pagamento. Retorna True se gravou, False se ignorou/falhou.

    Idempotente: um mesmo (mp_payment_id, status) só entra uma vez, mas transições
    de status do mesmo pagamento geram linhas novas (é um log, não um estado).
    """
    try:
        mp_id = str(pagamento.get("id") or "")
        status = (pagamento.get("status") or "").lower()
        if not mp_id:
            logger.warning("payment_events: pagamento sem id, ignorado")
            return False

        ja = await db.payment_events.find_one({"mp_payment_id": mp_id, "status": status})
        if ja:
            return False

        await db.payment_events.insert_one({
            "user_id": user_id,
            "plan_id": plan_id,
            "mp_payment_id": mp_id,
            "status": status,
            "status_detail": pagamento.get("status_detail"),
            "transaction_amount": pagamento.get("transaction_amount"),
            "raw_payload": pagamento,
            "received_at": datetime.utcnow(),
        })
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("payment_events: falha ao registrar evento: %s", e)
        return False


async def ultimo_por_usuario(db, user_id: str) -> Optional[Dict[str, Any]]:
    """Evento mais recente do usuário, ou None."""
    try:
        return await db.payment_events.find_one(
            {"user_id": user_id}, sort=[("received_at", -1)]
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("payment_events: falha ao ler ultimo evento: %s", e)
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && py -m pytest tests/test_auditoria_acesso.py -v`
Expected: PASS (17 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/payment_events.py backend/tests/test_auditoria_acesso.py
git commit -m "feat(auditoria): log append-only de eventos do Mercado Pago"
```

---

### Task 4: Índices no startup

**Files:**
- Modify: `backend/server.py` (bloco `@app.on_event("startup")`, junto dos índices de `users` em ~`:595`)

- [ ] **Step 1: Localizar o bloco de índices**

Run: `cd backend && grep -n "reset_token_hash" server.py`
Expected: uma linha dentro do bloco de índices de `users` no startup.

- [ ] **Step 2: Acrescentar os índices**

Logo após o bloco de índices de `users`, inserir:

```python
    # ── Auditoria de acesso e pagamento ──────────────────────────────────────
    try:
        # TTL: expira só docs COM `expira_em` (heartbeats). Login/logout, que não
        # têm o campo, ficam permanentes.
        await db.user_access_log.create_index("expira_em", expireAfterSeconds=0)
        await db.user_access_log.create_index([("user_id", 1), ("created_at", -1)])
    except Exception as e:
        logger.warning("Indices user_access_log: %s", e)

    try:
        await db.payment_events.create_index([("user_id", 1), ("received_at", -1)])
        # Composto: uma linha por transição de status; bloqueia duplicata real.
        await db.payment_events.create_index(
            [("mp_payment_id", 1), ("status", 1)], unique=True
        )
    except Exception as e:
        logger.warning("Indices payment_events: %s", e)

    try:
        # COMPOSTO, não simples: o Task 8B passa a gravar uma linha por transição
        # de status (pending -> approved). Um unique só em mp_payment_id
        # QUEBRARIA a ativação de boleto/PIX.
        await db.transactions.create_index(
            [("mp_payment_id", 1), ("status", 1)], unique=True
        )
    except Exception as e:
        logger.warning(
            "Indice unique transactions.(mp_payment_id,status) nao criado "
            "(provavel duplicata pre-existente): %s", e
        )
```

- [ ] **Step 3: Verificar que o app importa**

Run: `cd backend && py -c "import server; print('ok', len(server.app.routes))"`
Expected: `ok <n>` sem traceback.

- [ ] **Step 4: Commit**

```bash
git add backend/server.py
git commit -m "feat(auditoria): indices TTL e unicidade para acesso e eventos de pagamento"
```

---

### Task 5: Hook de login

**Files:**
- Modify: `backend/routes/auth.py` (rota de login, ~`:99-136`)

- [ ] **Step 1: Inspecionar a assinatura da rota**

Run: `cd backend && sed -n '95,140p' routes/auth.py`
Expected: ver a rota de login, o `create_token(u["id"])` e se há `Request` no parâmetro.

- [ ] **Step 2: Importar o serviço**

No topo de `backend/routes/auth.py`, junto dos demais imports de services:

```python
from services import acesso_log
```

- [ ] **Step 3: Registrar o evento após o login bem-sucedido**

Imediatamente antes do `return` que devolve o token (após o update que zera `failed_logins`), inserir:

```python
    # Auditoria de acesso (best-effort — nunca bloqueia o login)
    await acesso_log.registrar_login(
        db, u["id"],
        ip=(request.client.host if request and request.client else None),
        user_agent=request.headers.get("user-agent") if request else None,
    )
```

**Nota:** a rota já recebe `request: Request` por causa do `@limiter.limit` do slowapi (o slowapi exige esse parâmetro). Confirme no Step 1; se por algum motivo não houver, acrescente `request: Request` à assinatura.

- [ ] **Step 4: Verificar import**

Run: `cd backend && py -c "import routes.auth; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add backend/routes/auth.py
git commit -m "feat(auditoria): registra evento de login"
```

---

### Task 6: Hook de heartbeat

**Files:**
- Modify: `backend/dependencies.py:8-41`

- [ ] **Step 1: Ler o arquivo**

Run: `cd backend && sed -n '1,50p' dependencies.py`
Expected: ver `get_active_subscriber` e `get_authenticated_user`.

- [ ] **Step 2: Importar e criar o helper**

No topo de `backend/dependencies.py`:

```python
import asyncio
```

E, antes de `get_active_subscriber`, adicionar:

```python
def _heartbeat(db, uid: str) -> None:
    """Dispara o heartbeat sem bloquear a resposta (fire-and-forget).

    Importado aqui dentro para evitar import circular com services.
    """
    try:
        from services import acesso_log
        asyncio.create_task(acesso_log.registrar_heartbeat(db, uid))
    except Exception:  # noqa: BLE001
        pass
```

- [ ] **Step 3: Chamar nos dois pontos de estrangulamento**

Em `get_active_subscriber`, imediatamente antes de cada `return uid` que representa acesso concedido (o do bypass de admin e o final), e em `get_authenticated_user` antes do `return uid`, inserir:

```python
    _heartbeat(db, uid)
```

**Importante:** não chamar antes dos `raise HTTPException` — request negada não é acesso.

- [ ] **Step 4: Verificar import**

Run: `cd backend && py -c "import dependencies; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add backend/dependencies.py
git commit -m "feat(auditoria): heartbeat de sessao nas dependencies de acesso"
```

---

### Task 7: Marcar início de checkout

**Files:**
- Modify: `backend/routes/payments.py:29-41` (rota `create_preference`)

`datetime` (`:5`) e `logger` (`:26`) **já estão importados** — não reimportar.

- [ ] **Step 1: Injetar o `db` na rota**

A rota hoje **não recebe `db`**. Substituir a assinatura em `:31`:

```python
async def create_preference(request: Request, data: CreatePreferenceRequest, uid: str = Depends(get_current_user_id)):
```

por:

```python
async def create_preference(request: Request, data: CreatePreferenceRequest, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
```

(`get_db` já está importado em `:10`.)

- [ ] **Step 2: Gravar a intenção de pagamento**

Substituir as linhas `:40-41`:

```python
    logger.info("MP preference created: %s for user=%s plan=%s", response.get("id"), uid, data.plan_id)
    return {"init_point": init_point, "preference_id": response.get("id")}
```

por:

```python
    logger.info("MP preference created: %s for user=%s plan=%s", response.get("id"), uid, data.plan_id)
    # Topo do funil: marca a INTENÇÃO de pagar. Diagnóstico apenas — não concede
    # nem promete acesso (quem decide isso é plan_status).
    try:
        await db.users.update_one(
            {"id": uid},
            {"$set": {
                "checkout_started_at": datetime.utcnow(),
                "checkout_preference_id": str(response.get("id") or ""),
                "checkout_plan_id": data.plan_id,
            }},
        )
    except Exception as e:
        logger.warning("checkout_started nao gravado para %s: %s", uid, e)
    return {"init_point": init_point, "preference_id": response.get("id")}
```

- [ ] **Step 3: Verificar import**

Run: `cd backend && py -c "import routes.payments; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/routes/payments.py
git commit -m "feat(auditoria): registra inicio de checkout na criacao da preference"
```

---

### Task 8: Auditar o webhook (append-only, sem alterar comportamento)

**Files:**
- Modify: `backend/routes/payments.py:44-117` (webhook)

- [ ] **Step 1: Importar**

Após `:17` (`from models import CreatePreferenceRequest, Transaction`), acrescentar:

```python
from models.auditoria_acesso import derivar_status_funil
from services import payment_events
```

- [ ] **Step 2: Gravar TODO evento, antes dos returns antecipados**

Inserir logo após `:70` (o `logger.info("MP payment id=%s ...")`) e **antes** do `existing = await db.transactions.find_one(...)` de `:71`:

```python
    # Auditoria append-only: registra TODO evento — inclusive os que o fluxo
    # abaixo descarta (external_reference inválido, duplicata, status não
    # aprovado). Sem isto, esses casos somem sem rastro (`return {"ok": True}`).
    _parts_audit = external_ref.split("|", 1)
    _uid_audit = _parts_audit[0] if len(_parts_audit) == 2 else None
    _plan_audit = _parts_audit[1] if len(_parts_audit) == 2 else None
    await payment_events.registrar(db, _uid_audit, payment, _plan_audit)
```

- [ ] **Step 3: Espelhar o status de funil (diagnóstico)**

Inserir imediatamente antes do `return {"ok": True}` final da função (`:117`), no mesmo nível de indentação do `if payment_status == "approved":` de `:82`:

```python
    # Campo DIAGNÓSTICO. Não gateia nada — quem decide acesso é plan_status.
    try:
        if _uid_audit:
            u_atual = await db.users.find_one({"id": _uid_audit})
            if u_atual:
                ultimo = await payment_events.ultimo_por_usuario(db, _uid_audit)
                await db.users.update_one(
                    {"id": _uid_audit},
                    {"$set": {"subscription_status": derivar_status_funil(u_atual, ultimo)}},
                )
    except Exception as e:
        logger.warning("subscription_status nao atualizado para %s: %s", _uid_audit, e)
```

**Não remover, não reordenar e não condicionar** o `send_payment_email` (`:89`) nem o `notify_lead` (`:99`).

- [ ] **Step 4: Verificar import**

Run: `cd backend && py -c "import routes.payments; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add backend/routes/payments.py
git commit -m "feat(auditoria): grava eventos do webhook MP e status de funil diagnostico"
```

---

### Task 8B: BUG — boleto/PIX pago nunca ativa o plano

**Files:**
- Modify: `backend/routes/payments.py:71-73`
- Modify: `backend/tests/test_auditoria_acesso.py`

**O defeito.** A dedupe de `:71` casa só por `mp_payment_id`, ignorando o status:

```
Webhook 1  status=pending   -> :71 nada encontrado -> insere transaction(pending) -> :82 não aprova -> fim
Cliente paga o boleto
Webhook 2  status=approved  -> :71 ENCONTRA a transaction pending -> :73 return -> NUNCA ATIVA
```

Como `build_preference_data` usa `"excluded_payment_types": []` ([mercadopago_service.py:53](backend/services/mercadopago_service.py:53)), boleto e PIX estão liberados e **sempre** entram por `pending`. Cartão à vista escapa porque já chega `approved`; cartão em análise (`in_process`) cai no mesmo buraco.

- [ ] **Step 1: Write the failing test**

Acrescentar ao final de `backend/tests/test_auditoria_acesso.py`:

```python
# ── Regressão: PIX/boleto (pending -> approved) precisa ativar o plano ──────
# Exercita o HANDLER REAL `routes.payments.payment_webhook`. O único ponto
# falsificado é o SDK do Mercado Pago — todo o resto é o código de produção.
import routes.payments as pay


class _FakeQueryParams:
    def get(self, k, default=None):
        return default          # sem token na query


class _FakeRequest:
    def __init__(self, body):
        self._body = body
        self.query_params = _FakeQueryParams()

    async def json(self):
        return self._body


class _CollTxn:
    def __init__(self):
        self.docs = []
    async def find_one(self, flt, **kw):
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items()):
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


def _sdk_com_status(status):
    """SDK falso que devolve o pagamento 55 no status pedido."""
    class _SDK:
        def payment(self):
            return self
        def get(self, rid):
            return {"response": {
                "id": 55, "status": status, "status_detail": "ok",
                "external_reference": "u1|mensal", "transaction_amount": 89.9,
            }}
    return _SDK()


def test_pix_pago_ativa_o_plano_no_segundo_webhook(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_TOKEN", "")
    monkeypatch.setattr(pay, "send_payment_email", lambda *a, **kw: None)

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
    monkeypatch.setattr(pay, "send_payment_email", lambda *a, **kw: None)

    user = {"id": "u1", "name": "F", "email": "f@x.com", "plan_status": "inactive"}
    db = _DBWebhook(user)
    body = {"type": "payment", "data": {"id": 55}}
    monkeypatch.setattr(pay, "get_mp_sdk", lambda: _sdk_com_status("approved"))

    asyncio.run(pay.payment_webhook(_FakeRequest(body), db))
    asyncio.run(pay.payment_webhook(_FakeRequest(body), db))
    assert len(db.transactions.docs) == 1, "mesmo evento nao pode duplicar"
```

**Nota sobre `notify_lead`:** ele é importado *dentro* da função (`payments.py:98`) e disparado via `asyncio.create_task`. Sob `asyncio.run` a task é cancelada no fim do loop sem executar I/O real. Se a suíte reclamar de task pendente, adicionar
`monkeypatch.setattr("services.zayra_webhook.notify_lead", lambda *a, **kw: None)`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && py -m pytest tests/test_auditoria_acesso.py -k pix -v`
Expected: **FAIL** em `REGRESSAO: pagamento aprovado apos pending nao ativou o plano` — é o bug reproduzido contra o código real.

- [ ] **Step 3: Corrigir a dedupe**

Substituir `:71-73`:

```python
    existing = await db.transactions.find_one({"mp_payment_id": mp_payment_id})
    if existing:
        return {"ok": True}
```

por:

```python
    # Dedupe por (id, status): o MESMO evento é duplicata, mas uma TRANSIÇÃO de
    # status (pending -> approved, típica de boleto/PIX) precisa seguir adiante,
    # senão o cliente paga e nunca é ativado.
    existing = await db.transactions.find_one(
        {"mp_payment_id": mp_payment_id, "status": payment_status}
    )
    if existing:
        return {"ok": True}
```

- [ ] **Step 4: Verificar import e suíte**

Run: `cd backend && py -c "import routes.payments; print('ok')" && py -m pytest tests/test_auditoria_acesso.py -q`
Expected: `ok` e todos os testes passando.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/payments.py backend/tests/test_auditoria_acesso.py
git commit -m "fix(payments): boleto/PIX pago nao ativava o plano (dedupe ignorava transicao de status)"
```

**Validação manual obrigatória pós-deploy:** rodar um pagamento real por PIX em valor baixo e confirmar que `plan_status` vira `active` no segundo webhook. Este é o caminho que estava quebrado — merece teste de ponta a ponta, não só unitário.

---

### Task 9: Endpoints de auditoria

**Files:**
- Modify: `backend/routes/admin.py` (após `admin_list_users`, ~`:102`)

- [ ] **Step 1: Imports**

No topo de `backend/routes/admin.py`:

```python
from models.auditoria_acesso import AuditoriaUsuarioOut, TimelineOut, derivar_status_funil
```

- [ ] **Step 2: Endpoint de auditoria consolidada**

Acrescentar após `admin_list_users`:

```python
@router.get("/admin/users/audit", response_model=List[AuditoriaUsuarioOut])
async def admin_users_audit(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Funil de acesso e pagamento de todos os usuários. Somente leitura."""
    users = await db.users.find({}).sort("created_at", -1).to_list(5000)
    ids = [u["id"] for u in users]

    # Último evento de pagamento por usuário, em UMA passada (evita N+1).
    ultimo_por_uid = {}
    cursor = db.payment_events.find({"user_id": {"$in": ids}}).sort("received_at", 1)
    async for ev in cursor:
        ultimo_por_uid[ev["user_id"]] = ev  # sort ascendente ⇒ sobra o mais recente

    saida = []
    for u in users:
        ev = ultimo_por_uid.get(u["id"])
        saida.append(AuditoriaUsuarioOut(
            id=u["id"],
            name=u.get("name") or "",
            email=u.get("email") or "",
            role=u.get("role") or "",
            cadastrado_em=u.get("created_at"),
            ultimo_acesso=u.get("last_login_at"),
            total_acessos=int(u.get("login_count") or 0),
            nunca_acessou=not u.get("last_login_at"),
            plan=u.get("plan") or "",
            plan_status=u.get("plan_status") or "",
            plan_expires=u.get("plan_expires"),
            status_funil=derivar_status_funil(u, ev),
            checkout_iniciado_em=u.get("checkout_started_at"),
            ultimo_evento_pagamento=({
                "status": ev.get("status"),
                "status_detail": ev.get("status_detail"),
                "em": ev.get("received_at"),
            } if ev else None),
        ))
    return saida
```

- [ ] **Step 3: Endpoint de timeline**

```python
@router.get("/admin/users/{user_id}/timeline", response_model=TimelineOut)
async def admin_user_timeline(
    user_id: str, uid: str = Depends(get_admin_user), db=Depends(get_db)
):
    """Linha do tempo de acessos e pagamentos de um usuário."""
    acessos = await db.user_access_log.find({"user_id": user_id}) \
        .sort("created_at", -1).to_list(50)
    pagamentos = await db.payment_events.find({"user_id": user_id}) \
        .sort("received_at", -1).to_list(200)
    return TimelineOut(
        acessos=[serialize_doc(a) for a in acessos],
        pagamentos=[serialize_doc(p) for p in pagamentos],
    )
```

**Atenção à ordem de registro das rotas:** `/admin/users/audit` precisa ser declarada **antes** de qualquer rota `/admin/users/{algo}` existente, senão o FastAPI casa `audit` como `{user_id}`. Confirme com o Step 4.

- [ ] **Step 4: Verificar rotas e ausência de conflito**

Run: `cd backend && py -c "import server; [print(r.path) for r in server.app.routes if '/admin/users' in getattr(r,'path','')]"`
Expected: `/api/admin/users`, `/api/admin/users/audit`, `/api/admin/users/{user_id}/timeline` — com `audit` aparecendo **antes** de qualquer rota parametrizada de mesmo prefixo.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/admin.py
git commit -m "feat(auditoria): endpoints admin de auditoria e timeline por usuario"
```

---

### Task 10: Suíte completa, versionamento e deploy

**Files:**
- Modify: `frontend/build-number.txt`
- Modify: `Dockerfile` (variável `CACHEBUST_BACKEND`)

- [ ] **Step 1: Rodar a suíte inteira**

Run: `cd backend && py -m pytest tests/ -q`
Expected: os 18 testes novos de `test_auditoria_acesso.py` passam; nenhuma regressão nos existentes. A falha pré-existente `test_texto_ia` é conhecida e não conta.

- [ ] **Step 2: Verificar que o app sobe**

Run: `cd backend && py -c "import server; print('routers ok')"`
Expected: `routers ok`

- [ ] **Step 3: Bump do build-number (OBRIGATÓRIO — regra do CLAUDE.md)**

Ler o valor atual de `frontend/build-number.txt` e gravar valor + 1.

- [ ] **Step 4: Bump do CACHEBUST_BACKEND**

Alterar o valor de `CACHEBUST_BACKEND` no `Dockerfile` para a data de hoje com sufixo incremental (mudança é backend-only, então `CACHEBUST` do frontend não precisa mudar nesta fase).

- [ ] **Step 5: Commit**

```bash
git add frontend/build-number.txt Dockerfile
git commit -m "chore(auditoria): v1.4.<build> — auditoria de acesso e pagamento (backend)"
```

---

## Como validar em produção depois do deploy

1. **Login próprio** → `GET /api/admin/users/audit` deve mostrar `total_acessos: 1` e `ultimo_acesso` preenchido para a sua conta.
2. **Navegar 3 telas em 5 minutos** → `total_acessos` **não** muda (heartbeat não conta) e a timeline mostra **um** `session_heartbeat`.
3. **Abrir o checkout sem pagar** → `status_funil` vira `checkout_started` e `checkout_iniciado_em` é preenchido.
4. **Os 6 usuários atuais** aparecem com `nunca_acessou: true` e `status_funil: never_started` até acessarem — é o diagnóstico que o módulo existe para dar.
5. **Conferir nos logs do Railway** se o índice único de `transactions.mp_payment_id` foi criado ou se acusou duplicata pré-existente (mensagem do Task 4).

## Fora de escopo (Fase 2 e follow-ups)

- **Frontend:** colunas, badges, drawer de timeline e cards "Nunca acessaram"/"Abandonaram no checkout" em `frontend/src/pages/admin/UsuariosAdmin.jsx`.
- **Reenviar link de pagamento:** depende de corrigir `POST /subscription/change` ([payments.py:161](backend/routes/payments.py:161)), que hoje altera o plano **do próprio admin**, não do usuário-alvo.
- **`setup_indexes()` morto** em [db.py:28](backend/db.py:28) — nunca é chamado; índices de ptam_versions, contratos e cupons não existem em produção.
- **Assinatura HMAC `x-signature`** do Mercado Pago no webhook (hoje só há token em query param).
- **Renovação não acumula** tempo restante do plano vigente ([mercadopago_service.py:66](backend/services/mercadopago_service.py:66)).
