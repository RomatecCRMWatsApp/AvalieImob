import React from 'react';
import { Check, Star, CreditCard, Calendar } from 'lucide-react';
import { Button } from '../ui/button';
import { useToast } from '../../hooks/use-toast';
import { PLANS } from '../../mock/mock';
import { useAuth } from '../../contexts/AuthContext';

const SubscriptionPage = () => {
  const { toast } = useToast();
  const { user } = useAuth();

  const handleSubscribe = (plan) => {
    toast({ title: 'Em breve', description: `Integração de pagamento será adicionada. Plano: ${plan.name}` });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold text-gray-900">Assinatura</h1>
        <p className="text-gray-600 mt-1">Gerencie seu plano e faturamento.</p>
      </div>

      <div className="bg-gradient-to-br from-emerald-900 to-emerald-950 text-white rounded-xl p-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="text-xs text-emerald-200 uppercase tracking-wider mb-1">Plano atual</div>
            <div className="font-display text-3xl font-bold capitalize">{user?.plan || 'Mensal'}</div>
            <div className="flex items-center gap-2 text-sm text-emerald-200 mt-2"><Calendar className="w-4 h-4" />Próxima cobrança: 15/05/2026</div>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" className="border-white/30 text-white hover:bg-white/10 bg-transparent">Histórico</Button>
            <Button className="bg-amber-500 hover:bg-amber-400 text-emerald-950 font-semibold"><CreditCard className="w-4 h-4 mr-2" />Gerenciar pagamento</Button>
          </div>
        </div>
      </div>

      <div>
        <h2 className="font-display text-xl font-bold text-gray-900 mb-4">Fazer upgrade ou downgrade</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {PLANS.map(p => (
            <div key={p.id} className={`relative rounded-xl p-6 border-2 ${p.highlight ? 'border-emerald-900 bg-emerald-50/40' : 'border-gray-200 bg-white'}`}>
              {p.highlight && <div className="absolute -top-3 left-6 px-2.5 py-0.5 bg-amber-500 text-white text-[10px] font-bold rounded-full flex items-center gap-1"><Star className="w-3 h-3 fill-white" />POPULAR</div>}
              <div className="text-sm font-semibold text-emerald-700 mb-2">{p.name}</div>
              <div className="flex items-baseline gap-1"><span className="text-lg font-bold text-gray-900">R$</span><span className="font-display text-4xl font-bold text-gray-900">{p.price.toFixed(2).replace('.', ',')}</span></div>
              <div className="text-xs text-gray-500 mb-4">por {p.period}</div>
              <div className="space-y-2 mb-5 min-h-[160px]">{p.features.slice(0, 5).map((f, i) => (<div key={i} className="flex items-start gap-2 text-xs"><Check className="w-3.5 h-3.5 text-emerald-700 mt-0.5 flex-shrink-0" /><span>{f}</span></div>))}</div>
              <Button onClick={() => handleSubscribe(p)} className="w-full bg-emerald-900 hover:bg-emerald-800 text-white">Escolher {p.name}</Button>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Últimas faturas</h3>
        <div className="space-y-3">
          {[{ id: 'INV-001', date: '15/04/2026', amount: 239.90, status: 'Pago' }, { id: 'INV-002', date: '15/01/2026', amount: 239.90, status: 'Pago' }].map(inv => (
            <div key={inv.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3"><div className="w-9 h-9 rounded-lg bg-emerald-100 flex items-center justify-center"><CreditCard className="w-4 h-4 text-emerald-800" /></div><div><div className="font-semibold text-sm">{inv.id}</div><div className="text-xs text-gray-500">{inv.date}</div></div></div>
              <div className="flex items-center gap-3"><span className="text-sm font-semibold">R$ {inv.amount.toFixed(2).replace('.', ',')}</span><span className="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full">{inv.status}</span></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SubscriptionPage;
