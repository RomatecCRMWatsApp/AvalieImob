import React, { useEffect, useState } from 'react';
import { FileText, Users, Building2, DollarSign, TrendingUp, Clock, Loader2 } from 'lucide-react';
import { dashboardAPI, evaluationsAPI, clientsAPI } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';

const Stat = ({ icon: Icon, label, value, delta, color = 'emerald' }) => (
  <div className="bg-white rounded-xl p-5 border border-gray-200">
    <div className="flex items-center justify-between mb-3">
      <div className={`w-10 h-10 rounded-lg bg-${color}-100 flex items-center justify-center`}><Icon className={`w-5 h-5 text-${color}-800`} /></div>
      {delta && <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1"><TrendingUp className="w-3 h-3" />{delta}</span>}
    </div>
    <div className="font-display text-3xl font-bold text-gray-900">{value}</div>
    <div className="text-xs text-gray-500 mt-1">{label}</div>
  </div>
);

const DashOverview = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([dashboardAPI.stats(), evaluationsAPI.list(), clientsAPI.list()]).then(([s, e, c]) => {
      setStats(s);
      setRecent(e.slice(0, 4));
      setClients(c);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const getClient = (id) => clients.find(c => c.id === id)?.name || '';

  if (loading || !stats) return <div className="py-20 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-emerald-800" /></div>;

  const maxM = Math.max(1, ...stats.monthly.map(m => m.count));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold text-gray-900">Bem-vindo, {user?.name?.split(' ')[0]}!</h1>
        <p className="text-gray-600 mt-1">Resumo da sua atividade no RomaTec AvalieImob.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat icon={FileText} label="Laudos emitidos" value={stats.evaluations} />
        <Stat icon={Users} label="Clientes cadastrados" value={stats.clients} />
        <Stat icon={Building2} label="Imóveis cadastrados" value={stats.properties} />
        <Stat icon={DollarSign} label="Volume avaliado" value={`R$ ${(stats.revenue * 100).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl p-6 border border-gray-200">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="font-display text-xl font-bold text-gray-900">Laudos por mês</h3>
              <p className="text-xs text-gray-500">Últimos 6 meses</p>
            </div>
          </div>
          <div className="flex items-end gap-3 h-48">
            {stats.monthly.map((m) => (
              <div key={m.month} className="flex-1 flex flex-col items-center gap-2">
                <div className="w-full flex-1 flex items-end">
                  <div className="w-full bg-gradient-to-t from-emerald-800 to-emerald-600 rounded-t-md transition-all hover:from-emerald-900" style={{ height: `${(m.count / maxM) * 100}%`, minHeight: m.count > 0 ? '8px' : '2px' }} title={m.count} />
                </div>
                <div className="text-xs font-medium text-gray-600">{m.month}</div>
                <div className="text-[10px] text-gray-400">{m.count}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 border border-gray-200">
          <h3 className="font-display text-xl font-bold text-gray-900 mb-1">Atividade recente</h3>
          <p className="text-xs text-gray-500 mb-5">Últimos laudos</p>
          <div className="space-y-4">
            {recent.length === 0 && <div className="text-sm text-gray-400">Nenhuma atividade ainda. Crie seu primeiro laudo!</div>}
            {recent.map(e => (
              <div key={e.id} className="flex gap-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center flex-shrink-0"><Clock className="w-4 h-4 text-emerald-800" /></div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-gray-900 truncate">{e.code}</div>
                  <div className="text-xs text-gray-500 truncate">{getClient(e.client_id)} · {e.type}</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">{e.date}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashOverview;
