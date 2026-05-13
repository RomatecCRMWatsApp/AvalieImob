# CLAUDE.md — Instruções permanentes para o Claude Code

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
