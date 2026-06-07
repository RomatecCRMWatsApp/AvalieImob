// @module ptam/IncraTabelaSelector — Modal para escolher qual tabela INCRA usar no laudo.
// Lista todas as tabelas cadastradas (GET /incra/tabelas), com busca por região/fonte,
// preview resumido das faixas e seleção via radio. Botões: cadastrar nova / usar selecionada.
import React, { useEffect, useMemo, useState } from 'react';
import { X, Search, Plus, Loader2, CheckCircle2, RefreshCw } from 'lucide-react';
import { incraAPI } from '@/lib/api';

// "11230" -> "11,2k" ; "250000" -> "250k"
const fmtK = (v) => {
  const n = Number(v || 0);
  if (n >= 1000) {
    const k = n / 1000;
    return `${k.toLocaleString('pt-BR', { maximumFractionDigits: k < 100 ? 1 : 0 })}k`;
  }
  return n.toLocaleString('pt-BR', { maximumFractionDigits: 0 });
};

const nomeTabela = (t) =>
  [t.regiao, t.polo_regional || t.municipio].filter(Boolean).join(' / ') +
  (t.vigencia ? ` · ${t.vigencia}` : '');

const resumoFaixas = (t) => {
  const fx = Array.isArray(t.faixas) ? t.faixas : [];
  return fx
    .slice(0, 2)
    .map((f) => `${f.faixa}: ${fmtK(f.vr_min)}–${fmtK(f.vr_max)}`)
    .join(' · ') + (fx.length > 2 ? '…' : '');
};

export default function IncraTabelaSelector({ open, onClose, onUsar, currentId = null }) {
  const [tabelas, setTabelas] = useState([]);
  const [status, setStatus] = useState('loading'); // loading | ok | error
  const [busca, setBusca] = useState('');
  const [selId, setSelId] = useState(currentId);

  const carregar = () => {
    setStatus('loading');
    incraAPI
      .listar()
      .then((data) => { setTabelas(Array.isArray(data) ? data : []); setStatus('ok'); })
      .catch(() => setStatus('error'));
  };

  useEffect(() => {
    if (!open) return;
    setSelId(currentId);
    carregar();
  }, [open, currentId]);

  const filtradas = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (!q) return tabelas;
    return tabelas.filter((t) =>
      [t.regiao, t.polo_regional, t.municipio, t.fonte, t.vigencia]
        .filter(Boolean)
        .some((s) => String(s).toLowerCase().includes(q)),
    );
  }, [tabelas, busca]);

  if (!open) return null;

  const selecionada = tabelas.find((t) => t.id === selId) || null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">Selecionar Tabela INCRA</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Busca */}
        <div className="px-5 py-3 border-b border-gray-100">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por região ou fonte..."
              className="w-full pl-10 pr-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        {/* Lista */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2">
          {status === 'loading' && (
            <div className="py-10 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-600" /></div>
          )}
          {status === 'error' && (
            <div className="py-8 text-center text-sm text-red-600">Erro ao carregar tabelas.</div>
          )}
          {status === 'ok' && filtradas.length === 0 && (
            <div className="py-8 text-center text-sm text-gray-500">
              Nenhuma tabela {busca && 'para essa busca'}. Cadastre uma nova abaixo.
            </div>
          )}
          {status === 'ok' && filtradas.map((t) => {
            const ativa = t.id === selId;
            return (
              <label
                key={t.id}
                className={`block rounded-xl border p-3 cursor-pointer transition ${
                  ativa ? 'border-emerald-500 bg-emerald-50' : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="radio"
                    name="incra-tabela"
                    className="mt-1 accent-emerald-600"
                    checked={ativa}
                    onChange={() => setSelId(t.id)}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-sm text-gray-900">{nomeTabela(t)}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {t.fonte || '—'} · {(t.faixas?.length || 0)} faixa{(t.faixas?.length || 0) === 1 ? '' : 's'}
                    </div>
                    <div className="text-xs text-gray-400 mt-1 line-clamp-1">{resumoFaixas(t)}</div>
                  </div>
                  {t.id === currentId && (
                    <span className="text-[10px] uppercase font-semibold text-emerald-700 bg-emerald-100 rounded px-1.5 py-0.5 shrink-0">
                      em uso
                    </span>
                  )}
                </div>
              </label>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.open('/dashboard/admin/incra', '_blank')}
              className="text-sm text-emerald-700 hover:text-emerald-900 flex items-center gap-1"
            >
              <Plus className="w-4 h-4" /> Cadastrar nova tabela
            </button>
            <button onClick={carregar} title="Recarregar" className="text-gray-400 hover:text-gray-700">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <button
            disabled={!selecionada}
            onClick={() => selecionada && onUsar(selecionada)}
            className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-4 h-4" /> Usar selecionada
          </button>
        </div>
      </div>
    </div>
  );
}
