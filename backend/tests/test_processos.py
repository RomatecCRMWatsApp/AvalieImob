# @module tests.test_processos — processos de trabalho e agenda de vistorias.
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import get_db
from dependencies import get_active_subscriber
from services import processos as P
from tests.fake_mongo import FakeDB

A, B = "conta-A", "conta-B"


@pytest.fixture()
def c():
    from routes.processos import router
    fake = FakeDB()
    atual = {"uid": A}
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_active_subscriber] = lambda: atual["uid"]
    with TestClient(app) as cli:
        cli.fake = fake
        cli.como = lambda uid: atual.update({"uid": uid})
        yield cli


def _novo(c, **kw):
    r = c.post("/processos", json={"titulo": "Avaliação Casa Rua A", "tipo_servico": "avaliacao",
                                   "cliente_nome": "Maria", **kw})
    assert r.status_code == 201, r.text
    return r.json()


# ── regras puras ─────────────────────────────────────────────────────────────
def test_horario_com_fuso_e_guardado_em_utc():
    assert P.parse_inicio("2026-12-01T10:00:00-03:00") == datetime(2026, 12, 1, 13, 0)
    with pytest.raises(ValueError):
        P.parse_inicio("ontem")


def test_conflito_so_quando_os_horarios_se_sobrepoem():
    base = P.novo_compromisso("vistoria", "2026-12-01T13:00:00", 60)
    encosta = P.novo_compromisso("vistoria", "2026-12-01T14:00:00", 60)
    sobrepoe = P.novo_compromisso("reuniao", "2026-12-01T13:30:00", 30)
    cancelado = {**sobrepoe, "id": "x", "status": "cancelado"}
    assert P.conflitos(base, [encosta]) == []
    assert P.conflitos(base, [sobrepoe]) == [sobrepoe]
    assert P.conflitos(base, [cancelado]) == []


def test_reagendar_guarda_o_horario_anterior():
    comp = P.novo_compromisso("vistoria", "2026-12-01T13:00:00", 60)
    novo = P.aplicar_acao_agenda(comp, "reagendar", "2026-12-02T15:00:00", "cliente pediu")
    assert novo["inicio"] == datetime(2026, 12, 2, 15, 0) and novo["status"] == "agendado"
    ultimo = novo["historico"][-1]
    assert ultimo["de"] == datetime(2026, 12, 1, 13, 0) and "cliente pediu" in ultimo["evento"]
    cancel = P.aplicar_acao_agenda(novo, "cancelar")
    with pytest.raises(ValueError):
        P.aplicar_acao_agenda(cancel, "confirmar")


# ── rotas ───────────────────────────────────────────────────────────────────
def test_criar_numera_e_traz_as_etapas_do_tipo(c):
    p1, p2 = _novo(c), _novo(c)
    assert p1["numero"].endswith("-0001") and p2["numero"].endswith("-0002")
    assert [e["titulo"] for e in p1["etapas"]] == P.ETAPAS_PADRAO["avaliacao"]
    assert p1["progresso"] == 0 and p1["status"] == "aberto"


def test_concluir_etapa_atualiza_progresso_e_historico(c):
    p = _novo(c)
    eid = p["etapas"][0]["id"]
    r = c.patch(f"/processos/{p['id']}/etapas/{eid}", json={"concluida": True})
    assert r.status_code == 200
    assert r.json()["progresso"] == round(100 / 6)
    assert any("Etapa concluída" in h["evento"] for h in r.json()["historico"])


def test_vincular_documento_proprio_e_recusar_de_outra_conta(c):
    c.fake.ptam_documents.docs += [
        {"id": "ptam-a", "user_id": A, "numero_ptam": "0003", "property_label": "Casa"},
        {"id": "ptam-b", "user_id": B, "numero_ptam": "0009", "property_label": "Casa de B"},
    ]
    p = _novo(c)
    ok = c.post(f"/processos/{p['id']}/referencias", json={"tipo": "ptam", "id": "ptam-a"})
    assert ok.status_code == 201 and ok.json()["referencias"][0]["rotulo"] == "0003 — Casa"
    alheio = c.post(f"/processos/{p['id']}/referencias", json={"tipo": "ptam", "id": "ptam-b"})
    assert alheio.status_code == 404
    det = c.get(f"/processos/{p['id']}").json()
    assert [r["id"] for r in det["referencias"]] == ["ptam-a"]
    assert det["referencias"][0]["link"] == "/dashboard/ptam/ptam-a"
    # o documento vinculado não é alterado
    assert c.fake.ptam_documents.docs[0] == {"id": "ptam-a", "user_id": A, "numero_ptam": "0003",
                                             "property_label": "Casa"}


def test_seletor_so_lista_documentos_da_conta(c):
    c.fake.vistorias.docs += [{"id": "v-a", "user_id": A, "numero_tvi": "TVI-1"},
                              {"id": "v-b", "user_id": B, "numero_tvi": "TVI-2"}]
    r = c.get("/processos/documentos-disponiveis", params={"tipo": "tvi"})
    assert [d["id"] for d in r.json()] == ["v-a"]


def test_agenda_avisa_conflito_entre_processos_e_lista_no_periodo(c):
    p1, p2 = _novo(c), _novo(c, titulo="Outro")
    r1 = c.post(f"/processos/{p1['id']}/agenda",
                json={"tipo": "vistoria", "inicio": "2026-12-01T10:00:00-03:00", "duracao_min": 90})
    assert r1.status_code == 201 and r1.json()["conflitos"] == []
    r2 = c.post(f"/processos/{p2['id']}/agenda",
                json={"tipo": "vistoria", "inicio": "2026-12-01T11:00:00-03:00"})
    assert r2.status_code == 201 and len(r2.json()["conflitos"]) == 1  # avisa, não bloqueia
    ag = c.get("/processos/agenda", params={"de": "2026-12-01T00:00:00Z",
                                            "ate": "2026-12-02T00:00:00Z"}).json()
    assert [x["processo_titulo"] for x in ag] == ["Avaliação Casa Rua A", "Outro"]


def test_acoes_da_agenda_e_horario_invalido(c):
    p = _novo(c)
    r = c.post(f"/processos/{p['id']}/agenda", json={"tipo": "vistoria", "inicio": "amanhã"})
    assert r.status_code == 422
    aid = c.post(f"/processos/{p['id']}/agenda",
                 json={"tipo": "vistoria", "inicio": "2026-12-01T13:00:00Z"}).json()["compromisso"]["id"]
    conf = c.post(f"/processos/{p['id']}/agenda/{aid}/acao", json={"acao": "confirmar"})
    assert conf.json()["compromisso"]["status"] == "confirmado"
    reag = c.post(f"/processos/{p['id']}/agenda/{aid}/acao",
                  json={"acao": "reagendar", "novo_inicio": "2026-12-03T13:00:00Z"})
    assert reag.json()["compromisso"]["status"] == "agendado"
    assert len(reag.json()["compromisso"]["historico"]) == 3


def test_excluir_processo_nao_apaga_documentos(c):
    c.fake.ptam_documents.docs.append({"id": "ptam-a", "user_id": A})
    p = _novo(c)
    c.post(f"/processos/{p['id']}/referencias", json={"tipo": "ptam", "id": "ptam-a"})
    assert c.delete(f"/processos/{p['id']}").status_code == 200
    assert len(c.fake.ptam_documents.docs) == 1


def test_lista_e_agenda_sao_da_conta(c):
    _novo(c)
    c.como(B)
    assert c.get("/processos").json() == []
    assert c.get("/processos/agenda").json() == []
