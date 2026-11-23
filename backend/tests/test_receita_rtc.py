# @module tests.test_receita_rtc — integração com as calculadoras oficiais (CBS/IBS), Fase 2.
#
# As respostas usadas aqui são REAIS: gravadas das calculadoras 1.7.2 (regime regular) e 1.0.2 (Simples)
# rodando localmente em 21/11/2026 (tests/fixtures/receita_rtc). Integração ao vivo: test_integracao_ao_vivo
# (só roda com RTC_IT_RR_URL e RTC_IT_SN_URL definidas).
import asyncio
import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.receita_rtc import aliquotas as ALQ
from services.receita_rtc import client as CL
from services.receita_rtc import config as cfg
from services.receita_rtc import mapper as MP
from services.receita_rtc import service as SVC
from tests.fake_mongo import FakeDB

FX = Path(__file__).parent / "fixtures" / "receita_rtc"
RR = "http://rr.test/api"
SN = "http://sn.test/api"
CONF = cfg.Config(enabled=True, regime_regular_url=RR, simples_url=SN, timeout_conexao_s=1, timeout_leitura_s=1)


def fx(nome):
    return json.loads((FX / nome).read_text(encoding="utf-8"))


UFS = fx("ufs.json")
MUNICIPIOS_MA = [{"codigo": 2100055, "nome": "Açailândia"}, {"codigo": 2111300, "nome": "São Luís"}]
ERROS = {"REG-011": fx("erro_reg011.json"),
         "VSN-015": {"codigo": "VSN-015", "titulo": "Tipo de documento fiscal (tpDoc) não suportado",
                     "descricao": "O tipo de documento fiscal (tpDoc) informado não está habilitado..."}}


class Calc:
    """Calculadora falsa: responde com as fixtures reais e registra o que recebeu."""

    def __init__(self, calculo=None, calculo_status=200, headers=None, aliquotas_2026=True, falha=None):
        self.pedidos = []
        self.calculo = calculo
        self.calculo_status = calculo_status
        self.headers = headers or {}
        self.aliquotas_2026 = aliquotas_2026
        self.falha = falha  # "rede" | "500"

    def __call__(self, req: httpx.Request):
        self.pedidos.append(req)
        if self.falha == "rede":
            raise httpx.ConnectError("sem rede", request=req)
        if self.falha == "500":
            return httpx.Response(500, json={"erro": "interno"})
        p, q = req.url.path, dict(req.url.params)
        if p.endswith("/dados-abertos/ufs"):
            return httpx.Response(200, json=UFS)
        if p.endswith("/ufs/municipios"):
            return httpx.Response(200, json=MUNICIPIOS_MA if q.get("siglaUf") == "MA" else [])
        if "/dados-abertos/aliquota-" in p:
            if q.get("data", "").startswith("2026") and self.aliquotas_2026:
                v = {"aliquota-uniao": 0.9, "aliquota-uf": 0.1, "aliquota-municipio": 0.0}[p.rsplit("/", 1)[1]]
                return httpx.Response(200, json={"aliquotaReferencia": v})
            return httpx.Response(404, json=fx("aliquota_404.json"))
        if p.endswith("/erros"):
            return httpx.Response(200, json=ERROS.get(q.get("codigo"), {}))
        if p.endswith("/dados-abertos/versao"):
            return httpx.Response(200, json=fx("rr_versao.json"))
        if p.endswith("/versao"):
            return httpx.Response(200, json=fx("sn_versao.json"))
        if "/observabilidade/" in p:
            return httpx.Response(self.calculo_status, json=self.calculo, headers=self.headers)
        return httpx.Response(404, json={})

    def calculos(self):
        return [json.loads(r.content) for r in self.pedidos if r.method == "POST"]


@pytest.fixture(autouse=True)
def _limpa():
    CL.limpar_estado()
    yield
    CL.limpar_estado()


def run(coro):
    return asyncio.run(coro)


def entrada(data="2026-06-10", valor="1000.00", **kw):
    e = {"regime": "REGULAR", "data_operacao": data, "uf": "MA", "codigo_municipio": "2100055",
         "itens": [{"valor": valor, "nbs": "114039000", "cst": "200", "cClassTrib": "200052"}]}
    e.update(kw)
    return e


