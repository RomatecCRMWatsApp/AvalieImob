# Descoberta — AvalieImob × Calculadoras oficiais da Receita (CBS/IBS/IS/DANFSe)

Fase 0 da especificação "integração das Calculadoras Oficiais da Receita Federal" (21/11/2026).
**Nenhum código de integração foi escrito.** Este documento registra o que existe no repositório
e o que precisa ser decidido antes da Fase 1.

## 1. Stack real

| Camada | O que existe |
|---|---|
| Backend | Python 3.11 + FastAPI (`backend/server.py`, ~73 routers em `backend/routes/`) |
| Banco | MongoDB via Motor (async). Sem ORM; contratos em Pydantic v2 (`backend/models/`) |
| Migrações | Não há ferramenta de migração. Coleções/índices são criados no startup (`server.py`, idempotente). Mudanças são aditivas por natureza (documentos sem schema rígido) |
| Front-end | React 19 (Create React App + craco), Tailwind, shadcn/ui. Chamadas via `frontend/src/lib/api.js` (axios) |
| Autenticação | JWT HS256 (168 h), bcrypt. Perfis: assinante (`get_active_subscriber`) e administrador (`get_admin_user`, papéis admin/owner/ceo) |
| Isolamento | Todo dado de cliente é filtrado por `user_id` do token |
| HTTP de saída | `httpx` + `tenacity` já estão no `requirements.txt` (usados pelos adaptadores de assinatura externa) |
| Testes | `pytest` em `backend/tests/` (dublê de Mongo em `tests/fake_mongo.py`) |
| Logs | `logging` padrão + `services/log_redact.py` (mascara e-mail, CPF, telefone, tokens) |
| Pacotes | `pip` (`backend/requirements.txt`) e `yarn` (front) |

## 2. Implantação

- **Railway**, um único serviço construído pelo `Dockerfile` da raiz (`railway.json`: builder DOCKERFILE).
  O container junta o build do React e o backend Python; não há `docker-compose` em produção.
- **Java 25 e Go não estão no container atual.** Colocar as calculadoras dentro dele está fora de questão
  (a especificação pede serviços separados, e a imagem ficaria enorme).
- **Caminho viável (a confirmar):** criar **3 serviços novos no mesmo projeto Railway**, um por calculadora,
  cada um com seu Dockerfile, **sem domínio público**, falando com o backend pela rede privada do Railway
  (`<servico>.railway.internal`). Isso atende o item 2.3 (nada exposto à internet).
  Alternativa: uma VPS única para as 3 calculadoras, acessada por rede privada/VPN.
- **Não verificado daqui:** os planos/limites do projeto Railway do dono (memória dos serviços Java,
  custo adicional). Ver pergunta P-02.

### Repositórios oficiais conferidos em 21/11/2026 (leitura, sem uso ainda)

| Repositório | Tag mais recente | Commit da tag | Licença | Observação |
|---|---|---|---|---|
| calculadora-rtc-regime-regular | 1.7.2 | `32df719` | MIT (Receita Federal do Brasil, 2026) | `pom.xml` exige `java.version` 25; traz `flyway/` e `docs/exemplos.md` |
| calculadora-rtc-simples-nacional | 1.0.2 | `f90b652` | MIT | sem Dockerfile próprio (como dito na especificação) |
| calculadora-rtc-gerador-danfse | 1.0.0 | `8d79e6b` | MIT | traz `Dockerfile` |

O `docs/exemplos.md` do regime regular confirma: a requisição de cálculo leva, por item, `ncm` **ou** `nbs`,
`cst`, `cClassTrib`, `baseCalculo` **e `aliquotasNominais`** (CBS, IBS estadual e municipal), além de
`dhFatoGerador`, `municipio` (código IBGE) e `uf`. Ou seja, **a alíquota é entrada da chamada**
(obtida pelos endpoints `dados-abertos/aliquota-*`), não algo que a calculadora escolhe sozinha.
O exemplo de serviço (item 3) usa `nbs` + `cst 200` + `cClassTrib 200028` e devolve `gIBSCBS` com
`vBC`, `gIBSUF`, `gIBSMun`, `gCBS` e redução de alíquota.

## 3. Onde estão hoje as entidades da especificação

