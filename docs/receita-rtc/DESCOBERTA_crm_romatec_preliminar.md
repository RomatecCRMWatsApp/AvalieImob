# Descoberta preliminar — CRM Romatec (leitura pública, sem alterações)

Este arquivo fica no AvalieImob só porque esta sessão tem acesso de escrita apenas a este repositório.
O documento definitivo (`DESCOBERTA_crm.md`) deve ser commitado **no repositório do CRM** quando ele for
aberto numa sessão própria.

## Qual repositório é o "CRM Romatec"? (P-01)

Há dois candidatos na mesma organização do GitHub:

| Repositório | Versão | Stack | Tem propostas? |
|---|---|---|---|
| `Romatec_CRM_WhatsApp` | 1.188.3 | Node + TypeScript 5.9, Express, **tRPC 11**, **Drizzle ORM + MySQL**, React 19 + Vite, Electron; deploy Railway via Dockerfile | Sim: contratos, leads, robô de proposta, simulador de financiamento do empreendimento (`server/routers/simulador.router.ts`) |
| `RomatecVoiceAgent` (ZAYRA) | 3.198.1 | Node + TypeScript, Express, `mysql2`; deploy Railway | Sim: motores de precificação de propostas de consultoria (de onde saíram as propostas do AvalieImob) |

O nome e a presença de funil/leads/contratos apontam para **`Romatec_CRM_WhatsApp`**. Confirmar com o dono.

## O que já dá para dizer

- Mesmo provedor de hospedagem (Railway) do AvalieImob → os dois podem consumir as **mesmas** 3 calculadoras pela
  rede privada do projeto, se ficarem no **mesmo projeto Railway** (P-02). Projetos Railway diferentes não
  compartilham rede privada.
- Migrações versionadas existem (`drizzle/0000…0006` + `drizzle/migrations`): a tabela `simulacao_tributaria` entra
  como migração **aditiva** do Drizzle.
- Valores monetários: usar `decimal` no MySQL e `string`/`Big` no TypeScript, nunca `number` para totais.
- Permissões: o simulador de financiamento já separa equipe × administrador; o simulador tributário deve seguir o
  mesmo padrão (administrador e financeiro).

## Falta levantar (na sessão do CRM)

Entidade exata de proposta/venda no funil, perfis de usuário existentes, padrão de erros e logs, i18n, testes (vitest).
