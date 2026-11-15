# @module tests.test_prospeccao_wa_erros — fila de WhatsApp não queima tentativas por falha da Z-API.
import asyncio

from routes import prospeccao as P
from tests.test_atendimento_bot import _Coll, _DB as _BaseDB


class _C(_Coll):
    async def find_one(self, f, *a, sort=None, **k):
        docs = [d for d in self.docs if all(_match_ok(d, f) for _ in [0])]
        if sort:
            campo, _dir = sort[0]
            docs.sort(key=lambda d: d.get(campo) or "")
        return docs[0] if docs else None

    async def update_one(self, f, u, upsert=False):
        r = await _Coll.update_one(self, f, u)
        if not r.matched_count and upsert:
            novo = {k: v for k, v in f.items() if not k.startswith("$")}
            self.docs.append(novo)
            await _Coll.update_one(self, f, u)
        return r


def _match_ok(d, f):
    from tests.test_atendimento_bot import _match
    return _match(d, f)


class _DB(_BaseDB):
    def __getitem__(self, n):
        return self.c.setdefault(n, _C())


def _prospects(db, n=3):
    for i in range(n):
        db.prospeccao.docs.append({"id": f"p{i}", "user_id": "u", "nome": f"Imob {i}", "cidade": "X",
                                   "telefone": f"5599988880{i:03d}", "status": 0, "opt_out": False,
                                   "whatsapp_enviado_em": None})


def _rodar(monkeypatch, envio, conectado=True, limite=1):
    db = _DB()
    _prospects(db)
    db.prospeccao_campanha.docs.append({"_id": "u", "wa_limite_dia": 2})

    async def integ(_db, _uid):
        return {"zapi_instance_id": "i", "zapi_token": "t"}

    async def status_instance(*a, **k):
        return {"connected": conectado}

    async def dorme(*a, **k):
        return None

    monkeypatch.setattr("services.integracoes_util.carregar_integracoes", integ)
    monkeypatch.setattr("services.zapi_service.status_instance", status_instance)
    monkeypatch.setattr("services.zapi_service.send_text", envio)
    monkeypatch.setattr(P.asyncio, "sleep", dorme)
    n = asyncio.run(P._rodar_whatsapp(db, "u", limite))
    return db, n


def test_desconectada_nao_gasta_tentativa(monkeypatch):
    async def envio(**k):
        raise AssertionError("não deveria enviar")
    db, n = _rodar(monkeypatch, envio, conectado=False)
    assert n == 0
    assert all(not p.get("wa_tentativas") for p in db.prospeccao.docs)
    assert db.prospeccao_campanha.docs[0]["wa_ultimo_erro"]


def test_falha_da_zapi_para_o_lote_sem_queimar_contato(monkeypatch):
    async def envio(**k):
        raise RuntimeError("Z-API erro 500: instance not connected")
    db, n = _rodar(monkeypatch, envio, limite=2)
    assert n == 0
    assert all(not p.get("wa_tentativas") for p in db.prospeccao.docs)
    assert sum(1 for p in db.prospeccao.docs if p.get("whatsapp_erro")) == 1   # parou no 1º


def test_numero_sem_whatsapp_sai_da_fila_e_tenta_o_proximo(monkeypatch):
    chamados = []

    async def envio(**k):
        chamados.append(k["phone"])
        if len(chamados) == 1:
            raise RuntimeError("Z-API não entregou a mensagem (número pode não ter WhatsApp).")
        return {"messageId": "x"}
    db, n = _rodar(monkeypatch, envio, limite=1)
    assert n == 1 and len(chamados) == 2
    invalido = [p for p in db.prospeccao.docs if p.get("whatsapp_invalido")]
    assert len(invalido) == 1
    fila = P._wa_query("u", 4)
    assert fila["whatsapp_invalido"] == {"$ne": True}


def test_motivo_legivel():
    assert P._motivo_legivel("RuntimeError: Z-API não entregou a mensagem") == "Número sem WhatsApp ou inválido"
    assert "desconectado" in P._motivo_legivel("instance not connected")
    assert P._motivo_legivel("") == ""
