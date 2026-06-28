// @module DashOverview — Visão geral do dashboard (design v4).
// Compõe os subcomponentes via hook useDashboard. Mantém o shell (Sidebar + TopBar)
// fornecido por pages/Dashboard.jsx — este componente é apenas o conteúdo da home.
import React from 'react';
import { BrandSpinner } from '../brand/BrandSpinner';
import useDashboard from '../../hooks/useDashboard';
import DashboardHero from './DashboardHero';
import KpiStrip from './KpiStrip';
import LaudosChart from './LaudosChart';
import LaudosRecentes from './LaudosRecentes';
import PlanStrip from './PlanStrip';
import '../../styles/dashboard-tokens.css';

const DashOverview = () => {
  const {
    loading, firstName, greeting, today,
    kpis, monthly, rascunhos, recentes, plano,
  } = useDashboard();

  if (loading) {
    return (
      <div className="py-24 flex justify-center">
        <BrandSpinner label="Carregando…" />
      </div>
    );
  }

  return (
    <div
      className="dash-ui -m-4 sm:-m-6 lg:-m-8 p-4 sm:p-6 lg:p-8 space-y-6"
      style={{ background: 'var(--dash-bg)', minHeight: '100%' }}
    >
      <DashboardHero
        greeting={greeting}
        firstName={firstName}
        today={today}
        rascunhos={rascunhos}
        kpis={kpis}
      />

      <KpiStrip kpis={kpis} />

      {/* Grid inferior: gráfico (1fr) + recentes (300px) */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
        <LaudosChart data={monthly} />
        <LaudosRecentes
          recentes={recentes}
          volumeTotal={kpis.volumeTotal}
          volumeFull={kpis.volumeFull}
        />
      </div>

      <PlanStrip plano={plano} />
    </div>
  );
};

export default DashOverview;
