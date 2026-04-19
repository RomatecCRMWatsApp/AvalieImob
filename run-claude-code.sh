#!/bin/bash

# 🚀 CLAUDE CODE EXECUTOR - AVALIEMOB FRONTEND
# Este script executa Claude Code com o prompt pronto

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║         🚀 CLAUDE CODE EXECUTOR - AVALIEMOB FRONTEND 🚀        ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verificar dependências
echo -e "${BLUE}→${NC} Verificando dependências..."

if ! command -v node &> /dev/null; then
    echo "✗ Node.js não encontrado"
    exit 1
fi
echo -e "${GREEN}✓${NC} Node.js: $(node --version)"

if ! command -v npm &> /dev/null; then
    echo "✗ npm não encontrado"
    exit 1
fi
echo -e "${GREEN}✓${NC} npm: $(npm --version)"

echo ""
echo -e "${BLUE}→${NC} Instalando Claude Code CLI..."
npm install -g @anthropic/claude-code 2>/dev/null || echo "Claude Code já instalado"
echo -e "${GREEN}✓${NC} Claude Code pronto"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    STARTING CLAUDE CODE                        ║"
echo "║                                                                ║"
echo "║  Você vai executar 14 tarefas automáticamente:                 ║"
echo "║  • Vite + Tailwind setup                                       ║"
echo "║  • tRPC client integration                                     ║"
echo "║  • React pages + components                                    ║"
echo "║  • Dark mode verde (#228B22)                                   ║"
echo "║  • 14 commits automáticos                                      ║"
echo "║  • Build validation                                            ║"
echo "║                                                                ║"
echo "║  ⏱️  Tempo estimado: 5-6 horas                                  ║"
echo "║  🚀 Deixe rodar SEM INTERRUPÇÃO!                               ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

read -p "Pressione ENTER para iniciar Claude Code..."
echo ""
echo "Abrindo Claude Code interativo..."
echo ""
echo "PRÓXIMO PASSO:"
echo "1. Cole este prompt no chat do Claude Code:"
echo "---BEGIN PROMPT---"
cat PROMPT_COPIAR_COLAR.md
echo "---END PROMPT---"
echo ""
echo "2. Deixe Claude Code trabalhar (não interrompa!)"
echo "3. Monitore com: git log --oneline"
echo ""

claude-code interactive
