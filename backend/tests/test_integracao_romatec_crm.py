# @module tests.test_integracao_romatec_crm — Integração Romatec CRM → AvalieImob
# (provisionamento HMAC + SSO de uso único), via HTTP com DB falso.
#
# Regras cobertas:
#   - segredo ausente → 503; assinatura errada / timestamp velho → 401.
#   - ativar cria o usuário; ativar em quem tem plano próprio MAIS LONGO não encurta.
#   - suspender só atinge plan_origem "romatec_crm".
#   - SSO válido → token + user; jti reaproveitado → 401; aud errado/expirado → 401;
#     usuário suspenso → 403.
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

from db import get_db
from routes.integracoes_romatec import router
from services import acesso_log
from services import romatec_crm_integracao as RC
from services.auth_service import decode_token
from tests.test_trial_acesso import _Coll

SEGREDO = "segredo-de-teste-romatec-crm"


class _CollUnica(_Coll):
    """Coleção falsa com índice único num campo (emula sso_jti_usados.jti)."""

    def __init__(self, campo):
        super().__init__()
        self._campo = campo

    async def insert_one(self, doc):
        if any(d.get(self._campo) == doc.get(self._campo) for d in self.docs):
            raise DuplicateKeyError("duplicado")
        return await super().insert_one(doc)


class _CollUsers(_Coll):
    """Coleção falsa com suporte a $unset (plano_proprio)."""

    async def update_one(self, f, upd, upsert=False):
        r = await super().update_one(f, {k: v for k, v in upd.items() if k != "$unset"}, upsert)
        if upd.get("$unset"):
            for d in self.docs:
                if all(d.get(k) == v for k, v in f.items()):
                    for k in upd["$unset"]:
                        d.pop(k, None)
        return r


class _DB:
    def __init__(self):
        self.users = _CollUsers()
        self.sso_jti_usados = _CollUnica("jti")
        self.user_access_log = _Coll()


@pytest.fixture()
def cliente(monkeypatch):
    monkeypatch.setenv(RC.ENV_SEGREDO, SEGREDO)
    acesso_log.limpar_cache_throttle()
    fake = _DB()
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: fake
    with TestClient(app) as c:
        c.fake = fake
        yield c


# ── Helpers ──────────────────────────────────────────────────────────────────
def _payload(**kw):
    p = {"evento": "ativar", "crm_usuario_id": 42, "email": "Maria@Exemplo.com",
         "nome": "Maria Souza", "cpf": "12345678909", "telefone": "5599991112222",
         "plano": "pro", "ate": None}
    p.update(kw)
    return p


def _provisionar(c, payload, *, segredo=SEGREDO, ts=None, assinatura=None):
    corpo = json.dumps(payload).encode("utf-8")
    ts = str(int(time.time())) if ts is None else str(ts)
    sig = assinatura or RC.assinar(segredo, ts, corpo)
    return c.post("/api/integracoes/romatec/provisionar", content=corpo, headers={
        "Content-Type": "application/json",
        "X-Romatec-Timestamp": ts, "X-Romatec-Signature": sig})


def _jwt(sub="42", email="maria@exemplo.com", segredo=SEGREDO, **kw):
    agora = int(time.time())
    claims = {"iss": "romatec-crm", "aud": "avalieimob", "sub": sub, "email": email,
              "nome": "Maria Souza", "jti": str(uuid.uuid4()), "iat": agora, "exp": agora + 60}
    claims.update(kw)
    return jwt.encode(claims, segredo, algorithm="HS256")


def _sso(c, token):
    return c.post("/api/integracoes/romatec/sso", json={"token": token})


def _user(c, **filtro):
    return next(d for d in c.fake.users.docs if all(d.get(k) == v for k, v in filtro.items()))


# ── Provisionamento: autenticação ────────────────────────────────────────────
def test_sem_segredo_responde_503(cliente, monkeypatch):
    monkeypatch.delenv(RC.ENV_SEGREDO, raising=False)
    r = _provisionar(cliente, _payload())
    assert r.status_code == 503
    assert r.json()["detail"] == "Integração com o Romatec CRM não configurada"
    r = _sso(cliente, _jwt())
    assert r.status_code == 503


