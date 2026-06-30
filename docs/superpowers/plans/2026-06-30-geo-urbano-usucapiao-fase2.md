# Geo Urbano — Usucapião Extrajudicial (Fase 2: Frontend) — Implementation Plan

**Goal:** Tornar o serviço de Usucapião **usável na interface**: habilitar o seletor + wizard próprio tipo-aware (modalidade → posse & soma de posses → provas → partes/advogado → confrontantes & anuências → checklist A-G → geração → entrega) com validação ao vivo.

**Arquitetura:** componente NOVO `GeoUrbanoUsucapiaoWizard.jsx` (isolado), renderizado pelo componente de rota `GeoUrbanoWizard.jsx` quando `proj.tipo_servico === 'usucapiao'` (não toca o fluxo de remembramento/desdobro/retificação). Reusa `geoUrbanoAPI`, autosave PATCH (debounce), preview de PDF via `documento(id,tipo)` (blob→iframe), o padrão de upload e `EtapaConcluidaBox`. Backend da Fase 1 já provê tudo (validacao/checklist/anuencia/seed/geração/dossiê).

**Verificação:** `yarn build` (CRA) verde a cada task; verificação visual com preview_* ao final.

**Base:** spec §7 em `docs/superpowers/specs/2026-06-30-geo-urbano-usucapiao-design.md`.

---

## Estrutura de arquivos
- **Modificar** `frontend/src/lib/api.js` — `geoUrbanoAPI` += `validacao`, `checklist`, `anuenciaPdf`, `criarSeedUsucapiao`.
- **Modificar** `frontend/src/components/dashboard/topografia/GeoUrbanoList.jsx` — `usucapiao.pronto=true`; botão "Projeto-teste Usucapião"; texto do seletor.
- **Criar** `frontend/src/components/dashboard/topografia/GeoUrbanoUsucapiaoWizard.jsx` — wizard próprio (8 passos).
- **Modificar** `frontend/src/components/dashboard/topografia/GeoUrbanoWizard.jsx` — branch no topo: `if (proj.tipo_servico === 'usucapiao') return <GeoUrbanoUsucapiaoWizard .../>`.

## Passos do wizard de usucapião
1. **Projeto** — modalidade (7) + fundamento (se "outra") + situação registral (3) + valor atribuído + tema. Painel de **validação ao vivo** (`validacao`): anos cobertos vs prazo (barra verde/âmbar), área vs limite (+ nota STF Tema 815 na especial urbana), justo título (ordinária).
2. **Posse & Soma de posses** — início/natureza/origem/benfeitorias/justo título; editor de `soma_posses` (add/remover: possuidor/vínculo/início/fim).
3. **Provas (linha do tempo)** — editor de `provas_posse` (tipo/ano/descrição) + upload `prova_posse` (multi).
4. **Partes** — requerente (PF/PJ), cônjuge, **advogado (OAB)**, herdeiros, testemunhas.
5. **Confrontantes & Anuências** — editor (lado/confrontante/tipo/medida/telefone/canal); baixar Declaração/Notificação (`anuenciaPdf`) + status.
6. **Checklist A-G** — carrega `checklist`; itens agrupados por bloco com status (pendente/anexado/dispensado) + upload por chave.
7. **Geração** — botões gerar/preview de cada peça (`requerimento_usucapiao`/`ata_notarial`/`edital_usucapiao`/`memorial_descritivo`/`dossie`) via `documento(id,tipo)` (iframe).
8. **Entrega** — Dossiê (ver/baixar) + Enviar por WhatsApp (reusa `enviarWhatsapp`, peças de usucapião).

## Tasks
- **T1** — API + List (habilita seletor, botão seed-usucapião, métodos API).
- **T2** — Wizard skeleton + Passo 1 (Projeto + painel de validação).
- **T3** — Passos 2-3 (Posse & soma de posses; Provas).
- **T4** — Passos 4-5 (Partes/advogado; Confrontantes & Anuências).
- **T5** — Passo 6 (Checklist A-G).
- **T6** — Passos 7-8 (Geração; Entrega) + branch em GeoUrbanoWizard.
- **T7** — `yarn build` verde + verificação visual (preview) + bump versão + changelog.

## Notas
- Autosave: PATCH debounced (~1,2s) como o wizard existente; `posse` é dict-merge no backend; `soma_posses`/`provas_posse`/`anuentes`/`checklist` são arrays persistidos.
- `enviarWhatsapp` peça do usucapião: usar `requerimento_usucapiao`/`ata_notarial`/`edital_usucapiao`/`memorial_descritivo`/`dossie` (o `_PECA_LABEL`/`_peca_pdf_bytes` do backend precisa aceitá-las — conferir e estender se necessário na T6).
