# @module services.nfse.providers.sefin_nacional — Adapter direto Sefin Nacional.
# Pipeline: montar DPS XML → assinar (XMLDSIG) → GZip+Base64 → transmitir (mTLS).
# SEGURANÇA: a TRANSMISSÃO está BLOQUEADA — só monta/assina/empacota. Habilitar a Sefin
# exige (1) certificado ICP-Brasil .pfx configurado, (2) validação do XSD oficial, (3)
# teste em HOMOLOGAÇÃO. Sem isso, emitir() levanta erro controlado (nada é emitido).
from __future__ import annotations

from services.nfse.providers.base import NFSeProvider
from services.nfse.exceptions import NFSeProviderError
from models.nfse import NFSeDocumento, ResultadoEmissao, ResultadoEvento

NOME = "sefin_nacional"


class SefinNacionalProvider(NFSeProvider):
    def _preparar_payload(self, doc: NFSeDocumento) -> str:
        """Monta o XML da DPS, assina e empacota (GZip+Base64). Levanta se faltar certificado."""
        from services.nfse.sefin.dps_xml import montar_dps_xml
        from services.nfse.sefin.certificado import carregar_de_config
        from services.nfse.sefin.assinatura import assinar_dps
        from services.nfse.sefin.empacotamento import gzip_base64

        sefin_cfg = self.config.sefin.model_dump() if hasattr(self.config.sefin, "model_dump") else dict(self.config.sefin)
        cert = carregar_de_config(sefin_cfg)        # ← levanta NFSeConfigError sem .pfx
        xml = montar_dps_xml(doc, self.config)
        xml_assinado = assinar_dps(xml, cert.key_pem, cert.cert_pem)
        return gzip_base64(xml_assinado)

    async def emitir(self, doc: NFSeDocumento) -> ResultadoEmissao:
        # Monta/assina/empacota (valida cert). A TRANSMISSÃO permanece bloqueada.
        self._preparar_payload(doc)
        raise NFSeProviderError(
            "Sefin Nacional: transmissão NÃO habilitada. XML montado/empacotado OK, mas a "
            "transmissão mTLS exige validação do XSD oficial + homologação antes de produção.")

    async def consultar(self, chave_acesso: str) -> ResultadoEmissao:
        raise NFSeProviderError("Sefin Nacional: consulta não habilitada (pendente homologação).")

    async def cancelar(self, chave_acesso: str, motivo: str) -> ResultadoEvento:
        raise NFSeProviderError("Sefin Nacional: cancelamento não habilitado (pendente homologação).")

    async def baixar_danfse(self, chave_acesso: str) -> bytes:
        # O emissor próprio não devolve PDF: delega ao gerador de DANFSe do AvalieImob.
        raise NFSeProviderError("Sefin Nacional: usar o gerador DANFSe (pdf.templates.gerar_danfse).")
