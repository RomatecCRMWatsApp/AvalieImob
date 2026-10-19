// @module garantias/GarantiaModais — modais do card da Avaliação de Garantias.
// Paridade com o card do PTAM (e-mail, link público, recibo, Telegram, histórico do
// link e visualizador de PDF), apontando para as rotas /garantias/{id}/...
import React, { useEffect, useState } from 'react';
import { Check, Copy, Download, ExternalLink, Eye, Link2, Loader2, Mail, Receipt, Send, X } from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { garantiasAPI } from '../../../lib/api';
import { fmtDataHora } from '../../../utils/datasServidor';

export const rotulo = (g) => `Laudo ${g.numero || ''}`.trim();

const Casca = ({ onClose, icon: Icon, cor, titulo, sub, children, largura = 'max-w-md' }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
    <div className={`bg-white rounded-2xl shadow-xl w-full ${largura} p-6 relative max-h-[90vh] flex flex-col`}>
      <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600" aria-label="Fechar">
        <X className="w-5 h-5" />
      </button>
      <div className="flex items-center gap-3 mb-5">
        <div className={`w-10 h-10 rounded-xl ${cor} flex items-center justify-center`}><Icon className="w-5 h-5" /></div>
        <div>
          <h2 className="font-semibold text-gray-900 text-base">{titulo}</h2>
          <p className="text-xs text-gray-500">{sub}</p>
        </div>
      </div>
      {children}
    </div>
  </div>
);

const inputCls = 'w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-200';

export const EmailModal = ({ g, onClose, onSent }) => {
  const { toast } = useToast();
  const [form, setForm] = useState({ destinatario: g.solicitante?.email || '', nome_cliente: g.solicitante?.nome || '', mensagem_extra: '' });
  const [sending, setSending] = useState(false);
  const enviar = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      await garantiasAPI.sendEmail(g.id, { ...form, destinatario: form.destinatario.trim() });
      toast({ title: 'E-mail enviado com sucesso!' });
      onSent?.(); onClose();
    } catch (err) {
      toast({ title: err?.response?.data?.detail || 'Erro ao enviar e-mail.', variant: 'destructive' });
    } finally { setSending(false); }
  };
  return (
    <Casca onClose={onClose} icon={Mail} cor="bg-emerald-900/10 text-emerald-900" titulo="Enviar laudo por E-mail" sub={`${rotulo(g)} — PDF em anexo`}>
      <form onSubmit={enviar} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">E-mail do destinatário <span className="text-red-500">*</span></label>
          <input type="email" required value={form.destinatario} onChange={(e) => setForm(f => ({ ...f, destinatario: e.target.value }))} className={inputCls} placeholder="cliente@exemplo.com" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nome do cliente</label>
          <input value={form.nome_cliente} onChange={(e) => setForm(f => ({ ...f, nome_cliente: e.target.value }))} className={inputCls} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Mensagem adicional (opcional)</label>
          <textarea rows={3} value={form.mensagem_extra} onChange={(e) => setForm(f => ({ ...f, mensagem_extra: e.target.value }))} className={`${inputCls} resize-none`} />
        </div>
        <div className="flex gap-2 pt-1">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">Cancelar</Button>
          <Button type="submit" disabled={sending || !form.destinatario.trim()} className="flex-1 bg-emerald-900 hover:bg-emerald-800 text-white">
            {sending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Enviando...</> : <><Send className="w-4 h-4 mr-2" />Enviar</>}
          </Button>
        </div>
      </form>
    </Casca>
  );
};

