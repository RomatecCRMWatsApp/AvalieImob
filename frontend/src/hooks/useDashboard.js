// @module useDashboard — abstrai a busca e derivação de dados do Dashboard (Visão Geral).
// Reaproveita os endpoints já existentes (sem criar rotas novas):
//   GET /api/dashboard/stats   -> { evaluations, clients, properties, revenue, monthly:[{month,count}] }
//   GET /api/ptam              -> laudos recentes
//   GET /api/payments/status   -> { plan_status, plan, plan_expires }
import { useState, useEffect, useCallback, useMemo } from 'react';
import { dashboardAPI, ptamAPI, paymentsAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { PLANS } from '../mock/mock';
import { resolvePtamStatus } from '../components/dashboard/ptam/ptamStatus';

/* ── Helpers de formatação ─────────────────────────────────────────────── */
const fmtBRL = (v) =>
  `R$ ${Number(v || 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`;

// Volume compactado (ex.: R$ 2,4 M / R$ 850 mil)
const fmtCompact = (v) => {
  const n = Number(v || 0);
  if (n >= 1_000_000) return `R$ ${(n / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} M`;
  if (n >= 1_000)     return `R$ ${(n / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`;
  return fmtBRL(n);
};

const fmtPct = (v) => {
  if (v == null || Number.isNaN(Number(v))) return null;
  const n = Number(v);
  return `${n > 0 ? '+' : ''}${n.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
};

const greetingByHour = (h) => {
  if (h < 12) return 'Bom dia';
  if (h < 18) return 'Boa tarde';
  return 'Boa noite';
};

const todayLabel = () =>
  new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' });

/* ── Hook ──────────────────────────────────────────────────────────────── */
export function useDashboard() {
  const { user } = useAuth();
  const [stats, setStats]     = useState(null);
  const [recentRaw, setRecent] = useState([]);
  const [payStatus, setPay]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const reload = useCallback(() => {
    setLoading(true);
    Promise.all([
      dashboardAPI.stats(),
      ptamAPI.list().catch(() => []),
      paymentsAPI.status().catch(() => null),
    ])
      .then(([s, list, pay]) => {
        setStats(s || null);
        setRecent(Array.isArray(list) ? list : []);
        setPay(pay || null);
        setError(null);
      })
      .catch((err) => {
        console.warn('useDashboard: falha ao carregar', err);
        setError(err);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { reload(); }, [reload]);

  /* ── Derivações ──────────────────────────────────────────────────────── */
  const firstName = useMemo(
    () => (user?.name?.trim()?.split(/\s+/)[0]) || 'Avaliador',
    [user],
  );

  const greeting = useMemo(() => greetingByHour(new Date().getHours()), []);

  // KPIs derivados
  const kpis = useMemo(() => {
    const laudos   = Number(stats?.evaluations ?? 0);
    const clientes = Number(stats?.clients ?? 0);
    const imoveis  = Number(stats?.properties ?? 0);
    const volume   = Number(stats?.revenue ?? 0);
    const ticket   = laudos > 0 ? volume / laudos : 0;
    const porCli   = clientes > 0 ? laudos / clientes : 0;
    return {
      laudosTotal:      laudos,
      clientes,
      imoveis,
      volumeTotal:      volume,
      volumeCompact:    fmtCompact(volume),
      volumeFull:       fmtBRL(volume),
      ticketMedio:      fmtBRL(ticket),
      laudosPorCliente: porCli.toLocaleString('pt-BR', { maximumFractionDigits: 1 }),
      // variações vêm do backend se existirem; senão ficam neutras (flat)
      variacaoLaudos:   fmtPct(stats?.variacaoLaudos),
      variacaoVolume:   fmtPct(stats?.variacaoVolume),
    };
  }, [stats]);

  // Série mensal para o gráfico (últimos 6 meses)
  const monthly = useMemo(() => {
    const arr = Array.isArray(stats?.monthly) ? stats.monthly : [];
    return arr.slice(-6).map((m) => ({ mes: m.month, total: Number(m.count ?? 0) }));
  }, [stats]);

  // Rascunhos (para o subtítulo do hero)
  const rascunhos = useMemo(
    () => recentRaw.filter((p) => resolvePtamStatus(p) === 'rascunho').length,
    [recentRaw],
  );

  // Laudos recentes normalizados
  const recentes = useMemo(
    () =>
      recentRaw.slice(0, 5).map((p) => {
        const st = resolvePtamStatus(p);
        return {
          id:          p.id,
          numero:      p.numero_ptam || p.number || 'PTAM',
          solicitante: p.solicitante_nome || p.solicitante || '—',
          data:        p.created_at ? new Date(p.created_at).toLocaleDateString('pt-BR') : '',
          status:      st === 'rascunho' ? 'Rascunho' : 'Finalizado',
          rawStatus:   st,
        };
      }),
    [recentRaw],
  );

  // Plano
  const plano = useMemo(() => {
    const st       = payStatus?.plan_status || 'inactive';
    const label    = payStatus?.plan || user?.plan || 'Mensal';
    const obj      = PLANS.find(
      (p) => p.name?.toLowerCase() === String(label).toLowerCase() ||
             p.id?.toLowerCase() === String(label).toLowerCase(),
    );
    const expires  = payStatus?.plan_expires
      ? new Date(payStatus.plan_expires).toLocaleDateString('pt-BR')
      : null;
    return {
      nome:     obj?.name || label,
      ativo:    st === 'active',
      status:   st,
      validade: expires,
      features: obj?.features || [],
    };
  }, [payStatus, user]);

  return {
    loading,
    error,
    reload,
    firstName,
    greeting,
    today: todayLabel(),
    kpis,
    monthly,
    rascunhos,
    recentes,
    plano,
  };
}

export default useDashboard;