def simular(db, calc, ent, conf=CONF):
    return run(SVC.simular(db, "user-1", ent, "recibo", "rec-1", conf=conf, transport=httpx.MockTransport(calc)))


async def _cadastrar(db, tributo, aliquota, inicio="2027-01-01", fim=None, confirmar=True, **loc):
    reg = await ALQ.criar(db, {"tributo": tributo, "aliquota": aliquota, "vigencia_inicio": inicio,
                               "vigencia_fim": fim, "fonte": "Documento do contador nº 1/2027", **loc}, "admin")
    if confirmar:
        reg = await ALQ.confirmar(db, reg["id"], "admin", "Contador Fulano")
    return reg


async def _cadastrar_tres(db, situacao_mun="confirmar"):
    await _cadastrar(db, "CBS", "8.8")
    await _cadastrar(db, "IBS_UF", "0.05", uf="MA")
    await _cadastrar(db, "IBS_MUN", "0.05", uf="MA", codigo_municipio="2100055",
                     confirmar=(situacao_mun == "confirmar"))


# ── alíquotas: regras da seção 3.5 ────────────────────────────────────────────
def test_2026_usa_calculadora_e_nao_envia_aliquotas():
    db, calc = FakeDB(), Calc(calculo=fx("rr_2026_calculado.json"))
    snap = simular(db, calc, entrada())
    assert snap["situacao"] == "calculado" and not snap["simulado"]
    assert {a["origem"] for a in snap["aliquotas"].values()} == {"CALCULADORA"}
    assert snap["aliquotas"]["CBS"]["aliquota"] == "0.9"
    [op] = calc.calculos()
    assert "aliquotasNominais" not in op["itens"][0]           # REG-036: proibido antes de 2027
    assert op["dhFatoGerador"].startswith("2026-06-10") and op["municipio"] == 2100055
    assert snap["totais"] == {"base_calculo": "1000.00", "cbs": "6.30", "ibs": "0.70", "is": None}
    assert snap["itens"][0]["cbs"]["aliquota_efetiva"] == "0.63"
    assert cfg.AVISO_TABELA_INTERNA not in snap["avisos"] and cfg.AVISO_FIXO in snap["avisos"]
    assert snap["versao_calculadora"]["versao_app"] == "1.7.2"
    assert db.simulacao_tributaria.docs[0]["resultado_bruto"] == fx("rr_2026_calculado.json")


def test_2027_sem_registro_interno_nao_calcula():
    db, calc = FakeDB(), Calc(calculo=fx("rr_2027_simulado.json"))
    with pytest.raises(SVC.SemAliquota) as e:
        simular(db, calc, entrada("2027-06-10"))
    assert "CBS, IBS estadual, IBS municipal" in str(e.value) and "10/06/2027" in str(e.value)
    assert calc.calculos() == [] and db.simulacao_tributaria.docs == []


def test_2027_com_registro_confirmado_usa_tabela_interna_com_aviso():
    db = FakeDB()
    run(_cadastrar_tres(db))
    calc = Calc(calculo=fx("rr_2027_simulado.json"), headers={"x-warning-dados-simulados": "6"})
    snap = simular(db, calc, entrada("2027-06-10"))
    [op] = calc.calculos()
    assert op["itens"][0]["aliquotasNominais"] == {"cbs": 8.8, "ibsEstadual": 0.05, "ibsMunicipal": 0.05}
    assert {a["origem"] for a in snap["aliquotas"].values()} == {"TABELA_INTERNA"}
    assert all(a["registro_id"] for a in snap["aliquotas"].values())
    assert cfg.AVISO_TABELA_INTERNA in snap["avisos"] and snap["simulado"] is True
    assert snap["totais"]["cbs"] == "61.60"


