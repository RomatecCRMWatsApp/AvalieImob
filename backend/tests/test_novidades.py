# Testes da Central de Novidades: seed, pendentes/dispensar, público-alvo, idempotência, métricas.
import asyncio
from datetime import datetime, timedelta

import pytest

from services import novidades as NOV


class _Cur:
    def __init__(self, docs):
        self._d = docs
    def sort(self, key, direction=1):
        self._d = sorted(self._d, key=lambda x: (x.get(key) is None, x.get(key)), reverse=direction < 0)
        return self
    async def to_list(self, length=None):
        return [dict(x) for x in self._d]


class _Coll:
    def __init__(self):
        self.docs = []
    def _m(self, d, f):
        return all(d.get(k) == v for k, v in f.items())
    def find(self, f):
        return _Cur([d for d in self.docs if self._m(d, f)])
    async def find_one(self, f):
        return next((d for d in self.docs if self._m(d, f)), None)
    async def insert_one(self, doc):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("id")})()
    async def update_one(self, f, upd, upsert=False):
        d = next((d for d in self.docs if self._m(d, f)), None)
        if d:
            d.update(upd.get("$set", {}))
            return type("R", (), {"modified_count": 1})()
        if upsert:
            nd = dict(f); nd.update(upd.get("$setOnInsert", {})); nd.update(upd.get("$set", {}))
            self.docs.append(nd)
            return type("R", (), {"modified_count": 0, "upserted_id": nd.get("id")})()
        return type("R", (), {"modified_count": 0})()
    async def count_documents(self, f):
        return len([d for d in self.docs if self._m(d, f)])


class _DB:
    def __init__(self):
        self._c = {}
    def __getitem__(self, n):
        return self._c.setdefault(n, _Coll())
    def __getattr__(self, n):
        if n.startswith("_"):
            raise AttributeError(n)
        return self._c.setdefault(n, _Coll())


def test_seed_publicada_false_e_idempotente():
    db = _DB()
    asyncio.run(NOV.seed_inicial(db))
    n = asyncio.run(db[NOV.C_NOV].find_one({"slug": "assinatura-digital-byok"}))
    assert n and n["publicada"] is False
    asyncio.run(NOV.seed_inicial(db))
    assert asyncio.run(db[NOV.C_NOV].count_documents({})) == 1


def test_pendentes_so_publicadas_e_some_ao_dispensar():
    db = _DB(); db.users.docs.append({"id": "u1", "created_at": datetime.utcnow()})
    asyncio.run(NOV.seed_inicial(db))
    assert asyncio.run(NOV.listar_pendentes(db, "u1")) == []            # ainda não publicada
    nid = asyncio.run(db[NOV.C_NOV].find_one({}))["id"]
    asyncio.run(NOV.publicar(db, nid))
    p = asyncio.run(NOV.listar_pendentes(db, "u1"))
    assert len(p) == 1 and "conteudo_md" in p[0]                        # modal recebe o conteúdo
    asyncio.run(NOV.dispensar(db, "u1", nid))
    assert asyncio.run(NOV.listar_pendentes(db, "u1")) == []            # dispensou → não volta


def test_visualizada_nao_duplica():
    db = _DB(); db.users.docs.append({"id": "u1", "created_at": datetime.utcnow()})
    asyncio.run(NOV.seed_inicial(db))
    nid = asyncio.run(db[NOV.C_NOV].find_one({}))["id"]
    asyncio.run(NOV.marcar_visualizada(db, "u1", nid))
    asyncio.run(NOV.marcar_visualizada(db, "u1", nid))
    assert asyncio.run(db[NOV.C_VIS].count_documents({"user_id": "u1"})) == 1


def test_publico_alvo_existentes_vs_novos():
    db = _DB()
    n = asyncio.run(NOV.criar(db, {"slug": "x", "titulo": "T", "publico_alvo": "existentes"}))
    asyncio.run(NOV.publicar(db, n["id"]))
    pub = asyncio.run(db[NOV.C_NOV].find_one({"id": n["id"]}))["publicada_em"]
    db.users.docs.append({"id": "antigo", "created_at": pub - timedelta(days=1)})
    db.users.docs.append({"id": "novo", "created_at": pub + timedelta(days=1)})
    assert len(asyncio.run(NOV.listar_pendentes(db, "antigo"))) == 1     # existente vê
    assert asyncio.run(NOV.listar_pendentes(db, "novo")) == []           # novo não vê


def test_criar_slug_duplicado_erro():
    db = _DB()
    asyncio.run(NOV.criar(db, {"slug": "y", "titulo": "A"}))
    with pytest.raises(ValueError):
        asyncio.run(NOV.criar(db, {"slug": "y", "titulo": "B"}))


def test_metricas():
    db = _DB(); db.users.docs += [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    nid = asyncio.run(NOV.criar(db, {"slug": "m", "titulo": "M"}))["id"]
    asyncio.run(NOV.marcar_visualizada(db, "a", nid))
    asyncio.run(NOV.dispensar(db, "b", nid))
    asyncio.run(NOV.registrar_cta(db, "a", nid))
    m = asyncio.run(NOV.metricas(db, nid))
    assert m["destinatarios"] == 3 and m["vistos"] >= 1 and m["dispensados"] == 1 and m["cta_clicados"] == 1


def test_rotas_registradas():
    from routes.novidades import router
    paths = {getattr(r, "path", None) for r in router.routes}
    assert "/novidades/pendentes" in paths
    assert "/novidades/admin" in paths
    assert "/novidades/{novidade_id}/dispensar" in paths
