# 🚀 COMO RODAR CLAUDE CODE - FRONTEND AVALIEMOB

## ✅ TOKEN JÁ CONFIGURADO!

Seu GitHub token já foi adicionado ao repositório. Você pode prosseguir direto.

---

## 🎯 PRÓXIMAS AÇÕES (3 PASSOS)

### PASSO 1: Exportar OpenAI Key (2 min)

```bash
# Gerar/obter sua OpenAI API Key em:
# https://platform.openai.com/api-keys

export OPENAI_API_KEY=sk-seu_key_aqui
```

Se você já tem a key, apenas exporte:
```bash
export OPENAI_API_KEY=sk-proj-...
```

### PASSO 2: Rodar Claude Code (30 sec)

```bash
cd /home/claude/AvalieImob

# Opção A: Via script automático (RECOMENDADO)
./run-claude-code.sh

# OU Opção B: Direto no CLI
claude-code interactive
```

### PASSO 3: Cola o Prompt (1 min)

Quando Claude Code abrir o chat:

1. **Copie tudo de `PROMPT_COPIAR_COLAR.md`**
   ```bash
   cat PROMPT_COPIAR_COLAR.md
   ```

2. **Cole no chat do Claude Code**

3. **Pressione ENTER e deixe rodar** ⚠️ NÃO INTERROMPA!

---

## ⏱️ TIMELINE

```
⏱️  Instalação Claude Code:  1 min
⏱️  Cole o prompt:           1 min
⏱️  Claude Code trabalha:    5-6 horas (você não faz nada!)
⏱️  Build + testes:          10 min
───────────────────────────────
📈 Total:                     ~6 horas
```

---

## 🎯 O QUE VAI ACONTECER

Claude Code vai automaticamente:

```
✅ Criar estrutura Vite + React + TypeScript
✅ Instalar dependencies
✅ Setup Tailwind CSS
✅ Criar 8 páginas:
   ├─ Login + Register
   ├─ Dashboard
   ├─ Clientes CRUD
   ├─ Imóveis CRUD
   ├─ Avaliações + PTAM
   └─ Notificações + UX

✅ Criar 20+ componentes:
   ├─ UI base (Button, Card, Input, Modal, etc)
   ├─ Layout (Navbar, Sidebar, AppLayout)
   ├─ Forms (Login, Register, Cliente, Imóvel, etc)
   └─ Features (Audio transcrever, calcular, gerar PTAM)

✅ Integrar tRPC em 100% endpoints
✅ Validação Zod em 100% forms
✅ Dark mode verde (#228B22) premium
✅ Responsive design (mobile-first)
✅ Toast notifications
✅ Loading states + error handling
✅ 14 commits automáticos no GitHub
✅ Validar build (`npm run build`)
```

---

## 📊 ESTRUTURA FINAL

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

---

## 🔍 MONITORAR PROGRESSO

Enquanto Claude Code trabalha, você pode monitorar em outro terminal:

```bash
# Ver commits sendo feitos
watch -n 5 git log --oneline

# Ver mudanças no código
git diff HEAD~1

# Ver arquivos criados
find packages/frontend/src -type f | wc -l

# Ver se está buildando
tail -f /tmp/claude-code.log  # ou similar
```

---

## ✅ CHECKLIST ANTES DE INICIAR

- [ ] OpenAI API key obtida (https://platform.openai.com/api-keys)
- [ ] OpenAI key exportada: `export OPENAI_API_KEY=sk-...`
- [ ] GitHub token já foi configurado ✅ (você já fez isso)
- [ ] Na pasta: `/home/claude/AvalieImob`
- [ ] Leu `PROMPT_COPIAR_COLAR.md`
- [ ] Pronto para deixar rodar por 6 horas

---

## 🚀 INICIAR AGORA!

```bash
# Exportar OpenAI key (UM ÚNICO COMANDO)
export OPENAI_API_KEY=sk-proj-seu_key_aqui

# Ir para o diretório
cd /home/claude/AvalieImob

# Rodar Claude Code
./run-claude-code.sh

# OU direto:
claude-code interactive

# Depois: Cola o prompt de PROMPT_COPIAR_COLAR.md e deixa rodar!
```

---

## 📞 SE ALGO DER ERRADO

**Claude Code não abre?**
```bash
npm install -g @anthropic/claude-code
claude-code login
```

**Quer tentar de novo?**
```bash
cd /home/claude/AvalieImob
git reset --hard origin/main
./run-claude-code.sh
```

**Quer monitora em tempo real?**
```bash
# Em outro terminal
cd /home/claude/AvalieImob
watch -n 2 'git log --oneline | head -5'
```

---

## 💡 LEMBRE-SE

✨ **Você só precisa:**
1. Exportar OpenAI key (1 comando)
2. Rodar script (1 comando)
3. Cola prompt (copy/paste)
4. **DEIXAR RODAR POR 6 HORAS** ⚠️

✨ **NÃO INTERROMPA!**
- Claude Code vai fazer 14 commits
- Cada commit = 1 tarefa
- Build vai ser validado automaticamente
- Pronto para vender em ~6 horas

---

## 🎯 DEPOIS QUE TERMINAR

```bash
# Verificar build
npm run build

# Deploy no Railway
git push origin main
# Railway vai pegar automaticamente

# Em ~5 min vai estar live:
# https://avaliemob.railway.app
```

---

**BORA COMEÇAR! 🚀💚**
