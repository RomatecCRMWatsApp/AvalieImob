// @module DashOverview — Visão geral do dashboard (layout + dados)
import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText, Users, Building2, DollarSign, Clock,
  Loader2, Plus, BarChart2, CreditCard, Calendar, CheckCircle,
  AlertCircle, Zap
} from 'lucide-react';
import { dashboardAPI, evaluationsAPI, clientsAPI, paymentsAPI } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';
import { PLANS } from '../../mock/mock';
import { StatCard, Shortcut, BarCol, GOLD, DARK_GREEN } from './overview/widgets';

const EVAL_STATUS = {
  'Emitido':      'bg-emerald-100 text-emerald-800',
  'Em revisão':   'bg-amber-100 text-amber-800',
  'Em andamento': 'bg-blue-100 text-blue-800',
  'Rascunho':     'bg-gray-100 text-gray-600',
};

const SUB_STATUS = {
  active:   { label: 'Ativo',    bg: 'bg-emerald-100', text: 'text-emerald-800', Icon: CheckCircle },
  inactive: { label: 'Inativo',  bg: 'bg-gray-100',    text: 'text-gray-600',    Icon: AlertCircle },
  expired:  { label: 'Expirado', bg: 'bg-red-100',     text: 'text-red-700',     Icon: AlertCircle },
  pending:  { label: 'Pendente', bg: 'bg-amber-100',   text: 'text-amber-700',   Icon: Clock },
};

