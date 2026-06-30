# Geo Urbano — Usucapião Extrajudicial (design)

- **Data:** 2026-06-30
- **Módulo:** `Topografia & Geo / Geo Urbano` (`tipo_servico = "usucapiao"`)
- **Abordagem:** A — novo serviço aditivo dentro do módulo existente (como Desdobro e Retificação foram adicionados). Não toca Remembramento/Desdobro/Retificação.
- **Base normativa:** art. 1.071 CPC + art. 216-A da Lei 6.015/73 (LRP); regulamentação operacional consolidada no **Provimento CNJ 149/2023** (Código Nacional de Normas — Foro Extrajudicial), que absorveu o Prov. 65/2017. Prenotação: art. 406 do Prov. 149/2023. Silêncio do notificado = **concordância** (Lei 13.465/2017).

---

## 1. Objetivo

Permitir produzir o **dossiê completo de usucapião extrajudicial** de imóvel urbano (e rural, por referência) no Geo Urbano: o sistema **gera** as peças de texto e a planta/memorial e **rastreia** (status/upload) as peças formalizadas por terceiros (cartório de notas, advogado, distribuidores), entregando o pacote na ordem de protocolo do RI.

### Divisão GERA × RASTREIA
- **Gera (texto montado):** Requerimento ao Cartório de RI, Minuta da Ata Notarial, Memorial Descritivo, Declaração de Anuência (por confrontante/titular), Notificação de confrontante, Edital, checklist dinâmica, relatório fotográfico.
- **Núcleo técnico (upload georreferenciado):** Planta/Mapa (como nos demais serviços do módulo).
- **Rastreia (status/upload externo):** ata notarial lavrada, requerimento assinado por advogado, certidões (RI, distribuidores, confrontantes), ART/TRT, anuências formalizadas.

---

## 2. Modalidades (seletor)

| chave | Modalidade | Base legal | Prazo | Justo título | Área máx. | Urbano/Rural |
|---|---|---|---|---|---|---|
| `extraordinaria` | Extraordinária | CC art. 1.238 | 15 anos (→10 c/ moradia habitual ou obras/serviços produtivos) | Dispensa | Sem limite | ambos |
| `ordinaria` | Ordinária | CC art. 1.242 | 10 anos (→5 c/ aquisição onerosa + registro cancelado + moradia/investimento) | **Exige** | Sem limite | ambos |
| `especial_urbana` | Especial Urbana (pro misero) | CF art. 183 / CC art. 1.240 | 5 anos | Dispensa | 250 m² | urbano |
| `especial_rural` | Especial Rural (pro labore) | CF art. 191 / CC art. 1.239 | 5 anos | Dispensa | 50 ha | rural |
| `familiar` | Familiar (abandono de lar) | CC art. 1.240-A | 2 anos | Dispensa | 250 m² | urbano |
| `coletiva` | Coletiva | Lei 10.257/2001 art. 10 | 5 anos | Dispensa | > 250 m² (baixa renda, posse indivisa) | urbano |
| `outra` | Cartório define | campo livre `fundamento_legal` | — | — | — | — |

**Defaults sugeridos no seletor:** Extraordinária e Especial Urbana (urbano); Extraordinária e Especial Rural (rural). As demais como secundárias.

**Jurisprudência a travar:** STF RE 422.349 (Tema 815) — a usucapião especial urbana **não** se condiciona ao módulo mínimo de área municipal. A validação **não** pode bloquear lote abaixo do módulo nessa modalidade (os outros serviços do módulo travam lote mínimo; aqui é exceção explícita).

---

## 3. Caso do herdeiro (cenário central de teste)

Herdeiro/condômino com **posse exclusiva** que usucape a fração dos demais coproprietários. Dois institutos:

1. **Posse exclusiva de condômino/herdeiro** (STJ): exige prova do **rompimento do estado de composse** — não basta morar; é preciso demonstrar a exclusão dos demais herdeiros, com posse mansa, pacífica, *animus domini* sobre o todo.
2. **Soma de posses** (art. 1.243 CC + *saisine* art. 1.784 + sucessão da posse art. 1.207): soma a posse do *de cujus* à própria para completar o prazo (ex.: 6 anos do herdeiro + 10 do *de cujus* = 16 → extraordinária).

