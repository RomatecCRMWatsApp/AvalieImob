// @module dashboard/PlanStrip — Rodapé com plano atual (design v4).
import React from 'react';
import { Link } from 'react-router-dom';
import { Star } from 'lucide-react';

const PlanStrip = ({ plano }) => {
  const ativo = plano?.ativo;
  const sub = plano?.features?.[0]
    ? `${plano.features[0]}${plano.validade ? ` · válido até ${plano.validade}` : ''}`
    : (plano?.validade ? `Válido até ${plano.validade}` : 'Assinatura ativa');

  return (
    <Link
      to="/dashboard/assinatura"
      className="flex items-center justify-between gap-4 px-5 py-4 rounded-md transition-transform hover:-translate-y-0.5"
      style={{ background: 'var(--dash-green-hero)' }}
    >
      <div className="flex items-center gap-4 min-w-0">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ border: '1px solid var(--dash-green-mid)' }}
        >
          <Star className="w-5 h-5" style={{ color: 'var(--dash-gold)' }} fill="var(--dash-gold)" />
        </div>
        <div className="min-w-0">
          <div className="text-white font-semibold truncate" style={{ fontSize: 14 }}>
            Plano {plano?.nome} · Laudos ilimitados
          </div>
          <div className="truncate" style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>
            {sub}
          </div>
        </div>
      </div>

      <span
        className="text-[10px] font-bold px-3 py-1 rounded-full whitespace-nowrap"
        style={{
          background: ativo ? 'rgba(201,168,76,0.12)' : 'rgba(255,255,255,0.08)',
          color: ativo ? 'var(--dash-gold)' : 'rgba(255,255,255,0.6)',
          border: `1px solid ${ativo ? 'var(--dash-gold)' : 'rgba(255,255,255,0.2)'}`,
        }}
      >
        {ativo ? 'ATIVO' : 'INATIVO'}
      </span>
    </Link>
  );
};

export default PlanStrip;
