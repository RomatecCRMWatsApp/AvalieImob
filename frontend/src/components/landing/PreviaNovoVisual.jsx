// @module landing/PreviaNovoVisual — vídeo narrado da prévia do novo visual do painel.
// <video> nativo: controles, playsinline, preload=metadata, poster. Sem autoplay,
// loop ou muted — a narração do MP4 toca após o clique. As legendas já estão
// gravadas na imagem, por isso não há <track> ativo; VTT/SRT ficam para download.
// O vídeo foi gravado como prévia (fala em 'quando estiver disponível').
import React from 'react';
import { VERDE } from './campanha';

const BASE = '/video';

// Transcrição (Transcricao_Upgrade_AvalieImob.txt), dividida pelas cenas.
const TRANSCRICAO = [
  'Usar o AvalieImob vai ficar ainda mais simples. Estamos preparando uma nova interface, mais limpa, moderna e organizada, mantendo o verde e o dourado que você já conhece.',
  'A proposta começa pela tela inicial. O painel destaca as principais informações e dá mais visibilidade às ações do dia a dia, como criar um laudo ou cadastrar um cliente.',
  'Na navegação, os recursos ficam agrupados por finalidade: cadastros, laudos e avaliações, contratos e documentos e módulos geoespaciais. Assim, você encontra a área de que precisa sem enfrentar uma lista extensa de opções.',
  'Os indicadores ganham uma apresentação mais clara, com números e valores fáceis de ler. E as imagens dos módulos ajudam a identificar cada área, sem atrapalhar formulários e informações.',
  'No celular, a prioridade é aproveitar melhor o espaço. Botões mais fáceis de tocar, menu organizado e menos elementos sobrepostos pra deixar o conteúdo no centro da experiência.',
  'As ferramentas de apoio como ROMA-IA, fotos e consulta de CPF e CNPJ passam a ter uma área de acesso mais organizada, sem as abas cobrindo o painel.',
  'O foco deste upgrade é o visual e a navegação. Não estamos propondo mudanças nos seus registros, cálculos ou permissões. A ideia é melhorar a forma de acessar os recursos que você já utiliza.',
  'Essa é a direção da nova experiência do AvalieImob. Acompanhe a atualização e, quando ela estiver disponível, explore o novo painel. Em caso de dúvida, fale com o nosso atendimento.',
];

// Vídeos verticais de campanha (1080×1920) — mesmos arquivos da aba Divulgação.
const DIR_CAMPANHA = '/video/apresentacoes';
const VIDEOS_MODULOS = [
  { arquivo: 'AvalieImob_ptam_1080x1920', titulo: 'PTAM e laudos', desc: 'Clientes, imóveis e amostras conectados; laudo com a sua marca.' },
  { arquivo: 'AvalieImob_onr_1080x1920', titulo: 'Shapefile urbano (SIG-RI)', desc: 'Prov. CNJ 195/2025: envie os documentos e receba o pacote para o SIG-RI.' },
  { arquivo: 'AvalieImob_geo_1080x1920', titulo: 'Georreferenciamento', desc: 'Do memorial do SIGEF ao dossiê, sem espalhar o processo.' },
];

