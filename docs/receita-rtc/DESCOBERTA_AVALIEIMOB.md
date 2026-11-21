# Fase 0 — Descoberta: AvalieImob × Calculadoras da Receita (CBS/IBS/IS/DANFSe)

Data: 21/11/2026. Especificação de origem: "Especificação para o Coddy: integração das Calculadoras Oficiais da
Receita Federal" (enviada pelo solicitante). Esta fase **não altera código**: só levanta fatos, riscos e perguntas.

> Aviso que valerá para as telas: a simulação é uma conferência baseada nas calculadoras oficiais e não substitui
> o sistema emissor nem a validação do contador. A classificação (CST, cClassTrib, NBS) é de quem emite.

## 1. Stack real

| Item | AvalieImob |
|---|---|
| Linguagem | Python 3 (back-end) + JavaScript (front-end) |
| Back-end | FastAPI 0.110 (`backend/routes/*.py`, prefixo `/api`), modelos Pydantic v2 (`backend/models/`) |
| Front-end | React 19 (Create React App/craco), Tailwind + shadcn/ui (`frontend/src`) |
| Banco | **MongoDB** (Motor, assíncrono); isolamento obrigatório por `user_id`; numeração via coleção `counters` |
| Migrações | Sem ORM: coleções e índices criados no startup (`server.py`), de forma idempotente |
| Autenticação | JWT HS256 (168 h), bcrypt; papéis `admin/owner/ceo` e assinante (`plan_status`) |
| Testes | pytest (`backend/tests`, ≈700 testes) + build do CRA |
| Pacotes | pip (`backend/requirements.txt`) e yarn |
| Release | `frontend/build-number.txt` + `backend/data/releases.json` (aviso ao assinante); push na `main` = deploy |
| Arquivos | Cloudflare R2 (`services/r2_storage`) para PDFs e anexos |

## 2. Onde estão as entidades de negócio

| Conceito da especificação | No AvalieImob |
|---|---|
| Cliente | coleção `clients` (por usuário) |
| Laudo / avaliação | `ptam_documents` (PTAM), `garantias`, laudos de georreferenciamento/topografia |
| Honorário | `recibos` (recibo de honorários, inclusive gerado a partir do PTAM) e `propostas` (propostas de consultoria com motor de preço em `services/pricing/`) |
| NFS-e | Módulo **já existente**: `routes/nfse.py` + `services/nfse/` — emissão ABRASF (SpeedGov, Açailândia) e adaptador Sefin Nacional, ainda com **transmissão travada** por segurança |
| DANFSe | **Gerador próprio já existente** com 3 temas (`pdf/templates/danfse_*.py`) e importação de NFS-e já emitida em PDF (`services/nfse/danfse_import.py`) |

Consequência para a Fase 4: o DANFSe oficial da Receita entra como **opção** (layout oficial a partir do XML),
ao lado do gerador temático que já existe — não substitui nada.

## 3. Implantação

- Railway, build por `Dockerfile` (front-end CRA + back-end Python no mesmo container), MongoDB externo.
- **Não há bloqueio**: as calculadoras podem ser serviços separados no Railway (Java 25 e Go em Docker), acessados
  pela **rede privada** do projeto (`*.railway.internal`), sem domínio público. A rede privada é por projeto: se o
  CRM estiver em outro projeto, decidir onde as calculadoras ficam (pergunta 2).
- O back-end Python chamaria as calculadoras com `httpx` (já usado no projeto), com timeout, retry e circuit breaker.

## 4. Regime tributário e códigos

- A Romatec **não é optante do Simples Nacional** (NFS-e real nº 59: `OptanteSimplesNacional = 2`; ISS 2% em
  Açailândia/MA; item 17.01; CNAE 8211300).
- O AvalieImob é **SaaS usado por vários avaliadores** (pessoas físicas e empresas). O regime (regular × Simples)
  precisa ser **configurável por usuário**, no Perfil do Avaliador.
- O código NBS hoje cadastrado como padrão na emissão (`114039000`) já está marcado como "confirmar com a
  contabilidade". **Não usaremos nenhum NBS/cClassTrib sem confirmação** — ficam como configuração (PENDENCIAS.md).

## 5. Riscos e pontos de atenção

1. **Data do fato gerador** obrigatória e confirmada pelo usuário (transição 2026–2027).
2. **Valores monetários:** o AvalieImob usa `float` em vários motores (ex.: precificação). No módulo novo usar
   `Decimal` e guardar a resposta da calculadora sem recalcular.
3. **LGPD:** a calculadora só precisa de valor, município, data e classificação — não enviar nome/CPF do cliente.
4. **Ambiente desta sessão:** sem Docker, Java 21 e Go 1.24 → a Fase 1 não pode ser validada aqui (PENDENCIAS.md).

## 6. Perguntas abertas para o solicitante

1. As calculadoras rodam no **Railway** (serviços privados) ou no **servidor próprio** que será montado?
2. O AvalieImob e o CRM estão no **mesmo projeto do Railway**?
3. Regime da Romatec: **Lucro Presumido ou Real**? Os demais assinantes devem poder escolher o próprio regime?
4. Onde entra o "Simular CBS/IBS": **recibo de honorários**, **proposta de consultoria**, **PTAM** — ou os três?
5. O DANFSe oficial é desejado mesmo já havendo o gerador temático? (ele usaria o XML da NFS-e emitida)
6. O contador pode indicar o **NBS e o cClassTrib** de "serviços de avaliação imobiliária" e de "topografia/
   georreferenciamento"?
