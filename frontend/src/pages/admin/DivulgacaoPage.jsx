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
  msg: 'Crie sua conta no AvalieImob e teste o sistema completo por 3 dias grátis, sem cartão de crédito:',
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
  const site = comUtm(`${BASE}/`, { source: 'whatsapp', medium: 'video', campaign: `video-${v.id}` });
  return `${v.msg}\n\nSaiba mais: ${site}\nFale conosco: ${ZAP_ROMATEC}`;
};

function VideoCard({ v, toast }) {
  const [enviando, setEnviando] = React.useState(false);
  const mp4 = `${VIDEO_DIR}/${v.arquivo}.mp4`;
  const texto = textoVideo(v);
  // Sem o arquivo, o WhatsApp recebe o link do vídeo junto com a mensagem.
  const waLink = `https://wa.me/?text=${encodeURIComponent(`${texto}\n\nVídeo: ${BASE}${mp4}`)}`;

  // No celular, o compartilhamento nativo manda o PRÓPRIO vídeo para a conversa
  // escolhida (com a mensagem). Onde não houver suporte, abre o WhatsApp com o link.
  const enviarVideo = async () => {
    setEnviando(true);
    try {
      const blob = await (await fetch(mp4)).blob();
      const file = new File([blob], `${v.arquivo}.mp4`, { type: 'video/mp4' });
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
    <div className="rounded-2xl border border-gray-200 bg-white p-4 flex flex-col sm:flex-row gap-4">
      <div className="shrink-0 mx-auto sm:mx-0 w-[180px] rounded-xl overflow-hidden bg-black" style={{ aspectRatio: '9 / 16' }}>
        <video controls playsInline preload="none" poster={`${VIDEO_DIR}/${v.arquivo}.jpg`}
          aria-label={`Vídeo: ${v.titulo}`} className="block w-full h-full" style={{ objectFit: 'contain' }}>
          <source src={mp4} type="video/mp4" />
        </video>
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
          <a href={mp4} download={`${v.arquivo}.mp4`}
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
    try { await navigator.clipboard.writeText(`${f.msg} ${urlWhats}`); toast({ title: 'Mensagem copiada ✓', description: 'Cole no grupo do WhatsApp.' }); }
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
  const wa = `https://wa.me/?text=${encodeURIComponent(`${f.msg} ${urlWhats}`)}`;


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
            <ExternalLink className="w-3.5 h-3.5" /> {f.file === 'planos' ? 'Abrir página' : 'Abrir folder'}
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
      <div className="mb-8"><FolderCard f={CADASTRO} toast={toast} /></div>

      <BuscadoresCard toast={toast} />

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
