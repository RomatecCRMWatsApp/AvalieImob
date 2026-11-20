# @module tests.test_privacidade — Controles de privacidade (LGPD). Dados SINTÉTICOS.
import asyncio
import json
import logging
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from db import get_db
from dependencies import get_admin_user, get_authenticated_user
from services.log_redaction import RedactingFilter, redigir
from services.perfil_publico import perfil_publico
from services.privacidade import exclusao as EXC
from services.privacidade import exportacao as EXP
from services.privacidade import pedidos as PED
from services.ratelimit import pub_limiter
from tests.privacidade_fake import FakeDB


def run(c):
    return asyncio.run(c)


# ── Fixture HTTP ────────────────────────────────────────────────────────────
@pytest.fixture()
def ctx(monkeypatch):
    monkeypatch.setenv("PRIVACIDADE_RECURSOS_ATIVOS", "1")
    monkeypatch.setenv("PRIVACIDADE_MINUTAS_ATIVAS", "1")
    monkeypatch.delenv("PRIVACIDADE_EXCLUSAO_EXECUCAO_ATIVA", raising=False)
    enviados = []

    async def _coletor(email, protocolo, codigo):
        enviados.append({"email": email, "protocolo": protocolo, "codigo": codigo})

    monkeypatch.setattr(PED, "enviar_codigo", _coletor)
    pub_limiter.reset()
    from routes.privacidade import router

    db = FakeDB()
    db.users.docs.extend([
        {"id": "uA", "name": "Ana Sintética", "email": "ana@exemplo.test", "phone": "5599900000001",
         "role": "user", "plan": "mensal", "plan_status": "active", "password_hash": "x"},
        {"id": "uB", "name": "Bruno Sintético", "email": "bruno@exemplo.test", "role": "user",
         "password_hash": "y"},
        {"id": "adm", "name": "Admin", "email": "adm@exemplo.test", "role": "admin"},
    ])
    quem = {"uid": "uA"}
    app = FastAPI()
    app.state.limiter = pub_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_authenticated_user] = lambda: quem["uid"]
    app.dependency_overrides[get_admin_user] = lambda: "adm"
    with TestClient(app) as c:
        c.db, c.quem, c.enviados = db, quem, enviados
        yield c
    pub_limiter.reset()


def _pedido(**kw):
    base = {"nome": "Carla Titular", "email": "carla@exemplo.test", "relacao": "cliente_de_usuario",
            "tipo_direito": "confirmacao_acesso", "descricao": "Quero saber se há dados meus.",
            "declaracao_veracidade": True}
    base.update(kw)
    return base


# ── (a) Link público do laudo não expõe dados pessoais do avaliador ────────────
def test_perfil_publico_e_allowlist():
    perfil = {"nome_completo": "Avaliador X", "registros": [{"tipo": "CRECI", "numero": "1"}],
              "cpf": "123.456.789-09", "rg": "123", "assinatura_visual_b64": "AAAA",
              "certificado_cnai_b64": "BBBB", "campo_futuro_secreto": "z", "_id": 1, "user_id": "u"}
    pub = perfil_publico(perfil)
    assert pub == {"nome_completo": "Avaliador X", "registros": [{"tipo": "CRECI", "numero": "1"}]}
    assert perfil_publico(None) is None


