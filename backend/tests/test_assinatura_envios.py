# Testes do ciclo de envio BYOK: criar, sincronizar, webhook (HMAC/idempotência/d4sign), polling.
import asyncio
import hashlib
import hmac
from datetime import datetime, timedelta

import pytest

from services.assinatura import envios as ENV
from services.assinatura import factory
from services.assinatura.base import EnvioResult, OpcoesEnvio, SignatarioEnvio, StatusResult, WebhookEvent


# ── Fakes ─────────────────────────────────────────────────────────────────────
class _Cur:
    def __init__(self, docs):
        self._d = docs
    def sort(self, key, direction=1):
        self._d = sorted(self._d, key=lambda x: x.get(key) or 0, reverse=direction < 0)
        return self
    async def to_list(self, length=None):
        return [dict(x) for x in (self._d if length is None else self._d[:length])]


class _Coll:
    def __init__(self):
        self.docs = []
    def _match(self, d, flt):
        for k, v in flt.items():
            if isinstance(v, dict) and "$in" in v:
                if d.get(k) not in v["$in"]:
                    return False
            elif isinstance(v, dict) and "$lt" in v:
                if not (d.get(k) is not None and d.get(k) < v["$lt"]):
                    return False
            elif d.get(k) != v:
                return False
        return True
    def find(self, flt):
        return _Cur([d for d in self.docs if self._match(d, flt)])
    async def find_one(self, flt):
        return next((d for d in self.docs if self._match(d, flt)), None)
    async def insert_one(self, doc):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("id")})()
    async def update_one(self, flt, upd):
        d = next((d for d in self.docs if self._match(d, flt)), None)
        if not d:
            return type("R", (), {"modified_count": 0})()
        d.update(upd.get("$set", {}))
        for k, v in (upd.get("$push") or {}).items():
            d.setdefault(k, []).append(v)
        return type("R", (), {"modified_count": 1})()


class _DB:
    def __init__(self):
        self._c = {}
    def __getitem__(self, n):
        return self._c.setdefault(n, _Coll())


class FakeAdapter:
    def __init__(self, status="assinado", provider_doc_id="PDOC1", ambiente="producao"):
        self.ambiente = ambiente
        self._status = status
        self._pdoc = provider_doc_id
        self.cancelado = False
        self.opc = None
    async def enviar_documento(self, pdf, nome, sigs, opc):
        self.opc = opc
        return EnvioResult(provider_doc_id=self._pdoc)
    async def consultar_status(self, pid):
        return StatusResult(status=self._status, signatarios=[{"signatario": "joao@x.com", "status": "assinado"}])
    async def cancelar(self, pid, motivo=""):
        self.cancelado = True
        return True
    async def baixar_assinado(self, pid):
        return b"%PDF-signed"
    def parse_webhook(self, headers, body):
        return WebhookEvent(tipo=str(body.get("type") or body.get("event") or "status"),
                            provider_doc_id=self._pdoc, signatario=body.get("email"),
                            novo_status="assinado", raw=body)


def _patch(monkeypatch, adapter):
    async def _gp(db, uid, prov):
        return adapter
    monkeypatch.setattr(factory, "get_provider", _gp)


# ── Testes ────────────────────────────────────────────────────────────────────
def test_criar_envio_persiste_com_hash_e_webhook_url(monkeypatch):
    db = _DB(); ad = FakeAdapter(); _patch(monkeypatch, ad)
    sigs = [SignatarioEnvio(nome="João", email="joao@x.com")]
    out = asyncio.run(ENV.criar_envio(db, "u1", "d4sign", "ptam", "PT1", b"%PDF x", "doc.pdf", sigs, OpcoesEnvio()))
    assert out["status"] == "enviado" and out["provider_doc_id"] == "PDOC1"
    assert "webhook_secret" not in out                        # nunca exposto
    assert out["hash_arquivo_original"] == hashlib.sha256(b"%PDF x").hexdigest()
    assert ad.opc.webhook_url.endswith(f"/webhook/d4sign/{out['id']}")


def test_isolamento_envios(monkeypatch):
    db = _DB()
    db["assinatura_envios"].docs.append({"id": "E0", "user_id": "u1", "provider": "d4sign", "status": "enviado", "created_at": 1})
    assert asyncio.run(ENV.obter_raw(db, "u2", "E0")) is None
    assert asyncio.run(ENV.listar_envios(db, "u2")) == []


