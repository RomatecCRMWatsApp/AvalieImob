// @module components/common/LgpdBadge — selo "CERTIFICADO LGPD"
// Sinaliza ao visitante que o sistema esta em conformidade com a LGPD
// (Lei 13.709/2018). Aparece no Footer e em paginas de cadastro.
import React from 'react';
import { Lock } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function LgpdBadge({ size = 'md', className = '' }) {
  const sizes = {
    sm: { box: 'w-24 h-12', icon: 'w-5 h-5', sigla: 'text-base', cert: 'text-[8px]' },
    md: { box: 'w-32 h-16', icon: 'w-6 h-6', sigla: 'text-xl', cert: 'text-[9px]' },
    lg: { box: 'w-40 h-20', icon: 'w-7 h-7', sigla: 'text-2xl', cert: 'text-[10px]' },
  };
  const s = sizes[size] || sizes.md;

  return (
    <Link
      to="/privacidade"
      title="Sistema em conformidade com a LGPD — Lei 13.709/2018"
      className={`inline-flex items-center gap-2 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow px-3 py-2 ${s.box} ${className}`}
    >
      <div className="flex items-center justify-center bg-emerald-500 rounded-md p-1.5 flex-shrink-0">
        <Lock className={`${s.icon} text-white`} strokeWidth={2.5} />
      </div>
      <div className="flex flex-col leading-none">
        <span className={`${s.cert} font-semibold tracking-[0.15em] text-gray-500 uppercase`}>Certificado</span>
        <span className={`${s.sigla} font-extrabold text-emerald-600 tracking-tight`}>LGPD</span>
      </div>
    </Link>
  );
}
