# Roteiro de resposta a incidentes — AvalieImob

Rascunho operacional. Responsável e substituto **a definir pelo dono** (P-02). Nenhuma
comunicação à ANPD ou a titulares é disparada automaticamente.

1. **Identificar** — quem viu, quando, o quê (vazamento, acesso indevido, perda, link
   público exposto, credencial publicada). Abrir registro com data/hora UTC.
2. **Conter** — conforme o caso: desativar o link público afetado (botão de desativar link
   já existe nos módulos), revogar sessão/trocar senha da conta, girar a chave exposta
   (ver `implantacao-e-rollback.md`), bloquear o IP/rota, tirar a página do ar.
3. **Preservar evidência** — exportar logs do período (já mascarados), registros do Mongo
   envolvidos e versão do código (commit). Acesso restrito; não copiar documentos pessoais
   para o relatório.
4. **Avaliar o risco** — quais dados, quantos titulares, sensibilidade, se havia
   criptografia, probabilidade de dano. Usar os critérios do Regulamento de Comunicação de
   Incidente da ANPD (Resolução CD/ANPD nº 15/2024 — conferir versão vigente).
5. **Decidir a comunicação** — o responsável decide, com o jurídico, se comunica ANPD e
   titulares e em que prazo (a regulamentação vigente fixa prazo em dias úteis a partir do
   conhecimento — confirmar). Modelo de mensagem a preparar com o jurídico.
6. **Recuperar** — corrigir a causa, restaurar o serviço, reaplicar exclusões se houve restore.
7. **Lições** — registro do que aconteceu, causa, correção e o que muda.

Contatos (preencher): responsável · substituto · jurídico · Railway · Cloudflare · Mercado Pago.
