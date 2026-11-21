# Calculadoras oficiais da Receita (CBS/IBS) — operação

Origem: **Receita Federal do Brasil**, Portaria Cotec nº 342/2026, código aberto sob licença MIT
(`LICENSE.regime-regular`, `LICENSE.simples-nacional`). A lógica tributária é a oficial, sem alteração:
o `Dockerfile.java` clona a tag fixada em `VERSOES.env` e confere o commit.

| Serviço | Versão | Porta | Base |
|---|---|---|---|
| `rtc-regime-regular` | 1.7.2 (`32df719`) | 8080 | `/api` |
| `rtc-simples-nacional` | 1.0.2 (`f90b652`) | 8082 | `/api` |
| DANFSe (Go) | 1.0.0 | — | última fase, ainda não sobe |

## Consumo medido (21/11/2026, Java 25, perfil offline)

Medido com `docker stats`, o exemplo oficial de cálculo (`fixtures/regime-regular-operacao-exemplo.json`) no regime
regular e consulta de atividades no Simples, 1.500 pedidos com 16 em paralelo em cada serviço. Nenhum erro, nenhum
encerramento por falta de memória.

| Serviço | Subida | RAM parado | RAM com carga | Limite recomendado |
|---|---|---|---|---|
| Regime regular | ~15 s | 411–415 MB | ~479 MB | **768 MB** (a 512 MB ficou em 94% do limite) |
| Simples Nacional | ~13 s | 371–378 MB | ~395 MB | **512 MB** (77% do limite) |

Tempo de resposta depois de aquecido: ~15 ms por cálculo; CPU parada em ~0,2%.

### Custo estimado no Railway

Cobrança pelo **uso real**, não pelo limite. Preços de referência: ~US$ 10 por GB de RAM/mês e ~US$ 20 por vCPU/mês
(conferir em railway.com/pricing — não foi possível abrir a página a partir desta sessão).

| Item | Uso | Custo/mês |
|---|---|---|
| RAM | ~0,79 GB parado, ~0,87 GB com uso | ~US$ 8 a 9 |
| CPU | ~0,002 vCPU por serviço parado | < US$ 1 |
| Rede privada | — | sem cobrança |
| **Total** | | **~US$ 9 a 10** |

**App Sleeping fica desligado** (decisão do dono): a subida leva 13–15 s e a primeira simulação esperaria por isso.
Antes de criar os serviços, configurar um **alerta/limite de gasto** no Railway (`docs/receita-rtc/PENDENCIAS.md`, P-04 e seção 4.5).

## Railway (produção)

Para cada serviço, no **mesmo projeto** do AvalieImob:

1. Novo serviço a partir deste repositório, Dockerfile `infra/calculadoras-rtc/Dockerfile.java`,
   contexto `infra/calculadoras-rtc`.
2. Build args: `SERVICE` (`regime-regular` ou `simples-nacional`) e as 4 variáveis de `VERSOES.env`.
3. Variável `SERVER_PORT` (8080 ou 8082).
4. **Sem domínio público** (não gerar domínio em Settings ▸ Networking). O backend acessa por
   `http://<nome-do-servico>.railway.internal:<porta>/api`.
5. Limite de memória: 768 MB (regime regular) e 512 MB (Simples Nacional). App Sleeping desligado.

Os builds `CA extra` e `JAVA_TOOL_OPTIONS` do Dockerfile são opcionais e ficam vazios no Railway; existem só para
compilar atrás de um proxy com certificado próprio.

## Local

```bash
cd infra/calculadoras-rtc
./atualizar-calculadoras.sh                       # constrói as imagens nas versões fixadas
docker compose --env-file VERSOES.env up -d       # rede "rtc" interna, sem porta publicada
RR_URL=... SN_URL=... ./smoke-test.sh             # rodar de dentro da rede
```

## Atualizar a versão

1. Conferir as tags novas: `git ls-remote --tags https://github.com/ReceitaFederal/<repo>.git`.
2. Trocar **tag e commit** juntos em `VERSOES.env` (nunca `main`).
3. `./atualizar-calculadoras.sh` e `./smoke-test.sh`; ler o `CHANGELOG.md` oficial da versão.
4. Simulações já gravadas não são recalculadas: cada uma guarda a versão usada.

## Banco e logs

- O banco SQLite oficial é gerado no build (flyway do regime regular, ~5,6 MB) e embutido **somente leitura** nas
  duas imagens; não há dado nosso nele e não precisa de backup (é recriado a cada build).
- Logs: saída padrão do container (painel do Railway). As calculadoras não recebem dado pessoal nosso.
- No perfil offline, `GET /versao/status` consulta a versão publicada em `piloto-cbs.tributos.gov.br` (só nessa rota,
  sob demanda). Sem saída para a internet, essa rota responde erro; o cálculo não depende dela.
