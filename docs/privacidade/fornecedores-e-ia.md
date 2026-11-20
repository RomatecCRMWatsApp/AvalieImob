# Fornecedores e IA — AvalieImob

Lista tirada das variáveis e integrações presentes no código. **Região, retenção e treino
de modelos não foram verificados** nos contratos dos fornecedores: tudo marcado "verificar".
Não afirmar que os dados ficam no Brasil.

| Fornecedor | Uso | Dados enviados | Região / retenção / contrato |
|---|---|---|---|
| Railway | Hospedagem do app e do MongoDB | Todos | verificar região e DPA |
| Cloudflare R2 | Arquivos (PDFs, imagens, assinaturas) | documentos e imagens | verificar região e DPA |
| Mercado Pago | Checkout hospedado | e-mail, plano, valor | Brasil; termos do MP |
| SendGrid / SMTP (cPanel) / Resend | E-mail transacional e prospecção | e-mail, nome, conteúdo | verificar (SendGrid: EUA) |
| Z-API | WhatsApp (links de assinatura, envio de PDFs, prospecção) | telefone, nome, PDFs | verificar; PDFs grandes passam por URL do R2 |
| Groq, Google Gemini, Anthropic, OpenAI | Roma_IA, robô do site, textos de laudo/contrato | **texto digitado pelo usuário, que pode incluir dados de clientes** | verificar retenção e uso para treino de cada um; transferência internacional provável |
| ZAYRA (sistema da própria Romatec) | Recebe leads de cadastro/assinatura | nome, e-mail, telefone, UTM, plano | definir base legal e informar no aviso (P-05) |
| Google Analytics 4 / Microsoft Clarity | Medição opcional | identificadores do navegador, navegação | só após consentimento (implementado) |
| OpenStreetMap / ESRI | Mapas e imagens de satélite | coordenadas do imóvel (requisição de tile) | público; sem dado pessoal direto |
| ProspectaBR, cpf.dev, CNJ/DataJud, Receita | Consultas a pedido do assinante | CNPJ/CPF consultado | verificar termos |
| D4Sign / Clicksign / Autentique (BYOK) | Assinatura externa com credencial do próprio usuário | PDF e dados dos signatários | contrato é do usuário |

## IA — controles

Já existe: a IA é chamada pelo backend; chaves ficam no servidor; o robô do site tem limite
de mensagens e tamanho; o metadado `<<META>>` é removido antes do visitante ver.

Pendente (P2):
1. Verificar, para cada provedor, retenção e opção de não treinar com os dados; configurar
   onde existir e registrar o risco onde não existir (não prometer opt-out inexistente).
2. Minimizar: não enviar CPF, RG, telefone e e-mail de clientes no prompt quando a tarefa
   não precisa (ex.: "aperfeiçoar texto do memorial"). Proposta: máscara com
   `services/log_redact.redigir` antes do envio nos fluxos de redação.
3. Saída da IA é tratada como texto não confiável (já não executa ações); manter assim.
4. Conversas isoladas por sessão/usuário — conferir `ai_messages` por `user_id`.
