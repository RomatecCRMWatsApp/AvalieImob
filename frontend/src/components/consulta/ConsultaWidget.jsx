import { useState, useCallback } from 'react';
import ConsultaModal from './ConsultaModal';
import './ConsultaWidget.css';
import { FERRAMENTAS, useAberturaFerramenta, useNoPainel } from '../../lib/ferramentas';

export default function ConsultaWidget() {
  const [open, setOpen] = useState(false);
  const noPainel = useNoPainel();
  useAberturaFerramenta(FERRAMENTAS.CONSULTA, useCallback(() => setOpen(true), []));

  return (
    <>
      {/* Botão FAB lateral direito (no painel, o acesso é pelo botão Ferramentas) */}
      {!noPainel && (
      <button
        className="consulta-fab"
        onClick={() => setOpen(true)}
        title="Consultar CNPJ / CPF"
        aria-label="Abrir consulta CNPJ/CPF"
      >
        <span className="consulta-fab-icon">🔍</span>
        <span className="consulta-fab-label">CNPJ / CPF</span>
      </button>
      )}

      {open && <ConsultaModal onClose={() => setOpen(false)} />}
    </>
  );
}
