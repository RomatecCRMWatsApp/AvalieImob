# @module tests.test_admin_leads_cadastros — endpoints da aba "Cadastros" e das notificações.
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_admin_user
from routes.admin_leads import router
from tests.test_trial_acesso import _Coll


class _DB:
    def __init__(self):
        self.users = _Coll()
        self.sys_config = _Coll()
        self.leads_avaliacao = _Coll()
        self.payment_events = _Coll()


@pytest.fixture()
def cliente():
    fake = _DB()
    agora = datetime.utcnow()
    fake.users.docs.extend([
        {"id": "1", "name": "Bing 1", "email": "b1@x.com", "referrer": "https://www.bing.com/",
         "created_at": agora - timedelta(days=1), "plan_status": "inactive"},
        {"id": "2", "name": "Bing 2", "email": "b2@x.com", "referrer": "https://www.bing.com/",
         "created_at": agora - timedelta(days=3), "plan_status": "active", "plan": "mensal"},
        {"id": "3", "name": "Google", "email": "g@x.com", "referrer": "https://www.google.com/",
         "created_at": agora - timedelta(days=5), "plan_status": "active", "plan": "trial",
         "trial": True},
        {"id": "4", "name": "Direto", "email": "d@x.com",
         "created_at": agora - timedelta(days=2), "plan_status": "inactive"},
        {"id": "5", "name": "Antigo", "email": "a@x.com", "referrer": "https://www.google.com/",
         "created_at": agora - timedelta(days=200), "plan_status": "inactive"},
    ])
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_admin_user] = lambda: "admin1"
    with TestClient(app) as c:
        c.fake = fake
        yield c


def test_cadastros_agrupa_por_canal_no_periodo(cliente):
    r = cliente.get("/admin/leads/cadastros?dias=30")
    assert r.status_code == 200, r.text
    d = r.json()
    canais = {c["canal"]: c["total"] for c in d["canais"]}
    assert canais == {"bing": 2, "google": 1, "direto": 1}      # o de 200 dias ficou fora
    assert d["totais"]["cadastros"] == 4
    assert d["totais"]["assinantes"] == 1        # só o plano pago
    assert d["totais"]["em_teste"] == 1          # trial não conta como assinante
    assert d["totais"]["conversao"] == 25.0
    assert d["totais"]["total_base"] == 5        # base inteira, sem filtro de período


def test_cadastros_lista_traz_rotulo_legivel_e_situacao(cliente):
    linhas = cliente.get("/admin/leads/cadastros?dias=30").json()["cadastros"]
    por_email = {c["email"]: c for c in linhas}
    assert por_email["b1@x.com"]["canal_label"] == "Bing (orgânico)"
    assert por_email["g@x.com"]["situacao"] == "em_teste"
    assert por_email["b2@x.com"]["situacao"] == "assinante"
    assert por_email["d@x.com"]["canal"] == "direto"
    assert all("password_hash" not in c for c in linhas)


def test_cadastros_filtra_por_canal_e_busca(cliente):
    so_bing = cliente.get("/admin/leads/cadastros?dias=30&canal=bing").json()
    assert {c["email"] for c in so_bing["cadastros"]} == {"b1@x.com", "b2@x.com"}
    busca = cliente.get("/admin/leads/cadastros?dias=30&q=google").json()
    assert [c["email"] for c in busca["cadastros"]] == ["g@x.com"]


def test_janela_maior_inclui_o_cadastro_antigo(cliente):
    d = cliente.get("/admin/leads/cadastros?dias=365").json()
    assert d["totais"]["cadastros"] == 5


def test_config_de_notificacoes_salva_e_le(cliente):
    r = cliente.get("/admin/leads/notificacoes")
    assert r.status_code == 200 and r.json()["resumo_freq"] == "semanal"

    r = cliente.post("/admin/leads/notificacoes", json={
        "resumo_freq": "diario", "resumo_hora": 8, "email_destino": "Chefe@X.com ",
        "email_lead_ativo": False,
    })
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["resumo_freq"] == "diario" and cfg["resumo_hora"] == 8
    assert cfg["email_destino"] == "chefe@x.com"
    assert cfg["email_lead_ativo"] is False
    assert cliente.get("/admin/leads/notificacoes").json()["resumo_hora"] == 8


def test_hora_invalida_e_recusada_pelo_schema(cliente):
    assert cliente.post("/admin/leads/notificacoes", json={"resumo_hora": 99}).status_code == 422


def test_teste_de_email_de_lead(cliente, monkeypatch):
    enviados = []

    async def _fake(to, lead):
        enviados.append((to, lead))

    import email_service
    monkeypatch.setattr(email_service, "send_lead_email", _fake)
    r = cliente.post("/admin/leads/notificacoes/testar",
                     json={"tipo": "lead", "email": "eu@x.com"})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert enviados[0][0] == "eu@x.com"
    assert enviados[0][1]["nome"].startswith("Maria")


def test_teste_de_resumo_usa_dados_reais(cliente, monkeypatch):
    capturado = {}

    async def _fake(to, dados):
        capturado.update({"to": to, "dados": dados})

    import email_service
    monkeypatch.setattr(email_service, "send_resumo_email", _fake)
    r = cliente.post("/admin/leads/notificacoes/testar",
                     json={"tipo": "resumo", "email": "eu@x.com", "dias": 30})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert capturado["to"] == "eu@x.com"
    assert capturado["dados"]["cadastros"] == 4