def test_segredo_vazio_responde_503(cliente, monkeypatch):
    monkeypatch.setenv(RC.ENV_SEGREDO, "   ")
    assert _provisionar(cliente, _payload()).status_code == 503


def test_assinatura_errada_401(cliente):
    r = _provisionar(cliente, _payload(), segredo="outro-segredo")
    assert r.status_code == 401
    assert cliente.fake.users.docs == []


def test_assinatura_sobre_corpo_adulterado_401(cliente):
    corpo = json.dumps(_payload()).encode()
    ts = str(int(time.time()))
    sig = RC.assinar(SEGREDO, ts, corpo)
    adulterado = json.dumps(_payload(email="intruso@x.com")).encode()
    r = cliente.post("/api/integracoes/romatec/provisionar", content=adulterado, headers={
        "Content-Type": "application/json", "X-Romatec-Timestamp": ts, "X-Romatec-Signature": sig})
    assert r.status_code == 401


def test_headers_ausentes_401(cliente):
    r = cliente.post("/api/integracoes/romatec/provisionar", json=_payload())
    assert r.status_code == 401


def test_timestamp_velho_401(cliente):
    r = _provisionar(cliente, _payload(), ts=int(time.time()) - 301)
    assert r.status_code == 401
    r = _provisionar(cliente, _payload(), ts=int(time.time()) + 301)
    assert r.status_code == 401


def test_corpo_invalido_422(cliente):
    r = _provisionar(cliente, {"evento": "apagar", "crm_usuario_id": "x"})
    assert r.status_code == 422


