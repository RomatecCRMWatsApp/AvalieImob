# Testes do adapter ABRASF (SpeedGov/Açailândia) — monta/assina RPS; transmissão bloqueada.
import asyncio

import pytest
from lxml import etree

from models.nfse import (
    NFSeConfig, NFSeDocumento, Emitente, Servico, Tomador, Origem, DPS,
    Provider, TipoDocumento,
)
from services.nfse.abrasf.rps_xml import montar_lote_rps_xml
from services.nfse.providers.factory import get_provider
from services.nfse.exceptions import NFSeProviderError, NFSeConfigError

NS = "http://www.abrasf.org.br/nfse.xsd"


def _config():
    return NFSeConfig(
        municipio_nome="Açailândia", municipio_uf="MA", codigo_ibge="2100055",
        provider=Provider.abrasf,
        emitente=Emitente(razao_social="J R P BEZERRA LTDA", cnpj="17261987000109",
                          inscricao_municipal="26800"),
    )


def _doc(cfg):
    return NFSeDocumento(
        config_id=cfg.id, provider=Provider.abrasf,
        origem=Origem(tipo="servico_avulso", descricao="Avaliação"),
        tomador=Tomador(tipo_documento=TipoDocumento.cnpj, documento="57123389000180",
                        razao_nome="RODO RANCHO COMBUSTIVEIS LTDA"),
        servico=Servico(discriminacao="4ª parcela", item_lista_servico="17.01",
                        valor_servico=17500.00, aliquota_iss=0.02),
        dps=DPS(serie="1", numero=59, id_dps="rps59"),
    )


def _q(el, tag):
    return el.find(f".//{{{NS}}}{tag}")


def test_rps_estrutura_e_valores():
    cfg = _config()
    xml = montar_lote_rps_xml(_doc(cfg), cfg)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.tag == f"{{{NS}}}EnviarLoteRpsEnvio"
    assert _q(root, "ValorServicos").text == "17500.00"
    assert _q(root, "ValorIss").text == "350.00"        # 17500 * 2%
    assert _q(root, "Aliquota").text == "2.00"           # percentual (SpeedGov ISS V2)
    assert _q(root, "ItemListaServico").text == "1701"   # sem ponto
    assert _q(root, "CodigoMunicipio").text == "2100055"
    # prestador e tomador
    assert root.find(f".//{{{NS}}}Prestador/{{{NS}}}Cnpj").text == "17261987000109"
    assert root.find(f".//{{{NS}}}Tomador//{{{NS}}}Cnpj").text == "57123389000180"
    # ids p/ assinatura
    assert root.find(f".//{{{NS}}}InfRps").get("Id") == "rps59"
    assert root.find(f"{{{NS}}}LoteRps").get("Id") == "lote59"


def test_aliquota_aceita_fracao_e_percentual():
    cfg = _config()
    for entrada in (0.02, 2.0):            # fração OU percentual → sempre "2.00" (percentual)
        d = _doc(cfg)
        d.servico.aliquota_iss = entrada
        root = etree.fromstring(montar_lote_rps_xml(d, cfg).encode("utf-8"))
        assert _q(root, "Aliquota").text == "2.00"
        assert _q(root, "ValorIss").text == "350.00"


def test_iss_retido_flag():
    cfg = _config()
    d = _doc(cfg)
    d.servico.iss_retido = True
    xml = montar_lote_rps_xml(d, cfg)
    root = etree.fromstring(xml.encode("utf-8"))
    assert _q(root, "IssRetido").text == "1"   # 1=Sim


def test_factory_resolve_abrasf():
    cfg = _config()
    prov = get_provider(cfg)
    assert prov.__class__.__name__ == "AbrasfProvider"


def test_emissao_bloqueada_sem_transmissao():
    """Mesmo sem cert (db None), a transmissão é travada → levanta erro controlado (nada emite)."""
    cfg = _config()
    prov = get_provider(cfg)
    with pytest.raises((NFSeProviderError, NFSeConfigError)):   # sem cert OU trava → nada emite
        asyncio.run(prov.emitir(_doc(cfg)))


def test_assinatura_abrasf_quando_signxml():
    """Se signxml estiver disponível, assina RPS+Lote e gera 2 blocos Signature."""
    signxml = pytest.importorskip("signxml")  # noqa: F841
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    import datetime as _dt
    from services.nfse.abrasf.assinatura_abrasf import assinar_lote_rps

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subj = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TESTE")])
    cert = (x509.CertificateBuilder().subject_name(subj).issuer_name(subj)
            .public_key(key.public_key()).serial_number(1)
            .not_valid_before(_dt.datetime(2020, 1, 1)).not_valid_after(_dt.datetime(2030, 1, 1))
            .sign(key, hashes.SHA256()))
    key_pem = key.private_bytes(serialization.Encoding.PEM,
                                serialization.PrivateFormat.TraditionalOpenSSL,
                                serialization.NoEncryption())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    cfg = _config()
    xml = montar_lote_rps_xml(_doc(cfg), cfg)
    assinado = assinar_lote_rps(xml, key_pem, cert_pem, sha="sha1")
    root = etree.fromstring(assinado.encode("utf-8"))
    sigs = root.findall(".//{http://www.w3.org/2000/09/xmldsig#}Signature")
    assert len(sigs) >= 2   # 1 do RPS + 1 do Lote
