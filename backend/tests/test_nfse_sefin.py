# Testes do adapter Sefin direto (peças verificáveis SEM cert real/transmissão):
# empacotamento GZip+Base64, carga de .pfx, builder do XML da DPS. Assinatura via importorskip.
# NADA transmite. O leiaute do XML ainda exige validação contra o XSD oficial + homologação.
import asyncio
import datetime as _dt

import pytest
from lxml import etree

from models.nfse import (
    NFSeConfig, NFSeDocumento, Servico, Tomador, Origem, Emitente, Endereco, DPS,
    Provider, Ambiente,
)
from services.nfse.sefin.empacotamento import gzip_base64, base64_gunzip
from services.nfse.sefin.certificado import carregar_pfx
from services.nfse.sefin.dps_xml import montar_dps_xml, NS
from services.nfse.exceptions import NFSeConfigError, NFSeProviderError
from services.nfse.providers.factory import get_provider


# ── Empacotamento GZip + Base64 ──────────────────────────────────────────────
def test_gzip_base64_roundtrip():
    xml = "<DPS><infDPS>çãé 17500.00</infDPS></DPS>"
    pack = gzip_base64(xml)
    assert isinstance(pack, str) and pack
    assert base64_gunzip(pack).decode("utf-8") == xml


# ── Certificado .pfx (gera um self-signed só p/ o teste; NÃO é ICP real) ─────
def _gerar_pfx(senha="1234"):
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ROMATEC TESTE:17261987000109")])
    cert = (x509.CertificateBuilder().subject_name(nome).issuer_name(nome)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(_dt.datetime.utcnow() - _dt.timedelta(days=1))
            .not_valid_after(_dt.datetime.utcnow() + _dt.timedelta(days=365))
            .sign(key, hashes.SHA256()))
    return pkcs12.serialize_key_and_certificates(
        b"romatec", key, cert, None,
        serialization.BestAvailableEncryption(senha.encode())), key, cert


def test_carregar_pfx():
    pfx, _key, _cert = _gerar_pfx("senha123")
    cc = carregar_pfx(pfx, "senha123")
    assert cc.key_pem.startswith(b"-----BEGIN") and cc.cert_pem.startswith(b"-----BEGIN CERTIFICATE")
    assert "ROMATEC TESTE" in cc.titular


def test_carregar_pfx_senha_errada():
    pfx, _k, _c = _gerar_pfx("certa")
    with pytest.raises(NFSeConfigError):
        carregar_pfx(pfx, "errada")


# ── Builder do XML da DPS ────────────────────────────────────────────────────
def _doc_e_config():
    cfg = NFSeConfig(
        municipio_nome="Açailândia", municipio_uf="MA", codigo_ibge="2100055",
        provider=Provider.sefin_nacional, ambiente=Ambiente.homologacao,
        emitente=Emitente(razao_social="J R P BEZERRA LTDA", cnpj="17261987000109",
                          inscricao_municipal="26800",
                          endereco=Endereco(codigo_ibge="2100055")))
    doc = NFSeDocumento(
        config_id=cfg.id, provider=Provider.sefin_nacional, ambiente=Ambiente.homologacao,
        origem=Origem(tipo="servico_avulso"),
        tomador=Tomador(documento="57123389000180", razao_nome="RODO RANCHO COMBUSTIVEIS LTDA"),
        servico=Servico(valor_servico=17500.0, aliquota_iss=0.02, item_lista_servico="17.01",
                        codigo_tributacao_municipal="821130001", local_prestacao_ibge="2100055",
                        discriminacao="4ª parcela do contrato"),
        dps=DPS(serie="1", numero=59, id_dps="DPS59", data_emissao=_dt.datetime(2026, 6, 12, 12, 12, 40)))
    return doc, cfg