# ── Provisionamento: regras ──────────────────────────────────────────────────
def test_ativar_cria_usuario(cliente):
    r = _provisionar(cliente, _payload(ate="2027-01-31T23:59:59Z"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["acao"] == "criado" and body["user_id"]
    u = _user(cliente, id=body["user_id"])
    assert u["email"] == "maria@exemplo.com" and u["name"] == "Maria Souza"
    assert u["role"] == "user"
    assert u["plan"] == "romatec_crm" and u["plan_status"] == "active"
    assert u["plan_origem"] == "romatec_crm" and u["romatec_crm_id"] == 42
    assert u["plan_expires"] == datetime(2027, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
    assert u["password_hash"] and u["phone"] == "5599991112222"
    assert u.get("created_at") is not None

    # Idempotente: repetir o evento não duplica o usuário.
    r = _provisionar(cliente, _payload(ate="2027-01-31T23:59:59Z"))
    assert r.json()["acao"] == "ativado" and r.json()["user_id"] == body["user_id"]
    assert len(cliente.fake.users.docs) == 1


def test_ativar_sem_ate_vale_ate_2099(cliente):
    r = _provisionar(cliente, _payload(ate=None))
    u = _user(cliente, id=r.json()["user_id"])
    assert u["plan_expires"] == datetime(2099, 12, 31, tzinfo=timezone.utc)


def test_ativar_vincula_por_email_e_nao_encurta_plano_proprio(cliente):
    longe = datetime.now(timezone.utc) + timedelta(days=300)
    cliente.fake.users.docs.append({
        "id": "u1", "name": "Maria", "email": "maria@exemplo.com", "role": "Profissional",
        "plan": "anual", "plan_status": "active", "plan_expires": longe.replace(tzinfo=None),
        "password_hash": "HASH"})
    ate = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    r = _provisionar(cliente, _payload(ate=ate))
    assert r.status_code == 200 and r.json() == {"ok": True, "acao": "ativado", "user_id": "u1"}
    u = _user(cliente, id="u1")
    assert u["romatec_crm_id"] == 42                       # vinculado pelo e-mail
    assert abs((u["plan_expires"] - longe).total_seconds()) < 1   # não encurtou
    assert u["role"] == "Profissional" and u["password_hash"] == "HASH"
    assert u["plan_status"] == "active" and u["plan_origem"] == "romatec_crm"


def test_suspender_devolve_plano_proprio_guardado_na_ativacao(cliente):
    longe = datetime.now(timezone.utc) + timedelta(days=120)
    cliente.fake.users.docs.append({
        "id": "u1", "name": "Maria", "email": "maria@exemplo.com", "role": "Profissional",
        "plan": "anual", "plan_origem": "mercadopago", "plan_status": "active", "plan_expires": longe})
    assert _provisionar(cliente, _payload()).json()["acao"] == "ativado"   # sem data → 2099
    u = _user(cliente, id="u1")
    assert u["plan_origem"] == "romatec_crm" and u["plano_proprio"]["plan"] == "anual"
    # Reativar não sobrescreve o plano guardado
    _provisionar(cliente, _payload(evento="reativar"))
    assert _user(cliente, id="u1")["plano_proprio"]["plan_origem"] == "mercadopago"
    r = _provisionar(cliente, _payload(evento="suspender"))
    assert r.json() == {"ok": True, "acao": "restaurado_plano_proprio", "user_id": "u1"}
    u = _user(cliente, id="u1")
    assert u["plan"] == "anual" and u["plan_origem"] == "mercadopago" and u["plan_status"] == "active"
    assert abs((u["plan_expires"] - longe).total_seconds()) < 1 and "plano_proprio" not in u
    # Agora o plano é próprio: novo suspender não mexe
    assert _provisionar(cliente, _payload(evento="suspender")).json()["acao"] == "ignorado_plano_proprio"


def test_suspender_com_plano_proprio_ja_vencido_expira(cliente):
    cliente.fake.users.docs.append({
        "id": "u1", "email": "maria@exemplo.com", "role": "user", "romatec_crm_id": 42,
        "plan": "romatec_crm", "plan_origem": "romatec_crm", "plan_status": "active",
        "plan_expires": datetime(2099, 12, 31, tzinfo=timezone.utc),
        "plano_proprio": {"plan": "mensal", "plan_origem": "mercadopago",
                          "plan_expires": datetime.now(timezone.utc) - timedelta(days=1)}})
    assert _provisionar(cliente, _payload(evento="suspender")).json()["acao"] == "suspenso"
    u = _user(cliente, id="u1")
    assert u["plan_status"] == "expired" and "plano_proprio" not in u


def test_reativar_estende_acesso_vencido(cliente):
    cliente.fake.users.docs.append({
        "id": "u2", "email": "maria@exemplo.com", "role": "user", "romatec_crm_id": 42,
        "plan": "romatec_crm", "plan_origem": "romatec_crm", "plan_status": "expired",
        "plan_expires": datetime(2030, 1, 1)})
    r = _provisionar(cliente, _payload(evento="reativar", ate="2027-06-30T00:00:00+00:00"))
    assert r.json()["acao"] == "ativado"
    u = _user(cliente, id="u2")
    # Status não estava ativo → vale a nova data (não o vencimento antigo).
    assert u["plan_status"] == "active"
    assert u["plan_expires"] == datetime(2027, 6, 30, tzinfo=timezone.utc)


def test_suspender_so_afeta_origem_romatec_crm(cliente):
    futuro = datetime.now(timezone.utc) + timedelta(days=100)
    cliente.fake.users.docs.extend([
        {"id": "crm", "email": "crm@x.com", "role": "user", "romatec_crm_id": 1,
         "plan": "romatec_crm", "plan_origem": "romatec_crm", "plan_status": "active",
         "plan_expires": futuro},
        {"id": "proprio", "email": "proprio@x.com", "role": "user", "romatec_crm_id": 2,
         "plan": "anual", "plan_status": "active", "plan_expires": futuro},
        {"id": "adm", "email": "adm@x.com", "role": "admin", "romatec_crm_id": 3,
         "plan": "romatec_crm", "plan_origem": "romatec_crm", "plan_status": "active",
         "plan_expires": futuro},
    ])
    r = _provisionar(cliente, _payload(evento="suspender", crm_usuario_id=1, email="crm@x.com"))
    assert r.json() == {"ok": True, "acao": "suspenso", "user_id": "crm"}
    assert _user(cliente, id="crm")["plan_status"] == "expired"

    r = _provisionar(cliente, _payload(evento="suspender", crm_usuario_id=2, email="proprio@x.com"))
    assert r.json() == {"ok": True, "acao": "ignorado_plano_proprio", "user_id": "proprio"}
    assert _user(cliente, id="proprio")["plan_status"] == "active"

    r = _provisionar(cliente, _payload(evento="suspender", crm_usuario_id=3, email="adm@x.com"))
    assert r.json()["acao"] == "ignorado_plano_proprio"
    assert _user(cliente, id="adm")["plan_status"] == "active"

    r = _provisionar(cliente, _payload(evento="suspender", crm_usuario_id=99, email="nada@x.com"))
    assert r.json() == {"ok": True, "acao": "inexistente", "user_id": None}

    # Idempotente
    r = _provisionar(cliente, _payload(evento="suspender", crm_usuario_id=1, email="crm@x.com"))
    assert r.json()["acao"] == "suspenso"


# ── SSO ──────────────────────────────────────────────────────────────────────
def _provisionado(c):
    r = _provisionar(c, _payload())
    assert r.json()["acao"] == "criado"
    return r.json()["user_id"]


def test_sso_valido_devolve_token_e_usuario(cliente):
    uid = _provisionado(cliente)
    r = _sso(cliente, _jwt())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["id"] == uid and body["user"]["email"] == "maria@exemplo.com"
    assert body["user"]["plan"] == "romatec_crm" and body["user"]["plan_status"] == "active"
    assert decode_token(body["token"]) == uid
    # Acesso registrado como login
    assert any(d["user_id"] == uid and d["event"] == "login"
               for d in cliente.fake.user_access_log.docs)


def test_sso_fallback_por_email(cliente):
    cliente.fake.users.docs.append({
        "id": "u5", "name": "Maria", "email": "maria@exemplo.com", "role": "user",
        "plan": "anual", "plan_status": "active",
        "plan_expires": datetime.now(timezone.utc) + timedelta(days=10)})
    r = _sso(cliente, _jwt(sub="777"))
    assert r.status_code == 200 and r.json()["user"]["id"] == "u5"


def test_sso_jti_reutilizado_401(cliente):
    _provisionado(cliente)
    token = _jwt()
    assert _sso(cliente, token).status_code == 200
    r = _sso(cliente, token)
    assert r.status_code == 401 and r.json()["detail"] == "Link de acesso já utilizado"


@pytest.mark.parametrize("token_kw", [
    {"aud": "outro-sistema"},
    {"iss": "outro-emissor"},
    {"exp": int(time.time()) - 60, "iat": int(time.time()) - 120},
    {"segredo": "segredo-errado"},
    {"exp": int(time.time()) + 3600},          # vida longa demais
    {"sub": "nao-numerico"},
])
def test_sso_token_invalido_401(cliente, token_kw):
    _provisionado(cliente)
    r = _sso(cliente, _jwt(**token_kw))
    assert r.status_code == 401
    assert r.json()["detail"] == "Link de acesso inválido ou expirado"


def test_sso_sem_jti_401(cliente):
    agora = int(time.time())
    token = jwt.encode({"iss": "romatec-crm", "aud": "avalieimob", "sub": "42",
                        "iat": agora, "exp": agora + 60}, SEGREDO, algorithm="HS256")
    assert _sso(cliente, token).status_code == 401


def test_sso_usuario_suspenso_403(cliente):
    _provisionado(cliente)
    _provisionar(cliente, _payload(evento="suspender"))
    r = _sso(cliente, _jwt())
    assert r.status_code == 403
    assert "suspenso" in r.json()["detail"]
    # Sem a palavra que dispara o redirecionamento do axios p/ a tela de planos.
    assert "assinatura" not in r.json()["detail"].lower()


def test_sso_usuario_inexistente_403(cliente):
    r = _sso(cliente, _jwt(sub="5", email="ninguem@x.com"))
    assert r.status_code == 403
    assert r.json()["detail"] == ("Acesso ao AvalieImob ainda não liberado para sua conta "
                                  "do Romatec CRM")
