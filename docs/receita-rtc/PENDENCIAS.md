# PENDENCIAS: Integração das Calculadoras da Receita Federal (CBS / IBS / IS)

**Local no repositório:** `docs/receita-rtc/PENDENCIAS.md`
**Branch:** `feat/receita-rtc-fase0` (local, sem push ao GitHub)
**Última atualização:** 21/11/2026
**Sistemas:** AvalieImob e CRM Romatec

> Este documento é a fonte única de pendências, decisões e regras da integração. Quando uma pendência for resolvida, **não apague**: mude o status para `RESOLVIDA`, registre a data, quem decidiu e a evidência.

**Legenda de status:** `ABERTA` | `EM ANDAMENTO` | `AGUARDA CONTADOR` | `AGUARDA SOLICITANTE` | `RESOLVIDA`

---

## 1. Resumo executivo

| ID | Tema | Status | Responsável pela decisão |
|---|---|---|---|
| P-01 | Identidade do "CRM Romatec" | AGUARDA SOLICITANTE | Solicitante |
| P-02 | Projeto do Railway (CRM e AvalieImob no mesmo projeto?) | AGUARDA SOLICITANTE | Solicitante |
| P-03 | Estimativa de RAM e custo no Railway (medição real) | RESOLVIDA (21/11/2026, medida) | Coddy |
| P-04 | Saldo do plano Railway e alerta de gasto | AGUARDA SOLICITANTE | Solicitante |
| P-05 | Alíquotas de 2027 em diante (tabela interna) | AGUARDA CONTADOR | Contador / Solicitante |
| P-06 | NBS e cClassTrib dos serviços de avaliação | AGUARDA CONTADOR | Contador |
| P-07 | Regime tributário da Romatec | AGUARDA CONTADOR | Contador |
| P-08 | Regime, NBS e cClassTrib por assinante | ABERTA | Produto |
| P-09 | DANFSe oficial (serviço Go) | ABERTA (adiada) | Solicitante |
| P-10 | Versões fixadas das calculadoras | RESOLVIDA (21/11/2026) | Coddy |
| P-11 | Código NBS provisório no módulo de NFS-e | AGUARDA CONTADOR | Contador |
| P-12 | Local do botão "Simular CBS/IBS" | ABERTA | Solicitante |
| P-13 | Simples Nacional: serviço só a partir de 2027 e alíquota efetiva por conta | AGUARDA CONTADOR | Contador / Produto |
| P-14 | Código do município: a tabela da calculadora devolve 0,0 para município inexistente | RESOLVIDA (21/11/2026) | Coddy |

---

## 2. Decisões já tomadas (não reabrir sem motivo)

1. **Branch local.** O trabalho fica em `feat/receita-rtc-fase0`, sem push ao GitHub. O Lote 4 continua separado no branch dele.
2. **Calculadoras oficiais, sem reescrever a lógica tributária.** A fonte da verdade é a resposta da calculadora da Receita.
3. **Rede privada.** Os serviços das calculadoras **não têm endereço público**. Só os backends acessam, pela rede privada do Railway.
4. **Somente os 2 serviços Java na primeira entrega:** regime regular e Simples Nacional. O serviço Go do DANFSe fica para a **última fase** (ver P-09).
5. **Sem App Sleeping no começo** (ver seção 4.4).
6. **Simulador vale para todos os assinantes**, com regime, NBS e cClassTrib configuráveis **por conta**. Padrão: **desativado** até a conta ser configurada.
7. **Nenhum código NBS provisório será usado** no simulador (ver P-11).
8. **DANFSe oficial convive com o gerador temático já existente**, atrás de feature flag, apenas para quem tiver o XML da nota.
9. **Aviso fixo** em todas as telas de simulação: "Estimativa baseada nas calculadoras oficiais da Receita Federal. Não substitui o sistema emissor nem a validação do contador."

---

## 3. Alíquotas: regras (P-05)

### 3.1 O problema

