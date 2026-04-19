import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Sparkles } from 'lucide-react';
import { Button } from '../ui/button';
import { BRAND } from '../../mock/mock';

const Hero = () => {
  return (
    <section className="relative pt-32 pb-20 overflow-hidden bg-gradient-to-b from-emerald-50/40 to-white">
      <div className="absolute inset-0 opacity-[0.04] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#0d4f3c 1px, transparent 1px)', backgroundSize: '24px 24px' }} />

      <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center relative">
        <div className="animate-fade-in-up">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-900/5 border border-emerald-900/10 text-emerald-900 text-xs font-medium mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            Nova versão 2026 com IA integrada
          </div>

          <h1 className="font-display text-5xl md:text-6xl lg:text-7xl font-bold leading-[1.05] text-gray-900 mb-6">
            Avalie com <span className="brand-green">precisão.</span><br />
            Decida com <span className="brand-green italic">confiança.</span>
          </h1>

          <p className="text-lg text-gray-600 mb-8 max-w-xl leading-relaxed">
            A plataforma completa para emitir <strong>PTAM, Laudos e Avaliações</strong> de imóveis urbanos, rurais e outras garantias — grãos, safra, bovinos e equipamentos.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 mb-10">
            <Link to="/cadastro">
              <Button size="lg" className="bg-emerald-900 hover:bg-emerald-800 text-white px-8 h-12 text-base font-semibold shadow-lg shadow-emerald-900/20">
                Começar agora
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
            <a href="#planos">
              <Button size="lg" variant="outline" className="border-emerald-900/30 text-emerald-900 hover:bg-emerald-50 px-8 h-12 text-base">
                Ver planos
              </Button>
            </a>
          </div>

          <div className="flex flex-wrap gap-x-6 gap-y-3 text-sm text-gray-600">
            {['ABNT NBR 14.653', 'LGPD compliant', 'IA para textos', 'Suporte técnico'].map(item => (
              <div key={item} className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="relative animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          <div className="absolute -inset-4 bg-gradient-to-br from-emerald-100/60 to-emerald-50/30 rounded-3xl blur-2xl" />
          <div className="relative rounded-2xl overflow-hidden shadow-2xl shadow-emerald-900/20 border border-emerald-900/10">
            <img src="https://images.pexels.com/photos/8469999/pexels-photo-8469999.jpeg" alt="Engenheira avaliadora" className="w-full h-[520px] object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-emerald-900/40 via-transparent to-transparent" />

            <div className="absolute bottom-6 left-6 right-6 bg-white/95 backdrop-blur rounded-xl p-5 shadow-lg">
              <div className="flex items-center justify-between mb-3">
                <div className="text-xs font-semibold text-emerald-900 tracking-wider">PTAM-2026-001</div>
                <span className="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-900 rounded-full font-medium">Emitido</span>
              </div>
              <div className="font-display text-2xl font-bold text-gray-900">R$ 380.000,00</div>
              <div className="text-xs text-gray-500 mt-1">Apartamento 85m² • Calhau/MA • Método Comparativo</div>
            </div>
          </div>

          <div className="absolute -top-4 -left-4 bg-white rounded-xl shadow-xl border border-emerald-900/10 p-4 animate-float">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-900 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="text-xs text-gray-500">IA gerou</div>
                <div className="text-sm font-semibold text-gray-900">Fundamentação técnica</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
