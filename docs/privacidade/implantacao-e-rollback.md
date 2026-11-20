# Implantação e rollback — branch `seguranca/privacidade-lgpd`

> Nada foi publicado. `main` faz deploy automático no Railway: **merge só com aprovação**.

## O que muda ao fazer merge (mesmo com todas as flags desligadas)

| Mudança | Efeito visível | Risco |
|---|---|---|
| Perfil público do laudo (allowlist) | portal do laudo continua mostrando foto/nome/registros | baixo — se algum campo público faltar, acrescentar em `services/perfil_publico.py` |
| CPF mascarado na verificação pública | página `/v/laudo/v/...` mostra `***.456.789-**` | baixo |
| Filtro de logs | logs com telefone/e-mail/token mascarados | médio para investigação (menos detalhe nos logs) |
| GA4/Clarity condicionados | **banner de cookies aparece** se os IDs estiverem configurados; estatísticas só de quem aceitar | queda esperada nos números do Analytics/Clarity |
| `/privacidade`, `/termos`, `/privacidade/solicitacao` | páginas existem (antes 404) mostrando "em revisão"; links no rodapé | baixo |
| `conta_encerrada` bloqueia acesso | só afeta contas anonimizadas pelo novo fluxo | baixo |
| `routes/seed.py` | rota não registrada — sem efeito | nenhum |

## Ao fazer merge na `main` (regras do CLAUDE.md)

- Incrementar `frontend/build-number.txt` e adicionar a entrada no topo de
  `backend/data/releases.json` (itens do canal/central com `publico` conforme decisão;
  correções internas com `publico: "interno"`). **Não feito nesta branch** de propósito.
- Bump de `CACHEBUST`/`CACHEBUST_BACKEND` no Dockerfile (backend + frontend mudaram).

## Ativação gradual (homologação primeiro)

1. Homologação com dados sintéticos: `PRIVACIDADE_RECURSOS_ATIVOS=1` (backend) e
   `REACT_APP_PRIVACIDADE_RECURSOS_ATIVOS=1` (build do frontend); testar canal do titular
   com e-mail de teste (SMTP/SendGrid de homologação), Central, exportação.
2. Configurar `PRIVACIDADE_CONTROLADOR_*`, `PRIVACIDADE_EMAIL`, `PRIVACIDADE_PRAZO_DIAS`.
3. Após aprovação jurídica do texto: copiar a versão final para `backend/data/privacidade/`
   (ou `PRIVACIDADE_DOCS_DIR`) — **a pasta `docs/` não vai para a imagem Docker do backend
   se o contexto não incluir `docs/`; conferir** — e ligar `PRIVACIDADE_MINUTAS_ATIVAS=1`.
   Cada mudança de texto gera hash novo → usuários passam a "aceite pendente" (sem bloqueio).
4. `PRIVACIDADE_EXCLUSAO_EXECUCAO_ATIVA=1` só durante o atendimento de um pedido aprovado;
   sempre rodar antes o plano (dry-run) e guardar o relatório.

## Índices sugeridos (aditivos, não criados automaticamente)

`privacidade_pedidos`: `protocolo` (único), `status`, `user_id`; `privacidade_aceites`:
`(user_id, tipo)`; `privacidade_consentimentos`: `(user_id, finalidade, em)`;
`privacidade_exportacoes`: `token_hash` (único), TTL em `expira_em` (ex. 1 dia).

## Rollback

- Desligar as flags (efeito imediato nas rotas novas: 404/409).
- Reverter os commits da branch (`git revert`), sem perda de dados: as coleções novas
  `privacidade_*` ficam órfãs e podem ser mantidas (prova de atendimento) ou removidas
  por decisão do responsável.
- Banner de cookies: reverter o commit `feat(privacidade): GA4 e Clarity só carregam após
  consentimento` volta ao carregamento anterior (não recomendado — reabre o achado A2).

## Comandos de verificação

```bash
cd backend && python -m pytest -q tests/test_privacidade.py tests/test_seo_html.py
cd backend && python -m pytest -q            # suíte completa (2 falhas pré-existentes)
cd frontend && CI=true yarn test --watchAll=false
cd frontend && yarn build
```
