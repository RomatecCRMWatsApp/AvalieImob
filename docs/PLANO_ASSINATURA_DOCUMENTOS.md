# Esboço — Módulo "Assinatura de Documentos" (PDF avulso + ICP-Brasil)

> Status: **esboço / planejado** (não implementado). Pedido do dono em 14/06/2026.
> Objetivo: o usuário sobe um **PDF qualquer** (ART, TRT, ofício, declaração, etc.) e **assina
> com ICP-Brasil posicionando** a assinatura na página — exatamente como já faz em
> contratos/PTAM/recibo. Reaproveita ~90% da infraestrutura de assinatura existente.

---

## 1. Objetivo e escopo

- **Entrada:** um arquivo **PDF** enviado pelo usuário (upload).
- **Ação:** assinar com **ICP-Brasil (PAdES)**, **posicionando** o carimbo na página escolhida
  (mesma UX do "Posicionar" dos contratos).
- **Saída:** PDF assinado, com **visualizar / baixar**, e histórico/status.
- **Fora do escopo (v1):** assinatura de cliente por link/WhatsApp (canvas), folha de autoria
  (é doc externo — não geramos conteúdo), múltiplos signatários. Pode vir numa v2.

## 2. Fluxo do usuário (UX)

1. Menu lateral **"Documentos"** (novo item, seção Contratos, abaixo de Recibos).
2. Página lista os documentos enviados + botão **"+ Enviar documento"**.
3. Upload do PDF (drag&drop ou seletor) → aparece na lista com status **"Não assinado"**.
4. Botão **"Posicionar / Assinar"** → abre o `AssinaturaPosicionadaModal` (o MESMO dos
   contratos): renderiza as páginas, usuário arrasta o retângulo na posição desejada, escolhe
   o certificado e assina.
5. Status muda para **"Assinado"** → botões **Visualizar**, **Baixar assinado**, e (opcional)
   **Verificação** (QR/hash).
6. Excluir documento (com confirmação).

## 3. Reuso do que JÁ existe (chave do projeto)

O fluxo ICP posicionado já é **genérico por `tipo`** — basta plugar um tipo novo:

| Peça existente | Onde | Como reusar |
|---|---|---|
| Posicionar + assinar ICP | `routes/assinatura.py` (`preparar_assinatura_posicionada`, `assinar_posicionado`, `_gerar_pdf`, `_TIPO_COLECAO`, `_load_assinatura_bytes`, `download_icp`) | adicionar o tipo `"documento"` |
| Modal de posicionar | `components/dashboard/assinatura/AssinaturaPosicionadaModal.jsx` | já recebe `tipo` e `documentId` → passar `tipo="documento"` |
| Certificados ICP | `db.certificados` + `services/pades_service` | nenhuma mudança |
| Storage | `services/r2_storage` | guardar o PDF enviado e o assinado |
| Download/serve | `GET /assinatura/icp/{tipo}/{id}/download` | já keyed por `doc_tipo` |

## 4. Backend

### 4.1 Collection nova: `documentos_assinatura`
```
{ id (uuid), user_id, nome (do arquivo), titulo?, pdf_key (R2) , tamanho, paginas?,
  icp_status?, icp_hash?, icp_signed_at?, pdf_assinatura_key?, created_at, updated_at }
```
> Obs.: os campos `icp_*` e o assinado seguem o MESMO padrão dos contratos; o PDF assinado
> vai para `assinaturas_pdf` (já keyed por `doc_tipo="documento"`).

### 4.2 `_TIPO_COLECAO`
```python
_TIPO_COLECAO["documento"] = "documentos_assinatura"
```

### 4.3 `_gerar_pdf("documento", doc, ...)`
- **NÃO gera nada** — apenas BAIXA o PDF que o usuário enviou (`doc["pdf_key"]` no R2) e
  retorna os bytes. (É um PDF externo; não anexa folha de autoria, não monta layout.)

### 4.4 NOVO `routes/documentos_assinatura.py` (autenticado, isolado por `user_id`)
- `POST /documentos/upload` — multipart com o PDF; valida `%PDF-`; sobe no R2
  (`documentos/{uid}/{id}.pdf`); cria o registro; retorna {id, nome, paginas}.
- `GET /documentos` — lista os do usuário (com `icp_status`).
- `GET /documentos/{id}` — detalhe.
- `DELETE /documentos/{id}` — remove registro (+ objeto R2, best-effort).
- (opcional) `GET /documentos/{id}/pdf` — devolve o PDF original (para "Ver").
- Registrar o router em `routes/__init__.py`.

> Assinatura: usa os endpoints JÁ existentes `/assinatura/icp/documento/{id}/preparar` e
> `/posicionado` e `/download` (só precisam do tipo no `_TIPO_COLECAO` + branch no `_gerar_pdf`).

## 5. Frontend

- `lib/api.js`: `documentosAPI` = { upload(file), listar(), obter(id), excluir(id), pdf(id) }.
- NOVA página `components/dashboard/documentos/DocumentosList.jsx`:
  - header + botão "Enviar documento" (input file PDF, com progress).
  - grid/lista de cards: nome, status (Não assinado / ✓ Assinado), data.
  - por card: **Posicionar/Assinar** (abre `AssinaturaPosicionadaModal tipo="documento"`),
    **Visualizar**, **Baixar assinado** (quando assinado), **Excluir**.
- `Sidebar.jsx` + `Dashboard.jsx`: item "Documentos" (ícone FileSignature/Stamp) →
  rota `/dashboard/documentos`.

## 6. Etapas de implementação (ordem sugerida)

1. Backend: collection + `_TIPO_COLECAO["documento"]` + branch no `_gerar_pdf` + módulo de
   rotas (upload/listar/excluir) + registrar router.
2. Frontend: `documentosAPI` + página de lista/upload + item no menu.
3. Ligar o `AssinaturaPosicionadaModal` com `tipo="documento"` (assinar/baixar).
4. Testar ponta a ponta: upload → posicionar → assinar ICP → baixar assinado.
5. Versionar/deploy (ver memória `avalieimob-infra-deploy`).

## 7. Pontos de atenção

- **Tamanho do upload:** limitar (ex.: 25 MB) e validar `content-type`/header `%PDF-`.
- **Multi-worker:** geração/render do PDF é leve aqui (não regenera), mas o `renderizar_paginas`
  é CPU — manter em `asyncio.to_thread` (já é no fluxo atual).
- **Isolamento:** toda query com `{"user_id": uid}`.
- **Sem folha de autoria** no v1 (doc externo) — só o carimbo ICP/QR do PAdES.
- **R2:** guardar em prefixo próprio (`documentos/`), NÃO no bucket que apaga assinaturas
  (ver memória) — ou já prever bucket sem expiração.

## 8. Possível v2 (futuro)

- Assinatura por **link/WhatsApp** (cliente assina por traço) reusando `assinatura_cliente`.
- **Múltiplos signatários** posicionados.
- **Pastas/tags** e busca de documentos.
- **Modelos** (carimbos prontos por tipo de documento).
