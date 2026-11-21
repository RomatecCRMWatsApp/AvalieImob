# Pendências — integração das calculadoras oficiais da Receita (CBS/IBS/IS/DANFSe)

Itens que **não podem ser chutados**. Enquanto não respondidos, ficam como configuração com valor "não informado".

| ID | Pergunta | Quem responde | Bloqueia |
|---|---|---|---|
| P-01 | Qual repositório é o "CRM Romatec": `Romatec_CRM_WhatsApp` (provável) ou `RomatecVoiceAgent` (ZAYRA)? | Dono | Fase 3 |
| P-02 | Pode criar **3 serviços novos no projeto Railway** (Java 25 ×2 e Go), sem domínio público, só com rede privada? O CRM está no **mesmo projeto Railway** do AvalieImob? Há limite de custo/memória? | Dono | Fase 1 |
| P-03 | Regime tributário da Romatec: Lucro Presumido ou Lucro Real? (a NFS-e 59 confirma que **não** é Simples) | Contador | Simulação do dono |
| P-04 | Confirmar com o contador o **NBS** e o **cClassTrib/CST** aplicáveis a serviços de avaliação imobiliária, PTAM, topografia e georreferenciamento. O `114039000` hoje gravado no módulo NFS-e foi provisório | Contador | Fase 4 |
| P-05 | O DANFSe oficial (gerado a partir do XML) deve **conviver** com o DANFSe temático que o sistema já tem, ou substituí-lo? Recomendação: conviver, só quando houver XML | Dono | Fase 4 (DANFSe) |
| P-06 | O simulador de honorários vale só para a conta do dono ou para **todos os assinantes**? Se for para todos, cada um informa seu regime e códigos | Dono | Fase 4 |
| P-07 | Onde entra o botão "Simular CBS/IBS" no AvalieImob: recibo de honorários, passo Resultado do PTAM, proposta, avaliação de garantias? | Dono | Fase 4 |
| P-08 | Fonte das alíquotas nominais: a calculadora exige `aliquotasNominais` na entrada. Usar sempre os endpoints `dados-abertos/aliquota-*` da própria calculadora (recomendado) ou permitir informar manualmente? | Dono + contador | Fase 2 |

| P-09 | **Alíquotas de 2027 em diante** (CBS, IBS estadual, IBS municipal), por data de vigência, para alimentar a tabela interna. Não estão no código: o administrador cadastra depois que o contador confirmar | Contador | Simulações com data ≥ 2027 |
| P-10 | **Alerta/limite de gasto no Railway** antes de criar os 2 serviços Java (Railway ▸ Usage ▸ limites de uso). O dono confere o saldo em Usage | Dono | Fase 1 em produção |

## Decisões do dono (21/11/2026)

1. **CRM:** priorizar a tela de proposta/contrato. Qual repositório é o CRM e se ele está no mesmo projeto Railway
   continuam em aberto (P-01, P-02); se não estiver, o CRM consome as calculadoras **via backend do AvalieImob**.
2. **Railway:** serviços sem endereço público, só rede privada, no mesmo projeto do AvalieImob.
   Nesta etapa sobem **só** regime regular (1.7.2) e Simples Nacional (1.0.2). O DANFSe (Go) fica para a última fase.
   **App Sleeping desligado** (a 1ª simulação depois de dormir levaria 15–40 s).
3. **Simulador de honorários para todos os assinantes**, com regime, NBS e cClassTrib por conta.
   Vem **desativado** até a conta configurar. Sem código provisório de NBS/cClassTrib.
4. **Botão "Simular CBS/IBS":** primeiro no recibo/honorários do PTAM (AvalieImob) e na proposta/contrato (CRM).
   Proposta e garantias do AvalieImob ficam para depois.
5. **DANFSe oficial** convive com o temático, atrás de flag própria, só para quem tem o XML.

### Alíquotas — modelo híbrido

A documentação oficial (`docs/exemplos.md` do regime regular 1.7.2) diz: as alíquotas de referência estão
cadastradas **só para 2026**; a partir de 2027 a consulta devolve 404 e `aliquotasNominais` passa a ser
**obrigatório** na entrada (antes de 2027, é proibido informá-lo).

Regra adotada:

1. Consultar as tabelas da calculadora (`dados-abertos/aliquota-uniao`, `aliquota-uf`, `aliquota-municipio`) para a
   data da operação, com cache.
2. Sem alíquota na calculadora para a data (2027 em diante): usar a **tabela interna** de alíquotas (CBS, IBS estadual,
   IBS municipal) com vigência por data, mantida pelo **administrador** e válida para todos os assinantes.
   Cada registro guarda **fonte, início e fim da vigência, quem confirmou e data da confirmação**.
3. Resultado calculado com a tabela interna exibe: **"Estimativa com alíquota informada manualmente, aguardando
   confirmação"**.
4. Sem alíquota nos dois lugares: **não calcular**, explicar o motivo, nunca assumir um valor.
5. Nenhuma alíquota de 2027 fica gravada no código (P-09).

## Pendência técnica da Fase 1

- **Build do `Dockerfile.java` não foi concluído dentro desta sandbox**: o proxy local da sessão intercepta HTTPS e o
  Maven no container não aceitou o certificado. Os JARs oficiais foram compilados em Java 25 (dependências baixadas
  fora do container, compilação sem rede) e **medidos rodando**; o smoke test passou. O build no Railway não passa por
  esse proxy, mas **ainda não foi visto funcionando lá**: validar no primeiro deploy.

## Fatos já confirmados

- Os 3 repositórios oficiais existem, são MIT (Receita Federal do Brasil, 2026). Últimas tags em 21/11/2026:
  regime regular `1.7.2`, Simples Nacional `1.0.2`, DANFSe `1.0.0`.
- O regime regular exige Java 25 (`pom.xml`).
- Nada disso é emissão: emissão e transmissão continuam fora do escopo.