- A calculadora **não escolhe a alíquota sozinha**. Cada pedido de cálculo precisa receber **CBS, IBS estadual e IBS municipal**.
- A documentação da Receita informa que as **alíquotas de referência só estão cadastradas para 2026**.
- Para operações com data **a partir de 2027**, a consulta às tabelas da calculadora não encontra a alíquota, e ela passa a ser **obrigatória na entrada** do cálculo.
- Logo, para simular 2027 em diante, **alguém precisa fornecer e validar as alíquotas**.

### 3.2 Regra de resolução da alíquota (ordem obrigatória)

Para cada simulação, o sistema resolve CBS, IBS-UF e IBS-município separadamente, nesta ordem:

1. **Consulta às tabelas da calculadora** (`GET /dados-abertos/aliquota-uniao`, `/aliquota-uf` e `/aliquota-municipio`), usando a **data da operação** informada.
2. Se a consulta **não encontrar** valor para a data, usa a **tabela interna de alíquotas** (seção 3.3), pegando o registro **vigente na data da operação**.
3. Se **também** não houver registro vigente na tabela interna: **não calcula**. Mostra: "Não há alíquota cadastrada para [tributo] na data [data]. Solicite ao administrador o cadastro." **Nunca assumir, estimar ou reaproveitar** um valor de outro ano.

### 3.3 Tabela interna de alíquotas

**Escopo:** única e **global** (vale para todos os assinantes). CBS, IBS estadual e IBS municipal são iguais para todos que operam na mesma data e localidade, então o assinante **não** digita alíquota.
**Quem edita:** apenas o perfil de administrador do sistema (o solicitante). Assinantes só leem.

Campos mínimos:

| Campo | Tipo | Observação |
|---|---|---|
| id | PK | |
| tributo | enum | `CBS`, `IBS_UF`, `IBS_MUN` |
| uf | texto | obrigatório para `IBS_UF` e `IBS_MUN`; vazio para `CBS` |
| codigo_municipio | texto | código IBGE; obrigatório para `IBS_MUN` |
| aliquota | decimal | percentual, `NUMERIC`/`BigDecimal`, nunca float |
| vigencia_inicio | data | obrigatória |
| vigencia_fim | data | opcional; vazio = vigente até nova regra |
| fonte | texto | obrigatório (norma, resolução, portaria ou documento do contador) |
| situacao | enum | `RASCUNHO`, `CONFIRMADA`, `REVOGADA` |
| confirmado_por | texto | obrigatório quando `CONFIRMADA` |
| confirmado_em | data/hora | obrigatório quando `CONFIRMADA` |
| criado_por / criado_em | | auditoria |

Regras de integridade:

- **Só registros `CONFIRMADA` entram no cálculo.** `RASCUNHO` e `REVOGADA` são ignorados.
- **Não pode haver sobreposição** de vigências para a mesma combinação (tributo, UF, município).
- **Registros são imutáveis depois de confirmados.** Para corrigir, revogar e criar novo registro (histórico preservado).
- **Proibido gravar alíquotas de 2027 em diante no código-fonte, em migrations ou em seeds.** Os valores entram apenas pela interface de administração, depois da validação do contador.
- Toda inclusão, confirmação e revogação gera **log de auditoria**.

### 3.4 Transparência no resultado

- Todo resultado guarda, por tributo, a **origem da alíquota**: `CALCULADORA` ou `TABELA_INTERNA` (com o id do registro).
- Se **qualquer** alíquota veio da tabela interna, a tela mostra o aviso: **"Estimativa com alíquota informada manualmente, aguardando confirmação."**
- O snapshot da simulação guarda: alíquotas usadas, origem de cada uma e a versão da calculadora.
- **Não recalcular snapshots antigos** automaticamente quando uma alíquota for corrigida. Só quando o usuário pedir.

### 3.5 Testes obrigatórios para este tema

- Data de 2026 com alíquota na calculadora: usa `CALCULADORA`.
- Data de 2027 sem registro interno: **não calcula** e mostra a mensagem de ausência.
- Data de 2027 com registro `CONFIRMADA`: calcula, origem `TABELA_INTERNA`, aviso visível.
- Registro `RASCUNHO` ou `REVOGADA`: ignorado.
- Vigências sobrepostas: o cadastro é **rejeitado**.
- Alíquota ausente em apenas um dos três tributos: **não calcula** e identifica qual falta.
- Valor com casas decimais: sem perda de precisão.

