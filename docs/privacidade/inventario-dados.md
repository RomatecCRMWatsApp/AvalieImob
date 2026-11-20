# Inventário de dados pessoais — AvalieImob

Levantado no código em 20/11/2026 (branch `feat/privacidade-lgpd`). Bases legais marcadas
**"a validar"** são candidatas técnicas, não parecer jurídico. Prazos de retenção estão em
`retencao-e-direitos.md`.

## Papéis (a validar pelo jurídico)

| Situação | Quem decide a finalidade | Papel provável do AvalieImob |
|---|---|---|
| Conta do assinante (cadastro, login, pagamento) | J R P Bezerra LTDA (Romatec) | **Controlador** |
| Clientes, imóveis, laudos, contratos que o assinante cadastra | O assinante (avaliador/corretor) | **Operador** — trata por conta do assinante |
| Leads da calculadora pública, robô de atendimento, prospecção B2B, blog | Romatec | **Controlador** |
| Dados de terceiros consultados (CNPJ, certidões, CPF) a pedido do assinante | O assinante | Operador |

Consequência prática: pedido de titular sobre dados que um assinante cadastrou deve ser
encaminhado ao assinante (o canal público avisa isso) — a Romatec não decide sozinha
apagar o laudo de um cliente do avaliador.

## Por operação

| # | Operação | Titulares | Dados | Onde fica | Destinatários | Base legal candidata | Status |
|---|---|---|---|---|---|---|---|
| 1 | Cadastro e conta | Assinante | nome, e-mail, senha (hash bcrypt), perfil, CREA/CRECI opcional, origem do cadastro (página de entrada, referrer, UTM) | `users` | ZAYRA (webhook de leads), e-mail transacional | contrato (art. 7º V) — a validar; origem/UTM: legítimo interesse — a validar | Coleta mínima confirmada no `Register.jsx` (nome, e-mail, senha, papel, CREA opcional) |
| 2 | Login e auditoria de acesso | Assinante | data/hora de login, contagem, heartbeat de sessão | `users`, `user_access_log` (TTL 90 dias) | — | legítimo interesse/segurança — a validar | TTL já existe |
| 3 | Pagamento | Assinante | plano, valor, id da transação, status | `transactions`, `payment_events`, `users` | Mercado Pago (checkout hospedado) | contrato — a validar | Cartão nunca passa pelo servidor |
| 4 | Perfil profissional | Assinante | nome, registros (CRECI/CNAI/CFT/INCRA), endereço, telefone, assinatura gráfica, cartão/certidão CRECI, certificado CNAI | `perfil_avaliador`, R2 | Sai nos laudos/contratos que ele emite | contrato — a validar | — |
| 5 | Certificado digital ICP | Assinante | .pfx cifrado + senha cifrada | `certificados` | — | contrato — a validar | Cifrado (`cert_crypto`); nunca exportado |
| 6 | Clientes e partes | Terceiros (clientes do assinante, cônjuges, testemunhas) | nome, CPF/CNPJ, RG, CNH, filiação, estado civil, endereço, telefone, e-mail, documentos | `clients`, `contratos`, `testemunhas`, `documentos_externos`, R2 | Assinante; WhatsApp (Z-API) para links de assinatura | **definida pelo assinante** (Romatec = operador) | — |
| 7 | Laudos, PTAM, vistorias, georreferenciamento | Terceiros (proprietários, confrontantes) | identificação, matrícula, endereço preciso, fotos com GPS, coordenadas | `ptam_documents`, `vistorias`, `georef_projetos`, `geo_urbano_projetos`, `onr_sigri_jobs`, R2 | Destinatário do laudo; cartórios; link público do laudo | definida pelo assinante | Link público por token (não indexável) |
| 8 | Assinatura eletrônica de clientes | Terceiros | traço/nome digitado, CPF, IP, geolocalização (se permitida), user-agent, hash | sessões de assinatura, PDF final | Partes do contrato | definida pelo assinante; MP 2.200-2 / Lei 14.063 | IP/geo justificados como prova de autoria — retenção a definir |
| 9 | Calculadora pública | Visitante (lead) | nome, WhatsApp, e-mail, dados do imóvel, consentimento + data/hora, UTM | `leads_avaliacao` | Romatec (WhatsApp do dono, e-mail) | consentimento (checkbox desmarcado) | Já pede consentimento; texto ajustado nesta branch |
| 10 | Robô de atendimento | Visitante | mensagens, nome/telefone/e-mail se informados | `atendimento_conversas` | Provedores de IA (Groq/Gemini/Anthropic/OpenAI) | legítimo interesse/consentimento — a validar | Texto da conversa vai ao provedor de IA |
| 11 | Prospecção B2B | Imobiliárias/corretores (dados públicos de empresa) | nome, telefone, e-mail comercial | `prospeccao` | SendGrid/SMTP, Z-API | legítimo interesse — a validar (LIA pendente) | Tem descadastro (opt-out) |
| 12 | Métricas do blog | Visitante | **nenhum dado pessoal** — só artigo, botão e dia | `blog_eventos` | — | não é dado pessoal | Agregado, sem IP/cookie |
| 13 | Medição opcional (GA4/Clarity) | Visitante | identificadores de navegador, páginas, cliques, gravação de sessão (Clarity) | Google / Microsoft | Google, Microsoft | consentimento | **Bloqueado até o aceite** nesta branch |
| 14 | Pedidos de titulares | Qualquer pessoa | nome, e-mail, telefone opcional, descrição, trilha | `privacidade_solicitacoes` | — | obrigação legal (art. 18) | Novo nesta branch |
| 15 | Consultas a terceiros | Terceiros | CNPJ, CPF (validação local por dígito), certidões CND | `cnd_consultas`, `cnd_certidoes` | Receita/órgãos públicos, ProspectaBR, cpf.dev (se configurados) | definida pelo assinante | `/cpf/validar` não consulta base nominal |
| 16 | Logs | Todos | mensagens técnicas | stdout do Railway | Railway | legítimo interesse/segurança | **Mascaramento de e-mail/telefone/CPF/tokens** nesta branch |

## Dados sensíveis, crianças e decisões automatizadas

- **Sensíveis (art. 5º II):** não há coleta dirigida. Podem aparecer em documentos anexados
  pelo assinante (ex.: certidão de óbito em usucapião, CNH). Tratados como documento do
  assinante; nunca publicados por padrão. **Revisão jurídica recomendada.**
- **Crianças/adolescentes:** não há público-alvo; herdeiros menores podem constar em
  partilha/inventário cadastrados pelo assinante.
- **Decisão automatizada:** a estimativa da calculadora pública e o "estágio" do lead no
  robô são automáticos, mas não decidem direitos do titular (são estimativa e organização
  comercial). O valor dos laudos é responsabilidade do profissional. Sem art. 20 aplicável
  identificado — confirmar com o jurídico.

## Público × privado

Público por padrão: páginas do site, blog, `/planos`, `/privacidade`. Por link com token
(não indexável, `noindex`): laudo público, dossiê, aceite/assinatura. Documentos, contatos e
endereços de clientes **não** são publicados por padrão. Exceção conhecida: imagens em
`/upload/image/{id}` servidas sem login (ver `auditoria-e-plano.md`, item A-07).