Roda quase sempre como **Extraordinária** (sem justo título) ou **Ordinária** (com justo título: formal de partilha parcial / cessão de direitos hereditários). Capturado por `soma_posses` + bloco C da checklist (óbito, formal de partilha, certidões dos demais herdeiros, prova da posse exclusiva).

---

## 4. Modelo de dados

Tradução das tabelas relacionais sugeridas (`usucapioes_*`) para **arrays embutidos no documento `geo_urbano_projetos`** (padrão MongoDB do módulo — como `lotes_resultantes`, `confrontantes`, `partes`). Tudo aditivo em `models/geo_urbano.py`.

### 4.1 Novos Literals
```
ModalidadeUsucapiao = extraordinaria | ordinaria | especial_urbana | especial_rural | familiar | coletiva | outra
SituacaoRegistral   = matriculado_terceiro | nao_matriculado | transcricao_antiga
TipoProvaPosse      = agua | luz | iptu | telefone | contrato | benfeitoria | comprovante_endereco | declaracao | foto | outro
StatusDocChecklist  = pendente | anexado | dispensado
BlocoChecklist      = A | B | C | D | E | F | G
# PapelParte estendido: += advogado | herdeiro | titular_tabular | testemunha
```

### 4.2 Sub-models novos
- **`PossePeriodo`** (soma de posses): `id, possuidor_nome, possuidor_doc, vinculo (de_cujus|cedente|proprio), inicio (ano/data), fim (ano/data | "atual"), natureza, observacao`.
- **`ProvaPosse`** (linha do tempo): `id, tipo (TipoProvaPosse), descricao, ano | (periodo_inicio, periodo_fim), upload_id, observacao`.
- **`AnuenteUsucapiao`**: `id, papel (confrontante|titular_tabular), nome, doc, lado, medida_m, tipo (particular|via_publica|area_publica), telefone, endereco, canal (whatsapp|presencial), anuencia: Anuencia (reusa o sub-model da Retificação: pendente|assinada|recusada|notificado), doc_id (declaração gerada)`.
- **`DocChecklistItem`**: `id, bloco (BlocoChecklist), chave, label, obrigatorio (bool), status (StatusDocChecklist), upload_id, observacao`.
- **`Posse`**: `inicio, natureza (default "mansa, pacífica, ininterrupta, com animus domini"), origem, benfeitorias, benfeitorias_data, valor_venal`.

### 4.3 Campos novos em `GeoUrbanoProjeto`
```
modalidade_usucapiao: ModalidadeUsucapiao = "extraordinaria"
fundamento_legal: Optional[str]          # usado quando modalidade = "outra"
valor_atribuido: Optional[float]         # R$ — vai no requerimento/ata
situacao_registral: SituacaoRegistral = "nao_matriculado"
matricula_usucapienda_id: Optional[str]  # aponta p/ um Matricula em matriculas[] (situação matriculado_terceiro)
posse: Posse = Posse()
soma_posses: List[PossePeriodo] = []
provas_posse: List[ProvaPosse] = []
anuentes: List[AnuenteUsucapiao] = []
checklist: List[DocChecklistItem] = []
```
Advogado, cônjuge, herdeiros, titular tabular e testemunhas entram em `partes[]` pelos novos papéis. `AtualizarProjetoBody` ganha os campos correspondentes (parcial, `exclude_unset`).

---

## 5. Serviço `services/geo_urbano/usucapiao.py`

- **`MODALIDADES`**: dict `chave -> {label, fundamento, prazo_anos, prazo_reduzido, condicao_reducao, area_max_m2|area_max_ha, exige_justo_titulo, escopo (urbano|rural|ambos)}`.
- **`validar_posse(projeto) -> dict`**:
  - **Prazo:** período coberto = soma de `soma_posses` (ou `posse.inicio` → hoje). Compara com prazo da modalidade (considerando redução). Retorna `{anos_cobertos, prazo_exigido, ok, faltam}`.
  - **Área:** `area_declarada_m2` vs limite. **Exceção Tema 815:** em `especial_urbana` não bloqueia por módulo mínimo municipal (não usar `lote_minimo_municipal_m2` como trava nesta modalidade).
  - **Justo título:** se `ordinaria` e ausente → pendência.
