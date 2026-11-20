# Implantação e rollback — AvalieImob

Tudo desta entrega está na branch **`feat/privacidade-lgpd`**, sem push e sem merge.
Publicar exige a autorização do dono.

## O que esta branch muda em produção quando publicada

| Mudança | Efeito visível | Risco | Rollback |
|---|---|---|---|
| Página `/privacidade` + formulário do titular | Nova página; o 404 some | Baixo | Reverter commit |
| Rotas `/api/privacidade/*` e `/api/admin/privacidade/*` + coleção `privacidade_solicitacoes` (só índices novos, aditivo) | Novas rotas | Baixo — nada apagado; rate-limit 5/min no público | Reverter commit; a coleção pode ficar (inofensiva) |
| GA4/Clarity só após consentimento | Banner aparece **apenas se** `REACT_APP_GA_MEASUREMENT_ID` ou `REACT_APP_CLARITY_PROJECT_ID` estiverem no Railway; a contagem do GA vai cair (só quem aceitar) | Médio para métricas, nulo para o produto | Reverter `index.html` e `App.js` |
| Textos LGPD (selo, seção da home, cadastro, calculadoras, About, mock) | Sem "Certificado", sem ISO/AES | Baixo | Reverter commit |
| Mascaramento nos logs | Logs com `***1246`, `j***@dominio`, `[token]` | Baixo — dificulta um pouco o suporte | Remover `_log_redact.instalar()` do `server.py` |
| Rodapé "Fale com um Especialista" abre o WhatsApp | Antes fingia enviar | Baixo | Reverter `Footer.jsx` |

Antes do merge na `main`: seguir o ritual do CLAUDE.md (build-number, `releases.json` com
`publico: "interno"` exceto a área de Privacidade em Configurações, que é ferramenta do
usuário, `CACHEBUST` e `CACHEBUST_BACKEND`). Não foi feito na branch para não conflitar
com o bot de build da `main`.

## Itens preparados, NÃO executados (precisam de aprovação específica)

1. **URL assinada para `/upload/image/{id}` (A-07).** Plano: gerar `?exp=&sig=` (HMAC com
   segredo do servidor) ao devolver a URL; aceitar sem assinatura por um período de
   transição registrando o uso; depois exigir. Testar laudo público, portal do cliente,
   PDFs e o app. Rollback: voltar a aceitar sem assinatura (flag).
2. **Aceite de Termos versionado (P-03).** Desenho: `TERMOS_VERSAO` (vazio = desligado);
   com versão definida, o cadastro mostra checkbox desmarcado com link e o backend grava
   `aceite_termos: {versao, sha256_do_texto, em (servidor)}`; usuários antigos recebem
   pedido de aceite no próximo login sem bloquear o acesso a documentos já emitidos.
3. **Script de eliminação/anonimização** com simulação e relatório (ver
   `retencao-e-direitos.md`). Só com dados sintéticos até aprovação.
4. **Varredura do histórico do git e rotação de credenciais (A-12).** Se aparecer chave:
   gerar nova no fornecedor → trocar no Railway → reimplantar → revogar a antiga →
   conferir logs de uso. Apagar do arquivo não resolve vazamento histórico.
5. **TTL para logins em `user_access_log`** depois de definida a retenção (P-04).

## Testes executados nesta branch

- `python3 -m pytest -q tests/test_log_redact.py tests/test_privacidade.py` → 9 passaram.
- Suíte completa do backend: ver `checklist-validacao.md`.
- `CI=false yarn build` → compilou; nenhum aviso nos arquivos novos.
- Playwright (rede interceptada): ver `checklist-validacao.md`.
