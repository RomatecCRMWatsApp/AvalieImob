# @module services.nfse.providers.sefin_nacional — Adapter direto Sefin Nacional.
# Pipeline: montar DPS XML → assinar (XMLDSIG) → GZip+Base64 → transmitir (mTLS).
# SEGURANÇA: a TRANSMISSÃO está BLOQUEADA — só monta/assina/empacota. Habilitar a Sefin
# exige (1) certificado ICP-Brasil .pfx configurado, (2) validação do XSD oficial, (3)
# teste em HOMOLOGAÇÃO. Sem isso, emitir() levanta erro controlado (nada é emitido).
from __future__ import annotations

from services.nfse.providers.base import NFSeProvider
from services.nfse.exceptions import NFSeProviderError
from models.nfse import NFSeDocumento, ResultadoEmissao, ResultadoEvento, StatusNFSe

NOME = "sefin_nacional"


class SefinNacionalProvider(NFSeProvider):
    db = None             # injetados pelo service.emitir (p/ ler o e-CNPJ do banco)
    owner_uid = None

    async def _preparar(self, doc: NFSeDocumento):
        """Monta o XML da DPS, assina e empacota (GZip+Base64). Devolve (payload_b64, cert).
        Levanta se faltar certificado (e-CNPJ no banco ou .pfx por arquivo/env)."""
        from services.nfse.sefin.dps_xml import montar_dps_xml
        from services.nfse.sefin.certificado import carregar_para_emissao
        from services.nfse.sefin.assinatura import assinar_dps
        from services.nfse.sefin.empacotamento import gzip_base64

        cert = await carregar_para_emissao(self.db, self.owner_uid, self._sefin_cfg())
        xml = montar_dps_xml(doc, self.config)
        xml_assinado = assinar_dps(xml, cert.key_pem, cert.cert_pem)
        return gzip_base64(xml_assinado), cert

    def _sefin_cfg(self) -> dict:
        s = self.config.sefin
        return s.model_dump() if hasattr(s, "model_dump") else dict(s)

    async def emitir(self, doc: NFSeDocumento) -> ResultadoEmissao:
        payload_b64, cert = await self._preparar(doc)  # monta/assina/empacota (valida cert)
        sefin = self._sefin_cfg()

        # TRAVA: só transmite com a flag explicitamente habilitada (pós-homologação).
        if not sefin.get("transmissao_habilitada"):
            raise NFSeProviderError(
                "Sefin Nacional: transmissão DESABILITADA (segurança). DPS montada/assinada/"
                "empacotada OK. Habilite `sefin.transmissao_habilitada` SÓ após validar o XSD "
                "oficial e testar em HOMOLOGAÇÃO.")

        # ── Transmissão mTLS (dormante até habilitar) ────────────────────────
        from services.nfse.sefin.sefin_client import montar_ssl_context, SefinClient
        ctx = montar_ssl_context(cert.key_pem, cert.cert_pem, cert.chain_pem)
        client = SefinClient(sefin.get("base_url_sefin", ""), ctx)
        try:
            resp = await client.transmitir_dps(sefin.get("rota_emissao", "/sefin/dps"), payload_b64)
        except Exception as e:  # noqa: BLE001
            raise NFSeProviderError(f"Sefin: falha na transmissão mTLS: {e}") from e
        # Mapeamento da resposta → ResultadoEmissao (ajustar aos campos do Swagger oficial)
        return ResultadoEmissao(
            status=StatusNFSe.autorizada if resp.get("chaveAcesso") else StatusNFSe.processando,
            chave_acesso=resp.get("chaveAcesso"), numero_nfse=resp.get("numeroNfse"),
            codigo_verificacao=resp.get("codigoVerificacao"),
            url_consulta_publica=resp.get("linkConsulta"),
        )

    async def consultar(self, chave_acesso: str) -> ResultadoEmissao:
        raise NFSeProviderError("Sefin Nacional: consulta não habilitada (pendente homologação).")

    async def cancelar(self, chave_acesso: str, motivo: str) -> ResultadoEvento:
        raise NFSeProviderError("Sefin Nacional: cancelamento não habilitado (pendente homologação).")

    async def baixar_danfse(self, chave_acesso: str) -> bytes:
        # O emissor próprio não devolve PDF: delega ao gerador de DANFSe do AvalieImob.
        raise NFSeProviderError("Sefin Nacional: usar o gerador DANFSe (pdf.templates.gerar_danfse).")
