import React from 'react';
import '../../styles/carrossel-inferencia.css';
import { WhatsIcon } from './CampanhaModulos';

// Prévia da Análise Estatística Avançada (kit de 15/11/2026).
// É PRÉVIA: CTA "Conhecer a proposta" (WhatsApp), nunca "Usar agora".
// Rolagem nativa com snap, igual aos demais blocos de apresentação — sem biblioteca.
const DIR = '/campanha/analise-avancada';
const ZAP = 'https://wa.me/5599991811246?text=' + encodeURIComponent(
  'Olá! Vi a prévia da Análise Estatística Avançada do AvalieImob. Quero conhecer a proposta e acompanhar sua liberação.');
const VIDEO = '/video/apresentacoes/AvalieImob_Previa_Analise_Avancada_1080x1920';

const PAGINAS = [
  { n: '01', alt: 'Capa: sua amostra merece mais análise. Análise Estatística Avançada, nova opção em preparação.',
    legenda: 'Conheça a proposta de análise estatística avançada.' },
  { n: '02', alt: 'Página 2: a análise começa nos dados — amostras e variáveis organizadas; o avaliador define e revisa o modelo.',
    legenda: 'A análise começa nos dados; o avaliador define e revisa o modelo.' },
  { n: '03', alt: 'Página 3: mais que um valor, diagnósticos — resíduos, influência e coerência do modelo; alertas pedem análise, não exclusão automática.',
    legenda: 'Diagnósticos: resíduos, influência e pressupostos.' },
  { n: '04', alt: 'Página 4: estimativas com contexto — intervalos e memória de cálculo, modelo documentado e revisão do avaliador.',
    legenda: 'Intervalos de confiança e de predição, com memória de cálculo.' },
  { n: '05', alt: 'Página 5: quer conhecer a proposta? Em preparação, liberação após implementação e validação. WhatsApp (99) 99181-1246.',
    legenda: 'Em preparação — fale com a Romatec para acompanhar.' },
];

const PreviaAnaliseAvancada = () => (
  <section id="analise-avancada" className="av-inferencia" aria-labelledby="analise-avancada-titulo">
    <div className="av-inferencia__layout">
      <div className="av-inferencia__copy">
        <span className="av-inferencia__status">Prévia — em preparação</span>
        <h2 id="analise-avancada-titulo" className="av-inferencia__title font-sans">
          Análise Estatística Avançada
        </h2>
        <p className="av-inferencia__description">
          Uma proposta adicional para escolher variáveis, conferir diagnósticos e documentar a
          análise das amostras, sem substituir os tratamentos atuais — inclusive o tratamento
          científico que você já usa no laudo. Liberação após implementação e validação.
        </p>
        <div className="av-inferencia__actions">
          <a className="av-inferencia__cta" href={ZAP} target="_blank" rel="noopener noreferrer">
            <WhatsIcon className="w-5 h-5 mr-2" /> Conhecer a proposta
          </a>
        </div>
        <video className="av-inferencia__video" controls playsInline preload="none"
          poster={`${VIDEO}.jpg`} aria-label="Prévia da proposta de análise estatística avançada do AvalieImob">
          <source src={`${VIDEO}.mp4`} type="video/mp4" />
          <track kind="captions" src={`${VIDEO}.vtt`} srcLang="pt-BR" label="Português" default />
          Seu navegador não reproduz este vídeo.
        </video>
      </div>

      <div className="av-inferencia__media">
        <div className="av-inferencia__track" tabIndex={0} role="region"
          aria-label="Apresentação da prévia de análise estatística avançada">
          {PAGINAS.map((p, i) => (
            <figure key={p.n} className="av-inferencia__slide">
              <a className="av-inferencia__art-link" href={`${DIR}/${p.n}.webp`} target="_blank" rel="noopener noreferrer"
                aria-label={`Abrir a página ${i + 1} da prévia em tamanho maior, em nova aba`}>
                <img className="av-inferencia__image" src={`${DIR}/${p.n}.webp`} width={1080} height={1350}
                  loading="lazy" decoding="async" alt={p.alt} />
              </a>
              <figcaption className="av-inferencia__caption">{i + 1} de 5 — {p.legenda}</figcaption>
            </figure>
          ))}
        </div>
        <p className="av-inferencia__hint">Deslize para ver as páginas. Abra uma arte para ampliar.</p>
      </div>
    </div>
  </section>
);

export default PreviaAnaliseAvancada;
