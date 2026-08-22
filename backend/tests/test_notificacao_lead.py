# @module tests.test_notificacao_lead — avisos por e-mail (lead imediato + resumo).
import asyncio
from datetime import datetime, timedelta

import pytest

from services import notificacao_lead as NL
from tests.test_trial_acesso import _Coll


class _DB:
    def __init__(self):
        self.users = _Coll()
        self.sys_config = _Coll()
        self.leads_avaliacao = _Coll()
        self.payment_events = _Coll()


def run(coro):
    return asyncio.run(coro)


# ── Config ───────────────────────────────────────────────────────────────────
def test_config_default_liga_lead_e_resumo_semanal():
    cfg = NL.normalizar_config(None)
    assert cfg["email_lead_ativo"] is True
    assert cfg["resumo_ativo"] is True and cfg["resumo_freq"] == "semanal"
    assert cfg["resumo_hora"] == 17 and cfg["resumo_dia_semana"] == 4  # sexta 17h


def test_config_saneia_valores_absurdos():
    cfg = NL.normalizar_config({"resumo_hora": 99, "resumo_dia_semana": "x",
                                "resumo_freq": "mensal", "email_destino": "  A@X.COM "})
    assert cfg["resumo_hora"] == 17 and cfg["resumo_dia_semana"] == 4
    assert cfg["resumo_freq"] == "semanal"          # só diario|semanal
    assert cfg["email_destino"] == "a@x.com"


# ── Quando disparar o resumo (função pura) ───────────────────────────────────
def _sexta_17h_utc():
    # 2026-08-28 é uma sexta-feira; 20h UTC = 17h em Açailândia (UTC-3).
    return datetime(2026, 8, 28, 20, 0)


def test_resumo_semanal_dispara_na_sexta_no_horario():
    cfg = NL.normalizar_config({})
    assert NL.deve_enviar_resumo(cfg, _sexta_17h_utc()) is True


def test_resumo_semanal_nao_dispara_antes_da_hora():
    cfg = NL.normalizar_config({})
    assert NL.deve_enviar_resumo(cfg, _sexta_17h_utc() - timedelta(hours=3)) is False


def test_resumo_semanal_nao_dispara_em_outro_dia():
    cfg = NL.normalizar_config({})
    quinta = _sexta_17h_utc() - timedelta(days=1)
    assert NL.deve_enviar_resumo(cfg, quinta) is False


def test_resumo_nao_repete_no_mesmo_dia():
    cfg = NL.normalizar_config({"resumo_ultimo": "2026-08-28"})
    assert NL.deve_enviar_resumo(cfg, _sexta_17h_utc()) is False


def test_resumo_diario_dispara_todo_dia_no_horario():
    cfg = NL.normalizar_config({"resumo_freq": "diario", "resumo_hora": 8})
    # 11h UTC = 8h local, numa terça
    assert NL.deve_enviar_resumo(cfg, datetime(2026, 8, 25, 11, 0)) is True


def test_resumo_desligado_nunca_dispara():
    cfg = NL.normalizar_config({"resumo_ativo": False})
    assert NL.deve_enviar_resumo(cfg, _sexta_17h_utc()) is False


# ── Agregação do resumo ──────────────────────────────────────────────────────
def test_montar_resumo_conta_periodo_e_canais():
    db = _DB()
    agora = datetime.utcnow()
    run(db.users.insert_one({"id": "a", "email": "a@x.com", "created_at": agora - timedelta(days=1),
                             "referrer": "https://www.bing.com/"}))
    run(db.users.insert_one({"id": "b", "email": "b@x.com", "created_at": agora - timedelta(days=2),
                             "referrer": "https://www.google.com/", "plan_status": "active",
                             "plan": "mensal"}))
    run(db.users.insert_one({"id": "c", "email": "c@x.com", "created_at": agora - timedelta(days=40),
                             "referrer": "https://www.google.com/"}))   # fora da janela
    run(db.users.insert_one({"id": "d", "email": "d@x.com", "created_at": agora - timedelta(days=1),
                             "trial": True, "trial_inicio": agora - timedelta(days=1)}))
    run(db.leads_avaliacao.insert_one({"criado_em": agora - timedelta(hours=5)}))
    run(db.payment_events.insert_one({"user_id": "b", "status": "approved",
                                      "received_at": agora - timedelta(days=2)}))

    r = run(NL.montar_resumo(db, dias=7, agora=agora))
    assert r["cadastros"] == 3            # a, b, d (c ficou fora)
    assert r["leads_calculadora"] == 1
    assert r["testes_liberados"] == 1
    assert r["assinaturas"] == 1
    assert r["total_usuarios"] == 4
    canais = {c["canal"]: c["total"] for c in r["canais"]}
    assert canais["bing"] == 1 and canais["google"] == 1 and canais["direto"] == 1


