import React from 'react';
import { UserPlus, Calculator, FileCheck, LifeBuoy } from 'lucide-react';

const STEPS = [
  { num: '01', icon: UserPlus, title: 'Estruturação', items: ['Cadastro de clientes', 'Cadastro de imóveis e garantias', 'Cadastro de amostras de mercado'] },
  { num: '02', icon: Calculator, title: 'Processamento', items: ['Cálculos automatizados', 'Método Comparativo Direto', 'Método Evolutivo e Agronômico'] },
  { num: '03', icon: FileCheck, title: 'Emissão', items: ['PTAM profissional', 'Laudos de avaliação', 'Relatórios prontos para entrega'] },
  { num: '04', icon: LifeBuoy, title: 'Gestão e Suporte', items: ['Acompanhamento de trabalhos', 'Histórico completo', 'Suporte especializado'] },
];

const Flow = () => {
  return (
    <section id="fluxo" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="text-xs font-semibold tracking-[0.2em] text-emerald-700 mb-3">FLUXO DOS MÓDULOS</div>
          <h2 className="font-display text-4xl md:text-5xl font-bold text-gray-900 leading-tight mb-4">
            Do cadastro à emissão, <span className="brand-green italic">tudo conectado</span>
          </h2>
          <p className="text-gray-600 text-lg">Um fluxo prático e intuitivo do início ao fim.</p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={s.num} className="relative">
                {i < STEPS.length - 1 && (
                  <div className="hidden lg:block absolute top-8 -right-3 w-6 h-[2px] bg-gradient-to-r from-emerald-900/30 to-emerald-900/0" />
                )}
                <div className="relative p-6 rounded-xl bg-gradient-to-br from-emerald-50/60 to-white border border-emerald-900/10 h-full">
                  <div className="flex items-start justify-between mb-5">
                    <div className="w-14 h-14 rounded-lg bg-emerald-900 flex items-center justify-center">
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <div className="font-display text-4xl font-bold text-emerald-900/15">{s.num}</div>
                  </div>
                  <h3 className="font-display text-xl font-bold text-gray-900 mb-3">{s.title}</h3>
                  <ul className="space-y-2 text-sm text-gray-600">
                    {s.items.map((it, j) => (
                      <li key={j} className="flex gap-2"><span className="w-1 h-1 rounded-full bg-emerald-700 mt-2 flex-shrink-0" />{it}</li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Flow;
