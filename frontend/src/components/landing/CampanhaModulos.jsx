import React from 'react';
import { Check, MessageCircle } from 'lucide-react';
import { MODULOS, VERDE, DOURADO, CREME, whatsLink } from './campanha';
import PreviaAnaliseAvancada from './PreviaAnaliseAvancada';
import DemoPtam12Passos from './DemoPtam12Passos';

// Ícone do WhatsApp (o lucide não tem a marca).
export const WhatsIcon = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true">
    <path d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.61-.92-2.21-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.21 3.08c.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.69.63.71.23 1.36.2 1.87.12.57-.08 1.76-.72 2.01-1.42.25-.7.25-1.29.17-1.42-.07-.12-.27-.2-.57-.35zM12.05 21.5h-.01a9.4 9.4 0 0 1-4.8-1.31l-.34-.2-3.57.94.95-3.48-.22-.36a9.43 9.43 0 1 1 7.99 4.41zm8.02-17.47A11.25 11.25 0 0 0 2.36 17.6L.77 23.4l5.94-1.56a11.2 11.2 0 0 0 5.34 1.36h.01c6.2 0 11.25-5.05 11.25-11.25 0-3-1.17-5.83-3.24-7.92z" />
  </svg>
);

export const BotaoTeste = ({ codigo, assunto, children = 'Solicite seu acesso de teste', className = '' }) => (
  <a
    href={whatsLink(codigo, assunto)}
    target="_blank"
    rel="noopener noreferrer"
    className={`inline-flex items-center justify-center gap-3 rounded-full px-7 h-14 text-base font-extrabold tracking-tight shadow-lg transition-transform hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${className}`}
    style={{
      background: 'linear-gradient(180deg,#E8CF7A 0%,#C9A84C 55%,#B08A2E 100%)',
      color: VERDE,
      boxShadow: '0 12px 28px -10px rgba(201,168,76,.65), inset 0 1px 0 rgba(255,255,255,.45)',
    }}
  >
    <WhatsIcon className="w-6 h-6" />
    {children}
  </a>
);

const Modulo = ({ m, indice }) => {
  const escuro = m.escuro;
  const texto = escuro ? 'text-[#F3F1E6]' : 'text-[#0C3320]';
  const suave = escuro ? 'text-[#F3F1E6]/80' : 'text-[#0C3320]/75';
  const invertido = indice % 2 === 1;

  return (
    <section
      id={m.id}
      className="relative overflow-hidden py-20 md:py-28"
      style={{ background: escuro ? VERDE : CREME }}
      aria-labelledby={`${m.id}-titulo`}
    >
      <CurvasTopo cor={escuro ? 'rgba(201,168,76,.16)' : 'rgba(201,168,76,.22)'} />
      <div className="relative max-w-7xl mx-auto px-6 grid lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-12 items-center">
        <div className={`min-w-0 ${invertido ? 'lg:order-2' : ''}`}>
          <p className="text-xs font-bold tracking-[0.28em] uppercase mb-5" style={{ color: DOURADO }}>{m.eyebrow}</p>
          <h2 id={`${m.id}-titulo`} className={`font-sans font-extrabold tracking-tight leading-[1.02] text-4xl md:text-5xl ${texto}`} style={{ textWrap: 'balance' }}>
            {m.titulo}{' '}
            <span style={{ color: escuro ? DOURADO : '#9A7A1E' }}>{m.destaque}</span>
          </h2>
          <div className="w-16 h-[3px] rounded-full my-6" style={{ background: DOURADO }} />
          <p className={`text-lg leading-relaxed mb-6 ${suave}`}>{m.texto}</p>
          <ul className="space-y-3 mb-9">
            {m.itens.map((it) => (
              <li key={it} className={`flex items-start gap-3 ${texto}`}>
                <span className="mt-0.5 flex-none w-6 h-6 rounded-full grid place-items-center" style={{ background: DOURADO }}>
                  <Check className="w-4 h-4" style={{ color: VERDE }} strokeWidth={3} />
                </span>
                <span className="font-medium">{it}</span>
              </li>
            ))}
          </ul>
          <BotaoTeste codigo={m.codigo} assunto={m.assunto}>{m.cta}</BotaoTeste>
        </div>

        <div className={`min-w-0 ${invertido ? 'lg:order-1' : ''}`}>
          <div
            className="flex gap-4 overflow-x-auto snap-x snap-mandatory pb-4 -mx-6 px-6 lg:mx-0 lg:px-0"
            style={{ scrollbarWidth: 'thin' }}
            tabIndex={0}
            aria-label={`Apresentação do módulo: ${m.titulo} ${m.destaque}`}
          >
            {m.imagens.map((img, i) => (
              <img
                key={img.src}
                src={img.src}
                alt={img.alt}
                width={720}
                height={900}
                loading={i < 2 ? 'eager' : 'lazy'}
                decoding="async"
                className="snap-start flex-none w-[78%] sm:w-[46%] lg:w-[48%] rounded-2xl"
                style={{ boxShadow: escuro ? '0 24px 48px -20px rgba(0,0,0,.6)' : '0 24px 48px -24px rgba(12,51,32,.45)', border: `1px solid ${escuro ? 'rgba(201,168,76,.25)' : 'rgba(12,51,32,.08)'}` }}
              />
            ))}
          </div>
          <p className={`text-xs mt-2 flex items-center gap-2 ${suave}`}>
            <MessageCircle className="w-3.5 h-3.5" /> Arraste para ver a apresentação completa
          </p>
        </div>
      </div>
    </section>
  );
};

// Curvas de nível em dourado, o motivo das artes da campanha.
export const CurvasTopo = ({ cor }) => (
  <svg className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none" viewBox="0 0 1200 800" aria-hidden="true">
    {[0, 1, 2, 3, 4, 5, 6].map((k) => (
      <path
        key={k}
        d={`M-50 ${120 + k * 26} C 250 ${40 + k * 30}, 420 ${260 + k * 22}, 700 ${160 + k * 24} S 1100 ${60 + k * 28}, 1260 ${180 + k * 24}`}
        fill="none" stroke={cor} strokeWidth="1.2"
      />
    ))}
    {[0, 1, 2, 3, 4].map((k) => (
      <path
        key={`b${k}`}
        d={`M-50 ${640 + k * 22} C 300 ${560 + k * 26}, 520 ${760 + k * 18}, 860 ${650 + k * 22} S 1150 ${600 + k * 20}, 1260 ${700 + k * 20}`}
        fill="none" stroke={cor} strokeWidth="1"
      />
    ))}
  </svg>
);

const CampanhaModulos = () => (
  <div id="modulos">
    {MODULOS.map((m, i) => (
      <React.Fragment key={m.id}>
        <Modulo m={m} indice={i} />
        {/* Prévia logo após a Avaliação, onde a análise de amostras é apresentada. */}
        {m.id === 'avaliacao' && <DemoPtam12Passos />}
        {m.id === 'avaliacao' && <PreviaAnaliseAvancada />}
      </React.Fragment>
    ))}
  </div>
);

export default CampanhaModulos;
