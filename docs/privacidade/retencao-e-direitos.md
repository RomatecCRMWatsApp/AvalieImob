# Retenção, descarte e direitos dos titulares — AvalieImob

> Prazos marcados **[a validar]** são propostas técnicas; dependem do jurídico/contabilidade.
> Nenhuma rotina de exclusão automática foi ligada nesta branch.

## 1. Política de retenção proposta

| Categoria | Retenção proposta | Fundamento candidato | Mecanismo |
|---|---|---|---|
| Conta do assinante ativa | enquanto ativa | contrato | — |
| Conta encerrada (dados pessoais) | anonimizar após pedido ou X meses sem uso **[a validar]** | fim da finalidade (art. 15/16) | `exclusao.anonimizar_conta` |
| Pagamentos (`transactions`, `payment_events`) | 5 anos **[a validar — prazo fiscal/CDC]** | obrigação legal, defesa | preservado na exclusão de conta |
| Documentos assinados (laudos, contratos, recibos, NFS-e, `assinaturas_pdf`) | prazo prescricional/responsabilidade técnica **[a validar]** | exercício regular de direitos (art. 16 II/7º VI) | preservado; não é reescrito |
| Registros de acesso (`user_access_log`) | mín. 6 meses (Marco Civil art. 15) — proposta 12 meses | obrigação legal | TTL (heartbeat 90 d já existe) **[ajustar]** |
| Leads da calculadora | 12 meses sem conversão **[a validar]** | consentimento | **pendente rotina** |
| Conversas do robô | 12 meses **[a validar]** | legítimo interesse | **pendente rotina** |
| Prospecção B2B | até opt-out; opt-out mantido como lista de supressão | legítimo interesse | `opt_out` |
| Mensagens de IA | vida da conta | contrato | apagadas na anonimização |
| Exportações | 15 min / uso único | — | conteúdo apagado no download ou na expiração |
| Pedidos de titular | 5 anos **[a validar]** | prova de atendimento | — |
| Carteira do assinante | definida pelo assinante (controlador) | — | ferramentas do próprio assinante |

### Soft delete, backups e restauração

- `DELETE /contratos/{id}` é soft delete (marca); outros módulos apagam de fato. Soft delete
  **não** comprova eliminação — documentar por coleção na revisão de retenção.
- Backups (Mongo no Railway e bucket R2): ciclo e acesso **não verificados** (sem acesso).
  Proposta: retenção de backup ≤ 35 dias, acesso restrito, e após qualquer restore rodar
  `services.privacidade.exclusao.reaplicar_exclusoes(db)` — idempotente, reaplica toda
  anonimização registrada em `privacidade_exclusoes` (testado: `test_reaplicacao_apos_restore`).
  Limite: o registro `privacidade_exclusoes` precisa sobreviver ao restore (guardar export
  separado dele) — **pendente procedimento operacional**.
- Arquivos no R2 vinculados à conta (fotos, PDFs) **não** são apagados pela anonimização da
  conta (pertencem à carteira). Exclusão de tenant precisa listar prefixos R2 por usuário.

## 2. Quatro operações diferentes

| Operação | O que faz | O que NÃO faz | Onde |
|---|---|---|---|
| Excluir **conta de login** | anonimiza `users` e dados pessoais do perfil, apaga mensagens de IA/exportações/log de acesso, encerra o login (JWT ainda válido passa a 401) | não apaga carteira, pagamentos nem documentos assinados | `GET/POST /api/privacidade/admin/exclusao/conta/{id}/plano|executar` (execução exige flag + confirmação digitada) |
| Excluir **contato/cliente** | remove o cadastro do contato da carteira do próprio assinante | não reescreve laudos/contratos já emitidos | `DELETE /api/clients/{id}` (existente) + relatório `exclusao.planejar_contato` |
| **Pedido de titular** (sem conta) | registra, confirma e-mail, localiza onde o dado aparece e em qual conta | não decide sozinho; dado de carteira é encaminhado ao assinante controlador | `/api/privacidade/titular/*`, `/api/privacidade/admin/titular/localizar` |
| Excluir **empresa/tenant** | — | **não implementado** | depende de decisão de negócio (prazo, devolução da carteira, contrato) |

## 3. Fluxo dos pedidos

1. Titular abre pedido em `/privacidade/solicitacao` (sem conta) ou na Central (logado).
2. Canal público: código de 6 dígitos enviado ao e-mail (hash no banco, 24 h, 5 tentativas,
   resposta idêntica exista ou não conta — sem enumeração, limite 5 pedidos/hora por IP,
   honeypot). Logado: já autenticado.
3. Status: `aguardando_verificacao → recebido → em_analise / aguardando_informacao /
   encaminhado_controlador → concluido | indeferido`. Cada mudança grava evento em
   `historico` (quem, quando, o quê). Prazo interno = `PRIVACIDADE_PRAZO_DIAS` (padrão 15,
   **a validar** — a LGPD prevê resposta imediata simplificada ou até 15 dias para
   confirmação/acesso completo, art. 19; demais direitos têm regimes próprios).
4. Verificação adicional (documento, procuração) para eliminação ou terceiros: decisão do
   responsável, registrada como nota — o sistema não coleta documentos pelo canal público.

## 4. Exportação (Central de Privacidade)

- JSON ou CSV (CSV com neutralização de fórmulas `= + - @`), gerada no servidor com o
  `user_id` da sessão, link de uso único, 15 min (`PRIVACIDADE_EXPORTACAO_MINUTOS`), exige
  também a sessão do mesmo usuário (outro usuário com o link → 404).
- Inclui conta, perfil (sem imagens), aceites, consentimentos, pedidos, pagamentos e
  **contagem** dos registros de negócio. **Não** inclui conteúdo da carteira (terceiros).
- Não equivale automaticamente a "portabilidade" (art. 18 V depende de regulamentação da ANPD).