export const ShareModal = ({ g, url, onClose, onDesativar }) => {
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);
  const [telefone, setTelefone] = useState(g.solicitante?.telefone ? `55${String(g.solicitante.telefone).replace(/\D/g, '').replace(/^55/, '')}` : '55');
  const [enviando, setEnviando] = useState(false);
  const copiar = () => { navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  const whatsapp = async () => {
    const num = (telefone || '').replace(/\D/g, '');
    if (num.length < 12) {
      toast({ title: 'Informe o número com DDI + DDD', description: 'Ex.: 5599991811246', variant: 'destructive' });
      return;
    }
    setEnviando(true);
    try {
      await garantiasAPI.enviarWhatsAppLink(g.id, num);
      toast({ title: 'Link enviado via WhatsApp!' });
      onClose();
    } catch (e) {
      const detail = e.response?.data?.detail || '';
      if (/configurad|Cadastre/.test(detail)) {
        const text = `Segue o laudo de avaliação de garantia ${g.numero || ''}:\n${url}`;
        window.open(`https://wa.me/${num}?text=${encodeURIComponent(text)}`, '_blank');
        toast({ title: 'Z-API não configurada', description: 'Abrindo no WhatsApp Web (modo manual).' });
      } else {
        toast({ title: detail || 'Erro ao enviar via WhatsApp', variant: 'destructive' });
      }
    } finally { setEnviando(false); }
  };
  return (
    <Casca onClose={onClose} icon={Link2} cor="bg-emerald-900/10 text-emerald-900" titulo="Link de Compartilhamento" sub={rotulo(g)}>
      <div className="space-y-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">URL do laudo</p>
          <div className="flex gap-2">
            <input value={url} readOnly className="flex-1 bg-white border rounded px-3 py-2 text-sm font-mono text-gray-600 min-w-0" />
            <Button variant="outline" size="sm" onClick={copiar}>{copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}</Button>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-600"><Eye className="w-4 h-4" /><span>{g.link_views || 0} visualizações</span></div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Enviar direto para um número (opcional)</p>
          <input type="tel" value={telefone} onChange={(e) => setTelefone(e.target.value)} className="w-full bg-white border rounded px-3 py-2 text-sm" placeholder="55 99 99999-9999" />
        </div>
        <div className="flex gap-2">
          <Button className="flex-1 bg-green-600 hover:bg-green-700 text-white" onClick={whatsapp} disabled={enviando}>
            {enviando ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}{enviando ? 'Enviando...' : 'WhatsApp'}
          </Button>
          <Button variant="outline" className="flex-1" onClick={() => window.open(url, '_blank')}><ExternalLink className="w-4 h-4 mr-2" />Abrir</Button>
        </div>
        <Button variant="outline" className="w-full text-red-600 border-red-200 hover:bg-red-50" onClick={() => { onDesativar(); onClose(); }}>Desativar link</Button>
      </div>
    </Casca>
  );
};

