# Ponte Romatec CRM → calculadoras da Receita (CBS/IBS)

O CRM (`Romatec_CRM_WhatsApp`) não alcança a rede privada das calculadoras. Ele chama o **AvalieImob**,
que consulta as calculadoras e devolve o resultado. As calculadoras nunca ficam públicas.

## Autenticação

A mesma do provisionamento que já existe entre os dois sistemas:

- Segredo: `AVALIEIMOB_INTEGRACAO_SECRET` no CRM = `ROMATEC_CRM_INTEGRACAO_SECRET` no AvalieImob.
- Headers: `X-Romatec-Timestamp` (segundos Unix) e `X-Romatec-Signature` = HMAC-SHA256 hex de `"{timestamp}.{corpo}"`,
  sobre o corpo **exato** enviado. Janela de ±300 s. No CRM: `assinarCorpo(ts, txt)` em `server/saas/avalieimob.ts`.
- Todas as rotas são `POST` com corpo JSON (mesmo as de consulta), para a assinatura cobrir tudo.

## Rotas (`https://www.romatecavalieimob.com.br/api/integracoes/romatec/rtc/...`)

| Rota | Corpo | Resposta |
|---|---|---|
| `status` | `{}` | `{ativo, configurado, servicos: {REGULAR, SIMPLES}}` |
| `municipios` | `{"uf": "MA"}` | `{municipios: [{codigo, nome}]}` |
| `classificacoes` | `{"nbs": "9 dígitos", "data": "AAAA-MM-DD"}` | `{descricao, opcoes: [{cst, cClassTrib, descricao}]}` |
| `simular` | ver abaixo | simulação (snapshot sem a resposta bruta) |

### `simular`

```json
{
  "regime": "REGULAR",
  "data_operacao": "2026-06-10",
  "uf": "MA",
  "codigo_municipio": "2100055",
  "itens": [{"valor": "1000.00", "nbs": "114039000", "cst": "200", "cClassTrib": "200052"}],
  "simples": null,
  "origem": {"tipo": "proposta", "id": "123"},
  "solicitado_por": "usuário 7 do CRM"
}
```

- `regime`: `REGULAR` ou `SIMPLES` (no Simples: `simples` = `{crt, cAtivSN, pIBSSN, pCBSSN}`; `cst` dispensado).
- `valor` como **texto** com até 2 casas (nunca float no CRM).
- `data_operacao` é **obrigatória**: o CRM não pode preencher "hoje" sem o usuário confirmar.
- `origem.tipo`: `proposta`, `contrato` ou `venda`. Fica gravado no AvalieImob para auditoria.

Resposta (200): `id`, `situacao` (`calculado` | `calculado_com_erros` | `nao_calculado`), `simulado`, `itens[]`
(por tributo: `aliquota`, `aliquota_efetiva`, `reducao`, `valor`; `memoria`; `erros` traduzidos), `totais`
(`base_calculo`, `cbs`, `ibs`, `is` — **strings** como a calculadora devolve), `aliquotas` (origem de cada uma),
`avisos` (sempre o aviso fixo; o de "alíquota informada manualmente" quando vier da tabela interna),
`versao_calculadora`, `criado_em`.

### Erros

| HTTP | Quando | O que mostrar |
|---|---|---|
| 401 | assinatura errada ou fora da janela | erro de configuração (não mostrar ao usuário final) |
| 404 | simulador desligado no AvalieImob (`RECEITA_RTC_ENABLED`) | esconder o botão |
| 409 | sem alíquota para a data (`detail.mensagem`, `detail.faltantes`) | a mensagem |
| 422 | dado inválido (`detail` texto ou lista de campos) | a mensagem |
| 503 | calculadora fora do ar ou integração sem segredo | "Calculadora da Receita indisponível no momento. Tente novamente." |
