import React from 'react';
import { Award, MapPin, Phone, Mail, Globe, Briefcase, GraduationCap, Building } from 'lucide-react';

const CERTIFICATIONS = [
  { label: 'Avaliador Imobiliário Certificado', code: 'CNAI nº 031161' },
  { label: 'Técnico em Transações Imobiliárias', code: 'CRECI nº 4.705' },
  { label: 'Técnico em Edificações', code: 'CFT BR nº 0120918536-9' },
  { label: 'Técnico em Agrimensura', code: 'Código INCRA: FQNS' },
];

const EXPERTISE = [
  'Engenharia aplicada e gestão de projetos',
  'Agrimensura, geoprocessamento e georreferenciamento',
  'Avaliações imobiliárias e estudos mercadológicos',
  'Topografia, planialtimétrica e modelagem do terreno',
  'Laudos técnicos e vistorias de engenharia',
  'Perícias imobiliárias e pareceres técnicos',
  'Regularização fundiária urbana e rural',
  'Soluções integradas de engenharia e tecnologia',
];

const EXPERIENCE_HIGHLIGHTS = [
  { years: '12+', label: 'anos à frente da RomaTec' },
  { years: '15', label: 'anos como Consultor Registral' },
  { years: 'Desde 2012', label: 'CEO & Fundador' },
];

