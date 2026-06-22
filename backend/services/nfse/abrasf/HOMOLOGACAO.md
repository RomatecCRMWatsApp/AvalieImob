# ABRASF / SpeedGov (Açailândia) — checklist para HABILITAR a emissão

> Açailândia emite NFS-e pelo **SpeedGov — ISS Eletrônico** (`iss.speedgov.com.br/acailandia`),
> padrão **ABRASF** (RPS → NFS-e via webservice SOAP). O **portal** usa login/senha; o
> **webservice** usa o **certificado e-CNPJ** (XMLDSIG no RPS).
>
> Estado: o pipeline **monta o RPS → assina (XMLDSIG)**. A **transmissão está DESLIGADA**
> (`abrasf.transmissao_habilitada=False`). Nada é emitido até os passos abaixo.

## 1. Dados do webservice (do contador ou suporte SpeedGov)
- **URL do webservice (WSDL)** de Açailândia — homologação E produção → `abrasf.url_ws`/`url_ws_producao`.
- **Versão ABRASF** real (1.00 ou 2.x) → `abrasf.versao_abrasf` (muda namespace/leiaute/assinatura).
- Confirmar o **algoritmo de assinatura** (ABRASF 1.0 = RSA-SHA1) → `abrasf.assinatura_sha`.

## 2. Casar o envelope/operações com o WSDL
- `soap_client.montar_envelope_soap` hoje usa `<Operacao><xml><![CDATA[...]]></xml></Operacao>`.
  O SpeedGov pode exigir `nfseCabecMsg`/`nfseDadosMsg` ou `cabecalho`/`dados` — AJUSTAR ao WSDL.
- `soap_action_envio/consulta/cancela` → confirmar nomes exatos das operações.

## 3. Validar o leiaute do RPS (rps_xml.py)
- Conferir contra o XSD/manual do SpeedGov: **Aliquota** (fração vs %), **ItemListaServico**
  (com/sem ponto), campos obrigatórios do Tomador, ordem dos elementos.
- Hoje: alíquota como **fração** (0.0200), item **sem ponto** (1701), valores 2 casas.

## 4. Posição/forma da assinatura (assinatura_abrasf.py)
- Hoje assina cada `<Rps>` (ref `#InfRps.Id`) e o `<LoteRps>` (ref `#Id`). Confirmar se o
  SpeedGov quer só o RPS, só o Lote, ou ambos — e a POSIÇÃO da tag `<Signature>`.

## 5. Testar em HOMOLOGAÇÃO
- `ambiente=homologacao`, `abrasf.url_ws`=homologação. Enviar 1 RPS, conferir o retorno
  (protocolo → consultar lote → número da NFS-e + código de verificação), gerar o DANFSe.

## 6. Habilitar
- Só então `abrasf.transmissao_habilitada=True` (e `url_ws_producao` p/ produção).
- Numeração do RPS é sequencial/atômica por (config, série) — não reusar números.

## Reaproveitado do módulo Sefin
- Carga do certificado (`sefin.certificado.carregar_para_emissao`), SSLContext mTLS
  (`sefin.sefin_client.montar_ssl_context`), assinatura via signxml, gerador DANFSe.
