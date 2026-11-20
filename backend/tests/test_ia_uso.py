# @module tests.test_ia_uso — rastreio das chamadas de IA (sem guardar o texto).
import asyncio

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from services import ia_uso
from tests.fake_mongo import FakeDB

PERGUNTA = "Qual o valor do imóvel na Rua Sigilosa, 123? CPF 123.456.789-09"
RESPOSTA = "Resposta com dado sensível XYZ"


@pytest.fixture()
def fake(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(ia_uso, "_db_atual", lambda: db)
    return db


def _prov(resultado):
    async def fn(messages, max_tokens):
        if isinstance(resultado, BaseException):
            raise resultado
        return resultado
    return fn


def _rodar(provs, origem="teste", uid=None):
    async def go():
        ia_uso.definir_usuario(uid)
        return await ia_uso.cascata(provs, [{"role": "user", "content": PERGUNTA}], 500, origem=origem)
    return asyncio.run(go())


def test_registra_tentativas_e_nao_guarda_texto(fake):
    provs = [("groq", _prov(ValueError("sem chave"))), ("gemini", _prov(asyncio.TimeoutError())),
             ("claude", _prov("")), ("openai", _prov(RESPOSTA))]
    reply, prov = _rodar(provs, origem="chat:ptam", uid="conta-A")
    assert (reply, prov) == (RESPOSTA, "openai")
    [doc] = fake.ia_uso.docs
    assert doc["user_id"] == "conta-A" and doc["origem"] == "chat:ptam" and doc["sucesso"]
    assert doc["provedor"] == "openai" and doc["modelo"] == "gpt-4o-mini"
    # provedor sem chave não conta como tentativa; timeout e resposta vazia contam
    assert [(t["provedor"], t["resultado"]) for t in doc["tentativas"]] == [
        ("gemini", "timeout"), ("claude", "vazio"), ("openai", "ok")]
    assert doc["chars_entrada"] == len(PERGUNTA) and doc["chars_saida"] == len(RESPOSTA)
    gravado = repr(doc)
    assert "Sigilosa" not in gravado and "123.456" not in gravado and "XYZ" not in gravado


def test_nenhum_provedor_registra_falha_e_devolve_503(fake):
    provs = [("groq", _prov(RuntimeError("caiu"))), ("gemini", _prov(asyncio.TimeoutError()))]
    with pytest.raises(HTTPException) as e:
        _rodar(provs)
    assert e.value.status_code == 503 and "gemini timeout" in e.value.detail
    [doc] = fake.ia_uso.docs
    assert doc["sucesso"] is False and doc["provedor"] is None
    assert [t["resultado"] for t in doc["tentativas"]] == ["erro:RuntimeError", "timeout"]


def test_falha_ao_gravar_nao_derruba_a_resposta(monkeypatch):
    class Quebrado:
        def __getitem__(self, k):
            raise RuntimeError("mongo fora")
    monkeypatch.setattr(ia_uso, "_db_atual", lambda: Quebrado())
    assert _rodar([("groq", _prov("ok"))]) == ("ok", "groq")


def test_cascatas_do_sistema_registram_a_origem(fake, monkeypatch):
    import routes.ai as ai
    from services import contrato_ia_service as cia
    monkeypatch.setattr(ai, "_PROVIDERS", [("groq", _prov("r1"))])
    monkeypatch.setattr(cia, "_PROVIDERS", [("gemini", _prov("r2"))])
    assert asyncio.run(ai._roma_ia_cascata([], origem="atendimento_site")) == ("r1", "groq")
    assert asyncio.run(cia._roma_ia_cascata([], origem="instagram")) == "r2"
    assert asyncio.run(cia._roma_ia_cascata([])) == "r2"
    assert [d["origem"] for d in fake.ia_uso.docs] == ["atendimento_site", "instagram", "contratos"]


def test_usuario_da_autenticacao_chega_ao_registro(fake):
    """A dependência de autenticação define o usuário; a cascata no endpoint o enxerga."""
    from dependencies import _heartbeat
    app = FastAPI()

    async def dep():
        _heartbeat(None, "conta-Z")
        return "conta-Z"

    @app.get("/x")
    async def x(uid: str = Depends(dep)):
        await ia_uso.cascata([("groq", _prov("ok"))], [], 10, origem="t")
        return {}

    with TestClient(app) as c:
        assert c.get("/x").status_code == 200
    assert fake.ia_uso.docs[0]["user_id"] == "conta-Z"


def test_resumo_por_provedor_e_origem():
    docs = [
        {"origem": "chat:geral", "sucesso": True, "ms_total": 900, "tentativas": [
            {"provedor": "groq", "modelo": "m", "resultado": "timeout", "ms": 15000},
            {"provedor": "gemini", "modelo": "g", "resultado": "ok", "ms": 800}]},
        {"origem": "chat:geral", "sucesso": True, "ms_total": 400, "tentativas": [
            {"provedor": "groq", "modelo": "m", "resultado": "ok", "ms": 400}]},
        {"origem": "contratos", "sucesso": False, "ms_total": 100, "tentativas": [
            {"provedor": "groq", "modelo": "m", "resultado": "erro:X", "ms": 100}]},
    ]
    r = ia_uso.resumo(docs)
    assert r["chamadas"] == 3 and r["respondidas"] == 2 and r["taxa_sucesso"] == 66.7
    assert r["com_reserva"] == 1
    groq = next(p for p in r["provedores"] if p["provedor"] == "groq")
    assert groq["tentativas"] == 3 and groq["respondeu"] == 1
    assert groq["falhas"] == {"timeout": 1, "erro:X": 1} and groq["ms_medio"] == 400
    assert r["origens"][0] == {"origem": "chat:geral", "chamadas": 2, "falhas": 0}
    assert ia_uso.resumo([])["taxa_sucesso"] is None


def test_painel_admin(fake):
    from db import get_db
    from dependencies import get_admin_user
    from routes.admin_ia import router
    _rodar([("groq", _prov("ok"))], origem="chat:geral", uid="u1")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_admin_user] = lambda: "admin"
    with TestClient(app) as c:
        j = c.get("/admin/ia/uso", params={"dias": 30}).json()
    assert j["resumo"]["chamadas"] == 1 and j["recentes"][0]["origem"] == "chat:geral"
    assert "user_id" not in j["recentes"][0]
