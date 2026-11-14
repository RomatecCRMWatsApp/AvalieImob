// @module DarkModeToggle — pill flutuante lua/sol (dark/light).
// Auto-gerencia o tema: localStorage > prefers-color-scheme. Aplica a classe
// 'dark' no <html> (Tailwind darkMode: 'class'). Opt-in: default é claro.
import { useEffect, useState, useCallback } from 'react';
import { FERRAMENTAS, useAberturaFerramenta, useNoPainel } from '../lib/ferramentas';

const STORAGE_KEY = 'avalieimob-theme';

export default function DarkModeToggle() {
  const [isDark, setIsDark] = useState(false);

  // Inicialização: respeita a preferência salva ou o tema do sistema.
  useEffect(() => {
    let saved = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch (_e) { /* ignore */ }
    const prefersDark = typeof window !== 'undefined' && window.matchMedia
      && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const shouldBeDark = saved === 'dark' || (!saved && prefersDark);
    setIsDark(shouldBeDark);
    document.documentElement.classList.toggle('dark', shouldBeDark);
  }, []);

  const noPainel = useNoPainel();
  const toggle = useCallback(() => {
    setIsDark((prev) => {
      const next = !prev;
      document.documentElement.classList.toggle('dark', next);
      try { localStorage.setItem(STORAGE_KEY, next ? 'dark' : 'light'); } catch (_e) { /* ignore */ }
      return next;
    });
  }, []);
  // No painel, o tema é alternado pelo menu Ferramentas (sem pílula flutuante).
  useAberturaFerramenta(FERRAMENTAS.TEMA, toggle);
  if (noPainel) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      className={`theme-toggle-pill ${isDark ? 'dark' : 'light'}`}
      title={isDark ? 'Mudar para modo claro' : 'Mudar para modo escuro'}
      aria-label={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}
    >
      <span className="toggle-indicator">{isDark ? '🌙' : '☀️'}</span>
    </button>
  );
}
