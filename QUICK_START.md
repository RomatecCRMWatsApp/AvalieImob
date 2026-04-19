# ⚡ QUICK START - 30 SEGUNDOS

## 🎯 OBJETIVO
Frontend React 100% pronto com Claude Code em ~6 horas (automático).

## ⚙️ SETUP (2 min)

```bash
# 1. Exportar tokens (IMPORTANTE!)
export GITHUB_TOKEN=ghp_seu_token_aqui
export OPENAI_API_KEY=sk-sua-key-aqui

# 2. Ir para o diretório
cd /home/claude/AvalieImob

# 3. Executar script
./start-claude-code.sh

# 4. Escolher opção 1 no menu
# 5. Claude Code abre automaticamente
# 6. Colar o prompt (ou deixar script fazer)
# 7. Deixar rodar (~6 horas)
```

## 📊 O QUE ACONTECE

Claude Code vai:
- ✅ Criar 50+ arquivos React
- ✅ Instalar dependencies
- ✅ Setup Vite + Tailwind
- ✅ Criar 8 páginas + 20 components
- ✅ Integrar tRPC em tudo
- ✅ Validação Zod 100%
- ✅ Dark mode verde premium
- ✅ Fazer 14 commits automáticos
- ✅ Validar build (`npm run build`)

## 🎨 RESULTADO FINAL

```
✨ Dark mode verde (#228B22)
✨ Logo Romatec no header
✨ CRUD completo (Cliente/Imóvel/Avaliação)
✨ Geração PTAM automática
✨ Transcrição áudio (Whisper)
✨ Responsive mobile-first
✨ 14 commits automáticos
✨ Build validado
```

## 🚀 DEPLOYMENT

```bash
# Quando terminar, deploy é trivial:
git push origin main

# Railway pega automaticamente
# Build: < 5 min
# Live: https://avaliemob.railway.app
```

## ✅ CHECKLIST

- [ ] GitHub token exportado: `export GITHUB_TOKEN=...`
- [ ] OpenAI key exportado: `export OPENAI_API_KEY=...`
- [ ] Node.js 18+ instalado
- [ ] Na pasta: `/home/claude/AvalieImob`
- [ ] Executou: `./start-claude-code.sh`

## 🆘 PROBLEMAS?

**Claude Code não inicia?**
```bash
npm install -g @anthropic/claude-code
claude-code login
```

**Quer rodar manualmente?**
```bash
claude-code interactive
# Cole PROMPT_COPIAR_COLAR.md no chat
```

**Quer via Docker?**
```bash
docker run -it -v $(pwd):/workspace \
  -e GITHUB_TOKEN=... \
  -e OPENAI_API_KEY=... \
  anthropic/claude-code:latest
```

## 🎯 TIMELINE

- ⏱️ 2 min: Setup
- ⏱️ 6 horas: Claude Code trabalha (não interrompa!)
- ⏱️ 5 min: Deploy Railway
- ✅ PRONTO PARA VENDER

---

**Bora nessa! 🚀**
