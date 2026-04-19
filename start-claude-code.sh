#!/bin/bash

# 🚀 SCRIPT DE INICIALIZAÇÃO - CLAUDE CODE AVALIEMOB
# Este script facilita o setup e execução do Claude Code

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║        🚀 AVALIEMOB FRONTEND - CLAUDE CODE LAUNCHER 🚀       ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funções
print_step() {
    echo -e "${BLUE}→${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# 1. Verificar se estamos no diretório correto
print_step "Verificando diretório..."
if [ ! -f "CLAUDE_CODE_PROMPT.md" ]; then
    print_error "CLAUDE_CODE_PROMPT.md não encontrado!"
    print_warning "Execute este script na raiz do projeto AvalieImob"
    exit 1
fi
print_success "Diretório OK"

# 2. Verificar dependências
print_step "Verificando dependências..."

if ! command -v node &> /dev/null; then
    print_error "Node.js não encontrado! Instale em https://nodejs.org"
    exit 1
fi
print_success "Node.js: $(node --version)"

if ! command -v npm &> /dev/null; then
    print_error "npm não encontrado!"
    exit 1
fi
print_success "npm: $(npm --version)"

if ! command -v git &> /dev/null; then
    print_error "Git não encontrado!"
    exit 1
fi
print_success "Git: $(git --version | awk '{print $3}')"

# 3. Verificar GitHub token
print_step "Verificando GitHub token..."
if [ -z "$GITHUB_TOKEN" ]; then
    print_warning "GITHUB_TOKEN não definido!"
    echo ""
    echo "   Para criar um token:"
    echo "   1. Ir para: https://github.com/settings/tokens"
    echo "   2. Criar novo 'Personal Access Token'"
    echo "   3. Permissões: repo, workflow"
    echo "   4. Exportar: export GITHUB_TOKEN=ghp_..."
    echo ""
    read -p "   Deseja continuar sem token? (Não recomendado) [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "GitHub token detectado"
fi

# 4. Verificar OpenAI key
print_step "Verificando OpenAI API key..."
if [ -z "$OPENAI_API_KEY" ]; then
    print_warning "OPENAI_API_KEY não definido (necessário para Whisper)"
    read -p "   Deseja continuar? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "OpenAI API key detectada"
fi

# 5. Verificar se Claude Code está instalado
print_step "Verificando Claude Code CLI..."
if ! command -v claude-code &> /dev/null; then
    print_warning "Claude Code CLI não encontrado!"
    echo ""
    echo "   Instale com:"
    echo "   → npm install -g @anthropic/claude-code"
    echo ""
    read -p "   Deseja instalar agora? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Instalando Claude Code..."
        npm install -g @anthropic/claude-code
        print_success "Claude Code instalado!"
    else
        exit 1
    fi
else
    print_success "Claude Code CLI detectado"
fi

# 6. Mostrar resumo
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                     RESUMO CONFIGURAÇÃO                      ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                              ║"
echo "║  📁 Diretório:        $(pwd)"
echo "║  🔗 Repositório:      https://github.com/RomatecCRMWatsApp/AvalieImob"
echo "║  📝 Prompt:           CLAUDE_CODE_PROMPT.md"
echo "║  ⏱️  Tempo estimado:   ~5.5 horas"
echo "║  📦 Commits:          13"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 7. Menu de ação
echo "Escolha uma ação:"
echo ""
echo "  1) Iniciar Claude Code (recomendado)"
echo "  2) Ver prompt"
echo "  3) Ler guia de uso"
echo "  4) Sair"
echo ""
read -p "Opção [1-4]: " -n 1 -r option
echo ""
echo ""

case $option in
    1)
        print_step "Iniciando Claude Code..."
        echo ""
        echo "Instruções:"
        echo "1. Cole este prompt no chat do Claude Code:"
        echo "---"
        cat CLAUDE_CODE_PROMPT.md
        echo "---"
        echo ""
        echo "2. Deixe Claude Code trabalhar (não interrompa)"
        echo "3. Cada tarefa = 1 commit automático"
        echo "4. Você pode monitorar com: git log --oneline"
        echo ""
        read -p "Pressione Enter para abrir Claude Code interativo..."
        claude-code interactive
        ;;
    2)
        print_step "Exibindo prompt..."
        cat CLAUDE_CODE_PROMPT.md | less
        ;;
    3)
        print_step "Exibindo guia..."
        cat GUIA_CLAUDE_CODE.md | less
        ;;
    4)
        print_warning "Saindo..."
        exit 0
        ;;
    *)
        print_error "Opção inválida!"
        exit 1
        ;;
esac

print_success "Operação concluída!"
