import React, { useEffect, useState } from 'react';
import { Check, Star, CreditCard, Calendar, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { Button } from '../ui/button';
import { useToast } from '../../hooks/use-toast';
import { PLANS } from '../../mock/mock';
import { useAuth } from '../../contexts/AuthContext';
import { paymentsAPI } from '../../lib/api';

const STATUS_LABELS = {
  active: { label: 'Ativo', color: 'bg-emerald-100 text-emerald-800', icon: CheckCircle },
  inactive: { label: 'Inativo', color: 'bg-gray-100 text-gray-600', icon: AlertCircle },
  expired: { label: 'Expirado', color: 'bg-red-100 text-red-700', icon: AlertCircle },
  pending: { label: 'Pendente', color: 'bg-amber-100 text-amber-700', icon: Clock },
};

const TXN_STATUS = {
  approved: { label: 'Aprovado', color: 'bg-emerald-100 text-emerald-800' },
  pending:  { label: 'Pendente',  color: 'bg-amber-100 text-amber-700'   },
  rejected: { label: 'Rejeitado', color: 'bg-red-100 text-red-700'       },
};

// Map mock plan ids to backend plan ids
const PLAN_ID_MAP = {
  monthly: 'mensal',
  quarterly: 'trimestral',
  annual: 'anual',
};

const SubscriptionPage = () => {
  const { toast } = useToast();
  const { user } = useAuth();
  const [payStatus, setPayStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(null);

  useEffect(() => {
    paymentsAPI.status()
      .then(setPayStatus)
      .catch(() => setPayStatus(null))
      .finally(() => setLoading(false));

    // Show toast on return from MP checkout
    const params = new URLSearchParams(window.location.search);
    const payment = params.get('payment');
    if (payment === 'success') {
      toast({ title: 'Pagamento aprovado!', description: 'Seu plano foi ativado com sucesso.' });
      window.history.replaceState({}, '', window.location.pathname);
    } else if (payment === 'failure') {
      toast({ title: 'Pagamento recusado', description: 'Tente novamente ou use outro cartão.', variant: 'destructive' });
      window.history.replaceState({}, '', window.location.pathname);
    } else if (payment === 'pending') {
      toast({ title: 'Pagamento pendente', description: 'Aguardando confirmação do pagamento.' });
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [toast]);

  const handleSubscribe = async (plan) => {
    const planId = PLAN_ID_MAP[plan.id] || plan.id;
    setSubscribing(plan.id);
    try {
      const { init_point } = await paymentsAPI.createPreference(planId);
      window.location.href = init_point;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao iniciar pagamento. Tente novamente.';
      toast({ title: 'Erro', description: msg, variant: 'destructive' });
      setSubscribing(null);
    }
  };

  const planSt = payStatus?.plan_status || 'inactive';
  const statusInfo = STATUS_LABELS[planSt] || STATUS_LABELS.inactive;
  const StatusIcon = statusInfo.icon;

  const formatDate = (iso) => {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('pt-BR');
    } catch { return iso; }
  };

  const formatCurrency = (v) =>
    Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold text-gray-900">Assinatura</h1>
        <p className="text-gray-600 mt-1">Gerencie seu plano e faturamento.</p>
      </div>

      {/* Current plan banner */}
      <div className="bg-gradient-to-br from-emerald-900 to-emerald-950 text-white rounded-xl p-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="text-xs text-emerald-200 uppercase tracking-wider mb-1">Plano atual</div>
            <div className="font-display text-3xl font-bold capitalize">
              {payStatus?.plan || user?.plan || 'Mensal'}
            </div>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold flex items-center gap-1 ${statusInfo.color}`}>
                <StatusIcon className="w-3 h-3" />
                {statusInfo.label}
              </span>
              {payStatus?.plan_expires && (
                <span className="flex items-center gap-1 text-sm text-emerald-200">
                  <Calendar className="w-4 h-4" />
                  Expira em: {formatDate(payStatus.plan_expires)}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Plan cards */}
      <div>
        <h2 className="font-display text-xl font-bold text-gray-900 mb-4">Escolha seu plano</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {PLANS.map(p => (
            <div key={p.id} className={`relative rounded-xl p-6 border-2 ${p.highlight ? 'border-emerald-900 bg-emerald-50/40' : 'border-gray-200 bg-white'}`}>
              {p.highlight && (
                <div className="absolute -top-3 left-6 px-2.5 py-0.5 bg-amber-500 text-white text-[10px] font-bold rounded-full flex items-center gap-1">
                  <Star className="w-3 h-3 fill-white" />POPULAR
                </div>
              )}
              <div className="text-sm font-semibold text-emerald-700 mb-2">{p.name}</div>
              <div className="flex items-baseline gap-1">
                <span className="text-lg font-bold text-gray-900">R$</span>
                <span className="font-display text-4xl font-bold text-gray-900">{p.price.toFixed(2).replace('.', ',')}</span>
              </div>
              <div className="text-xs text-gray-500 mb-4">por {p.period}</div>
              {p.saving && <div className="text-xs font-semibold text-emerald-700 mb-2">{p.saving}</div>}
              <div className="space-y-2 mb-5 min-h-[160px]">
                {p.features.slice(0, 5).map((f) => (
                  <div key={f} className="flex items-start gap-2 text-xs">
                    <Check className="w-3.5 h-3.5 text-emerald-700 mt-0.5 flex-shrink-0" />
                    <span>{f}</span>
                  </div>
                ))}
              </div>
              <Button
                onClick={() => handleSubscribe(p)}
                disabled={subscribing === p.id}
                className="w-full bg-emerald-900 hover:bg-emerald-800 text-white"
              >
                {subscribing === p.id ? 'Redirecionando...' : `Assinar ${p.name}`}
              </Button>
            </div>
          ))}
        </div>
      </div>

      {/* Transaction history */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Histórico de pagamentos</h3>
        {loading ? (
          <p className="text-sm text-gray-500">Carregando...</p>
        ) : !payStatus?.transactions?.length ? (
          <p className="text-sm text-gray-500">Nenhum pagamento registrado ainda.</p>
        ) : (
          <div className="space-y-3">
            {payStatus.transactions.map((txn) => {
              const st = TXN_STATUS[txn.status] || { label: txn.status, color: 'bg-gray-100 text-gray-600' };
              return (
                <div key={txn.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-emerald-100 flex items-center justify-center">
                      <CreditCard className="w-4 h-4 text-emerald-800" />
                    </div>
                    <div>
                      <div className="font-semibold text-sm capitalize">{txn.plan_id}</div>
                      <div className="text-xs text-gray-500">{formatDate(txn.created_at)}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold">{formatCurrency(txn.amount)}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${st.color}`}>{st.label}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default SubscriptionPage;
