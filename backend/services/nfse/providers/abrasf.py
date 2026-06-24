# @module services.nfse.providers.abrasf — Adapter webservice municipal padrão ABRASF (SOAP).
# Ex.: SpeedGov — ISS Eletrônico de Açailândia. Pipeline: RPS XML → assina (XMLDSIG) →
# envelope SOAP → RecepcionarLoteRps (mTLS). TRANSMISSÃO BLOQUEADA até validar o WSDL + homologação.
from __future__ import annotations

from services.nfse.providers.base import NFSeProvider
from services.nfse.exceptions import NFSeProviderError
from models.nfse import NFSeDocumento, ResultadoEmissao, ResultadoEvento, StatusNFSe

NOME = "abrasf"


class AbrasfProvider(NFSeProvider):
    db = None             # injetados pelo service.emitir (p/ ler o e-CNPJ do banco)
    owner_uid = None

    def _cfg(self) -> dict:
        a = self.config.abrasf
        return a.model_dump() if hasattr(a, "model_dump") else dict(a)

    async def _preparar(self, doc: NFSeDocumento):
        """Monta o RPS/Lote (ABRASF), assina com o e-CNPJ e devolve (xml_assinado, cert)."""
        from services.nfse.abrasf.rps_xml import montar_lote_rps_xml
        from services.nfse.abrasf.assinatura_abrasf import assinar_lote_rps
        from services.nfse.sefin.certificado import carregar_para_emissao

        cfg = self._cfg()
        cert = await carregar_para_emissao(self.db, self.owner_uid,
                                           {"certificado_id": cfg.get("certificado_id")})
        xml = montar_lote_rps_xml(doc, self.config)
        # SpeedGov/Intersol NÃO usa assinatura no EnviarLoteRpsEnvio (a <Signature> dispara E160 —
        # ACBr SpeedGov.ini: [Assinar] todos=0, UseCertificado=0). Só assina se assinar_rps=True
        # (default False) — mantido p/ outros provedores ABRASF que exigem XMLDSIG.
        if cfg.get("assinar_rps"):
            xml = assinar_lote_rps(xml, cert.key_pem, cert.cert_pem,
                                   sha=cfg.get("assinatura_sha", "sha1"),
                                   namespace=cfg.get("namespace"))
        return xml, cert

    async def emitir(self, doc: NFSeDocumento) -> ResultadoEmissao:
        xml_assinado, cert = await self._preparar(doc)   # monta/assina (valida cert)
        cfg = self._cfg()

        # TRAVA: só transmite com a flag explicitamente habilitada (pós-WSDL/homologação).
        if not cfg.get("transmissao_habilitada"):
            raise NFSeProviderError(
                "ABRASF/SpeedGov: transmissão DESABILITADA (segurança). RPS montado/assinado OK. "
                "Habilite `abrasf.transmissao_habilitada` SÓ após casar envelope/SOAPAction com o "
                "WSDL do SpeedGov de Açailândia e testar em HOMOLOGAÇÃO.")

        # ── Transmissão SOAP (dormante até habilitar) ────────────────────────
        from services.nfse.abrasf.soap_client import AbrasfClient, montar_envelope_soap
        from services.nfse.abrasf.rps_xml import montar_cabecalho
        from services.nfse.sefin.sefin_client import montar_ssl_context
        # SpeedGov é http:// (sem TLS de cliente garantido) — usa o cert só p/ assinar o RPS.
        ctx = None
        if str(cfg.get("url_ws", "")).startswith("https"):
            ctx = montar_ssl_context(cert.key_pem, cert.cert_pem, cert.chain_pem)
        header = montar_cabecalho()
        envelope = montar_envelope_soap(cfg.get("operacao_envio", "RecepcionarLoteRps"),
                                        header, xml_assinado, cfg.get("namespace_ws"))
        client = AbrasfClient(cfg.get("url_ws", ""), ctx)
        try:
            resp = await client.chamar(cfg.get("soap_action", ""), envelope)
        except Exception as e:  # noqa: BLE001
            raise NFSeProviderError(f"ABRASF: falha na transmissão SOAP: {e}") from e
        # Parse da resposta → ResultadoEmissao (ajustar ao retorno real do SpeedGov)
        return ResultadoEmissao(status=StatusNFSe.processando, xml_autorizado=resp)

    async def consultar(self, chave_acesso: str) -> ResultadoEmissao:
        raise NFSeProviderError("ABRASF: consulta não habilitada (pendente WSDL/homologação).")

    async def cancelar(self, chave_acesso: str, motivo: str) -> ResultadoEvento:
        raise NFSeProviderError("ABRASF: cancelamento não habilitado (pendente WSDL/homologação).")

    async def baixar_danfse(self, chave_acesso: str) -> bytes:
        raise NFSeProviderError("ABRASF: usar o gerador DANFSe (pdf.templates.gerar_danfse).")
