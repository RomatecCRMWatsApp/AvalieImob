# PLANO — Assinatura do Cliente via WhatsApp (AvalieImob, adaptado do MD ZAYRA)

**Stack real:** Python 3 + FastAPI + MongoDB (Motor) · ReportLab/pypdf/pyHanko · Z-API · R2.
**Decisões fechadas (usuário):**
1. Implementar no **AvalieImob** (não ZAYRA).
2. Posicionamento do traço = **reusar "Posicionar"** (corretor arrasta 1 retângulo por signatário; rects salvos; traço carimbado ali via pypdf). **NÃO** usar âncora fixa (page 8) — o bloco de assinaturas é ReportLab-flow e a página varia.

## DE → PARA (o que já existe — REUSAR, não duplicar)

| Conceito | Nome real AvalieImob | Arquivo:linha | Ação |
|---|---|---|---|
| Token de signatário | `gerar_token()` (`secrets.token_urlsafe(32)`) | services/contrato_exclusividade_assinatura.py:13 | reusar |
| Signatário (status/IP/UA/ts/hash) | array `signatarios[]` no doc | routes/contratos_exclusividade.py:53 | reusar padrão |
| Hash documento | `gerar_hash_documento(doc)` | services/contrato_exclusividade_assinatura.py:22 | reusar |
| Z-API texto | `zapi_service.send_text(instance_id,token,security_token,phone,message)` | services/zapi_service.py:153 | reusar |
| Z-API PDF | `zapi_service.send_document_pdf(...)` | services/zapi_service.py:77 | reusar |
| Credenciais Z-API | `integracoes_util.carregar_integracoes(db,uid)` + `_zapi_cfg()` | services/integracoes_util.py:75 ; routes/contratos_exclusividade.py:143 | reusar |
| Render páginas p/ posicionar | `pdf_preview.renderizar_paginas(bytes)` → [{pagina,imagem_b64,largura_pt,altura_pt,largura_px,altura_px}] | services/pdf_preview.py:13 | reusar |
| Endpoint preparar (gera PDF + render) | `POST /assinatura/icp/{tipo}/{id}/preparar` | routes/assinatura.py:918 | reusar/estender |
| Carimbar imagem na página | `_aplicar_carimbo_em_pagina(base, carimbo_page, page_index)` (pypdf merge) | services/pades_service.py:456 | **reusar (com imagem)** |
| Gerar overlay numa caixa | `_gerar_carimbo_em_caixa(page_w,page_h,x,y,larg,alt,...)` | services/pades_service.py:373 | base p/ versão "imagem" |
| ICP PAdES (append, campo RomatecICP) | `assinar_pdf_icp_posicionado()` / `_assinar_pades()` | services/pades_service.py:475 / 293 | reusar (rodar POR ÚLTIMO) |
| PDF assinado (R2+inline) | coleção `assinaturas_pdf` + `_load_assinatura_bytes()` | routes/assinatura.py:866 | reusar |
| Upload R2 | `r2_storage.upload_bytes(data,key,ct)` | services/r2_storage.py:74 | reusar |
| Página pública aceite | `pages/AceiteContrato.jsx` `/aceite/:token` | App.js | estender (add canvas) |
| Página verificar | `pages/VerificarContrato.jsx` `/verificar/:hash` | App.js | reusar |
| `_gerar_pdf(tipo,doc,db,perfil)` (contrato→registry prime2) | routes/assinatura.py:190 | reusar |
| Procuração | `_generate_procuracao_pdf_bytes(doc,uid,empresa)` (só bytes) | routes/contratos.py | posicionar via Posicionar tb |

## Ordem de integridade (PAdES) — CRÍTICO
1. Gera contrato/procuração **sem** ICP. 2. Corretor **posiciona** as caixas (1 por signatário, por doc). 3. Clientes assinam (traço). 4. Quando todos assinam → **carimba os traços** (pypdf) no PDF sem-ICP. 5. **ICP do corretor por último** (pyHanko append) sela tudo. 6. Reenvia PDF final via Z-API.

## Modelo de dados (MongoDB — coleções novas, prefixo `assinatura_cliente_*`)
> Não há tabela paralela de signatários a reaproveitar p/ ESTE fluxo (o de exclusividade é por proprietário). Criar coleção própria, mas reusar helpers acima.

