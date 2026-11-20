# Lote 0 — Diagnóstico do AvalieImob contra o contrato de implementação

Data: 20/11/2026. Somente leitura: nada foi instalado, executado contra banco, migrado ou publicado.

## 1. Checkout

| Item | Valor |
|---|---|
| Remoto | `github.com/RomatecCRMWatsApp/AvalieImob` |
| Snapshot do contrato | `b3802c1` = `main` atual (bot de build 1561) |
| Checkout local | `873839b` (v1.4.1559), ancestral direto do snapshot |
| Diferença | só `frontend/build-number.txt` (1559 → 1561) |
| CRM Romatec | **não está nesta sessão** — nada do CRM foi lido nem alterado |

## 2. O que o contrato afirma × o que o código mostra

| Afirmação | Confirmado? | Evidência |
|---|---|---|
| Isolamento predominante por `user_id`; `tenant_id` só espelho | Sim | `tenant_id` só em `inferencia`, `pdf_branding`, `r2_storage` |
| Sem voz/transcrição em PTAM/TVI | Sim | nenhuma ocorrência de whisper/transcri/speech no backend/frontend |
| Agenda existente é de Instagram/prospecção | Sim | `routes/instagram.py`, `routes/prospeccao.py` |
| Não há processo/tarefa transversal | Sim | cada módulo tem só `etapas_concluidas` do próprio documento |
| Fila offline em `MobileVistoriaForm`/`useOfflineStorage` | **Parcial** | os arquivos existem, mas **não estão montados em nenhuma rota** (código órfão) e o `syncPending` chama `tviAPI.create` **sem chave de idempotência** — se a resposta se perder, o retry duplica a vistoria |
| Roma_IA = chat com cascata; `services/inferencia` separado | Sim | `routes/ai.py` (`_roma_ia_cascata`) |
| R2 com fallback base64 | Sim | `services/image_store.py` + 7 testes |
| CRM HMAC/SSO | Sim | `routes/integracoes_romatec.py` + 20 testes (assinatura, timestamp velho, jti reutilizado, suspensão) |

## 3. Testes existentes relevantes (não executados nesta inspeção)

Com isolamento entre contas: inferência (rotas e PTAM), ONR, garantias, INSS de obra,
assinatura (credenciais/envios/origem). Também: CRM HMAC/SSO, image store, SEO (noindex de
links pessoais), privacidade, release notes.

**Lacunas**: não há teste de isolamento para **PTAM** (rotas), **TVI**, **contratos genéricos**,
**recibos** e **clientes**; não há teste de **lacre/versão** do PTAM nem de **link público**
devolvendo 404 com token errado.

## 4. Classificação dos tickets

| Ticket | Classificação | Observação |
|---|---|---|
| AIM-P0-001 Snapshot | **feito** (este documento) | |
| AIM-P0-002 Contratos e isolamento | **refinamento** | preencher as lacunas da seção 3 |
| AIM-P1-001 Processo transversal | **proposta nova** | nativo; referencia PTAM/TVI/garantia/contrato/georref por id |
| AIM-P1-002 Ledger de evidências | **proposta nova** | começa como projeção só-leitura das fontes existentes |
| AIM-P1-003 Captura offline | **refinamento + correção** | o código existe mas está desligado e sem idempotência |
| AIM-P1-004 Handoff CRM | **bloqueado por evidência** | depende do contrato do CRM (lead/conversa) — repositório fora desta sessão |
| AIM-P2-001 IA rastreável | **refinamento** | registrar provedor/modelo/latência por chamada em `routes/ai.py` |
| AIM-P2-002 Retenção | **pendente de decisão** | já mapeado em `docs/privacidade/retencao-e-direitos.md` (P-04) |
| AIM-P2-003 SEO verificável | **parcialmente existe** | `SEO_PAGINAS` + `seo_html` + testes; falta manifest único |
| AIM-P3-001 Voz sintética | **não agora** | fora do laudo, fase posterior |

## 5. Os 10 repositórios (licença conferida no HEAD de 20/11/2026)

| Repositório | Licença raiz | Uso recomendado agora |
|---|---|---|
| cal.diy (`ae027bb`) | MIT | inspiração para a agenda de vistoria; integrar só se a agenda nativa não bastar |
| astryx (`938dbc4`) | MIT (beta) | só conceitos de estados de erro/processamento; sem trocar a UI |
| AppFlowy (`8fcee27`) | **AGPL-3.0** | só ideias (checklist/comentários); nada de código |
| openproject (`2725194`) | **GPL-3.0** | só ideias (estados, responsável, prazo); nada de código |
| OpenWhisper (`52be835`) | MIT | referência para ditado; modelos/pesos têm termos próprios |
| Cap (`c7bc350`) | **mista** (AGPL + trechos MIT) | não usar agora |
| VoiceStudio (`d535c6b`) | **AGPL-3.0** + aviso | não usar agora |
| chatwoot (`5d1afdf`) | **mista** (MIT fora de `enterprise/`) | assunto do CRM, não do AvalieImob |
| Open-Generative-AI (`7858e08`) | MIT (provedor MuAPI à parte) | só divulgação pública, fase posterior |
| open-seo (`af3f995`) | MIT (provedores à parte) | checklist de auditoria, sem instalar |

Copiar código de projeto AGPL/GPL para dentro do AvalieImob (SaaS) traria obrigações de
abertura do código. Por isso, nos três itens prioritários, a implementação é **nativa**.

## 6. Primeiro lote proposto (pequeno, sem dependência nova)

**Lote 1 — proteção antes de mexer:**
1. Testes de isolamento para PTAM, TVI, contratos, recibos e clientes (conta A não lê, edita,
   exporta nem baixa PDF da conta B).
2. Teste de lacre/versão do PTAM (alterar após lacre gera nova versão, não sobrescreve).
3. Teste de link público com token errado → 404 e `noindex`.

**Lote 2 — evidência e fila offline (depois do Lote 1):**
1. Chave de idempotência (`client_id` gerado no celular) na criação de vistoria: o servidor
   devolve a existente se a chave já foi vista — o retry deixa de duplicar.
2. Montar o `MobileVistoriaForm` numa rota real com o indicador de pendências.
3. Linha do tempo de evidências **só-leitura** por PTAM/TVI (versões, lacre, fotos com
   GPS/data, assinaturas), sem nova coleção de arquivos.

**Lote 3 — processo e agenda de vistoria (nativos):** coleção `processos` com
`owner_user_id`, `status`, `due_at`, responsável e referências `{tipo, id}` para os documentos
existentes; agenda de vistoria com data/hora, confirmação, cancelamento e reagendamento.

Voz, vídeo, voz sintética e geração multimídia ficam depois, com consentimento e revisão humana.

## 7. Rollback

Lote 1 só adiciona testes. Lote 2 é aditivo (campo `client_id` opcional + índice parcial;
sem ele o comportamento atual continua). Lote 3 é coleção nova atrás de item de menu — basta
esconder o item.
