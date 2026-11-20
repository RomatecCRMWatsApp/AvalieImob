# Fornecedores e inteligência artificial — AvalieImob

> Levantado pelo código (variáveis de ambiente e URLs chamadas). **Região, retenção,
> treinamento, subprocessadores e contratos NÃO foram verificados** (sem acesso às contas).
> Nada aqui afirma que dados ficam no Brasil.

| Fornecedor | Uso no sistema | Dados enviados | Evidência | A verificar |
|---|---|---|---|---|
| Railway | hospedagem da aplicação e do MongoDB | todos | CLAUDE.md (migração Atlas→Railway), `Dockerfile` | região, backups, DPA, transferência internacional |
| Cloudflare R2 | arquivos (fotos, PDFs, assinaturas) | documentos e imagens | `services/r2_storage.py` | bucket privado? `R2_PUBLIC_BASE` define URL pública — conferir |
| Mercado Pago | checkout hospedado | id do usuário, plano, valor; dados de cartão ficam no MP | `services/mercadopago_service.py` | DPA |
| SendGrid / SMTP (HostGator) | e-mail transacional e prospecção | e-mail, nome, conteúdo | `email_service.py` | região, retenção de logs |
| Z-API / Meta WhatsApp Cloud | envio de links e PDFs | telefone, nome, documentos PDF (via URL R2 temporária) | `services/zapi_service.py`, `meta_whatsapp_service.py` | retenção de mídia, região |
| D4Sign / Clicksign / Autentique | assinatura externa (credenciais do próprio assinante — BYOK) | documento e signatários | `routes/assinatura_externa.py` | contrato do assinante com o provedor |
| Groq, Google Gemini, Anthropic, OpenAI | Roma_IA (chat), cláusulas de contrato, memoriais, robô do site | texto digitado e contexto do documento (pode conter nomes/CPF) | `routes/ai.py:95-183`, `services/contrato_ia_service.py`, `services/atendimento/` | política de treino/retenção por conta de API; uso de dados em API normalmente não treina por padrão, **confirmar em cada contrato** |
| ReceitaWS, CNPJ.ws, ProspectaBR, DataJud e emissores de CND | consultas cadastrais e certidões | CPF/CNPJ consultado | `routes/consulta.py`, `services/cnd/` | base legal da consulta (assinante) |
| Nominatim/OpenStreetMap, Esri | geocodificação, mapas e satélite | endereço/coordenadas | `routes/maps.py`, `services/mapa_estatico.py` | política de uso |
| Google Analytics 4, Microsoft Clarity | estatística e gravação de sessão | navegação; **agora só após consentimento** | `public/rastreio-consentido.js` | mascaramento de campos no Clarity (configurar no painel) |
| Google Fonts | fonte do site | IP do visitante | `public/index.html` | substituir por fonte local |
| ZAYRA / CRM Romatec | notificação de cadastro/assinatura; SSO e provisionamento | nome, e-mail, telefone, UTM, plano | `services/zayra_webhook.py`, `routes/integracoes_romatec.py` | base legal e menção no aviso |

## IA — controles existentes e lacunas

- **Isolamento**: histórico `ai_messages` filtrado por `user_id` + `session_id`
  (`routes/ai.py:227`). O robô público usa coleção própria por sessão.
- **Ferramentas**: a IA não executa ações no banco; só devolve texto. Saída tratada como
  sugestão que o usuário revisa (não há execução de comandos a partir da saída).
- **Prompt injection**: risco limitado (sem ferramentas), mas textos de documentos
  importados (ex.: PDFs extraídos) podem conter instruções — manter a IA sem acesso a
  ações sensíveis.
- **Lacunas (pendente)**: (1) minimização — avisar o usuário para não colar CPF/dados de
  clientes no chat e/ou mascarar CPF antes do envio quando o recurso não precisar dele;
  (2) registrar em contrato/conta de cada provedor a opção de não-treino e retenção;
  (3) a cascata envia o mesmo prompt a provedores diferentes em caso de falha —
  transferência internacional para vários países.
