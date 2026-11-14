// @module dashboard/LaudosRecentes — Lista de laudos recentes (upgrade visual).
import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, ArrowRight } from 'lucide-react';


const StatusPill = ({ status }) => {
  const cls = status === 'Rascunho' ? 'dash-pill-rascunho' : 'dash-pill-finalizado';
  return (
    <span className={`${cls} text-[10px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap`}>
      {status}
    </span>
  );
};

const LaudosRecentes = ({ recentes = [] }) => {

  return (
    <div className="av-card p-5 sm:p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--av-text)' }}>
          Laudos recentes
        </h2>
        <Link
          to="/dashboard/ptam"
          className="flex items-center gap-1 text-sm font-semibold hover:underline"
          style={{ color: 'var(--av-gold-ink)', minHeight: 44 }}
        >
          Ver todos <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      {/* Tabela */}
      {recentes.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-8 gap-3">
          <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: 'var(--dash-green-light)' }}>
            <FileText className="w-5 h-5" style={{ color: 'var(--dash-green-mid)' }} />
          </div>
          <p className="text-sm" style={{ color: 'var(--dash-muted)' }}>Nenhum laudo ainda.</p>
          <Link
            to="/dashboard/ptam"
            className="text-xs font-semibold px-3 py-1.5 rounded-lg text-white"
            style={{ background: 'var(--dash-green-mid)' }}
          >
            Criar primeiro laudo
          </Link>
        </div>
      ) : (
        <div className="flex-1 -mx-2">
          {recentes.map((r) => (
            <Link
              key={r.id}
              to={`/dashboard/ptam/${r.id}`}
              className="dash-row flex items-center justify-between gap-2 px-2 py-2.5 rounded-lg transition-colors min-h-[44px]"
            >
              <div className="min-w-0">
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--av-text)' }}>
                  {r.numero}
                </div>
                <div className="truncate" style={{ fontSize: 12, color: 'var(--dash-text)' }}>
                  {r.solicitante}
                </div>
                {r.data && (
                  <div style={{ fontSize: 10, color: 'var(--dash-muted)' }}>{r.data}</div>
                )}
              </div>
              <StatusPill status={r.status} />
            </Link>
          ))}
        </div>
      )}

    </div>
  );
};

export default LaudosRecentes;