### 3.6 Ações pendentes

| # | Ação | Responsável | Status |
|---|---|---|---|
| 1 | Contador fornece as alíquotas de CBS, IBS-UF e IBS-município por vigência, com a fonte legal | Contador | AGUARDA CONTADOR |
| 2 | Definir quais UFs e municípios entram na carga inicial (começar pelos que o solicitante e os assinantes de fato usam) | Solicitante | ABERTA |
| 3 | Implementar a tela de administração e a tabela com auditoria | Coddy | EM ANDAMENTO: backend, regras e auditoria prontos e testados (Fase 2); falta a tela |
| 4 | Definir a rotina de revisão (por exemplo, a cada mudança normativa e no início de cada ano) | Solicitante + Contador | ABERTA |

---

## 4. Railway: regras (P-02, P-03, P-04)

### 4.1 Situação do AvalieImob

- Roda hoje no Railway em **um único container Python**, sem Java nem Go.
- As calculadoras exigem **Java 25** (regime regular e Simples Nacional) e **Go** (DANFSe). O caminho viável é criar **serviços novos no mesmo projeto do Railway**, acessados pela **rede privada**.

### 4.2 Regras de infraestrutura

1. **Sem domínio público e sem porta exposta** nos serviços das calculadoras. Acesso somente pelo hostname interno do Railway (`*.railway.internal`).
2. Cada serviço com **limite de memória configurado**. Limites definidos pela medição (4.3): **768 MB** no regime regular e **512 MB** no Simples Nacional.
3. JVM configurada para economizar: memória máxima de **70% do container** e coletor de lixo simples.
4. **Banco SQLite somente leitura** (`calculadora-pro.db`), gerado na compilação da imagem ou em volume somente leitura. O Simples Nacional **reaproveita o banco do regime regular**.
5. **Healthcheck** configurado em cada serviço, considerando que a subida medida leva **13 a 15 segundos** (até 40 s em máquina mais lenta). Tempo limite do healthcheck: **90 s**. Rotas: regime regular `GET /api/calculadora/dados-abertos/versao`; Simples Nacional `GET /api/versao` (ambas respondem 200 em menos de 10 ms e trazem `versaoApp`/`versaoDb`, usados no snapshot).
6. **Versões fixadas** por tag ou commit (ver P-10). Nada de `main` flutuante.
7. As variáveis de ambiente dos serviços consumidores ficam no padrão:
   ```
   RECEITA_RTC_ENABLED=false
   RECEITA_RTC_REGIME_REGULAR_URL=http://<servico-regime-regular>.railway.internal:<porta>/api
   RECEITA_RTC_SIMPLES_URL=http://<servico-simples>.railway.internal:<porta>/api
   RECEITA_RTC_TIMEOUT_MS=15000
   ```
8. **Se o CRM Romatec estiver em outro projeto do Railway**, a rede privada **não** o alcança. Neste caso, escolher uma das opções e registrar a decisão:
   - (a) O CRM chama o AvalieImob, que faz de ponte para as calculadoras.
   - (b) Mover os serviços ou o CRM para o mesmo projeto.
   - **Não** expor as calculadoras publicamente como solução.

### 4.3 RAM e custo (MEDIDOS em 21/11/2026)

> **Medido**, não estimado. Java 25, perfil offline, imagens das versões fixadas (P-10), `docker stats`.
> Carga: 1.500 pedidos com 16 em paralelo em cada serviço (regime regular com o exemplo oficial de cálculo de
> `docs/exemplos.md`; Simples Nacional com a consulta de atividades). Todos os pedidos responderam 200, sem
> encerramento por falta de memória. Smoke test (`infra/calculadoras-rtc/smoke-test.sh`) passou.

| Serviço | Subida | RAM parado | RAM com carga | Limite definido |
|---|---|---|---|---|
| Regime regular 1.7.2 | ~15 s | 411 a 415 MB | ~479 MB | **768 MB** |
| Simples Nacional 1.0.2 | ~13 s | 371 a 378 MB | ~395 MB | **512 MB** |