def test_rota_publica_do_laudo_nao_vaza_assinatura_nem_cpf(monkeypatch):
    from routes import ptam as ptam_routes
    from services import link_tracking

    async def _nada(*a, **kw):
        return None

    monkeypatch.setattr(link_tracking, "registrar_evento", _nada)
    db = FakeDB()
    db.ptam_documents.docs.append({"id": "p1", "user_id": "uA", "link_publico_token": "tok",
                                   "link_publico_ativo": True, "numero_ptam": "PTAM-1"})
    db.perfil_avaliador.docs.append({"user_id": "uA", "nome_completo": "Avaliador X",
                                     "cpf": "12345678909", "assinatura_visual_b64": "SECRETO"})
    app = FastAPI()
    app.include_router(ptam_routes.router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        r = c.get("/ptam/public/tok", headers={"user-agent": "Mozilla"})
    assert r.status_code == 200, r.text
    corpo = r.text
    assert "SECRETO" not in corpo and "12345678909" not in corpo
    assert r.json()["perfil_avaliador"]["nome_completo"] == "Avaliador X"


def test_verificacao_publica_mascara_cpf():
    from routes.assinatura import _mascarar_doc_publico
    assert _mascarar_doc_publico("123.456.789-09") == "***.456.789-**"
    assert _mascarar_doc_publico("12.345.678/0001-95") == "12.345.678/0001-95"
    assert _mascarar_doc_publico(None) is None


# ── (h) Logs sem PII/segredos ───────────────────────────────────────────────
def test_redacao_de_logs():
    s = redigir("Falha WhatsApp p/ 5599985157964 email fulano@gmail.com cpf 123.456.789-09 "
                "GET /api/ptam/public/AbCdEf_ghIJklmnOPqrstuVWxyz0123456789-xyz "
                "?token=segredo123 Bearer eyJabc.def.ghi id=3f2a1b4c-1111-2222-3333-444455556666 "
                "cnpj 12345678000195")
    assert "5599985157964" not in s and "fulano@" not in s and "123.456.789-09" not in s
    assert "AbCdEf_ghIJ" not in s and "segredo123" not in s
    assert "3f2a1b4c-1111-2222-3333-444455556666" in s  # ids internos preservados
    assert "12345678000195" in s                         # CNPJ é dado empresarial


def test_filtro_aplicado_ao_registro():
    rec = logging.LogRecord("x", logging.INFO, __file__, 1, "envio p/ %s falhou", ("ana@x.com.br",), None)
    assert RedactingFilter().filter(rec) is True
    assert "ana@" not in rec.getMessage() and "a***@x.com.br" in rec.getMessage()


# ── (e) Canal do titular sem conta, com prevenção de fraude ───────────────────
def test_canal_desligado_responde_404(ctx, monkeypatch):
    monkeypatch.setenv("PRIVACIDADE_RECURSOS_ATIVOS", "0")
    assert ctx.post("/privacidade/titular/pedidos", json=_pedido()).status_code == 404


def test_pedido_titular_fluxo_completo(ctx):
    r = ctx.post("/privacidade/titular/pedidos", json=_pedido())
    assert r.status_code == 202, r.text
    proto = r.json()["protocolo"]
    assert proto.startswith("PRIV-")
    doc = ctx.db.privacidade_pedidos.docs[0]
    assert doc["status"] == "aguardando_verificacao"
    codigo = ctx.enviados[0]["codigo"]
    assert codigo not in json.dumps(doc, default=str)          # código não fica em claro
    # código errado → falha genérica e conta tentativa
    r = ctx.post(f"/privacidade/titular/pedidos/{proto}/verificar",
                 json={"email": "carla@exemplo.test", "codigo": "000000" if codigo != "000000" else "111111"})
    assert r.status_code == 400
    # e-mail de outra pessoa não confirma
    r = ctx.post(f"/privacidade/titular/pedidos/{proto}/verificar",
                 json={"email": "intruso@exemplo.test", "codigo": codigo})
    assert r.status_code == 400
    r = ctx.post(f"/privacidade/titular/pedidos/{proto}/verificar",
                 json={"email": "CARLA@exemplo.test", "codigo": codigo})
    assert r.status_code == 200 and r.json()["status"] == "recebido"
    assert r.json()["prazo_em"]
    # consulta de status exige o e-mail do pedido
    assert ctx.post(f"/privacidade/titular/pedidos/{proto}/status",
                    json={"email": "outro@exemplo.test"}).status_code == 404
    assert ctx.post(f"/privacidade/titular/pedidos/{proto}/status",
                    json={"email": "carla@exemplo.test"}).json()["status"] == "recebido"


def test_pedido_bloqueia_apos_tentativas(ctx):
    proto = ctx.post("/privacidade/titular/pedidos", json=_pedido()).json()["protocolo"]
    for _ in range(PED.MAX_TENTATIVAS):
        ctx.post(f"/privacidade/titular/pedidos/{proto}/verificar",
                 json={"email": "carla@exemplo.test", "codigo": "x"})
    codigo = ctx.enviados[0]["codigo"]
    r = ctx.post(f"/privacidade/titular/pedidos/{proto}/verificar",
                 json={"email": "carla@exemplo.test", "codigo": codigo})
    assert r.status_code == 400 and "tentativas" in r.json()["detail"]


def test_codigo_expirado_nao_confirma(ctx):
    proto = ctx.post("/privacidade/titular/pedidos", json=_pedido()).json()["protocolo"]
    ctx.db.privacidade_pedidos.docs[0]["codigo_expira_em"] = datetime.utcnow() - timedelta(minutes=1)
    r = ctx.post(f"/privacidade/titular/pedidos/{proto}/verificar",
                 json={"email": "carla@exemplo.test", "codigo": ctx.enviados[0]["codigo"]})
    assert r.status_code == 400


def test_mesma_resposta_com_ou_sem_conta_e_honeypot(ctx):
    a = ctx.post("/privacidade/titular/pedidos", json=_pedido(email="ana@exemplo.test")).json()
    b = ctx.post("/privacidade/titular/pedidos", json=_pedido(email="naoexiste@exemplo.test")).json()
    assert a["mensagem"] == b["mensagem"] and set(a) == set(b)
    n = len(ctx.db.privacidade_pedidos.docs)
    r = ctx.post("/privacidade/titular/pedidos", json=_pedido(website="spam"))
    assert r.status_code == 202 and len(ctx.db.privacidade_pedidos.docs) == n  # robô: nada gravado


def test_validacao_e_limite_de_taxa(ctx):
    assert ctx.post("/privacidade/titular/pedidos",
                    json=_pedido(declaracao_veracidade=False)).status_code == 422
    assert ctx.post("/privacidade/titular/pedidos", json=_pedido(email="sem-arroba")).status_code == 422
    codigos = [ctx.post("/privacidade/titular/pedidos", json=_pedido()).status_code for _ in range(6)]
    assert 429 in codigos


def test_admin_trilha_e_regras_de_status(ctx):
    proto = ctx.post("/privacidade/titular/pedidos", json=_pedido()).json()["protocolo"]
    pid = ctx.db.privacidade_pedidos.docs[0]["id"]
    # sem e-mail confirmado não avança
    assert ctx.patch(f"/privacidade/admin/pedidos/{pid}", json={"status": "em_analise"}).status_code == 422
    ctx.post(f"/privacidade/titular/pedidos/{proto}/verificar",
             json={"email": "carla@exemplo.test", "codigo": ctx.enviados[0]["codigo"]})
    r = ctx.patch(f"/privacidade/admin/pedidos/{pid}",
                  json={"status": "em_analise", "responsavel": "Equipe X", "nota": "conferindo"})
    assert r.status_code == 200
    acoes = [e["acao"] for e in r.json()["historico"]]
    assert acoes[:2] == ["criado", "verificado"] and {"status", "responsavel", "nota"} <= set(acoes)
    assert "codigo_hash" not in r.json()
    lista = ctx.get("/privacidade/admin/pedidos").json()
    assert len(lista) == 1


# ── (c) Aceite versionado e consentimentos separados ──────────────────────────
def test_aceite_pendente_e_registro_com_versao_hash(ctx):
    me = ctx.get("/privacidade/me").json()
    assert me["aceites"]["termos"]["pendente"] is True        # usuário antigo: pendente, não bloqueado
    doc = ctx.get("/privacidade/documentos/termos").json()
    assert "MINUTA" in doc["texto"] and len(doc["hash"]) == 64
    ruim = ctx.post("/privacidade/me/aceites", json={"tipo": "termos", "versao": doc["versao"], "hash": "0" * 64})
    assert ruim.status_code == 409
    ok = ctx.post("/privacidade/me/aceites", json={"tipo": "termos", "versao": doc["versao"], "hash": doc["hash"]})
    assert ok.status_code == 200
    reg = ctx.db.privacidade_aceites.docs[0]
    assert reg["user_id"] == "uA" and reg["hash"] == doc["hash"] and isinstance(reg["aceito_em"], datetime)
    assert "ip" not in reg
    me = ctx.get("/privacidade/me").json()
    assert me["aceites"]["termos"]["pendente"] is False
    assert me["aceites"]["privacidade"]["pendente"] is True   # aceites independentes


def test_aceite_indisponivel_sem_minutas(ctx, monkeypatch):
    monkeypatch.setenv("PRIVACIDADE_MINUTAS_ATIVAS", "0")
    assert ctx.get("/privacidade/documentos/termos").status_code == 404
    assert ctx.post("/privacidade/me/aceites",
                    json={"tipo": "termos", "versao": "x", "hash": "y"}).status_code == 409


def test_consentimento_marketing_padrao_off_revogavel_com_historico(ctx):
    me = ctx.get("/privacidade/me").json()
    assert me["consentimentos"]["marketing_email"]["concedido"] is False
    ctx.post("/privacidade/me/consentimentos", json={"finalidade": "marketing_email", "concedido": True})
    r = ctx.post("/privacidade/me/consentimentos", json={"finalidade": "marketing_email", "concedido": False})
    est = r.json()["marketing_email"]
    assert est["concedido"] is False and est["eventos"] == 2
    assert r.json()["marketing_whatsapp"]["concedido"] is False   # finalidades independentes
    assert ctx.post("/privacidade/me/consentimentos",
                    json={"finalidade": "tudo", "concedido": True}).status_code == 422


# ── (d) Exportação sem vazamento + link expirado ───────────────────────────
def _semear_dois_usuarios(db):
    db.clients.docs += [{"id": "c1", "user_id": "uA", "name": "Cliente da Ana", "doc": "11122233344"},
                        {"id": "c2", "user_id": "uB", "name": "Cliente do Bruno", "doc": "55566677788"}]
    db.transactions.docs += [{"user_id": "uA", "status": "approved", "amount": 1, "mp_payment_id": "MA",
                              "created_at": datetime.utcnow()},
                             {"user_id": "uB", "status": "approved", "amount": 2, "mp_payment_id": "MB"}]
    db.perfil_avaliador.docs.append({"user_id": "uA", "nome_completo": "Ana", "assinatura_visual_b64": "IMG"})


def test_exportacao_escopo_do_proprio_usuario(ctx):
    _semear_dois_usuarios(ctx.db)
    r = ctx.post("/privacidade/me/exportacao", json={"formato": "json"})
    assert r.status_code == 201
    url = r.json()["url"].replace("/api", "")
    d = ctx.get(url)
    assert d.status_code == 200 and d.headers["cache-control"] == "no-store"
    txt = d.text
    assert "ana@exemplo.test" in txt and "MA" in txt
    for proibido in ("bruno@", "MB", "Cliente do Bruno", "Cliente da Ana", "password_hash", "IMG"):
        assert proibido not in txt, proibido
    pacote = json.loads(txt)
    assert pacote["contagem_registros"]["clients"] == 1
    # uso único
    assert ctx.get(url).status_code == 410


def test_exportacao_de_outro_usuario_e_expirada(ctx):
    url = ctx.post("/privacidade/me/exportacao", json={"formato": "csv"}).json()["url"].replace("/api", "")
    ctx.quem["uid"] = "uB"
    assert ctx.get(url).status_code == 404            # token certo, sessão errada
    ctx.quem["uid"] = "uA"
    ctx.db.privacidade_exportacoes.docs[0]["expira_em"] = datetime.utcnow() - timedelta(seconds=1)
    assert ctx.get(url).status_code == 410
    assert ctx.db.privacidade_exportacoes.docs[0]["conteudo"] is None   # conteúdo descartado


def test_csv_neutraliza_formulas():
    assert EXP.celula_segura("=HYPERLINK(\"x\")").startswith("'=")
    assert EXP.celula_segura("+55 99") == "'+55 99"
    assert EXP.celula_segura("normal") == "normal"
    csv_ = EXP.para_csv({"conta": {"name": "=cmd|' /C calc'!A0"}}).decode("utf-8")
    assert "\"'=cmd" in csv_


# ── (f)(j) Exclusão separada por alvo, retenção e reaplicação após restore ─────
def _semear_conta(db):
    db.users.docs.append({"id": "uC", "name": "Clara Excluir", "email": "clara@exemplo.test",
                          "phone": "5599911112222", "role": "user", "password_hash": "h"})
    db.perfil_avaliador.docs.append({"user_id": "uC", "cpf": "12345678909", "assinatura_visual_b64": "IMG"})
    db.clients.docs.append({"id": "cc", "user_id": "uC", "name": "Terceiro"})
    db.ptam_documents.docs.append({"id": "pt", "user_id": "uC", "icp_status": "assinado"})
    db.transactions.docs.append({"user_id": "uC", "status": "approved"})
    db.ai_messages.docs.append({"user_id": "uC", "content": "texto"})


def test_plano_de_exclusao_e_dry_run(ctx):
    _semear_conta(ctx.db)
    antes = json.dumps(ctx.db.users.docs, default=str)
    r = ctx.get("/privacidade/admin/exclusao/conta/uC/plano")
    assert r.status_code == 200
    p = r.json()
    assert p["carteira_nao_tocada"]["clients"] == 1 and p["preservar"]["transactions"]["quantidade"] == 1
    assert "email" in p["anonimizar"]["users"] and p["apagar"]["ai_messages"] == 1
    assert json.dumps(ctx.db.users.docs, default=str) == antes      # nada mudou


def test_execucao_exige_flag_e_confirmacao(ctx, monkeypatch):
    _semear_conta(ctx.db)
    r = ctx.post("/privacidade/admin/exclusao/conta/uC/executar", json={"confirmacao": "ANONIMIZAR uC"})
    assert r.status_code == 403
    monkeypatch.setenv("PRIVACIDADE_EXCLUSAO_EXECUCAO_ATIVA", "1")
    assert ctx.post("/privacidade/admin/exclusao/conta/uC/executar",
                    json={"confirmacao": "sim"}).status_code == 422
    assert ctx.post("/privacidade/admin/exclusao/conta/adm/executar",
                    json={"confirmacao": "ANONIMIZAR adm"}).status_code == 409
    r = ctx.post("/privacidade/admin/exclusao/conta/uC/executar", json={"confirmacao": "ANONIMIZAR uC"})
    assert r.status_code == 200, r.text
    u = next(d for d in ctx.db.users.docs if d["id"] == "uC")
    assert u["email"].endswith("@anonimizado.invalid") and u["phone"] is None and u["conta_encerrada"]
    perfil = next(d for d in ctx.db.perfil_avaliador.docs if d["user_id"] == "uC")
    assert perfil["cpf"] is None and perfil["assinatura_visual_b64"] is None
    assert len(ctx.db.clients.docs) == 1 and len(ctx.db.ptam_documents.docs) == 1   # carteira preservada
    assert len(ctx.db.transactions.docs) == 1                                      # retenção fiscal
    assert ctx.db.ai_messages.docs == []
    # idempotente
    assert ctx.post("/privacidade/admin/exclusao/conta/uC/executar",
                    json={"confirmacao": "ANONIMIZAR uC"}).status_code == 200
    assert len(ctx.db.privacidade_exclusoes.docs) == 1


def test_reaplicacao_apos_restore():
    db = FakeDB()
    _semear_conta(db)
    run(EXC.anonimizar_conta(db, "uC", "adm"))
    # simula restauração de backup anterior à exclusão
    u = next(d for d in db.users.docs if d["id"] == "uC")
    u.update({"email": "clara@exemplo.test", "name": "Clara Excluir", "phone": "5599911112222"})
    assert run(EXC.reaplicar_exclusoes(db)) == ["uC"]
    assert u["email"].endswith("@anonimizado.invalid")
    assert run(EXC.reaplicar_exclusoes(db)) == []          # idempotente


def test_conta_encerrada_perde_acesso_mesmo_com_jwt():
    from fastapi import HTTPException
    from dependencies import get_authenticated_user as dep
    db = FakeDB()
    db.users.docs.append({"id": "uZ", "conta_encerrada": True})
    with pytest.raises(HTTPException) as e:
        run(dep(uid="uZ", db=db))
    assert e.value.status_code == 401


def test_localizar_titular_por_conta_sem_devolver_dados(ctx):
    ctx.db.clients.docs.append({"id": "cx", "user_id": "uB", "name": "Fulano", "doc": "111.222.333-44",
                                "email": "fulano@exemplo.test"})
    r = ctx.get("/privacidade/admin/titular/localizar", params={"documento": "11122233344"})
    occ = r.json()["ocorrencias"]
    assert occ == [{"colecao": "clients", "campo": "doc", "registro_id": "cx", "conta_responsavel": "uB"}]
    assert ctx.get("/privacidade/admin/titular/localizar").status_code == 422


# ── (i) Assinatura: sem renovação automática; arrependimento sem estorno automático ─
def test_assinatura_informa_e_arrependimento_idempotente(ctx):
    ctx.db.transactions.docs.append({"user_id": "uA", "status": "approved",
                                     "created_at": datetime.utcnow() - timedelta(days=2)})
    info = ctx.get("/privacidade/me/assinatura").json()
    assert info["renovacao_automatica"] is False and info["dentro_prazo_arrependimento_7_dias"] is True
    a = ctx.post("/privacidade/me/assinatura/arrependimento").json()
    b = ctx.post("/privacidade/me/assinatura/arrependimento").json()
    assert a["protocolo"] == b["protocolo"]
    assert len(ctx.db.privacidade_pedidos.docs) == 1
    u = next(d for d in ctx.db.users.docs if d["id"] == "uA")
    assert u["plan_status"] == "active"        # nada financeiro/acesso alterado automaticamente
    ctx.db.transactions.docs[0]["created_at"] = datetime.utcnow() - timedelta(days=10)
    assert ctx.get("/privacidade/me/assinatura").json()["dentro_prazo_arrependimento_7_dias"] is False


# ── (g) Uploads inválidos continuam recusados ────────────────────────────────
def test_upload_recusa_conteudo_falso():
    from dependencies import get_active_subscriber
    from routes.uploads import router as up
    app = FastAPI()
    app.include_router(up)
    app.dependency_overrides[get_db] = lambda: FakeDB()
    app.dependency_overrides[get_active_subscriber] = lambda: "uA"
    with TestClient(app) as c:
        r = c.post("/upload/image", files={"file": ("x.png", b"<script>alert(1)</script>", "image/png")})
        assert r.status_code == 400
        r = c.post("/upload/image", files={"file": ("x.html", b"<html></html>", "text/html")})
        assert r.status_code == 400


# ── Páginas de Privacidade/Termos existem (antes caíam em 404) e ficam fora do índice ─
def test_rotas_de_privacidade_existem_e_sao_noindex():
    from services import seo_html
    for p in ("/privacidade", "/termos", "/privacidade/solicitacao"):
        assert seo_html.rota_existe(p), p
        assert seo_html.eh_noindex(p), p


def test_documentos_minuta_versionados():
    from services.privacidade import documentos
    for tipo in documentos.TIPOS:
        d = documentos.carregar(tipo)
        assert d and d["minuta"] is True and d["versao"].startswith("0.1-minuta")
    assert documentos.carregar("inexistente") is None
