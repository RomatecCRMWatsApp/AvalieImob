// @module dashboard/KpiStrip — 4 KPIs horizontais (design v4).
// Cards brancos com border-left colorido, valor em Playfair e badge de variação.
import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const DeltaBadge = ({ delta }) => {
  if (!delta) {
    return (
      <span className="dash-delta-flat inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full">
        <Minus className="w-3 h-3" /> estável
      </span>
    );
  }
  const up = !delta.startsWith('-');
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <span className={`${up ? 'dash-delta-up' : 'dash-delta-down'} inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full`}>
      <Icon className="w-3 h-3" /> {delta}
    </span>
  );
};

const KpiCard = ({ eyebrow, value, label, accent, delta, showDelta }) => (
  <div
    className="bg-white rounded-xl p-5 shadow-sm flex flex-col gap-1"
    style={{ borderLeft: `3px solid ${accent}` }}
  >
    <div className="flex items-start justify-between">
      <span className="dash-eyebrow" style={{ fontSize: 9, color: 'var(--dash-muted)' }}>
        {eyebrow}
      </span>
      {showDelta && <DeltaBadge delta={delta} />}
    </div>
    <div className="dash-display" style={{ fontSize: 30, color: 'var(--dash-text)', lineHeight: 1.05 }}>
      {value}
    </div>
    <span style={{ fontSize: 11, color: 'var(--dash-muted)' }}>{label}</span>
  </div>
);

const KpiStrip = ({ kpis }) => (
  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
    <KpiCard
      eyebrow="Volume avaliado"
      value={kpis.volumeCompact}
      label="Total acumulado"
      accent="var(--dash-kpi-1)"
      delta={kpis.variacaoVolume}
      showDelta
    />
    <KpiCard
      eyebrow="Laudos emitidos"
      value={kpis.laudosTotal}
      label="No período"
      accent="var(--dash-kpi-2)"
      delta={kpis.variacaoLaudos}
      showDelta
    />
    <KpiCard
      eyebrow="Ticket médio"
      value={kpis.ticketMedio}
      label="Por laudo"
      accent="var(--dash-kpi-3)"
    />
    <KpiCard
      eyebrow="Laudos / cliente"
      value={kpis.laudosPorCliente}
      label="Média"
      accent="var(--dash-kpi-4)"
    />
  </div>
);

export default KpiStrip;