- O regime regular **não** foi reduzido para 512 MB: testado com 512 MB, chegou a 479 MB sob carga (**94% do limite**), sem folga.
- O Simples Nacional foi reduzido para 512 MB: com carga ficou em 77% do limite.
- A estimativa preliminar (250 a 350 MB parado) estava **abaixo** do real.
- Depois de aquecido: ~15 ms por cálculo; CPU parada em ~0,2% (~0,002 vCPU).

| Item | Uso medido | Custo |
|---|---|---|
| RAM (2 serviços) | ~0,79 GB parados, ~0,87 GB com uso | ~US$ 8 a 9 / mês |
| CPU | ~0,002 vCPU por serviço parado | menos de US$ 1 / mês |
| Rede privada | n/d | sem cobrança, pelo que se conhece |
| **Total** | | **~US$ 9 a 10 / mês** |

Premissas de preço: RAM a ~US$ 10 por GB/mês e CPU a ~US$ 20 por vCPU/mês, cobrados pelo **uso real** e não pelo limite. **Confirmar em railway.com/pricing**, pois a página não pôde ser aberta na sessão do Coddy.

> **Limitação da medição:** o build do `Dockerfile.java` **não completou dentro da sandbox** (o proxy da sessão intercepta HTTPS e o Maven no container recusou o certificado). Os JARs oficiais foram compilados em Java 25 com as dependências baixadas fora do container e medidos rodando. O build no Railway não passa por esse proxy, mas **ainda não foi visto funcionando lá**: validar no primeiro deploy (4.6, ação 9).

### 4.4 App Sleeping

- **Não ativar no início.** Com o serviço dormindo, a primeira simulação levaria de **15 a 40 segundos**, o que é ruim para o usuário.
- Reavaliar somente se o custo medido exigir economia e se a equipe aceitar a latência da primeira chamada.

### 4.5 Plano, saldo e alerta de gasto (P-04)

- O plano Pro inclui **US$ 20 de uso por mês**, **compartilhado** com o AvalieImob. O que importa é **quanto sobra hoje**.
- O solicitante confere em **Railway > Usage** e registra aqui: saldo disponível por mês: `US$ ____` | data da conferência: `__/__/____`.
- Configurar **alerta e/ou limite de gasto** no Railway antes de subir os serviços. Alerta sugerido a 80% do crédito mensal.
- **Regra de parada:** se a medição real indicar custo adicional maior que o saldo disponível, **não prosseguir** com a criação definitiva. Reportar ao solicitante com alternativas (reduzir limites, unir serviços ou usar outra hospedagem).

### 4.6 Ações pendentes

| # | Ação | Responsável | Status |
|---|---|---|---|
| 1 | Concluir a compilação das imagens, subir os 2 serviços Java e **medir RAM real**: parado e com o exemplo oficial de cálculo | Coddy | RESOLVIDA (21/11/2026) |
| 2 | Atualizar a tabela 4.3 com **valores medidos** e rotulá-los como medidos | Coddy | RESOLVIDA (21/11/2026) |
| 3 | Reduzir o limite de RAM se a medição mostrar folga | Coddy | RESOLVIDA: Simples 512 MB; regime regular mantido em 768 MB |
| 4 | Confirmar preços em railway.com/pricing | Solicitante | ABERTA |
| 5 | Conferir o saldo em Usage e registrar na seção 4.5 | Solicitante | AGUARDA SOLICITANTE |
| 6 | Configurar alerta e limite de gasto | Solicitante | AGUARDA SOLICITANTE |
| 7 | Confirmar se o CRM está no mesmo projeto do Railway (P-02) | Solicitante | AGUARDA SOLICITANTE |
| 8 | Definir o healthcheck e o tempo limite de subida | Coddy | RESOLVIDA: rotas e 90 s em 4.2 item 5 |
| 9 | Validar o build do `Dockerfile.java` no primeiro deploy no Railway | Coddy | ABERTA |

---

## 5. Demais pendências

### P-01: Identidade do "CRM Romatec"

