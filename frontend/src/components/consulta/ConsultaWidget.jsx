import { useState } from 'react';
import ConsultaModal from './ConsultaModal';
import './ConsultaWidget.css';

export default function ConsultaWidget() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Botão FAB lateral direito */}
      <button
        className="consulta-fab"
        onClick={() => setOpen(true)}
        title="Consultar CNPJ / CPF"
        aria-label="Abrir consulta CNPJ/CPF"
      >
        <span className="consulta-fab-icon">🔍</span>
        <span className="consulta-fab-label">CNPJ / CPF</span>
      </button>

      {open && <ConsultaModal onClose={() => setOpen(false)} />}
    </>
  );
}
