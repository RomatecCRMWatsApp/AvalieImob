# Documentos Externos (`doc-ext`) — Assinatura de PDF externo via WhatsApp + ICP

**Data:** 2026-06-27
**Status:** Aprovado (desenho) — pronto para plano de implementação
**Sistema:** AvalieImob v1.4.1062+ (FastAPI + MongoDB + React CRA/JSX + Z-API)

## 1. Contexto e objetivo

Hoje o AvalieImob assina documentos **gerados dentro do sistema** (contratos, recibos, PTAM)
e já possui dois módulos que, juntos, cobrem ~80% do que se quer aqui:

- `routes/documentos_assinatura.py` (v1.4.932) — upload de PDF avulso + assinatura ICP posicionada.
- `routes/assinatura_cliente.py` (v1.4.868→927) — posicionar caixas, enviar link por WhatsApp,
  cliente desenha a assinatura no celular, carimbar o traço, folha de auditoria
  (IP/UA/geo/SHA-256), reenviar o PDF final.

**O que falta:** rodar o fluxo de assinatura via WhatsApp sobre um **PDF arbitrário enviado por
upload** (gerado fora do sistema — contrato particular de compra e venda, termo de comissão,
termo de vistoria, etc.) com uma **lista de N signatários de papéis configuráveis**. Hoje o
`assinatura_cliente` é amarrado a um **contrato gerado** com apenas Contratante + Cônjuge.

**Objetivo:** novo módulo "Documentos Externos" que permite upload de PDF, cadastro de N
signatários, posicionamento visual das assinaturas, envio por WhatsApp, coleta por desenho no
celular, estampagem com metadados auditáveis, assinatura ICP-Brasil final (opcional) do RT e
redistribuição do PDF assinado.

## 2. Decisão arquitetural

**Path B — módulo novo fino que reusa o motor, não a orquestração de contratos.**

Módulo `documentos_externos` próprio (coleção própria, rotas próprias, card próprio) que
**delega** o trabalho pesado às funções de motor já existentes e **nunca toca** `db.contratos`.

Rejeitados:
- *Path A (estender `assinatura_cliente` in place):* generaliza, mas thread "source type" por
  ~10 funções acopladas a `db.contratos` → risco de regressão no fluxo de contrato em produção
  (o módulo mais sensível, estabilizado em v1.4.868→927).
- *Spec literal (greenfield com `pyHanko`/`react-pdf`/ObjectId/`backend/app/`):* reinventa o motor
  e viola as convenções do CLAUDE.md (uuid string id, `user_id` isolation, PAdES já existente,
  CRA/JSX).

### Reuso (sem alteração)
`assinatura_cliente_carimbo.carimbar_documento`, `pdf_preview.renderizar_paginas`,
`marca_dagua.aplicar_marca_dagua`, `zapi_service` + `integracoes_util.carregar_integracoes`,
`r2_storage`, `assinatura_default.gerar_assinatura_nome_b64`, e o pipeline PAdES/ICP de
`routes/assinatura.py`.

### Edições aditivas (não quebram nada existente)
1. `routes/assinatura.py`: `_TIPO_COLECAO["doc-ext"]="documentos_externos"` + branch em
   `_gerar_pdf` (base do ICP = `pdf_key_intermediario` carimbado) + hook pós-ICP
   (marca `finalizado` + distribui). Branches existentes intactos.
2. `assinatura_cliente_carimbo.carimbar_documento`: honrar `posicao.tipo` —
   `assinatura`/`rubrica` carimbam o PNG (como hoje); `data` carimba o timestamp;
   `nome_extenso` carimba o nome. Aditivo, default = `assinatura`.

## 3. Escopo do v1 (decisões fechadas)

**Inclui:**
- Upload de PDF arbitrário (≤25 MB, validação `%PDF-`).
- N signatários com papéis configuráveis (sugestões + texto livre).
- **Tipos de posição múltiplos** por signatário: `assinatura`, `rubrica`, `data`, `nome_extenso`
  (mantido a pedido do usuário).
- Várias caixas por signatário.
- ICP-Brasil final do RT **opcional por documento** (toggle `requer_icp_rt`).
- O RT **desenha + ICP** (opção A dos contratos: traço visível carimbado antes do envio + selo
  ICP no fim; reusa a assinatura salva em `perfil_avaliador.assinatura_visual_b64`).
