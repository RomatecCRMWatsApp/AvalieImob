# Checklist de aceite — AvalieImob

Status: **implementado e testado** · **implementado sem teste** · **pendente** · **bloqueado** · **não aplicável**.
Branch `seguranca/privacidade-lgpd`. Testes: `backend/tests/test_privacidade.py` (27),
`frontend/src/__tests__/consentimentoCookies.test.js` (7).

| Item | Status | Evidência / pendência |
|---|---|---|
| Projeto correto, ambientes e modelo de negócio identificados | implementado sem teste | `inventario-dados.md` §1. Ambiente de produção/Railway não acessado |
| Inventário, finalidades, bases legais candidatas e responsáveis | implementado sem teste | `inventario-dados.md` (bases "a validar"; responsáveis pendentes) |
| Dados públicos/privados/próprios/de terceiros separados | implementado e testado | allowlist `services/perfil_publico.py` + `test_rota_publica_do_laudo_nao_vaza_assinatura_nem_cpf`; `inventario-dados.md` §4 |
| Termos/aviso e identificação real preparados; publicação condicionada | implementado e testado | minutas em `minutas/`; `PRIVACIDADE_MINUTAS_ATIVAS`; `test_aceite_indisponivel_sem_minutas`, `test_documentos_minuta_versionados`. Identificação: **pendente dados** |
| Aceite versionado e consentimentos opcionais independentes | implementado e testado | `services/privacidade/aceites.py`; `test_aceite_pendente_e_registro_com_versao_hash`, `test_consentimento_marketing_padrao_off_revogavel_com_historico`. UI de aceite no cadastro: **pendente decisão** |
| Cookies/pixels/SDKs opcionais controlados, rejeição e revogação | implementado e testado | `public/rastreio-consentido.js`, `CookieConsent.jsx`; 7 testes Jest (DOM jsdom). Verificação em navegador real com IDs reais: **pendente homologação**. Google Fonts: pendente |
| Canal de titulares sem conta, verificação proporcional | implementado e testado | `routes/privacidade.py` `/titular/*`; testes de fluxo, tentativas, expiração, anti-enumeração, honeypot, rate limit, admin com trilha |
| Exportação com escopo, proteção do arquivo e link temporário | implementado e testado | `services/privacidade/exportacao.py`; `test_exportacao_escopo_do_proprio_usuario`, `test_exportacao_de_outro_usuario_e_expirada`, `test_csv_neutraliza_formulas` |
| Exclusão de conta, contato, titular e tenant separadas | implementado e testado (conta, titular); implementado sem teste (relatório de contato); **pendente** (tenant) | `services/privacidade/exclusao.py`; `test_plano_de_exclusao_e_dry_run`, `test_execucao_exige_flag_e_confirmacao`, `test_localizar_titular_por_conta_sem_devolver_dados` |
| Retenção, descarte, backups e reaplicação documentados/testados | implementado e testado (reaplicação); pendente (prazos, rotinas, backup) | `retencao-e-direitos.md`; `test_reaplicacao_apos_restore` |
| Autorização no servidor e testes de acesso cruzado | implementado e testado (módulo novo); verificado por leitura (demais) | varredura em `auditoria-e-plano.md` §1; testes de 2 usuários na exportação e localização |
| Contas admin, sessões, recuperação, autenticação | pendente (parcial) | conta encerrada perde acesso (`test_conta_encerrada_perde_acesso_mesmo_com_jwt`); MFA admin, revogação de JWT, rate limit por IP real: pendentes (A9–A11) |
| Banco, arquivos e uploads protegidos | implementado e testado (uploads); pendente (A8 imagens sem expiração) | `test_upload_recusa_conteudo_falso` |
| Secrets e logs revisados; plano de rotação | implementado e testado (logs); implementado sem teste (seed) | `services/log_redaction.py` + `test_redacao_de_logs`, `test_filtro_aplicado_ao_registro`; rotação em `auditoria-e-plano.md` §4 |
| Fornecedores e IA avaliados | implementado sem teste (documental) | `fornecedores-e-ia.md`; minimização de prompts pendente |
| Roteiro de incidentes | implementado sem teste | `resposta-incidentes.md`; responsáveis pendentes |
| Cobrança, cancelamento, arrependimento, webhooks | implementado e testado (informação + pedido idempotente, sem efeito financeiro); webhooks: testes existentes | `test_assinatura_informa_e_arrependimento_idempotente`; `tests/test_pagamento_seguranca.py`. Regra de devolução: pendente jurídico |
| Lint, typecheck, testes e build com resultados reais | implementado | ver `implantacao-e-rollback.md`; resultados no relatório da entrega |
| Documentação, pendências e plano de implantação/rollback | implementado | esta pasta |
| Relatório independente; produção não alterada | implementado | nenhum deploy, nenhuma operação em dados reais |
