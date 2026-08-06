# Testes do CRUD de credenciais BYOK: máscara, upsert, padrão exclusivo, isolamento multi-tenant.
import asyncio

import pytest

from services.assinatura import credenciais as CRED
from services.assinatura.catalogo import catalogo_publico, SLUGS


# ── Fake DB async (padrão dos testes de serviço do repo) ──────────────────────
class _Cursor:
    def __init__(self, docs):
        self._docs = docs
    async def to_list(self, length=None):
        return [dict(d) for d in self._docs]


class _Coll:
    def __init__(self):
        self.docs = []
    def _match(self, d, flt):
        return all(d.get(k) == v for k, v in flt.items())
    def find(self, flt):
        return _Cursor([d for d in self.docs if self._match(d, flt)])
    async def find_one(self, flt):
        return next((d for d in self.docs if self._match(d, flt)), None)
    async def insert_one(self, doc):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("id")})()
    async def update_one(self, flt, upd):
        d = next((d for d in self.docs if self._match(d, flt)), None)
        if d:
            d.update(upd.get("$set", {}))
            return type("R", (), {"modified_count": 1})()
        return type("R", (), {"modified_count": 0})()
    async def update_many(self, flt, upd):
        n = 0
        for d in self.docs:
            if self._match(d, flt):
                d.update(upd.get("$set", {}))
                n += 1
        return type("R", (), {"modified_count": n})()
    async def delete_one(self, flt):
        for i, d in enumerate(self.docs):
            if self._match(d, flt):
                del self.docs[i]
                return type("R", (), {"deleted_count": 1})()
        return type("R", (), {"deleted_count": 0})()


class _DB:
    def __init__(self):
        self._c = {}
    def __getitem__(self, name):
        return self._c.setdefault(name, _Coll())


_D4 = {"token_api": "TOK123456789", "crypt_key": "CK987654321", "uuid_safe": "cofre-1"}


def test_rotas_registradas():
    from routes.assinatura_externa import router
    paths = {getattr(r, "path", None) for r in router.routes}
    assert "/assinatura-externa/provedores" in paths
    assert "/assinatura-externa/credenciais" in paths
    assert "/assinatura-externa/credenciais/{provider}/padrao" in paths


def test_catalogo_tem_os_tres_provedores_sem_segredo():
    cat = catalogo_publico()
    assert set(SLUGS) == {"d4sign", "clicksign", "autentique"}
    assert {p["slug"] for p in cat} == {"d4sign", "clicksign", "autentique"}
    # nenhum segredo no catálogo, só descritores de campo
    assert all("credenciais_encrypted" not in p for p in cat)


def test_salvar_e_listar_mascarado():
    db = _DB()
    out = asyncio.run(CRED.salvar(db, "u1", "d4sign", "producao", _D4))
    assert out["provider"] == "d4sign"
    assert out["credenciais_mascaradas"]["token_api"].endswith("6789")
    assert out["credenciais_mascaradas"]["token_api"].startswith("•")
    assert "TOK123456789" not in str(out)          # nunca em claro
    lst = asyncio.run(CRED.listar(db, "u1"))
    assert len(lst) == 1
    assert lst[0]["credenciais_mascaradas"]["crypt_key"].endswith("4321")


def test_campos_obrigatorios_faltando():
    db = _DB()
    with pytest.raises(CRED.CredencialInvalida):
        asyncio.run(CRED.salvar(db, "u1", "clicksign", "producao", {}))


def test_upsert_nao_duplica():
    db = _DB()
    asyncio.run(CRED.salvar(db, "u1", "d4sign", "producao", _D4))
    asyncio.run(CRED.salvar(db, "u1", "d4sign", "sandbox",
                            {"token_api": "X" * 12, "crypt_key": "Y" * 12, "uuid_safe": "c2"}))
    lst = asyncio.run(CRED.listar(db, "u1"))
    assert len(lst) == 1 and lst[0]["ambiente"] == "sandbox"


def test_edicao_parcial_mantem_campos_nao_digitados():
    db = _DB()
    asyncio.run(CRED.salvar(db, "u1", "d4sign", "producao", _D4))
    # edita SÓ o cofre; token/crypt vêm vazios (mascarados na UI) → mantém os atuais
    asyncio.run(CRED.salvar(db, "u1", "d4sign", "producao",
                            {"token_api": "", "crypt_key": "", "uuid_safe": "cofre-2"}))
    doc, cred = asyncio.run(CRED.obter_decifrada(db, "u1", "d4sign"))
    assert cred["token_api"] == "TOK123456789"   # preservado
    assert cred["uuid_safe"] == "cofre-2"          # atualizado


def test_definir_padrao_exclusivo():
    db = _DB()
    asyncio.run(CRED.salvar(db, "u1", "d4sign", "producao", _D4))
    asyncio.run(CRED.salvar(db, "u1", "clicksign", "producao", {"access_token": "C" * 12}, padrao=True))
    asyncio.run(CRED.definir_padrao(db, "u1", "d4sign"))
    padrao = {c["provider"]: c["padrao"] for c in asyncio.run(CRED.listar(db, "u1"))}
    assert padrao["d4sign"] is True and padrao["clicksign"] is False


def test_isolamento_multi_tenant():
    db = _DB()
    asyncio.run(CRED.salvar(db, "u1", "d4sign", "producao", _D4))
    assert asyncio.run(CRED.listar(db, "u2")) == []                     # u2 não vê
    assert asyncio.run(CRED.remover(db, "u2", "d4sign")) is False       # u2 não apaga
    assert len(asyncio.run(CRED.listar(db, "u1"))) == 1                 # u1 intacto


def test_obter_decifrada_por_usuario():
    db = _DB()
    asyncio.run(CRED.salvar(db, "u1", "autentique", "sandbox", {"api_token": "SECRETTOKEN99"}))
    doc, cred = asyncio.run(CRED.obter_decifrada(db, "u1", "autentique"))
    assert cred["api_token"] == "SECRETTOKEN99"
    d2, c2 = asyncio.run(CRED.obter_decifrada(db, "u2", "autentique"))   # user errado
    assert d2 is None and c2 is None
