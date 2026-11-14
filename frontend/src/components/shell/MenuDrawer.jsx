// @module shell/MenuDrawer — gaveta acessível do menu principal (mobile/tablet).
// Diálogo modal: fecha no backdrop e no Escape, prende o foco enquanto aberto,
// bloqueia a rolagem do fundo e respeita prefers-reduced-motion (via CSS).
// O retorno do foco ao botão que abriu fica com quem chama (onClose).
import React, { useEffect, useRef } from 'react';

const FOCAVEIS = 'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';

export default function MenuDrawer({ open, onClose, children }) {
  const painelRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const painel = painelRef.current;
    const anterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // foco inicial: item ativo do menu, senão o primeiro focável
    const t = setTimeout(() => {
      const alvo = painel?.querySelector('[aria-current="page"]') || painel?.querySelector(FOCAVEIS);
      alvo?.focus();
    }, 30);

    const tecla = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); onClose(); return; }
      if (e.key !== 'Tab' || !painel) return;
      const itens = Array.from(painel.querySelectorAll(FOCAVEIS)).filter((el) => el.offsetParent !== null);
      if (!itens.length) return;
      const primeiro = itens[0];
      const ultimo = itens[itens.length - 1];
      if (e.shiftKey && document.activeElement === primeiro) { e.preventDefault(); ultimo.focus(); }
      else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primeiro.focus(); }
    };
    document.addEventListener('keydown', tecla);
    return () => {
      clearTimeout(t);
      document.removeEventListener('keydown', tecla);
      document.body.style.overflow = anterior;
    };
  }, [open, onClose]);

  return (
    <div className="lg:hidden">
      {open && <div className="av-drawer-backdrop" onClick={onClose} aria-hidden="true" />}
      <div
        ref={painelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Menu principal"
        className="av-drawer"
        data-open={open ? 'true' : 'false'}
      >
        {children}
      </div>
    </div>
  );
}
