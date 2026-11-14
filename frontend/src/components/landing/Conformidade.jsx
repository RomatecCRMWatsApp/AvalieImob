import React from 'react';
import { CheckCircle } from 'lucide-react';
import { VERDE, CREME } from './campanha';

const NORMAS = [
  'NBR 14.653-1:2019 — Avaliação de Bens (Procedimentos Gerais)',
  'NBR 14.653-2:2011 — Imóveis Urbanos',
  'NBR 14.653-3:2019 — Imóveis Rurais',
  'NBR 14.653-4:2002 — Empreendimentos',
  'COFECI — Resolução 1.066/2007 (PTAM por Corretor)',
  'CRECI — Registro profissional de Corretor de Imóveis',
  'CREA/CAU — Engenheiros e Arquitetos Avaliadores',
  'CNAI — Cadastro Nacional de Avaliadores Imobiliários',
  'Provimento CNJ 195/2025 — SIG-RI (mapa do imóvel no registro)',
  'Lei 10.267/2001 — Georreferenciamento de imóveis rurais',
  'Lei 14.063/2020 — Assinaturas eletrônicas',
  'MP 2.200-2/2001 — ICP-Brasil',
  'Lei 6.530/1978 — Regulamenta profissão de Corretor',
  'Lei 8.245/1991 — Lei do Inquilinato (Locação)',
  'LGPD — Lei 13.709/2018 (Proteção de Dados)',
  'INCRA — Cadastro Rural (SIGEF/CCIR/CAR)',
  'SFH/SFI — Sistema Financeiro Habitacional e Imobiliário',
  'Dec.-Lei 3.365/1941 — Desapropriações',
];

const Conformidade = () => (
  <section className="py-16 md:py-20" style={{ background: CREME }} aria-labelledby="conformidade-titulo">
    <div className="max-w-7xl mx-auto px-6">
      <p className="text-xs font-bold tracking-[0.28em] uppercase mb-3 text-[#9A7A1E]">Conformidade legal e normativa</p>
      <h2 id="conformidade-titulo" className="font-sans font-extrabold tracking-tight text-3xl md:text-4xl mb-8" style={{ color: VERDE }}>
        As normas que o sistema segue por você.
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {NORMAS.map((norma) => {
          const [sigla, ...resto] = norma.split(' — ');
          return (
            <div key={norma} className="flex items-start gap-2 bg-white/70 border border-[#C9A84C]/30 rounded-lg px-3 py-2.5">
              <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-[#9A7A1E]" />
              <span className="text-xs text-gray-700 leading-snug">
                <span className="font-semibold" style={{ color: VERDE }}>{sigla}</span>
                {resto.length > 0 && <span className="text-gray-500"> — {resto.join(' — ')}</span>}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  </section>
);

export default Conformidade;
