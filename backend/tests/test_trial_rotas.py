# @module tests.test_trial_rotas — endpoints /admin/trials (HTTP, com DB e Z-API falsos).
#
# Cobre o caminho REAL da tela: criar → listar → estender → encerrar → reenviar,
# incluindo a serialização das datas (que já saem como string ISO do serviço).
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_admin_user
from routes.trials import router
from tests.test_trial_acesso import _DB


@pytest.fixture()
def cliente(monkeypatch):
    fake = _DB()

    async def _sem_zapi(db, admin_uid, *, telefone, mensagem):
        return {"ok": True, "telefone": telefone}

    async def _sem_email(email, nome, senha, dias, expira_em):
        return {"ok": True}

    import routes.trials as R
    monkeypatch.setattr(R, "_enviar_whatsapp", _sem_zapi)
    monkeypatch.setattr(R, "_enviar_email", _sem_email)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_admin_user] = lambda: "admin1"
    with TestClient(app) as c:
        c.fake = fake
        yield c


def test_fluxo_completo_do_painel(cliente):
    # 1) cria o login de teste de 7 dias e "envia" por WhatsApp + e-mail
    r = cliente.post("/admin/trials", json={
        "nome": "Cristiano Miola", "email": "cristiano@teste.com", "telefone": "5599991811246",
        "dias": 7, "enviar_whatsapp": True, "enviar_email": True,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["criado"] is True and body["senha_temporaria"]
    assert body["envios"]["whatsapp"]["ok"] and body["envios"]["email"]["ok"]
    assert "Cristiano" in body["mensagem"] and body["senha_temporaria"] in body["mensagem"]
    uid = body["user"]["id"]

    # 2) aparece na lista, com dias restantes e resumo
    r = cliente.get("/admin/trials")
    assert r.status_code == 200
    lista = r.json()
    assert lista["resumo"]["ativos"] == 1 and lista["resumo"]["total"] == 1
    assert lista["trials"][0]["dias_restantes"] == 7
    assert "password_hash" not in lista["trials"][0]

    # 3) estende +3 dias
    r = cliente.post(f"/admin/trials/{uid}/estender", json={"dias": 3})
    assert r.status_code == 200 and r.json()["user"]["dias_restantes"] == 10

    # 4) reenviar credenciais com senha nova
    r = cliente.post(f"/admin/trials/{uid}/reenviar",
                     json={"nova_senha": True, "telefone": "5599991811246"})
    assert r.status_code == 200 and r.json()["senha_temporaria"]

    # 5) encerra na hora
    r = cliente.post(f"/admin/trials/{uid}/encerrar")
    assert r.status_code == 200
    assert r.json()["user"]["situacao"] == "encerrado"
    assert cliente.fake.users.docs[0]["plan_status"] == "expired"


def test_dias_invalidos_retorna_422(cliente):
    r = cliente.post("/admin/trials", json={"email": "x@y.com", "dias": 0})
    assert r.status_code == 422


def test_email_invalido_retorna_422(cliente):
    r = cliente.post("/admin/trials", json={"email": "sem-arroba", "dias": 7})
    assert r.status_code == 422


def test_assinante_pagante_retorna_409(cliente):
    from datetime import datetime, timedelta
    cliente.fake.users.docs.append({
        "id": "pg", "email": "pagante@x.com", "plan": "anual", "plan_status": "active",
        "plan_expires": datetime.utcnow() + timedelta(days=100),
    })
    r = cliente.post("/admin/trials", json={"email": "pagante@x.com", "dias": 7})
    assert r.status_code == 409
    assert "assinatura ativa" in r.json()["detail"]


def test_liberar_para_conta_existente_nao_devolve_senha(cliente):
    cliente.fake.users.docs.append({
        "id": "u9", "name": "Já Cadastrado", "email": "ja@x.com",
        "password_hash": "HASH", "plan_status": "inactive",
    })
    r = cliente.post("/admin/trials", json={"email": "ja@x.com", "dias": 3,
                                            "enviar_email": True})
    assert r.status_code == 201
    body = r.json()
    assert body["criado"] is False and body["senha_temporaria"] is None
    assert cliente.fake.users.docs[0]["password_hash"] == "HASH"
    assert "*Senha:*" not in body["mensagem"]