const DashOverview = () => {
  const { user } = useAuth();
  const [stats, setStats]         = useState(null);
  const [recent, setRecent]       = useState([]);
  const [clients, setClients]     = useState([]);
  const [payStatus, setPayStatus] = useState(null);
  const [loading, setLoading]     = useState(true);

  const loadAll = useCallback(() => {
    Promise.all([
      dashboardAPI.stats(),
      evaluationsAPI.list(),
      clientsAPI.list(),
      paymentsAPI.status().catch(() => null),
    ]).then(([s, e, c, pay]) => {
      setStats(s);
      setRecent(e.slice(0, 5));
      setClients(c);
      setPayStatus(pay);
    })
    .catch(err => console.warn('Failed to load dashboard', err))
    .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const getClient = (id) => clients.find(c => c.id === id)?.name || '—';

  if (loading || !stats) {
    return (
      <div className="py-24 flex justify-center">
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: DARK_GREEN }} />
      </div>
    );
  }

  const maxM   = Math.max(1, ...stats.monthly.map(m => m.count));
  const maxIdx = stats.monthly.findIndex(m => m.count === maxM);

  const planSt    = payStatus?.plan_status || 'inactive';
  const subInfo   = SUB_STATUS[planSt] || SUB_STATUS.inactive;
  const SubIcon   = subInfo.Icon;
  const planLabel = payStatus?.plan || user?.plan || 'Mensal';
  const planObj   = PLANS.find(p => p.name.toLowerCase() === planLabel?.toLowerCase() || p.id.toLowerCase() === planLabel?.toLowerCase());
  const planExpires = payStatus?.plan_expires ? new Date(payStatus.plan_expires).toLocaleDateString('pt-BR') : null;
  const firstName = user?.name?.split(' ')[0] || 'Avaliador';

  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-gray-900 leading-tight">Bom dia, {firstName}!</h1>
          <p className="text-gray-500 mt-1 text-sm">Aqui está o resumo da sua atividade hoje.</p>
        </div>
        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-xl px-4 py-2.5 shadow-sm self-start sm:self-auto">
          <div className="w-2 h-2 rounded-full" style={{ background: planSt === 'active' ? '#16a34a' : '#6b7280' }} />
          <span className="text-xs font-semibold text-gray-700 capitalize">{planLabel}</span>
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${subInfo.bg} ${subInfo.text}`}>{subInfo.label}</span>
          {planExpires && (
            <span className="hidden sm:flex items-center gap-1 text-[10px] text-gray-400">
              <Calendar className="w-3 h-3" /> {planExpires}
            </span>
          )}
        </div>
      </div>

      {/* Quick shortcuts */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Shortcut icon={Plus}      label="Novo Laudo"   to="/dashboard/ptam"     accent />
        <Shortcut icon={Users}     label="Novo Cliente" to="/dashboard/clientes" />
        <Shortcut icon={BarChart2} label="Nova Amostra" to="/dashboard/amostras" />
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={FileText}  label="Laudos emitidos" value={stats.evaluations} iconBg="bg-emerald-100" iconColor="text-emerald-800" delta="+12%" href="/dashboard/ptam" />
        <StatCard icon={Users}     label="Clientes"        value={stats.clients}     iconBg="bg-blue-100"    iconColor="text-blue-700"   href="/dashboard/clientes" />
        <StatCard icon={Building2} label="Imóveis"         value={stats.properties}  iconBg="bg-violet-100"  iconColor="text-violet-700" href="/dashboard/imoveis" />
        <StatCard icon={DollarSign} label="Volume avaliado" value={`R$ ${(stats.revenue).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`} iconBg="bg-amber-100" iconColor="text-amber-700" delta="+8%" href="/dashboard/laudos" />
      </div>

      {/* Chart + Activity */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="font-display text-lg font-bold text-gray-900">Laudos por mês</h3>
              <p className="text-xs text-gray-400 mt-0.5">Últimos 6 meses</p>
            </div>
            <div className="flex items-center gap-3 text-[10px] font-semibold text-gray-500">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm inline-block" style={{ background: GOLD }} />Regular</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm inline-block" style={{ background: DARK_GREEN }} />Pico</span>
            </div>
          </div>
          <div className="flex items-end gap-3 h-44">
            {stats.monthly.map((m, i) => (
              <BarCol key={m.month} m={m} pct={(m.count / maxM) * 100} isMax={i === maxIdx} />
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="font-display text-lg font-bold text-gray-900">Atividade recente</h3>
              <p className="text-xs text-gray-400 mt-0.5">Últimos laudos</p>
            </div>
            <Link to="/dashboard/ptam" className="text-xs font-semibold hover:underline transition-colors" style={{ color: DARK_GREEN }}>Ver todos</Link>
          </div>

          {recent.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-8 gap-3">
              <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
                <FileText className="w-5 h-5 text-gray-400" />
              </div>
              <p className="text-sm text-gray-400">Nenhuma atividade ainda.</p>
              <Link to="/dashboard/ptam" className="text-xs font-semibold px-3 py-1.5 rounded-lg text-white" style={{ background: DARK_GREEN }}>Criar primeiro laudo</Link>
            </div>
          ) : (
            <div className="relative flex-1">
              <div className="absolute left-[17px] top-2 bottom-2 w-px bg-gray-100" />
              <div className="space-y-4">
                {recent.map((e, i) => {
                  const statusCls = EVAL_STATUS[e.status] || 'bg-gray-100 text-gray-600';
                  return (
                    <div key={e.id} className="flex gap-3 relative">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border-2 border-white shadow-sm z-10" style={{ background: i === 0 ? GOLD : '#f3f4f6' }}>
                        <Clock className={`w-3.5 h-3.5 ${i === 0 ? 'text-white' : 'text-gray-400'}`} />
                      </div>
                      <div className="flex-1 min-w-0 pb-1">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <span className="text-sm font-semibold text-gray-900 truncate">{e.code}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap ${statusCls}`}>{e.status}</span>
                        </div>
                        <div className="text-xs text-gray-500 truncate mt-0.5">{getClient(e.client_id)}</div>
                        <div className="text-[10px] text-gray-400 mt-0.5">{e.date}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Subscription card */}
      <div className="rounded-2xl p-6 text-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4" style={{ background: `linear-gradient(135deg, ${DARK_GREEN} 0%, #2a7a2a 100%)` }}>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.12)' }}>
            <CreditCard className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="text-xs text-emerald-200 uppercase tracking-wider mb-0.5 font-semibold">Plano atual</div>
            <div className="font-display text-xl font-bold capitalize">{planLabel}</div>
            {planObj && <div className="text-xs text-emerald-200 mt-0.5">{planObj.features[0]} · {planObj.features[1]}</div>}
          </div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`text-xs font-bold px-3 py-1.5 rounded-full flex items-center gap-1.5 ${subInfo.bg} ${subInfo.text}`}><SubIcon className="w-3.5 h-3.5" />{subInfo.label}</span>
          {planExpires && <span className="text-xs text-emerald-200 flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Expira {planExpires}</span>}
          <Link to="/dashboard/assinatura" className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-90" style={{ background: GOLD, color: '#1a1a1a' }}>
            <Zap className="w-3.5 h-3.5" /> Gerenciar plano
          </Link>
        </div>
      </div>
    </div>
  );
};

export default DashOverview;
