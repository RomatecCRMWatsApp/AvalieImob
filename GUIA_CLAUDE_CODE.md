# 🔧 COMO USAR CLAUDE CODE PARA AVALIEMOB

## 1️⃣ INSTALAÇÃO & SETUP

### No seu computador:
```bash
# Instalar Claude Code (CLI)
npm install -g @anthropic/claude-code

# Ou via Homebrew (macOS)
brew install anthropic-claude-code

# Logar
claude-code login

# Escolher repo
claude-code set-repo https://github.com/RomatecCRMWatsApp/AvalieImob
```

### Via Docker (mais fácil):
```bash
docker run -it \
  -v /caminho/para/AvalieImob:/workspace \
  -e GITHUB_TOKEN=seu_token \
  -e OPENAI_API_KEY=sk-... \
  anthropic/claude-code:latest
```

---

## 2️⃣ WORKFLOW

### Cada tarefa:
```bash
cd /workspace

# 1. Ler o PROMPT
cat CLAUDE_CODE_PROMPT.md

# 2. Executar prompt direto no Claude Code
claude-code exec << 'EOF'
## TAREFA 1: Setup Vite + Tailwind

[seu prompt aqui]
EOF

# 3. Ou, abrir interativo
claude-code interactive

# 4. Colar o prompt da TAREFA e deixar rolar
```

---

## 3️⃣ COMANDOS ÚTEIS

```bash
# Ver status do repo
claude-code status

# Push automático (já faz sozinho)
claude-code push

# Ver logs
claude-code logs

# Rodar testes
claude-code test

# Build
claude-code build
```

---

## 4️⃣ FLUXO RECOMENDADO

**Opção A: Via Terminal Claude Code**

```bash
# Abrir prompt interativo
claude-code interactive

# Colar este prompt no chat:
"""
Você é um developer full-stack sênior.
Você vai implementar o FRONTEND do AvalieImob seguindo exatamente este prompt:

[COPIAR CONTEÚDO DO CLAUDE_CODE_PROMPT.md AQUI]

COMECE PELA TAREFA 1: Setup Vite + Tailwind.

Quando terminar cada tarefa:
- Faça commit automaticamente
- Execute `npm run build` para validar
- Aviseme quando estiver pronto para a próxima
- Nunca peça confirmação - execute direto
"""
```

**Opção B: Criar issue no GitHub + Claude Code pega automaticamente**

```bash
# No GitHub, criar issue:
Title: "FRONTEND Phase 2: Complete React UI"
Body: [COLAR CLAUDE_CODE_PROMPT.md]

# Claude Code vê a issue e começa automaticamente
```

---

## 5️⃣ O QUE CLAUDE CODE FAZ AUTOMATICAMENTE

✅ Clona o repo  
✅ Lê arquivos existentes  
✅ Cria novos arquivos  
✅ Edita código  
✅ Rodar `npm install`  
✅ Rodar `npm run build`  
✅ Fazer `git add -A && git commit && git push`  
✅ Testar código  
✅ Repordar erros  

---

## 6️⃣ MONITORAR PROGRESSO

```bash
# Ver último commit
git log --oneline | head -10

# Ver branch
git status

# Ver mudanças
git diff HEAD~1

# Acompanhar em tempo real
watch -n 5 git log --oneline
```

---

## 7️⃣ SE DER ERRO

Claude Code tentará corrigir automaticamente. Se não conseguir:

```bash
# Volta 1 commit
git revert HEAD

# Ou, manual fix
cd packages/frontend
npm install  # Se faltou dep
npm run build  # Validar
git add -A && git commit -m "fix: error correction"
git push
```

---

## 8️⃣ AMBIENTE VARIABLES

Criar `.env.local` no repo:

```env
GITHUB_TOKEN=ghp_sua_token_aqui
OPENAI_API_KEY=sk_...
VITE_API_URL=http://localhost:3001/api/trpc
```

Claude Code lê automaticamente.

---

## 9️⃣ CHECKLIST ANTES DE COMEÇAR

- [ ] GitHub token criado (Settings → Developer Settings → Personal Access Tokens)
- [ ] Token com permissões: repo, workflow
- [ ] Repo AvalieImob clonado localmente
- [ ] Node.js 18+ instalado
- [ ] npm/yarn instalado
- [ ] CLAUDE_CODE_PROMPT.md no repo

---

## 🔟 ESTIMATIVA DE TEMPO

| Tarefa | Tempo | Commits |
|--------|-------|---------|
| 1. Vite Setup | 10 min | 1 |
| 2. Auth | 20 min | 1 |
| 3. Routing | 15 min | 1 |
| 4. UI Components | 30 min | 1 |
| 5. Auth Pages | 25 min | 1 |
| 6. Dashboard | 20 min | 1 |
| 7. Cliente CRUD | 30 min | 1 |
| 8. Imóvel CRUD | 35 min | 1 |
| 9. Avaliação Core | 40 min | 1 |
| 10. PTAM | 30 min | 1 |
| 11. Notificações | 20 min | 1 |
| 12. Styling | 30 min | 1 |
| 13. Integration | 20 min | 1 |
| **TOTAL** | **325 min** | **13** |
| | **~5.5h** | |

---

## 🎯 PRÓXIMO PASSO

1. **Copiar o arquivo `CLAUDE_CODE_PROMPT.md`**
2. **Abrir Claude Code interactive**: `claude-code interactive`
3. **Colar o prompt completo**
4. **Deixar rodar 5-6 horas**
5. **Frontend pronto + 13 commits automáticos**

---

## 🔗 LINKS ÚTEIS

- Claude Code Docs: https://docs.anthropic.com/claude-code
- GitHub Token: https://github.com/settings/tokens
- Vite Docs: https://vitejs.dev
- Tailwind: https://tailwindcss.com
- tRPC React: https://trpc.io/docs/react

---

**Bora nessa! 🚀**
