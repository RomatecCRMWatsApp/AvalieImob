// @module pages/admin/UsuariosAdmin — Usuários + auditoria de acesso e pagamento (admin).
// O badge de "Funil" é DIAGNÓSTICO: descreve em que etapa o usuário parou.
// Quem decide acesso continua sendo `plan_status` (coluna Assinatura).
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Users, Loader2, Search, CheckCircle2, Clock, AlertCircle, ShieldCheck,
  RefreshCw, Trash2, X, LogIn, CreditCard, UserX, ShoppingCart,
} from 'lucide-react';
import { BrandSpinner } from '../../components/brand/BrandSpinner';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { useToast } from '../../hooks/use-toast';
import { useAuth } from '../../contexts/AuthContext';
import { adminAPI } from '../../lib/api';

// O backend grava datetime NAIVE em UTC (datetime.utcnow(), padrão do repo) e
// serializa sem sufixo de fuso. `new Date("...T16:10:00")` sem fuso é lido pelo
// JS como horário LOCAL — o que exibiria 16:10 em vez de 13:10 aqui (UTC-3).
// Este helper marca a string como UTC antes de converter.
const comoUTC = (v) => {
  if (!v) return null;
  if (typeof v === 'string' && !/([Zz]|[+-]\d{2}:?\d{2})$/.test(v)) return new Date(`${v}Z`);
  return new Date(v);
};

const fmtData = (v) => {
  const d = comoUTC(v);
  return d ? d.toLocaleDateString('pt-BR') : '—';
};
const fmtDataHora = (v) => {
  const d = comoUTC(v);
  return d ? d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';
};

