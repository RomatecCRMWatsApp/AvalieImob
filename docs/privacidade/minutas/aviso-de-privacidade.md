versao: 0.1-minuta-2026-11-20

# Aviso de Privacidade — AvalieImob

> **MINUTA PARA REVISÃO JURÍDICA — NÃO PUBLICAR.** Texto preparado pela equipe técnica a
> partir do que o sistema efetivamente faz (ver `docs/privacidade/inventario-dados.md`).
> Os trechos marcados **[PENDENTE]** dependem de dados e decisões do responsável. Este
> texto não é parecer jurídico e não atesta conformidade.

## 1. Quem somos e como falar conosco

- Responsável pelo AvalieImob (controlador): **[PENDENTE — razão social e CPF/CNPJ]**
- Endereço: **[PENDENTE]**
- Canal de privacidade: formulário "Solicitação sobre dados pessoais" no site e e-mail **[PENDENTE]**
- Encarregado (DPO) ou canal equivalente: **[PENDENTE — decisão do responsável/jurídico]**

## 2. A quem este aviso se aplica

1. **Assinantes e pessoas em teste** (avaliadores, corretores, técnicos) que criam conta.
2. **Visitantes do site** e quem usa a calculadora "Quanto vale meu imóvel?" ou o atendimento automático.
3. **Pessoas cadastradas pelos assinantes** (clientes, proprietários, compradores, vendedores,
   testemunhas, confrontantes, informantes de amostras). Para esses dados, em regra **o assinante
   decide por que e como trata** e o AvalieImob processa as informações em nome dele
   **[PENDENTE — confirmar papéis controlador/operador no contrato com o assinante]**.

## 3. Quais dados tratamos e para quê

| Situação | Dados | Finalidade | Base legal candidata **[a validar]** |
|---|---|---|---|
| Conta | nome, e-mail, telefone, senha (só o hash), perfil profissional (registros CRECI/CNAI/CFT, CPF, RG, endereço profissional, assinatura gráfica, documentos de regularidade) | criar e manter a conta, emitir laudos e documentos em nome do profissional | execução de contrato (art. 7º, V) |
| Pagamento | plano, valor, situação e identificador do pagamento | cobrança e comprovação | execução de contrato; obrigação legal |
| Uso e segurança | registros de acesso (data/hora, contagem de logins), bloqueio por tentativas | segurança da conta e prevenção a fraude | legítimo interesse / obrigação legal (Marco Civil) |
| Calculadora | nome, WhatsApp, e-mail, dados do imóvel | enviar estimativa e entrar em contato | consentimento (marcado pelo visitante) |
| Atendimento automático | mensagens digitadas, contato deixado | responder dúvidas e retornar contato | legítimo interesse / procedimentos preliminares |
| Dados da carteira do assinante | qualificação de partes, documentos, imóveis, fotos, coordenadas | prestar o serviço contratado pelo assinante | definida pelo assinante (controlador) |
| Origem de acesso | página de entrada, site de origem, parâmetros de campanha | medir de onde vêm os cadastros | legítimo interesse **[a validar]** |

Não usamos dados para decisões automatizadas que produzam efeitos jurídicos sobre pessoas.
A estimativa da calculadora é indicativa e não substitui laudo.

## 4. Com quem compartilhamos

Fornecedores que operam a plataforma, apenas no necessário: hospedagem e banco de dados,
armazenamento de arquivos, envio de e-mail, envio de WhatsApp, pagamentos, provedores de
inteligência artificial usados nos recursos de texto, assinatura eletrônica escolhida pelo
assinante, mapas e consultas cadastrais públicas. A lista atual está em
`docs/privacidade/fornecedores-e-ia.md` **[PENDENTE — publicar versão resumida]**.
Alguns fornecedores processam dados fora do Brasil **[PENDENTE — mecanismo de transferência
internacional por fornecedor]**.

Documentos compartilhados por link (laudo, contrato, dossiê) ficam acessíveis a quem tiver o
link enquanto ele estiver ativo; o assinante pode desativá-lo.

## 5. Cookies e tecnologias semelhantes

- **Necessários**: sessão de login, preferências de tela, rascunhos e identificação de origem
  do cadastro guardados no navegador.
- **Opcionais**: Google Analytics e Microsoft Clarity (estatística e gravação de sessão),
  quando configurados. **Só são carregados após o seu aceite** e podem ser recusados ou
  revogados a qualquer momento em "Preferências de cookies".

## 6. Por quanto tempo guardamos

Pela duração da conta e, depois, pelos prazos de guarda legal ou de defesa de direitos
(pagamentos, documentos assinados). Detalhe por categoria em
`docs/privacidade/retencao-e-direitos.md` **[PENDENTE — prazos aprovados]**.

## 7. Seus direitos

Confirmação e acesso, correção, anonimização/bloqueio/eliminação, portabilidade, informação
sobre compartilhamento, revogação do consentimento, oposição e revisão. Quem não tem conta
usa o formulário público (confirmação por código enviado ao e-mail). Quem tem conta usa a
**Central de Privacidade**. Se os dados pertencerem à carteira de um assinante, podemos
encaminhar o pedido a ele, que é quem decide sobre aqueles dados.

## 8. Segurança

Senhas guardadas apenas como hash (bcrypt), conexão cifrada (HTTPS), separação dos dados de
cada conta e limitação de tentativas. Nenhum sistema é imune a falhas; incidentes são
tratados conforme `docs/privacidade/resposta-incidentes.md`.

## 9. Alterações

Mudanças relevantes serão comunicadas antes de entrarem em vigor; a versão e a data constam
no topo deste documento.
