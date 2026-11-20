# Inventário de dados pessoais — AvalieImob

> Levantamento técnico feito por inspeção do código (branch `seguranca/privacidade-lgpd`,
> 20/11/2026). **Não foi consultado banco real.** Bases legais são **candidatas, a validar**
> pelo jurídico. "Responsável" = área interna a definir pelo dono (PENDENTE).

## 1. Modelo de negócio e papéis (a validar)

- SaaS B2B/B2C para avaliadores, corretores e técnicos (pessoas físicas e empresas), com
  cadastro público, teste gratuito e assinatura paga por período (Mercado Pago, checkout
  hospedado, **pagamento avulso sem renovação automática**).
- **Dados da conta do assinante**: AvalieImob tende a ser **controlador**.
- **Carteira do assinante** (clientes, partes de contratos, proprietários, testemunhas,
  confrontantes, fotos e documentos de imóveis): quem decide finalidade é o assinante →
  AvalieImob tende a ser **operador**. Exige cláusulas de tratamento no contrato
  (PENDENTE jurídico). Não há compartilhamento entre contas: todas as consultas filtram
  `user_id` (verificado por varredura — ver `auditoria-e-plano.md`).
- **Leads/visitantes** (calculadora, robô de atendimento, prospecção B2B): controlador.
- **Integração com o CRM da Romatec** (SSO/provisionamento e webhook ZAYRA): envio de dados
  de conta/assinatura a outro sistema do mesmo dono. Mesmo dono não autoriza
  compartilhamento automaticamente — **a validar** (finalidade e base legal próprias).

## 2. Operações e categorias

| # | Operação | Titulares | Campos | Onde (coleções/buckets) | Destinatários | Base legal candidata | Retenção proposta | Descarte |
|---|---|---|---|---|---|---|---|---|
| 1 | Conta e login | assinantes | nome, e-mail, telefone, hash bcrypt, papel, plano, origem de cadastro (referrer/UTM) | `users` | Railway (hosting/DB) | contrato (art. 7º V) | vida da conta + prazo a validar | anonimização (`services/privacidade/exclusao.py`) |
| 2 | Perfil profissional | assinantes | CPF, RG, registros CRECI/CNAI/CFT, endereço, foto, **imagem da assinatura**, cartão/certidão CRECI, CNAI | `perfil_avaliador` | aparece nos PDFs emitidos | contrato | vida da conta | campos zerados na anonimização |
| 3 | Segurança/acesso | assinantes | data/hora de login, contadores, heartbeat | `user_access_log` (TTL 90 d no heartbeat), `users.failed_logins` | — | legítimo interesse / Marco Civil art. 15 (6 meses mínimo p/ registros de acesso a aplicação) | 6–12 meses (a validar) | TTL / anonimização |
| 4 | Pagamentos | assinantes | plano, valor, status, id MP | `transactions`, `payment_events` | Mercado Pago | contrato / obrigação legal | prazo fiscal (a validar, ex. 5 anos) | preservar; não apagar na exclusão de conta |
| 5 | Carteira: clientes | clientes do assinante | nome, CPF/CNPJ, RG, CNH, estado civil, regime de bens, filiação, endereço, telefone, e-mail | `clients` | — | definida pelo assinante | definida pelo assinante | `DELETE /clients/{id}` (escopado) |
| 6 | Laudos PTAM/garantias/locação | proprietários, solicitantes, informantes de amostras | qualificação, endereço exato, matrícula, coordenadas, fotos | `ptam_documents`, `garantias`, `locacoes`, `amostras_mercado`, `images`, R2 | link público por token (opcional) | definida pelo assinante | prova técnica/responsabilidade profissional (a validar) | não reescrever documento assinado |
| 7 | Contratos, procurações, documentos externos, testemunhas | partes, cônjuges, testemunhas | qualificação completa, CNH (imagem), traço de assinatura, IP, geolocalização, user-agent, hash | `contratos`, `contratos_exclusividade`, `documentos_externos`, `assinatura_cliente_sessoes`, `testemunhas`, R2 | Z-API/Meta (link WhatsApp), D4Sign/Clicksign/Autentique (BYOK) | execução de contrato entre as partes / exercício de direitos | prazo prescricional (a validar) | preservar enquanto houver prazo |
| 8 | Topografia (georef, geo urbano, ONR, INSS obra, usucapião) | proprietários, confrontantes, herdeiros, falecidos | qualificação, certidões de óbito/casamento, documentos de identidade, vértices | `georef_projetos`, `geo_urbano_projetos`, `onr_sigri_jobs`, `inss_obra`, R2 | cartórios/Prefeitura (pelo assinante) | definida pelo assinante | idem | idem |
| 9 | Calculadora pública | visitantes | nome, WhatsApp, e-mail, dados do imóvel, UTM, consentimento+data | `leads_avaliacao` | e-mail/WhatsApp do dono | consentimento (marcado) | 12 meses sem conversão (a validar) | apagar/anonimizar lote — PENDENTE rotina |
| 10 | Robô de atendimento | visitantes | mensagens livres, contato | `atendimento_conversas` | provedores de IA (cascata) | legítimo interesse / procedimentos preliminares | 12 meses (a validar) | PENDENTE rotina |
| 11 | Prospecção B2B | imobiliárias/corretores | nome, e-mail, telefone, cidade | `prospeccao`, `prospeccao_campanha` | SendGrid/SMTP, Z-API | legítimo interesse (B2B) com opt-out (`/prospeccao/descadastrar`) | até opt-out + prazo | marcar opt_out |
| 12 | IA (Roma_IA, cláusulas, memoriais) | quem estiver no texto | texto digitado/gerado | `ai_messages` | Groq, Google Gemini, Anthropic, OpenAI | contrato | vida da conta | apagado na anonimização |
| 13 | Consultas CND/CNPJ | titulares consultados | CPF/CNPJ, certidões | `cnd_consultas`, `cnd_certidoes` | ReceitaWS, CNPJ.ws, ProspectaBR, DataJud | definida pelo assinante | 50 últimas visíveis; exclusão manual existe | `DELETE /cnd/consulta/{id}` |
| 14 | Privacidade (novo) | todos | pedidos (nome, e-mail, descrição), aceites (versão/hash/data), consentimentos, exportações (15 min) | `privacidade_pedidos`, `privacidade_aceites`, `privacidade_consentimentos`, `privacidade_exportacoes`, `privacidade_exclusoes` | e-mail (código) | obrigação legal (art. 18) / prova | pedidos: prazo a validar; exportação: conteúdo apagado no download/expiração | — |

