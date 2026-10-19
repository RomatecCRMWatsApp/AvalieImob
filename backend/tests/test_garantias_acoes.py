# @module tests.test_garantias_acoes — ações do card da Avaliação de Garantias (HTTP, DB falso).
#
# Paridade com o card do PTAM: PDF, DOCX, clonar, WhatsApp, link público com
# contador, histórico, recibo. O que os testes protegem:
#   - o PDF é laudo de GARANTIA (não o layout do PTAM que a assinatura usava antes);
#   - o WhatsApp manda o MESMO PDF que se baixa;
#   - o clone não herda assinatura, link nem recibo do original;
#   - o PUT do wizard não apaga o estado do servidor (link/recibo/assinatura);
#   - isolamento: um usuário não alcança a garantia de outro.
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber
from routes.garantias import router

USER_A, USER_B = "userA", "userB"


class _Cur:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *a, **k):
        return self

    async def to_list(self, n):
        return [dict(d) for d in self.docs[:n]]


class _Coll:
    def __init__(self):
        self.docs = []

    def _m(self, d, f):
        for k, v in (f or {}).items():
            a = d.get(k)
            if isinstance(v, dict):
                if "$regex" in v and not (a and re.search(v["$regex"], str(a))):
                    return False
                if "$exists" in v and (k in d) != bool(v["$exists"]):
                    return False
            elif a != v:
                return False
        return True

    def find(self, f=None, *a, **k):
        return _Cur([d for d in self.docs if self._m(d, f)])

    async def find_one(self, f, *a, sort=None, **k):
        return next((dict(d) for d in self.docs if self._m(d, f)), None)

    async def count_documents(self, f):
        return len([d for d in self.docs if self._m(d, f)])

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def delete_one(self, f):
        antes = len(self.docs)
        self.docs = [d for d in self.docs if not self._m(d, f)]
        return type("R", (), {"deleted_count": antes - len(self.docs)})()

    async def update_one(self, f, upd, upsert=False):
        d = next((d for d in self.docs if self._m(d, f)), None)
        if d is None:
            if not upsert:
                return
            d = {k: v for k, v in f.items() if not isinstance(v, dict)}
            self.docs.append(d)
        d.update(upd.get("$set", {}))
        for k, v in (upd.get("$inc") or {}).items():
            d[k] = (d.get(k) or 0) + v
        for k, v in (upd.get("$max") or {}).items():
            d[k] = max(d.get(k) or 0, v)

    async def find_one_and_update(self, f, upd, upsert=False, return_document=None):
        await self.update_one(f, upd, upsert=True)
        return await self.find_one(f)


class _DB:
    def __init__(self):
        for n in ("garantias", "counters", "users", "perfil_avaliador", "ptam_link_eventos",
                  "recibos", "recibos_garantia", "perfis_avaliador", "email_logs", "assinaturas_pdf"):
            setattr(self, n, _Coll())

    def __getitem__(self, nome):
        return getattr(self, nome)


@pytest.fixture()
def ctx(monkeypatch):
    fake = _DB()
    atual = {"uid": USER_A}
    enviados = []

    async def _envia(**kw):
        enviados.append(kw)
        return {"ok": True}

    async def _integra(db, uid, fallback_zapi=True):
        return {"zapi_instance_id": "i", "zapi_token": "t", "zapi_security_token": "s"}

    async def _sem_marca(db, uid):
        raise RuntimeError("sem marca no teste")

    monkeypatch.setattr("services.zapi_service.send_document_pdf", _envia)
    monkeypatch.setattr("services.zapi_service.send_text", _envia)
    monkeypatch.setattr("routes.garantias.carregar_integracoes", _integra)
    monkeypatch.setattr("services.branding_repository.get_branding", _sem_marca)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_active_subscriber] = lambda: atual["uid"]
    with TestClient(app) as c:
        c.fake, c.enviados = fake, enviados
        c.como = lambda uid: atual.update({"uid": uid})
        yield c


