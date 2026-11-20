# @module tests.test_evidencias — linha do tempo de evidências (só leitura).
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber
from services.evidencias import eventos_ptam, eventos_tvi
from tests.fake_mongo import FakeDB

DONO = "dono"


def _cliente(modulo, fake):
    import importlib
    app = FastAPI()
    app.include_router(importlib.import_module(modulo).router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_active_subscriber] = lambda: DONO
    return TestClient(app)


def test_eventos_do_ptam_em_ordem_e_com_hash_do_lacre():
    ptam = {"numero_ptam": "0007", "created_at": "2026-11-01T10:00:00",
            "icp_status": "assinado", "icp_signed_at": "2026-11-03T09:00:00",
            "icp_titular": "JOSÉ", "icp_hash": "abc"}
    versoes = [
        {"id": "v2", "tipo": "lacrado", "numero_versao": 2, "hash_sha256": "h2",
         "numero_lacre": "PTAM-2026-0007-v2", "created_at": "2026-11-02T12:00:00"},
        {"id": "v1", "tipo": "auto", "numero_versao": 1, "hash_sha256": "h1",
         "diffs": [{}, {}], "created_at": "2026-11-02T08:00:00"},
    ]
    link = [{"tipo": "visualizado", "created_at": "2026-11-04T08:00:00",
             "ip": "1.2.3.4", "user_agent": "x"}]
    ev = eventos_ptam(ptam, versoes, link)
    assert [e["tipo"] for e in ev] == ["criado", "versao", "lacre", "assinatura", "link_visualizado"]
    lacre = next(e for e in ev if e["tipo"] == "lacre")
    assert lacre["hash_sha256"] == "h2" and lacre["referencia"] == "PTAM-2026-0007-v2"
    assert "1.2.3.4" not in str(ev)  # IP de quem abriu o link não aparece


def test_eventos_da_vistoria_com_gps_e_hash_da_assinatura():
    vist = {"numero_tvi": "TVI-0003/2026", "client_id": "cel-1", "created_at": "2026-11-01T10:00:00"}
    fotos = [{"id": "f1", "ambiente": "Sala", "timestamp": "2026-11-01T10:05:00",
              "gps": {"lat": -4.9458, "lng": -47.4555}, "url": "/api/upload/image/x"}]
    assin = [{"signatario": "Maria", "data_b64": "AAA", "created_at": "2026-11-01T10:20:00"}]
    ev = eventos_tvi(vist, fotos, assin)
    assert [e["tipo"] for e in ev] == ["criado", "foto", "assinatura"]
    assert "fila" in ev[0]["detalhe"]
    assert "-4.945800" in ev[1]["detalhe"]
    assert len(ev[2]["hash_sha256"]) == 64
    assert "AAA" not in str(ev)  # a imagem da assinatura não é devolvida


def test_rota_do_ptam_nao_altera_nada_e_mostra_o_lacre():
    fake = FakeDB()
    fake.ptam_documents.docs.append({"id": "p1", "user_id": DONO, "numero_ptam": "0001",
                                     "created_at": "2026-11-01T10:00:00"})
    fake.ptam_versions.docs.append({"id": "v1", "ptam_id": "p1", "user_id": DONO,
                                    "tipo": "lacrado", "numero_versao": 1, "hash_sha256": "hh",
                                    "snapshot": {"grande": "x"}, "created_at": "2026-11-02"})
    antes = [dict(d) for d in fake.ptam_documents.docs]
    with _cliente("routes.ptam", fake) as c:
        r = c.get("/ptam/p1/evidencias")
    assert r.status_code == 200
    tipos = [e["tipo"] for e in r.json()["eventos"]]
    assert tipos == ["criado", "lacre"]
    assert "grande" not in r.text  # snapshot não vem junto
    assert fake.ptam_documents.docs == antes


def test_rota_da_vistoria_lista_fotos_e_assinaturas():
    fake = FakeDB()
    fake.vistorias.docs.append({"id": "t1", "user_id": DONO, "model_id": "M",
                                "created_at": "2026-11-01T10:00:00"})
    fake.vistoria_photos.docs.append({"id": "f1", "vistoria_id": "t1", "ambiente": "Cozinha",
                                      "url": "/u", "timestamp": "2026-11-01T10:01:00"})
    fake.vistoria_signatures.docs.append({"id": "s1", "vistoria_id": "t1", "signatario": "Ana",
                                          "data_b64": "ZZ", "created_at": "2026-11-01T10:09:00"})
    with _cliente("routes.tvi", fake) as c:
        r = c.get("/tvi/vistoria/t1/evidencias")
    assert r.status_code == 200
    assert [e["tipo"] for e in r.json()["eventos"]] == ["criado", "foto", "assinatura"]
