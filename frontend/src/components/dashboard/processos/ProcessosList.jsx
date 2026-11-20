// @module ProcessosList — processos de trabalho + próximos compromissos da agenda.
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, CalendarClock, Briefcase, X } from 'lucide-react';
import { processosAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';
import { fmtDataHora } from '../../../utils/datasServidor';

export const STATUS_COR = {
  aberto: 'bg-sky-100 text-sky-800',
  em_andamento: 'bg-amber-100 text-amber-800',
  aguardando_cliente: 'bg-purple-100 text-purple-800',
  concluido: 'bg-emerald-100 text-emerald-800',
  cancelado: 'bg-gray-200 text-gray-600',
};
export const AGENDA_STATUS = {
  agendado: 'Agendado', confirmado: 'Confirmado', realizado: 'Realizado', cancelado: 'Cancelado',
};
const F = 'w-full rounded-xl border border-gray-300 bg-white px-3 py-2.5 text-sm min-h-[44px]';

function NovoProcesso({ opcoes, onCriado, onFechar }) {
  const { toast } = useToast();
  const [f, setF] = useState({ titulo: '', tipo_servico: 'avaliacao', cliente_nome: '', responsavel: '', prazo: '' });
  const [salvando, setSalvando] = useState(false);
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const criar = async (e) => {
    e.preventDefault();
    if (!f.titulo.trim()) return toast({ title: 'Dê um título ao processo', variant: 'destructive' });
    setSalvando(true);
    try {
      const p = await processosAPI.criar({ ...f, prazo: f.prazo || null });
      onCriado(p);
    } catch (err) {
      toast({ title: 'Não foi possível criar', description: err?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setSalvando(false); }
  };
  return (
    <form onSubmit={criar} className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-[#0C3320]">Novo processo</h2>
        <button type="button" onClick={onFechar} aria-label="Fechar" className="w-9 h-9 rounded-lg hover:bg-gray-100 flex items-center justify-center"><X className="w-4 h-4" /></button>
      </div>
      <input className={F} placeholder="Título (ex.: Avaliação — Casa Rua São Raimundo)" value={f.titulo} onChange={set('titulo')} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <select className={F} value={f.tipo_servico} onChange={set('tipo_servico')}>
          {(opcoes?.tipos_servico || []).map((t) => <option key={t.id} value={t.id}>{t.rotulo}</option>)}
        </select>
        <input className={F} placeholder="Cliente" value={f.cliente_nome} onChange={set('cliente_nome')} />
        <input className={F} placeholder="Responsável" value={f.responsavel} onChange={set('responsavel')} />
        <label className="text-xs text-gray-500">Prazo de entrega
          <input type="date" className={F} value={f.prazo} onChange={set('prazo')} />
        </label>
      </div>
      <p className="text-xs text-gray-500">
        As etapas padrão do tipo escolhido já vêm prontas; dá para editar depois.
      </p>
      <button type="submit" disabled={salvando}
        className="rounded-xl bg-[#0C3320] text-white px-4 py-2.5 text-sm font-semibold disabled:opacity-60 min-h-[44px]">
        {salvando ? 'Criando…' : 'Criar processo'}
      </button>
    </form>
  );
}

export default function ProcessosList() {
  const nav = useNavigate();
  const [lista, setLista] = useState(null);
  const [agenda, setAgenda] = useState([]);
  const [opcoes, setOpcoes] = useState(null);
  const [status, setStatus] = useState('');
  const [q, setQ] = useState('');
  const [novo, setNovo] = useState(false);

  const carregar = useCallback(() => {
    processosAPI.listar({ status: status || undefined }).then(setLista).catch(() => setLista([]));
  }, [status]);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => {
    processosAPI.opcoes().then(setOpcoes).catch(() => {});
    processosAPI.agenda().then(setAgenda).catch(() => setAgenda([]));
  }, []);

  const termo = q.trim().toLowerCase();
  const filtrada = (lista || []).filter((p) => !termo || [p.numero, p.titulo, p.cliente_nome, p.responsavel]
    .join(' ').toLowerCase().includes(termo));
  const proximos = agenda.filter((c) => c.status !== 'cancelado' && c.status !== 'realizado').slice(0, 8);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="font-display text-[30px] font-bold leading-tight text-[#C9A84C]">Processos e agenda</h1>
          <p className="text-sm text-[#5B7466] dark:text-[#9FB5A6] mt-1">
            Acompanhe cada trabalho do início à entrega: etapas, prazos, vistorias agendadas e os documentos ligados a ele.
          </p>
        </div>
        <button type="button" onClick={() => setNovo(true)}
          className="inline-flex items-center gap-2 rounded-[10px] px-4 py-2.5 text-sm font-semibold bg-[#C9A84C] text-[#0C3320] hover:brightness-95 min-h-[44px]">
          <Plus className="w-4 h-4" /> Novo processo
        </button>
      </div>

      {novo && (
        <NovoProcesso opcoes={opcoes} onFechar={() => setNovo(false)}
          onCriado={(p) => nav(`/dashboard/processos/${p.id}`)} />
      )}

      <section className="rounded-2xl border border-gray-200 bg-white p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
          <CalendarClock className="w-4 h-4 text-emerald-700" /> Próximos compromissos (30 dias)
        </h2>
        {proximos.length === 0 ? (
          <p className="text-sm text-gray-500 mt-2">Nenhum compromisso agendado.</p>
        ) : (
          <ul className="mt-2 divide-y divide-gray-100">
            {proximos.map((c) => (
              <li key={c.id}>
                <button type="button" onClick={() => nav(`/dashboard/processos/${c.processo_id}`)}
                  className="w-full text-left py-2 flex flex-wrap items-baseline gap-x-3 gap-y-0.5 hover:bg-gray-50 rounded-lg px-1">
                  <span className="text-sm font-medium text-gray-900">{fmtDataHora(c.inicio)}</span>
                  <span className="text-sm text-gray-700">{opcoes?.agenda_tipos?.find((t) => t.id === c.tipo)?.rotulo || c.tipo}</span>
                  <span className="text-xs text-gray-500 break-words">{c.processo_titulo}{c.local ? ` · ${c.local}` : ''}</span>
                  <span className="text-xs text-gray-500">{AGENDA_STATUS[c.status]}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex gap-2 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input className={`${F} pl-9`} placeholder="Buscar processo, cliente…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <select className={`${F} w-auto`} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Situação">
            <option value="">Todas as situações</option>
            {(opcoes?.status || []).map((s) => <option key={s.id} value={s.id}>{s.rotulo}</option>)}
          </select>
        </div>
        {lista === null ? (
          <div className="py-10 flex justify-center"><BrandSpinner label="Carregando…" /></div>
        ) : filtrada.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
            <Briefcase className="w-6 h-6 mx-auto mb-2 text-gray-400" />
            {lista.length ? 'Nada encontrado com esse filtro.' : 'Nenhum processo ainda. Crie o primeiro.'}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {filtrada.map((p) => (
              <button key={p.id} type="button" onClick={() => nav(`/dashboard/processos/${p.id}`)}
                className="text-left rounded-xl border border-gray-200 bg-white p-4 hover:shadow-md transition">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-semibold text-emerald-700">{p.numero}</span>
                  <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COR[p.status] || ''}`}>{p.status_rotulo}</span>
                </div>
                <div className="font-semibold text-gray-900 mt-1 break-words">{p.titulo}</div>
                <div className="text-xs text-gray-500 mt-0.5 break-words">
                  {[p.cliente_nome, p.responsavel].filter(Boolean).join(' · ') || '—'}
                </div>
                <div className="mt-3 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div className="h-full bg-emerald-600" style={{ width: `${p.progresso}%` }} />
                </div>
                <div className="mt-1 flex justify-between text-xs text-gray-500">
                  <span>{p.progresso}% das etapas</span>
                  {p.prazo && <span>Prazo {p.prazo.split('-').reverse().join('/')}</span>}
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
