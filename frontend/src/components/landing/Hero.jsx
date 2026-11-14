import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Calculator, ShieldCheck, Sigma, Sparkles, MapPinned, FileSignature } from 'lucide-react';
import { VERDE, DOURADO, CREME, WHATS_FMT } from './campanha';
import { BotaoTeste, CurvasTopo } from './CampanhaModulos';

// Identidade da campanha: verde profundo, dourado e as artes dos módulos em leque.
const DESTAQUES = [
  { label: 'PTAM · NBR 14.653', icon: Sparkles },
  { label: 'Inferência estatística — Grau III', icon: Sigma },
  { label: 'Georreferenciamento e SIG-RI', icon: MapPinned },
  { label: 'Contratos e procuração', icon: FileSignature },
  { label: 'Assinatura ICP-Brasil', icon: ShieldCheck },
];

const LEQUE = [
  { src: '/campanha/geo-1.jpg', alt: 'Do memorial ao dossiê: módulo de georreferenciamento', cls: '-rotate-[7deg] -translate-x-[38%] translate-y-6', z: 1 },
  { src: '/campanha/exc-1.jpg', alt: 'Exclusividade assinada pelo celular', cls: 'rotate-[7deg] translate-x-[38%] translate-y-6', z: 2 },
  { src: '/campanha/ptam-4.jpg', alt: 'Um laudo com a sua marca: PTAM em PDF com assinatura ICP-Brasil', cls: '', z: 3 },
];

const Hero = () => (
  <section className="relative overflow-hidden pt-16 pb-20 md:pt-20 md:pb-28" style={{ background: VERDE }}>
    <CurvasTopo cor="rgba(201,168,76,.14)" />
    <div
      className="absolute -right-40 -top-40 w-[560px] h-[560px] rounded-full pointer-events-none"
      style={{ background: 'radial-gradient(circle, rgba(201,168,76,.18) 0%, rgba(201,168,76,0) 70%)' }}
    />

    <div className="relative max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-14 items-center">
      <div className="min-w-0 animate-fade-in-up">
        <p className="text-xs font-bold tracking-[0.3em] uppercase mb-6" style={{ color: DOURADO }}>
          Avaliação · Topografia · Contratos
        </p>

        <h1 className="font-sans font-extrabold tracking-tight leading-[1.02] text-[2.15rem] sm:text-6xl lg:text-[4.1rem] mb-3" style={{ color: CREME, textWrap: 'balance' }}>
          Software de PTAM e avaliação imobiliária.{' '}
          <span className="block" style={{ color: DOURADO }}>Do laudo ao contrato assinado.</span>
        </h1>

        <div className="w-16 h-[3px] rounded-full my-7" style={{ background: DOURADO }} />

        <p className="text-lg leading-relaxed mb-8 max-w-xl" style={{ color: 'rgba(243,241,230,.82)' }}>
          A plataforma do corretor, do avaliador e do agrimensor: emita <strong className="text-[#F3F1E6]">PTAM e laudos</strong> conforme a NBR 14.653, monte o <strong className="text-[#F3F1E6]">dossiê do georreferenciamento</strong> com o shapefile do SIG-RI e feche <strong className="text-[#F3F1E6]">contratos de exclusividade</strong> assinados pelo celular.
        </p>

        <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-5">
          <BotaoTeste codigo="SITE-HERO" />
          <Link
            to="/cadastro"
            className="inline-flex items-center justify-center gap-2 rounded-full px-7 h-14 text-base font-semibold border transition-colors hover:bg-white/5"
            style={{ color: CREME, borderColor: 'rgba(201,168,76,.55)' }}
          >
            Criar minha conta <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <p className="text-sm mb-9" style={{ color: 'rgba(243,241,230,.65)' }}>
          Atendimento no WhatsApp <span className="font-semibold" style={{ color: DOURADO }}>{WHATS_FMT}</span> · liberamos o seu teste na hora
        </p>

        <div className="flex flex-wrap gap-2">
          {DESTAQUES.map((d) => {
            const Icon = d.icon;
            return (
              <span key={d.label} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border" style={{ color: CREME, borderColor: 'rgba(201,168,76,.35)', background: 'rgba(255,255,255,.04)' }}>
                <Icon className="w-3.5 h-3.5" style={{ color: DOURADO }} />
                {d.label}
              </span>
            );
          })}
        </div>
      </div>

      <div className="min-w-0 relative animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
        <div className="relative mx-auto w-[62%] max-w-[360px] aspect-[4/5]">
          {LEQUE.map((c) => (
            <img
              key={c.src}
              src={c.src}
              alt={c.alt}
              width={720}
              height={900}
              decoding="async"
              className={`absolute inset-0 w-full h-full object-cover rounded-2xl ${c.cls}`}
              style={{ zIndex: c.z, boxShadow: '0 30px 60px -20px rgba(0,0,0,.7)', border: '1px solid rgba(201,168,76,.35)' }}
            />
          ))}
        </div>

        {/* Calculadora pública — continua em destaque para quem quer só saber o valor do imóvel */}
        <Link to="/quanto-vale-meu-imovel" className="group relative z-10 mt-16 flex items-center gap-4 rounded-2xl px-5 py-4 border transition-transform hover:-translate-y-0.5" style={{ background: CREME, borderColor: DOURADO }} aria-label="Calcular quanto vale meu imóvel">
          <span className="flex-none w-12 h-12 rounded-xl grid place-items-center" style={{ background: 'linear-gradient(135deg,#E0C264,#B08A2E)' }}>
            <Calculator className="w-6 h-6" style={{ color: VERDE }} />
          </span>
          <span className="flex-1 min-w-0">
            <span className="flex items-center gap-1.5 mb-0.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
              </span>
              <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700">Grátis · leva 1 minuto</span>
            </span>
            <span className="block font-extrabold text-lg leading-tight" style={{ color: VERDE }}>Quanto vale o seu imóvel?</span>
            <span className="block text-xs text-gray-600">Estimativa de mercado na hora, sem cadastro</span>
          </span>
          <ArrowRight className="w-5 h-5 flex-none text-amber-700 group-hover:translate-x-1 transition-transform" />
        </Link>
      </div>
    </div>
  </section>
);

export default Hero;