def test_dps_xml_estrutura_e_valores():
    doc, cfg = _doc_e_config()
    xml = montar_dps_xml(doc, cfg)
    root = etree.fromstring(xml.encode("utf-8"))

    def t(path):
        el = root.find(path.replace("{}", f"{{{NS}}}"))
        return el.text if el is not None else None

    inf = root.find(f"{{{NS}}}infDPS")
    assert inf is not None and inf.get("Id") == "DPS59"
    assert t("{}infDPS/{}tpAmb") == "2"                       # homologação (seguro)
    assert t("{}infDPS/{}nDPS") == "59"
    assert t("{}infDPS/{}prest/{}CNPJ") == "17261987000109"
    assert t("{}infDPS/{}prest/{}IM") == "26800"
    assert t("{}infDPS/{}toma/{}CNPJ") == "57123389000180"
    assert t("{}infDPS/{}prest/{}regTrib/{}opSimpNac") == "1"      # 1=Não Optante (MOC)
    assert t("{}infDPS/{}serv/{}cServ/{}cTribNac") == "170100"     # [0-9]{6} (item 17.01)
    assert t("{}infDPS/{}serv/{}cServ/{}cNBS") == "000000000"      # [0-9]{9} obrigatório
    assert t("{}infDPS/{}valores/{}vServPrest/{}vServ") == "17500.00"
    assert t("{}infDPS/{}valores/{}trib/{}tribMun/{}tribISSQN") == "1"
    assert t("{}infDPS/{}valores/{}trib/{}tribMun/{}pAliq") == "2.0000"
    assert t("{}infDPS/{}valores/{}trib/{}tribMun/{}tpRetISSQN") == "1"  # 1=Não Retido
    assert t("{}infDPS/{}valores/{}trib/{}totTrib/{}indTotTrib") == "0"
    # tribMun NÃO carrega vISSQN/vBC/cLocIncid (XSD); IBSCBS (RTC) é opcional → omitido
    assert root.find(f"{{{NS}}}infDPS/{{{NS}}}valores/{{{NS}}}trib/{{{NS}}}tribMun/{{{NS}}}vISSQN") is None
    assert root.find(f"{{{NS}}}infDPS/{{{NS}}}IBSCBS") is None


def test_dps_xml_producao_muda_tpamb():
    doc, cfg = _doc_e_config()
    doc.ambiente = Ambiente.producao
    root = etree.fromstring(montar_dps_xml(doc, cfg).encode("utf-8"))
    assert root.find(f"{{{NS}}}infDPS/{{{NS}}}tpAmb").text == "1"


def test_dps_xml_valida_contra_xsd_se_presente():
    """Validação programática contra o XSD oficial (defina NFSE_DPS_XSD apontando p/ o
    DPS_v1.00.xsd do pacote gov.br/nfse). Sem o XSD, o teste é pulado."""
    import os
    from services.nfse.sefin.dps_xml import validar_dps_xsd
    xsd = os.environ.get("NFSE_DPS_XSD")
    if not xsd or not os.path.exists(xsd):
        pytest.skip("NFSE_DPS_XSD não definido — baixar o XSD oficial p/ validar.")
    doc, cfg = _doc_e_config()
    ok, erros = validar_dps_xsd(montar_dps_xml(doc, cfg), xsd)
    assert ok, f"DPS não conforme ao XSD: {erros[:5]}"


# ── Assinatura (só roda se signxml estiver instalado) ────────────────────────
def test_assinatura_xmldsig():
    pytest.importorskip("signxml")
    from services.nfse.sefin.assinatura import assinar_dps
    pfx, key, cert = _gerar_pfx("s")
    from cryptography.hazmat.primitives import serialization
    key_pem = key.private_bytes(serialization.Encoding.PEM,
                                serialization.PrivateFormat.TraditionalOpenSSL,
                                serialization.NoEncryption())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    doc, cfg = _doc_e_config()
    xml = montar_dps_xml(doc, cfg)
    assinado = assinar_dps(xml, key_pem, cert_pem)
    assert "Signature" in assinado and "SignatureValue" in assinado


# ── Cliente mTLS — SSLContext a partir do cert em memória (sem rede) ─────────
def test_montar_ssl_context():
    import ssl
    from cryptography.hazmat.primitives import serialization
    from services.nfse.sefin.sefin_client import montar_ssl_context
    _pfx, key, cert = _gerar_pfx("s")
    key_pem = key.private_bytes(serialization.Encoding.PEM,
                                serialization.PrivateFormat.TraditionalOpenSSL,
                                serialization.NoEncryption())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    ctx = montar_ssl_context(key_pem, cert_pem)
    assert isinstance(ctx, ssl.SSLContext)


# ── SEGURANÇA: emitir() NÃO transmite (sem cert + flag desabilitada) ─────────
def test_emitir_bloqueado_sem_certificado():
    _doc, cfg = _doc_e_config()
    doc = NFSeDocumento(config_id=cfg.id, provider=Provider.sefin_nacional,
                        origem=Origem(tipo="servico_avulso"), tomador=Tomador(),
                        servico=Servico(valor_servico=100))
    provider = get_provider(cfg)
    with pytest.raises((NFSeProviderError, NFSeConfigError)):
        asyncio.run(provider.emitir(doc))
    # mesmo com a flag ligada, sem certificado a emissão continua bloqueada
    cfg.sefin.transmissao_habilitada = True
    with pytest.raises((NFSeProviderError, NFSeConfigError)):
        asyncio.run(get_provider(cfg).emitir(doc))
