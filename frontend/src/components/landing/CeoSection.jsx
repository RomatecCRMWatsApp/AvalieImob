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
        {/* Cross-link to parent company site */}
        <div className="mt-12 bg-gradient-to-r from-emerald-900 via-emerald-800 to-emerald-900 rounded-2xl p-8 text-white text-center">
          <div className="text-xs font-semibold tracking-[0.2em] text-amber-300 mb-3">FAMÍLIA ROMATEC</div>
          <h3 className="font-display text-2xl md:text-3xl font-bold mb-3">
            Conheça também a <span className="italic text-amber-300">RomaTec Consultoria Total</span>
          </h3>
          <p className="text-emerald-100 max-w-2xl mx-auto mb-6">
            Projetos, engenharia, agrimensura, georreferenciamento e regularização fundiária.
            Uma década de excelência técnica a serviço de empresas, construtoras e escritórios de engenharia.
          </p>
          <a
            href="https://www.consultoriaromatec.com.br"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-400 text-emerald-950 font-semibold px-6 py-3 rounded-lg transition-colors"
          >
            Visitar consultoriaromatec.com.br
            <span aria-hidden>→</span>
          </a>
        </div>
      </div>
    </section>
  );
};

export default CeoSection;
