Você é um developer React sênior. Integre os 3 ícones brand AvalieImob no frontend React.

REPOSITÓRIO: https://github.com/RomatecCRMWatsApp/AvalieImob
Ícones já estão em /public/: avaliemob-icon.svg, avaliemob-icon-only.svg, avaliemob-icon-white.svg

REGRAS:
- Nunca peça confirmação
- 1 tarefa = 1 commit + push
- Dark mode padrão (#0f1419)
- Tailwind only
- Responsive mobile

7 TAREFAS RÁPIDAS:

1. TAREFA 1: Favicon + og:image
   - Adicionar favicon em HTML head
   - Usar avaliemob-icon-only.svg
   - Meta og:image com avaliemob-icon.svg
   - COMMIT: "feat: add favicon and og:image"

2. TAREFA 2: Logo Component
   - Criar src/components/Logo.tsx
   - Props: variant (dark|white), size (small|medium|large)
   - Hover effects com Tailwind
   - COMMIT: "feat: create Logo component"

3. TAREFA 3: Navbar Logo
   - Atualizar Layout/Navbar.tsx
   - Integrar Logo component
   - Logo + "AvalieImob" text em verde #228B22
   - COMMIT: "feat: integrate logo in navbar"

4. TAREFA 4: Sidebar Logo
   - Atualizar Layout/Sidebar.tsx
   - Ícone pequeno no topo
   - Link para dashboard
   - COMMIT: "feat: add logo to sidebar"

5. TAREFA 5: Dashboard Avatar
   - Atualizar pages/Dashboard.tsx
   - Avatar circular com ícone
   - Usar avaliemob-icon-only.svg
   - COMMIT: "feat: add avatar to dashboard"

6. TAREFA 6: Auth Pages Logo
   - Atualizar pages/Login.tsx e Register.tsx
   - Logo animado no topo (animação flutuante)
   - Tailwind animation
   - COMMIT: "feat: add animated logo to auth pages"

7. TAREFA 7: Dark/Light Mode Ready
   - Preparar componente para futuro switch de tema
   - Dark: avaliemob-icon.svg
   - Light: avaliemob-icon-white.svg
   - COMMIT: "feat: dark mode logo variants ready"

COMPONENTE LOGO (usar como template):

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

TAILWIND ANIMAÇÕES:
- hover:scale-105, hover:scale-110
- hover:drop-shadow-xl
- transition-transform duration-300
- Custom float no global.css (se precisar)

CORES:
- Verde: #228B22
- Ouro: #d4af37
- Dark BG: #0f1419

COMECE AGORA!

TAREFA 1: Favicon + og:image

Não peça confirmação. Execute direto.

GO! 🚀