- **Dúvida:** o CRM é o **Romatec_CRM_WhatsApp** (funil, leads e contratos) ou a **ZAYRA**?
- **Impacto:** define onde fica o botão "Simular CBS/IBS" e quais entidades (proposta, contrato, venda) recebem o snapshot.
- **Estado:** a descoberta do CRM está **preliminar** (`DESCOBERTA_crm_romatec_preliminar.md`). Só será concluída depois desta resposta.
- **Critério de escolha:** o sistema que tem **proposta, contrato ou venda com valor**.

### P-06: NBS e cClassTrib dos serviços de avaliação

- **Dúvida:** qual NBS e qual cClassTrib se aplicam a serviços de avaliação imobiliária (PTAM, laudos)?
- **Regra:** **não chutar**. Deve ser **configuração por conta**, com campo obrigatório antes de habilitar o simulador.
- **Responsável:** contador. Registrar aqui o código confirmado, a data e a fonte.

### P-07: Regime tributário da Romatec

- **Fato:** a NFS-e nº 59 mostra que a Romatec **não** é do Simples Nacional.
- **Dúvida:** Lucro Presumido ou Lucro Real? Depende do contador.
- **Impacto:** a Romatec usa a calculadora do **regime regular**.

### P-08: Regime, NBS e cClassTrib por assinante

- Os honorários de PTAM e os recibos são **de cada assinante**, e cada um pode ter regime diferente (Simples Nacional, Lucro Presumido, Lucro Real, ou MEI).
- **Configuração por conta:** regime, NBS, cClassTrib, UF e município de prestação.
- **Regra de segurança:** o simulador **fica desativado** até a conta ter tudo preenchido. O sistema orienta o assinante a **confirmar com o contador dele**.
- **Definir:** como o MEI será tratado (ver o que a calculadora do Simples Nacional aceita) e se haverá aviso específico.
- **O módulo de NFS-e do sistema é só do solicitante** (não é por assinante). Não misturar as configurações dos dois.

### P-09: DANFSe oficial (serviço Go)

- **Decisão:** convive com o gerador temático existente (3 temas), atrás de flag, apenas para quem tiver o XML.
- **Adiado:** o serviço Go **não** sobe na primeira entrega. Será criado somente quando houver demanda ou na última fase.
- **Requisitos futuros:** `SERVER_PORT` diferente do regime regular (que usa 8080), limite de XML de **5 MiB** (`XML_MAX_SIZE_BYTES`), tratar erro 400 como "XML inválido **ou** erro interno" (limitação documentada no repositório oficial).

### P-10: Versões fixadas

| Repositório | Versão a fixar (informada pelo Coddy) |
|---|---|
| calculadora-rtc-regime-regular | 1.7.2 |
| calculadora-rtc-simples-nacional | 1.0.2 |
| calculadora-rtc-gerador-danfse | 1.0.0 |

- **Feito:** tag e **commit SHA** de cada repositório em `infra/calculadoras-rtc/VERSOES.env` (regime regular `32df719…`, Simples `f90b652…`, DANFSe `8d79e6b…`). O `Dockerfile.java` confere o SHA ao clonar e falha se não bater.
- **Regra de atualização:** só atualizar com teste de regressão, usando as fixtures oficiais, e com registro no `CHANGELOG`.

### P-11: Código NBS provisório no módulo de NFS-e

- O módulo de NFS-e do sistema hoje usa o código provisório **114039000**.
- **Decisão:** o simulador **não** o utiliza. O código só deve mudar no módulo de NFS-e **depois** de confirmação do contador (ver P-06).

### P-13: Simples Nacional — data e alíquota efetiva

- **Fato (testado na calculadora 1.0.2, 21/11/2026):** para serviço (documento tipo `91`, atividades `07` a `14`), a calculadora do Simples só calcula com fato gerador **a partir de 2027**. Em 2026 responde **VSN-015** (tipo de documento não suportado). O simulador mostra esse erro traduzido; não há o que fazer para 2026.
- **A calculadora do Simples exige a alíquota efetiva do Simples** (`pIBSSN` e `pCBSSN`, em pontos percentuais) e o código da atividade (`cAtivSN`). Esses valores dependem da faixa de faturamento de cada empresa: entram na **configuração por conta** (P-08), informados pelo assinante a partir do contador dele. O sistema **não** calcula nem sugere esses valores.
- **MEI (`CRT=4`) está fora do escopo da calculadora** (NT 2026.005): o simulador recusa com mensagem clara.
- **Ação:** contador confirmar, para a Romatec e para orientação dos assinantes, de onde tirar `pIBSSN`/`pCBSSN`.

