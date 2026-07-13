# Instagram Studio — AvalieImob (Design)

**Data:** 2026-07-12
**Autor:** José Romário (Romatec) + Claude
**Conta alvo:** [@avalieimob](https://www.instagram.com/avalieimob)
**Status:** Aprovado para plano de implementação

---

## 1. Contexto e objetivo

O AvalieImob precisa de um módulo interno para **promover o próprio sistema no Instagram**
(@avalieimob). Hoje o sistema só tem divulgação por e-mail (módulo Prospecção) e
WhatsApp/QR (módulo Divulgação). Não há nada de Instagram.

O objetivo é uma **fábrica de conteúdo**: o admin gera posts (texto + arte com a marca),
organiza num calendário editorial e publica de forma **semi-automática** (o Instagram não
permite pré-preencher legenda por link — trava do próprio Instagram — então o fluxo é
"copiar legenda + baixar arte + abrir o Instagram").

Este módulo é **admin-only** (irmão do módulo Prospecção): é o José/Romatec promovendo o
sistema, **não** uma feature multi-tenant para cada assinante.

### Relação com o ChatPlace (importante — não confundir)
O ChatPlace é uma ferramenta **do Claude** (MCP), usada **fora** do AvalieImob, para
**analisar** a conta e **automatizar DMs/funis**. Ele **não** é o motor deste módulo e
**não** é chamado pelo backend do AvalieImob. É um extra opcional de estratégia. Este spec
trata apenas do módulo interno de produção de conteúdo.

---

## 2. Escopo

### Faz
- Gera conteúdo com IA por **pilar**: Recursos do sistema, Autoridade/Educação,
  "Quanto vale meu imóvel" (topo de funil → Calculadora Pública), Novidades e Ofertas.
- Formatos: **post único**, **carrossel** e **roteiro de Reel**.
- Gera a **arte com a identidade da marca** (verde `#0C3320` / dourado `#C9A84C`, logo "A",
  Playfair/Inter, rodapé `@avalieimob`) e exporta **PNG**.
- **Calendário editorial**: status (Ideia → Aprovado → Publicado), data agendada, pilar.
- **Publicação semi-automática (deep link)**: copiar legenda + baixar arte + abrir Instagram.

### Não faz (YAGNI)
- ❌ Publicação/agendamento automático via API Meta (deep link manual foi a escolha).
- ❌ Multi-tenant (só admin).
- ❌ Análise de métricas da conta (isso é o ChatPlace, no Claude).
- ❌ Geração de imagem por IA (usa templates da marca).
- ❌ Scheduler que dispara sozinho — `data_agendada` é só lembrete no calendário.

---

## 3. Arquitetura

Segue os padrões do repositório (rotas sob `/api`, `get_admin_user`, `serialize_doc`,
isolamento por `user_id`, IDs uuid, índices no startup do `server.py`).

### Backend
- `backend/models/instagram_post.py` — modelos Pydantic v2.
- `backend/services/instagram_ia_service.py` — monta os prompts por pilar e chama a
  **cascata de IA já existente** (mesma usada em `contrato_ia_service.py`:
  Groq → Gemini → Claude → OpenAI). Retorna JSON estruturado (título, legenda, hashtags,
  slides/roteiro, cta, link).
- `backend/routes/instagram.py` — router `tags=["instagram"]`, todas as rotas com
  `Depends(get_admin_user)`. Registrado em `routes/__init__.py`.
- Collection **`instagram_posts`** (isolada por `user_id`). Índices no `server.py`:
  `user_id + status`, `user_id + data_agendada`, `id` único.

### Frontend
- `frontend/src/lib/api.js` → `instagramAPI` (gerar / CRUD posts / status).
- `frontend/src/components/dashboard/instagram/InstagramStudio.jsx` — página com 3 blocos.
- `frontend/src/components/dashboard/instagram/InstagramArt.jsx` — templates da marca +
  export PNG.
- Item **"Instagram"** no `Sidebar.jsx` (bloco admin, perto de Prospecção/Divulgação,
  ícone `Instagram`/`Camera`). Rota `/dashboard/admin/instagram` no `Dashboard.jsx`.

---

## 4. Modelo de dados — `instagram_posts`

```
InstagramPost
  id: str (uuid)
  user_id: str
  pilar: "recursos" | "autoridade" | "quanto_vale" | "novidades"
  formato: "post_unico" | "carrossel" | "reel_roteiro"
  titulo: str
  legenda: str          # inclui CTA + "Siga @avalieimob"
  hashtags: list[str]
  slides: list[{ titulo: str, texto: str }]   # só carrossel
  roteiro: str          # só reel_roteiro
  cta: str
  link: str             # destino conforme o pilar
  template_arte: str    # id do template escolhido
  status: "ideia" | "aprovado" | "publicado"
  data_agendada: str | None   # ISO date (lembrete)
  data_publicado: str | None
  criado_em: str (ISO)
  atualizado_em: str (ISO)
```

---

## 5. Pilares e prompts de IA

`instagram_ia_service` guarda um bloco de **contexto do AvalieImob** (o que o sistema faz:
PTAM/laudo NBR 14.653, contratos, assinatura ICP, georreferenciamento, prospecção;
público = corretores/imobiliárias e proprietários) + **regras**:

1. Nada de clickbait vazio ("você não vai acreditar").
2. CTA claro e único por post.
3. Hashtags do nicho (avaliação imobiliária, corretor, imóveis, laudo).
4. Português do Brasil, tom profissional e acessível.
5. Sempre fechar com "Siga @avalieimob".

Cada pilar tem instrução própria e um **link padrão**:
- **recursos** → `/cadastro` (captar assinantes).
- **autoridade** → `/cadastro` (autoridade + conversão).
- **quanto_vale** → `/quanto-vale-meu-imovel` (Calculadora Pública, topo de funil).
- **novidades** → `/cadastro` (pode citar cupom ativo, se houver).

Saída sempre em JSON: `{ titulo, legenda, hashtags[], slides[]|roteiro, cta, link }`.

---

## 6. Geração de arte (frontend, templates da marca)

A arte é montada **no frontend** (HTML/CSS com as fontes reais da marca — Playfair/Inter já
carregadas no app — e o `BrandMark` "A"), e exportada para **PNG** com uma lib leve de
HTML→imagem (`html-to-image`, `toPng`). Antes do capture, aguardar `document.fonts.ready`
para as fontes entrarem no PNG.

**Templates (v1):**
- **T1 — Frase de impacto** (feed 1080×1080): título grande (Playfair), subtítulo, logo "A",
  rodapé `@avalieimob`.
- **T2 — Carrossel de dica** (1080×1350): capa + N slides numerados (título + texto),
  último slide com CTA.
- **T3 — Anúncio de recurso** (feed 1080×1080): nome do recurso + benefício + CTA + logo.

Cores fixas: fundo verde `#0C3320`, destaque dourado `#C9A84C`, texto creme. Cada slide do
carrossel exporta um PNG (`avalieimob-<id>-slide-N.png`).

---

## 7. Fluxo de uso

```
1. Gerador: pilar + assunto + formato  →  [Gerar com IA]
2. Editar título/legenda/hashtags/slides (+ "Aperfeiçoar com IA")
3. Salvar  →  post com status "Ideia"
4. Ver Arte  →  escolher template  →  preview ao vivo
5. Aprovar + agendar data  →  status "Aprovado"
6. No dia: [Copiar legenda] + [Baixar arte] + [Abrir Instagram]
7. Marcar "Publicado"
```

O **Calendário** lista os posts por mês, com filtro por status/pilar, badges coloridos e as
ações acima.

---

## 8. Endpoints (`/api/instagram`, admin)

| Método | Rota | Função |
|---|---|---|
| POST | `/instagram/gerar` | Gera conteúdo com IA (não persiste). Body `{pilar, assunto, formato}`. |
| POST | `/instagram/posts` | Cria post (status `ideia`). |
| GET | `/instagram/posts` | Lista (filtros `mes`, `status`, `pilar`). |
| GET | `/instagram/posts/{id}` | Detalhe. |
| PUT | `/instagram/posts/{id}` | Edita. |
| POST | `/instagram/posts/{id}/status` | Muda status (`ideia`/`aprovado`/`publicado`). |
| DELETE | `/instagram/posts/{id}` | Exclui. |

`POST /instagram/gerar` roda a IA em `asyncio` (padrão do projeto). Erros de IA retornam
mensagem clara (não 500 genérico).

---

## 9. Integrações internas
- **Calculadora Pública** (`/quanto-vale-meu-imovel`): destino do pilar "quanto_vale".
- **Cupons** (`cuponsAPI`): o pilar "novidades" pode sugerir um cupom ativo na legenda.
- **Marca**: reusa cores, `BrandMark` e fontes já existentes no app.

---

## 10. Riscos e limitações
- **Instagram não pré-preenche legenda por link** → por isso o fluxo é copiar+baixar+abrir
  (semi-automático). Expectativa já alinhada com o usuário.
- **Export PNG** depende das fontes carregadas → aguardar `document.fonts.ready`.
- **Nova dependência frontend** (`html-to-image`) — leve e popular; alternativa sem dep é
  desenhar em `<canvas>` nativo (mais trabalhoso).
- **Versionamento**: bump `frontend/build-number.txt` + `CACHEBUST`/`CACHEBUST_BACKEND` a
  cada deploy (regra do projeto).

---

## 11. Decomposição sugerida (para o plano)
1. Backend: modelo + serviço de IA + rotas + índices (testável via API).
2. Frontend: `instagramAPI` + Gerador + Calendário (CRUD e IA funcionando).
3. Frontend: `InstagramArt` (templates + export PNG) + ações de publicação (deep link).
4. Integrações (link Calculadora, cupons) + item no Sidebar + versionamento.
