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

## 3. Endpoints + payload (ajustar ao Swagger)
- `nfse_config.sefin.base_url_sefin` = base de **homologação** primeiro.
- `rota_emissao` / `rota_consulta` e o corpo do POST em
  `services/nfse/sefin/sefin_client.py` (`{"dpsXmlGZipB64": ...}`) → confirmar no Swagger.

## 4. Testar em HOMOLOGAÇÃO
- `ambiente = "homologacao"` (o builder já força `tpAmb=2`).
- Emitir uma DPS de teste, conferir retorno (chave 50, código verificação),
  gerar o DANFSe (`pdf.templates.gerar_danfse`), validar o XML autorizado.

## 5. Habilitar
- Só então: `sefin.transmissao_habilitada = True` (e, para produção, `ambiente="producao"`).
- A numeração da DPS é sequencial/atômica por `(config, série)` — não reusar números.
