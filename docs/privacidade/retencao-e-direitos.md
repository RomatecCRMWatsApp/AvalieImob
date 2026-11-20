# Retenção, descarte e direitos dos titulares — AvalieImob

## Quatro coisas diferentes (não misturar)

| Ação | O que significa | Como funciona hoje |
|---|---|---|
| **Encerrar a conta de login** | O assinante deixa de usar o sistema | Pedido com protocolo (Configurações ▸ Privacidade). **Não apaga** nada automaticamente |
| **Excluir um cliente do CRM** | O assinante remove um cadastro dele | Feito pelo próprio assinante no painel (já existia) |
| **Atender pedido de titular** | Pessoa (com ou sem conta) pede acesso/correção/eliminação | Formulário em `/privacidade` → protocolo → Admin ▸ Pedidos LGPD |
| **Excluir a empresa (tenant)** | Encerrar todos os dados de um assinante | Não automatizado. Exige plano de impacto e aprovação (ver abaixo) |

"Excluir minha conta" **nunca** apaga a carteira de clientes, laudos ou contratos assinados.

## Fluxo de pedido de titular (implementado)

1. Pedido entra por `/privacidade` (sem conta) ou Configurações ▸ Privacidade (com conta).
2. Recebe protocolo `PRIV-AAAAMMDD-XXXXXX`, status `recebida`, prazo de referência e trilha.
3. **Identidade:** pedido feito logado = verificado pelo login. Pedido público = `pendente`:
   o responsável confirma pelo e-mail informado antes de entregar ou apagar dados
   (proporcional: pedir confirmação a partir do e-mail cadastrado; documento só se houver
   dúvida). Nunca enviar dados a um e-mail diferente do cadastrado sem verificação.
4. Se os dados foram cadastrados por um assinante (cliente de avaliador), encaminhar ao
   assinante, que é o controlador desses dados.
5. Status: `recebida → verificando_identidade → em_analise → atendida | indeferida`, com
   nota e responsável. Indeferimento precisa de motivo registrado.

Prazos de referência: configuráveis em `sys_config._id = "privacidade_prazos"`; padrão
15 dias corridos para todos (a LGPD fixa 15 dias para a declaração completa de acesso,
art. 19, II). **Os demais prazos dependem de validação jurídica** — não publicar como promessa.

## Exportação da própria conta (implementado)

`GET /api/privacidade/meus-dados` gera um JSON na hora (sem link guardado, `no-store`), só
com documentos `user_id = token`. Exclui senha, tokens, certificados, credenciais e binários
(imagens/PDF aparecem como referência). Não é garantia de todo o alcance da portabilidade
do art. 18, V — o alcance precisa de avaliação jurídica. CSV não é gerado (sem risco de
fórmula); se um dia for, prefixar células iniciadas com `= + - @` com apóstrofo.

## Retenção proposta (A VALIDAR com jurídico e contador)

| Categoria | Proposta | Justificativa / exceção |
|---|---|---|
| Conta encerrada | bloquear acesso; anonimizar dados de cadastro após o prazo legal aplicável | Obrigações fiscais/contábeis ligadas a pagamentos |
| Pagamentos e notas | prazo fiscal (ex.: 5 anos — confirmar com contador) | Legislação tributária |
| Laudos, contratos e recibos | decisão do assinante (controlador); manter enquanto a conta existir | Prova em processos, responsabilidade técnica |
| PDFs assinados e trilha de assinatura (IP, geo, user-agent) | mesmo prazo do documento assinado | Prova de autoria (MP 2.200-2, Lei 14.063) |
| Leads da calculadora sem conversão | 12 meses — a validar | Legítimo interesse/consentimento |
| Robô de atendimento | 12 meses — a validar | idem |
| Heartbeat de sessão | 90 dias (já implementado, TTL) | Segurança |
| Logins | **sem prazo hoje** → propor 12 meses | Segurança |
| Logs do servidor | conforme retenção do Railway; já mascarados | Segurança |
| Pedidos de titulares | 5 anos após conclusão — a validar | Prova de atendimento |

## Eliminação (preparado, NÃO executado)

Qualquer eliminação real depende de aprovação específica (ver `implantacao-e-rollback.md`).
Requisitos para o script futuro: idempotente, modo simulação com relatório (quantos
documentos por coleção, quais arquivos no R2), cobre Mongo + R2 + caches; documentos
assinados de terceiros (contrato com várias partes) não são apagados — no máximo
anonimizados com registro do motivo. **Backups:** o Railway mantém cópias próprias e há o
bucket `avalieimob-backups`; definir ciclo limitado, acesso restrito e lista de exclusões a
reaplicar após qualquer restauração. Não prometer apagamento instantâneo.
