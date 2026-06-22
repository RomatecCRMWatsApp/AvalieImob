# Sefin Nacional direto — checklist para HABILITAR a emissão (homologação → produção)

> Estado atual: o pipeline **monta → assina → empacota** a DPS. A **transmissão está
> DESLIGADA** por segurança (`nfse_config.sefin.transmissao_habilitada = False`).
> Nada é emitido até os passos abaixo serem concluídos.

## 1. Certificado ICP-Brasil A1 (.pfx) — como secret no Railway
- Suba o `.pfx` como **secret file/volume** (NÃO commitar, NÃO no Mongo em claro).
- Defina as env vars:
  - `ROMATEC_CERT_PFX_PATH` = caminho do arquivo (ex.: `/secrets/romatec.pfx`)
  - `ROMATEC_CERT_SENHA` = senha do .pfx
- No `nfse_config.sefin`: `certificado_ref = "/secrets/romatec.pfx"`,
  `certificado_senha_ref = "ROMATEC_CERT_SENHA"`.

## 2. Validar o LEIAUTE do XML da DPS contra o XSD oficial
- A estrutura do `dps_xml.py` (infDPS/prest/toma/serv/valores/trib) JÁ foi conferida
  e validou 100% contra o `TDPS` do schema nacional (cTribNac 6díg, cNBS 9díg,
  tribMun sem vISSQN/vBC [a ADN calcula o ISS], tpRetISSQN 1=não-retido, IBSCBS opcional
  omitido). Resta validar contra o XSD do SEU município/ADN antes de produção.
- Baixar o pacote XSD do **gov.br/nfse** (ex.: `xsd_pl_nfse_1-00`) e apontar o
  `DPS_v1.00.xsd` via env **`NFSE_DPS_XSD`** → `pytest tests/test_nfse_sefin.py` valida.
- Função pronta: `services.nfse.sefin.dps_xml.validar_dps_xsd(xml, xsd_path) -> (ok, erros)`.
- Ajustar **cNBS** (código NBS real do serviço, 9 díg.) e **cTribNac** (se o município
  usar código nacional próprio) — hoje cNBS sai `000000000` (placeholder).

## 3. Endpoints + payload — CONFIRMADOS (Manual Contribuintes Emissor Público v1.2, out/2025)
Homologação = ambiente **"Produção Restrita"**. URLs base (já são o default da tela):
- **Sefin** (recepção da DPS, mTLS):
  - Homologação: `https://sefin.producaorestrita.nfse.gov.br/API/SefinNacional`
  - Produção:    `https://sefin.nfse.gov.br/SefinNacional`
- **ADN** (consulta/DANFSe):
  - Homologação: `https://adn.producaorestrita.nfse.gov.br`
  - Produção:    `https://adn.nfse.gov.br`
- Swaggers: `…/API/SefinNacional/docs/index` (Sefin), `…/contribuintes/docs/index.html` (ADN).

Métodos REST (já default em `SefinConfig`):
- `POST /nfse` — geração síncrona da NFS-e (recebe a DPS). Corpo JSON
  `{"dpsXmlGZipB64": "<gzip+base64 do XML da DPS assinado>"}` (já é o que o `sefin_client` envia).
- `GET /nfse/{chaveAcesso}` — consulta NFS-e pela chave.
- `GET /dps/{id}` — recupera a chave de acesso a partir do id da DPS.
- Cancelamento = **Evento de Cancelamento por Substituição** (POST de uma DPS substituta com a chave da NFS-e a cancelar).
- Auth = **mTLS** com o e-CNPJ A1 (sem token); o `montar_ssl_context` já faz isso.

## 4. Testar em HOMOLOGAÇÃO
- `ambiente = "homologacao"` (o builder já força `tpAmb=2`).
- Emitir uma DPS de teste, conferir retorno (chave 50, código verificação),
  gerar o DANFSe (`pdf.templates.gerar_danfse`), validar o XML autorizado.

## 5. Habilitar
- Só então: `sefin.transmissao_habilitada = True` (e, para produção, `ambiente="producao"`).
- A numeração da DPS é sequencial/atômica por `(config, série)` — não reusar números.