def test_rascunho_e_revogada_sao_ignorados():
    db = FakeDB()
    run(_cadastrar_tres(db, situacao_mun="rascunho"))
    with pytest.raises(SVC.SemAliquota) as e:
        simular(db, Calc(calculo=fx("rr_2027_simulado.json")), entrada("2027-06-10"))
    assert e.value.faltantes == ["IBS_MUN"] and "IBS municipal" in str(e.value)
    # revoga a CBS confirmada: passa a faltar também
    cbs = next(d for d in db.rtc_aliquotas.docs if d["tributo"] == "CBS")
    run(ALQ.revogar(db, cbs["id"], "admin", "valor corrigido pelo contador"))
    with pytest.raises(SVC.SemAliquota) as e:
        simular(db, Calc(calculo=fx("rr_2027_simulado.json")), entrada("2027-06-10"))
    assert e.value.faltantes == ["CBS", "IBS_MUN"]


def test_vigencia_sobreposta_e_rejeitada():
    db = FakeDB()
    run(_cadastrar(db, "CBS", "8.8", "2027-01-01", "2027-12-31"))
    with pytest.raises(ALQ.AliquotaInvalida, match="sobreposta"):
        run(_cadastrar(db, "CBS", "9.0", "2027-06-01"))
    run(_cadastrar(db, "CBS", "9.0", "2028-01-01"))        # depois do fim: aceito
    # outra UF não conflita
    run(_cadastrar(db, "IBS_UF", "0.05", uf="MA"))
    run(_cadastrar(db, "IBS_UF", "0.05", uf="PA"))


def test_vigencia_respeita_inicio_e_fim():
    db = FakeDB()
    run(_cadastrar(db, "CBS", "8.8", "2027-01-01", "2027-12-31"))
    assert run(ALQ.vigente(db, "CBS", "", "", date(2027, 12, 31)))["aliquota"] == "8.8"
    assert run(ALQ.vigente(db, "CBS", "", "", date(2028, 1, 1))) is None


def test_precisao_decimal_e_limites():
    assert ALQ.normalizar_aliquota("0,123456") == Decimal("0.123456")
    assert str(ALQ.normalizar_aliquota("8.8")) == "8.8"
    for ruim in ("0.1234567", "-1", "101", "abc"):
        with pytest.raises(ALQ.AliquotaInvalida):
            ALQ.normalizar_aliquota(ruim)
    db = FakeDB()
    reg = run(_cadastrar(db, "CBS", "8.812345"))
    assert reg["aliquota"] == "8.812345"
    op = MP.montar_regular(MP.validar_entrada(entrada("2027-06-10", "1234.56")), "x",
                           {"CBS": {"aliquota": "8.812345"}, "IBS_UF": {"aliquota": "0.05"},
                            "IBS_MUN": {"aliquota": "0.05"}})
    texto = json.dumps(op)
    assert '"baseCalculo": 1234.56' in texto and '"cbs": 8.812345' in texto


def test_confirmado_e_imutavel_e_exige_quem_confirmou():
    db = FakeDB()
    reg = run(_cadastrar(db, "CBS", "8.8", confirmar=False))
    with pytest.raises(ALQ.AliquotaInvalida, match="confirmado_por"):
        run(ALQ.confirmar(db, reg["id"], "admin", ""))
    run(ALQ.confirmar(db, reg["id"], "admin", "Contador Fulano"))
    with pytest.raises(ALQ.AliquotaInvalida, match="imutável"):
        run(ALQ.confirmar(db, reg["id"], "admin", "Outro"))
    acoes = [e["acao"] for e in db.rtc_aliquotas_auditoria.docs]
    assert acoes == ["criar", "confirmar"]


def test_registro_exige_fonte_e_localidade():
    for dados, msg in [({"tributo": "CBS", "aliquota": "8.8", "vigencia_inicio": "2027-01-01", "fonte": ""}, "fonte"),
                       ({"tributo": "IBS_UF", "aliquota": "0.1", "vigencia_inicio": "2027-01-01", "fonte": "Lei x"}, "uf"),
                       ({"tributo": "IBS_MUN", "uf": "MA", "aliquota": "0.1", "vigencia_inicio": "2027-01-01",
                         "fonte": "Lei x"}, "codigo_municipio"),
                       ({"tributo": "ICMS", "aliquota": "1", "vigencia_inicio": "2027-01-01", "fonte": "Lei x"}, "tributo")]:
        with pytest.raises(ALQ.AliquotaInvalida, match=msg):
            ALQ.validar_registro(dados)


