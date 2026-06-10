// @module pages/admin/UsuariosAdmin — Lista de usuários cadastrados + assinaturas (admin).
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Users, Loader2, Search, CheckCircle2, Clock, AlertCircle, ShieldCheck, RefreshCw } from 'lucide-react';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { useToast } from '../../hooks/use-toast';
import { adminAPI } from '../../lib/api';

const fmtData = (v) => (v ? new Date(v).toLocaleDateString('pt-BR') : '—');

const PLAN_STATUS = {
  active:   { label: 'Ativa',    cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', Icon: CheckCircle2 },
  inactive: { label: 'Inativa',  cls: 'bg-gray-100 text-gray-500 border-gray-200',          Icon: AlertCircle },
  expired:  { label: 'Expirada', cls: 'bg-amber-50 text-amber-700 border-amber-200',         Icon: Clock },
  pending:  { label: 'Pendente', cls: 'bg-blue-50 text-blue-700 border-blue-200',            Icon: Clock },
};

const StatCard = ({ label, value, accent, Icon }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
    <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: `${accent}1A` }}>
      <Icon className="w-5 h-5" style={{ color: accent }} />
    </div>
    <div>
      <div className="font-display text-2xl font-bold text-gray-900 leading-none">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  </div>
);

const UsuariosAdmin = () => {
  const { toast } = useToast();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [filtro, setFiltro] = useState('todos');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminAPI.listUsers();
      setUsers(Array.isArray(data) ? data : []);
    } catch (e) {
      toast({ title: 'Erro ao carregar usuários', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const stats = useMemo(() => {
    const total = users.length;
    const ativas = users.filter((u) => u.plan_status === 'active').length;
    const inativas = users.filter((u) => u.plan_status !== 'active').length;
    const admins = users.filter((u) => ['admin', 'owner', 'ceo'].includes(String(u.role || '').toLowerCase())).length;
    return { total, ativas, inativas, admins };
  }, [users]);

  const filtrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return users.filter((u) => {
      if (filtro === 'ativas' && u.plan_status !== 'active') return false;
      if (filtro === 'inativas' && u.plan_status === 'active') return false;
      if (!q) return true;
      return (u.name || '').toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q);
    });
  }, [users, busca, filtro]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold text-emerald-900 flex items-center gap-2">
            <Users className="w-6 h-6" /> Usuários
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">Usuários cadastrados e status das assinaturas.</p>
        </div>
        <Button variant="outline" onClick={load} className="gap-1 self-start"><RefreshCw className="w-4 h-4" /> Atualizar</Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Cadastrados"        value={stats.total}    accent="#1E6B38" Icon={Users} />
        <StatCard label="Assinaturas ativas" value={stats.ativas}   accent="#C9A84C" Icon={CheckCircle2} />
        <StatCard label="Inativas/Expiradas" value={stats.inativas} accent="#6B8072" Icon={AlertCircle} />
        <StatCard label="Administradores"    value={stats.admins}   accent="#2E8B57" Icon={ShieldCheck} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
          <option value="todos">Todos</option>
          <option value="ativas">Assinatura ativa</option>
          <option value="inativas">Inativas/Expiradas</option>
        </select>
        <div className="relative max-w-xs flex-1">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome ou e-mail..." className="pl-9" />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        {loading ? (
          <div className="py-16 flex justify-center"><Loader2 className="w-7 h-7 animate-spin text-emerald-700" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-100">
                <th className="text-left py-3 px-4">Nome</th>
                <th className="text-left py-3 px-4">E-mail</th>
                <th className="text-left py-3 px-4">Plano</th>
                <th className="text-left py-3 px-4">Assinatura</th>
                <th className="text-left py-3 px-4">Validade</th>
                <th className="text-left py-3 px-4">Cadastro</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((u) => {
                const st = PLAN_STATUS[u.plan_status] || PLAN_STATUS.inactive;
                const isAdmin = ['admin', 'owner', 'ceo'].includes(String(u.role || '').toLowerCase());
                return (
                  <tr key={u.id} className="border-t border-gray-100 hover:bg-emerald-50/30">
                    <td className="py-3 px-4 font-semibold text-gray-800">
                      {u.name || '—'}
                      {isAdmin && <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-amber-600">admin</span>}
                    </td>
                    <td className="py-3 px-4 text-gray-600">{u.email}</td>
                    <td className="py-3 px-4 text-gray-600 capitalize">{u.plan || '—'}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${st.cls}`}>
                        <st.Icon className="w-3 h-3" /> {st.label}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs text-gray-500">{fmtData(u.plan_expires)}</td>
                    <td className="py-3 px-4 text-xs text-gray-500">{fmtData(u.created_at)}</td>
                  </tr>
                );
              })}
              {filtrados.length === 0 && (
                <tr><td colSpan={6} className="text-center py-10 text-gray-400">Nenhum usuário encontrado</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default UsuariosAdmin;
