// @page admin/Divulgação — links dos folders de divulgação + WhatsApp + QR Code.
import React, { useRef } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import { Megaphone, Copy, ExternalLink, Download, Send, Search, Share2 } from 'lucide-react';
import { useToast } from '../../hooks/use-toast';
import { adminAPI } from '../../lib/api';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const BASE = 'https://www.romatecavalieimob.com.br';

// ── Marcação de origem (UTM) ────────────────────────────────────────────────
// Sem isso, todo cadastro que vem dos folders aparece como "Direto" no painel de
// Leads — o link não conta de onde veio. Com a marcação, cada peça é rastreada
// separadamente: dá para saber qual folder e qual canal trouxe o assinante.
// Os folders são HTML estático e repassam a marcação ao /cadastro por um script
// próprio (frontend/public/folder/*.html) — sem ele a origem morreria ali.
const comUtm = (url, { source, medium, campaign }) => {
  const u = new URL(url);
  u.searchParams.set('utm_source', source);
  u.searchParams.set('utm_medium', medium);
  if (campaign) u.searchParams.set('utm_campaign', campaign);
  return u.toString();
};

// Canal por onde a peça é entregue — vira `utm_source` no painel.
const CANAIS = {
  whatsapp: { source: 'whatsapp', medium: 'folder', rotulo: 'WhatsApp' },
  link: { source: 'link', medium: 'folder', rotulo: 'link copiado' },
  qr: { source: 'qrcode', medium: 'impresso', rotulo: 'QR Code' },
};

const linkDe = (f, canal) => comUtm(f.url, { ...CANAIS[canal], campaign: `folder-${f.file}` });

const FOLDERS = [
  {
    file: 'geral', titulo: 'Sistema completo (Geral)',
    desc: 'Visão do sistema todo — o link único para compartilhar em qualquer grupo.',
    url: `${BASE}/folder/`,
    msg: 'Conheça o AvalieImob — avaliação, contratos e georreferenciamento num só sistema:',
  },
  {
    file: 'avaliacao', titulo: 'Avaliação Imobiliária (PTAM)',
    desc: 'Para corretores — laudos NBR 14.653 com IA, fotos GPS, ART/TRT e assinatura ICP.',
    url: `${BASE}/folder/avaliacao.html`,
    msg: 'Seu laudo de avaliação (PTAM) pronto e assinado em minutos:',
  },
  {
    file: 'contratos', titulo: 'Contratos, Recibos & Assinatura',
    desc: 'Exclusividade + procuração, recibos, assinatura por WhatsApp e certificado ICP-Brasil.',
    url: `${BASE}/folder/contratos.html`,
    msg: 'Contratos e recibos assinados pelo WhatsApp, com validade jurídica:',
  },
  {
    file: 'topografia', titulo: 'Topografia & Geo',
    desc: 'Georreferenciamento rural/urbano, averbação, desmembramento, Shapefile SIG-RI e Dossiê.',
    url: `${BASE}/folder/topografia.html`,
    msg: 'Georreferenciamento, averbação e desmembramento — do memorial ao cartório:',
  },
];

// A calculadora é a porta de entrada de lead mais direta: o visitante deixa
// contato para receber a estimativa. Vale ter o link e o QR marcados também.
const CALCULADORA = {
  file: 'calculadora', titulo: 'Calculadora "Quanto vale meu imóvel?"',
  desc: 'Página pública de estimativa — o visitante informa o imóvel, vê a faixa de valor e deixa o contato. O lead cai no painel com a origem marcada.',
  url: `${BASE}/quanto-vale-meu-imovel`,
  msg: 'Descubra em 1 minuto quanto vale o seu imóvel — estimativa de mercado gratuita:',
};

// Resposta pronta para "qual o valor da assinatura?" — página só com os planos.
const PLANOS = {
  file: 'planos', titulo: 'Valores da assinatura (planos)',
  desc: 'Página só com os planos — mensal R$ 89,90, trimestral R$ 239,90 e anual R$ 849,90 — e o botão de cadastro com 3 dias grátis.',
  url: `${BASE}/planos`,
  msg: 'Os valores da assinatura do AvalieImob: mensal R$ 89,90, trimestral R$ 239,90 ou anual R$ 849,90 — e 3 dias grátis para testar:',
};

// Link direto para o cadastro: quem cria a conta ganha o teste automático de 3 dias.
const CADASTRO = {
  file: 'cadastro', titulo: 'Cadastro com 3 dias de teste grátis',
  desc: 'Link direto para a tela de cadastro. Ao criar a conta, o lead já entra com 3 dias de teste liberados automaticamente — sem cartão.',
  url: `${BASE}/cadastro`,
  // Folder da campanha — vai como imagem junto com a mensagem e é o preview do link.
  arte: '/campanha/cadastro-3-dias.jpg',
  msg: 'Crie sua conta no AvalieImob e teste o sistema completo por 3 dias grátis, sem cartão de crédito:',
  // Variações prontas — o card mostra a escolhida e é ela que vai no WhatsApp/cópia.
  msgs: [
    { rotulo: 'Convite completo', texto:
      'Olá! 👋 Tudo bem?\n\n' +
      'Liberei pra você *3 dias de teste GRÁTIS* no *AvalieImob* — a plataforma que eu uso no dia a dia para:\n\n' +
      '✅ *PTAM e laudos de avaliação* (NBR 14.653) prontos em minutos\n' +
      '✅ *Contratos de exclusividade e compra e venda*, com assinatura pelo WhatsApp\n' +
      '✅ *Georreferenciamento, memorial e shapefile* para cartório\n' +
      '✅ *Recibos e propostas* com a sua marca\n' +
      '✅ *Inteligência artificial* que redige os textos técnicos pra você\n\n' +
      'Sem cartão de crédito e sem compromisso. São só *3 dias* — aproveita pra testar com um caso real seu. 🚀\n\n' +
      '👉 Crie sua conta aqui:' },
    { rotulo: 'Gatilho: tempo', texto:
      'Quanto tempo você gasta montando um *laudo* ou um *contrato* do zero? ⏳\n\n' +
      'No *AvalieImob* o PTAM sai conforme a NBR 14.653, o contrato já vai para assinatura pelo WhatsApp e a IA escreve os textos técnicos — tudo em um só lugar.\n\n' +
      '🎁 Você tem *3 dias grátis* para testar o sistema completo, *sem cartão*.\n\n' +
      '👉 Comece agora:' },
    { rotulo: 'Curta', texto:
      '🎁 *3 dias grátis* no AvalieImob: PTAM, laudos, contratos com assinatura e georreferenciamento num só sistema. Sem cartão.\n\n' +
      '👉 Cadastre-se:' },
  ],
};

