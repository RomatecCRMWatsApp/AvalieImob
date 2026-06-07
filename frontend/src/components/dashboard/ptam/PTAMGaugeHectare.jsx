// @module ptam/PTAMGaugeHectare — Gauge âmbar 96px com valor por hectare (PTAM rural).
// Preenche o arco proporcional ao VTI médio da tabela INCRA (se houver); senão 75% visual.
import React from 'react';

const RAIO = 40;
const CIRCUNFERENCIA = 2 * Math.PI * RAIO; // ~251.3

const fmtBRL0 = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(Number(v || 0));

export default function PTAMGaugeHectare({ valorTotal, areaHa, valorReferencia }) {
  const valorHa = areaHa > 0 ? Number(valorTotal || 0) / areaHa : 0;
  const percentual = valorReferencia && valorReferencia > 0
    ? Math.min((valorHa / valorReferencia) * 100, 100)
    : 75;
  const offset = CIRCUNFERENCIA - (percentual / 100) * CIRCUNFERENCIA;

  return (
    <div style={{ position: 'relative', width: 96, height: 96, flexShrink: 0 }}>
      <svg width="96" height="96" viewBox="0 0 96 96" style={{ position: 'absolute', top: 0, left: 0 }}>
        <circle cx="48" cy="48" r={RAIO} fill="none" stroke="#1a1505" strokeWidth="5" />
        <circle
          cx="48" cy="48" r={RAIO} fill="none" stroke="#f59e0b" strokeWidth="5"
          strokeDasharray={CIRCUNFERENCIA} strokeDashoffset={offset}
          strokeLinecap="round" transform="rotate(-90 48 48)"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 6,
      }}>
        <span style={{ fontSize: 8, color: '#94a3b8', textTransform: 'uppercase', lineHeight: 1.2 }}>
          Valor por<br />hectare
        </span>
        <span style={{ fontSize: 10, fontWeight: 600, color: '#f59e0b', margin: '2px 0', lineHeight: 1.2 }}>
          {fmtBRL0(valorHa)}
        </span>
        <span style={{ fontSize: 8, color: '#64748b' }}>/ ha</span>
      </div>
    </div>
  );
}
