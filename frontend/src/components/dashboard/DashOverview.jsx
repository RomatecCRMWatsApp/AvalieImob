// @module DashOverview — Visão geral do painel (upgrade visual verde/dourado/creme).
// Mesmos dados do useDashboard; o shell (Sidebar + TopBar) vem de pages/Dashboard.jsx.
import React from 'react';
import { RefreshCw } from 'lucide-react';
import { BrandSpinner } from '../brand/BrandSpinner';
import useDashboard from '../../hooks/useDashboard';
import DashboardHero from './DashboardHero';
import KpiStrip from './KpiStrip';
import ModuleCards from './ModuleCards';
import AdminResumo from './AdminResumo';
import LaudosChart from './LaudosChart';
import LaudosRecentes from './LaudosRecentes';
import PlanStrip from './PlanStrip';
import '../../styles/dashboard-tokens.css';

const DashOverview = () => {
  const {
    loading, error, reload, firstName, greeting, today,
    kpis, monthly, rascunhos, recentes, plano,
  } = useDashboard();

  return (
    <div className="max-w-[1440px] mx-auto space-y-5 sm:space-y-6">
      <DashboardHero greeting={greeting} firstName={firstName} today={today} rascunhos={rascunhos} />

      {loading ? (
        <div className="py-16 flex justify-center" role="status" aria-live="polite">
          <BrandSpinner label="Carregando indicadores…" />
        </div>
      ) : error ? (
        <div role="alert" className="av-card p-5 flex flex-col sm:flex-row sm:items-center gap-3" style={{ borderColor: '#f0c9c9', background: '#fbe9e9' }}>
          <p style={{ color: '#a52a2a', fontSize: 14, flex: 1 }}>
            Não foi possível carregar os indicadores agora. Verifique a conexão e tente de novo.
          </p>
          <button type="button" onClick={reload} className="av-btn" style={{ border: '1px solid #a52a2a', color: '#a52a2a', background: '#fff' }}>
            <RefreshCw size={16} aria-hidden="true" /> Tentar de novo
          </button>
        </div>
      ) : (
        <KpiStrip kpis={kpis} />
      )}

      <ModuleCards />

      <AdminResumo />

      {!loading && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-5 sm:gap-6">
          <LaudosChart data={monthly} />
          <LaudosRecentes recentes={recentes} />
        </div>
      )}

      {!loading && <PlanStrip plano={plano} />}
    </div>
  );
};

export default DashOverview;
