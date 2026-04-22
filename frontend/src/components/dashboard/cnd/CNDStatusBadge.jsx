import React from 'react';
import { CheckCircle, AlertTriangle, XCircle, MinusCircle } from 'lucide-react';

const STATUS_CONFIG = {
  negativa: {
    label: 'Negativa',
    className: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    Icon: CheckCircle,
  },
  positiva: {
    label: 'Positiva',
    className: 'bg-yellow-50 text-yellow-700 border border-yellow-200',
    Icon: AlertTriangle,
  },
  erro: {
    label: 'Erro',
    className: 'bg-red-50 text-red-700 border border-red-200',
    Icon: XCircle,
  },
  indisponivel: {
    label: 'Indisponível',
    className: 'bg-gray-100 text-gray-500 border border-gray-200',
    Icon: MinusCircle,
  },
  processando: {
    label: 'Processando',
    className: 'bg-blue-50 text-blue-600 border border-blue-200',
    Icon: null,
  },
};

export default function CNDStatusBadge({ status, small = false }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.indisponivel;
  const { Icon } = cfg;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${
        small ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1'
      } ${cfg.className}`}
    >
      {status === 'processando' ? (
        <span className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      ) : Icon ? (
        <Icon className={small ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      ) : null}
      {cfg.label}
    </span>
  );
}
