// @module ptam/PTAMStatusCircle — Círculo SVG 72px de status do PTAM (verde/azul/âmbar).
// concluido = anel verde completo · assinado = anel azul completo · rascunho = anel âmbar
// proporcional ao progresso (%). Texto central: rótulo + status + sub (data/hora ou %).
import React from 'react';

const RAIO = 30;
const CIRCUNFERENCIA = 2 * Math.PI * RAIO; // ~188.5

function formatarDataCurta(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const data = d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  const hora = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return `${data} · ${hora}`;
}

export default function PTAMStatusCircle({ status, dataAtualizacao, progressoPercent = 0 }) {
  const calcOffset = (pct) => CIRCUNFERENCIA - (Math.max(0, Math.min(100, pct)) / 100) * CIRCUNFERENCIA;

  const config = {
    concluido: {
      cor: '#4ade80', corFundo: '#1a2e1a', offset: 0,
      label: 'Última atualização', texto: 'CONCLUÍDO', corTexto: '#4ade80',
      sub: formatarDataCurta(dataAtualizacao),
    },
    assinado: {
      cor: '#60a5fa', corFundo: '#0a1a2e', offset: 0,
      label: 'Status', texto: 'ASSINADO', corTexto: '#60a5fa',
      sub: formatarDataCurta(dataAtualizacao),
    },
    rascunho: {
      cor: '#f59e0b', corFundo: '#1a1505', offset: calcOffset(progressoPercent),
      label: 'Laudo', texto: 'EM ANDAMENTO', corTexto: '#f59e0b',
      sub: `${Math.round(progressoPercent)}%`,
    },
  };

  const c = config[status] || config.rascunho;

  return (
    <div style={{ position: 'relative', width: 72, height: 72, flexShrink: 0 }}>
      <svg width="72" height="72" viewBox="0 0 72 72" style={{ position: 'absolute', top: 0, left: 0 }}>
        <circle cx="36" cy="36" r={RAIO} fill="none" stroke={c.corFundo} strokeWidth="5" />
        <circle
          cx="36" cy="36" r={RAIO} fill="none" stroke={c.cor} strokeWidth="5"
          strokeDasharray={CIRCUNFERENCIA} strokeDashoffset={c.offset}
          strokeLinecap="round" transform="rotate(-90 36 36)"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 4,
      }}>
        <span style={{ fontSize: 7, color: '#94a3b8', lineHeight: 1.2, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
          {c.label}
        </span>
        <span style={{ fontSize: 8, fontWeight: 600, color: c.corTexto, lineHeight: 1.2, margin: '2px 0' }}>
          {c.texto}
        </span>
        {c.sub ? <span style={{ fontSize: 7, color: '#94a3b8' }}>{c.sub}</span> : null}
      </div>
    </div>
  );
}
