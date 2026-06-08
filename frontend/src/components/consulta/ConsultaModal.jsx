// @module consulta/ConsultaModal — Popup flutuante (FAB) que envolve o ConsultaPanel
import { useEffect } from 'react';
import ConsultaPanel from './ConsultaPanel';
import './ConsultaModal.css';

export default function ConsultaModal({ onClose }) {
  // Fechar com ESC
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      className="consulta-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="consulta-modal" role="dialog" aria-modal="true" aria-label="Consulta CNPJ/CPF">
        <div className="consulta-header">
          <div className="consulta-header-title">
            <span className="consulta-header-icon">🔍</span>
            <span>Consulta Rápida</span>
          </div>
          <button className="consulta-close" onClick={onClose} aria-label="Fechar">✕</button>
        </div>

        <ConsultaPanel autoFocus />
      </div>
    </div>
  );
}
