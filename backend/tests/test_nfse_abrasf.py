# Testes do adapter ABRASF (SpeedGov/Açailândia) — monta/valida RPS contra o XSD oficial.
import asyncio

import pytest
from lxml import etree

from models.nfse import (
    NFSeConfig, NFSeDocumento, Emitente, Servico, Tomador, Origem, DPS,
    Provider, TipoDocumento,
)
from services.nfse.abrasf.rps_xml import montar_lote_rps_xml, validar_rps_xsd, NS_TIPOS, NS_ENVIO
from services.nfse.providers.factory import get_provider
from services.nfse.exceptions import NFSeProviderError, NFSeConfigError


def _config():
    cfg = NFSeConfig(
        municipio_nome="Açailândia", municipio_uf="MA", codigo_ibge="2100055",
        provider=Provider.abrasf,
        emitente=Emitente(razao_social="J R P BEZERRA LTDA", cnpj="17261987000109",
                          inscricao_municipal="26800"),
    )
    cfg.fiscal_defaults.cnae = "8211300"
    cfg.fiscal_defaults.codigo_tributacao_municipal = "821130001"
    return cfg


def _doc(cfg):
    return NFSeDocumento(
        config_id=cfg.id, provider=Provider.abrasf,
        origem=Origem(tipo="servico_avulso", descricao="Reparo piso"),
        tomador=Tomador(tipo_documento=TipoDocumento.cnpj, documento="07133563000105",
                        razao_nome="CEARA DISTRIBUIDORA DE ALIMENTOS LTDA"),
        servico=Servico(discriminacao="Serviço de Reparo Piso em porcelanato setor Adm.",
                        item_lista_servico="17.01", valor_servico=6000.00, aliquota_iss=0.02),
        dps=DPS(serie="1", numero=1),
    )


def _q(el, tag):
    return el.find(f".//{{{NS_TIPOS}}}{tag}")


def test_rps_valido_contra_xsd_oficial():
    """O coração: o RPS gerado tem que validar 100% no XSD oficial do SpeedGov."""
    cfg = _config()
    xml = montar_lote_rps_xml(_doc(cfg), cfg)
    ok, erros = validar_rps_xsd(xml)
    assert ok is True, f"XSD inválido: {erros}"


def test_rps_estrutura_e_valores():
    cfg = _config()
    root = etree.fromstring(montar_lote_rps_xml(_doc(cfg), cfg).encode("utf-8"))
    assert root.tag == f"{{{NS_ENVIO}}}EnviarLoteRpsEnvio"
    assert root.find(f"{{{NS_ENVIO}}}LoteRps").get("Id") == "lote1"
    assert _q(root, "ValorServicos").text == "6000.00"
    assert _q(root, "ValorIss").text == "120.00"          # 6000 * 2%
    assert _q(root, "Aliquota").text == "0.0200"          # tsAliquota: FRACIONÁRIO (2% = 0.0200), manual pg.21
    assert _q(root, "ItemListaServico").text == "1701"
    assert _q(root, "CodigoCnae").text == "8211300"
    assert _q(root, "CodigoMunicipio").text == "2100055"
    assert root.find(f".//{{{NS_TIPOS}}}InfRps").get("Id") == "rps1"
    assert root.find(f".//{{{NS_TIPOS}}}Prestador/{{{NS_TIPOS}}}Cnpj").text == "17261987000109"
    assert root.find(f".//{{{NS_TIPOS}}}Tomador//{{{NS_TIPOS}}}Cnpj").text == "07133563000105"


def test_aliquota_aceita_fracao_e_percentual():
    cfg = _config()
    for entrada in (0.02, 2.0):
        d = _doc(cfg)
        d.servico.aliquota_iss = entrada
        root = etree.fromstring(montar_lote_rps_xml(d, cfg).encode("utf-8"))
        assert _q(root, "Aliquota").text == "0.0200"
        assert _q(root, "ValorIss").text == "120.00"


def test_factory_resolve_abrasf():
    assert get_provider(_config()).__class__.__name__ == "AbrasfProvider"


def test_emissao_bloqueada_sem_transmissao():
    prov = get_provider(_config())
    with pytest.raises((NFSeProviderError, NFSeConfigError)):
        asyncio.run(prov.emitir(_doc(_config())))


def test_assinatura_abrasf_quando_xmlsec():
    """Se xmlsec disponível: assina RPS+Lote (2 Signatures) e o assinado valida no XSD."""
    pytest.importorskip("xmlsec")
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
    assinado = assinar_lote_rps(montar_lote_rps_xml(_doc(cfg), cfg), key_pem, cert_pem, sha="sha1")
    root = etree.fromstring(assinado.encode("utf-8"))
    sigs = root.findall(".//{http://www.w3.org/2000/09/xmldsig#}Signature")
    assert len(sigs) >= 2
    ok, erros = validar_rps_xsd(assinado)
    assert ok is True, f"assinado inválido: {erros}"
