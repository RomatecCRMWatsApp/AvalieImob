import React from 'react';
import { Link } from 'react-router-dom';
import { Check, Star } from 'lucide-react';
import { Button } from '../ui/button';
import { PLANS } from '../../mock/mock';

const Pricing = () => {
  return (
    <section id="planos" className="py-24 bg-gradient-to-b from-emerald-50/30 to-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="text-xs font-semibold tracking-[0.2em] text-emerald-700 mb-3">ASSINE AGORA</div>
          <h2 className="font-display text-4xl md:text-5xl font-bold text-gray-900 leading-tight mb-4">
            Planos flexíveis para <span className="brand-green italic">cada profissional</span>
          </h2>
          <p className="text-gray-600 text-lg">Mensal, trimestral ou anual — escolha o que melhor combina com você.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {PLANS.map((p) => (
            <div key={p.id} className={`relative rounded-2xl p-8 border-2 transition-all hover:-translate-y-1 ${p.highlight ? 'border-emerald-900 bg-gradient-to-b from-emerald-900 to-emerald-950 text-white shadow-2xl shadow-emerald-900/30 scale-[1.02]' : 'border-gray-200 bg-white hover:border-emerald-900/30 hover:shadow-xl'}`}>
              {p.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-amber-500 text-white text-xs font-bold rounded-full flex items-center gap-1">
                  <Star className="w-3 h-3 fill-white" />
                  MAIS POPULAR
                </div>
              )}
              <div className={`text-sm font-semibold mb-2 ${p.highlight ? 'text-emerald-200' : 'text-emerald-700'}`}>{p.name}</div>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-2xl font-bold">R$</span>
                <span className="font-display text-5xl font-bold">{p.price.toFixed(2).replace('.', ',')}</span>
              </div>
              <div className={`text-sm mb-3 ${p.highlight ? 'text-emerald-200/80' : 'text-gray-500'}`}>por {p.period}</div>
              {p.saving && (
                <div className={`inline-block px-2 py-0.5 text-xs font-semibold rounded mb-4 ${p.highlight ? 'bg-amber-500/20 text-amber-200' : 'bg-emerald-50 text-emerald-800'}`}>{p.saving}</div>
              )}
              <p className={`text-sm mb-6 ${p.highlight ? 'text-emerald-100/90' : 'text-gray-600'}`}>{p.desc}</p>

              <div className="space-y-3 mb-8">
                {p.features.map((f, i) => (
                  <div key={i} className="flex items-start gap-3 text-sm">
                    <Check className={`w-4 h-4 mt-0.5 flex-shrink-0 ${p.highlight ? 'text-amber-300' : 'text-emerald-700'}`} />
                    <span className={p.highlight ? 'text-emerald-50' : 'text-gray-700'}>{f}</span>
                  </div>
                ))}
              </div>

              <Link to="/cadastro" className="block">
                <Button className={`w-full h-11 font-semibold ${p.highlight ? 'bg-white text-emerald-900 hover:bg-emerald-50' : 'bg-emerald-900 hover:bg-emerald-800 text-white'}`}>
                  Assinar {p.name}
                </Button>
              </Link>
            </div>
          ))}
        </div>

        <div className="text-center mt-10 text-sm text-gray-500">
          Sem renovação automática · Cancele quando quiser · Suporte em português
        </div>
      </div>
    </section>
  );
};

export default Pricing;
