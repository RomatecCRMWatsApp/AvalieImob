// @module overview/StatCard — Card de estatística do dashboard
import React from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, ChevronRight } from 'lucide-react';

export const GOLD = '#D4A830';
export const DARK_GREEN = '#1B4D1B';

export const StatCard = ({ icon: Icon, label, value, iconBg, iconColor, delta, href }) => (
  <Link
    to={href || '#'}
    className="group bg-white rounded-2xl p-5 border border-gray-100 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 block"
  >
    <div className="flex items-start justify-between mb-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${iconBg}`}>
        <Icon className={`w-5 h-5 ${iconColor}`} />
      </div>
      {delta !== undefined && (
        <span className="flex items-center gap-0.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-1 rounded-full">
          <TrendingUp className="w-3 h-3" />{delta}
        </span>
      )}
    </div>
    <div className="font-display text-3xl font-bold text-gray-900 leading-tight">{value}</div>
    <div className="flex items-center justify-between mt-1">
      <span className="text-xs text-gray-500 font-medium">{label}</span>
      <ChevronRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-gray-500 group-hover:translate-x-0.5 transition-all" />
    </div>
  </Link>
);

export const Shortcut = ({ icon: Icon, label, to, accent }) => (
  <Link
    to={to}
    className={`flex items-center gap-3 px-4 py-3 rounded-xl border text-sm font-semibold transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 ${accent ? 'border-transparent text-white' : 'bg-white border-gray-200 text-gray-700 hover:border-emerald-200 hover:text-emerald-800'}`}
    style={accent ? { background: DARK_GREEN } : {}}
  >
    <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${accent ? 'bg-white/15' : 'bg-gray-100'}`}>
      <Icon className={`w-4 h-4 ${accent ? 'text-white' : 'text-gray-600'}`} />
    </div>
    {label}
    <span className="ml-auto opacity-60 text-xs">↗</span>
  </Link>
);

export const BarCol = ({ m, pct, isMax }) => (
  <div className="flex-1 flex flex-col items-center gap-2 group">
    <div className="text-[10px] font-semibold text-gray-500 group-hover:text-gray-800 transition-colors">{m.count}</div>
    <div className="w-full flex-1 flex items-end">
      <div
        className="w-full rounded-t-lg transition-all duration-700"
        style={{
          height: `${pct}%`,
          minHeight: m.count > 0 ? '6px' : '2px',
          background: isMax
            ? `linear-gradient(to top, ${DARK_GREEN}, #2d7a2d)`
            : `linear-gradient(to top, ${GOLD}aa, ${GOLD})`,
        }}
      />
    </div>
    <div className="text-xs font-medium text-gray-500">{m.month}</div>
  </div>
);
