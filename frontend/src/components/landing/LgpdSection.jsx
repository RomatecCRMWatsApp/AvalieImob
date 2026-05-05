// @module components/landing/LgpdSection — secao dedicada LGPD na home
// Reforca confianca explicitando praticas de protecao de dados.
import React from 'react';
import { Link } from 'react-router-dom';
import { Lock, ShieldCheck, FileLock, KeyRound, Trash2 } from 'lucide-react';

const PILARES = [
  {
    icon: ShieldCheck,
    titulo: 'Coleta mínima',
    desc: 'Pedimos apenas os dados estritamente necessários para prestar o serviço de avaliação imobiliária.',
  },
  {
    icon: FileLock,
    titulo: 'Armazenamento seguro',
    desc: 'Dados criptografados em repouso e em trânsito (TLS 1.3 + AES-256). Servidores em data centers com certificação ISO 27001.',
  },
  {
    icon: KeyRound,
    titulo: 'Senhas com hash bcrypt',
    desc: 'Senhas são armazenadas apenas como hash bcrypt — nem nossos engenheiros têm acesso à senha original.',
  },
  {
    icon: Trash2,
    titulo: 'Direito ao esquecimento',
    desc: 'Você pode solicitar a exclusão completa dos seus dados a qualquer momento. Atendido em até 15 dias.',
  },
];

export default function LgpdSection() {
  return (
    <section id="lgpd" className="py-20 bg-gradient-to-b from-emerald-50 to-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Selo grande à esquerda */}
          <div className="flex flex-col items-center lg:items-start gap-6">
            <div className="inline-flex items-center gap-3 bg-white rounded-2xl shadow-lg px-6 py-5 border border-emerald-100">
              <div className="flex items-center justify-center bg-emerald-500 rounded-xl p-3">
                <Lock className="w-10 h-10 text-white" strokeWidth={2.5} />
              </div>
              <div className="flex flex-col leading-none">
                <span className="text-xs font-semibold tracking-[0.2em] text-gray-500 uppercase mb-1">Certificado</span>
                <span className="text-4xl font-extrabold text-emerald-600 tracking-tight">LGPD</span>
              </div>
            </div>
            <Link
              to="/privacidade"
              className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-700 hover:text-emerald-900 hover:underline"
            >
              Ler nossa Política de Privacidade completa →
            </Link>
          </div>

          {/* Texto + pilares à direita */}
          <div>
            <div className="text-xs font-semibold tracking-[0.2em] text-emerald-600 mb-3">SEGURANÇA E PRIVACIDADE</div>
            <h2 className="font-display text-3xl md:text-4xl font-bold text-gray-900 leading-tight mb-4">
              Em conformidade com a LGPD
            </h2>
            <p className="text-gray-600 mb-8 leading-relaxed">
              O AvalieImob foi projetado desde o primeiro dia respeitando a Lei Geral de Proteção de Dados (Lei 13.709/2018). Seus dados de cliente, laudos e amostras de mercado ficam isolados e protegidos.
            </p>

            <div className="grid sm:grid-cols-2 gap-4">
              {PILARES.map((p, i) => (
                <div key={i} className="flex gap-3 p-4 bg-white rounded-xl border border-gray-100 shadow-sm">
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center">
                    <p.icon className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <div className="font-semibold text-sm text-gray-900 mb-1">{p.titulo}</div>
                    <div className="text-xs text-gray-600 leading-relaxed">{p.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