def test_sincronizar_atualiza_status_e_signatarios(monkeypatch):
    db = _DB(); _patch(monkeypatch, FakeAdapter(status="assinado"))
    envio = {"id": "E1", "user_id": "u1", "provider": "clicksign", "provider_doc_id": "P1",
             "signatarios": [{"email": "joao@x.com", "status": "pendente"}]}
    db["assinatura_envios"].docs.append(dict(envio))
    assert asyncio.run(ENV.sincronizar(db, "u1", envio)) == "assinado"
    doc = asyncio.run(db["assinatura_envios"].find_one({"id": "E1"}))
    assert doc["status"] == "assinado" and doc["signatarios"][0]["status"] == "assinado"


def test_webhook_hmac_invalido_levanta(monkeypatch):
    db = _DB(); _patch(monkeypatch, FakeAdapter())
    db["assinatura_envios"].docs.append({"id": "E2", "user_id": "u1", "provider": "clicksign",
                                         "provider_doc_id": "P2", "webhook_secret": "sec", "signatarios": []})
    with pytest.raises(ENV.WebhookInvalido):
        asyncio.run(ENV.processar_webhook(db, "clicksign", "E2", {"content-hmac": "sha256=bad"},
                                          b'{"event":"x"}', {"event": "x"}))


def test_webhook_hmac_valido_e_idempotente(monkeypatch):
    db = _DB(); _patch(monkeypatch, FakeAdapter())
    secret, raw = "sec", b'{"event":"sign"}'
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    db["assinatura_envios"].docs.append({"id": "E3", "user_id": "u1", "provider": "clicksign",
                                         "provider_doc_id": "P3", "webhook_secret": secret, "signatarios": []})
    r1 = asyncio.run(ENV.processar_webhook(db, "clicksign", "E3", {"content-hmac": sig}, raw, {"event": "sign"}))
    assert r1["ok"] is True and not r1.get("idempotente")
    r2 = asyncio.run(ENV.processar_webhook(db, "clicksign", "E3", {"content-hmac": sig}, raw, {"event": "sign"}))
    assert r2.get("idempotente") is True                      # duplicado não reprocessa


def test_webhook_d4sign_confirma_via_api(monkeypatch):
    db = _DB(); _patch(monkeypatch, FakeAdapter(status="assinado"))
    db["assinatura_envios"].docs.append({"id": "E4", "user_id": "u1", "provider": "d4sign",
                                         "provider_doc_id": "P4",
                                         "signatarios": [{"email": "joao@x.com", "status": "pendente"}]})
    r = asyncio.run(ENV.processar_webhook(db, "d4sign", "E4", {}, b'{"uuid":"P4","type":"Finalizado"}',
                                          {"uuid": "P4", "type": "Finalizado"}))
    assert r["ok"] is True
    assert asyncio.run(db["assinatura_envios"].find_one({"id": "E4"}))["status"] == "assinado"


def test_webhook_envio_inexistente_ignora_sem_vazar():
    r = asyncio.run(ENV.processar_webhook(_DB(), "clicksign", "NOPE", {}, b"{}", {}))
    assert r.get("ignorado")


def test_polling_so_pega_antigos_pendentes(monkeypatch):
    db = _DB(); _patch(monkeypatch, FakeAdapter(status="assinado"))
    velho = datetime.utcnow() - timedelta(hours=3)
    novo = datetime.utcnow()
    db["assinatura_envios"].docs += [
        {"id": "A", "user_id": "u1", "provider": "clicksign", "provider_doc_id": "PA",
         "status": "enviado", "updated_at": velho, "signatarios": []},
        {"id": "B", "user_id": "u1", "provider": "clicksign", "provider_doc_id": "PB",
         "status": "enviado", "updated_at": novo, "signatarios": []},          # recente → ignora
        {"id": "C", "user_id": "u1", "provider": "clicksign", "provider_doc_id": "PC",
         "status": "assinado", "updated_at": velho, "signatarios": []},        # já finalizado → ignora
    ]
    assert asyncio.run(ENV.rodar_polling(db)) == 1
    assert asyncio.run(db["assinatura_envios"].find_one({"id": "A"}))["status"] == "assinado"
