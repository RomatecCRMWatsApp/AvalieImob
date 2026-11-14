// @module shell/ToolsLauncher — ponto único de entrada das ferramentas do painel
// (Roma_IA, Fotos, Consulta CNPJ/CPF e tema). Substitui as abas verticais que
// cobriam o conteúdo. Cada ferramenta continua sendo o widget original: aqui só
// se pede que ele abra (lib/ferramentas).
import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Wrench, Sparkles, Camera, Building2, SunMoon, FileSearch } from 'lucide-react';
import { FERRAMENTAS, abrirFerramenta } from '../../lib/ferramentas';

const ITENS = [
  { id: FERRAMENTAS.ROMA_IA, Icon: Sparkles, label: 'Roma_IA', desc: 'Assistente de avaliação (chat)' },
  { id: FERRAMENTAS.FOTOS, Icon: Camera, label: 'Fotos', desc: 'Galeria com GPS e tarja' },
  { id: FERRAMENTAS.CONSULTA, Icon: Building2, label: 'CNPJ / CPF', desc: 'Consulta rápida' },
];

export default function ToolsLauncher() {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const btnRef = useRef(null);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const fora = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    const tecla = (e) => {
      if (e.key === 'Escape') { setOpen(false); btnRef.current?.focus(); }
    };
    document.addEventListener('mousedown', fora);
    document.addEventListener('keydown', tecla);
    // foco no primeiro item ao abrir
    const t = setTimeout(() => menuRef.current?.querySelector('button, a')?.focus(), 0);
    return () => {
      clearTimeout(t);
      document.removeEventListener('mousedown', fora);
      document.removeEventListener('keydown', tecla);
    };
  }, [open]);

  const usar = (id) => { setOpen(false); abrirFerramenta(id); };

  // Setas ↑/↓ percorrem os itens do menu.
  const onKeyMenu = (e) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault();
    const itens = Array.from(menuRef.current?.querySelectorAll('button, a') || []);
    const i = itens.indexOf(document.activeElement);
    const prox = e.key === 'ArrowDown' ? (i + 1) % itens.length : (i - 1 + itens.length) % itens.length;
    itens[prox]?.focus();
  };

  return (
    <div ref={wrapRef} style={{ position: 'relative' }}>
      <button
        ref={btnRef}
        type="button"
        className="av-icon-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Ferramentas"
        title="Ferramentas"
        onClick={() => setOpen((v) => !v)}
      >
        <Wrench size={18} aria-hidden="true" />
      </button>

      {open && (
        <div ref={menuRef} role="menu" aria-label="Ferramentas" className="av-popover" onKeyDown={onKeyMenu}>
          <div style={{ padding: '0.5rem 0.75rem 0.25rem', fontSize: 12, fontWeight: 600, color: 'var(--av-text-secondary)' }}>
            Ferramentas
          </div>
          {ITENS.map(({ id, Icon, label, desc }) => (
            <button key={id} type="button" role="menuitem" className="av-menu-item" onClick={() => usar(id)}>
              <Icon size={18} aria-hidden="true" style={{ color: 'var(--av-brand)', flexShrink: 0 }} />
              <span>{label}<small>{desc}</small></span>
            </button>
          ))}
          <Link role="menuitem" to="/dashboard/cnd" className="av-menu-item" onClick={() => setOpen(false)}>
            <FileSearch size={18} aria-hidden="true" style={{ color: 'var(--av-brand)', flexShrink: 0 }} />
            <span>Certidões CND<small>Abre a página de consultas</small></span>
          </Link>
          <div style={{ height: 1, background: 'var(--av-border)', margin: '0.25rem 0.5rem' }} />
          <button type="button" role="menuitem" className="av-menu-item" onClick={() => usar(FERRAMENTAS.TEMA)}>
            <SunMoon size={18} aria-hidden="true" style={{ color: 'var(--av-brand)', flexShrink: 0 }} />
            <span>Tema claro / escuro</span>
          </button>
        </div>
      )}
    </div>
  );
}