`assinatura_cliente_sessoes`:
```
{ id, user_id, contrato_id, status: pendente|parcial|concluida|expirada|cancelada,
  hash_sessao, expira_em, created_at, updated_at,
  documentos: [ { tipo: contrato|procuracao, pdf_key_base (R2, sem ICP),
                  ancoras: [ {role, pagina(0-idx), x_pt, y_pt, larg_pt, alt_pt} ],
                  pdf_key_final } ],
  signatarios: [ { role: contratante|conjuge_anuente|outorgante, nome, cpf, telefone,
                   token, status: pendente|enviado|assinado|recusado,
                   assinado_em, ip, geo_lat, geo_lng, user_agent, traco_key(R2 png) } ] }
```

## Backend — arquivos
1. **services/assinatura_cliente_carimbo.py** (NÚCLEO testável): `carimbar_traco_em_pagina(pdf_bytes, pagina_idx, rect_pt, traco_png) -> bytes` — gera overlay A4 com `drawImage` do PNG centralizado no rect (margem 4pt, proporção preservada) e faz merge via pypdf (reusa padrão de `_aplicar_carimbo_em_pagina`). `carimbar_documento(pdf_bytes, ancoras, assinaturas) -> (bytes, hash)` + folha de autoria (base legal Lei 14.063/2020, MP 2.200-2, CC 1.647; IP/geo/UA/SHA-256 por signatário).
2. **routes/assinatura_cliente.py** (router autenticado + público):
   - `POST /contratos/{cid}/assinatura-cliente/preparar` → gera PDF(s) sem-ICP, sobe R2, render páginas, devolve p/ posicionar.
   - `POST /contratos/{cid}/assinatura-cliente/posicionar` → salva ancoras[] por role/doc + cria sessão + signatários (token) + dispara Z-API.
   - público `GET /publico/assinatura-cliente/{token}` (rate-limit) → valida token/expira, devolve nome/role + preview.
   - público `POST /publico/assinatura-cliente/{token}` → recebe tracoBase64(png)+geo, salva traço(R2)+IP/UA, status; quando todos assinam → `processar_carimbo` (carimba traços nos rects → ICP último → R2 final → Z-API final + status contrato Assinado).
   - registrar 2 routers em routes/__init__.py + índices no server.py startup (token unique, contrato_id, hash_sessao).
3. Reusar `_gerar_pdf`, `pdf_preview`, `pades_service`, `zapi_service`, `r2_storage`, `gerar_token`, `gerar_hash_documento`.

## Frontend
- **AssinaturaPosicionadaModal**: estender p/ capturar **N caixas** (uma por role) numerando-as; salvar via `/posicionar`.
- Card de Contratos: botão **"📲 Assinatura cliente"** → preparar → modal posicionar → enviar.
- Página pública `/assinar-cliente/:token` (nova, tema verde/dourado): saudação+role, preview PDF, **canvas** (desenho dedo/mouse)+Limpar, checkbox consentimento (Lei 14.063/2020), geo opcional, botão Assinar → `toDataURL('image/png')` → POST. Tela sucesso.
- lib/api.js: `assinaturaClienteAPI` (preparar/posicionar + público obter/assinar).

## Testes
- isolado: `carimbar_traco_em_pagina` embute o PNG no rect certo (conta /XObject, página certa, rect dentro do frame); rejeita página inexistente (422). (Padrão dos testes de fotos/sig já feitos nesta sessão.)

## Aceite
- [ ] Botão dispara preparar→posicionar→envia links Z-API (contratante + cônjuge, números distintos).
- [ ] Público valida token/expira, mostra doc, captura traço+geo+consentimento.
- [ ] Todos assinam → traços carimbados NOS RECTS posicionados (contrato + procuração) + folha de autoria (base legal+SHA-256).
- [ ] ICP do corretor por último (PAdES não invalidada).
- [ ] PDF final reenviado via Z-API; status → Assinado.
- [ ] Sem âncora fixa. Reuso máximo. Build front + isolado verdes. Versionar (build-number + CACHEBUST + CLAUDE.md).
