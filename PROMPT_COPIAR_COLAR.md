# PROMPT PARA CLAUDE CODE - COPIAR E COLAR

Você é um developer full-stack sênior. Seu objetivo: implementar o FRONTEND React 100% funcional do AvalieImob.

## REPOSITÓRIO
- URL: https://github.com/RomatecCRMWatsApp/AvalieImob
- Branch: main
- Caminho: /home/claude/AvalieImob

## STACK
React 18 + TypeScript + Vite + Tailwind CSS + tRPC + React Router v6 + React Hook Form

## INSTRUÇÕES CRÍTICAS

1. **NUNCA PEÇA CONFIRMAÇÃO** - execute tudo direto
2. **1 TAREFA = 1 COMMIT** - faça commit após cada etapa
3. **TESTE ANTES DE COMMITAR** - `npm run build` deve passar
4. **UTF-8 SEM BOM** em todos arquivos
5. **DARK MODE VERDE** (#228B22) como accent, backgrounds dark (#0f1419, #1f2937)
6. **TAILWIND ONLY** - sem CSS extra, classes do Tailwind
7. **VALIDAÇÃO ZOD** em 100% dos forms
8. **tRPC TYPES** - use types do backend, zero `any`
9. **COMMIT MESSAGES EM INGLÊS** - descritivas, tipo: feat/fix/style

## TAREFAS (ORDEM EXATA)

### TAREFA 1: Setup Vite + Tailwind + TypeScript
- Criar vite.config.ts com @vitejs/plugin-react
- Criar tsconfig.json (strict: true)
- Criar tailwind.config.js + postcss.config.js
- Criar index.html com <div id="root"></div>
- Instalar: tailwindcss autoprefixer postcss typescript
- COMMIT: "setup: vite + tailwind + typescript"

### TAREFA 2: tRPC Client Setup
- Criar src/lib/trpc.ts (createTRPCReact)
- Criar src/lib/trpc-provider.tsx (TRPCProvider com httpBatchLink)
- Criar src/lib/auth.ts (getToken, setToken, removeToken)
- Instalar: @trpc/client @trpc/react-query @tanstack/react-query
- COMMIT: "feat: trpc client + provider"

### TAREFA 3: Auth Hooks & Context
- Criar src/hooks/useAuth.ts com login/logout/register functions
- Usar tRPC auth.login, auth.registro, auth.me
- Armazenar token em localStorage
- Criar useLocalStorage.ts hook
- COMMIT: "feat: auth hooks + context"

### TAREFA 4: UI Base Components
- Criar src/components/UI/Button.tsx (verde, dark mode)
- Criar src/components/UI/Card.tsx
- Criar src/components/UI/Input.tsx
- Criar src/components/UI/Textarea.tsx
- Criar src/components/UI/Modal.tsx
- Todos com Tailwind, sem dependências extras
- COMMIT: "feat: base ui components"

### TAREFA 5: Routing + Layout
- Criar App.tsx com React Router (BrowserRouter)
- Criar src/components/Layout/AppLayout.tsx (Navbar + Sidebar + Outlet)
- Criar src/components/Layout/Navbar.tsx com logo Romatec + user profile
- Criar src/components/Layout/Sidebar.tsx com menu navegação
- Criar src/components/Auth/AuthGuard.tsx (ProtectedRoute)
- Routes: /, /login, /register, /dashboard, /clientes, /imoveis, /avaliacoes, /ptams, /*
- COMMIT: "feat: routing + layout"

### TAREFA 6: Auth Pages
- Criar pages/Login.tsx com LoginForm (email, password)
- Criar pages/Register.tsx com RegisterForm (email, password, nome, role)
- Usar React Hook Form + Zod
- Validação: email válido, senha min 8 chars
- Toast erro/sucesso com notificação
- Redirecionar pós-sucesso para /dashboard
- COMMIT: "feat: login + register pages"

### TAREFA 7: Dashboard Home
- Criar pages/Dashboard.tsx
- Criar components/Dashboard/StatsCards.tsx (4 cards: clientes, imóveis, PTAMs, audios)
- Usar tRPC para fetch de stats
- Cards com números grandes, verde accent
- Links rápidos para CRUD sections
- COMMIT: "feat: dashboard home"

### TAREFA 8: Cliente CRUD
- Criar pages/Clientes.tsx com tabela + actions
- Criar components/Cliente/ClienteList.tsx (tabela com razao_social, cnpj, city)
- Criar components/Cliente/ClienteForm.tsx (modal com create/edit)
- Criar components/Cliente/ClienteDetail.tsx
- Usar tRPC: cliente.listar, cliente.criar, cliente.atualizar, cliente.deletar
- Delete com modal confirmação
- Paginação básica
- COMMIT: "feat: clientes crud"

### TAREFA 9: Imóvel CRUD
- Criar pages/Imoveis.tsx
- Criar components/Imovel/ImovelList.tsx (cards ou table com endereço, cidade, tipo)
- Criar components/Imovel/ImovelForm.tsx (form com: endereco, lat/long, cidade, estado, tipo, áreas m2/ha)
- Criar components/Imovel/ImovelDetail.tsx
- Usar tRPC: imovel.* endpoints
- Upload fotos (array URLs base64)
- Filtro por cliente
- COMMIT: "feat: imoveis crud"

### TAREFA 10: Avaliação Core Interface
- Criar pages/Avaliacoes.tsx
- Criar components/Avaliacao/AvaliacaoList.tsx (lista com status: rascunho/em_andamento/pronto/emitido)
- Criar components/Avaliacao/AvaliacaoForm.tsx (criar novo PTAM)
- Criar components/Avaliacao/AmostraForm.tsx (adicionar amostras dinâmico - table com rows)
- Criar components/Avaliacao/AudioTranscrever.tsx (upload audio + button Whisper + text display)
- Criar components/Avaliacao/CalculosMostra.tsx (tabela com resultados: valor unitário, valor total, margem erro)
- Usar tRPC: avaliacao.*, amostra.*, audio.*, calculo.*
- COMMIT: "feat: avaliacoes core interface"

### TAREFA 11: PTAM Generator + Viewer
- Criar pages/PTAMs.tsx
- Criar components/PTAM/PTAMList.tsx (documentos emitidos com numero_ptam, data)
- Criar components/PTAM/PTAMGenerator.tsx (button gerar DOCX + loading + success toast)
- Criar components/PTAM/PTAMViewer.tsx (embed do DOCX ou iframe)
- Usar tRPC: ptam.gerar, ptam.listar, ptam.obter
- Download DOCX/PDF buttons
- COMMIT: "feat: ptam generator + viewer"

### TAREFA 12: Notifications & UX
- Criar hooks/useNotification.ts (toast hook)
- Implementar toast notifications (erro/sucesso/info/warning)
- Loading states em buttons durante requests
- Error boundaries básicas
- Empty states em listas
- Success messages após CRUD
- COMMIT: "feat: notifications + ux polish"

### TAREFA 13: Styling & Dark Mode Complete
- Aplicar dark mode em TODAS pages/components
- Cores: Verde (#228B22) accent, backgrounds #0f1419, cards #1f2937
- Logo Romatec no header (src/assets/logo.svg ou inline SVG)
- Responsive design (Tailwind breakpoints md/lg/xl)
- Hover states, transitions, shadows
- Typography hierarchy
- Spacing consistente
- COMMIT: "style: dark mode verde + responsive"

### TAREFA 14: Integration Tests + Build
- Testar flow completo: login → criar cliente → criar imóvel → criar avaliação → gerar PTAM
- Validar build sem erros: `npm run build`
- Validar TypeScript: `npx tsc --noEmit`
- Verificar performance (Lighthouse)
- COMMIT: "test: integration tests + build"

## ESTRUTURA FINAL

```
packages/frontend/
├── src/
│   ├── components/
│   │   ├── Auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── RegisterForm.tsx
│   │   │   └── AuthGuard.tsx
│   │   ├── Layout/
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── AppLayout.tsx
│   │   ├── Dashboard/
│   │   │   ├── DashboardHome.tsx
│   │   │   └── StatsCards.tsx
│   │   ├── Cliente/
│   │   │   ├── ClienteList.tsx
│   │   │   ├── ClienteForm.tsx
│   │   │   └── ClienteDetail.tsx
│   │   ├── Imovel/
│   │   │   ├── ImovelList.tsx
│   │   │   ├── ImovelForm.tsx
│   │   │   └── ImovelDetail.tsx
│   │   ├── Avaliacao/
│   │   │   ├── AvaliacaoList.tsx
│   │   │   ├── AvaliacaoForm.tsx
│   │   │   ├── AmostraForm.tsx
│   │   │   ├── AudioTranscrever.tsx
│   │   │   └── CalculosMostra.tsx
│   │   ├── PTAM/
│   │   │   ├── PTAMList.tsx
│   │   │   ├── PTAMGenerator.tsx
│   │   │   └── PTAMViewer.tsx
│   │   └── UI/
│   │       ├── Button.tsx
│   │       ├── Card.tsx
│   │       ├── Input.tsx
│   │       ├── Textarea.tsx
│   │       └── Modal.tsx
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Clientes.tsx
│   │   ├── Imoveis.tsx
│   │   ├── Avaliacoes.tsx
│   │   ├── PTAMs.tsx
│   │   └── NotFound.tsx
│   ├── lib/
│   │   ├── trpc.ts
│   │   ├── trpc-provider.tsx
│   │   └── auth.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useNotification.ts
│   │   └── useLocalStorage.ts
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── package.json
└── .env.example
```

## CORES & TOKENS

```
Verde Primary: #228B22
Dark BG: #0f1419
Card BG: #1f2937
Text Primary: #f1f5f9
Border: #334155
Success: #10b981
Error: #ef4444
```

## COMECE AGORA!

**TAREFA 1: Setup Vite + Tailwind + TypeScript**

Não peça confirmação - execute direto. Faça commit quando terminar. Próxima tarefa.

**GO! 🚀**
