# @module tests.test_trial_acesso — Acesso de Teste (trial por N dias)
#
# Regras cobertas:
#   - trial = plan_status "active" + plan_expires no futuro (o gate existente em
#     dependencies.get_active_subscriber expira sozinho — sem cron).
#   - criar login novo OU liberar teste para quem JÁ é cadastrado (sem trocar senha).
#   - NUNCA rebaixar quem tem assinatura PAGA ativa.
#   - estender / encerrar / nova senha / listar.
import asyncio
from datetime import datetime, timedelta

import pytest

from services import trial_service as TS


class _Cur:
    def __init__(self, docs):
        self._d = docs

    def sort(self, key, direction=1):
        self._d = sorted(self._d, key=lambda x: (x.get(key) is None, str(x.get(key) or "")),
                         reverse=direction < 0)
        return self

    async def to_list(self, length=None):
        return [dict(x) for x in self._d]


class _Coll:
    def __init__(self):
        self.docs = []

    def _m(self, d, f):
        for k, v in f.items():
            atual = d.get(k)
            if isinstance(v, dict):
                if "$ne" in v and atual == v["$ne"]:
                    return False
                if "$gte" in v and not (atual is not None and atual >= v["$gte"]):
                    return False
                if "$lt" in v and not (atual is not None and atual < v["$lt"]):
                    return False
                if "$in" in v and atual not in v["$in"]:
                    return False
                if "$exists" in v and (atual is not None) != bool(v["$exists"]):
                    return False
            elif atual != v:
                return False
        return True

    def find(self, f=None, *a, **kw):
        return _Cur([d for d in self.docs if self._m(d, f or {})])

    async def find_one(self, f, *a, **kw):
        return next((dict(d) for d in self.docs if self._m(d, f)), None)

    async def insert_one(self, doc):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("id")})()

    async def update_one(self, f, upd, upsert=False):
        d = next((d for d in self.docs if self._m(d, f)), None)
        if not d:
            if not upsert:
                return type("R", (), {"matched_count": 0, "modified_count": 0})()
            d = {k: v for k, v in f.items() if not isinstance(v, dict)}
            d.update(upd.get("$setOnInsert", {}))
            self.docs.append(d)
        d.update(upd.get("$set", {}))
        for k in (upd.get("$unset") or {}):
            d.pop(k, None)
        for k, v in (upd.get("$push") or {}).items():
            d.setdefault(k, []).append(v)
        return type("R", (), {"matched_count": 1, "modified_count": 1})()


class _DB:
    def __init__(self):
        self.users = _Coll()


def run(coro):
    return asyncio.run(coro)


# ── Funções puras ────────────────────────────────────────────────────────────
def test_senha_temporaria_legivel_e_forte():
    s = TS.gerar_senha_temporaria()
    assert len(s) >= 8
    # sem caracteres ambíguos — a senha é ditada/copiada por WhatsApp
    assert not set(s) & set("0O1lI")


def test_calcular_expiracao_sete_dias():
    agora = datetime(2026, 8, 22, 12, 0, 0)
    assert TS.calcular_expiracao(7, agora) == datetime(2026, 8, 29, 12, 0, 0)


def test_dias_invalidos_sao_rejeitados():
    for d in (0, -3, 400, "abc", None):
        with pytest.raises(ValueError):
            TS.validar_dias(d)
    assert TS.validar_dias("7") == 7


def test_status_trial_em_andamento():
    agora = datetime(2026, 8, 22, 12, 0)
    u = {"trial": True, "trial_dias": 7, "plan": "trial", "plan_status": "active",
         "plan_expires": agora + timedelta(days=3, hours=2)}
    st = TS.status_trial(u, agora)
    assert st["em_trial"] is True and st["expirado"] is False
    assert st["dias_restantes"] == 4       # 3d2h ⇒ arredonda p/ cima
    assert st["situacao"] == "ativo"


def test_status_trial_expirado():
    agora = datetime(2026, 8, 22, 12, 0)
    u = {"trial": True, "trial_dias": 3, "plan": "trial", "plan_status": "active",
         "plan_expires": agora - timedelta(days=1)}
    st = TS.status_trial(u, agora)
    assert st["expirado"] is True and st["dias_restantes"] == 0
    assert st["situacao"] == "expirado"


def test_status_trial_convertido_em_assinante():
    agora = datetime(2026, 8, 22, 12, 0)
    u = {"trial": True, "plan": "mensal", "plan_status": "active",
         "plan_expires": agora + timedelta(days=30)}
    assert TS.status_trial(u, agora)["situacao"] == "convertido"


def test_usuario_sem_trial():
    st = TS.status_trial({"plan_status": "active", "plan": "mensal"}, datetime.utcnow())
    assert st["em_trial"] is False and st["situacao"] == "nao_trial"


def test_mensagem_whatsapp_traz_credenciais_e_prazo():
    msg = TS.montar_mensagem_trial(
        nome="Cristiano", email="cristiano@x.com", senha="Teste-4K7Z", dias=7,
        expira_em=datetime(2026, 8, 29), link="https://www.exemplo.com/login")
    assert "Cristiano" in msg and "cristiano@x.com" in msg
    assert "Teste-4K7Z" in msg and "7 dias" in msg
    assert "29/08/2026" in msg and "https://www.exemplo.com/login" in msg