const PAGAMENTO = {
  file: 'pagamento', titulo: 'Dados para Pagamento (PIX / Banco)',
  desc: 'Página com a chave Pix e os dados bancários da Romatec. Funciona em qualquer aparelho — envie ao cliente ou mostre o QR para ele pagar na hora.',
  url: `${BASE}/pagamento/`,
  msg: 'Dados para pagamento (PIX e banco) — Romatec Consultoria Total:',
};

// ── Vídeos de apresentação para o cliente ───────────────────────────────────
// Vídeos verticais (720×1280) em frontend/public/video/apresentacoes/, com os
// nomes originais. O texto padrão é o da Mensagem_Para_Enviar_Ao_Cliente.txt.
const VIDEO_DIR = '/video/apresentacoes';
const ZAP_ROMATEC = 'https://wa.me/5599991811246';

const VIDEOS = [
  {
    id: 'geral', arquivo: 'AvalieImob_Apresentacao_Clientes_WhatsApp_720x1280', duracao: '45 s',
    titulo: 'Apresentação completa',
    desc: 'Todos os módulos: avaliação e laudos, georreferenciamento, contratos, shapefile urbano e ONR.',
    msg: 'Olá! Tudo bem? Segue um vídeo rápido para você conhecer a AvalieImob e seus módulos de avaliação e laudos, georreferenciamento, contratos, shapefile urbano e ONR.\n\nQual desses módulos faz mais sentido para o seu trabalho?\n\nSe quiser, posso orientar seu acesso para um teste e você conhece a plataforma no seu ritmo.',
  },
  {
    id: 'ptam-campanha', arquivo: 'AvalieImob_ptam_1080x1920', duracao: '25 s',
    titulo: 'Campanha — PTAM',
    desc: 'Para corretores e avaliadores: clientes, imóveis e amostras conectados, IA que apoia e laudo com a sua marca e assinatura ICP-Brasil.',
    msg: 'Olá! Tudo bem? Seu PTAM não precisa virar uma maratona. Segue um vídeo rápido da AvalieImob: você organiza clientes, imóveis e amostras de mercado em um só lugar, conta com cálculos automatizados e textos que você revisa, e entrega o laudo com a sua marca e assinatura com certificado digital.\n\nSe quiser, posso orientar seu acesso para um teste.',
  },
  {
    id: 'onr-campanha', arquivo: 'AvalieImob_onr_1080x1920', duracao: '29 s',
    titulo: 'Campanha — Shapefile urbano (SIG-RI)',
    desc: 'Provimento CNJ 195/2025: envie os documentos, o sistema extrai, você confere e recebe o pacote .shp/.shx/.dbf/.prj.',
    msg: 'Olá! Tudo bem? Os dados no SIG-RI agora são exigidos (Provimento CNJ 195/2025) na retificação administrativa, no parcelamento e na regularização fundiária. Segue um vídeo rápido de como a AvalieImob resolve isso: você envia a planta, o memorial, a ART e a matrícula, o sistema extrai as informações, você confere e recebe o pacote Shapefile pronto para o envio.\n\nSe quiser, posso orientar seu acesso para um teste.',
  },
  {
    id: 'geo-campanha', arquivo: 'AvalieImob_geo_1080x1920', duracao: '26 s',
    titulo: 'Campanha — Georreferenciamento',
    desc: 'Para agrimensores e topógrafos: do memorial SIGEF ao dossiê, com as peças, a assinatura ICP-Brasil e o sumário clicável.',
    msg: 'Olá! Tudo bem? Seu processo de georreferenciamento ainda está espalhado? Segue um vídeo rápido de como a AvalieImob organiza tudo: você sobe o memorial do SIGEF, confere vértices, área, perímetro e confrontantes, e entrega ao cliente o dossiê com as peças certas (Shapefile, KML, memorial, requerimento, DRL e laudo), assinado com ICP-Brasil.\n\nSe quiser, posso orientar seu acesso para um teste do módulo de georreferenciamento.',
  },
  {
    id: 'ptam', arquivo: 'AvalieImob_PTAM_Apresentacao_Clientes', duracao: '18 s',
    titulo: 'PTAM e avaliações',
    desc: 'Clientes, imóveis e amostras conectados; análise revisada e laudo em PDF com a sua marca.',
    msg: 'Olá! Tudo bem? Segue um vídeo rápido do módulo de avaliações da AvalieImob: você conecta clientes, imóveis e amostras e gera o laudo (PTAM) em PDF com a sua marca.\n\nSe quiser, posso orientar seu acesso para um teste.',
  },
  {
    id: 'georreferenciamento', arquivo: 'AvalieImob_Georreferenciamento_Apresentacao_Clientes', duracao: '14 s',
    titulo: 'Georreferenciamento',
    desc: 'Do memorial SIGEF ao dossiê para o cartório.',
    msg: 'Olá! Tudo bem? Segue um vídeo rápido do módulo de georreferenciamento da AvalieImob — do memorial ao dossiê para o cartório.\n\nSe quiser, posso orientar seu acesso para um teste.',
  },
  {
    id: 'contratos', arquivo: 'AvalieImob_Contratos_Apresentacao_Clientes', duracao: '14 s',
    titulo: 'Contratos',
    desc: 'Contratos e procuração com assinatura pelo WhatsApp e certificado ICP-Brasil.',
    msg: 'Olá! Tudo bem? Segue um vídeo rápido do módulo de contratos da AvalieImob, com assinatura pelo WhatsApp.\n\nSe quiser, posso orientar seu acesso para um teste.',
  },
  {
    id: 'onr', arquivo: 'AvalieImob_ONR_Apresentacao_Clientes', duracao: '16 s',
    titulo: 'Shapefile urbano / ONR',
    desc: 'Extração e conferência dos documentos e o pacote de arquivos para o SIG-RI.',
    msg: 'Olá! Tudo bem? Segue um vídeo rápido do módulo ONR da AvalieImob: você confere os dados extraídos dos documentos e gera o pacote para o SIG-RI.\n\nSe quiser, posso orientar seu acesso para um teste.',
  },
];

