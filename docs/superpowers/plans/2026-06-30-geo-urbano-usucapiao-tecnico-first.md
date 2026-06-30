# Geo Urbano — Usucapião: reestruturação "técnico-first" — Implementation Plan

**Goal:** Reordenar o Usucapião para espelhar o **Remembramento** (peça técnica de agrimensura como motor), reusando o `GeoUrbanoWizard` — usucapião vira mais um `tipo` nele. O bloco jurídico (Posse/Provas/Partes/Anuências/Checklist) vira a **última** aba, seedada.

**Decisão de arquitetura (aprovada):** usucapião vira um tipo no `GeoUrbanoWizard` (máx. reuso). Realização de **baixo risco**: as abas são guardadas por **NOME do passo** (`passoAtual === 'Nome'`) em vez de índice — os corpos JSX existentes **não se movem**; só muda o guard. `PASSOS` passa a ser tipo-aware, então a ORDEM/INCLUSÃO de abas difere por tipo reusando os mesmos blocos. Remembramento mantém os mesmos nomes/ordem → **saída idêntica** (regressão ≈ zero).

**Confirmado pelo usuário:** (1) `/v/:hash` (verificação pública por hash/QR) fica **fora de escopo** (não existe no Geo Urbano); reusa a Aprovação Z-API atual. (2) Ata Notarial **não** entra na assinatura por WhatsApp (é do tabelião) — só peça gerada/baixável.

**Verificação:** `CI=false npx craco build` verde + `py -m pytest tests/test_usucapiao.py tests/test_geo_urbano.py -q` verde.

---

## Abas da usucapião (PASSOS tipo-aware)
`Projeto · Uploads & Extração · Certidões & BCI · Vértices & Mapa · Peças Técnicas · Aprovação · Entrega · Jurídico`
(Remembramento permanece: `Projeto · Uploads · Matrículas & BCI · Vértices & Mapa · Partes · Geração · Aprovação · Entrega`.)
Mapeamento de blocos (guard por nome):
- Projeto → bloco Projeto (+ campos usucapião: modalidade/situação/valor + card Aferição, condicionais por `isUsucapiao`).
- Uploads & Extração → bloco Uploads (cards filtrados por tipo; já é tipo-aware).
- Certidões & BCI → bloco "Matrículas & BCI".
- Vértices & Mapa → idem.
- Peças Técnicas → bloco "Geração" (conjunto de peças da usucapião).
- Aprovação → bloco Aprovação (oculta Superintendência p/ usucapião; possuidor assina requerimento_usucapiao + ART/TRT).
- Entrega → bloco Entrega (capa Lupa + dossiê).
- Jurídico → NOVO bloco `<JuridicoBloco/>` (Posse/Provas/Partes/Anuências/Checklist — extraído do GeoUrbanoUsucapiaoWizard).

## Tasks
- **R1 — Backend:** `assinatura_proprietario` monta as peças por tipo (usucapião → `requerimento_usucapiao` + `art_trt`; demais inalterados). NOVO `POST /projetos/{pid}/usucapiao/seed-juridico` (best-effort: provas_posse ← uploads `prova_posse`; confrontantes ← vértices/confrontantes; checklist marca planta/memorial/ART). Testes.
- **R2 — Frontend GeoUrbanoWizard:** `PASSOS` tipo-aware + `passoAtual` + guards por nome em TODOS os blocos; remover o branch `if usucapiao return <UsucapiaoWizard>`; header tipo-aware ("Usucapião Extrajudicial"); badge de progresso sobre o bloco técnico.
- **R3 — Projeto + Geração + Aprovação tipo-aware:** Projeto ganha modalidade/situação/valor + Aferição (via `usucapiaoValidacao`); Geração usa o conjunto de peças da usucapião; Aprovação oculta Superintendência e usa as peças da usucapião.
- **R4 — JuridicoBloco:** extrair Posse/Provas/Partes/Anuências/Checklist do `GeoUrbanoUsucapiaoWizard` para `JuridicoBloco.jsx`; renderizar no passo "Jurídico"; botão "Seedar do bloco técnico". Remover `GeoUrbanoUsucapiaoWizard.jsx`.
- **R5 — Build verde + versão + changelog.**

## Notas
- Reuso de backend total (extração/uploads/PATCH/documento/capa/dossiê já atendem `tipo=usucapiao`). Único ajuste: peças do `assinatura_proprietario`.
- `bloco_tecnico_concluido`: derivar de `etapas_concluidas` das abas técnicas (ou flag simples); libera/realça o passo Jurídico.
- Sem `juridico` subdoc — os campos (posse/soma_posses/provas_posse/anuentes/checklist) seguem top-level (já no modelo da Fase 1); o "seeding" só os pré-preenche.