## 3. Dados sensíveis, crianças e decisões automatizadas

- **Sensíveis (art. 5º II)**: não há coleta deliberada, mas documentos anexados (CNH,
  certidões de óbito/casamento, fotos) e texto livre podem conter dado sensível ou de
  criança (ex.: herdeiros menores em usucapião). Recomendação: avaliação específica pelo
  jurídico; não há tratamento automatizado sobre eles.
- **Biometria**: a imagem da assinatura desenhada e a CNH NÃO são usadas para
  reconhecimento biométrico (só carimbo visual) — registrar isso no aviso.
- **Decisões automatizadas**: calculadora pública (estimativa indicativa) e enquadramento
  de grau NBR (triagem técnica revisada pelo avaliador). Nenhuma produz efeito jurídico
  sozinha. O robô de atendimento classifica leads (curioso → qualificado) para priorizar
  contato — perfil comercial; transparência recomendada no aviso.

## 4. Público × privado

| Público por padrão | Privado por padrão |
|---|---|
| páginas do site, blog, planos | toda a carteira e documentos |
| perfil profissional **resumido** no portal do laudo (nome, foto, registros, contato profissional) — allowlist em `services/perfil_publico.py` | CPF/RG/assinatura/documentos do avaliador (antes vazavam — corrigido) |
| verificação de autenticidade por hash (CPF do signatário **mascarado**) | — |
| link de laudo/contrato/dossiê **somente se o assinante gerar** o link | imagens `/upload/image/{uuid}`: sem login, mas por UUID não enumerável (risco aceito, ver auditoria) |

## 5. Armazenamento no navegador (cookies/localStorage)

| Item | Finalidade | Categoria |
|---|---|---|
| token JWT e usuário (`localStorage`) | sessão | necessário |
| tema, grupos do menu, rascunhos, sessão do robô/IA, aviso de instalação | preferência/funcionamento | necessário |
| `utm_data`, `landing_page`, `landing_referrer` (sessionStorage) | atribuição de origem do cadastro, enviada só no cadastro | necessário/medição própria — **a validar** |
| `avalie_consentimento_cookies` | guardar a escolha de cookies | necessário |
| Google Analytics 4 (`_ga*`) | estatística | **opcional — só após aceite** |
| Microsoft Clarity (`_clck`, `_clsk`, gravação de sessão) | heatmap/replay | **opcional — só após aceite** |
| Google Fonts (requisição a fonts.googleapis.com) | tipografia | terceiro carregado sem consentimento — recomenda-se hospedar a fonte localmente (pendente) |
| `/blog/evento` | contagem agregada anônima (sem IP) | medição própria sem identificador |
