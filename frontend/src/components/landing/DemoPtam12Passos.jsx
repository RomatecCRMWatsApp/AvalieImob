import React from 'react';
import { VERDE, DOURADO, DOURADO_CLARO, CREME } from './campanha';

// Demonstração narrada do PTAM em 12 passos (kit de 15/11/2026).
// Só apresentação: não mexe em rota, motor, plano ou cobrança. O botão leva ao
// cadastro que já existe. Legendas já vêm gravadas na imagem — a faixa VTT fica
// opcional (sem `default`) para não aparecer duas legendas.
const VIDEO = '/video/apresentacoes/AvalieImob_PTAM_Demonstracao_Web_1280x720';
const CADASTRO = '/cadastro?utm_source=site&utm_medium=video&utm_campaign=ptam_12_passos_demo';

const CAPITULOS = [
  [28, 'Solicitante'], [47, 'Objetivo'], [65, 'Imóvel'], [91, 'Região'],
  [107, 'Caracterização'], [131, 'Amostras'], [159, 'Metodologia'], [177, 'Cálculos'],
  [201, 'Ponderação'], [219, 'Depreciação'], [239, 'Resultado'], [268, 'Conclusão'],
  [288, 'PTAM exportado'], [317, 'Assinatura e entrega'],
];
const mmss = (t) => `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;

const DemoPtam12Passos = () => {
  const videoRef = React.useRef(null);
  const boxRef = React.useRef(null);
  const [src, setSrc] = React.useState(null);

  // Só atribui o arquivo perto da entrada na tela (13 MB). Sem IntersectionObserver,
  // atribui de imediato; o toque/clique no player também garante o carregamento.
  React.useEffect(() => {
    if (src) return undefined;
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      setSrc(`${VIDEO}.mp4`);
      return undefined;
    }
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { setSrc(`${VIDEO}.mp4`); io.disconnect(); }
    }, { rootMargin: '300px 0px' });
    if (boxRef.current) io.observe(boxRef.current);
    return () => io.disconnect();
  }, [src]);

  // Link de divulgação chega com #ptam-12-passos: rola até aqui depois que a página monta.
  React.useEffect(() => {
    if (typeof window === 'undefined' || window.location.hash !== '#ptam-12-passos') return undefined;
    const t = setTimeout(() => boxRef.current?.closest('section')?.scrollIntoView({ block: 'start' }), 400);
    return () => clearTimeout(t);
  }, []);

  const garantir = () => { if (!src) setSrc(`${VIDEO}.mp4`); };

  const irPara = (t) => {
    garantir();
    const el = videoRef.current;
    if (!el) return;
    const tocar = () => { el.currentTime = t; el.play().catch(() => {}); };
    if (el.readyState >= 1) tocar();
    else el.addEventListener('loadedmetadata', tocar, { once: true });
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  return (
    <section id="ptam-12-passos" aria-labelledby="ptam-12-titulo"
      className="px-4 py-14 sm:py-20" style={{ background: VERDE, color: CREME }}>
      <div className="max-w-5xl mx-auto">
        <p className="text-xs font-bold uppercase tracking-[0.2em]" style={{ color: DOURADO_CLARO }}>
          Demonstração · 6 minutos
        </p>
        <h2 id="ptam-12-titulo" className="mt-2 text-3xl sm:text-4xl font-extrabold leading-tight">
          Veja o PTAM em 12 passos
        </h2>
        <p className="mt-3 max-w-2xl text-base" style={{ color: '#C9D8CE' }}>
          Do cadastro do solicitante ao documento com capa, sumário e anexos: amostras com imagens e
          planta baixa do comparável, tratamentos e memória de cálculo. Você revisa e assina; a
          plataforma apoia o seu trabalho.
        </p>

        <div ref={boxRef} onPointerDown={garantir} className="mt-7 rounded-[20px] overflow-hidden"
          style={{ background: '#051e15', border: `1px solid ${DOURADO}33` }}>
          <video ref={videoRef} controls playsInline preload="metadata" src={src || undefined}
            poster={`${VIDEO}.jpg`} aria-label="Demonstração do PTAM em 12 passos no AvalieImob"
            className="block w-full" style={{ aspectRatio: '16 / 9', objectFit: 'contain' }}>
            <track kind="captions" srcLang="pt-BR" label="Português (Brasil)" src={`${VIDEO}.vtt`} />
            Seu navegador não consegue reproduzir este vídeo.
          </video>
        </div>

        <nav aria-label="Capítulos da demonstração" className="mt-4 flex flex-wrap gap-2">
          {CAPITULOS.map(([t, nome], i) => (
            <button key={t} type="button" onClick={() => irPara(t)}
              className="text-xs px-3 py-1.5 rounded-full border transition-colors hover:bg-white/10"
              style={{ borderColor: `${DOURADO}55`, color: CREME }}>
              <span style={{ color: DOURADO_CLARO }}>{mmss(t)}</span>{' '}
              {i < 12 ? `${i + 1}. ` : ''}{nome}
            </button>
          ))}
        </nav>

        <div className="mt-8 flex flex-col sm:flex-row sm:items-center gap-3">
          <a href={CADASTRO}
            className="inline-flex items-center justify-center rounded-xl px-6 py-3.5 font-bold"
            style={{ background: DOURADO, color: VERDE }}>
            Cadastre-se e experimente
          </a>
          <p className="text-sm" style={{ color: '#C9D8CE' }}>
            7 dias grátis. Depois, a contratação é opcional — sem cobrança automática.
          </p>
        </div>
      </div>
    </section>
  );
};

export default DemoPtam12Passos;