const CeoSection = () => {
  return (
    <section id="ceo" className="py-24 bg-gradient-to-b from-white to-emerald-50/30">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="text-xs font-semibold tracking-[0.2em] text-emerald-700 mb-3">LIDERANÇA</div>
          <h2 className="font-display text-4xl md:text-5xl font-bold text-gray-900 leading-tight mb-4">
            Conheça o <span className="brand-green italic">idealizador</span>
          </h2>
          <p className="text-gray-600 text-lg">
            Mais de uma década de experiência consolidada em engenharia, agrimensura e avaliações imobiliárias.
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 mb-12">
          {/* Profile card */}
          <div className="bg-white rounded-2xl border border-emerald-900/10 p-8 shadow-sm">
            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-700 to-emerald-900 flex items-center justify-center mb-6 mx-auto">
              <span className="font-display text-4xl font-bold text-white">JR</span>
            </div>
            <div className="text-center">
              <h3 className="font-display text-2xl font-bold text-gray-900">José Romário Pinto Bezerra</h3>
              <p className="text-sm text-emerald-800 font-semibold mt-1">CEO & Fundador</p>
              <p className="text-xs text-gray-500 mt-1">RomaTec Consultoria Total — Desde 2012</p>
            </div>

            <div className="mt-8 space-y-3 text-sm">
              <div className="flex items-start gap-3">
                <MapPin className="w-4 h-4 text-emerald-700 mt-0.5 flex-shrink-0" />
                <span className="text-gray-600">Rua São Raimundo, nº 10, Centro — Açailândia/MA</span>
              </div>
              <div className="flex items-start gap-3">
                <Phone className="w-4 h-4 text-emerald-700 mt-0.5 flex-shrink-0" />
                <span className="text-gray-600">(99) 99181-1246</span>
              </div>
              <div className="flex items-start gap-3">
                <Mail className="w-4 h-4 text-emerald-700 mt-0.5 flex-shrink-0" />
                <span className="text-gray-600 break-all">contato@consultoriaromatec.com.br</span>
              </div>
              <div className="flex items-start gap-3">
                <Globe className="w-4 h-4 text-emerald-700 mt-0.5 flex-shrink-0" />
                <a href="https://www.consultoriaromatec.com.br" target="_blank" rel="noreferrer" className="text-emerald-800 hover:underline break-all">
                  www.consultoriaromatec.com.br
                </a>
              </div>
            </div>
          </div>

          {/* Bio + certifications */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-2xl border border-gray-200 p-8">
              <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 tracking-[0.2em] mb-4">
                <Briefcase className="w-4 h-4" />PERFIL PROFISSIONAL
              </div>
              <p className="text-gray-700 leading-relaxed mb-4">
                Especialista em Projetos, Engenharia, Agrimensura e Avaliações Imobiliárias, com atuação multidisciplinar
                em diagnósticos, levantamentos e soluções construtivas. Atua estrategicamente na gestão e execução de projetos
                arquitetônicos, estruturais, georreferenciamento, topografia, regularização fundiária e certificações técnicas.
              </p>
              <p className="text-gray-700 leading-relaxed">
                Consultor registral com 15 anos de atuação junto ao Cartório do 1º Ofício Extrajudicial de Açailândia/MA,
                trazendo visão completa sobre a cadeia imobiliária — análise documental, conferência de matrículas, relatórios
                técnicos de regularização e interface com órgãos públicos.
              </p>
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 p-8">
              <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 tracking-[0.2em] mb-5">
                <GraduationCap className="w-4 h-4" />QUALIFICAÇÕES E CERTIFICAÇÕES
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                {CERTIFICATIONS.map((c) => (
                  <div key={c.code} className="flex items-start gap-3 p-3 rounded-lg bg-emerald-50/50 border border-emerald-900/10">
                    <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center flex-shrink-0">
                      <Award className="w-4 h-4 text-amber-600" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-900">{c.label}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{c.code}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
          {EXPERIENCE_HIGHLIGHTS.map((h) => (
            <div key={h.label} className="bg-gradient-to-br from-emerald-900 to-emerald-950 text-white rounded-2xl p-8 text-center">
              <div className="font-display text-4xl md:text-5xl font-bold text-amber-300">{h.years}</div>
              <div className="text-sm text-emerald-200 mt-2">{h.label}</div>
            </div>
          ))}
        </div>

        {/* Expertise */}
        <div className="bg-white rounded-2xl border border-gray-200 p-8">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 tracking-[0.2em] mb-6">
            <Building className="w-4 h-4" />COMPETÊNCIAS E ESPECIALIDADES
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {EXPERTISE.map((item) => (
              <div key={item} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-700 mt-2 flex-shrink-0" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
        {/* Família Romatec — dois logos lado a lado */}
        <div className="mt-12 bg-gradient-to-r from-emerald-900 via-emerald-800 to-emerald-900 rounded-2xl p-8 text-white text-center">
          <div className="text-xs font-semibold tracking-[0.2em] text-amber-300 mb-3">FAMÍLIA ROMATEC</div>
          <h3 className="font-display text-2xl md:text-3xl font-bold mb-8">
            Conheça o nosso <span className="italic text-amber-300">ecossistema</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {/* Romatec Engenharia e Agrimensura */}
            <div className="bg-white/10 hover:bg-white/20 transition-colors rounded-xl p-6 flex flex-col items-center gap-4">
              <a
                href="https://www.consultoriaromatec.com.br"
                target="_blank"
                rel="noreferrer"
                aria-label="Visitar consultoriaromatec.com.br"
              >
                <img
                  src="/brand/romatec_ea.jpg"
                  alt="Romatec Consultoria Total — Engenharia e Agrimensura"
                  className="h-24 w-auto object-contain rounded-lg"
                />
              </a>
              <div>
                <div className="font-semibold text-white text-sm mb-1">Romatec Consultoria Total</div>
                <div className="text-xs text-emerald-200 mb-4">Engenharia &amp; Agrimensura</div>
                <a
                  href="https://www.consultoriaromatec.com.br"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-400 text-emerald-950 font-semibold px-5 py-2 rounded-lg transition-colors text-sm"
                >
                  Visitar consultoriaromatec.com.br
                  <span aria-hidden>→</span>
                </a>
              </div>
            </div>

            {/* Romanutri */}
            <div className="bg-white/10 hover:bg-white/20 transition-colors rounded-xl p-6 flex flex-col items-center gap-4">
              <a
                href="https://www.instagram.com/espaco_romanutri_rn"
                target="_blank"
                rel="noreferrer"
                aria-label="Ver Romanutri no Instagram"
              >
                <img
                  src="/brand/romanutri.jpg"
                  alt="Romanutri — Espaço de Nutrição"
                  className="h-24 w-auto object-contain rounded-lg"
                />
              </a>
              <div>
                <div className="font-semibold text-white text-sm mb-1">Romanutri</div>
                <div className="text-xs text-emerald-200 mb-4">Nutrição &amp; Saúde</div>
                <a
                  href="https://www.instagram.com/espaco_romanutri_rn"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 bg-pink-500 hover:bg-pink-400 text-white font-semibold px-5 py-2 rounded-lg transition-colors text-sm"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/>
                  </svg>
                  @espaco_romanutri_rn
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default CeoSection;