export const ReciboModal = ({ g, onClose, onGerado }) => {
  const { toast } = useToast();
  const [valor, setValor] = useState(g.honorarios ? String(g.honorarios) : '');
  const [forma, setForma] = useState('PIX');
  const [data, setData] = useState(new Date().toISOString().slice(0, 10));
  const [gerando, setGerando] = useState(false);
  const [gerado, setGerado] = useState(Boolean(g.recibo_emitido));
  const gerar = async (e) => {
    e.preventDefault();
    const v = parseFloat(String(valor).replace(/\./g, '').replace(',', '.'));
    if (!v || v <= 0) { toast({ title: 'Informe um valor válido', variant: 'destructive' }); return; }
    setGerando(true);
    try {
      await garantiasAPI.gerarRecibo(g.id, { valor_honorarios: v, forma_pagamento: forma, data_pagamento: data });
      toast({ title: 'Recibo gerado com sucesso!' });
      setGerado(true); onGerado?.();
    } catch (err) {
      toast({ title: err.response?.data?.detail || 'Erro ao gerar recibo', variant: 'destructive' });
    } finally { setGerando(false); }
  };
  const baixar = async () => {
    try {
      const blob = await garantiasAPI.downloadRecibo(g.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `RECIBO_GARANTIA_${(g.numero || 'sem-numero').replace(/\//g, '-')}.pdf`; a.click();
      window.URL.revokeObjectURL(url);
    } catch { toast({ title: 'Erro ao baixar recibo', variant: 'destructive' }); }
  };
  return (
    <Casca onClose={onClose} icon={Receipt} cor="bg-amber-100 text-amber-700" titulo="Recibo de Honorários" sub={rotulo(g)}>
      <form onSubmit={gerar} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Valor dos honorários (R$) <span className="text-red-500">*</span></label>
          <input inputMode="decimal" required value={valor} onChange={(e) => setValor(e.target.value)} placeholder="0,00" className={inputCls} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Forma de pagamento</label>
            <select value={forma} onChange={(e) => setForma(e.target.value)} className={inputCls}>
              {['PIX', 'Dinheiro', 'Transferência bancária', 'Boleto', 'Cartão de crédito', 'Cartão de débito', 'Cheque'].map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data do pagamento</label>
            <input type="date" value={data} onChange={(e) => setData(e.target.value)} className={inputCls} />
          </div>
        </div>
        <Button type="submit" disabled={gerando} className="w-full bg-amber-500 hover:bg-amber-600 text-white font-bold gap-2">
          {gerando ? <><Loader2 className="w-4 h-4 animate-spin" />Gerando...</> : <><Receipt className="w-4 h-4" />Gerar recibo</>}
        </Button>
        {gerado && (
          <Button type="button" variant="outline" onClick={baixar} className="w-full gap-2 text-amber-800 border-amber-200 hover:bg-amber-50">
            <Download className="w-4 h-4" />Baixar PDF do recibo
          </Button>
        )}
      </form>
    </Casca>
  );
};

export const TelegramModal = ({ g, onClose }) => {
  const { toast } = useToast();
  const [chatId, setChatId] = useState(() => { try { return localStorage.getItem('avalieimob_telegram_chat_id') || ''; } catch { return ''; } });
  const [legenda, setLegenda] = useState(`Segue o laudo de avaliação de garantia ${g.numero || ''}`);
  const [enviando, setEnviando] = useState(false);
  const enviar = async (e) => {
    e.preventDefault();
    if (!chatId.trim()) { toast({ title: 'Informe o chat_id ou @username', variant: 'destructive' }); return; }
    setEnviando(true);
    try {
      await garantiasAPI.enviarTelegram(g.id, chatId.trim(), legenda);
      try { localStorage.setItem('avalieimob_telegram_chat_id', chatId.trim()); } catch { /* sem storage */ }
      toast({ title: 'Enviado via Telegram!' });
      onClose();
    } catch (err) {
      toast({ title: err.response?.data?.detail || 'Erro ao enviar Telegram', variant: 'destructive' });
    } finally { setEnviando(false); }
  };
  return (
    <Casca onClose={onClose} icon={Send} cor="bg-sky-100 text-sky-600" titulo="Enviar via Telegram" sub={rotulo(g)}>
      <form onSubmit={enviar} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Chat ID ou @usuario <span className="text-red-500">*</span></label>
          <input required value={chatId} onChange={(e) => setChatId(e.target.value)} placeholder="ex: @joaosilva ou 123456789" className={`${inputCls} font-mono`} />
          <p className="text-xs text-gray-500 mt-1">Pra grupo, use o ID numérico (começa com -100). O destinatário precisa ter iniciado conversa com o bot.</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Legenda</label>
          <textarea rows={3} value={legenda} onChange={(e) => setLegenda(e.target.value)} className={`${inputCls} resize-none`} />
        </div>
        <Button type="submit" disabled={enviando} className="w-full bg-sky-500 hover:bg-sky-600 text-white font-bold gap-2">
          {enviando ? <><Loader2 className="w-4 h-4 animate-spin" />Enviando...</> : <><Send className="w-4 h-4" />Enviar via Telegram</>}
        </Button>
      </form>
    </Casca>
  );
};

const CANAL = { whatsapp: 'WhatsApp', telegram: 'Telegram', email: 'E-mail', link: 'Link' };
const EVENTO = {
  gerado: { icon: Link2, color: 'text-gray-500', bg: 'bg-gray-100', label: 'Link gerado' },
  enviado: { icon: Send, color: 'text-emerald-600', bg: 'bg-emerald-100', label: 'Enviado' },
  visualizado: { icon: Eye, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Visualizado pelo cliente' },
  desativado: { icon: X, color: 'text-red-500', bg: 'bg-red-100', label: 'Link desativado' },
};

export const LinkEventosModal = ({ g, onClose }) => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [dados, setDados] = useState(null);
  useEffect(() => {
    let vivo = true;
    garantiasAPI.linkEventos(g.id)
      .then((d) => { if (vivo) setDados(d); })
      .catch((e) => toast({ title: e.response?.data?.detail || 'Erro ao carregar histórico', variant: 'destructive' }))
      .finally(() => { if (vivo) setLoading(false); });
    return () => { vivo = false; };
  }, [g.id, toast]);
  const resumo = dados?.resumo || {};
  const eventos = dados?.eventos || [];
  return (
    <Casca onClose={onClose} icon={Eye} cor="bg-blue-100 text-blue-600" titulo="Controle do Link" sub={rotulo(g)} largura="max-w-lg">
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="rounded-xl bg-blue-50 border border-blue-100 p-3">
          <p className="text-2xl font-bold text-blue-600">{resumo.views || 0}</p>
          <p className="text-xs text-gray-500">Visualizações do cliente</p>
          {resumo.views_last && <p className="text-[11px] text-gray-400 mt-1">Última: {fmtDataHora(resumo.views_last)}</p>}
        </div>
        <div className="rounded-xl bg-emerald-50 border border-emerald-100 p-3">
          <p className="text-2xl font-bold text-emerald-600">{resumo.sends || 0}</p>
          <p className="text-xs text-gray-500">Envios realizados</p>
          {resumo.last_sent && <p className="text-[11px] text-gray-400 mt-1">Último: {CANAL[resumo.last_canal] || resumo.last_canal || ''} · {fmtDataHora(resumo.last_sent)}</p>}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto -mx-1 px-1">
        {loading && <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-blue-600" /></div>}
        {!loading && eventos.length === 0 && <div className="text-center py-10 text-gray-400 text-sm">Nenhum evento registrado ainda.</div>}
        {!loading && eventos.map((ev) => {
          const cfg = EVENTO[ev.tipo] || EVENTO.gerado;
          const Icon = cfg.icon;
          const canal = ev.canal && ev.tipo === 'enviado' ? ` via ${CANAL[ev.canal] || ev.canal}` : '';
          return (
            <div key={ev.id} className="flex items-start gap-3 py-2 border-b border-gray-50 last:border-0">
              <div className={`w-8 h-8 rounded-lg ${cfg.bg} flex items-center justify-center shrink-0`}><Icon className={`w-4 h-4 ${cfg.color}`} /></div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-800">{cfg.label}{canal}</p>
                {ev.destinatario && <p className="text-xs text-gray-500 truncate">Para: {ev.destinatario}</p>}
                <p className="text-[11px] text-gray-400">{fmtDataHora(ev.created_at)}{ev.ip ? ` · ${ev.ip}` : ''}</p>
              </div>
            </div>
          );
        })}
      </div>
    </Casca>
  );
};

export const PdfViewer = ({ modal, onClose }) => (
  <div onClick={onClose} className="fixed inset-0 z-[1000] flex items-center justify-center p-4" style={{ background: 'rgba(8,14,9,0.78)', backdropFilter: 'blur(3px)' }}>
    <div onClick={(e) => e.stopPropagation()} className="flex flex-col overflow-hidden rounded-2xl"
      style={{ width: 'min(960px, 96vw)', height: 'min(92vh, 1000px)', background: '#14241a', border: '1px solid rgba(76,175,80,0.22)', boxShadow: '0 18px 50px rgba(0,0,0,0.55)' }}>
      <div className="flex items-center gap-2.5 px-4 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
        <span className="flex-1 truncate text-[13px] font-semibold" style={{ color: '#E8F5E9' }}>{modal.titulo}</span>
        <a href={modal.url} target="_blank" rel="noopener noreferrer" className="text-xs whitespace-nowrap rounded-md px-3 py-1.5" style={{ color: '#B8860B', border: '1px solid rgba(184,134,11,0.4)' }}>Abrir em nova aba</a>
        <button onClick={onClose} aria-label="Fechar" className="w-8 h-8 rounded-md text-white/70" style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}>✕</button>
      </div>
      <iframe src={modal.url} title="Visualizador de PDF" className="flex-1 w-full border-0" style={{ background: '#f5f5f0' }} />
    </div>
  </div>
);
