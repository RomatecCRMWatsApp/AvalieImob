// @module dashboard/novidades/NovidadesPage — Timeline pública interna de novidades (/novidades).
import React, { useState, useEffect, useMemo } from 'react';
import { ChevronDown, Search, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { novidadesAPI } from '../../../lib/api';
import { useAuth } from '../../../contexts/AuthContext';
import { Button } from '../../ui/button';
import { BrandSpinner } from '../../brand/BrandSpinner';
import MarkdownLite from './MarkdownLite';

const ehAdmin = (role) => ['admin', 'owner', 'ceo'].includes(String(role || '').toLowerCase());

const TAG = {
  novidade: { l: 'Novidade', c: 'bg-emerald-100 text-emerald-700' },
  melhoria: { l: 'Melhoria', c: 'bg-sky-100 text-sky-700' },
  correcao: { l: 'Correção', c: 'bg-amber-100 text-amber-700' },
  aviso: { l: 'Aviso', c: 'bg-red-100 text-red-600' },
};
const fmt = (iso) => { try { return iso ? new Date(iso).toLocaleDateString('pt-BR') : ''; } catch { return ''; } };

const NovidadesPage = () => {
  const nav = useNavigate();
  const { user } = useAuth();
  const [itens, setItens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tag, setTag] = useState('');
  const [q, setQ] = useState('');
  const [aberto, setAberto] = useState(null);

  useEffect(() => {
    novidadesAPI.historico().then((d) => setItens(Array.isArray(d) ? d : [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtrados = useMemo(() => itens.filter((n) =>
    (!tag || n.tag === tag) &&
    (!q || `${n.titulo} ${n.resumo}`.toLowerCase().includes(q.toLowerCase()))), [itens, tag, q]);

  const grupos = useMemo(() => {
    const m = new Map();
    filtrados.forEach((n) => { const v = n.versao || '—'; if (!m.has(v)) m.set(v, []); m.get(v).push(n); });
    return [...m.entries()];
  }, [filtrados]);

  if (loading) return <div className="py-20 flex justify-center"><BrandSpinner label="Carregando…" /></div>;

  return (
    <div className="max-w-3xl mx-auto pb-24 space-y-4">
      <div className="flex items-center justify-between">
        <div className="font-display text-2xl font-bold text-gray-900">Novidades</div>
        {ehAdmin(user?.role) && (
          <Button variant="outline" onClick={() => nav('/dashboard/admin/novidades')} className="gap-1 h-8 text-xs">
            <Settings className="w-3.5 h-3.5" /> Gerenciar
          </Button>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[180px]">
          <Search className="w-4 h-4 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar…"
            className="w-full pl-8 pr-3 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400" />
        </div>
        {['', 'novidade', 'melhoria', 'correcao', 'aviso'].map((t) => (
          <button key={t || 'todas'} type="button" onClick={() => setTag(t)}
            className={`px-3 py-1 rounded-full text-xs font-semibold border ${tag === t ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-600 border-gray-200'}`}>
            {t ? (TAG[t]?.l || t) : 'Todas'}
          </button>
        ))}
      </div>

      {grupos.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 p-10 text-center text-sm text-gray-400">Nenhuma novidade.</div>
      ) : grupos.map(([versao, lista]) => (
        <div key={versao}>
          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 mb-2">
            {versao !== '—' ? `Versão ${versao}` : 'Novidades'}
          </div>
          <div className="space-y-2 border-l-2 border-emerald-100 pl-4">
            {lista.map((n) => {
              const open = aberto === n.id;
              const tg = TAG[n.tag] || TAG.novidade;
              return (
                <div key={n.id} className="rounded-xl border border-gray-200 bg-white">
                  <button type="button" onClick={() => setAberto(open ? null : n.id)} className="w-full text-left p-3 flex items-start gap-2">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${tg.c} shrink-0`}>{tg.l}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-gray-800 text-sm">{n.titulo}</div>
                      {n.resumo && !open && <div className="text-[11px] text-gray-500 line-clamp-1">{n.resumo}</div>}
                    </div>
                    <span className="text-[10px] text-gray-400 shrink-0">{fmt(n.publicada_em)}</span>
                    <ChevronDown className={`w-4 h-4 text-gray-400 transition shrink-0 ${open ? 'rotate-180' : ''}`} />
                  </button>
                  {open && <div className="border-t border-gray-100 p-3"><MarkdownLite text={n.conteudo_md} /></div>}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

export default NovidadesPage;
