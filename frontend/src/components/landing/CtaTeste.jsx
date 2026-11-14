import React from 'react';
import { BrandMark } from '../brand/BrandMark';
import { VERDE, DOURADO, CREME, WHATS_FMT } from './campanha';
import { BotaoTeste, CurvasTopo } from './CampanhaModulos';

const CtaTeste = () => (
  <section className="relative overflow-hidden py-20 md:py-24" style={{ background: VERDE }} aria-labelledby="cta-teste-titulo">
    <CurvasTopo cor="rgba(201,168,76,.16)" />
    <div className="relative max-w-3xl mx-auto px-6 text-center flex flex-col items-center">
      <BrandMark variant="badge" size={64} />
      <p className="mt-6 text-xs font-bold tracking-[0.3em] uppercase px-4 py-2 rounded-full border" style={{ color: DOURADO, borderColor: 'rgba(201,168,76,.5)' }}>
        Acesso de teste
      </p>
      <h2 id="cta-teste-titulo" className="mt-6 font-sans font-extrabold tracking-tight leading-[1.04] text-4xl md:text-6xl" style={{ color: CREME, textWrap: 'balance' }}>
        Sua próxima captação <span style={{ color: DOURADO }}>começa aqui.</span>
      </h2>
      <div className="w-16 h-[3px] rounded-full my-7" style={{ background: DOURADO }} />
      <p className="text-lg mb-9 max-w-xl" style={{ color: 'rgba(243,241,230,.8)' }}>
        Chame no WhatsApp, a gente libera o seu acesso de teste e mostra o sistema em 10 minutos com o seu próprio caso.
      </p>
      <BotaoTeste codigo="SITE-RODAPE" className="w-full sm:w-auto" />
      <p className="mt-5 text-lg font-bold" style={{ color: CREME }}>{WHATS_FMT}</p>
    </div>
  </section>
);

export default CtaTeste;