def test_mensagem_para_quem_ja_tem_conta_nao_expoe_senha():
    msg = TS.montar_mensagem_trial(
        nome="Cristiano", email="c@x.com", senha=None, dias=3,
        expira_em=datetime(2026, 8, 25), link="https://x/login")
    assert "senha" in msg.lower()          # orienta a usar a senha do próprio cadastro
    assert "*Senha:*" not in msg


# ── Criação / liberação ──────────────────────────────────────────────────────
def test_cria_login_novo_com_acesso_de_7_dias():
    db = _DB()
    res = run(TS.criar_ou_liberar_trial(db, "admin1", nome="Novo Cliente",
                                        email=" Novo@Cliente.com ", dias=7))
    assert res["criado"] is True
    assert res["senha_temporaria"]
    u = run(db.users.find_one({"email": "novo@cliente.com"}))
    assert u["plan_status"] == "active"    # o gate de acesso exige "active"
    assert u["plan"] == "trial" and u["trial"] is True
    assert u["trial_dias"] == 7
    assert u["password_hash"] and "senha" not in u   # senha nunca em claro no banco
    assert (u["plan_expires"] - datetime.utcnow()).days in (6, 7)


def test_libera_teste_para_quem_ja_se_cadastrou_sem_trocar_a_senha():
    db = _DB()
    run(db.users.insert_one({"id": "u9", "name": "Cristiano Miola",
                             "email": "cristiano@x.com", "password_hash": "HASH-ORIGINAL",
                             "plan_status": "inactive"}))
    res = run(TS.criar_ou_liberar_trial(db, "admin1", nome="", email="cristiano@x.com", dias=3))
    assert res["criado"] is False
    assert res["senha_temporaria"] is None
    u = run(db.users.find_one({"id": "u9"}))
    assert u["password_hash"] == "HASH-ORIGINAL"
    assert u["plan_status"] == "active" and u["trial"] is True and u["trial_dias"] == 3


def test_nao_rebaixa_assinante_pagante():
    db = _DB()
    run(db.users.insert_one({"id": "p1", "email": "pagante@x.com", "plan": "anual",
                             "plan_status": "active",
                             "plan_expires": datetime.utcnow() + timedelta(days=200)}))
    with pytest.raises(TS.TrialError):
        run(TS.criar_ou_liberar_trial(db, "admin1", nome="", email="pagante@x.com", dias=7))


def test_email_invalido_recusado():
    db = _DB()
    with pytest.raises(ValueError):
        run(TS.criar_ou_liberar_trial(db, "admin1", nome="X", email="sem-arroba", dias=7))


# ── Ações sobre um trial ─────────────────────────────────────────────────────
def test_estender_soma_dias_a_partir_do_vencimento_futuro():
    db = _DB()
    exp = datetime.utcnow() + timedelta(days=2)
    run(db.users.insert_one({"id": "t1", "email": "t@x.com", "trial": True, "trial_dias": 3,
                             "plan": "trial", "plan_status": "active", "plan_expires": exp}))
    run(TS.estender_trial(db, "t1", 5))
    u = run(db.users.find_one({"id": "t1"}))
    assert (u["plan_expires"] - exp).days == 5
    assert u["trial_dias"] == 8


def test_estender_trial_ja_vencido_conta_a_partir_de_agora():
    db = _DB()
    run(db.users.insert_one({"id": "t2", "email": "t2@x.com", "trial": True, "trial_dias": 3,
                             "plan": "trial", "plan_status": "expired",
                             "plan_expires": datetime.utcnow() - timedelta(days=10)}))
    run(TS.estender_trial(db, "t2", 7))
    u = run(db.users.find_one({"id": "t2"}))
    assert u["plan_status"] == "active"
    assert 6 <= (u["plan_expires"] - datetime.utcnow()).days <= 7


def test_encerrar_trial_corta_o_acesso_na_hora():
    db = _DB()
    run(db.users.insert_one({"id": "t3", "email": "t3@x.com", "trial": True, "plan": "trial",
                             "plan_status": "active",
                             "plan_expires": datetime.utcnow() + timedelta(days=5)}))
    run(TS.encerrar_trial(db, "t3"))
    u = run(db.users.find_one({"id": "t3"}))
    assert u["plan_status"] == "expired"
    assert u["plan_expires"] <= datetime.utcnow()


def test_nova_senha_gera_hash_novo():
    db = _DB()
    run(db.users.insert_one({"id": "t4", "email": "t4@x.com", "trial": True,
                             "password_hash": "ANTIGO", "plan_status": "active"}))
    senha = run(TS.redefinir_senha(db, "t4"))
    u = run(db.users.find_one({"id": "t4"}))
    assert senha and u["password_hash"] != "ANTIGO"


def test_listar_traz_dias_restantes_e_situacao():
    db = _DB()
    run(db.users.insert_one({"id": "a", "name": "A", "email": "a@x.com", "trial": True,
                             "plan": "trial", "plan_status": "active", "trial_dias": 7,
                             "trial_inicio": datetime.utcnow(),
                             "plan_expires": datetime.utcnow() + timedelta(days=2)}))
    run(db.users.insert_one({"id": "b", "name": "B", "email": "b@x.com", "plan_status": "active"}))
    lista = run(TS.listar_trials(db))
    assert [t["id"] for t in lista] == ["a"]      # só quem está em teste
    assert lista[0]["dias_restantes"] == 2 and lista[0]["situacao"] == "ativo"
    assert "password_hash" not in lista[0]
