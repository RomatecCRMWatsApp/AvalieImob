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

## Fatos já confirmados

- Os 3 repositórios oficiais existem, são MIT (Receita Federal do Brasil, 2026). Últimas tags em 21/11/2026:
  regime regular `1.7.2`, Simples Nacional `1.0.2`, DANFSe `1.0.0`.
- O regime regular exige Java 25 (`pom.xml`).
- Nada disso é emissão: emissão e transmissão continuam fora do escopo.
