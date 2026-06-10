# CLAUDE.md — Instruções permanentes para o Claude Code

## ⚠️ Versionamento — OBRIGATÓRIO a cada atualização/deploy

**SEMPRE que fizer qualquer alteração que vá para a `main` (deploy), ANTES do commit:**

1. **Incrementar `frontend/build-number.txt`** (+1 em relação ao valor atual). Este é o passo
   que faz o badge de versão mudar.
2. A versão exibida é `v{MAJOR}.{MINOR}.{build}`, gerada por `frontend/scripts/genversion.js`
   (prebuild) em `frontend/src/version.js`.
3. **Por que isso é necessário:** no build do Docker/Railway o `.git` NÃO existe
   (`.dockerignore` exclui `**/.git`), então `git rev-list` falha e o número vem **só** do
   `build-number.txt`. Um `git push` direto **não incrementa nada** — só o `DEPLOY.bat` ou
   esta regra incrementam. Se esquecer, o badge fica travado (ex.: ficou preso em v1.0.350).
4. **Subir o MINOR** (constante em `genversion.js`) em marcos/releases relevantes.
5. Após bumpar, rodar `node frontend/scripts/genversion.js` para regenerar o `version.js`
   (opcional — o Railway regenera no prebuild).
6. Registrar a atualização também no Obsidian (ver seção abaixo), nota de releases/changelog.

**Estado atual: v1.3.659** (MAJOR=1, MINOR=3) — release: link público do laudo vinculado ao recibo (3 pontos) — (1) gerar_recibo_ptam gera o link_publico do PTAM automaticamente se não existir e grava em recibo.ptam_link; (2) ReciboWizard mostra campo read-only "Link do laudo" com botão Copiar; (3) legenda_recibo (WhatsApp) inclui o ptam_link + faz strip de HTML do servico/descricao. Histórico abaixo:

**v1.3.658** (MAJOR=1, MINOR=3) — release: bloco de assinatura do recibo (recibo_pdf.py) passa a usar a qualificação COMPLETA do avaliador via utils.avaliador.resolver_dados_avaliador (mesma fonte do PTAM): nome em maiúsculas + "Avaliador — CRECI/MA · CNAI · CFT/MA · ..." + endereço completo + telefone (substitui o antigo cargo "Admin" + 1º registro). Histórico abaixo:

**v1.3.657** (MAJOR=1, MINOR=3) — release: recibo ganha paridade com PTAM (tudo aditivo) — (A) campo Descrição com RichTextEditor + botão "Aperfeiçoar com IA" (aiAPI.chat) no ReciboWizard; recibo_pdf limpa HTML do descricao (_strip_html). (B) gerar_recibo_ptam grava ptam_link (link público do laudo) no recibo, exibido no PDF. (C) RecibosList ganha botão "Posicionar" abrindo AssinaturaPosicionadaModal tipo="recibo" (mesmo retângulo do PTAM; backend assinatura.py já suporta recibo). Histórico abaixo:

**v1.3.656** (MAJOR=1, MINOR=3) — release: recibo gerado pelo card PTAM agora também é persistido na collection `recibos` (upsert por `ptam_id`, número via counter `recibo_honorarios_{ano}`, status=emitido, emitente hidratado, destinatário do PTAM), aparecendo na aba Recibos para editar/assinar. `gerar_recibo_ptam` grava em `recibos` além de `recibos_ptam`; PTAM passa a guardar `recibo_id`. Releases anteriores: 655 botão verde "✓ Recibo Emitido" no card; 651 Dashboard v4.

## Obsidian MCP — Sincronização automática

A cada feature implementada, bug corrigido, decisão técnica tomada ou ideia registrada nesta sessão, salve automaticamente no Obsidian via MCP na pasta correspondente. Nunca peça confirmação para salvar.

### Mapeamento de pastas Obsidian

| Tipo de mudança | Pasta no Obsidian |
|-----------------|-------------------|
| Nova feature ou módulo | `03-Frontend/` ou `02-Backend/` |
| Nova rota de API | `02-Backend/Rotas API.md` |
| Novo serviço ou lógica de negócio | `02-Backend/Services.md` ou `02-Backend/Regras de Negócio.md` |
| Nova collection MongoDB ou campo | `01-Banco de Dados/Schema Completo.md` |
| Bug corrigido | `04-Roadmap/Bugs Conhecidos.md` |
| Decisão técnica ou arquitetural | `05-Decisões Técnicas/ADRs.md` |
| Funcionalidade planejada ou ideia | `04-Roadmap/Funcionalidades Planejadas.md` |
| Novo componente React | `03-Frontend/Componentes.md` |
| Nova página ou rota frontend | `03-Frontend/Páginas.md` |
| Mudança na stack ou dependências | `00-Overview/Stack Tecnológica.md` |

### Como salvar no Obsidian

Use o MCP tool `mcp__obsidian__str_replace` para atualizar notas existentes, ou `mcp__obsidian__create` para novas notas.

Exemplo para adicionar uma rota nova:
```
mcp__obsidian__str_replace(
  path="02-Backend/Rotas API.md",
  old_str="## Outros módulos",
  new_str="| POST | `/nova-rota` | JWT | Descrição |\n\n## Outros módulos"
)
```

## Contexto do projeto

- **Projeto:** RomaTec AvalieImob — SaaS de avaliação imobiliária brasileiro
- **Backend:** FastAPI + Python + MongoDB (Motor async)
- **Frontend:** React 19 + Tailwind CSS + shadcn/ui
- **Banco:** MongoDB (sem schema rígido, modelos Pydantic como contrato)
- **Auth:** JWT HS256, 168h, bcrypt
- **Pagamentos:** Mercado Pago (mensal R$89.90, trimestral R$239.90, anual R$849.90)
- **IA:** Roma_IA com cascata Groq → Gemini → Claude → OpenAI
- **Docs completos:** Vault Obsidian em `C:\Users\Ronicley Pinto\Documents\ROMATEC_AVALIEIMOB_\ROMATECAVALIEIMOB\`

## Convenções do projeto

- Rotas backend: todas com prefixo `/api`, arquivo em `backend/routes/`
- Modelos: Pydantic v2 em `backend/models/`, use `model_dump(mode="json")`
- Isolamento de dados: sempre inclua `{"user_id": uid}` nas queries MongoDB
- Numeração de documentos: use padrão `find_one_and_update` com `$inc` na collection `counters`
- Versionamento: PTAM e Contratos usam sistema de versões com SHA-256 + diff
- Rate limiting: `@limiter.limit()` nas rotas sensíveis
- Segurança: headers de segurança aplicados globalmente via `SecurityHeadersMiddleware`
