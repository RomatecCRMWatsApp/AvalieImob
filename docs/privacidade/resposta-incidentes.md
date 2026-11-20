# Roteiro de resposta a incidentes de segurança com dados pessoais — AvalieImob

> Roteiro operacional. **Responsáveis e contatos: PENDENTE** (dono definir). Nenhuma
> comunicação à ANPD ou aos titulares é disparada automaticamente pelo sistema.

## Papéis (preencher)

| Papel | Pessoa | Contato |
|---|---|---|
| Coordenador do incidente | [PENDENTE] | [PENDENTE] |
| Técnico (aplicação/Railway/R2) | [PENDENTE] | [PENDENTE] |
| Jurídico / encarregado | [PENDENTE] | [PENDENTE] |
| Comunicação com clientes | [PENDENTE] | [PENDENTE] |

## Etapas

1. **Identificação** (registrar data/hora da ciência): alerta de log, relato de cliente,
   aviso de fornecedor. Abrir registro interno (o quê, quando, quem soube, sistemas).
2. **Contenção** (horas): desativar link público afetado (`link_publico_ativo=false`),
   rotacionar segredo exposto (JWT_SECRET derruba todas as sessões; chaves de API;
   `CREDENCIAIS_FERNET_KEY` exige recriptografar credenciais BYOK), bloquear conta
   comprometida (`plan_status`/`conta_encerrada`), restringir bucket R2.
3. **Preservação de evidência**: exportar logs do Railway do período (já redigidos de PII
   pelo filtro `services/log_redaction.py` — tokens/telefones aparecem mascarados; isso
   reduz exposição mas pode limitar a investigação), snapshot do banco com acesso restrito,
   lista de commits/deploys. Não copiar dados pessoais para canais informais.
4. **Avaliação de risco**: quais categorias (CPF, documentos de identidade, assinatura,
   dados financeiros), quantos titulares, quais contas (assinantes) — usar
   `GET /api/privacidade/admin/titular/localizar` para mapear contas afetadas sem expor
   conteúdo. Avaliar se o incidente pode acarretar **risco ou dano relevante**.
5. **Comunicação**: se houver risco ou dano relevante, comunicar ANPD e titulares no
   prazo e forma do **Regulamento de Comunicação de Incidente de Segurança da ANPD
   (Resolução CD/ANPD nº 15/2024 — conferir versão vigente)**; quando o AvalieImob atuar
   como operador (carteira do assinante), avisar o assinante-controlador sem demora para
   que ele avalie a própria comunicação. Decisão final: coordenador + jurídico.
6. **Recuperação**: corrigir causa, restaurar serviço, se houve restore de backup rodar
   `reaplicar_exclusoes`.
7. **Análise posterior**: registro do incidente (mantido mesmo sem comunicação), ações
   preventivas, atualização deste roteiro.

## Cenários conhecidos para treinar

- Link público de laudo encaminhado indevidamente (A1 corrigido; o laudo em si continua
  acessível a quem tem o link → desativar link).
- URL de imagem `/upload/image/{uuid}` exposta (A8, sem expiração).
- Vazamento de `JWT_SECRET` (permite forjar sessão de qualquer usuário, inclusive admin).