def _nova(ctx, **extra):
    body = {"tipo_garantia": "imovel_rural", "modalidade_financeira": "credito_rural",
            "municipio": "Açailândia", "uf": "MA", "area_total_ha": 120.5,
            "valor_mercado": 1500000, "descricao_bem": "Fazenda Boa Vista",
            "solicitante": {"nome": "João da Silva"}, **extra}
    r = ctx.post("/garantias", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_numeracao_sequencial_sem_duplicar(ctx):
    a, b = _nova(ctx), _nova(ctx)
    assert a["numero"] != b["numero"]
    assert re.match(r"GAR-\d{4}-0001", a["numero"])


def test_pdf_e_laudo_de_garantia(ctx):
    g = _nova(ctx)
    r = ctx.get(f"/garantias/{g['id']}/pdf")
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF-")
    assert "Laudo_Garantia_" in r.headers["content-disposition"]
    import fitz
    txt = "".join(p.get_text() for p in fitz.open(stream=r.content, filetype="pdf"))
    assert "LAUDO DE AVALIAÇÃO DE GARANTIA" in txt
    assert "1.500.000,00" in txt


def test_docx(ctx):
    g = _nova(ctx)
    r = ctx.get(f"/garantias/{g['id']}/docx")
    assert r.status_code == 200
    assert r.content[:2] == b"PK"


def test_whatsapp_envia_o_mesmo_pdf(ctx):
    g = _nova(ctx)
    baixado = ctx.get(f"/garantias/{g['id']}/pdf").content
    r = ctx.post(f"/garantias/{g['id']}/whatsapp", json={"phone": "5599991811246"})
    assert r.status_code == 200, r.text
    enviado = ctx.enviados[-1]["pdf_bytes"]
    # mesmo laudo (o PDF carrega data de criação; compara o texto)
    import fitz
    t = lambda b: "".join(p.get_text() for p in fitz.open(stream=b, filetype="pdf"))
    assert t(enviado) == t(baixado)
    doc = ctx.fake.garantias.docs[0]
    assert doc["link_sends"] == 1 and doc["link_last_canal"] == "whatsapp"


def test_link_publico_conta_visualizacao_e_ignora_bot(ctx):
    g = _nova(ctx)
    r = ctx.post(f"/garantias/{g['id']}/compartilhar")
    token = r.json()["token"]
    assert r.json()["url"].endswith(f"/api/garantias/publico/{token}")
    ctx.get(f"/garantias/publico/{token}", headers={"user-agent": "WhatsApp/2.0"})
    p = ctx.get(f"/garantias/publico/{token}", headers={"user-agent": "Mozilla/5.0"})
    assert p.status_code == 200 and "og:title" in p.text
    assert ctx.fake.garantias.docs[0]["link_views"] == 1
    assert ctx.get(f"/garantias/publico/{token}/pdf").content.startswith(b"%PDF-")
    ev = ctx.get(f"/garantias/{g['id']}/link-eventos").json()
    assert ev["resumo"]["views"] == 1
    ctx.delete(f"/garantias/{g['id']}/compartilhar")
    assert ctx.get(f"/garantias/publico/{token}").status_code == 404


def test_put_do_wizard_nao_apaga_estado_do_servidor(ctx):
    g = _nova(ctx)
    ctx.post(f"/garantias/{g['id']}/compartilhar")
    ctx.fake.garantias.docs[0]["icp_status"] = "assinado"
    ctx.put(f"/garantias/{g['id']}", json={**g, "descricao_bem": "editado"})
    d = ctx.fake.garantias.docs[0]
    assert d["descricao_bem"] == "editado"
    assert d["link_publico_ativo"] is True and d["icp_status"] == "assinado"


def test_clone_nao_herda_assinatura_link_nem_recibo(ctx):
    g = _nova(ctx)
    ctx.post(f"/garantias/{g['id']}/compartilhar")
    ctx.fake.garantias.docs[0].update({"icp_status": "assinado", "recibo_emitido": True})
    r = ctx.post(f"/garantias/{g['id']}/clonar")
    c = r.json()
    assert c["id"] != g["id"] and c["numero"] != g["numero"]
    assert c["descricao_bem"] == "Fazenda Boa Vista"
    assert not c.get("icp_status") and not c.get("link_publico_ativo") and not c.get("recibo_emitido")
    assert c["status"] == "rascunho"


def test_recibo(ctx):
    g = _nova(ctx)
    r = ctx.post(f"/garantias/{g['id']}/recibo", json={"valor_honorarios": 2500})
    assert r.status_code == 200, r.text
    assert ctx.fake.garantias.docs[0]["recibo_emitido"] is True
    assert ctx.fake.recibos.docs[0]["garantia_id"] == g["id"]
    b = ctx.get(f"/garantias/{g['id']}/recibo")
    assert b.status_code == 200 and b.content.startswith(b"%PDF-")


def test_isolamento(ctx):
    g = _nova(ctx)
    ctx.como(USER_B)
    for metodo, url in [("get", f"/garantias/{g['id']}/pdf"), ("post", f"/garantias/{g['id']}/clonar"),
                        ("post", f"/garantias/{g['id']}/compartilhar"),
                        ("delete", f"/garantias/{g['id']}")]:
        assert getattr(ctx, metodo)(url).status_code == 404
    r = ctx.post(f"/garantias/{g['id']}/whatsapp", json={"phone": "5599991811246"})
    assert r.status_code == 404
