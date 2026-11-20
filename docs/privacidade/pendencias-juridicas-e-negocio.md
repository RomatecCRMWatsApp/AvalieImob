# Pendências jurídicas e de negócio — AvalieImob

Nada abaixo foi decidido pelo código. Cada item precisa do dono e/ou do jurídico.

| ID | Pendência | Quem decide | Bloqueia |
|---|---|---|---|
| P-01 | Revisar e aprovar a **minuta do Aviso de Privacidade** (`minutas/aviso-de-privacidade.md`). Após aprovar: `aviso_completo_aprovado: true` + versão em `frontend/src/data/privacidade.json` e publicar o texto na página | Jurídico + dono | Aviso completo no site |
| P-02 | **Encarregado (DPO)**: designar ou avaliar dispensa (Resolução CD/ANPD nº 2/2022 para agentes de pequeno porte — confirmar enquadramento). Hoje o canal é `contato@romatecavalieimob.com.br` | Dono + jurídico | Identificação no aviso |
| P-03 | **Termos de Uso**: não existem. Minuta em `minutas/termos-de-uso.md`. Depois de aprovados, implementar aceite com versão e data/hora no servidor (desenho pronto em `implantacao-e-rollback.md`). Usuários antigos ficam com aceite pendente — não presumir aceite | Jurídico + dono | Aceite no cadastro |
| P-04 | **Prazos de retenção** por categoria (`retencao-e-direitos.md`) e prazos de resposta a titulares | Jurídico + contador | Script de eliminação |
| P-05 | **Compartilhamento com a ZAYRA** (leads de cadastro/assinatura): base legal, menção no aviso, e se o CRM é o mesmo controlador | Jurídico + dono | Aviso; CRM |
| P-06 | **CDC**: se o público inclui consumidor (corretor pessoa física pode ser), preparar arrependimento de 7 dias (art. 49), identificação do fornecedor na contratação (Decreto 7.962/2013), resumo contratual e confirmação. Não presumir que CNPJ exclui o CDC | Jurídico + dono | Fluxo de pagamento |
| P-07 | **Papel de operador**: contrato/termo com os assinantes sobre os dados de clientes deles (instruções, suboperadores, incidentes) | Jurídico | Termos de Uso |
| P-08 | **Legítimo interesse** na prospecção B2B e no rastreio de origem do cadastro: teste de balanceamento (LIA) | Jurídico | Prospecção |
| P-09 | Frases de produto sem comprovação nas páginas de serviço (relatado em 19/11) | Dono | — |
| P-10 | Autorização para **varrer o histórico do git** atrás de credenciais e, se achar algo, plano de rotação | Dono | A-12 |

## Dados empresariais usados (já publicados pelo dono no site)

Razão social J R P Bezerra LTDA (RomaTec Consultoria Total), CNPJ 17.261.987/0001-09,
Rua São Raimundo, nº 10, Centro, Açailândia/MA, CEP 65930-000, contato@romatecavalieimob.com.br.
**Confirmar se continuam corretos** antes de publicar o aviso. Nenhum dado foi inventado.