const PLAN_STATUS = {
  active:   { label: 'Ativa',    cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', Icon: CheckCircle2 },
  inactive: { label: 'Inativa',  cls: 'bg-gray-100 text-gray-500 border-gray-200',         Icon: AlertCircle },
  expired:  { label: 'Expirada', cls: 'bg-amber-50 text-amber-700 border-amber-200',       Icon: Clock },
  pending:  { label: 'Pendente', cls: 'bg-blue-50 text-blue-700 border-blue-200',          Icon: Clock },
};

// Etapa do funil — diagnóstico, não permissão.
const FUNIL = {
  never_started:      { label: 'Nunca iniciou',     cls: 'bg-gray-100 text-gray-500 border-gray-200' },
  checkout_started:   { label: 'Iniciou pagamento', cls: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  payment_pending:    { label: 'Pgto. pendente',    cls: 'bg-orange-50 text-orange-700 border-orange-200' },
  active:             { label: 'Ativo',             cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  expired:            { label: 'Expirado',          cls: 'bg-red-50 text-red-800 border-red-200' },
  blocked_no_payment: { label: 'Sem pagamento',     cls: 'bg-red-100 text-red-700 border-red-300' },
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

/** Painel lateral com a linha do tempo de acessos e pagamentos do usuário. */
const TimelineDrawer = ({ alvo, onClose }) => {
  const { toast } = useToast();
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let vivo = true;
    (async () => {
      setCarregando(true);
      try {
        const d = await adminAPI.userTimeline(alvo.id);
        if (vivo) setDados(d);
      } catch (e) {
        toast({ title: 'Erro ao carregar histórico', description: e.response?.data?.detail, variant: 'destructive' });
      } finally { if (vivo) setCarregando(false); }
    })();
    return () => { vivo = false; };
  }, [alvo.id, toast]);

  const acessos = dados?.acessos || [];
  const pagamentos = dados?.pagamentos || [];

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white w-full max-w-md h-full overflow-y-auto shadow-xl">
        <div className="sticky top-0 bg-emerald-900 text-white px-5 py-4 flex items-start justify-between">
          <div>
            <div className="font-display font-bold">{alvo.name || '—'}</div>
            <div className="text-xs text-emerald-200">{alvo.email}</div>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded"><X className="w-5 h-5" /></button>
        </div>

        {carregando ? (
          <div className="py-16 flex justify-center"><BrandSpinner label="Carregando…" /></div>
        ) : (
          <div className="p-5 space-y-6">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-gray-500">Último acesso</div>
                <div className="font-semibold text-gray-800 mt-0.5">{fmtDataHora(alvo.ultimo_acesso)}</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-gray-500">Total de logins</div>
                <div className="font-semibold text-gray-800 mt-0.5">{alvo.total_acessos ?? 0}</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 col-span-2">
                <div className="text-gray-500">Checkout iniciado em</div>
                <div className="font-semibold text-gray-800 mt-0.5">{fmtDataHora(alvo.checkout_iniciado_em)}</div>
              </div>
            </div>

            <section>
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5 mb-2">
                <CreditCard className="w-3.5 h-3.5" /> Pagamentos ({pagamentos.length})
              </h3>
              {pagamentos.length === 0 ? (
                <p className="text-xs text-gray-400 italic">Nenhum evento de pagamento registrado.</p>
              ) : (
                <ul className="space-y-2">
                  {pagamentos.map((p, i) => (
                    <li key={p.id || p.mp_payment_id + p.status + i} className="border border-gray-200 rounded-lg p-3 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-gray-800">{p.status || '—'}</span>
                        <span className="text-gray-400">{fmtDataHora(p.received_at)}</span>
                      </div>
                      {p.status_detail && (
                        <div className="text-gray-500 mt-1 font-mono text-[10px]">{p.status_detail}</div>
                      )}
                      <div className="text-gray-400 mt-1">
                        MP #{p.mp_payment_id}
                        {p.transaction_amount != null && ` · R$ ${Number(p.transaction_amount).toFixed(2)}`}
                        {p.plan_id && ` · ${p.plan_id}`}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5 mb-2">
                <LogIn className="w-3.5 h-3.5" /> Acessos ({acessos.length})
              </h3>
              {acessos.length === 0 ? (
                <p className="text-xs text-gray-400 italic">Nenhum acesso registrado ainda.</p>
              ) : (
                <ul className="space-y-1.5">
                  {acessos.map((a, i) => (
                    <li key={a.id || i} className="flex items-center justify-between text-xs border-b border-gray-50 pb-1.5">
                      <span className={a.event === 'login' ? 'font-semibold text-emerald-700' : 'text-gray-500'}>
                        {a.event === 'login' ? 'Login' : 'Sessão ativa'}
                      </span>
                      <span className="text-gray-400">{fmtDataHora(a.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-[10px] text-gray-400 mt-2">
                Registros de sessão são mantidos por 90 dias; logins são permanentes.
              </p>
            </section>
          </div>
        )}
      </div>
    </div>
  );
};

const UsuariosAdmin = () => {
  const { toast } = useToast();
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [filtro, setFiltro] = useState('todos');
  const [deleting, setDeleting] = useState({});
  const [bulkLoading, setBulkLoading] = useState(false);
  const [detalhe, setDetalhe] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminAPI.usersAudit();
      setUsers(Array.isArray(data) ? data : []);
    } catch (e) {
      toast({ title: 'Erro ao carregar usuários', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const excluir = async (u) => {
    if (!window.confirm(`Excluir o usuário ${u.name || u.email}? Esta ação não pode ser desfeita.`)) return;
    setDeleting((p) => ({ ...p, [u.id]: true }));
    try {
      await adminAPI.excluirUsuario(u.id);
      setUsers((prev) => prev.filter((x) => x.id !== u.id));
      toast({ title: 'Usuário excluído' });
    } catch (e) {
      toast({ title: 'Erro ao excluir', description: e.response?.data?.detail, variant: 'destructive' });
    } finally {
      setDeleting((p) => ({ ...p, [u.id]: false }));
    }
  };

  const excluirInativos = async () => {
    if (!window.confirm('Excluir TODOS os usuários sem assinatura ativa? (não inclui a sua conta)')) return;
    setBulkLoading(true);
    try {
      const r = await adminAPI.excluirInativos();
      toast({ title: `${r.excluidos ?? 0} usuário(s) inativo(s) excluído(s)` });
      load();
    } catch (e) {
      toast({ title: 'Erro ao excluir inativos', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setBulkLoading(false); }
  };

  const stats = useMemo(() => {
    const total = users.length;
    const ativas = users.filter((u) => u.plan_status === 'active').length;
    const nuncaAcessaram = users.filter((u) => u.nunca_acessou).length;
    // "Quase converteu": iniciou o checkout e não há NENHUM evento de pagamento.
    const abandonaram = users.filter((u) => u.status_funil === 'checkout_started').length;
    const admins = users.filter((u) => ['admin', 'owner', 'ceo'].includes(String(u.role || '').toLowerCase())).length;
    return { total, ativas, nuncaAcessaram, abandonaram, admins };
  }, [users]);

  const filtrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return users.filter((u) => {
      if (filtro === 'ativas' && u.plan_status !== 'active') return false;
      if (filtro === 'inativas' && u.plan_status === 'active') return false;
      if (filtro === 'nunca_acessou' && !u.nunca_acessou) return false;
      if (filtro === 'abandonou' && u.status_funil !== 'checkout_started') return false;
      if (filtro === 'sem_pagamento' && u.status_funil !== 'blocked_no_payment') return false;
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
          <p className="text-sm text-gray-500 mt-0.5">Cadastro, acesso e funil de pagamento.</p>
        </div>
        <div className="flex items-center gap-2 self-start">
          <Button variant="outline" onClick={load} className="gap-1"><RefreshCw className="w-4 h-4" /> Atualizar</Button>
          <Button
            onClick={excluirInativos}
            disabled={bulkLoading}
            className="gap-1 bg-red-600 hover:bg-red-700 text-white"
            title="Excluir todos sem assinatura ativa (exceto a sua conta)"
          >
            {bulkLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />} Excluir inativos
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard label="Cadastrados"            value={stats.total}          accent="#1E6B38" Icon={Users} />
        <StatCard label="Assinaturas ativas"     value={stats.ativas}         accent="#C9A84C" Icon={CheckCircle2} />
        <StatCard label="Nunca acessaram"        value={stats.nuncaAcessaram} accent="#6B8072" Icon={UserX} />
        <StatCard label="Pararam no checkout"    value={stats.abandonaram}    accent="#D9822B" Icon={ShoppingCart} />
        <StatCard label="Administradores"        value={stats.admins}         accent="#2E8B57" Icon={ShieldCheck} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
          <option value="todos">Todos</option>
          <option value="ativas">Assinatura ativa</option>
          <option value="inativas">Inativas/Expiradas</option>
          <option value="nunca_acessou">Nunca acessaram</option>
          <option value="abandonou">Pararam no checkout</option>
          <option value="sem_pagamento">Pagamento recusado</option>
        </select>
        <div className="relative max-w-xs flex-1">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome ou e-mail..." className="pl-9" />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        {loading ? (
          <div className="py-16 flex justify-center"><BrandSpinner label="Carregando…" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-100">
                <th className="text-left py-3 px-4">Nome</th>
                <th className="text-left py-3 px-4">E-mail</th>
                <th className="text-left py-3 px-4">Último acesso</th>
                <th className="text-center py-3 px-2">Acessos</th>
                <th className="text-left py-3 px-4">Funil</th>
                <th className="text-left py-3 px-4">Assinatura</th>
                <th className="text-left py-3 px-4">Validade</th>
                <th className="text-right py-3 px-4">Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((u) => {
                const st = PLAN_STATUS[u.plan_status] || PLAN_STATUS.inactive;
                const fn = FUNIL[u.status_funil] || FUNIL.never_started;
                const isAdmin = ['admin', 'owner', 'ceo'].includes(String(u.role || '').toLowerCase());
                return (
                  <tr
                    key={u.id}
                    className="border-t border-gray-100 hover:bg-emerald-50/30 cursor-pointer"
                    onClick={() => setDetalhe(u)}
                  >
                    <td className="py-3 px-4 font-semibold text-gray-800">
                      {u.name || '—'}
                      {isAdmin && <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-amber-600">admin</span>}
                    </td>
                    <td className="py-3 px-4 text-gray-600">{u.email}</td>
                    <td className="py-3 px-4 text-xs text-gray-500">
                      {u.nunca_acessou
                        ? <span className="text-gray-400 italic">nunca acessou</span>
                        : fmtDataHora(u.ultimo_acesso)}
                    </td>
                    <td className="py-3 px-2 text-center text-xs font-semibold text-gray-700">{u.total_acessos ?? 0}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded-full border ${fn.cls}`}>
                        {fn.label}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${st.cls}`}>
                        <st.Icon className="w-3 h-3" /> {st.label}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs text-gray-500">{fmtData(u.plan_expires)}</td>
                    <td className="py-3 px-2 text-right" onClick={(e) => e.stopPropagation()}>
                      {u.id === user?.id ? (
                        <span className="text-[10px] text-gray-300">você</span>
                      ) : (
                        <button
                          onClick={() => excluir(u)}
                          disabled={deleting[u.id]}
                          title="Excluir usuário"
                          className="p-1.5 hover:bg-red-50 rounded text-red-600"
                        >
                          {deleting[u.id] ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
              {filtrados.length === 0 && (
                <tr><td colSpan={8} className="text-center py-10 text-gray-400">Nenhum usuário encontrado</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-[11px] text-gray-400">
        Clique numa linha para ver o histórico de acessos e pagamentos. A coluna <strong>Funil</strong> é
        diagnóstica — quem controla o acesso ao sistema é a coluna <strong>Assinatura</strong>.
      </p>

      {detalhe && <TimelineDrawer alvo={detalhe} onClose={() => setDetalhe(null)} />}
    </div>
  );
};

export default UsuariosAdmin;