# ── entrada ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("valor", ["0", "-10", "10.999", "abc"])
def test_valor_zero_negativo_ou_invalido_e_rejeitado(valor):
    with pytest.raises(MP.EntradaInvalida, match="valor"):
        MP.validar_entrada(entrada(valor=valor))


def test_data_da_operacao_e_obrigatoria():
    with pytest.raises(MP.EntradaInvalida, match="data_operacao"):
        MP.validar_entrada(entrada(data=""))


def test_municipio_de_outra_uf_e_rejeitado():
    db = FakeDB()
    with pytest.raises(MP.EntradaInvalida, match="não pertence"):
        simular(db, Calc(calculo=fx("rr_2026_calculado.json")),
                entrada(codigo_municipio="1501402"))


# ── erros da observabilidade ──────────────────────────────────────────────────
def test_erros_por_item_sao_traduzidos():
    resp = {"objetos": [
        fx("rr_2026_calculado.json")["objetos"][0],
        {"nObj": 2, "estadoItem": "INCONSISTENCIA_ENTRADA", "erros": [
            {"code": "REG-011", "title": "NCM não vinculada", "pointer": "#/itens/1/nbs", "detail": "detalhe"}]}],
        "total": fx("rr_2026_calculado.json")["total"]}
    ent = entrada()
    ent["itens"].append(dict(ent["itens"][0]))
    snap = simular(FakeDB(), Calc(calculo=resp), ent)
    assert snap["situacao"] == "calculado_com_erros"
    erro = snap["itens"][1]["erros"][0]
    assert erro["codigo"] == "REG-011" and erro["descricao"].startswith("O código NCM informado")


def test_reg036_de_verdade_aparece_traduzido():
    snap = simular(FakeDB(), Calc(calculo=fx("rr_2026_reg036.json")), entrada())
    assert snap["situacao"] == "nao_calculado"
    assert snap["itens"][0]["erros"][0]["codigo"] == "REG-036"


# ── Simples Nacional ──────────────────────────────────────────────────────────
def entrada_sn(data="2027-06-10"):
    return {"regime": "SIMPLES", "data_operacao": data, "uf": "MA", "codigo_municipio": "2100055",
            "itens": [{"valor": "1000.00", "nbs": "114039000", "cClassTrib": "200052"}],
            "simples": {"crt": "1", "cAtivSN": "07", "pIBSSN": "1.25", "pCBSSN": "2.75"}}


def test_simples_2027_calcula():
    calc = Calc(calculo=fx("sn_2027_calculado.json"))
    snap = simular(FakeDB(), calc, entrada_sn())
    [op] = calc.calculos()
    assert op["tpDoc"] == "91" and op["itens"][0]["baseCalculo"] == "1000.00" and op["itens"][0]["pIBSSN"] == "1.25"
    assert snap["situacao"] == "calculado" and snap["aliquotas"] is None
    assert snap["totais"]["cbs"] == "27.50" and snap["totais"]["ibs"] == "12.50" and snap["totais"]["total"] == "40.00"
    assert snap["versao_calculadora"]["versao_app"] == "1.0.2"


def test_simples_2026_servico_recusado_com_erro_traduzido():
    calc = Calc(calculo=fx("sn_2026_vsn015_422.json"), calculo_status=422)
    snap = simular(FakeDB(), calc, entrada_sn("2026-06-10"))
    assert snap["situacao"] == "nao_calculado" and snap["http_status"] == 422
    assert snap["erros_gerais"][0]["codigo"] == "VSN-015" and snap["erros_gerais"][0]["descricao"]
    assert len(calc.calculos()) == 1                                   # 4xx: sem nova tentativa


def test_simples_rejeita_mei():
    e = entrada_sn()
    e["simples"]["crt"] = "4"
    with pytest.raises(MP.EntradaInvalida, match="MEI"):
        MP.validar_entrada(e)


# ── resiliência ───────────────────────────────────────────────────────────────
def test_flag_desligada_nao_chama_nada():
    calc = Calc(calculo=fx("rr_2026_calculado.json"))
    conf = cfg.Config(False, RR, SN, 1, 1)
    with pytest.raises(SVC.SimuladorDesativado):
        simular(FakeDB(), calc, entrada(), conf=conf)
    assert calc.pedidos == []


