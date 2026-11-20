# Auditoria técnica de privacidade e segurança — AvalieImob

> Revisão de código (somente leitura + correções pequenas) na branch
> `seguranca/privacidade-lgpd`, a partir de `origin/main` @ 51c7c3b (20/11/2026).
> Sem acesso a produção, banco real, Railway ou provedores. Não é auditoria externa nem
> parecer jurídico. Severidade: P0 crítico/exposição ativa · P1 alto · P2 médio · P3 melhoria.

## 1. Como a revisão foi feita

- Varredura automática de todas as consultas Mongo em `backend/routes/*.py` sem
  `user_id` no filtro (201 ocorrências) e revisão manual de cada grupo: em todos os casos
  verificados a rota carrega antes o documento com `{"id": ..., "user_id": uid}` e só
  depois atualiza por `id` — **nenhum IDOR encontrado** nas rotas autenticadas.
- Lista de rotas sem dependência de autenticação (≈55) e leitura do que cada uma devolve.
- Busca de segredos em arquivos versionados (padrões de chaves, `.env`, certificados).
- Busca de dados pessoais em mensagens de log.
- Leitura de `index.html`, armazenamento no navegador, fluxo de cadastro/login/reset,
  webhook do Mercado Pago, cascata de IA.

## 2. Achados

| # | Sev. | Achado | Evidência (antes) | Situação |
|---|---|---|---|---|
| A1 | **P1** | Link público do laudo devolvia o perfil INTEIRO do avaliador: CPF, RG, **imagem da assinatura gráfica**, imagens do cartão/certidão CRECI e CNAI. Qualquer pessoa com o link (cliente, banco, quem recebeu encaminhado) podia copiar a assinatura e o CPF. | `backend/routes/ptam.py:1517` (main 51c7c3b) — `perfil_avaliador` sem projeção; front usa só foto/nome/registros | **Corrigido e testado** — allowlist `backend/services/perfil_publico.py`; teste `test_rota_publica_do_laudo_nao_vaza_assinatura_nem_cpf` |
| A2 | **P1** | Rastreadores opcionais (Google Analytics 4 e **Microsoft Clarity — gravação de sessão**) carregavam incondicionalmente quando o ID estava configurado, antes de qualquer escolha do visitante. | `frontend/public/index.html:62-89` (main) | **Corrigido e testado** — `frontend/public/rastreio-consentido.js` + `CookieConsent.jsx`; 7 testes Jest |
| A3 | **P1** | Links "Política de Privacidade" (consentimento LGPD da calculadora, rodapé, selo) apontavam para `/privacidade`, rota inexistente → servidor respondia 404. O consentimento coletado referencia um documento que não existe. | `frontend/src/pages/avaliacao/Calculadora*.jsx`; `backend/services/seo_html.py` (`_EXATAS` sem `/privacidade`) | **Parcial** — rota criada (mostra "em revisão" + canal do titular); texto final depende de aprovação (minuta pronta) |
| A4 | **P1 (jurídico/comercial)** | Selo "**Certificado LGPD**" e afirmações não verificadas no site: "certificação ISO 27001", "AES-256 em repouso", "exclusão atendida em até 15 dias", "em conformidade com a LGPD". Não existe certificação LGPD oficial; risco de publicidade enganosa (CDC art. 37) e de responsabilização se houver incidente. | `frontend/src/components/common/LgpdBadge.jsx:26`, `frontend/src/components/landing/LgpdSection.jsx:16,26,42` | **Pendente — decisão do dono** (texto publicado não foi alterado). Proposta em `pendencias-juridicas-e-negocio.md` |
| A5 | P2 | Telefones, e-mails e CPF de destinatários gravados em logs (envios WhatsApp/e-mail, CND, prospecção, trials); tokens de links públicos e `?token=` do webhook no access log. | ex.: `routes/assinatura_cliente.py:172,176`, `routes/trials.py:46,56`, `services/cnd/cnd_service.py:98`, `routes/ptam.py:1409` | **Corrigido e testado** — filtro global `backend/services/log_redaction.py` instalado em `server.py` |
| A6 | P2 | Verificação pública de autenticidade (`/v/laudo/v/{hash}`) exibia o CPF completo do titular do certificado ICP. | `backend/routes/assinatura.py:1507` (main) | **Corrigido e testado** — CPF mascarado; CNPJ mantido |
| A7 | P2 | Rota legada `seed-admin` com hash fixo e **senha em texto em comentário**. Rota não está registrada (código morto), mas o segredo está no histórico do git. | `backend/routes/seed.py` (main) | **Corrigido no código**; **rotação pendente** se a senha já foi usada em qualquer conta (ver §4) |
| A8 | P2 | Imagens `/upload/image/{uuid}` servidas sem autenticação (capability URL). UUID v4 não é enumerável, mas a URL vaza por encaminhamento, histórico ou log de terceiros e não expira. Inclui fotos de documentos (CNH, certidões) convertidos de PDF. | `backend/routes/uploads.py:116` | **Pendente** — exige URL assinada com expiração (mudança de arquitetura; afeta PDFs/portal). Conhecido no CLAUDE.md |
| A9 | P2 | Rate limit de login/cadastro/reset usa `get_remote_address` (IP do balanceador do Railway) → limite compartilhado por todos os clientes. O `real_ip` (X-Forwarded-For 1º salto) é falsificável pelo cliente. Bloqueio por conta (6 erros/15 min) mitiga força bruta. | `backend/routes/auth.py:30`, `backend/services/ratelimit.py` | **Pendente** — confirmar semântica do proxy do Railway antes de mudar |
| A10 | P2 | JWT HS256 de 168 h guardado em `localStorage`; sem revogação no logout/troca de senha. XSS = roubo de sessão por até 7 dias. | `services/auth_service.py:20`, `frontend/src/contexts/AuthContext.jsx:9` | **Parcial** — conta encerrada (LGPD) agora perde acesso mesmo com JWT válido (`dependencies._recusar_conta_encerrada`). Revogação geral pendente |
| A11 | P2 | Cadastro responde "E-mail já cadastrado" (enumeração). O reset de senha já é genérico. | `backend/routes/auth.py:71` | **Pendente** — mudar quebra UX; avaliar com o dono (mitigado por 3/min) |
| A12 | P2 | Dados do assinante enviados a outro sistema (webhook ZAYRA / CRM Romatec) em cadastro e pagamento: nome, e-mail, telefone, UTM. Mesmo dono ≠ base legal automática. | `routes/payments.py:156`, `routes/auth.py:26` | **Pendente — decisão jurídica** (finalidade/base legal e menção no aviso) |
| A13 | P2 | Prompts de IA vão a 4 provedores (Groq, Google, Anthropic, OpenAI) com o texto que o usuário digitar, que pode conter CPF/nomes de clientes. Sem minimização automática. | `backend/routes/ai.py:95-183`, `services/contrato_ia_service.py` | **Pendente** — ver `fornecedores-e-ia.md` |
| A14 | P3 | Google Fonts carregado de `fonts.googleapis.com` sem consentimento (envia IP ao Google). | `frontend/public/index.html:55-57` | **Pendente** — hospedar fontes localmente |
| A15 | P3 | Usuário de teste com senha fraca fixa em script (`seed_test_user.py`) — só local, mas a conta não pode existir em produção. | `backend/seed_test_user.py:30` | **Pendente** — conferir em produção (dono) |
| A16 | P3 | Verificação de contrato por hash devolve `pdf_final_url`. Hash é SHA-256 do documento (não adivinhável); quem tem o hash tem o documento. | `routes/contratos_exclusividade.py:516` | Risco aceito — registrar no aviso |
| A17 | — | Uploads: tipo declarado + **tipo real (magic bytes)** + tamanho 5 MB + nome normalizado. PDF rasterizado. | `routes/uploads.py:27-` | **Verificado** — teste de regressão `test_upload_recusa_conteudo_falso` |
| A18 | — | Webhook Mercado Pago: token + HMAC opcional (`MERCADOPAGO_WEBHOOK_SECRET`), reconsulta o pagamento na API, dedupe por (id, status). Checkout hospedado (sem cartão no sistema). | `routes/payments.py:68-`, `services/mp_webhook_seguranca.py` | **Verificado** (testes existentes `test_pagamento_seguranca.py`); HMAC depende da env no Railway |
| A19 | — | Cabeçalhos de segurança, CORS com allowlist, bcrypt, papel admin não atribuível pelo cliente, isolamento por `user_id`. | `server.py:97-`, `routes/auth._sanitize_role` | Verificado por leitura |

