# 🎨 PROMPT CLAUDE CODE - INTEGRAR ÍCONES AVALIEMOB

## OBJETIVO
Integrar os 3 ícones brand AvalieImob no frontend React completo. Ícones já estão em `/public/`.

## REPOSITÓRIO
https://github.com/RomatecCRMWatsApp/AvalieImob
Branch: main
Ícones: `/public/avaliemob-icon.svg`, `/public/avaliemob-icon-only.svg`, `/public/avaliemob-icon-white.svg`

## INSTRUÇÕES CRÍTICAS
1. NUNCA peça confirmação - executa direto
2. 1 tarefa = 1 commit + push
3. Use SVG direto (já otimizado)
4. Mantenha dark mode (#0f1419) como padrão
5. Responsive em mobile
6. Tailwind ONLY - sem CSS extra

## 7 TAREFAS (RÁPIDAS)

### TAREFA 1: Favicon + HTML Head
- Adicionar favicon aos arquivos HTML
- Usar: `/avaliemob-icon-only.svg`
- Adicionar meta tags: og:image com `/avaliemob-icon.svg`
- COMMIT: "feat: add favicon and og:image"
- PUSH

### TAREFA 2: Logo Component
- Criar `src/components/Logo.tsx`
- Importar `/public/avaliemob-icon.svg`
- Componente reutilizável com props: variant (dark|white), size (small|medium|large)
- Tailwind styling com hover effects
- COMMIT: "feat: create Logo component"
- PUSH

### TAREFA 3: Navbar Integration
- Atualizar `src/components/Layout/Navbar.tsx`
- Usar Logo component no header
- Adicionar animação de hover
- Logo + "AvalieImob" text em verde (#228B22)
- COMMIT: "feat: integrate logo in navbar"
- PUSH

### TAREFA 4: Sidebar Integration
- Atualizar `src/components/Layout/Sidebar.tsx`
- Colocar ícone pequeno no topo da sidebar
- Link para dashboard ao clicar
- COMMIT: "feat: add logo to sidebar"
- PUSH

### TAREFA 5: Dashboard Avatar
- Atualizar `src/pages/Dashboard.tsx`
- Adicionar avatar com ícone no card do usuário
- Usar `/avaliemob-icon-only.svg` em circular border
- COMMIT: "feat: add avatar to dashboard"
- PUSH

### TAREFA 6: Login/Register Pages
- Atualizar `src/pages/Login.tsx` e `Register.tsx`
- Colocar logo animado no topo
- Animação flutuante com Tailwind
- COMMIT: "feat: add animated logo to auth pages"
- PUSH

### TAREFA 7: Dark/Light Mode Toggle
- Criar switch de tema em Navbar (opcional, para futuro)
- Quando dark: usar `/avaliemob-icon.svg`
- Quando light: usar `/avaliemob-icon-white.svg`
- COMMIT: "feat: dark mode logo variants ready"
- PUSH

## COMPONENTE LOGO (EXEMPLO)

```typescript
interface LogoProps {
  variant?: 'dark' | 'white';
  size?: 'small' | 'medium' | 'large';
  animated?: boolean;
  href?: string;
}

export function Logo({ 
  variant = 'dark', 
  size = 'medium',
  animated = false,
  href = '/'
}: LogoProps) {
  const sizeMap = {
    small: 'w-8 h-8',
    medium: 'w-12 h-12',
    large: 'w-16 h-16'
  };

  const iconSrc = variant === 'white' 
    ? '/avaliemob-icon-white.svg'
    : '/avaliemob-icon.svg';

  const className = `${sizeMap[size]} drop-shadow-lg ${
    animated ? 'hover:scale-110 transition-transform' : ''
  }`;

  return (
    <a href={href}>
      <img src={iconSrc} alt="AvalieImob" className={className} />
    </a>
  );
}
```

## TAILWIND CLASSES PARA ANIMAÇÕES

```
Hover Effects:
- hover:scale-105
- hover:scale-110
- hover:drop-shadow-xl
- transition-transform duration-300

Animations:
- animate-pulse (suave)
- animate-bounce (jump)

Custom float (no global.css):
@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}
.animate-float { animation: float 3s ease-in-out infinite; }
```

## ARQUIVOS A MODIFICAR

1. `src/components/Logo.tsx` - CRIAR
2. `src/components/Layout/Navbar.tsx` - ATUALIZAR
3. `src/components/Layout/Sidebar.tsx` - ATUALIZAR
4. `src/pages/Dashboard.tsx` - ATUALIZAR
5. `src/pages/Login.tsx` - ATUALIZAR
6. `src/pages/Register.tsx` - ATUALIZAR
7. `src/index.css` - ADICIONAR animações (se precisar)

## CORES ROMATEC

```
Verde Primary:     #228B22
Verde Escuro:      #1a6b1a
Ouro Accent:       #d4af37
Dark BG:           #0f1419
Card BG:           #1f2937
```

## COMECE AGORA!

**TAREFA 1: Favicon + HTML Head**

Não peça confirmação. Execute direto. 1 commit por tarefa.

GO! 🚀💚