# ── Envio (com e-mail falso) ─────────────────────────────────────────────────
def test_enviar_email_lead_respeita_o_desligado(monkeypatch):
    db = _DB()
    run(NL.salvar_config(db, {"email_lead_ativo": False}))
    r = run(NL.enviar_email_lead(db, {"nome": "X"}))
    assert r["ok"] is False and r["erro"] == "desativado"


def test_enviar_email_lead_usa_destino_configurado(monkeypatch):
    db = _DB()
    run(NL.salvar_config(db, {"email_lead_ativo": True, "email_destino": "chefe@x.com"}))
    enviados = []

    async def _fake(to, lead):
        enviados.append((to, lead))

    import email_service
    monkeypatch.setattr(email_service, "send_lead_email", _fake)
    r = run(NL.enviar_email_lead(db, {"nome": "Maria"}))
    assert r["ok"] is True and r["para"] == "chefe@x.com"
    assert enviados and enviados[0][0] == "chefe@x.com"


def test_enviar_resumo_monta_e_envia(monkeypatch):
    db = _DB()
    run(db.users.insert_one({"id": "a", "email": "a@x.com", "created_at": datetime.utcnow(),
                             "referrer": "https://www.bing.com/"}))
    run(NL.salvar_config(db, {"email_destino": "chefe@x.com"}))
    capturado = {}

    async def _fake(to, dados):
        capturado["to"] = to
        capturado["dados"] = dados

    import email_service
    monkeypatch.setattr(email_service, "send_resumo_email", _fake)
    r = run(NL.enviar_resumo(db))
    assert r["ok"] is True
    assert capturado["to"] == "chefe@x.com"
    assert capturado["dados"]["cadastros"] == 1


def test_falha_no_envio_nao_levanta(monkeypatch):
    db = _DB()
    run(NL.salvar_config(db, {"email_destino": "chefe@x.com"}))

    async def _explode(*a, **kw):
        raise RuntimeError("SMTP fora do ar")

    import email_service
    monkeypatch.setattr(email_service, "send_lead_email", _explode)
    r = run(NL.enviar_email_lead(db, {"nome": "X"}))
    assert r["ok"] is False and "SMTP" in r["erro"]


# ── Templates ────────────────────────────────────────────────────────────────
def test_template_do_lead_traz_dados_e_link_do_whatsapp():
    from email_service import build_lead_email
    s, html = build_lead_email({
        "nome": "Maria", "whatsapp": "5599991811246", "email": "m@x.com",
        "imovel": {"tipo": "casa", "area": 120, "cidade": "Açailândia", "uf": "MA"},
        "estimativa": {"faixa_texto": "R$ 288.000 a R$ 366.000"},
    })
    assert "Maria" in s and "Açailândia" in s
    assert "wa.me/5599991811246" in html and "R$ 288.000" in html


def test_template_do_resumo_desenha_os_canais():
    from email_service import build_resumo_email
    s, html = build_resumo_email({
        "dias": 7, "cadastros": 4, "leads_calculadora": 2, "assinaturas": 1,
        "testes_liberados": 1, "total_usuarios": 12,
        "canais": [{"canal": "bing", "label": "Bing (orgânico)", "total": 3},
                   {"canal": "direto", "label": "Direto", "total": 1}],
    })
    assert "4 cadastro(s)" in s
    assert "Bing (orgânico)" in html and "Direto" in html