const textoVideo = (v) => {
  if (v.texto) return v.texto;  // campanha com texto/destino próprios
  // O vídeo do teste grátis leva direto ao cadastro (3 dias liberados na hora).
  const site = comUtm(`${BASE}${v.destino || '/'}`, { source: 'whatsapp', medium: 'video', campaign: `video-${v.id}` });
  return `${v.msg}\n\n${v.destino ? 'Crie sua conta' : 'Saiba mais'}: ${site}\nFale conosco: ${ZAP_ROMATEC}`;
};

// Vídeo da campanha dos 3 dias grátis — mostrado logo abaixo do card de cadastro.
const VIDEO_CADASTRO = {
  id: 'cadastro-3-dias', arquivo: 'AvalieImob_3_Dias_Gratis_Carrossel_Narrado_1080x1920', duracao: '26 s',
  destino: '/cadastro',
  titulo: 'Vídeo — 3 dias grátis',
  desc: 'Carrossel narrado da campanha de teste grátis, com o link direto para o cadastro.',
  msg: 'Olá! Tudo bem? 👋 Separei um vídeo rápido da AvalieImob — PTAM, laudos, contratos com assinatura e georreferenciamento num só sistema.\n\n🎁 Você tem *3 dias grátis* para testar tudo, sem cartão e sem cobrança automática.',
};