- **`checklist_para(projeto) -> List[DocChecklistItem]`**: monta a checklist dinâmica (blocos A-G) pela modalidade + `situacao_registral` + caso herdeiro (há `soma_posses` com vínculo `de_cujus`/há partes `herdeiro`) + escopo urbano/rural. Preserva status já marcado ao recomputar (idempotente).
- **`anuentes_de(projeto) -> List[AnuenteUsucapiao]`**: deriva de `confrontantes`/`vertices` (lados) + titular tabular da matrícula, mesclando os anuentes já cadastrados.

---

## 6. Geradores (`services/geo_urbano/generators/`)

`textos.py` (novos builders) + `pdf.py` (novos doc-types no `gerar_pdf` + funções dedicadas para peças por-anuente, como `drl` hoje):
- `requerimento_usucapiao(projeto)` — Prov. 149/2023 / art. 216-A: qualificação do requerente + advogado (OAB), modalidade/fundamento legal, descrição do imóvel (matrícula nº … OU "requer abertura de matrícula" se sem registro), origem/natureza da posse, edificação/benfeitorias **com datas**, **possuidores anteriores somados** (de `soma_posses`), rol de confrontantes, valor atribuído, lista de documentos instrutórios.
- `ata_notarial(projeto)` — minuta-modelo da declaração de posse (tabelião certifica tempo/natureza/condições; oitiva de testemunhas listadas em `partes` papel `testemunha`; comprovantes).
- `declaracao_anuencia(projeto, anuente, tema)` — por anuente (estilo `drl`).
- `notificacao(projeto, anuente, tema)` — notificação de confrontante.
- `edital_usucapiao(projeto, tema)` — edital (interessados incertos).
- **Memorial** e **planta** reusam o existente (`memorial()` + mapa upload).

Checklist dinâmica reflete blocos A-G:
- **A) Jurídica:** requerimento (gerado) · procuração + OAB · ata notarial.
- **B) Técnica:** planta+memorial assinados (profissional + confrontantes + titulares) · ART/TRT (guia paga) · [rural] SIGEF/CCIR/CAR.
- **C) Partes:** docs requerente+cônjuge · comprovante endereço · certidão estado civil < 90 dias · [herdeiro] óbito do *de cujus* + formal de partilha/escritura + certidões dos demais herdeiros + prova posse exclusiva.
- **D) Imóvel:** certidão inteiro teor da matrícula OU negativa de propriedade (sem registro) · certidões dos confrontantes (inteiro teor/negativas) · certidões negativas de ônus e ações reais · IPTU/ITR + valor venal.
- **E) Posse:** provas do período aquisitivo (linha do tempo).
- **F) Pessoais:** certidões negativas dos distribuidores (comarca do imóvel + domicílio do requerente).
- **G) Anuências:** declaração dos confrontantes + anuência dos titulares de direitos da matrícula.

---

## 7. Fluxo de anuências (WhatsApp + presencial)

Por anuente, o operador escolhe o `canal`:
- **WhatsApp:** reusa `assinatura_proprietario` (papel anuente) — lê planta/memorial, desenha, carimbo posicionado.
- **Presencial:** baixa a Declaração de Anuência (PDF) e marca status (assinada/recusada/notificado), estilo DRL da Retificação.

Silêncio do notificado = concordância (Lei 13.465/2017) → refletido como `notificado` (não bloqueia o dossiê).

---

## 8. Dossiê — `ORDEM_DOSSIE_USUCAPIAO`

