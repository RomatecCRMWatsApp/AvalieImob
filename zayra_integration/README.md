# Feature 04 — Integração ZAYRA → AvalieImob (lado ZAYRA)

> ✅ Os arquivos reais JÁ FORAM aplicados no projeto ZAYRA (RomatecVoiceAgent),
> batendo com o schema verdadeiro. Esta pasta é só referência/histórico.
> Arquivos aplicados no ZAYRA:
> - `src/middleware/requireApiKey.ts`
> - `src/routes/galeriaExport.ts`
> - `src/server.ts` (import + `app.use('/api/galeria', galeriaExportRouter)`)

## Schema real (confirmado no código do ZAYRA)

O spec original assumia `fotos_galeria(user_id, url, sincronizada, email)`. O
**real** (migrations-relatorio-fotografico.ts) é outro:

- `relatorios_fotograficos(id, colaborador, municipio, data_vistoria, ...)`
- `fotos_vistoria(id, relatorio_id, base64_overlay, latitude, longitude,
  logradouro, municipio, horario_captura, descricao, colaborador, ordem)`
- A imagem é o **`base64_overlay`** (já com GPS/data carimbados no overlay técnico).
- O dono da foto é o **`colaborador` (nome)** — não há e-mail/user_id na foto.

## Endpoints criados no ZAYRA

- `GET /api/galeria/export?colaborador=NOME&limit=&offset=&desde=` → lista (metadados + `url`)
- `GET /api/galeria/foto/:id` → decodifica `base64_overlay` e serve os bytes da imagem

Ambos protegidos por `X-API-Key` (= `AVALIEIMOB_API_KEY`).

## Casamento de usuário

O AvalieImob envia o **nome do avaliador** (`perfil_avaliador.nome` → `users.name`)
na query `colaborador`; o ZAYRA filtra `fotos_vistoria.colaborador LIKE '%nome%'`.
Se o nome no AvalieImob e no ZAYRA divergirem, ajuste o nome no perfil do
avaliador (AvalieImob) ou o `colaborador` das fotos (ZAYRA).

## Variáveis de ambiente

AvalieImob (Railway):
```
ZAYRA_API_URL=https://romatecvoiceagent-production.up.railway.app
ZAYRA_API_KEY=<chave>
```
ZAYRA (Railway):
```
AVALIEIMOB_API_KEY=<a MESMA chave>
```

## Teste

```bash
curl -H "X-API-Key: $AVALIEIMOB_API_KEY" \
  "https://romatecvoiceagent-production.up.railway.app/api/galeria/export?colaborador=Jose%20Romario&limit=3"
```
Esperado: `{ "fotos": [ { "id":..., "url":"/api/galeria/foto/...", "latitude":..., "data_hora":..., "legenda":... } ], "total":... }`
