# Pendências jurídicas e de negócio — AvalieImob

Separação usada: **[LEI]** obrigação legal identificada · **[TÉC]** recomendação técnica ·
**[DECISÃO]** decisão de negócio/jurídica do responsável.

## Dados empresariais que faltam (não inventados)

Configurar no ambiente (aparecem como "pendente" até lá): `PRIVACIDADE_CONTROLADOR_NOME`,
`PRIVACIDADE_CONTROLADOR_DOCUMENTO` (CPF/CNPJ), `PRIVACIDADE_CONTROLADOR_ENDERECO`,
`PRIVACIDADE_EMAIL`, `PRIVACIDADE_ENCARREGADO`. Também preencher os **[PENDENTE]** das
minutas em `docs/privacidade/minutas/`.

## Decisões

1. **[DECISÃO][LEI — CDC art. 37 / LGPD art. 6º VI]** Selo "Certificado LGPD" e frases
   "ISO 27001", "AES-256 em repouso", "exclusão em até 15 dias", "em conformidade com a
   LGPD" (`LgpdBadge.jsx`, `LgpdSection.jsx`). Não há certificação LGPD oficial e as
   demais afirmações não foram comprovadas. **Proposta de texto** (não aplicada):
   selo → "Privacidade e LGPD" (sem "Certificado"); pilares → "Senhas com hash bcrypt",
   "Conexão cifrada (HTTPS)", "Dados de cada conta separados", "Pedidos sobre seus dados
   pelo canal de privacidade — prazo informado no protocolo".
2. **[DECISÃO]** Papéis: confirmar que o assinante é controlador da carteira e o AvalieImob
   operador; incluir cláusulas de tratamento (operador) nos Termos.
3. **[DECISÃO]** Encarregado (DPO): nomear ou avaliar dispensa (Resolução CD/ANPD nº 2/2022
   para agentes de pequeno porte — conferir se aplicável); manter canal funcional de todo modo.
4. **[DECISÃO]** Prazos de retenção da tabela em `retencao-e-direitos.md` (fiscal,
   prescricional, leads, robô, logs, backups).
5. **[LEI — CDC art. 49; Decreto 7.962/2013]** Arrependimento em 7 dias na contratação
   online: regra de devolução, marco inicial (pagamento × início do acesso, considerando o
   teste gratuito) e forma de estorno. O sistema só **registra o pedido**; estorno é manual.
   Identificação do fornecedor (nome, CNPJ, endereço) visível na página de planos/checkout
   — **pendente dados**.
6. **[DECISÃO]** Exportação da carteira (clientes/laudos) pelo assinante: hoje só contagem.
7. **[DECISÃO]** Envio de dados de cadastro/assinatura ao CRM Romatec/ZAYRA: finalidade,
   base legal e menção no aviso (achado A12).
8. **[DECISÃO]** Exclusão de tenant (empresa inteira): prazo, devolução da carteira,
   arquivos no R2 — não implementada.
9. **[DECISÃO][LEI — consentimento específico]** Texto do checkbox da calculadora
   ("Autorizo o contato e o tratamento dos meus dados conforme a Política de Privacidade")
   referencia política ainda não publicada; sugerido revisar redação quando o aviso for aprovado.
10. **[TÉC]** Clarity: ativar mascaramento de campos/textos no painel do Clarity antes de
    voltar a usá-lo; avaliar se a gravação de sessão é necessária.
11. **[DECISÃO]** Usuários antigos: aceite dos novos Termos fica "pendente" (não bloqueia).
    Definir se e quando o aceite passará a ser exigido e como comunicar a mudança.
12. **[DECISÃO]** Mudança de "E-mail já cadastrado" no cadastro (enumeração) — impacto de UX.
