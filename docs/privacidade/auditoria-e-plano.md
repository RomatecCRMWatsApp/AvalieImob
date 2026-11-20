# Auditoria e plano — AvalieImob

Inspeção do código feita em 20/11/2026 na branch `feat/privacidade-lgpd`. Sem acesso ao
banco de produção, ao painel do Railway nem ao histórico completo do git: o que depende
disso está marcado como **pendente/bloqueado**. Nenhuma alteração foi publicada.

Prioridade: **P0** exposição ativa · **P1** alto · **P2** médio · **P3** melhoria.
Tipo: **[L]** obrigação legal identificada · **[T]** recomendação técnica · **[N]** decisão jurídica/de negócio.

## Achados

| ID | P | Tipo | Achado | Evidência | Situação |
|---|---|---|---|---|---|
| A-01 | P1 | L | Cadastro dizia "você concorda com nossos Termos e Política de Privacidade" — **não existe** nenhum dos dois documentos. Aceite inválido e informação falsa ao usuário | `frontend/src/pages/Register.jsx:165` (antes) | **Implementado e testado (build)**: texto trocado por link "como tratamos seus dados". Aceite versionado de Termos: **pendente** (documento não existe — ver P-03) |
| A-02 | P1 | L/N | Selo **"CERTIFICADO LGPD"** no rodapé, cadastro e painel. Não há certificação oficial de LGPD | `LgpdBadge.jsx`, `LgpdSection.jsx` | **Implementado**: vira "Privacidade · LGPD", sem a palavra certificado |
| A-03 | P1 | L/N | Home afirmava "TLS 1.3 + AES-256", "data centers ISO 27001", "exclusão completa… em até 15 dias", "nem nossos engenheiros…", "Total conformidade com a LGPD" — sem comprovação | `LgpdSection.jsx`, `About.jsx`, `mock.js` | **Implementado**: só afirmações verificáveis no código (HTTPS, bcrypt, isolamento por conta, canal de direitos) |
| A-04 | P1 | L | `/privacidade` era linkada no rodapé, cadastro, calculadoras e seção LGPD, mas **não existia** (404). Consentimento da calculadora citava política inexistente | `App.js`, `seo_html._EXATAS` | **Implementado e testado**: página com responsável, canal do titular e cookies; aviso completo aguardando revisão (`data/privacidade.json → aviso_completo_aprovado:false`) |
| A-05 | P1 | L | Sem canal para titulares (inclusive sem conta), sem exportação, sem pedido de exclusão | — | **Implementado e testado**: `routes/privacidade.py`, `services/privacidade.py`, `/privacidade`, Configurações ▸ Privacidade, Admin ▸ Pedidos LGPD |
| A-06 | P1 | L | Google Analytics 4 e Microsoft Clarity carregavam **sem consentimento** sempre que a variável do Railway existisse | `frontend/public/index.html` (antes, linhas 63–89) | **Implementado e testado (Playwright, rede)**: nada baixado antes da escolha; rejeitar mantém bloqueado; aceitar carrega; revogar apaga escolha e cookies de medição |
| A-07 | P1 | T | `GET /api/upload/image/{id}` serve imagens **sem login** (fotos de imóveis, documentos convertidos em imagem). Proteção = id UUID4 não adivinhável | `routes/uploads.py:115` | **Pendente**: exige URL assinada com expiração e revisão das páginas públicas que usam `<img src>`; mudança de risco — plano em `implantacao-e-rollback.md` |
| A-08 | P1 | L | Logs gravavam telefone, e-mail e CPF de clientes em texto aberto (~20 pontos) e tokens de links públicos aparecem no log de acesso | `routes/assinatura_cliente.py:172`, `routes/trials.py:46`, `services/cnd/cnd_service.py:98`, logs do uvicorn | **Implementado e testado**: `services/log_redact.py` instalado em todos os handlers. Limite: texto de traceback não é mascarado |
| A-09 | P1 | N/L | Cada cadastro/assinatura é enviado ao webhook da **ZAYRA** (nome, e-mail, telefone, UTM). Compartilhamento entre aplicativos sem menção em aviso | `services/zayra_webhook.py` | **Pendente jurídico** (P-05): definir base legal e informar no aviso; comportamento não alterado |
| A-10 | P2 | L | Formulário "Fale com um Especialista" mostrava "Mensagem enviada!" **sem enviar nada** | `Footer.jsx:38` | **Implementado**: abre o WhatsApp com o texto, a pessoa confirma o envio |
| A-11 | P2 | T | Conversas do robô e textos de laudos vão a provedores de IA (Groq, Gemini, Anthropic, OpenAI) | `routes/ai.py:_roma_ia_cascata`, `routes/atendimento.py` | **Pendente**: verificar retenção/treino de cada provedor e minimizar prompt — ver `fornecedores-e-ia.md` |
| A-12 | P2 | T | Varredura de segredos só na versão atual (limpa). **Histórico do git não varrido** | `git grep` | **Bloqueado**: precisa autorização para varrer histórico; ver rotação em `implantacao-e-rollback.md` |
| A-13 | P2 | L | Pagamento avulso por período (sem renovação automática). Sem fluxo de arrependimento (CDC art. 49) nem identificação completa do fornecedor no checkout | `routes/payments.py:40` | **Pendente jurídico/negócio** (P-06) |
| A-14 | P3 | T | `logins` em `user_access_log` sem expiração (só o heartbeat tem TTL de 90 dias) | `services/acesso_log.py` | **Pendente**: definir retenção (P-04) |
| A-15 | P3 | T | Páginas de serviço com frases sem comprovação ("mais completa do Brasil", "conformidade total") | `frontend/src/data/servicos/*.json` | **Pendente dono** (já relatado na v1.4.1555) |

## Já correto (verificado, não alterado)

- Isolamento por `user_id` do token em todas as rotas de documentos (auditoria v1.4.1265) e
  testes de isolamento em ONR, inferência, garantias, privacidade.
- `role` não pode ser escolhido pelo cliente (`routes/auth._sanitize_role`); bloqueio por
  conta após 6 senhas erradas; senha mínima 8; reset de senha com token de uso único
  (hash SHA-256, 30 min) e resposta anti-enumeração.
- CORS por lista; headers de segurança globais; `geolocation=(self)`.
- Upload: tipo real conferido por assinatura (`upload_security.detect_content_type`),
  limite 5 MB, nome normalizado.
- Webhook do Mercado Pago: HMAC opcional + reconsulta + dedupe `(id, status)`.
- Certificados ICP e credenciais BYOK cifrados (Fernet).
- Cartão: checkout hospedado do Mercado Pago, nada de cartão no servidor.
