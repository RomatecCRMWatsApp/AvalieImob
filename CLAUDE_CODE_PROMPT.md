# 🚀 CLAUDE CODE - FRONTEND AVALIEMOB PHASE 2

## OBJETIVO
Completar o FRONTEND React do AvalieImob com tRPC integrado. Projeto pronto para comercialização SaaS.

## REPOSITÓRIO & ACESSO
```
GitHub: https://github.com/RomatecCRMWatsApp/AvalieImob
Local: /home/claude/AvalieImob
Branch: main
Token: [seu-github-token]
```

## STACK DEFINIDO
- **Framework:** React 18 + TypeScript
- **Build:** Vite
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui (opcional) ou custom
- **HTTP:** tRPC + React Query
- **Routing:** React Router v6
- **Auth:** JWT localStorage + Bearer token
- **Form:** React Hook Form + Zod
- **Icons:** Lucide React
- **Theme:** Dark mode verde premium (#228B22)

## ESTRUTURA FRONTEND

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
│   │   │   └── ImovelMap.tsx
│   │   ├── Avaliacao/
│   │   │   ├── AvaliacaoList.tsx
│   │   │   ├── AvaliacaoForm.tsx
│   │   │   ├── AmostraForm.tsx
│   │   │   ├── AudioTranscrever.tsx
│   │   │   └── CalculosMostra.tsx
│   │   ├── PTAM/
│   │   │   ├── PTAMViewer.tsx
│   │   │   ├── PTAMList.tsx
│   │   │   └── PTAMGenerator.tsx
│   │   └── UI/
│   │       ├── Button.tsx
│   │       ├── Card.tsx
│   │       ├── Modal.tsx
│   │       ├── Input.tsx
│   │       └── Textarea.tsx
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
│   │   ├── auth.ts
│   │   └── utils.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useLocalStorage.ts
│   │   └── useNotification.ts
│   ├── styles/
│   │   ├── globals.css
│   │   └── tailwind.config.js
│   ├── App.tsx
│   ├── main.tsx
│   └── vite-env.d.ts
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── package.json
└── .env.example
```

## TAREFAS PRINCIPAIS (COMMIT POR TAREFA)

### 1️⃣ SETUP VITE + TAILWIND + TYPESCRIPT
```bash
# ✅ Criar vite.config.ts, tsconfig.json, tailwind.config.js
# ✅ Criar index.html com root div
# ✅ Criar package.json com dev scripts
# ✅ Instalar: @vitejs/plugin-react, autoprefixer, postcss
# ✅ Commit: "setup: vite + tailwind + typescript"
```

### 2️⃣ AUTH CONTEXT & HOOKS
```bash
# ✅ Criar useAuth.ts com login/logout/register
# ✅ Criar auth.ts com JWT management (localStorage)
# ✅ Criar AuthGuard.tsx para rotas protegidas
# ✅ Commit: "feat: authentication context + hooks"
```

### 3️⃣ ROUTING & LAYOUT
```bash
# ✅ Criar App.tsx com React Router
# ✅ Criar AppLayout.tsx (Navbar + Sidebar)
# ✅ Criar Navbar.tsx com user profile + logout
# ✅ Criar Sidebar.tsx com menu navegação
# ✅ Commit: "feat: routing + layout base"
```

### 4️⃣ UI COMPONENTS BASE
```bash
# ✅ Button.tsx (verde, dark mode)
# ✅ Card.tsx (container)
# ✅ Input.tsx (styled, com label)
# ✅ Textarea.tsx (form textarea)
# ✅ Modal.tsx (dialog)
# ✅ Badge.tsx (status tags)
# ✅ Commit: "feat: base ui components"
```

### 5️⃣ AUTH PAGES
```bash
# ✅ pages/Login.tsx com form tRPC
# ✅ pages/Register.tsx com form tRPC
# ✅ Validação Zod frontend
# ✅ Toast/notification erro/sucesso
# ✅ Commit: "feat: login + register pages"
```

### 6️⃣ DASHBOARD
```bash
# ✅ pages/Dashboard.tsx com overview
# ✅ StatsCards.tsx (total clientes, imóveis, PTAMs)
# ✅ Gráficos simples (recharts opcional)
# ✅ Links rápidos para CRUD
# ✅ Commit: "feat: dashboard home"
```

### 7️⃣ CLIENTES CRUD
```bash
# ✅ pages/Clientes.tsx com lista + actions
# ✅ ClienteList.tsx (tabela com dados)
# ✅ ClienteForm.tsx (criar/editar modal)
# ✅ ClienteDetail.tsx (detail view)
# ✅ Delete com confirmação
# ✅ Commit: "feat: clientes crud"
```

### 8️⃣ IMÓVEIS CRUD
```bash
# ✅ pages/Imoveis.tsx com lista + filtros
# ✅ ImovelForm.tsx (form com lat/long, áreas)
# ✅ ImovelList.tsx (cards ou tabela)
# ✅ ImovelDetail.tsx (detail com mapa Leaflet básico)
# ✅ Upload fotos (array de URLs)
# ✅ Commit: "feat: imoveis crud"
```

### 9️⃣ AVALIAÇÕES CORE
```bash
# ✅ pages/Avaliacoes.tsx
# ✅ AvaliacaoForm.tsx (criar novo PTAM)
# ✅ AvaliacaoList.tsx (lista com status)
# ✅ AmostraForm.tsx (adicionar amostras dinâmico)
# ✅ AudioTranscrever.tsx (upload + button Whisper)
# ✅ CalculosMostra.tsx (resultados tabela)
# ✅ Commit: "feat: avaliacoes core interface"
```

### 🔟 PTAM GERADOR
```bash
# ✅ pages/PTAMs.tsx
# ✅ PTAMList.tsx (documentos emitidos)
# ✅ PTAMGenerator.tsx (button gerar + preview)
# ✅ PTAMViewer.tsx (embed DOCX)
# ✅ Download DOCX/PDF
# ✅ Commit: "feat: ptam generator + viewer"
```

### 1️⃣1️⃣ NOTIFICAÇÕES & UX
```bash
# ✅ useNotification.ts hook
# ✅ Toast notifications (erro/sucesso/info)
# ✅ Loading states em buttons
# ✅ Error boundaries
# ✅ Commit: "feat: notifications + ux polish"
```

### 1️⃣2️⃣ STYLING & POLISH
```bash
# ✅ Dark mode aplicado em tudo
# ✅ Cores verde (#228B22) + ouro consistentes
# ✅ Responsive design (mobile first)
# ✅ Logo Romatec no header
# ✅ Commit: "style: dark mode verde + responsive"
```

### 1️⃣3️⃣ FINAL INTEGRATION & TESTS
```bash
# ✅ Testar todos endpoints tRPC
# ✅ E2E básico (login → CRUD → gerar PTAM)
# ✅ Performance check
# ✅ Build production
# ✅ Commit: "test: integration tests + build"
```

## REGRAS OBRIGATÓRIAS

1. **UTF-8 sem BOM** em todos arquivos
2. **Commit após cada tarefa** (1 tarefa = 1 commit)
3. **Mensagens de commit em inglês**, descritivas
4. **Zero confirmação** - executa direto, confia em si mesmo
5. **Teste antes de commitar** - build deve passar
6. **TypeScript strict: true**
7. **Validação Zod em TODOS forms**
8. **Tailwind classes** - sem CSS extra
9. **tRPC types** - use types do backend, zero any
10. **Dark mode** - verde (#228B22) como accent, backgrounds dark

## CORES & BRANDING

```
Primary Verde:    #228B22
Dark BG:          #0f1419 ou #1a1f2e
Card BG:          #1f2937
Text Primary:     #f1f5f9
Text Secondary:   #94a3b8
Border:           #334155
Accent Ouro:      #d4af37 (opcional)
Success:          #10b981
Error:            #ef4444
Warning:          #f59e0b
```

## ENV VARIABLES FRONTEND

```
VITE_API_URL=http://localhost:3001/api/trpc
VITE_APP_NAME=AvalieImob
VITE_APP_LOGO=/logo.svg
```

## CHECKLIST PRÉ-DEPLOY

- [ ] Build sem erros: `npm run build`
- [ ] All pages carregam
- [ ] Login → Register → Dashboard flow funciona
- [ ] CRUD base (Cliente/Imóvel) 100%
- [ ] Avaliação → PTAM flow 100%
- [ ] Responsive em mobile (375px)
- [ ] Dark mode ativado por padrão
- [ ] Logo Romatec visível
- [ ] Git push automático após cada commit

## GIT WORKFLOW

```bash
# Workflow automático:
# 1. Fazer tarefa
# 2. git add -A
# 3. git commit -m "tipo: descrição"
# 4. git push origin main
# 5. Próxima tarefa

# Tipos de commit:
feat:  nova funcionalidade
fix:   correção de bug
style: formatação/dark mode
test:  testes
docs:  documentação
refactor: refatoração
setup: setup inicial
```

## DÚVIDAS/DECISÕES

Se encontrar decisão:
- **UI Framework:** Use custom components com Tailwind (mais leve, mais controle)
- **Gráficos:** Recharts para dashboard (leve + tRPC friendly)
- **Mapa:** Leaflet básico para ImovelDetail (OpenStreetMap free)
- **Upload:** Base64 por enquanto (S3 depois)
- **Cache:** React Query padrão (TTL 5min)
- **Validação:** Zod frontend + backend Zod (double validation)

## SUCESSO FINAL

Quando terminar:
```
✅ Frontend 100% funcional
✅ TRPC integrado em todos endpoints
✅ Dark mode verde premium
✅ Deploy pronto (Vite build)
✅ Pronto para vender
```

---

**LET'S BUILD THIS! 🚀**

Comece pela **TAREFA 1: SETUP VITE + TAILWIND**.

Depois me avisa quando terminar cada tarefa, e eu vou comitando e pushando direto.

**GO! 💪**
