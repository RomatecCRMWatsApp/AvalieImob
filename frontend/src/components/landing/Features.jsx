import React from 'react';
import * as Icons from 'lucide-react';
import { FEATURES } from '../../mock/mock';

const Features = () => {
  return (
    <section id="features" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="max-w-2xl mb-16">
          <div className="text-xs font-semibold tracking-[0.2em] text-emerald-700 mb-3">FUNCIONALIDADES</div>
          <h2 className="font-display text-4xl md:text-5xl font-bold text-gray-900 leading-tight mb-4">
            Tudo que o avaliador precisa, <span className="brand-green italic">em um só lugar</span>
          </h2>
          <p className="text-gray-600 text-lg">Uma plataforma moderna pensada para engenheiros, corretores, peritos e profissionais técnicos.</p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((f, i) => {
            const Icon = Icons[f.icon] || Icons.Circle;
            return (
              <div key={f.id} className="group relative p-6 rounded-xl border border-gray-200 hover:border-emerald-900/30 hover:shadow-lg hover:-translate-y-1 transition-all duration-300 bg-white" style={{ animationDelay: `${i * 50}ms` }}>
                <div className="w-12 h-12 rounded-lg bg-emerald-900/5 flex items-center justify-center mb-4 group-hover:bg-emerald-900 transition-colors">
                  <Icon className="w-6 h-6 text-emerald-900 group-hover:text-white transition-colors" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-600 leading-relaxed">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Features;
