// @module ptam/PTAMStatusBadge — Badge de status sobreposto no banner de foto do card.
import React from 'react';

const STATUS_STYLES = {
  rascunho:  { bg: 'rgba(38,38,38,0.85)', color: '#9ca3af', label: 'Rascunho' },
  concluido: { bg: 'rgba(26,74,42,0.9)',  color: '#4ade80', label: 'Concluído' },
  assinado:  { bg: 'rgba(26,42,74,0.9)',  color: '#60a5fa', label: 'Assinado' },
};

export default function PTAMStatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.rascunho;
  return (
    <span style={{
      background: s.bg, color: s.color, fontSize: 10, fontWeight: 600,
      padding: '3px 10px', borderRadius: 99, backdropFilter: 'blur(2px)',
      border: `1px solid ${s.color}33`,
    }}>
      {s.label}
    </span>
  );
}