def test_calculadora_fora_do_ar_retry_e_circuito(monkeypatch):
    async def sem_espera(*_):
        return None
    monkeypatch.setattr(CL.asyncio, "sleep", sem_espera)
    calc = Calc(falha="rede")
    for _ in range(3):
        with pytest.raises(CL.CalculadoraIndisponivel) as e:
            simular(FakeDB(), calc, entrada())
        assert str(e.value) == cfg.MSG_INDISPONIVEL
    assert len(calc.pedidos) == 9                                       # 3 chamadas × (1 + 2 retries)
    with pytest.raises(CL.CalculadoraIndisponivel):                     # circuito aberto: nem tenta
        simular(FakeDB(), calc, entrada())
    assert len(calc.pedidos) == 9


def test_5xx_tem_retry(monkeypatch):
    async def sem_espera(*_):
        return None
    monkeypatch.setattr(CL.asyncio, "sleep", sem_espera)
    calc = Calc(falha="500")
    with pytest.raises(CL.CalculadoraIndisponivel):
        simular(FakeDB(), calc, entrada())
    assert len(calc.pedidos) == 3


def test_cache_das_tabelas():
    db, calc = FakeDB(), Calc(calculo=fx("rr_2026_calculado.json"))
    simular(db, calc, entrada())
    n = len(calc.pedidos)
    simular(db, calc, entrada())
    assert len(calc.pedidos) == n + 1          # tabelas, versão e localidade vêm do cache; só o cálculo é refeito


def test_logs_nao_levam_corpo(caplog):
    caplog.set_level("INFO", logger="romatec")
    simular(FakeDB(), Calc(calculo=fx("rr_2026_calculado.json")), entrada(valor="4321.09"))
    assert "4321" not in caplog.text and "114039000" not in caplog.text


# ── rotas de administração ────────────────────────────────────────────────────
def test_rotas_admin_aliquotas():
    from db import get_db
    from dependencies import get_admin_user
    from routes.receita_rtc import router
    db = FakeDB()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_admin_user] = lambda: "admin"
    with TestClient(app) as c:
        r = c.post("/admin/receita-rtc/aliquotas", json={"tributo": "CBS", "aliquota": "8,8",
                                                          "vigencia_inicio": "2027-01-01", "fonte": "Doc. contador 1"})
        assert r.status_code == 200 and r.json()["situacao"] == "RASCUNHO" and r.json()["aliquota"] == "8.8"
        rid = r.json()["id"]
        assert c.post("/admin/receita-rtc/aliquotas", json={"tributo": "CBS", "aliquota": "9",
                                                           "vigencia_inicio": "2027-03-01",
                                                           "fonte": "Doc. contador 2"}).status_code == 422
        r = c.post(f"/admin/receita-rtc/aliquotas/{rid}/confirmar", json={"confirmado_por": "Contador Fulano"})
        assert r.status_code == 200 and r.json()["situacao"] == "CONFIRMADA"
        assert c.post(f"/admin/receita-rtc/aliquotas/{rid}/confirmar",
                      json={"confirmado_por": "X y z"}).status_code == 409
        assert len(c.get("/admin/receita-rtc/aliquotas").json()["aliquotas"]) == 1
        assert [e["acao"] for e in c.get("/admin/receita-rtc/aliquotas/auditoria").json()["eventos"]] == \
            ["confirmar", "criar"]


# ── ao vivo (opcional) ────────────────────────────────────────────────────────
@pytest.mark.skipif(not (os.environ.get("RTC_IT_RR_URL") and os.environ.get("RTC_IT_SN_URL")),
                    reason="calculadoras locais não configuradas (RTC_IT_RR_URL / RTC_IT_SN_URL)")
