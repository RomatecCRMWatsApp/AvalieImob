// @module dashboard/KpiStrip — indicadores do painel (upgrade visual).
// Mesmas fontes de antes (GET /dashboard/stats via useDashboard). Valores em fonte
// de interface, sem quebrar linha; valor completo no title/aria quando compactado.
// Tendência só aparece se o backend enviar a variação (hoje não envia).
import React from 'react';
import { Link } from 'react-router-dom';
import { FileCheck2, Users, Building2, Landmark, Receipt, Divide, TrendingUp, TrendingDown } from 'lucide-react';

const Variacao = ({ delta }) => {
  if (!delta) return null;
  const up = !delta.startsWith('-');
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <span className={`${up ? 'dash-delta-up' : 'dash-delta-down'} inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full`}>
      <Icon className="w-3 h-3" aria-hidden="true" /> {delta}
    </span>
  );
};

const Metric = ({ Icon, label, value, full, desc, to, delta }) => {
  const conteudo = (
    <>
      <span aria-hidden="true" className="hidden min-[440px]:flex items-center justify-center flex-shrink-0"
        style={{ width: 40, height: 40, borderRadius: 999, background: 'var(--av-surface-soft)', color: 'var(--av-brand)' }}>
        <Icon size={19} strokeWidth={1.75} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2 flex-wrap" style={{ fontSize: 13, color: 'var(--av-text-secondary)' }}>
          {label} <Variacao delta={delta} />
        </span>
        <span className="av-metric-value block" title={full || undefined}>
          {value}
          {full && full !== value && <span className="sr-only"> ({full})</span>}
        </span>
        {desc && <span className="block" style={{ fontSize: 12, color: 'var(--av-text-secondary)' }}>{desc}</span>}
      </span>
    </>
  );
  const cls = 'av-card flex items-center gap-3 p-4 min-w-0';
  return to ? (
    <Link to={to} className={`${cls} hover:shadow-md transition-shadow`} style={{ textDecoration: 'none', color: 'inherit' }}>{conteudo}</Link>
  ) : (
    <div className={cls}>{conteudo}</div>
  );
};

const KpiStrip = ({ kpis }) => (
  <section aria-label="Indicadores">
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
      <Metric Icon={FileCheck2} label="Laudos" value={kpis.laudosTotal.toLocaleString('pt-BR')} desc="PTAMs cadastrados" to="/dashboard/ptam" delta={kpis.variacaoLaudos} />
      <Metric Icon={Users} label="Clientes" value={kpis.clientes.toLocaleString('pt-BR')} desc="No cadastro" to="/dashboard/clientes" />
      <Metric Icon={Building2} label="Imóveis" value={kpis.imoveis.toLocaleString('pt-BR')} desc="Identificados" to="/dashboard/imoveis" />
      <Metric Icon={Landmark} label="Volume avaliado" value={kpis.volumeCompact} full={kpis.volumeFull} desc="Soma dos laudos" delta={kpis.variacaoVolume} />
      <Metric Icon={Receipt} label="Ticket médio" value={kpis.ticketCompact} full={kpis.ticketMedio} desc="Por laudo" />
      <Metric Icon={Divide} label="Laudos por cliente" value={kpis.laudosPorCliente} desc="Média" />
    </div>
  </section>
);

export default KpiStrip;
