import React from 'react';
import { ShieldCheck, Lock, RefreshCw, Award } from 'lucide-react';
import { TESTIMONIALS } from '../../mock/mock';

const About = () => {
  const items = [
    { icon: ShieldCheck, title: 'Segurança', desc: 'Níveis de certificação de segurança da informação.' },
    { icon: Lock, title: 'Privacidade', desc: 'Total conformidade com a LGPD e dados criptografados.' },
    { icon: RefreshCw, title: 'Sincronização', desc: 'Painel limpo com sincronização em tempo real na nuvem.' },
    { icon: Award, title: 'Certificação', desc: 'Capacitação técnica reconhecida pelo mercado.' },
  ];

  return (
    <section id="sobre" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid lg:grid-cols-2 gap-16 items-center mb-24">
          <div className="relative">
            <div className="grid grid-cols-2 gap-4">
              <img src="https://images.pexels.com/photos/31923308/pexels-photo-31923308.jpeg" alt="Urbano" className="rounded-xl h-64 w-full object-cover" />
              <img src="https://images.unsplash.com/photo-1671308819531-1097d5ab5dcc" alt="Rural" className="rounded-xl h-64 w-full object-cover mt-8" />
              <img src="https://images.unsplash.com/photo-1669222214700-6b331f0f64cc" alt="Bairro" className="rounded-xl h-64 w-full object-cover -mt-4" />
              <img src="https://images.unsplash.com/photo-1742825715166-f23f9ed20e24" alt="Fazenda" className="rounded-xl h-64 w-full object-cover mt-4" />
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold tracking-[0.2em] text-emerald-700 mb-3">SOBRE</div>
            <h2 className="font-display text-4xl md:text-5xl font-bold text-gray-900 leading-tight mb-6">
              Por que escolher o <span className="brand-green italic">RomaTec AvalieImob?</span>
            </h2>
            <p className="text-gray-600 leading-relaxed mb-4">
              O RomaTec AvalieImob é uma plataforma online de avaliação desenvolvida para corretores, peritos judiciais, assistentes técnicos, engenheiros avaliadores e demais profissionais que atuam com PTAM, laudos e avaliações imobiliárias, urbanas, rurais e de garantias.
            </p>
            <p className="text-gray-600 leading-relaxed mb-6">
              Nossas avaliações seguem o <strong>Método Comparativo Direto de Mercado</strong>, <strong>Método Evolutivo</strong> e <strong>avaliações agronômicas</strong>, conforme normas técnicas da ABNT NBR 14.653 — tudo potencializado por inteligência artificial.
            </p>
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
              <div><div className="font-display text-3xl font-bold brand-green">+5 mil</div><div className="text-xs text-gray-500 mt-1">Laudos emitidos</div></div>
              <div><div className="font-display text-3xl font-bold brand-green">+800</div><div className="text-xs text-gray-500 mt-1">Profissionais</div></div>
              <div><div className="font-display text-3xl font-bold brand-green">27</div><div className="text-xs text-gray-500 mt-1">Estados atendidos</div></div>
            </div>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-24">
          {items.map((it) => {
            const Icon = it.icon;
            return (
              <div key={it.title} className="flex gap-4 p-5 rounded-xl bg-emerald-50/40 border border-emerald-900/10">
                <div className="w-11 h-11 rounded-lg bg-white flex items-center justify-center flex-shrink-0">
                  <Icon className="w-5 h-5 text-emerald-900" />
                </div>
                <div>
                  <div className="font-semibold text-gray-900 mb-1">{it.title}</div>
                  <div className="text-xs text-gray-600 leading-relaxed">{it.desc}</div>
                </div>
              </div>
            );
          })}
        </div>

        <div>
          <div className="text-center max-w-2xl mx-auto mb-12">
            <div className="text-xs font-semibold tracking-[0.2em] text-emerald-700 mb-3">DEPOIMENTOS</div>
            <h3 className="font-display text-3xl md:text-4xl font-bold text-gray-900">Profissionais que <span className="brand-green italic">confiam no RomaTec</span></h3>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {TESTIMONIALS.map(t => (
              <div key={t.id} className="p-6 rounded-xl border border-gray-200 bg-white hover:shadow-lg transition-shadow">
                <div className="flex gap-1 mb-4">{[...Array(5)].map((_, i) => <span key={i} className="text-amber-500">★</span>)}</div>
                <p className="text-gray-700 italic mb-6 leading-relaxed">“{t.text}”</p>
                <div className="flex items-center gap-3 pt-4 border-t border-gray-100">
                  <img src={t.avatar} alt={t.name} className="w-11 h-11 rounded-full object-cover" />
                  <div>
                    <div className="font-semibold text-gray-900 text-sm">{t.name}</div>
                    <div className="text-xs text-gray-500">{t.role} · {t.crea}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default About;
