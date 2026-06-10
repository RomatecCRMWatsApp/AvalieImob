// @module dashboard/LaudosRecentes — Lista de laudos recentes + bloco de volume (design v4).
import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { FileText, ArrowRight } from 'lucide-react';

// Meta anual de volume avaliado (referência para a barra de progresso).
const META_VOLUME = 5_000_000;

const StatusPill = ({ status }) => {
  const cls = status === 'Rascunho' ? 'dash-pill-rascunho' : 'dash-pill-finalizado';
  return (
    <span className={`${cls} text-[10px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap`}>
      {status}
    </span>
  );
};

const LaudosRecentes = ({ recentes = [], volumeTotal = 0, volumeFull = 'R$ 0' }) => {
  const ano = new Date().getFullYear();
  const pct = useMemo(
    () => Math.min(100, Math.round((Number(volumeTotal) / META_VOLUME) * 100)),
    [volumeTotal],
  );
  const restante = Math.max(0, META_VOLUME - Number(volumeTotal));
  const fmt = (v) => `R$ ${Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`;

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="dash-display" style={{ fontSize: 18, color: 'var(--dash-text)' }}>
          Laudos recentes
        </h3>
        <Link
          to="/dashboard/ptam"
          className="flex items-center gap-1 text-xs font-semibold hover:underline"
          style={{ color: 'var(--dash-green-mid)' }}
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
              className="dash-row flex items-center justify-between gap-2 px-2 py-2.5 rounded-lg transition-colors"
            >
              <div className="min-w-0">
                <div className="dash-display" style={{ fontSize: 13, color: 'var(--dash-text)' }}>
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

      {/* Bloco de volume */}
      <div className="mt-4 pt-4" style={{ borderTop: '1px solid var(--dash-green-light)' }}>
        <div className="flex items-center justify-between mb-1.5">
          <span style={{ fontSize: 11, color: 'var(--dash-muted)' }}>Volume avaliado {ano}</span>
          <span className="font-semibold" style={{ fontSize: 11, color: 'var(--dash-green-mid)' }}>{pct}%</span>
        </div>
        <div className="dash-display mb-2" style={{ fontSize: 20, color: 'var(--dash-text)' }}>
          {volumeFull}
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--dash-green-light)' }}>
          <div className="dash-progress-fill h-full rounded-full transition-all duration-700" style={{ width: `${pct}%` }} />
        </div>
        <div className="flex items-center justify-between mt-1.5" style={{ fontSize: 9, color: 'var(--dash-muted)' }}>
          <span>Meta {fmt(META_VOLUME)}</span>
          <span>Faltam {fmt(restante)}</span>
        </div>
      </div>
    </div>
  );
};

export default LaudosRecentes;