def test_integracao_ao_vivo():
    conf = cfg.Config(True, os.environ["RTC_IT_RR_URL"], os.environ["RTC_IT_SN_URL"], 3, 15)
    db = FakeDB()
    snap = run(SVC.simular(db, "u", entrada(), conf=conf))
    assert snap["situacao"] == "calculado" and snap["totais"]["cbs"] == "6.30"
    run(_cadastrar_tres(db))
    snap = run(SVC.simular(db, "u", entrada("2027-06-10"), conf=conf))
    assert snap["simulado"] and cfg.AVISO_TABELA_INTERNA in snap["avisos"] and snap["totais"]["cbs"] == "61.60"
    snap = run(SVC.simular(db, "u", entrada_sn(), conf=conf))
    assert snap["totais"]["total"] == "40.00"
    diag = run(SVC.diagnostico(conf))
    assert diag["servicos"]["REGULAR"]["no_ar"] and diag["servicos"]["SIMPLES"]["versao"] == "1.0.2"


# ── Fase 4: configuração por conta e simulação pelo recibo ────────────────────
def _app_assinante(monkeypatch, db, calc, ativo=True, uid="user-1"):
    from db import get_db
    from dependencies import get_active_subscriber
    from routes.receita_rtc import router_assinante
    conf = cfg.Config(ativo, RR, SN, 1, 1)
    monkeypatch.setattr(cfg, "carregar", lambda: conf)
    original = SVC.clientes
    monkeypatch.setattr(SVC, "clientes", lambda c=None, t=None: original(conf, httpx.MockTransport(calc)))
    app = FastAPI()
    app.include_router(router_assinante)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_active_subscriber] = lambda: uid
    return TestClient(app)


CONFIG_OK = {"regime": "REGULAR", "uf": "MA", "codigo_municipio": "2100055", "nome_municipio": "Açailândia",
             "nbs": "114039000", "cst": "200", "cClassTrib": "200052", "confirmado_com_contador": True}


def test_flag_desligada_esconde_tudo(monkeypatch):
    c = _app_assinante(monkeypatch, FakeDB(), Calc(), ativo=False)
    assert c.get("/receita-rtc/disponivel").json() == {"ativo": False}
    assert c.put("/receita-rtc/config", json=CONFIG_OK).status_code == 404
    assert c.post("/receita-rtc/simular", json={"origem_id": "x", "data_operacao": "2026-06-10"}).status_code == 404


def test_conta_sem_configuracao_nao_simula(monkeypatch):
    db = FakeDB()
    db.recibos.docs.append({"id": "rec-1", "user_id": "user-1", "valor": 1000.0})
    c = _app_assinante(monkeypatch, db, Calc(calculo=fx("rr_2026_calculado.json")))
    d = c.get("/receita-rtc/disponivel").json()
    assert d["ativo"] and not d["configurado"] and "nbs" in d["faltantes"]
    sem_ciencia = {**CONFIG_OK, "confirmado_com_contador": False}
    assert c.put("/receita-rtc/config", json=sem_ciencia).json()["faltantes"] == ["confirmado_com_contador"]
    r = c.post("/receita-rtc/simular", json={"origem_id": "rec-1", "data_operacao": "2026-06-10"})
    assert r.status_code == 409 and r.json()["detail"]["faltantes"] == ["confirmado_com_contador"]


def test_config_mal_formada_e_recusada(monkeypatch):
    c = _app_assinante(monkeypatch, FakeDB(), Calc())
    for ruim in ({**CONFIG_OK, "nbs": "123"}, {**CONFIG_OK, "regime": "LUCRO"},
                 {**CONFIG_OK, "regime": "SIMPLES", "simples": {"crt": "4"}}):
        assert c.put("/receita-rtc/config", json=ruim).status_code == 422