| Conceito da especificação | No AvalieImob | Valor monetário |
|---|---|---|
| Laudo / avaliação | `ptam_documents` (PTAM), `garantias` (avaliação de garantias), `modelos_inferencia` | `ptam.honorarios` (`float`, opcional) e `garantias.honorarios` |
| Honorário (recebido) | `recibos` (`models/recibo.py`, tipo `honorarios`, `valor: float`), vinculado ao PTAM por `ptam_id` | `recibos.valor` |
| Proposta / serviço | `propostas` (`models/proposta.py`, motor `services/pricing/`), total em `custos_calculados.secao_5_total` | float |
| Cliente | `clients` (por `user_id`) | — |
| NFS-e | Módulo **administrativo** (só do dono): `nfse_config`, `nfse_documentos`, `services/nfse/` (ABRASF/SpeedGov, Sefin Nacional — transmissão travada) | — |
| DANFSe | **Já existe um gerador próprio** (`pdf/templates/danfse_*`, temas Prime I/II/Tradicional) e importação do PDF de uma nota emitida (`services/nfse/danfse_import.py`) | — |

Consequências para o desenho:

1. **Dois públicos diferentes.** O módulo NFS-e é do dono (Romatec). Já os honorários de PTAM/recibos são de
   **cada assinante**, e cada assinante pode ter regime tributário diferente (corretor autônomo PF, MEI,
   Simples, Lucro Presumido). O regime e os códigos (NBS, CST, cClassTrib) precisam ser **configuração por conta**.
2. **O DANFSe da Receita seria um 3º caminho de PDF.** Hoje o sistema já gera um DANFSe temático a partir dos
   dados da nota. O gerador oficial (Go) recebe o **XML** da NFS-e. Proposta: oferecer o oficial apenas quando
   houver XML anexado, sem substituir o temático (decisão P-05).
3. **Grupo IBSCBS hoje é omitido** no XML da DPS do adaptador Sefin (`services/nfse/sefin/dps_xml.py`, comentário
   na linha 153). A calculadora oficial gera e valida esse grupo (`/xml/generate`, `/xml/validate`); pode ser
   aproveitada lá no futuro, mas isso é emissão e está **fora de escopo** desta entrega.

## 4. Convenções que a implementação deve seguir

- Rotas em `backend/routes/<nome>.py`, prefixo `/api`, **sem** `from __future__ import annotations` nos arquivos
  de rota (quebra o rate limiter; ver nota em `routes/avaliacao_publica.py`).
- Serviços puros e testáveis em `backend/services/<nome>/`; testes em `backend/tests/test_<nome>.py`.
- Gravações sempre filtrando `{"id": ..., "user_id": uid}`; numeração via `counters` com `$inc`.
- Feature flag por variável de ambiente (padrão já usado: `ASSINATURA_POLLING_ENABLED`, `TRIAL_CADASTRO_DIAS`).
- **Dinheiro:** o sistema usa `float` na maior parte; o módulo INSS de Obra usa `Decimal`. O módulo novo deve usar
  `Decimal` e guardar os valores da calculadora **como strings**, exatamente como vêm (`"42.24"`).
- Toda entrega para a `main` segue o ritual do `CLAUDE.md` (build-number, `releases.json`, CACHEBUST).
- Textos para o usuário em PT-BR; ícones lucide com import nomeado (regra do iOS).

## 5. Regime tributário

- **Romatec (dono):** a NFS-e real nº 59 traz `OptanteSimplesNacional=2` → **não é optante do Simples**.
  Se é Lucro Presumido ou Real **não está no sistema** (P-03).
- **Assinantes:** não há campo de regime tributário no perfil. Precisa ser criado (configurável por conta),
  com valor inicial "não informado".
- Defaults fiscais hoje gravados (só no módulo NFS-e do dono): `codigo_nbs = 114039000` (marcado no código como
  "CONFIRMAR por serviço") e Código de Tributação Nacional `170101`. **Não reutilizar como verdade**: entra em
  `PENDENCIAS.md`.

## 6. Proposta de encaixe (para validar antes da Fase 1)

- Módulo `backend/services/receita_rtc/` (client, dto, mapper, service, config) + `backend/routes/receita_rtc.py`.
- Coleção `simulacao_tributaria` (uma por simulação, imutável): `origem_tipo` (`ptam`, `recibo`, `proposta`,
  `garantia`), `origem_id`, `user_id`, `regime`, `data_operacao`, `entrada`, `resultado` (bruto), totais em string,
  `versao_calculadora`, `criado_em`. Coleção `anexo_danfse` só com a flag do DANFSe.
- Botão "Simular CBS/IBS" no **recibo de honorários** e no **passo Resultado do PTAM**; painel no card da
  proposta. Tudo atrás de `RECEITA_RTC_ENABLED=false`.
- Aviso fixo: "Estimativa baseada nas calculadoras oficiais da Receita Federal. Não substitui o sistema emissor
  nem a validação do contador."

## 7. Perguntas abertas

Ver `PENDENCIAS.md` (P-01 a P-08).
