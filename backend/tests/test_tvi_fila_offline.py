# @module tests.test_tvi_fila_offline — reenvio da fila offline não duplica nada.
#
# O celular grava a vistoria na fila e reenvia até receber resposta. Se a 1ª tentativa
# chegou ao servidor e só a resposta se perdeu, o reenvio traz a MESMA chave
# (client_id / client_photo_id) e o servidor devolve o que já existe.
# Sem chave, o comportamento é o de sempre (cada envio cria um registro).
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber
from tests.fake_mongo import FakeDB

A, B = "conta-A", "conta-B"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture()
def ctx(monkeypatch):
    from routes.tvi import router

    async def _salvar(db, uid, data, ct, nome, image_id=None):
        return image_id

    monkeypatch.setattr("services.image_store.salvar_imagem", _salvar)
    fake = FakeDB()
    atual = {"uid": A}
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_active_subscriber] = lambda: atual["uid"]
    with TestClient(app) as c:
        c.fake = fake
        c.como = lambda uid: atual.update({"uid": uid})
        yield c


def _criar(c, **extra):
    r = c.post("/tvi/vistoria", json={"model_id": "TVI-01", "titulo": "Casa", **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_reenvio_com_mesma_chave_nao_duplica_a_vistoria(ctx):
    v1 = _criar(ctx, client_id="cel-123")
    v2 = _criar(ctx, client_id="cel-123")
    assert v1["id"] == v2["id"] and v1["numero_tvi"] == v2["numero_tvi"]
    assert len(ctx.fake.vistorias.docs) == 1


def test_sem_chave_cada_envio_cria_uma_vistoria(ctx):
    _criar(ctx)
    _criar(ctx)
    assert len(ctx.fake.vistorias.docs) == 2


def test_mesma_chave_em_contas_diferentes_nao_se_mistura(ctx):
    va = _criar(ctx, client_id="cel-123")
    ctx.como(B)
    vb = _criar(ctx, client_id="cel-123")
    assert va["id"] != vb["id"]
    assert {d["user_id"] for d in ctx.fake.vistorias.docs} == {A, B}


def _foto(c, vid, chave=None):
    data = {"ambiente": "Sala", "gps_lat": "-4.94", "gps_lng": "-47.45"}
    if chave:
        data["client_photo_id"] = chave
    return c.post(f"/tvi/vistoria/{vid}/photos", data=data,
                  files={"files": ("f.png", PNG, "image/png")})


def test_reenvio_da_mesma_foto_nao_duplica(ctx):
    vid = _criar(ctx, client_id="cel-1")["id"]
    r1 = _foto(ctx, vid, "foto-1")
    r2 = _foto(ctx, vid, "foto-1")
    assert r1.status_code == 201 and r2.status_code == 201
    assert r2.json().get("repetida") is True
    assert r1.json()["photos"][0]["id"] == r2.json()["photos"][0]["id"]
    assert len(ctx.fake.vistoria_photos.docs) == 1
    assert _foto(ctx, vid, "foto-2").status_code == 201
    assert len(ctx.fake.vistoria_photos.docs) == 2


def test_gps_da_foto_e_gravado(ctx):
    vid = _criar(ctx)["id"]
    _foto(ctx, vid, "foto-1")
    gps = ctx.fake.vistoria_photos.docs[0]["gps"]
    assert gps["lat"] == pytest.approx(-4.94) and gps["lng"] == pytest.approx(-47.45)


def test_reenvio_da_assinatura_nao_duplica(ctx):
    vid = _criar(ctx)["id"]
    corpo = {"data_b64": "data:image/png;base64,AA==", "signatario": "José", "client_id": "ass-1"}
    a1 = ctx.post(f"/tvi/vistoria/{vid}/signature", json=corpo)
    a2 = ctx.post(f"/tvi/vistoria/{vid}/signature", json=corpo)
    assert a1.status_code == a2.status_code == 201
    assert a1.json()["id"] == a2.json()["id"]
    assert len(ctx.fake.vistoria_signatures.docs) == 1


def test_foto_em_vistoria_de_outra_conta_e_barrada(ctx):
    vid = _criar(ctx)["id"]
    ctx.como(B)
    assert _foto(ctx, vid, "foto-x").status_code == 404
    assert ctx.fake.vistoria_photos.docs == []
