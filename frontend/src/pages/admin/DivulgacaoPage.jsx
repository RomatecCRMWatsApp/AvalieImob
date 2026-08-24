// @page admin/Divulgação — links dos folders de divulgação + WhatsApp + QR Code.
import React, { useRef } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import { Megaphone, Copy, ExternalLink, Download, Send, Search } from 'lucide-react';
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

const PAGAMENTO = {
  file: 'pagamento', titulo: 'Dados para Pagamento (PIX / Banco)',
  desc: 'Página com a chave Pix e os dados bancários da Romatec. Funciona em qualquer aparelho — envie ao cliente ou mostre o QR para ele pagar na hora.',
  url: `${BASE}/pagamento/`,
  msg: 'Dados para pagamento (PIX e banco) — Romatec Consultoria Total:',
};

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
            <ExternalLink className="w-3.5 h-3.5" /> Abrir folder
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
            Folders prontos para os grupos de WhatsApp — copie o link, envie direto ou baixe o QR Code para imprimir.
          </p>
        </div>
      </header>

      <div className="rounded-xl bg-amber-50 border border-amber-100 p-4 mb-6 text-sm text-amber-800">
        💡 <strong>Dica:</strong> no celular, o botão <em>“Enviar no WhatsApp”</em> abre a lista de conversas para você
        escolher o grupo. O <em>QR Code</em> é ótimo para cartão de visita, adesivo ou status.
      </div>

      <BuscadoresCard toast={toast} />

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
