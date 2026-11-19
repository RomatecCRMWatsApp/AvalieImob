# @module tests.test_blog_metricas — contagem anônima de leituras/cliques nos artigos + funil.
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_admin_user
from services import blog_metricas as BM
from tests.test_trial_acesso import _Coll

SLUG = "como-fazer-ptam-passo-a-passo-nbr-14653"
OUTRO = "como-calcular-valor-liquidacao-forcada-vlf"


class _DB:
    def __init__(self):
        self.users = _Coll()
        self.blog_eventos = _Coll()
        self.sys_config = _Coll()
        self.leads_avaliacao = _Coll()
        self.payment_events = _Coll()

    def __getitem__(self, nome):
        return getattr(self, nome)


def test_valida_recusa_lixo():
    assert BM.valida(SLUG, "clique", "meio") is None
    assert BM.valida(SLUG, "leitura", "pagina") is None
    assert BM.valida("artigo-inventado", "clique", "meio")
    assert BM.valida(SLUG, "clique", "qualquer")
    assert BM.valida(SLUG, "leitura", "meio")
    assert BM.valida(SLUG, "clique", "pagina")
    assert BM.valida(SLUG, "compra", "meio")


def test_resumo_monta_funil_por_artigo():
    agora = datetime(2026, 11, 19, 12, 0)
    eventos = [
        {"dia": "2026-11-18", "slug": SLUG, "tipo": "leitura", "posicao": "pagina", "n": 40},
        {"dia": "2026-11-19", "slug": SLUG, "tipo": "clique", "posicao": "meio", "n": 3},
        {"dia": "2026-11-19", "slug": SLUG, "tipo": "clique", "posicao": "fim", "n": 1},
        {"dia": "2026-11-19", "slug": OUTRO, "tipo": "leitura", "posicao": "pagina", "n": 10},
        {"dia": "2026-01-01", "slug": SLUG, "tipo": "clique", "posicao": "meio", "n": 99},  # fora
    ]
    usuarios = [
        {"page_origin": "/blog/" + SLUG, "created_at": agora - timedelta(days=2),
         "plan": "mensal", "plan_status": "active", "login_count": 3},
        {"page_origin": "/blog/" + SLUG + "?utm_source=x", "created_at": agora - timedelta(days=1),
         "plan": "trial", "plan_status": "active", "trial": True},
        {"page_origin": "/", "created_at": agora},                                   # não é blog
        {"page_origin": "/blog/" + SLUG, "created_at": agora - timedelta(days=90)},  # fora
    ]
    r = BM.resumo(eventos, usuarios, 30, agora=agora)
    a = {x["slug"]: x for x in r["artigos"]}[SLUG]
    assert a["leituras"] == 40 and a["cliques"] == 4
    assert a["cliques_por_posicao"] == {"meio": 3, "fim": 1}
    assert a["cadastros"] == 2 and a["assinantes"] == 1 and a["em_teste"] == 1
    assert a["nunca_acessaram"] == 1
    assert a["taxa_clique"] == 10.0
    assert r["totais"]["leituras"] == 50 and r["totais"]["cadastros"] == 2
    assert r["artigos"][0]["slug"] == SLUG


@pytest.fixture()
def cliente():
    from routes.admin_leads import router as admin
    from routes.blog_metricas import router as publico
    fake = _DB()
    app = FastAPI()
    app.include_router(publico)
    app.include_router(admin)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_admin_user] = lambda: "admin1"
    from services.ratelimit import pub_limiter
    app.state.limiter = pub_limiter
    with TestClient(app) as c:
        c.fake = fake
        yield c


def test_rota_publica_agrega_por_dia_sem_dado_pessoal(cliente):
    for _ in range(3):
        r = cliente.post("/blog/evento", json={"slug": SLUG, "tipo": "clique", "posicao": "meio"})
        assert r.status_code == 200, r.text
    cliente.post("/blog/evento", json={"slug": SLUG, "tipo": "leitura", "posicao": "pagina"})
    docs = cliente.fake.blog_eventos.docs
    assert len(docs) == 2                      # um documento por dia/artigo/tipo/posição
    clique = [d for d in docs if d["tipo"] == "clique"][0]
    assert clique["n"] == 3
    assert set(clique) <= {"_id", "n", "dia", "slug", "tipo", "posicao", "atualizado_em"}
    assert cliente.post("/blog/evento", json={"slug": "nao-existe", "tipo": "clique",
                                              "posicao": "meio"}).status_code == 422

    r = cliente.get("/admin/leads/blog?dias=30")
    assert r.status_code == 200, r.text
    a = r.json()["artigos"][0]
    assert a["slug"] == SLUG and a["cliques"] == 3 and a["leituras"] == 1
