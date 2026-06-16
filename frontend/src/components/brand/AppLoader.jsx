import React from 'react';
import { BrandMark } from './BrandMark';

// Loader/splash com o monograma "A". fullscreen cobre a viewport (boot/splash);
// inline (fullscreen={false}) ocupa o container — ex.: enquanto gera um PTAM.
export function AppLoader({ label = 'Carregando…', fullscreen = true }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={
        (fullscreen
          ? 'fixed inset-0 z-50 bg-white dark:bg-[#0C3320] '
          : 'w-full py-16 ') + 'flex flex-col items-center justify-center gap-5'
      }
    >
      <div className="relative flex items-center justify-center" style={{ width: 72, height: 72 }}>
        <span
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            borderRadius: '24%',
            border: '2px solid #0C3320',
            animation: 'brand-ring 1.8s ease-out infinite',
          }}
        />
        <BrandMark size={64} variant="badge" title="AvalieImob" />
      </div>

      <div className="w-44 h-1 rounded-full bg-black/10 dark:bg-white/15 overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ background: '#B8860B', animation: 'brand-bar 2.2s ease-in-out infinite' }}
        />
      </div>

      <span className="text-sm text-neutral-600 dark:text-neutral-300">{label}</span>
    </div>
  );
}

export default AppLoader;