const PreviaNovoVisual = () => (
  <section
    aria-labelledby="titulo-preview-upgrade"
    className="py-16 md:py-20 bg-[#F3F1E6] dark:bg-[#0C3320]"
  >
    <div className="max-w-5xl mx-auto px-4 sm:px-6">
      <p className="text-xs font-bold tracking-[0.28em] uppercase mb-3 text-[#9A7A1E] dark:text-[#C9A84C]">
        Prévia de layout
      </p>
      <h2
        id="titulo-preview-upgrade"
        className="font-sans font-extrabold tracking-tight text-3xl md:text-4xl mb-3 dark:!text-[#F3F1E6]"
        style={{ color: VERDE }}
      >
        Conheça a prévia do novo visual
      </h2>
      <p id="descricao-preview-upgrade" className="text-base text-gray-700 dark:text-[#d7e3da] mb-6 max-w-3xl">
        Apresentação narrada do novo visual do painel do AvalieImob: navegação agrupada por finalidade,
        indicadores mais legíveis e ferramentas reunidas em um só lugar.
      </p>

      <div className="w-full rounded-2xl overflow-hidden shadow-lg border border-[#C9A84C]/30 bg-black" style={{ aspectRatio: '16 / 9' }}>
        <video
          controls
          playsInline
          preload="metadata"
          poster={`${BASE}/Poster_Upgrade_AvalieImob.jpg`}
          aria-label="Vídeo: prévia narrada do novo visual do AvalieImob"
          aria-describedby="descricao-preview-upgrade transcricao-preview-upgrade"
          width="1280"
          height="720"
          className="block w-full h-full"
          style={{ aspectRatio: '16 / 9', objectFit: 'contain' }}
        >
          <source src={`${BASE}/AvalieImob_Upgrade_Web_1280x720.mp4`} type="video/mp4" />
          {/* Sem <track> ativo: as legendas já estão incorporadas no MP4. */}
          Seu navegador não consegue reproduzir este vídeo. Leia a transcrição abaixo.
        </video>
      </div>

      <details
        id="transcricao-preview-upgrade"
        className="mt-5 rounded-xl border border-[#C9A84C]/30 bg-white/80 dark:bg-white/5 px-4 sm:px-5"
      >
        <summary className="cursor-pointer py-3 min-h-[44px] flex items-center text-sm font-semibold text-[#0C3320] dark:text-[#F3F1E6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#9A7A1E] rounded">
          Leia a transcrição da apresentação
        </summary>
        <div className="pb-4 space-y-3 text-sm leading-relaxed text-gray-700 dark:text-[#d7e3da]">
          {TRANSCRICAO.map((t) => <p key={t.slice(0, 24)}>{t}</p>)}
          <p className="text-xs pt-1">
            Legendas para download:{' '}
            <a className="underline text-[#7A5E12] dark:text-[#C9A84C]" href={`${BASE}/Legendas_Upgrade_AvalieImob.vtt`} download>WebVTT (.vtt)</a>
            {' · '}
            <a className="underline text-[#7A5E12] dark:text-[#C9A84C]" href={`${BASE}/Legendas_Upgrade_AvalieImob.srt`} download>SubRip (.srt)</a>
          </p>
        </div>
      </details>

      <h3 className="font-sans font-extrabold tracking-tight text-2xl md:text-3xl mt-12 mb-2 dark:!text-[#F3F1E6]" style={{ color: VERDE }}>
        Veja os módulos em ação
      </h3>
      <p className="text-base text-gray-700 dark:text-[#d7e3da] mb-6 max-w-3xl">
        Vídeos curtos do PTAM, do shapefile urbano e do georreferenciamento.
      </p>
      <div className="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-2 -mx-4 px-4 sm:mx-0 sm:px-0 sm:grid sm:grid-cols-3 sm:gap-6 sm:overflow-visible max-w-4xl">
        {VIDEOS_MODULOS.map((v) => (
          <figure key={v.arquivo} className="min-w-0 w-[44%] shrink-0 snap-start sm:w-auto">
            <div className="rounded-2xl overflow-hidden shadow-lg border border-[#C9A84C]/30 bg-black" style={{ aspectRatio: '9 / 16' }}>
              <video
                controls
                playsInline
                preload="none"
                poster={`${DIR_CAMPANHA}/${v.arquivo}.jpg`}
                aria-label={`Vídeo: ${v.titulo}`}
                width="1080"
                height="1920"
                className="block w-full h-full"
                style={{ objectFit: 'contain' }}
              >
                <source src={`${DIR_CAMPANHA}/${v.arquivo}.mp4`} type="video/mp4" />
                Seu navegador não consegue reproduzir este vídeo.
              </video>
            </div>
            <figcaption className="mt-2">
              <span className="block text-sm sm:text-base font-semibold text-[#0C3320] dark:text-[#F3F1E6]">{v.titulo}</span>
              <span className="block text-xs sm:text-sm text-gray-600 dark:text-[#d7e3da]">{v.desc}</span>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  </section>
);

export default PreviaNovoVisual;