- Minuta (marca d'água) enviada junto com o link.
- Folha de auditoria, status no card ("X/N assinaram"), reenvio, recusa formal.
- Distribuição automática do PDF final a todos os signatários.

**Cortado do v1 (pode entrar depois):**
- Webhook Z-API de auto-resposta (detecção de intenção "já assinei"/"link expirou").
- Ordem obrigatória de assinatura (`ordem_obrigatoria`).

## 4. Modelo de dados — coleção `documentos_externos`

```
id              # uuid4 hex
user_id         # isolamento
codigo          # DOCEXT-AAAA-NNNN via counters $inc
titulo
descricao?
valor_referencia?

# PDF original (upload)
pdf_key                 # R2: documentos-externos/{uid}/{id}.pdf
pdf_hash_sha256
nome_arquivo
paginas
tamanho

requer_icp_rt           # bool, default true (o toggle)

signatarios: [{
  id, nome, cpf_cnpj, papel, whatsapp, email?,
  posicoes: [{ pagina, x_pt, y_pt, larg_pt, alt_pt, tipo, label? }],  # tipo ∈ assinatura|rubrica|data|nome_extenso
  token, status,        # status ∈ pendente|enviado|assinado|recusado
  assinado_em?, ip?, user_agent?, geo_lat?, geo_lng?, traco_b64?
}]

# RT (corretor)
rt_traco_b64?           # assinatura visual desenhada pelo RT (carimbada antes do envio)
rt_ancora?              # { pagina, x_pt, y_pt, larg_pt, alt_pt } da assinatura visual do RT

pdf_key_intermediario?  # carimbado com as assinaturas dos clientes
pdf_key_final?          # após ICP do RT

status                  # rascunho|aguardando|parcial|clientes_ok|finalizado|cancelado
historico: [{ em, tipo, signatario_id?, ip?, detalhe }]
created_at, updated_at
```

A sessão de assinatura vive **inline no documento** (sem coleção `sessoes` separada). Lookup
público: `find_one({"signatarios.token": token})`. O registro ICP do RT vai para a coleção
existente `assinaturas_pdf` keyed `doc_tipo="doc-ext"`, `doc_id=id`.

### Índices (server.py startup, idempotentes)
```
documentos_externos: codigo (unique), {"signatarios.token": 1} (sparse unique),
                     {user_id:1, created_at:-1}, {status:1, created_at:-1}
```

### Estados (status global)
`rascunho` (criado, sem envio) → `aguardando` (links enviados, ninguém assinou) →
`parcial` (alguns assinaram) → `clientes_ok` (todos os signatários assinaram; falta ICP se
`requer_icp_rt`) → `finalizado` (ICP completo + distribuído, OU sem ICP quando
`requer_icp_rt=false`) → `cancelado`.

## 5. Endpoints

### Autenticadas — `routes/documentos_externos.py` (prefix `/documentos-externos`)
| Método | Rota | Descrição |
|---|---|---|
| POST | `/upload` | multipart PDF → cria rascunho (código, hash, páginas) |
| GET | `` | lista (user_id) |
| GET | `/{id}` | detalhe |
| PATCH | `/{id}` | edita titulo/descricao/requer_icp_rt |
| DELETE | `/{id}` | cancela (soft) + remove R2 + assinaturas_pdf |
| GET | `/{id}/pdf-original` | PDF original (inline) |
| GET | `/{id}/pdf-intermediario` | PDF carimbado (clientes) |
| GET | `/{id}/pdf-final` | PDF final (após ICP) — assinado se houver |
| POST | `/{id}/signatarios` | adiciona signatário |
| PATCH | `/{id}/signatarios/{sid}` | edita (se não assinado) |
| DELETE | `/{id}/signatarios/{sid}` | remove (se não assinado) |
| POST | `/{id}/preparar` | renderiza páginas + pré-carrega assinatura do RT |
| POST | `/{id}/posicionar` | salva posições por signatário, carimba traço do RT, gera tokens, dispara links + minuta |
| POST | `/{id}/reenviar` | reenvia links aos pendentes (telefones editáveis) |
| GET | `/{id}/sessao-status` | status p/ o card |
| POST | `/{id}/distribuir-final` | envia PDF final a todos via WhatsApp |

### ICP — reusa `routes/assinatura.py` com `tipo="doc-ext"`
Frontend chama `/assinatura/icp/doc-ext/{id}/preparar` e `/posicionado` (mesma mecânica do
posicionador ICP já existente).

### Públicas — `routes/documentos_externos_publico.py` (prefix `/publico/documentos-externos`, rate-limited)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/{token}` | dados do signatário (nome/papel/já assinado) |
| POST | `/{token}` | recebe traço PNG + geo + consentimento → carimba quando todos assinam |
| POST | `/{token}/recusar` | recusa formal → status `recusado` + notifica RT |

## 6. Mudanças no motor de carimbo

`carimbar_documento(base_bytes, posicoes, assinaturas)` passa a olhar `posicao.tipo`:
- `assinatura` / `rubrica` → carimba o PNG do traço do signatário (comportamento atual).
- `data` → carimba `assinado_em` formatado (DD/MM/AAAA HH:MM:SS).
- `nome_extenso` → carimba o nome do signatário em caixa-alta.

A micro-tag de auditoria (nome • CPF • data • hash curto) e a folha de aceite final
(quadro por signatário com IP/geo/hash) continuam como hoje, agora cobrindo N signatários.

## 7. Frontend (CRA/JSX)

- `lib/api.js` → `documentosExternosAPI` (upload/listar/obter/patch/excluir/signatarios/
  preparar/posicionar/reenviar/status/distribuir + pdfs).
- `components/dashboard/documentos-externos/DocumentosExternosList.jsx` — card clonado do
  `ContratosList`: Abrir / Ver / PDF / Posicionar / Assinar ICP / WhatsApp / Reenviar /
  Status "X/N assinaram" / Excluir; badge de status; código `DOCEXT-AAAA-NNNN`.
- `ModalUpload.jsx` — drag-and-drop de PDF + título/descrição + toggle "exigir ICP do RT".
- `ModalSignatarios.jsx` — nome/CPF-CNPJ/papel(sugestões+livre)/WhatsApp/email +
  quick-add de `clientsAPI`.
- `PositionerDocExt.jsx` — clone do `AssinaturaClienteModal` para **N signatários**: cor por
  papel, várias caixas por signatário, seletor de tipo de caixa
  (assinatura/rubrica/data/nome), canvas da assinatura do RT, posiciona a caixa do RT.
- Página pública: reusa `AssinarCliente.jsx` numa rota `/assinar-doc/:token` apontando para os
  endpoints `doc-ext` (componente já genérico: token, canvas responsivo, geo, consentimento).
- `Sidebar.jsx` — novo item no bloco **CONTRATOS**, posicionado **logo após "Assinar
  Documentos"** (`id: 'documentos'`) e antes de "Recibos":
  `{ id: 'documentos-externos', label: 'Documentos Externos', icon: Send, route: '/dashboard/documentos-externos', tag: 'NOVO' }`
  (ícone `Send` — envio por WhatsApp — para distinguir do `Stamp` de "Assinar Documentos" e do
  `FileSignature` de "Contratos"; importar `Send` de lucide-react). Rota correspondente em
  `Dashboard.jsx`/`App.js`.

## 8. Fluxo ponta-a-ponta

1. RT faz upload do PDF → sistema persiste, calcula SHA-256, conta páginas, gera
   `DOCEXT-2026-NNNN` (status `rascunho`).
2. RT cadastra N signatários (nome, CPF/CNPJ, papel, WhatsApp).
3. RT abre "Posicionar": desenha a própria assinatura (carimbada antes do envio), posiciona a
   caixa do RT e ≥1 caixa por signatário (com tipo).
4. RT envia links por WhatsApp (Z-API) + minuta (marca d'água) → status `aguardando`.
5. Cada signatário abre o link no celular, confirma dados, desenha a assinatura, consente.
6. Backend carimba os traços nos rects + folha de auditoria; status `parcial` → `clientes_ok`
   quando todos assinam; o intermediário vai para o R2; notifica o RT.
7. Se `requer_icp_rt`: RT assina ICP (posicionador existente, `tipo="doc-ext"`, base =
   intermediário carimbado) → status `finalizado`. Senão, `clientes_ok` já finaliza.
8. Sistema distribui o PDF final a todos os signatários por WhatsApp.

## 9. Validade jurídica

Mesma base do fluxo atual de assinatura do cliente: MP 2.200-2/2001 art. 10 §2º,
Lei 14.063/2020, CPC art. 784 III. Garantias técnicas: hash SHA-256 do original e a cada
assinatura, IP+UA+geolocalização por signatário, termo de aceite explícito, folha de auditoria
anexa, e (quando exigido) selo PAdES ICP-Brasil do RT como camada final.

## 10. Arquivos

**Novos (backend):** `models/documento_externo.py`, `routes/documentos_externos.py`,
`routes/documentos_externos_publico.py`, `services/documento_externo_service.py` (orquestração
fina: posicionar/sessão/reenviar/assinar-público/processar-carimbo/distribuir).

**Novos (frontend):** `DocumentosExternosList.jsx`, `ModalUpload.jsx`, `ModalSignatarios.jsx`,
`PositionerDocExt.jsx`, e a rota pública `/assinar-doc/:token`.

**Edições aditivas:** `routes/assinatura.py` (branch `doc-ext`),
`services/assinatura_cliente_carimbo.py` (tipos de posição), `routes/__init__.py` (2 routers),
`server.py` (índices), `lib/api.js`, `Sidebar.jsx`, `App.js`, `Dashboard.jsx`.

## 11. Casos de teste obrigatórios

1. 3 signatários assinam em ordem aleatória, RT assina ICP, PDF final distribuído.
2. Documento com `requer_icp_rt=false` finaliza ao último cliente assinar (sem ICP).
3. Link expirado (>72h) → status reflete + reenviar gera novo envio (mesmo token).
4. Recusa formal → status `recusado` + RT notificado.
5. PDF grande (50+ páginas) com múltiplas caixas por signatário em páginas distintas.
6. Canvas vazio → backend rejeita.
7. Tipos de caixa `data`/`nome_extenso` carimbam texto correto; `assinatura` carimba PNG.
8. Mesmo WhatsApp para 2 signatários (casal) → tokens distintos, links distintos.
9. ICP com base = intermediário carimbado (não o original) → final contém todas as assinaturas.

## 12. Versionamento

Incrementar `frontend/build-number.txt` e bumpar a entrada de release no CLAUDE.md antes do
deploy, conforme a regra obrigatória do projeto.
