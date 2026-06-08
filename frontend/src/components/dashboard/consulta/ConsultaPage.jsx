// @module dashboard/consulta/ConsultaPage — Acesso integrado (página) à Consulta Rápida
import ConsultaPanel from '../../consulta/ConsultaPanel';
import '../../consulta/ConsultaModal.css';

export default function ConsultaPage() {
  return (
    <div className="p-4 md:p-6">
      <div className="mb-5">
        <h1 className="font-display text-2xl font-bold text-gray-900">Consulta CNPJ / CPF</h1>
        <p className="text-sm text-gray-500 mt-1">
          Consulta de empresas na Receita Federal e validação de CPF. Gere o PDF, baixe
          ou envie por WhatsApp / Telegram.
        </p>
      </div>

      <div className="consulta-page-card">
        <div className="consulta-header">
          <div className="consulta-header-title">
            <span className="consulta-header-icon">🔍</span>
            <span>Consulta Rápida</span>
          </div>
        </div>
        <ConsultaPanel autoFocus={false} />
      </div>
    </div>
  );
}