function VideoCard({ v, toast }) {
  const [enviando, setEnviando] = React.useState(false);
  const mp4 = `${VIDEO_DIR}/${v.arquivo}.mp4`;
  // Arquivo que vai para a conversa: a versão leve, quando existir.
  const envio = `${VIDEO_DIR}/${v.envio || v.arquivo}.mp4`;
  const videoRef = React.useRef(null);
  const texto = textoVideo(v);
  // Sem o arquivo, o WhatsApp recebe o link do vídeo junto com a mensagem.
  const waLink = `https://wa.me/?text=${encodeURIComponent(`${texto}\n\nVídeo: ${BASE}${envio}`)}`;

  // No celular, o compartilhamento nativo manda o PRÓPRIO vídeo para a conversa
  // escolhida (com a mensagem). Onde não houver suporte, abre o WhatsApp com o link.
  const enviarVideo = async () => {
    setEnviando(true);
    try {
      const blob = await (await fetch(envio)).blob();
      const file = new File([blob], `${v.envio || v.arquivo}.mp4`, { type: 'video/mp4' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        try { await navigator.clipboard.writeText(texto); } catch { /* opcional */ }
        await navigator.share({ files: [file], text: texto });
        return;
      }
      window.open(waLink, '_blank', 'noopener');
    } catch (e) {
      if (e?.name !== 'AbortError') window.open(waLink, '_blank', 'noopener');
    } finally { setEnviando(false); }
  };
  const copiarMsg = async () => {
    try { await navigator.clipboard.writeText(texto); toast({ title: 'Mensagem copiada ✓', description: 'Cole junto com o vídeo no WhatsApp.' }); }
    catch { toast({ title: 'Não foi possível copiar', variant: 'destructive' }); }
  };

  return (
    <div className={`rounded-2xl border border-gray-200 bg-white p-4 flex flex-col gap-4 ${v.horizontal ? '' : 'sm:flex-row'}`}>
      <div className={v.horizontal ? 'w-full' : 'shrink-0 mx-auto sm:mx-0 w-[180px]'}>
        <div className="rounded-xl overflow-hidden bg-black" style={{ aspectRatio: v.horizontal ? '16 / 9' : '9 / 16' }}>
          <video ref={videoRef} controls playsInline preload="none" poster={`${VIDEO_DIR}/${v.arquivo}.jpg`}
            aria-label={`Vídeo: ${v.titulo}`} className="block w-full h-full" style={{ objectFit: 'contain' }}>
            <source src={mp4} type="video/mp4" />
            {/* Legendas já gravadas na imagem: a faixa fica opcional (sem default) para não duplicar. */}
            {(v.legendas || v.legendasOpcionais) && (
              v.legendasOpcionais
                ? <track kind="captions" src={`${VIDEO_DIR}/${v.arquivo}.vtt`} srcLang="pt-BR" label="Português (Brasil)" />
                : <track kind="captions" src={`${VIDEO_DIR}/${v.arquivo}.vtt`} srcLang="pt-BR" label="Português" default />
            )}
          </video>
        </div>
        {v.capitulos && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {v.capitulos.map(([t, rotulo]) => (
              <button key={t} type="button"
                onClick={() => { const el = videoRef.current; if (!el) return; el.currentTime = t; el.play().catch(() => {}); }}
                className="text-[11px] px-2 py-1 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-50">
                {`${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`} · {rotulo}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold" style={{ color: GREEN }}>
          {v.titulo} <span className="text-xs font-normal text-gray-400">· {v.duracao}</span>
        </h3>
        <p className="text-sm text-gray-500 mt-1">{v.desc}</p>
        <pre className="mt-3 text-xs text-gray-600 whitespace-pre-wrap font-sans bg-gray-50 border border-gray-100 rounded-lg p-3 max-h-32 overflow-auto">{texto}</pre>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <button onClick={enviarVideo} disabled={enviando}
            className="inline-flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-semibold text-white disabled:opacity-60"
            style={{ background: GREEN }}>
            <Share2 className="w-3.5 h-3.5" /> {enviando ? 'Preparando…' : 'Enviar o vídeo'}
          </button>
          <a href={waLink} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-semibold border text-emerald-800 border-emerald-200 hover:bg-emerald-50">
            <Send className="w-3.5 h-3.5" /> Mandar link no WhatsApp
          </a>
          <a href={envio} download={`${v.envio || v.arquivo}.mp4`}
            className="inline-flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-medium border text-gray-700 border-gray-200 hover:bg-gray-50">
            <Download className="w-3.5 h-3.5" /> Baixar vídeo
          </a>
          <button onClick={copiarMsg}
            className="inline-flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-medium border text-gray-700 border-gray-200 hover:bg-gray-50">
            <Copy className="w-3.5 h-3.5" /> Copiar mensagem
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Campanha: PTAM em 12 passos (kit de 15/11/2026) ──
// Oferta aprovada: 3 dias grátis, contratação opcional depois, sem cobrança automática.
// Textos do dono, sem alteração. Os vídeos já trazem a legenda gravada na imagem.
const P12_CAD_INSTA = 'https://www.romatecavalieimob.com.br/cadastro?utm_source=instagram&utm_medium=paid_social&utm_campaign=ptam_12_passos_3_dias';
const P12_CAD_ZAP = 'https://www.romatecavalieimob.com.br/cadastro?utm_source=whatsapp&utm_medium=folder&utm_campaign=folder-cadastro';
const P12_LEGENDA = [
  'Documentos espalhados, retrabalho e dificuldade para explicar o valor ao cliente?',
  'Conheça o AvalieImob, da Romatec: um fluxo de PTAM em 12 passos, do cadastro à apresentação do parecer.',
  'Organize os dados do imóvel, mapas, documentos e pesquisa de mercado. Em cada amostragem, você pode anexar imagens e planta baixa do comparável, além de registrar área, valor, fonte e características — mais contexto para uma análise bem documentada.',
  'Confira os tratamentos e a memória de cálculo e prepare a entrega com resultado, conclusão, capa, sumário e anexos. Você revisa e assina; a plataforma apoia o seu trabalho.',
  'Para corretores, avaliadores e peritos que querem uma rotina mais organizada e uma apresentação mais clara para o cliente.',
  'Teste grátis por 3 dias. Depois, você decide se quer contratar. Sem cobrança automática.',
  `Faça seu cadastro:\n${P12_CAD_INSTA}`,
  '#AvalieImob #Romatec #PTAM #AvaliacaoImobiliaria #CorretorDeImoveis #PeritoImobiliario',
].join('\n\n');
const P12_CURTA = [
  'Do cadastro à entrega: conheça o PTAM em 12 passos no AvalieImob.',
  'Organize comparáveis com campos para imagens e planta baixa, confira os tratamentos e a memória de cálculo e prepare um documento com capa, sumário e anexos. Você revisa e assina.',
  '3 dias grátis para conhecer. Contratação opcional depois do teste, sem cobrança automática.',
  `Cadastre-se:\n${P12_CAD_INSTA}`,
].join('\n\n');
const P12_LEAD = [
  'Olá! Preparei esta apresentação rápida do AvalieImob para você conhecer o fluxo de PTAM, a pesquisa de amostras, os tratamentos e a organização do documento final.',
  'Você pode testar a plataforma grátis por 3 dias. Depois, decide se quer contratar, sem cobrança automática.',
  `Cadastro:\n${P12_CAD_ZAP}`,
  'Se quiser, também posso te enviar a demonstração completa das 12 etapas.',
].join('\n\n');
const P12_DEMO_MSG = [
  'Olá! Como combinamos, segue a demonstração completa do PTAM em 12 passos no AvalieImob (cerca de 6 minutos): do cadastro do solicitante ao documento final com capa, sumário e anexos, assinatura e entrega.',
  'Você pode testar a plataforma grátis por 3 dias. Depois, decide se quer contratar, sem cobrança automática.',
  `Cadastro:\n${P12_CAD_ZAP}`,
].join('\n\n');
const P12_TEXTOS = [
  { id: 'principal', rotulo: 'Legenda principal (Instagram)', texto: P12_LEGENDA },
  { id: 'curta', rotulo: 'Versão curta (Reels / anúncio)', texto: P12_CURTA },
  { id: 'lead', rotulo: 'Mensagem ao lead (WhatsApp)', texto: P12_LEAD },
];
const P12_VIDEO = {
  id: 'ptam-12-passos', arquivo: 'AvalieImob_PTAM_Divulgacao_1080x1920', envio: 'AvalieImob_PTAM_Divulgacao_WhatsApp_720x1280',
  duracao: '1 min', legendasOpcionais: true,
  titulo: 'Anúncio — PTAM em 12 passos',
  desc: 'Vertical, narrado, com legenda na imagem. "Enviar o vídeo" e "Baixar" usam a versão leve (2,4 MB). No anúncio, aponte o botão para o link de cadastro da legenda.',
  texto: P12_LEAD,
};
const P12_DEMO = {
  id: 'ptam-12-passos-demo', arquivo: 'AvalieImob_PTAM_Demonstracao_Web_1280x720',
  duracao: '6 min', legendasOpcionais: true, horizontal: true,
  titulo: 'Demonstração completa — PTAM em 12 passos',
  desc: 'Para o lead que quer detalhes. Clique num capítulo para ir direto à etapa.',
  texto: P12_DEMO_MSG,
  capitulos: [
    [0, 'Abertura'], [28, '1. Solicitante'], [47, '2. Objetivo'], [65, '3. Imóvel'], [91, '4. Região'],
    [107, '5. Caracterização'], [131, '6. Amostras'], [159, '7. Metodologia'], [177, '8. Cálculos'],
    [201, '9. Ponderação'], [219, '10. Depreciação'], [239, '11. Resultado'], [268, '12. Conclusão'],
    [288, 'PTAM exportado'], [317, 'Assinatura e entrega'], [339, '3 dias grátis'],
  ],
};

// Mesma demonstração, em pé (9:16) — feita para o WhatsApp e o Status.
const P12_DEMO_VERT = {
  id: 'ptam-12-passos-demo-vertical', arquivo: 'AvalieImob_PTAM_Demonstracao_WhatsApp_Vertical_720x1280',
  duracao: '6 min', legendasOpcionais: true,
  titulo: 'Demonstração completa — vertical (WhatsApp)',
  desc: 'A demonstração inteira em pé, para enviar pelo WhatsApp (18 MB). É o mesmo vídeo que aparece no chat de ajuda do sistema.',
  texto: P12_DEMO_MSG,
};
// Links prontos para colar em bio, grupos e anúncios. Cada um marca a origem (UTM).
const P12_LINKS = [
  { rotulo: 'Página com a demonstração (site)', desc: 'Abre o site já na seção do vídeo, com capítulos e botão de cadastro.',
    url: `${BASE}/?utm_source=whatsapp&utm_medium=link&utm_campaign=ptam_12_passos_demo#ptam-12-passos` },
  { rotulo: 'Página com a demonstração — Instagram (bio/stories)', desc: 'Mesmo destino, marcado como Instagram.',
    url: `${BASE}/?utm_source=instagram&utm_medium=social&utm_campaign=ptam_12_passos_demo#ptam-12-passos` },
  { rotulo: 'Vídeo vertical (arquivo)', desc: 'Link direto do vídeo em pé, abre e toca no celular.',
    url: `${BASE}${VIDEO_DIR}/AvalieImob_PTAM_Demonstracao_WhatsApp_Vertical_720x1280.mp4` },
  { rotulo: 'Vídeo horizontal (arquivo)', desc: 'Link direto da versão 16:9, para computador.',
    url: `${BASE}${VIDEO_DIR}/AvalieImob_PTAM_Demonstracao_Web_1280x720.mp4` },
  { rotulo: 'Cadastro — 3 dias grátis (WhatsApp)', desc: 'Para mandar junto do vídeo.', url: P12_CAD_ZAP },
  { rotulo: 'Cadastro — 3 dias grátis (Instagram)', desc: 'Para bio, sticker de link ou botão do anúncio.', url: P12_CAD_INSTA },
];

function LinksPtam12({ toast }) {
  const copiar = async (l) => {
    try { await navigator.clipboard.writeText(l.url); toast({ title: 'Link copiado ✓', description: l.rotulo }); }
    catch { toast({ title: 'Não foi possível copiar', variant: 'destructive' }); }
  };
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4">
      <h3 className="font-semibold" style={{ color: GREEN }}>Links para divulgação</h3>
      <ul className="mt-3 divide-y divide-gray-100">
        {P12_LINKS.map((l) => (
          <li key={l.rotulo} className="py-2.5 flex flex-col sm:flex-row sm:items-center gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800">{l.rotulo}</p>
              <p className="text-[11px] text-gray-500">{l.desc}</p>
              <p className="text-[11px] text-gray-400 break-all">{l.url}</p>
            </div>
            <div className="flex gap-2 shrink-0">
              <button type="button" onClick={() => copiar(l)}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-white" style={{ background: GREEN }}>
                <Copy className="w-3.5 h-3.5" /> Copiar
              </button>
              <a href={`https://wa.me/?text=${encodeURIComponent(l.url)}`} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border text-emerald-800 border-emerald-200 hover:bg-emerald-50">
                <Send className="w-3.5 h-3.5" /> WhatsApp
              </a>
              <a href={l.url} target="_blank" rel="noopener noreferrer" aria-label={`Abrir: ${l.rotulo}`}
                className="inline-flex items-center px-2.5 py-2 rounded-lg text-xs border text-gray-600 border-gray-200 hover:bg-gray-50">
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CampanhaPtam12({ toast }) {
  const [sel, setSel] = React.useState('principal');
  const atual = P12_TEXTOS.find((t) => t.id === sel) || P12_TEXTOS[0];
  const copiar = async () => {
    try { await navigator.clipboard.writeText(atual.texto); toast({ title: 'Texto copiado ✓', description: atual.rotulo }); }
    catch { toast({ title: 'Não foi possível copiar', variant: 'destructive' }); }
  };
  return (
    <div className="space-y-4 mb-9">
      <div className="rounded-2xl border border-gray-200 bg-white p-4">
        <h3 className="font-semibold" style={{ color: GREEN }}>Legendas e mensagens</h3>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {P12_TEXTOS.map((t) => (
            <button key={t.id} type="button" onClick={() => setSel(t.id)} aria-pressed={sel === t.id}
              className={`text-xs px-3 py-1.5 rounded-full border ${sel === t.id ? 'text-white border-transparent' : 'text-gray-600 border-gray-200 hover:bg-gray-50'}`}
              style={sel === t.id ? { background: GREEN } : undefined}>
              {t.rotulo}
            </button>
          ))}
        </div>
        <pre className="mt-3 text-xs text-gray-600 whitespace-pre-wrap font-sans bg-gray-50 border border-gray-100 rounded-lg p-3 max-h-48 overflow-auto">{atual.texto}</pre>
        <p className="text-[11px] text-gray-400 mt-1">
          No Instagram o link da legenda não é clicável: use o link da bio, um sticker de link ou o botão do anúncio.
        </p>
        <button onClick={copiar}
          className="mt-3 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-xs font-semibold text-white"
          style={{ background: GREEN }}>
          <Copy className="w-3.5 h-3.5" /> Copiar texto
        </button>
      </div>
      <VideoCard v={P12_VIDEO} toast={toast} />
      <VideoCard v={P12_DEMO} toast={toast} />
      <VideoCard v={P12_DEMO_VERT} toast={toast} />
      <LinksPtam12 toast={toast} />
    </div>
  );
}

// ── Campanha: prévia da Análise Estatística Avançada (kit de 15/11/2026) ──
// É PRÉVIA: a chamada é "conhecer a proposta" (WhatsApp), nunca "usar agora".
const AA_DIR = '/campanha/analise-avancada';
const AA_ZAP = 'https://wa.me/5599991811246?text=' + encodeURIComponent(
  'Olá! Vi a prévia da Análise Estatística Avançada do AvalieImob. Quero conhecer a proposta e acompanhar sua liberação.');
const AA_SITE = comUtm(`${BASE}/`, { source: 'instagram', medium: 'social', campaign: 'analise_avancada_previa' });
const AA_LEGENDA = [
  'SUA AMOSTRA MERECE MAIS ANÁLISE.',
  'O AvalieImob prepara uma opção adicional de Análise Estatística Avançada para apoiar o trabalho com amostras de mercado.',
  'A proposta reúne escolha de variáveis, regressão linear múltipla, diagnósticos do modelo, estimativas com intervalos e memória de cálculo, com revisão do avaliador e sem substituir os tratamentos atuais.',
  'PRÉVIA: a opção está em preparação. A disponibilização depende da implementação, dos testes e da liberação técnica. As telas desta publicação são ilustrativas.',
  'Quer conhecer a proposta e acompanhar a liberação? Fale com a Romatec.',
  `WhatsApp: (99) 99181-1246\n${AA_ZAP}`,
  `Conheça a plataforma:\n${AA_SITE}`,
  '#AvalieImob #Romatec #AvaliacaoImobiliaria #InferenciaEstatistica #EngenhariaDeAvaliacoes #PericiaImobiliaria',
].join('\n\n');
const AA_PAGINAS = ['01', '02', '03', '04', '05'];
const AA_VIDEO = {
  id: 'analise-avancada-previa', arquivo: 'AvalieImob_Previa_Analise_Avancada_1080x1920', duracao: '32 s',
  legendas: true,
  titulo: 'Vídeo — prévia da Análise Estatística Avançada',
  desc: 'Narrado, com legendas. Telas ilustrativas: anuncia a proposta em preparação, não uma função liberada.',
  texto: AA_LEGENDA,
};

function CampanhaAnaliseAvancada({ toast }) {
  const [enviando, setEnviando] = React.useState(false);
  const arquivos = async (nomes) => Promise.all(nomes.map(async (n) => {
    const blob = await (await fetch(`${AA_DIR}/${n}.jpg`)).blob();
    return new File([blob], `AvalieImob_Analise_Avancada_${n}.jpg`, { type: 'image/jpeg' });
  }));
  const compartilhar = async (nomes) => {
    setEnviando(true);
    try {
      const files = await arquivos(nomes);
      try { await navigator.clipboard.writeText(AA_LEGENDA); } catch { /* opcional */ }
      if (navigator.canShare && navigator.canShare({ files })) {
        await navigator.share({ files, text: AA_LEGENDA });
      } else {
        toast({ title: 'Legenda copiada ✓', description: 'Neste aparelho, baixe as imagens e publique pelo app.' });
      }
    } catch (e) {
      if (e?.name !== 'AbortError') toast({ title: 'Não foi possível compartilhar', variant: 'destructive' });
    } finally { setEnviando(false); }
  };
  const copiar = async () => {
    try { await navigator.clipboard.writeText(AA_LEGENDA); toast({ title: 'Legenda copiada ✓' }); }
    catch { toast({ title: 'Não foi possível copiar', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-4 mb-9">
      <div className="rounded-2xl border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold" style={{ color: GREEN }}>Carrossel + folder</h3>
          <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full"
            style={{ background: '#FBF3DC', color: '#8A6D1F' }}>Prévia · em preparação</span>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          5 páginas para o Instagram (1080×1350, nesta ordem) e o folder avulso para grupos e status.
        </p>
        <div className="mt-3 flex gap-2 overflow-x-auto pb-2">
          {[...AA_PAGINAS, 'Folder_Analise_Estatistica_Avancada'].map((n) => (
            <a key={n} href={`${AA_DIR}/${n}.jpg`} download={`AvalieImob_Analise_Avancada_${n}.jpg`}
              className="shrink-0 w-[110px] group" title="Baixar imagem">
              <img src={`${AA_DIR}/${n}.webp`} alt={n === 'Folder_Analise_Estatistica_Avancada' ? 'Folder' : `Página ${n}`}
                loading="lazy" width={110} height={138}
                className="w-[110px] h-[138px] object-cover rounded-lg border border-gray-200 group-hover:opacity-80" />
              <span className="block text-[10px] text-center text-gray-500 mt-1">
                {n.startsWith('Folder') ? 'Folder' : `Página ${n}`} · baixar
              </span>
            </a>
          ))}
        </div>
        <pre className="mt-2 text-xs text-gray-600 whitespace-pre-wrap font-sans bg-gray-50 border border-gray-100 rounded-lg p-3 max-h-40 overflow-auto">{AA_LEGENDA}</pre>
        <p className="text-[11px] text-gray-400 mt-1">
          No Instagram o link da legenda não é clicável: use o link da bio, um sticker de link ou o botão de WhatsApp do anúncio.
        </p>
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
          <button onClick={() => compartilhar(AA_PAGINAS)} disabled={enviando}
            className="inline-flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-semibold text-white disabled:opacity-60"
            style={{ background: GREEN }}>
            <Share2 className="w-3.5 h-3.5" /> {enviando ? 'Preparando…' : 'Enviar carrossel'}
          </button>
          <button onClick={() => compartilhar(['Folder_Analise_Estatistica_Avancada'])} disabled={enviando}
            className="inline-flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-semibold border text-emerald-800 border-emerald-200 hover:bg-emerald-50 disabled:opacity-60">
            <Send className="w-3.5 h-3.5" /> Enviar folder
          </button>
          <button onClick={copiar}
            className="inline-flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-medium border text-gray-700 border-gray-200 hover:bg-gray-50">
            <Copy className="w-3.5 h-3.5" /> Copiar legenda
          </button>
          <a href={AA_ZAP} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-medium border text-gray-700 border-gray-200 hover:bg-gray-50">
            <Send className="w-3.5 h-3.5" /> Testar o WhatsApp
          </a>
        </div>
      </div>
      <VideoCard v={AA_VIDEO} toast={toast} />
    </div>
  );
}

// Avisa Bing e Yandex (IndexNow) de que o site tem página nova ou atualizada.
// O Google não usa IndexNow — lá o caminho é o Search Console, indicado no card.
const BuscadoresCard = ({ toast }) => {
  const [enviando, setEnviando] = React.useState('');

  const pingar = async (escopo) => {
    setEnviando(escopo);
    try {
      const r = await adminAPI.indexnowPing(escopo === 'blog' ? { escopo: 'blog' } : {});
      toast({
        title: r.ok ? `${r.submitted} endereços enviados ao IndexNow` : 'O envio não foi aceito',
        description: r.mensagem || r.error,
        variant: r.ok ? undefined : 'destructive',
      });
    } catch (e) {
      toast({ title: 'Falha ao avisar os buscadores',
              description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setEnviando(''); }
  };

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <Search className="w-4 h-4" style={{ color: GOLD }} />
        <span className="text-xs font-bold uppercase tracking-wide text-gray-500">
          Avisar os buscadores
        </span>
      </div>
      <p className="text-sm text-gray-600 mb-3">
        Publicou artigo novo ou mexeu numa página? Avise o <strong>Bing</strong> e o
        <strong> Yandex</strong> na hora, em vez de esperar eles passarem sozinhos.
      </p>
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => pingar('blog')} disabled={!!enviando}
                className="px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-60"
                style={{ background: GREEN }}>
          {enviando === 'blog' ? 'Enviando…' : 'Avisar sobre os artigos'}
        </button>
        <button type="button" onClick={() => pingar('tudo')} disabled={!!enviando}
                className="px-4 py-2 rounded-lg text-sm font-semibold border border-gray-300 disabled:opacity-60">
          {enviando === 'tudo' ? 'Enviando…' : 'Avisar sobre o site inteiro'}
        </button>
        <a href="https://search.google.com/search-console" target="_blank" rel="noreferrer"
           className="px-4 py-2 rounded-lg text-sm font-semibold border border-gray-300 inline-flex items-center gap-1.5">
          Google Search Console <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
      <p className="text-[11px] text-gray-400 mt-2">
        O Google não usa IndexNow: lá, abra o Search Console, cole o endereço em
        “Inspeção de URL” e clique em <em>Solicitar indexação</em>.
      </p>
    </div>
  );
};

function FolderCard({ f, toast }) {
  const ref = useRef(null);
  const [msgIdx, setMsgIdx] = React.useState(0);
  const msg = f.msgs?.[msgIdx]?.texto || f.msg;
  const [baixandoPdf, setBaixandoPdf] = React.useState(false);

  // Cada canal leva a SUA marcação — é o que separa "veio do folder de topografia
  // pelo WhatsApp" de "veio do QR impresso" no painel de Leads.
  const urlWhats = linkDe(f, 'whatsapp');
  const urlLink = linkDe(f, 'link');
  const urlQr = linkDe(f, 'qr');

  const copiar = async () => {
    try { await navigator.clipboard.writeText(urlLink); toast({ title: 'Link copiado ✓', description: urlLink }); }
    catch { toast({ title: 'Não foi possível copiar', variant: 'destructive' }); }
  };
  const copiarMsg = async () => {
    try { await navigator.clipboard.writeText(`${msg} ${urlWhats}`); toast({ title: 'Mensagem copiada ✓', description: 'Cole no grupo do WhatsApp.' }); }
    catch { toast({ title: 'Não foi possível copiar', variant: 'destructive' }); }
  };
  const baixarQr = () => {
    const canvas = ref.current?.querySelector('canvas');
    if (!canvas) return;
    const a = document.createElement('a');
    a.href = canvas.toDataURL('image/png');
    a.download = `qr-avalieimob-${f.file}.png`;
    document.body.appendChild(a); a.click(); a.remove();
  };
  // PNG serve para WhatsApp; para impressão grande a gráfica precisa do vetor.
  const baixarQrPdf = async () => {
    setBaixandoPdf(true);
    try {
      const blob = await adminAPI.qrPdf(urlQr, f.titulo);
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href; a.download = `qr-avalieimob-${f.file}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(href);
    } catch (e) {
      toast({ title: 'Não foi possível gerar o PDF',
              description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setBaixandoPdf(false); }
  };
  const wa = `https://wa.me/?text=${encodeURIComponent(`${msg} ${urlWhats}`)}`;

  // No celular, o compartilhamento nativo manda a ARTE + a mensagem com o link para
  // a conversa escolhida. Sem suporte, abre o WhatsApp só com o texto (o link já
  // mostra o folder no preview).
  const [enviandoArte, setEnviandoArte] = React.useState(false);
  const enviarArte = async () => {
    const texto = `${msg} ${urlWhats}`;
    setEnviandoArte(true);
    try {
      const blob = await (await fetch(f.arte)).blob();
      const file = new File([blob], `avalieimob-${f.file}.jpg`, { type: 'image/jpeg' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        try { await navigator.clipboard.writeText(texto); } catch { /* opcional */ }
        await navigator.share({ files: [file], text: texto });
        return;
      }
      window.open(wa, '_blank', 'noopener');
    } catch (e) {
      if (e?.name !== 'AbortError') window.open(wa, '_blank', 'noopener');
    } finally { setEnviandoArte(false); }
  };


  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 flex flex-col sm:flex-row gap-5">
      {/* QR */}
      <div className="flex flex-col items-center gap-2 shrink-0">
        <div ref={ref} className="p-2.5 rounded-xl bg-white border" style={{ borderColor: '#eadfbf' }}>
          {/* Badge de 20 px (15% do lado), não 28: com a marcação a URL ficou mais
              longa, o código mais denso, e um badge maior cobria um padrão de
              alinhamento — o QR de topografia deixava de ser lido. */}
          <QRCodeCanvas
            value={urlQr} size={132} level="H" bgColor="#ffffff" fgColor={GREEN}
            imageSettings={{ src: '/icon-192.png', height: 20, width: 20, excavate: true }}
          />
        </div>
        <button onClick={baixarQr}
          className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border text-emerald-800 border-emerald-200 hover:bg-emerald-50">
          <Download className="w-3.5 h-3.5" /> Baixar QR
        </button>
        <button onClick={baixarQrPdf} disabled={baixandoPdf}
          title="PDF vetorial — a gráfica amplia sem serrilhar"
          className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border text-gray-600 border-gray-200 hover:bg-gray-50 disabled:opacity-50">
          <Download className="w-3.5 h-3.5" /> {baixandoPdf ? 'Gerando…' : 'PDF p/ gráfica'}
        </button>
      </div>

      {/* Info + ações */}
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-gray-800" style={{ color: GREEN }}>{f.titulo}</h3>
        <p className="text-sm text-gray-500 mt-1">{f.desc}</p>
        <div className="mt-2 text-xs font-mono text-gray-400 break-all">{urlLink}</div>
        <div className="mt-1 text-[11px] text-gray-400">
          Cada botão marca a origem: <strong>WhatsApp</strong>, <strong>link copiado</strong> ou
          <strong> QR Code</strong> — o painel de Leads mostra de qual peça veio o cadastro.
        </div>

        {f.arte && (
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <a href={f.arte} target="_blank" rel="noopener noreferrer" title="Abrir o folder em tamanho real"
              className="block w-[120px] shrink-0 rounded-lg overflow-hidden border" style={{ borderColor: '#eadfbf' }}>
              <img src={f.arte} alt={`Folder — ${f.titulo}`} loading="lazy" className="block w-full h-auto" />
            </a>
            <div className="flex flex-col gap-2 min-w-0">
              <button onClick={enviarArte} disabled={enviandoArte}
                className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold disabled:opacity-60"
                style={{ background: '#C9A84C', color: GREEN }}>
                <Send className="w-3.5 h-3.5" /> {enviandoArte ? 'Preparando…' : 'Enviar folder + mensagem'}
              </button>
              <a href={f.arte} download={`avalieimob-${f.file}.jpg`}
                className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border text-gray-700 border-gray-200 hover:bg-gray-50">
                <Download className="w-3.5 h-3.5" /> Baixar folder
              </a>
              <span className="text-[11px] text-gray-400">No celular, o folder vai como imagem com a mensagem.</span>
            </div>
          </div>
        )}

        {f.msgs && (
          <div className="mt-3">
            <div className="text-xs font-semibold text-gray-600 mb-1.5">Mensagem para enviar</div>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {f.msgs.map((m, i) => (
                <button key={m.rotulo} type="button" onClick={() => setMsgIdx(i)} aria-pressed={i === msgIdx}
                  className={`text-xs px-2.5 py-1 rounded-full border ${i === msgIdx
                    ? 'text-white border-transparent' : 'text-gray-600 border-gray-200 hover:bg-gray-50'}`}
                  style={i === msgIdx ? { background: GREEN } : {}}>
                  {m.rotulo}
                </button>
              ))}
            </div>
            <div className="text-xs text-gray-700 whitespace-pre-wrap break-words rounded-lg p-3 border"
              style={{ background: '#F7F4EA', borderColor: '#eadfbf' }}>
              {msg} <span className="text-emerald-700 break-all">{urlWhats}</span>
            </div>
          </div>
        )}

        <div className="mt-4 grid grid-cols-2 gap-2">
          <a href={wa} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold text-white"
            style={{ background: GREEN }}>
            <Send className="w-3.5 h-3.5" /> Enviar no WhatsApp
          </a>
          <button onClick={copiarMsg}
            className="inline-flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold border text-gray-700 border-gray-200 hover:bg-gray-50">
            <Copy className="w-3.5 h-3.5" /> Copiar mensagem
          </button>
          <button onClick={copiar}
            className="inline-flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium border text-gray-700 border-gray-200 hover:bg-gray-50">
            <Copy className="w-3.5 h-3.5" /> Copiar só o link
          </button>
          <a href={f.url} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium border text-gray-700 border-gray-200 hover:bg-gray-50">
            <ExternalLink className="w-3.5 h-3.5" /> {['planos', 'cadastro'].includes(f.file) ? 'Abrir página' : 'Abrir folder'}
          </a>
        </div>
      </div>
    </div>
  );
}

export default function DivulgacaoPage() {
  const { toast } = useToast();
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 pr-9 sm:pr-12">
      <header className="flex items-start gap-3 mb-6">
        <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: GREEN }}>
          <Megaphone className="w-6 h-6" style={{ color: GOLD }} />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: GREEN }}>Divulgação</h1>
          <p className="text-sm text-gray-500">
            Vídeos e folders prontos para enviar ao cliente — mande o vídeo, copie o link ou baixe o QR Code para imprimir.
          </p>
        </div>
      </header>

      <div className="rounded-xl bg-amber-50 border border-amber-100 p-4 mb-6 text-sm text-amber-800">
        💡 <strong>Dica:</strong> no celular, o botão <em>“Enviar no WhatsApp”</em> abre a lista de conversas para você
        escolher o grupo. O <em>QR Code</em> é ótimo para cartão de visita, adesivo ou status.
      </div>

      <h2 className="text-sm font-bold uppercase tracking-wide mb-3" style={{ color: GREEN }}>
        Valores da assinatura
      </h2>
      <div className="mb-8"><FolderCard f={PLANOS} toast={toast} /></div>
      <div className="mb-8 space-y-4">
        <FolderCard f={CADASTRO} toast={toast} />
        <VideoCard v={VIDEO_CADASTRO} toast={toast} />
      </div>

      <BuscadoresCard toast={toast} />

      <h2 className="text-sm font-bold uppercase tracking-wide mt-2 mb-1" style={{ color: GREEN }}>
        Campanha — PTAM em 12 passos (3 dias grátis)
      </h2>
      <p className="text-xs text-gray-500 mb-3">
        Para captar: o anúncio vertical com o link de cadastro. Para o lead que quer detalhes: a demonstração completa.
      </p>
      <CampanhaPtam12 toast={toast} />

      <h2 className="text-sm font-bold uppercase tracking-wide mt-2 mb-1" style={{ color: GREEN }}>
        Campanha — Análise Estatística Avançada (prévia)
      </h2>
      <p className="text-xs text-gray-500 mb-3">
        Material da proposta em preparação. A chamada é <strong>conhecer a proposta</strong> pelo WhatsApp —
        não anuncia a função como liberada.
      </p>
      <CampanhaAnaliseAvancada toast={toast} />

      <h2 className="text-sm font-bold uppercase tracking-wide mt-2 mb-1" style={{ color: GREEN }}>
        Vídeos de apresentação para clientes
      </h2>
      <p className="text-xs text-gray-500 mb-3">
        No celular, <strong>Enviar o vídeo</strong> abre o compartilhamento: escolha o WhatsApp e a conversa — o vídeo vai
        com a mensagem (ela também fica copiada, caso o app não a cole sozinho). No computador, baixe o vídeo e anexe na conversa.
      </p>
      <div className="space-y-4 mb-9">
        {VIDEOS.map((v) => <VideoCard key={v.id} v={v} toast={toast} />)}
      </div>

      <h2 className="text-sm font-bold uppercase tracking-wide mb-3" style={{ color: GREEN }}>
        Folders
      </h2>

      <div className="space-y-4">
        {FOLDERS.map((f) => <FolderCard key={f.file} f={f} toast={toast} />)}
      </div>

      <h2 className="text-sm font-bold uppercase tracking-wide mt-9 mb-3" style={{ color: GREEN }}>
        Captação de leads
      </h2>
      <FolderCard f={CALCULADORA} toast={toast} />

      <h2 className="text-sm font-bold uppercase tracking-wide mt-9 mb-3" style={{ color: GREEN }}>
        Cobrança / Pagamento
      </h2>
      <FolderCard f={PAGAMENTO} toast={toast} />
    </div>
  );
}
