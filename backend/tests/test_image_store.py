import asyncio
import base64

from services import image_store


class FakeImages:
    def __init__(self):
        self.docs = {}

    async def insert_one(self, doc):
        self.docs[doc["id"]] = doc

    async def find_one(self, filtro):
        for d in self.docs.values():
            if all(d.get(k) == v for k, v in filtro.items()):
                return d
        return None

    async def delete_one(self, filtro):
        self.docs = {k: v for k, v in self.docs.items() if v.get("id") != filtro.get("id")}


class FakeDB:
    def __init__(self):
        self.images = FakeImages()


def test_salva_base64_quando_sem_r2(monkeypatch):
    monkeypatch.setattr(image_store, "r2_ativo", lambda: False)
    db = FakeDB()
    doc = asyncio.run(
        image_store.salvar_imagem(db, "u1", b"\xff\xd8\xffdata", "image/jpeg", "f.jpg")
    )
    assert doc.get("data_b64") and "r2_key" not in doc
    assert asyncio.run(image_store.carregar_bytes(db, doc["id"])) == b"\xff\xd8\xffdata"


def test_salva_no_r2_quando_ativo(monkeypatch):
    monkeypatch.setattr(image_store, "r2_ativo", lambda: True)
    subiu = {}

    def fake_upload(data, key, content_type, **kw):
        subiu["key"], subiu["data"] = key, data
        return "http://r2/" + key

    monkeypatch.setattr(image_store.r2_storage, "upload_bytes", fake_upload)
    monkeypatch.setattr(image_store.r2_storage, "download_bytes", lambda k: subiu["data"])
    db = FakeDB()
    doc = asyncio.run(image_store.salvar_imagem(db, "u1", b"PNGdata", "image/png", "f.png"))
    assert doc.get("r2_key", "").startswith("images/u1/") and "data_b64" not in doc
    assert asyncio.run(image_store.carregar_bytes(db, doc["id"])) == b"PNGdata"


def test_carrega_legado_data_b64(monkeypatch):
    monkeypatch.setattr(image_store, "r2_ativo", lambda: True)
    db = FakeDB()
    asyncio.run(
        db.images.insert_one(
            {"id": "old1", "user_id": "u1", "data_b64": base64.b64encode(b"antigo").decode()}
        )
    )
    assert asyncio.run(image_store.carregar_bytes(db, "old1")) == b"antigo"


def test_r2_falha_cai_para_base64(monkeypatch):
    monkeypatch.setattr(image_store, "r2_ativo", lambda: True)

    def boom(*a, **k):
        raise RuntimeError("r2 down")

    monkeypatch.setattr(image_store.r2_storage, "upload_bytes", boom)
    db = FakeDB()
    doc = asyncio.run(image_store.salvar_imagem(db, "u1", b"xy", "image/png", "f.png"))
    assert doc.get("data_b64") and "r2_key" not in doc


def test_find_one_preenche_data_b64_do_r2(monkeypatch):
    monkeypatch.setattr(image_store, "r2_ativo", lambda: True)
    monkeypatch.setattr(image_store.r2_storage, "upload_bytes", lambda d, k, c, **kw: "u")
    monkeypatch.setattr(image_store.r2_storage, "download_bytes", lambda k: b"\x89PNGbytes")
    db = FakeDB()
    doc = asyncio.run(image_store.salvar_imagem(db, "u1", b"\x89PNGbytes", "image/png", "f.png"))
    assert "data_b64" not in doc  # salvo no R2
    got = asyncio.run(image_store.find_one(db, {"id": doc["id"]}))
    # find_one preenche data_b64 baixando do R2 → leitor legado funciona
    assert base64.b64decode(got["data_b64"]) == b"\x89PNGbytes"


def test_find_one_legado_mantem_data_b64(monkeypatch):
    monkeypatch.setattr(image_store, "r2_ativo", lambda: True)
    db = FakeDB()
    asyncio.run(
        db.images.insert_one(
            {"id": "leg", "user_id": "u1", "data_b64": base64.b64encode(b"legado").decode()}
        )
    )
    got = asyncio.run(image_store.find_one(db, {"id": "leg"}))
    assert base64.b64decode(got["data_b64"]) == b"legado"


def test_remover_apaga_do_r2_e_do_mongo(monkeypatch):
    monkeypatch.setattr(image_store, "r2_ativo", lambda: True)
    apagou = {}
    monkeypatch.setattr(image_store.r2_storage, "upload_bytes", lambda d, k, c, **kw: "u")
    monkeypatch.setattr(
        image_store.r2_storage, "delete_object", lambda k: apagou.setdefault("key", k)
    )
    db = FakeDB()
    doc = asyncio.run(image_store.salvar_imagem(db, "u1", b"z", "image/png", "f.png"))
    ok = asyncio.run(image_store.remover_imagem(db, doc["id"], uid="u1"))
    assert ok and apagou.get("key") == doc["r2_key"]
    assert asyncio.run(image_store.carregar_bytes(db, doc["id"])) is None