def test_simulacao_pelo_recibo_e_historico(monkeypatch):
    db = FakeDB()
    db.recibos.docs += [{"id": "rec-1", "user_id": "user-1", "valor": 1000.0},
                        {"id": "rec-9", "user_id": "outra-conta", "valor": 5000.0}]
    calc = Calc(calculo=fx("rr_2026_calculado.json"))
    c = _app_assinante(monkeypatch, db, calc)
    assert c.put("/receita-rtc/config", json=CONFIG_OK).json()["faltantes"] == []
    r = c.post("/receita-rtc/simular", json={"origem_id": "rec-1", "data_operacao": "2026-06-10"})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["totais"]["cbs"] == "6.30" and cfg.AVISO_FIXO in s["avisos"]
    assert "resultado_bruto" not in s and "entrada_enviada" not in s and "user_id" not in s
    assert calc.calculos()[0]["itens"][0]["baseCalculo"] == 1000.0        # valor vem do recibo
    # recibo de outra conta: nem calcula
    assert c.post("/receita-rtc/simular", json={"origem_id": "rec-9", "data_operacao": "2026-06-10"}).status_code == 404
    # data obrigatória
    assert c.post("/receita-rtc/simular", json={"origem_id": "rec-1", "data_operacao": ""}).status_code == 422
    hist = c.get("/receita-rtc/simulacoes", params={"origem_tipo": "recibo", "origem_id": "rec-1"}).json()
    assert len(hist["simulacoes"]) == 1 and hist["simulacoes"][0]["id"] == s["id"]
    # outra conta não vê o histórico
    c2 = _app_assinante(monkeypatch, db, calc, uid="outra-conta")
    assert c2.get("/receita-rtc/simulacoes", params={"origem_tipo": "recibo", "origem_id": "rec-1"}).json() == \
        {"simulacoes": []}


def test_simulacao_2027_sem_aliquota_devolve_motivo(monkeypatch):
    db = FakeDB()
    db.recibos.docs.append({"id": "rec-1", "user_id": "user-1", "valor": 1000.0})
    c = _app_assinante(monkeypatch, db, Calc(calculo=fx("rr_2027_simulado.json")))
    c.put("/receita-rtc/config", json=CONFIG_OK)
    r = c.post("/receita-rtc/simular", json={"origem_id": "rec-1", "data_operacao": "2027-06-10"})
    assert r.status_code == 409 and "Solicite ao administrador" in r.json()["detail"]["mensagem"]


def test_calculadora_fora_do_ar_responde_503(monkeypatch):
    async def sem_espera(*_):
        return None
    monkeypatch.setattr(CL.asyncio, "sleep", sem_espera)
    db = FakeDB()
    db.recibos.docs.append({"id": "rec-1", "user_id": "user-1", "valor": 1000.0})
    c = _app_assinante(monkeypatch, db, Calc(falha="rede"))
    db.rtc_config_conta.docs.append({**CONFIG_OK, "user_id": "user-1", "simples": {}})
    r = c.post("/receita-rtc/simular", json={"origem_id": "rec-1", "data_operacao": "2026-06-10"})
    assert r.status_code == 503 and r.json()["detail"] == cfg.MSG_INDISPONIVEL


def test_ajuda_de_classificacao_pelo_nbs(monkeypatch):
    calc = Calc()
    orig = calc.__call__

    def com_nbs(req):
        if req.url.path.endswith("/dados-abertos/nbs"):
            return httpx.Response(200, json={"capitulo": "Serviços de engenharia", "item": "Outros"})
        if req.url.path.endswith("/situacoes-classificacoes-tributarias"):
            return httpx.Response(200, json=[{"codigoSituacaoTributaria": "200", "descricaoSituacaoTributaria": "Alíquota reduzida",
                                              "codigoClassificacaoTributaria": "200052",
                                              "descricaoClassificacaoTributaria": "Prestação de serviços de profissões intelectuais"}])
        return orig(req)
    c = _app_assinante(monkeypatch, FakeDB(), com_nbs)
    r = c.get("/receita-rtc/classificacoes", params={"nbs": "114039000", "data": "2026-11-23"}).json()
    assert r["descricao"] == "Serviços de engenharia — Outros"
    assert r["opcoes"][0] == {"cst": "200", "cst_descricao": "Alíquota reduzida", "cClassTrib": "200052",
                              "descricao": "Prestação de serviços de profissões intelectuais"}


# ── Ponte Romatec CRM -> calculadoras (assinada com o segredo da integração) ───
SEGREDO_CRM = "s" * 40


def _app_crm(monkeypatch, db, calc, ativo=True):
    import time as _t
    from db import get_db
    from routes.integracoes_romatec_rtc import router as crm_router
    conf = cfg.Config(ativo, RR, SN, 1, 1)
    monkeypatch.setattr(cfg, "carregar", lambda: conf)
    original = SVC.clientes
    monkeypatch.setattr(SVC, "clientes", lambda c=None, t=None: original(conf, httpx.MockTransport(calc)))
    monkeypatch.setenv("ROMATEC_CRM_INTEGRACAO_SECRET", SEGREDO_CRM)
    app = FastAPI()
    app.include_router(crm_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app), _t


