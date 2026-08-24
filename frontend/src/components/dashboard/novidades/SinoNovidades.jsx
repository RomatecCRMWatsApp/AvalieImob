// @module dashboard/novidades/SinoNovidades — Dropdown do sino (últimas novidades).
import React from 'react';
import { X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const TAG_DOT = { novidade: '#10b981', melhoria: '#0ea5e9', correcao: '#f59e0b', aviso: '#ef4444' };
// Backend grava naive em UTC — sem marcar o fuso, "há 3 min" viraria data futura.
const comoUTC = (v) => (typeof v === 'string' && !/([Zz]|[+-]\d{2}:?\d{2})$/.test(v)
  ? new Date(`${v}Z`) : new Date(v));
const rel = (iso) => {
  try {
    const s = (Date.now() - comoUTC(iso).getTime()) / 1000;
    if (s < 60) return 'agora';
    if (s < 3600) return `${Math.max(1, Math.floor(s / 60))}min`;
    if (s < 86400) return `${Math.floor(s / 3600)}h`;
    return `${Math.floor(s / 86400)}d`;
  } catch { return ''; }
};

const SinoNovidades = ({ open, onClose, itens }) => {
  const nav = useNavigate();
  if (!open) return null;
  const lista = (itens || []).slice(0, 10);
  return (
    <>
      <div className="fixed inset-0 z-[55]" onClick={onClose} />
      <div className="fixed z-[56] top-14 right-3 w-80 max-w-[calc(100vw-24px)] bg-white rounded-xl shadow-2xl border border-gray-100 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-gray-100 flex items-center justify-between">
          <span className="font-semibold text-sm text-gray-800">Novidades</span>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X className="w-4 h-4" /></button>
        </div>
        <div className="max-h-80 overflow-y-auto">
          {lista.length === 0 ? (
            <div className="p-6 text-center text-xs text-gray-400">Nenhuma novidade.</div>
          ) : lista.map((n) => (
            <div key={n.id} className={`px-4 py-2.5 border-b border-gray-50 ${n.lida ? 'opacity-60' : ''}`}>
              <div className="flex items-center gap-2">
                <span style={{ background: TAG_DOT[n.tag] || '#10b981' }} className="w-1.5 h-1.5 rounded-full shrink-0" />
                <span className="text-[13px] font-medium text-gray-800 flex-1 truncate">{n.titulo}</span>
                <span className="text-[10px] text-gray-400 shrink-0">{rel(n.publicada_em)}</span>
              </div>
              {n.resumo && <div className="text-[11px] text-gray-500 mt-0.5 ml-3.5 line-clamp-2">{n.resumo}</div>}
            </div>
          ))}
        </div>
        <button onClick={() => { onClose(); nav('/dashboard/novidades'); }}
          className="w-full py-2.5 text-[12px] font-semibold text-emerald-700 hover:bg-emerald-50 border-t border-gray-100">
          Ver todas as novidades
        </button>
      </div>
    </>
  );
};

export default SinoNovidades;
