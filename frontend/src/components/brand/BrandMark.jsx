import React, { useId } from 'react';

// Fonte ÚNICA do monograma "A" da AvalieImob (mesma geometria do ícone do PWA).
// O furo do "A" usa fillRule="evenodd" (revela o fundo). Cada instância gera um id
// de gradiente único via useId() para não colidir quando há vários marks na tela.
//
// variant: 'badge' (quadrado arredondado, ícone) | 'circle' (redondo, FAB/avatar)
//          | 'glyph' (A verde em transparente) | 'glyphGold' (A dourado, sobre escuro)
//          | 'seal' (A verde dentro de anel dourado, impressão)
// state:   'idle' | 'thinking' (anel dourado girando — IA processando)

const A_PATH =
  'M512 222 L805 802 L654 802 L512 498 L370 802 L219 802 Z ' +
  'M512 372 L575 478 L449 478 Z';
const GREEN = '#0C3320';

export function BrandMark({
  size = 40,
  variant = 'badge',
  state = 'idle',
  title = 'AvalieImob',
  className,
}) {
  const gid = useId();
  const bg = `url(#${gid})`;
  const thinking = state === 'thinking';
  const round = variant === 'circle' || variant === 'seal';

  return (
    <span
      className={className}
      role="img"
      aria-label={title}
      style={{ display: 'inline-flex', position: 'relative', width: size, height: size }}
    >
      {thinking && (
        <span
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: -Math.round(size * 0.12),
            borderRadius: round ? '50%' : '24%',
            border: `${Math.max(2, Math.round(size * 0.05))}px solid transparent`,
            borderTopColor: '#B8860B',
            borderRightColor: '#B8860B',
            animation: 'brand-spin .9s linear infinite',
          }}
        />
      )}
      <svg width={size} height={size} viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#E0C264" />
            <stop offset="0.55" stopColor="#C9A84C" />
            <stop offset="1" stopColor="#B8860B" />
          </linearGradient>
        </defs>

        {variant === 'badge' && (
          <>
            <rect width="1024" height="1024" rx="228" fill={bg} />
            <path d={A_PATH} fill={GREEN} fillRule="evenodd" />
          </>
        )}
        {variant === 'circle' && (
          <>
            <circle cx="512" cy="512" r="512" fill={bg} />
            <path d={A_PATH} fill={GREEN} fillRule="evenodd" />
          </>
        )}
        {variant === 'glyph' && <path d={A_PATH} fill={GREEN} fillRule="evenodd" />}
        {variant === 'glyphGold' && <path d={A_PATH} fill={bg} fillRule="evenodd" />}
        {variant === 'seal' && (
          <>
            <circle cx="512" cy="512" r="496" fill="none" stroke={bg} strokeWidth="28" />
            <path
              d={A_PATH}
              fill={GREEN}
              fillRule="evenodd"
              transform="translate(512 512) scale(0.78) translate(-512 -512)"
            />
          </>
        )}
      </svg>
    </span>
  );
}

export default BrandMark;