Capa (Lupa Geo) → Requerimento → Ata Notarial → Planta/Mapa → Memorial → ART/TRT → Certidão/cadeia da matrícula (ou negativa de propriedade) → Declarações de anuência → Certidões dos confrontantes → Certidões negativas (ônus/ações reais) → IPTU/valor venal → **Provas de posse (linha do tempo, por ano)** → Relatório fotográfico → Docs do herdeiro (óbito/partilha) → Justo título → Certidões dos distribuidores → Notificações/Edital → Docs pessoais do requerente.

Ramo `usucapiao` em `_montar_dossie` (routes) e em `dossie.gerar_dossie` (ordem própria).

---

## 9. Rotas (`routes/geo_urbano.py`)

- `_montar_dossie`: ramo `usucapiao`.
- Geração: lista de documentos do usucapião no `GerarDocumentosBody`/dispatch.
- `GET /projetos/{pid}/usucapiao/validacao` — posse/área (`validar_posse`).
- `GET /projetos/{pid}/usucapiao/checklist` — checklist dinâmica (recomputa preservando status).
- Anuentes: CRUD reusando o padrão de `confrontantes`/DRL; `GET …/anuencia/{aid}/declaracao` (PDF); `POST …/anuencia/{aid}/status`.
- `GET …/edital` e `GET …/notificacao/{aid}` (PDFs).
- Uploads (tipos novos): `planta_usucapiao` (ou reusa `mapa`), `ata_notarial`, `certidao_matricula`, `certidao_confrontante` (multi), `certidao_negativa` (multi), `iptu`, `justo_titulo`, `certidao_obito`, `formal_partilha`, `certidao_estado_civil`, `procuracao_oab`, `certidao_distribuidor` (multi), `prova_posse` (multi, vincula `prova_id`), `art_trt`.

---

## 10. Frontend (`GeoUrbanoWizard` + `GeoUrbanoList`)

- `GeoUrbanoList`: `usucapiao.pronto = true` (habilita o seletor).
- Wizard tipo-aware (`isUsucapiao`): etapas — Projeto (modalidade + fundamento + valor + situação registral) · Imóvel/Matrícula · **Posse & Soma de posses** · **Provas (linha do tempo + barra período coberto vs prazo)** · Partes (requerente/cônjuge/advogado-OAB/herdeiros/testemunhas) · Confrontantes & Anuências (canal WhatsApp/presencial + status) · Checklist A-G (status + uploads) · Geração + preview · Entrega (dossiê + ICP do RT na planta/memorial).
- Validação ao vivo: período de posse coberto vs prazo (verde/âmbar) + área vs limite (com nota STF Tema 815 na especial urbana).

---

## 11. Seed + testes

- **`seed_usucapiao`**: caso do **herdeiro** (extraordinária, soma de posse do *de cujus* + herdeiro, lote urbano Açailândia/MA) — fixture de demo/teste.
- **`tests/test_usucapiao.py`**: catálogo de modalidades; `validar_posse` (soma alcança/não alcança prazo; área excede/ok; Tema 815 não trava especial urbana); `checklist_para` (herdeiro adiciona óbito/partilha; ordinária exige justo título; rural adiciona CCIR/CAR/SIGEF); geradores produzem PDF válido (requerimento/ata/anuência/notificação/edital); `anuentes_de`; ordem do dossiê de usucapião. Suíte `geo_urbano` existente segue intacta.

---

## 12. Fora de escopo (v1) / faseamento

**Fora (v1):** termo de declaração testemunhal próprio (testemunhas entram só na minuta da ata); integração automática com MP/Fazendas/distribuidores (tarefas externas rastreadas pela checklist); recertificação SIGEF rural (referencia o módulo Georreferenciamento, não recertifica).

**Faseamento:**
- **Fase 1 — Backend núcleo:** modelo + `usucapiao.py` (modalidades/validação/checklist) + geradores (requerimento, ata, anuência, notificação, edital) + dossiê + rotas + seed + testes.
- **Fase 2 — Frontend:** wizard tipo-aware + List habilitado + uploads + preview + validação ao vivo.
- **Fase 3 — Anuências ponta-a-ponta** (WhatsApp + presencial) + assinatura ICP do RT na planta/memorial.
