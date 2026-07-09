// @page admin/Divulgação — links dos folders de divulgação + WhatsApp + QR Code.
import React, { useRef } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import { Megaphone, Copy, ExternalLink, Download, Send } from 'lucide-react';
import { useToast } from '../../hooks/use-toast';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const BASE = 'https://www.romatecavalieimob.com.br';

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

const PAGAMENTO = {
  file: 'pagamento', titulo: 'Dados para Pagamento (PIX / Banco)',
  desc: 'Página com a chave Pix e os dados bancários da Romatec. Funciona em qualquer aparelho — envie ao cliente ou mostre o QR para ele pagar na hora.',
  url: `${BASE}/pagamento/`,
  msg: 'Dados para pagamento (PIX e banco) — Romatec Consultoria Total:',
};

function FolderCard({ f, toast }) {
  const ref = useRef(null);

  const copiar = async () => {
    try { await navigator.clipboard.writeText(f.url); toast({ title: 'Link copiado ✓', description: f.url }); }
    catch { toast({ title: 'Não foi possível copiar', variant: 'destructive' }); }
  };
  const copiarMsg = async () => {
    try { await navigator.clipboard.writeText(`${f.msg} ${f.url}`); toast({ title: 'Mensagem copiada ✓', description: 'Cole no grupo do WhatsApp.' }); }
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
  const wa = `https://wa.me/?text=${encodeURIComponent(`${f.msg} ${f.url}`)}`;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 flex flex-col sm:flex-row gap-5">
      {/* QR */}
      <div className="flex flex-col items-center gap-2 shrink-0">
        <div ref={ref} className="p-2.5 rounded-xl bg-white border" style={{ borderColor: '#eadfbf' }}>
          <QRCodeCanvas
            value={f.url} size={132} level="H" bgColor="#ffffff" fgColor={GREEN}
            imageSettings={{ src: '/icon-192.png', height: 28, width: 28, excavate: true }}
          />
        </div>
        <button onClick={baixarQr}
          className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border text-emerald-800 border-emerald-200 hover:bg-emerald-50">
          <Download className="w-3.5 h-3.5" /> Baixar QR
        </button>
      </div>

      {/* Info + ações */}
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-gray-800" style={{ color: GREEN }}>{f.titulo}</h3>
        <p className="text-sm text-gray-500 mt-1">{f.desc}</p>
        <div className="mt-2 text-xs font-mono text-gray-400 break-all">{f.url}</div>

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
    <div className="max-w-4xl mx-auto px-4 py-8">
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

      <div className="space-y-4">
        {FOLDERS.map((f) => <FolderCard key={f.file} f={f} toast={toast} />)}
      </div>

      <h2 className="text-sm font-bold uppercase tracking-wide mt-9 mb-3" style={{ color: GREEN }}>
        Cobrança / Pagamento
      </h2>
      <FolderCard f={PAGAMENTO} toast={toast} />
    </div>
  );
}
