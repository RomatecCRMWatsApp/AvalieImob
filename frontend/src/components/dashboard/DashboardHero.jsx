// @module dashboard/DashboardHero — Hero do Dashboard (design v4).
// Fundo verde escuro + textura blueprint + saudação dinâmica, credenciais,
// stats à direita e botões de ação.
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FilePlus2, UserPlus, BarChart2 } from 'lucide-react';

const CREDENCIAIS = 'CNAI 031161 · CRECI/MA 4.705 · CFT/MA 01209185369';

const HeroStat = ({ value, label, gold }) => (
  <div
    className="flex flex-col gap-0.5 rounded-lg px-4 py-3 min-w-[88px]"
    style={{ border: '1px solid rgba(201,168,76,0.2)', background: 'rgba(255,255,255,0.02)' }}
  >
    <span
      className="dash-display leading-none"
      style={{ fontSize: 26, color: gold ? 'var(--dash-gold)' : '#fff' }}
    >
      {value}
    </span>
    <span className="dash-eyebrow" style={{ fontSize: 9, color: 'rgba(255,255,255,0.45)' }}>
      {label}
    </span>
  </div>
);

const DashboardHero = ({ greeting, firstName, today, rascunhos, kpis }) => {
  const nav = useNavigate();

  return (
    <section
      className="relative overflow-hidden rounded-2xl"
      style={{ background: 'var(--dash-green-hero)', padding: 28 }}
    >
      {/* Textura blueprint (grid duplo 8px + 40px) */}
      <div className="dash-blueprint absolute inset-0 pointer-events-none" />

      {/* SVG decorativo de planta baixa (canto direito) */}
      <svg
        className="absolute top-0 right-0 h-full pointer-events-none hidden md:block"
        viewBox="0 0 220 200" width="320" fill="none"
        style={{ opacity: 0.06 }}
        aria-hidden="true"
      >
        <g stroke="var(--dash-gold)" strokeWidth="1.5">
          <rect x="20" y="20" width="180" height="160" />
          <line x1="110" y1="20" x2="110" y2="180" />
          <line x1="20" y1="100" x2="200" y2="100" />
          <rect x="34" y="34" width="60" height="50" />
          <rect x="124" y="34" width="62" height="50" />
          <rect x="34" y="116" width="60" height="50" />
          <rect x="124" y="116" width="62" height="50" />
          <line x1="60" y1="20" x2="60" y2="32" />
          <line x1="150" y1="180" x2="150" y2="168" />
        </g>
      </svg>

      <div className="relative flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
        {/* ── Texto ── */}
        <div className="min-w-0">
          <div className="dash-eyebrow" style={{ fontSize: 11, color: 'var(--dash-gold)' }}>
            Romatec Consultoria Total · Açailândia / MA
          </div>

          <h1 className="dash-display mt-2" style={{ fontSize: 26, color: '#fff', fontWeight: 500 }}>
            {greeting}, <span style={{ fontStyle: 'italic', color: 'var(--dash-gold)' }}>{firstName}.</span>
          </h1>

          <p className="mt-1 capitalize" style={{ color: 'rgba(255,255,255,0.35)', fontSize: 13 }}>
            {today}
            {rascunhos > 0 && (
              <span className="lowercase"> · {rascunhos} laudo{rascunhos > 1 ? 's' : ''} em rascunho</span>
            )}
          </p>

          <p className="mt-3" style={{ color: 'var(--dash-green-soft)', fontSize: 12, letterSpacing: '0.02em' }}>
            {CREDENCIAIS}
          </p>
        </div>

        {/* ── Stats à direita ── */}
        <div className="flex gap-3 flex-shrink-0">
          <HeroStat value={kpis.laudosTotal} label="Laudos" gold />
          <HeroStat value={kpis.clientes} label="Clientes" />
          <HeroStat value={kpis.imoveis} label="Imóveis" />
        </div>
      </div>

      {/* ── Ações ── */}
      <div
        className="relative mt-6 pt-5 flex flex-wrap gap-3"
        style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
      >
        <button
          onClick={() => nav('/dashboard/ptam')}
          className="flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-transform hover:-translate-y-0.5"
          style={{ background: 'var(--dash-gold)', color: 'var(--dash-text)' }}
        >
          <FilePlus2 className="w-4 h-4" /> Novo Laudo
        </button>
        <button
          onClick={() => nav('/dashboard/clientes')}
          className="flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-white/10"
          style={{ border: '1px solid rgba(255,255,255,0.2)' }}
        >
          <UserPlus className="w-4 h-4" /> Novo Cliente
        </button>
        <button
          onClick={() => nav('/dashboard/amostras')}
          className="flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-white/10"
          style={{ border: '1px solid rgba(255,255,255,0.2)' }}
        >
          <BarChart2 className="w-4 h-4" /> Nova Amostra
        </button>
      </div>
    </section>
  );
};

export default DashboardHero;
