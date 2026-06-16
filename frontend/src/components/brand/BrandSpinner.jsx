import React from 'react';
import { BrandMark } from './BrandMark';

// Spinner inline padrão do app: o "A" parado com o arco dourado girando.
// Substitui spinners genéricos em estados de carregamento standalone (não em
// botões). variant: 'glyph' (A verde, fundo claro) | 'glyphGold' (fundo escuro) | 'badge'.
export function BrandSpinner({ size = 30, label, variant = 'glyph', className }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={'flex flex-col items-center justify-center gap-3 ' + (className || '')}
    >
      <span
        className="relative inline-flex items-center justify-center"
        style={{ width: size + 16, height: size + 16 }}
      >
        <span
          aria-hidden="true"
          className="absolute inset-0 rounded-full border-[2.5px] border-transparent"
          style={{
            borderTopColor: '#B8860B',
            borderRightColor: '#B8860B',
            animation: 'brand-spin .9s linear infinite',
          }}
        />
        <BrandMark size={size} variant={variant} title="" />
      </span>
      {label && <span className="text-[13px] text-neutral-500 dark:text-neutral-400">{label}</span>}
    </div>
  );
}

export default BrandSpinner;