Testes pré-existentes que falham na `main` (não relacionados): `tests/test_texto_ia.py::test_normaliza_quebras`
e `tests/test_testemunha_cripto.py::test_resave_nao_incremental_quebra_a_parte` (confirmado
rodando a `origin/main` limpa no mesmo ambiente).

## 3. Plano (o que foi implementado nesta branch)

1. Correções A1, A2, A5, A6, A7 (acima).
2. Módulo `backend/services/privacidade/` + `backend/routes/privacidade.py` (atrás de flags):
   canal do titular sem conta, Central de Privacidade, aceite versionado, consentimento de
   marketing, exportação, exclusão separada (conta × contato × titular × tenant), reaplicação
   após restore, informação de assinatura e pedido de arrependimento.
3. Telas: `/privacidade`, `/termos`, `/privacidade/solicitacao`, `/dashboard/privacidade`.
4. Documentação desta pasta + minutas.

## 4. Plano de rotação de credenciais (preparado — NÃO executado)

| Item | Onde estava | Ação proposta | Impacto | Responsável |
|---|---|---|---|---|
| Senha do antigo `seed-admin` | `backend/routes/seed.py` (histórico git) | Se essa senha foi usada em qualquer conta (admin ou pessoal), trocá-la; conferir se existe conta `admin@romatec.com` em produção e removê-la/trocar senha | baixo | dono |
| Usuário `teste@avalieimob.com` | `seed_test_user.py` | Verificar se existe em produção; se existir, excluir | baixo | dono |

Nenhum valor de segredo foi copiado para relatórios ou documentos.

## 5. Próximos passos recomendados (por prioridade)

1. Decidir A4 (selo/afirmações) — maior risco jurídico imediato e custo zero.
2. URL assinada e com expiração para imagens/documentos (A8).
3. Revogação de sessão (versão de token no usuário) e cookie HttpOnly no lugar de localStorage (A10).
4. Rotina de retenção para leads, atendimento e logs de acesso (ver `retencao-e-direitos.md`).
5. Minimização nos prompts de IA e configuração de retenção/treino por provedor (A13).
