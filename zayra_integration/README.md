# Feature 04 — Integração ZAYRA → AvalieImob (lado ZAYRA)

Estes arquivos vão no **projeto ZAYRA** (Node 22 + TS + Express + MySQL2), não no
AvalieImob. Foram escritos no modelo **service-to-service (X-API-Key)** porque os
dois sistemas têm segredos JWT próprios.

## 1. Copiar os arquivos

```
src/middleware/requireApiKey.ts   ← requireApiKey.ts
src/routes/galeriaExport.ts       ← galeriaExport.ts
```

Ajuste os imports `../database` (pool MySQL2) e `../middleware/requireApiKey`
ao layout real do ZAYRA.

## 2. Registrar no app.ts do ZAYRA

```typescript
import galeriaExportRouter from './routes/galeriaExport'
app.use('/api/galeria', galeriaExportRouter)
```

## 3. Variável de ambiente no ZAYRA

```
AVALIEIMOB_API_KEY=<gere uma chave forte; a MESMA vai no AvalieImob como ZAYRA_API_KEY>
```

Gerar a chave (exemplo): `openssl rand -hex 32`

## 4. Conferir o schema real ANTES de subir

```sql
DESCRIBE fotos_galeria;
DESCRIBE users;
```

O endpoint assume:
- `users(id, email)`
- `fotos_galeria(id, numero, url, latitude, longitude, endereco, data_hora, legenda, sincronizada, user_id)`

Se um nome de coluna for diferente (ex.: `foto_url` em vez de `url`, ou
`usuario_id` em vez de `user_id`), ajuste o `SELECT` e o `WHERE` em
`galeriaExport.ts`. A foto precisa ter uma **URL acessível** (o AvalieImob baixa
os bytes por ela — pode ser absoluta no storage do ZAYRA ou relativa à API).

## 5. Testar

```bash
curl -H "X-API-Key: $AVALIEIMOB_API_KEY" \
  "https://seu-zayra.up.railway.app/api/galeria/export?user=romateccrm@gmail.com&limit=5"
```

Resposta esperada:

```json
{ "fotos": [ { "id": 191, "numero": 191, "url": "...", "latitude": -4.95, "longitude": -47.49, "data_hora": "2026-06-08T13:20:00Z", "legenda": "..." } ], "total": 1, "limit": 5, "offset": 0 }
```

## 6. Do lado AvalieImob (já implementado)

Variáveis no Railway do **AvalieImob**:

```
ZAYRA_API_URL=https://seu-zayra.up.railway.app
ZAYRA_API_KEY=<a MESMA AVALIEIMOB_API_KEY>
```

Fluxo: `GET /api/zayra/galeria` (lista) e `POST /api/zayra/importar/{ptam_id}`
(baixa os bytes, grava em `db.images` com GPS e referencia em `fotos_imovel`).
A foto importada renderiza no PDF do PTAM com GPS, igual às nativas.

## Decisão de auth (registro)

Optou-se por **X-API-Key + e-mail do avaliador** em vez de "JWT compartilhado".
Vantagem: não exige que ZAYRA e AvalieImob usem o mesmo `JWT_SECRET`/IDs.
Requisito: o e-mail do avaliador no AvalieImob deve existir como `email` no
`users` do ZAYRA (é a chave de casamento). Se preferirem casar por CPF ou por um
campo `external_id`, troque o `WHERE email = ?` no `galeriaExport.ts` e o
identificador enviado em `routes/zayra.py` (`identificador = user.email`).
