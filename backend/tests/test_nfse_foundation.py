# Testes da FUNDAÇÃO do módulo de emissão de NFS-e (PR1): modelos, cálculo fiscal,
# contador sequencial de DPS (atômico) e factory de provider. NADA transmite.
import asyncio

import pytest

from models.nfse import (
    NFSeConfig, NFSeDocumento, Servico, Tomador, Origem, Emitente, Provider,
    TipoDocumento, StatusNFSe, calcular_valores,
)
from services.nfse import repository as repo
from services.nfse.providers.factory import get_provider
from services.nfse.providers.gateway import GatewayProvider
from services.nfse.providers.sefin_nacional import SefinNacionalProvider
from services.nfse.exceptions import NFSeProviderError, NFSeConfigError


# ── Cálculo fiscal (mesma regra do DANFSe; caso real NFS-e 59) ───────────────
def test_calculo_nfse_59():
    s = Servico(valor_servico=17500.0, aliquota_iss=0.02)
    c = calcular_valores(s)
    assert c["base_calculo"] == 17500.00
    assert c["valor_iss"] == 350.00      # 17.500 × 2%
    assert c["valor_liquido"] == 17500.00


def test_calculo_com_deducao_desconto_retencao_e_iss_retido():
    s = Servico(valor_servico=10000, valor_deducoes=1000, desconto_incondicionado=500,
                desconto_condicionado=200, aliquota_iss=0.05, iss_retido=True)
    s.tributos_federais.retencoes_federais = 300
    c = calcular_valores(s)
    assert c["base_calculo"] == 8500.0           # 10000-1000-500
    assert c["valor_iss"] == 425.0               # 8500 × 5%
    # líquido = 10000 - 500 - 200 - 300 - 425(iss retido) = 8575
    assert c["valor_liquido"] == 8575.0


def test_aliquota_aceita_fracao_ou_percentual():
    assert calcular_valores(Servico(valor_servico=1000, aliquota_iss=0.02))["valor_iss"] == 20.0
    assert calcular_valores(Servico(valor_servico=1000, aliquota_iss=2.0))["valor_iss"] == 20.0


# ── Modelos ──────────────────────────────────────────────────────────────────
def test_modelos_default_e_ibscbs_presente():
    cfg = NFSeConfig(municipio_nome="Açailândia", municipio_uf="MA", codigo_ibge="2100055",
                     emitente=Emitente(razao_social="J R P BEZERRA LTDA", cnpj="17261987000109"))
    assert cfg.provider == Provider.gateway
    assert cfg.ambiente.value == "homologacao"          # default SEGURO = homologação
    assert cfg.fiscal_defaults.ibscbs.incluir is True   # transição RTC sempre presente
    doc = NFSeDocumento(config_id=cfg.id,
                        origem=Origem(tipo="recibo_honorarios"),
                        tomador=Tomador(tipo_documento=TipoDocumento.cnpj, documento="57123389000180"),
                        servico=Servico(valor_servico=17500, aliquota_iss=0.02))
    assert doc.status == StatusNFSe.pendente
    assert doc.chave_acesso is None and doc.idempotency_key


# ── Factory de provider ──────────────────────────────────────────────────────
def _cfg(provider):
    return NFSeConfig(municipio_nome="Açailândia", municipio_uf="MA", codigo_ibge="2100055",
                      provider=provider,
                      emitente=Emitente(razao_social="X", cnpj="17261987000109"))


def test_factory_resolve_providers():
    assert isinstance(get_provider(_cfg(Provider.gateway)), GatewayProvider)
    assert isinstance(get_provider(_cfg(Provider.sefin_nacional)), SefinNacionalProvider)


def test_providers_stub_bloqueiam_emissao():
    """SEGURANÇA: nenhum adapter transmite no PR1 — emitir() levanta erro controlado."""
    for prov in (Provider.gateway, Provider.sefin_nacional):
        p = get_provider(_cfg(prov))
        doc = NFSeDocumento(config_id="c1", origem=Origem(tipo="servico_avulso"),
                            tomador=Tomador(), servico=Servico(valor_servico=100))
        with pytest.raises(NFSeProviderError):
            asyncio.run(p.emitir(doc))


# ── Contador sequencial de DPS (atômico, sem buracos) ────────────────────────
class _FakeCounters:
    """Simula db.counters.find_one_and_update com $inc + upsert (ReturnDocument.AFTER)."""
    def __init__(self):
        self.store = {}

    async def find_one_and_update(self, filtro, update, upsert=False, return_document=None):
        _id = filtro["_id"]
        self.store[_id] = self.store.get(_id, 0) + update["$inc"]["seq"]
        return {"_id": _id, "seq": self.store[_id]}


class _FakeDB:
    def __init__(self):
        self.counters = _FakeCounters()


def test_contador_dps_sequencial_sem_buracos():
    db = _FakeDB()
    nums = [asyncio.run(repo.proximo_numero_dps(db, "cfgA", "1")) for _ in range(5)]
    assert nums == [1, 2, 3, 4, 5]
    # série/config diferentes têm contadores independentes
    assert asyncio.run(repo.proximo_numero_dps(db, "cfgA", "2")) == 1
    assert asyncio.run(repo.proximo_numero_dps(db, "cfgB", "1")) == 1
    assert asyncio.run(repo.proximo_numero_dps(db, "cfgA", "1")) == 6
