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
- Baixar o XSD/dicionário do **MOC NFS-e Nacional** (Swagger contribuintes ISSQN,
  `nfse.gov.br/swagger/contribuintesissqn/`).
- Conferir nomes/ordem das tags em `services/nfse/sefin/dps_xml.py`
  (grupos `infDPS/prest/toma/serv/valores/trib/IBSCBS`) — ajustar onde divergir.
- Validar um XML montado contra o XSD (lxml `etree.XMLSchema`).

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
