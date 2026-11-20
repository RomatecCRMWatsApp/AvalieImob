# Checklist de aceite — AvalieImob

Branch `feat/privacidade-lgpd`, 20/11/2026. Estados: **implementado e testado** ·
**implementado sem teste** · **pendente** · **bloqueado** · **não aplicável**.

| # | Item | Estado | Evidência / pendência |
|---|---|---|---|
| 1 | Projeto, ambientes e modelo de negócio identificados | implementado e testado | SaaS B2B/B2C para avaliadores e corretores (React + FastAPI + MongoDB no Railway, R2, Mercado Pago avulso). Só produção existe; sem ambiente de homologação separado — por isso tudo fica na branch |
| 2 | Inventário, finalidades, bases candidatas, responsáveis | implementado sem teste | `inventario-dados.md` (bases "a validar") |
| 3 | Dados públicos, privados, próprios e de terceiros separados | implementado sem teste | `inventario-dados.md` — papéis controlador × operador |
| 4 | Termos/aviso e identificação real; publicação condicionada | implementado sem teste | Minutas em `minutas/`; página mostra só fatos + canal; `aviso_completo_aprovado:false`. Pendente P-01, P-02 |
| 5 | Aceite versionado e consentimentos opcionais separados | pendente | Termos não existem (P-03). Consentimento da calculadora já separado e desmarcado; cookies separados do cadastro |
| 6 | Cookies/pixels controlados, verificados em rede; rejeição e revogação | implementado e testado | Playwright: 0 requisições a googletagmanager/clarity antes da escolha e após "Rejeitar" + navegação; ambas após "Aceitar"; revogar apaga a escolha e reabre o banner; sem IDs configurados não há banner |
| 7 | Canal de titulares sem conta, verificação proporcional | implementado e testado | `tests/test_privacidade.py::test_pedido_publico_sem_conta...`, honeypot, rate-limit 5/min; Playwright: formulário a 390 px devolve protocolo |
| 8 | Exportação escopada, protegida, sem link persistente | implementado e testado | `test_exportacao_so_traz_dados_da_propria_conta_e_sem_segredos` (2 contas; senha, token, certificado, credencial e binário fora) |
| 9 | Exclusão de conta, contato, titular e tenant separadas | implementado e testado | `test_encerrar_conta_abre_pedido_sem_apagar_carteira`; `retencao-e-direitos.md` |
| 10 | Retenção, descarte, backups, reaplicação | pendente | Proposta em `retencao-e-direitos.md`; P-04; script só após aprovação |
| 11 | Autorização no servidor e acesso cruzado | implementado e testado | Rotas novas: `user_id` sempre do token; admin exige `get_admin_user` (`test_admin_exige_perfil_admin`). Demais módulos: auditoria v1.4.1265 + testes de isolamento existentes |
| 12 | Contas administrativas, sessões, recuperação | pendente | Já existe: bloqueio por conta, reset com token único, role não escolhível. Falta MFA para admin e revogação de sessões (JWT de 168 h sem lista de revogação) |
| 13 | Banco, arquivos e uploads protegidos | pendente | Upload validado por tipo real. **A-07**: imagens servidas sem login por UUID |
| 14 | Secrets e logs revisados; plano de rotação | implementado e testado (logs) · bloqueado (histórico) | `tests/test_log_redact.py` (3). Histórico do git aguardando P-10 |
| 15 | Fornecedores e IA avaliados | pendente | `fornecedores-e-ia.md`; contratos/retenção não verificados |
| 16 | Roteiro de incidentes | implementado sem teste | `resposta-incidentes.md`; responsável a definir |
| 17 | Cobrança, cancelamento, arrependimento, webhooks | pendente | Sem renovação automática (nenhuma cobrança futura a cancelar). Webhook MP com HMAC/dedupe já testado (v1.4.1309). Arrependimento CDC: P-06 |
| 18 | Lint, typecheck, testes e build | implementado e testado | Backend: 807 passaram, 1 falha antiga (`test_texto_ia`, não relacionada). Frontend: build compilado; sem typecheck (projeto em JS) |
| 19 | Documentação e plano de implantação/rollback | implementado sem teste | `docs/privacidade/*` |
| 20 | Relatório independente por aplicativo; produção intacta | implementado e testado | Nada publicado. CRM da Romatec **não revisado** nesta sessão |

Comandos usados:

```
cd backend && python3 -m pytest -q tests/test_log_redact.py tests/test_privacidade.py
cd backend && python3 -m pytest -q -p no:cacheprovider
cd frontend && CI=false yarn build
node v.js   # Playwright com rede interceptada (script na pasta temporária da sessão)
```