### P-14: Município inexistente

- A consulta `aliquota-municipio` devolve `0,0` (e não erro) para um código de município que não existe. Por isso o sistema **confere o município na lista oficial da UF** (`dados-abertos/ufs/municipios`) antes de calcular, e recusa município de outra UF. Coberto por teste.

### P-12: Local do botão "Simular CBS/IBS"

| Sistema | Primeira entrega | Fase seguinte |
|---|---|---|
| AvalieImob | Recibo / honorários do PTAM | Proposta e avaliação de garantias |
| CRM Romatec | Proposta ou contrato (depende de P-01) | Relatórios |

---

## 6. Riscos registrados

| Risco | Impacto | Mitigação |
|---|---|---|
| Alíquotas de 2027 não cadastradas | Simulação bloqueada para datas futuras | Tabela interna validada pelo contador (seção 3) |
| Alíquota digitada errada | Estimativa incorreta | Só registros `CONFIRMADA`, fonte obrigatória, auditoria, aviso de estimativa |
| Custo no Railway acima do esperado | Estouro do crédito do plano | Limites de RAM, alerta de gasto e regra de parada (seção 4.5) |
| Estimativa de RAM errada | Custo e estabilidade | Medida em 21/11/2026 (4.3); remedir após cada atualização de versão |
| Build da imagem não validado no Railway | Primeiro deploy pode falhar | Validar no primeiro deploy (4.6, ação 9); os JARs oficiais já foram compilados e medidos |
| Assinante usar com regime ou NBS errado | Simulação enganosa | Desativado até configurar, aviso fixo e orientação para o contador |
| Calculadoras fora do ar | Tela de simulação indisponível | Timeout, circuit breaker, mensagem amigável e feature flag |
| Mudança normativa nas calculadoras | Resultado diferente | Versões fixadas, atualização com teste de regressão |
| CRM em outro projeto do Railway | Sem acesso à rede privada | Decisão registrada em 4.2 item 8 |

---

## 7. Checklist para liberar a Fase 1

- [ ] P-01 respondida (qual é o CRM Romatec)
- [ ] P-02 respondida (mesmo projeto do Railway?)
- [ ] Saldo do Railway conferido e registrado (4.5)
- [ ] Alerta/limite de gasto configurado
- [x] RAM medida e tabela 4.3 atualizada com valores reais
- [ ] Custo medido compatível com o saldo disponível
- [x] Versões e SHAs registrados (`infra/calculadoras-rtc/VERSOES.env`)

## 8. Checklist para liberar o simulador em produção

- [ ] Contador confirmou NBS e cClassTrib (P-06) para a conta do solicitante
- [ ] Contador confirmou o regime da Romatec (P-07)
- [ ] Tabela interna de alíquotas com as vigências necessárias, `CONFIRMADA` e com fonte
- [ ] Testes da seção 3.5 passando
- [ ] Aviso fixo visível nas telas
- [ ] Feature flag testada nos dois estados (ligada e desligada)
- [ ] Comportamento com as calculadoras fora do ar testado

---

## 9. Histórico

| Data | Alteração | Autor |
|---|---|---|
| 21/11/2026 | Criação com decisões, regras de alíquotas e Railway | Solicitante + Coddy |
| 21/11/2026 | RAM e custo medidos (4.3), limites 768/512 MB, healthcheck, P-03 e P-10 resolvidas | Coddy |
| 22/11/2026 | Fase 2: módulo `receita_rtc` (cliente, alíquotas híbridas, tabela interna com auditoria, snapshot), 27 testes com respostas reais + teste ao vivo; P-13 e P-14 registradas | Coddy |