def _post_assinado(c, caminho, corpo: dict, segredo=SEGREDO_CRM, ts=None):
    import time as _t
    from services import romatec_crm_integracao as RC
    txt = json.dumps(corpo)
    ts = str(int(_t.time()) if ts is None else ts)
    return c.post(caminho, content=txt, headers={"Content-Type": "application/json", "X-Romatec-Timestamp": ts,
                                                 "X-Romatec-Signature": RC.assinar(segredo, ts, txt.encode())})


PEDIDO_CRM = {**entrada(), "origem": {"tipo": "proposta", "id": "PROP-123"}, "solicitado_por": "usuario 7"}


def test_ponte_crm_simula_com_assinatura_valida(monkeypatch):
    db = FakeDB()
    c, _ = _app_crm(monkeypatch, db, Calc(calculo=fx("rr_2026_calculado.json")))
    r = _post_assinado(c, "/integracoes/romatec/rtc/simular", PEDIDO_CRM)
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["totais"]["cbs"] == "6.30" and s["origem_tipo"] == "crm_proposta" and s["origem_id"] == "PROP-123"
    assert "resultado_bruto" not in s and "user_id" not in s and cfg.AVISO_FIXO in s["avisos"]
    [doc] = db.simulacao_tributaria.docs
    assert doc["user_id"] == "romatec-crm" and doc["solicitado_por_crm"] == "usuario 7"


def test_ponte_crm_recusa_assinatura_errada_ou_velha(monkeypatch):
    import time as _t
    db, calc = FakeDB(), Calc(calculo=fx("rr_2026_calculado.json"))
    c, _ = _app_crm(monkeypatch, db, calc)
    assert _post_assinado(c, "/integracoes/romatec/rtc/simular", PEDIDO_CRM, segredo="x" * 40).status_code == 401
    assert _post_assinado(c, "/integracoes/romatec/rtc/simular", PEDIDO_CRM, ts=int(_t.time()) - 900).status_code == 401
    assert c.post("/integracoes/romatec/rtc/simular", json=PEDIDO_CRM).status_code == 401
    assert calc.pedidos == [] and db.simulacao_tributaria.docs == []


def test_ponte_crm_sem_segredo_ou_desligada(monkeypatch):
    db = FakeDB()
    c, _ = _app_crm(monkeypatch, db, Calc(), ativo=False)
    assert _post_assinado(c, "/integracoes/romatec/rtc/simular", PEDIDO_CRM).status_code == 404
    monkeypatch.delenv("ROMATEC_CRM_INTEGRACAO_SECRET")
    assert _post_assinado(c, "/integracoes/romatec/rtc/simular", PEDIDO_CRM).status_code == 503


def test_ponte_crm_erros_de_entrada_e_sem_aliquota(monkeypatch):
    c, _ = _app_crm(monkeypatch, FakeDB(), Calc(calculo=fx("rr_2027_simulado.json")))
    assert _post_assinado(c, "/integracoes/romatec/rtc/simular", {**PEDIDO_CRM, "origem": {"tipo": "lead", "id": "1"}}).status_code == 422
    assert _post_assinado(c, "/integracoes/romatec/rtc/simular", {**PEDIDO_CRM, "data_operacao": ""}).status_code == 422
    r = _post_assinado(c, "/integracoes/romatec/rtc/simular", {**entrada("2027-06-10"), "origem": {"tipo": "contrato", "id": "C-9"}})
    assert r.status_code == 409 and r.json()["detail"]["faltantes"] == ["CBS", "IBS_UF", "IBS_MUN"]


def test_ponte_crm_status_e_municipios(monkeypatch):
    c, _ = _app_crm(monkeypatch, FakeDB(), Calc())
    st = _post_assinado(c, "/integracoes/romatec/rtc/status", {}).json()
    assert st["ativo"] and st["servicos"]["REGULAR"]["versao"] == "1.7.2"
    m = _post_assinado(c, "/integracoes/romatec/rtc/municipios", {"uf": "MA"}).json()
    assert {"codigo": "2100055", "nome": "Açailândia"} in m["municipios"]
