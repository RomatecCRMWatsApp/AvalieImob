import React from 'react';
import * as Icons from 'lucide-react';
import { SERVICES } from '../../mock/mock';

const Services = () => {
  return (
    <section id="services" className="py-24 bg-gradient-to-b from-white to-emerald-50/30">
      <div className="max-w-7xl mx-auto px-6">
        <div className="max-w-2xl mb-16">
          <div className="text-xs font-semibold tracking-[0.2em] text-emerald-700 mb-3">O QUE VOCÊ AVALIA</div>
          <h2 className="font-display text-4xl md:text-5xl font-bold text-gray-900 leading-tight mb-4">
            Urbano, rural e garantias <span className="brand-green italic">em uma só plataforma</span>
          </h2>
          <p className="text-gray-600 text-lg">Do apartamento à fazenda, da safra ao rebanho — tudo com fundamentação técnica.</p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {SERVICES.map((s) => {
            const Icon = Icons[s.icon] || Icons.Circle;
            return (
              <div key={s.id} className="group relative rounded-2xl overflow-hidden bg-white border border-gray-200 hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
                <div className="relative h-48 overflow-hidden">
                  <img src={s.img} alt={s.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                  <div className="absolute inset-0 bg-gradient-to-t from-emerald-900/80 via-emerald-900/20 to-transparent" />
                  <div className="absolute top-4 left-4 w-11 h-11 rounded-lg bg-white/95 backdrop-blur flex items-center justify-center">
                    <Icon className="w-5 h-5 text-emerald-900" />
                  </div>
                </div>
                <div className="p-6">
                  <h3 className="font-display text-xl font-bold text-gray-900 mb-2">{s.title}</h3>
                  <p className="text-sm text-gray-600 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Services;
