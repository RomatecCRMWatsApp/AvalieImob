import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, FileText, Download, Trash2, Loader2, Calendar, DollarSign, FileDown, Mail, X, Send, Lock, Link2, Eye, Check, Copy, ExternalLink, PenLine, Copy as CopyIcon, Receipt, MessageCircle, Edit3, ShieldCheck, RefreshCw } from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { ptamAPI, ptamExtrasAPI } from '../../../lib/api';
import AssinaturaDigital from './AssinaturaDigital';

// ── Modal de envio por email ──────────────────────────────────────────────────
const EmailModal = ({ ptam, onClose, onSent }) => {
  const { toast } = useToast();
  const [form, setForm] = useState({ destinatario: '', nome_cliente: '', mensagem_extra: '' });
  const [sending, setSending] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!form.destinatario.trim()) return;
    setSending(true);
    try {
      await ptamAPI.sendEmail(ptam.id, {
        destinatario: form.destinatario.trim(),
        nome_cliente: form.nome_cliente.trim(),
        mensagem_extra: form.mensagem_extra.trim(),
      });
      toast({ title: 'E-mail enviado com sucesso!' });
      onSent();
      onClose();
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Erro ao enviar e-mail.';
      toast({ title: detail, variant: 'destructive' });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition"
          aria-label="Fechar"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-emerald-900/10 flex items-center justify-center">
            <Mail className="w-5 h-5 text-emerald-900" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900 text-base">Enviar PTAM por E-mail</h2>
            <p className="text-xs text-gray-500">PTAM {ptam.number} — PDF em anexo</p>
          </div>
        </div>

        <form onSubmit={handleSend} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              E-mail do destinatário <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              required
              placeholder="cliente@exemplo.com"
              value={form.destinatario}
              onChange={e => setForm(f => ({ ...f, destinatario: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm
                         focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-200"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome do cliente
            </label>
            <input
              type="text"
              placeholder="Ex.: João da Silva"
              value={form.nome_cliente}
              onChange={e => setForm(f => ({ ...f, nome_cliente: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm
                         focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-200"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Mensagem adicional (opcional)
            </label>
            <textarea
              rows={3}
              placeholder="Ex.: Qualquer dúvida estou à disposição."
              value={form.mensagem_extra}
              onChange={e => setForm(f => ({ ...f, mensagem_extra: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm resize-none
                         focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-200"
            />
          </div>

          <div className="flex gap-2 pt-1">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={sending || !form.destinatario.trim()}
              className="flex-1 bg-emerald-900 hover:bg-emerald-800 text-white"
            >
              {sending ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Enviando...</>
              ) : (
                <><Send className="w-4 h-4 mr-2" />Enviar</>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ── Lista de PTAMs ─────────────────────────────────────────────────────────────
const PtamList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState({});
  const [docxLoading, setDocxLoading] = useState({});
  const [emailModal, setEmailModal] = useState(null);
  const [shareModal, setShareModal] = useState(null);
  const [shareLoading, setShareLoading] = useState({});
  const [assinaturaModal, setAssinaturaModal] = useState(null);
  const [reciboModal, setReciboModal] = useState(null);
  const [telegramModal, setTelegramModal] = useState(null);
  const [cloneLoading, setCloneLoading] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try { setItems(await ptamAPI.list()); }
    catch (err) { console.warn(err); toast({ title: 'Erro ao carregar', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const handleCompartilhar = async (ptam) => {
    setShareLoading(prev => ({ ...prev, [ptam.id]: true }));
    try {
      if (ptam.link_publico_ativo) {
        // Já tem link ativo, apenas copiar
        const url = `${window.location.origin}/laudo/${ptam.link_publico_token}`;
        navigator.clipboard.writeText(url);
        toast({ title: 'Link copiado!', description: 'URL copiada para a área de transferência' });
      } else {
        // Gerar novo link
        const res = await ptamAPI.compartilhar(ptam.id);
        navigator.clipboard.writeText(res.url);
        toast({ title: 'Link gerado!', description: 'URL copiada para a área de transferência' });
        load(); // Recarregar lista
      }
    } catch (err) {
      toast({ title: 'Erro ao compartilhar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setShareLoading(prev => ({ ...prev, [ptam.id]: false }));
    }
  };

  const handleDesativarCompartilhamento = async (ptam) => {
    try {
      await ptamAPI.desativarCompartilhamento(ptam.id);
      toast({ title: 'Compartilhamento desativado' });
      load();
    } catch (err) {
      toast({ title: 'Erro ao desativar', variant: 'destructive' });
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Remover este PTAM? Esta ação não pode ser desfeita.')) return;
    try { await ptamAPI.remove(id); setItems(items.filter((p) => p.id !== id)); toast({ title: 'PTAM removido' }); }
    catch { toast({ title: 'Erro ao remover', variant: 'destructive' }); }
  };

  const clonar = async (p) => {
    setCloneLoading(prev => ({ ...prev, [p.id]: true }));
    try {
      const novo = await ptamExtrasAPI.clonar(p.id);
      toast({ title: `PTAM clonado: ${novo.numero_ptam || novo.number}` });
      load();
    } catch (e) {
      toast({ title: 'Erro ao clonar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally {
      setCloneLoading(prev => ({ ...prev, [p.id]: false }));
    }
  };

  // Envio direto via Z-API ou Meta (provedor configurado em Configurações).
  // Faz fallback pra wa.me se a integração não estiver configurada.
  const enviarWhatsApp = async (p) => {
    const phone = window.prompt('WhatsApp do destinatário (com DDI+DDD, só dígitos):', '55');
    if (!phone) return;
    try {
      const res = await ptamExtrasAPI.enviarWhatsApp(p.id, phone.trim());
      toast({ title: `Laudo enviado via ${res.provider === 'meta' ? 'Meta' : 'Z-API'}!` });
    } catch (e) {
      const detail = e.response?.data?.detail || '';
      // Se integração não configurada, abre wa.me como fallback
      if (detail.includes('não configurada') || detail.includes('Cadastre')) {
        const link = `${window.location.origin}/laudo/${p.link_publico_token || ''}`;
        const texto = `Segue o laudo PTAM ${p.numero_ptam || p.number}` + (p.link_publico_ativo ? `\n${link}` : '');
        const url = `https://wa.me/${phone.replace(/\D/g, '')}?text=${encodeURIComponent(texto)}`;
        toast({
          title: 'Z-API/Meta não configurados',
          description: 'Abrindo no WhatsApp Web (modo manual). Configure em Configurações → Integrações.',
        });
        window.open(url, '_blank');
      } else {
        toast({ title: detail || 'Erro ao enviar WhatsApp', variant: 'destructive' });
      }
    }
  };

  const download = async (p) => {
    setDocxLoading((prev) => ({ ...prev, [p.id]: true }));
    try {
      const blob = await ptamAPI.downloadDocx(p.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `PTAM_${(p.number || 'sem-numero').replace(/\//g, '-')}.docx`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast({ title: 'DOCX gerado com sucesso' });
    } catch { toast({ title: 'Erro ao baixar DOCX', variant: 'destructive' }); }
    finally { setDocxLoading((prev) => ({ ...prev, [p.id]: false })); }
  };

  const downloadPdf = async (p) => {
    setPdfLoading((prev) => ({ ...prev, [p.id]: true }));
    try {
      const blob = await ptamAPI.downloadPdf(p.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      a.download = `PTAM_${(p.number || 'sem-numero').replace(/\//g, '-')}_${date}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast({ title: 'PDF gerado com sucesso' });
    } catch {
      toast({ title: 'Erro ao gerar PDF', variant: 'destructive' });
    } finally {
      setPdfLoading((prev) => ({ ...prev, [p.id]: false }));
    }
  };

  const statusColor = (s) => {
    if (s === 'Emitido') return 'bg-emerald-100 text-emerald-800';
    if (s === 'Em revisão') return 'bg-amber-100 text-amber-800';
    return 'bg-gray-100 text-gray-700';
  };

  // Modal de compartilhamento
  const ShareModal = ({ ptam, onClose }) => {
    const url = `${window.location.origin}/laudo/${ptam.link_publico_token}`;
    const [copied, setCopied] = useState(false);

    const copyLink = () => {
      navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    const shareWhatsApp = () => {
      const text = `Segue o laudo de avaliação do imóvel: ${url}`;
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
    };

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative">
          <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-emerald-900/10 flex items-center justify-center">
              <Link2 className="w-5 h-5 text-emerald-900" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900 text-base">Link de Compartilhamento</h2>
              <p className="text-xs text-gray-500">PTAM {ptam.number}</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">URL do laudo</p>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  value={url} 
                  readOnly 
                  className="flex-1 bg-white border rounded px-3 py-2 text-sm font-mono text-gray-600"
                />
                <Button variant="outline" size="sm" onClick={copyLink}>
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
            </div>

            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Eye className="w-4 h-4" />
              <span>{ptam.visualizacoes || 0} visualizações</span>
            </div>

            <div className="flex gap-2">
              <Button className="flex-1 bg-green-600 hover:bg-green-700 text-white" onClick={shareWhatsApp}>
                <Send className="w-4 h-4 mr-2" />
                WhatsApp
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => window.open(url, '_blank')}>
                <ExternalLink className="w-4 h-4 mr-2" />
                Abrir
              </Button>
            </div>

            <Button 
              variant="outline" 
              className="w-full text-red-600 border-red-200 hover:bg-red-50"
              onClick={() => { handleDesativarCompartilhamento(ptam); onClose(); }}
            >
              Desativar link
            </Button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {emailModal && (
        <EmailModal
          ptam={emailModal}
          onClose={() => setEmailModal(null)}
          onSent={load}
        />
      )}

      {shareModal && (
        <ShareModal
          ptam={shareModal}
          onClose={() => setShareModal(null)}
        />
      )}

      {assinaturaModal && (
        <AssinaturaDigital
          tipo="ptam"
          docId={assinaturaModal.id}
          docData={assinaturaModal}
          onClose={() => setAssinaturaModal(null)}
          onUpdate={(updates) => {
            setItems(prev => prev.map(p => p.id === assinaturaModal.id ? { ...p, ...updates } : p));
          }}
        />
      )}

      {reciboModal && (
        <ReciboModal
          ptam={reciboModal}
          onClose={() => setReciboModal(null)}
          onGerado={load}
        />
      )}

      {telegramModal && (
        <TelegramModal
          ptam={telegramModal}
          onClose={() => setTelegramModal(null)}
        />
      )}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-gray-900">PTAM — Pareceres Técnicos</h1>
          <p className="text-gray-600 mt-1">Crie laudos completos conforme NBR 14.653 com exportação em DOCX e PDF.</p>
        </div>
        <Button onClick={() => nav('/dashboard/ptam/novo')} className="bg-emerald-900 hover:bg-emerald-800 text-white"><Plus className="w-4 h-4 mr-2" />Novo PTAM</Button>
      </div>

      {loading ? (
        <div className="py-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-800" /></div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-gray-200">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <div className="font-semibold text-gray-900">Nenhum PTAM criado ainda</div>
          <p className="text-sm text-gray-500 mt-1">Clique em "Novo PTAM" para iniciar seu primeiro laudo.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((p) => (
            <div key={p.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-900/10 flex items-center justify-center"><FileText className="w-5 h-5 text-emerald-900" /></div>
                <div className="flex gap-1.5 flex-wrap justify-end">
                  <Badge className={statusColor(p.status)}>{p.status}</Badge>
                  {p.lacrado && (
                    <Badge className="bg-blue-100 text-blue-800 border border-blue-200" title={p.versao_lacrada || 'Versão lacrada'}>
                      <Lock className="w-3 h-3 mr-1 inline" />Lacrado
                    </Badge>
                  )}
                  {p.d4sign_status === 'assinado' && (
                    <Badge className="bg-indigo-900 text-white border border-indigo-800">
                      Assinado
                    </Badge>
                  )}
                  {p.d4sign_status === 'aguardando' && (
                    <Badge className="bg-amber-100 text-amber-800 border border-amber-200">
                      Aguardando
                    </Badge>
                  )}
                </div>
              </div>
              <div className="text-xs font-semibold text-emerald-700 tracking-wider">PTAM {p.number}</div>
              <div className="font-semibold text-gray-900 mt-1 line-clamp-1">{p.property_label || p.property_address || '(sem título)'}</div>
              <div className="text-xs text-gray-500 mt-1 line-clamp-1">{p.solicitante || '—'}</div>
              <div className="mt-4 pt-4 border-t border-gray-100 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs text-gray-600"><DollarSign className="w-3 h-3" />R$ {Number(p.total_indemnity || 0).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}</div>
                <div className="flex items-center gap-1.5 text-xs text-gray-500"><Calendar className="w-3 h-3" />{p.updated_at ? new Date(p.updated_at).toLocaleDateString('pt-BR') : '—'}</div>
              </div>
              {/* Linha 1: ações principais */}
              <div className="flex gap-2 mt-4 flex-wrap">
                <Button
                  size="sm"
                  className="bg-amber-400 hover:bg-amber-500 text-emerald-950 font-semibold gap-1"
                  onClick={() => nav(`/dashboard/ptam/${p.id}`)}
                  title="Abrir / Editar"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  Abrir
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  title="Exportar PDF"
                  onClick={() => downloadPdf(p)}
                  disabled={pdfLoading[p.id]}
                  className="gap-1"
                >
                  {pdfLoading[p.id] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5" />}
                  PDF
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  title="Clonar PTAM"
                  onClick={() => clonar(p)}
                  disabled={cloneLoading[p.id]}
                  className="gap-1 text-amber-700 border-amber-200 hover:bg-amber-50"
                >
                  {cloneLoading[p.id] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CopyIcon className="w-3.5 h-3.5" />}
                  Clonar
                </Button>
              </div>

              {/* Linha 2: assinatura */}
              <div className="flex gap-2 mt-2 flex-wrap">
                <Button
                  size="sm"
                  variant="outline"
                  title={
                    p.icp_status === 'assinado'
                      ? 'Assinado com ICP-Brasil'
                      : p.d4sign_status === 'assinado'
                      ? 'Assinado via D4Sign'
                      : p.d4sign_status === 'aguardando'
                      ? 'Aguardando assinaturas'
                      : 'Assinar digitalmente'
                  }
                  onClick={() => setAssinaturaModal(p)}
                  className={
                    `gap-1 ${
                      p.icp_status === 'assinado'
                        ? 'text-emerald-700 border-emerald-300 bg-emerald-50 hover:bg-emerald-100'
                        : p.d4sign_status === 'assinado'
                        ? 'text-indigo-700 border-indigo-200 hover:bg-indigo-50'
                        : p.d4sign_status === 'aguardando'
                        ? 'text-amber-700 border-amber-200 hover:bg-amber-50'
                        : 'text-emerald-700 border-emerald-200 hover:bg-emerald-50'
                    }`
                  }
                >
                  {p.icp_status === 'assinado' ? <ShieldCheck className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                  {p.icp_status === 'assinado' || p.d4sign_status === 'assinado' ? 'Assinado' : 'Assinar'}
                </Button>
                {(p.icp_status === 'assinado' || p.d4sign_status === 'assinado') && (
                  <Button
                    size="sm"
                    variant="outline"
                    title="Reassinar (gera nova assinatura sobre versão atual)"
                    onClick={() => setAssinaturaModal({ ...p, icp_status: null, d4sign_status: null })}
                    className="gap-1 text-blue-700 border-blue-200 hover:bg-blue-50"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Re-assinar
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  title="Recibo de honorários"
                  onClick={() => setReciboModal(p)}
                  className="gap-1 text-amber-800 border-amber-200 bg-amber-50 hover:bg-amber-100"
                >
                  <Receipt className="w-3.5 h-3.5" />
                  Recibo
                </Button>
              </div>

              {/* Linha 3: envio */}
              <div className="flex gap-2 mt-2 flex-wrap">
                <Button
                  size="sm"
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white gap-1"
                  title="Enviar por WhatsApp"
                  onClick={() => enviarWhatsApp(p)}
                >
                  <MessageCircle className="w-3.5 h-3.5" />
                  WhatsApp
                </Button>
                <Button
                  size="sm"
                  className="flex-1 bg-sky-500 hover:bg-sky-600 text-white gap-1"
                  title="Enviar via Telegram"
                  onClick={() => setTelegramModal(p)}
                >
                  <Send className="w-3.5 h-3.5" />
                  Telegram
                </Button>
                <Button size="sm" variant="outline" title="Enviar por E-mail" onClick={() => setEmailModal(p)}
                  className="text-emerald-700 hover:bg-emerald-50 border-emerald-200">
                  <Mail className="w-3.5 h-3.5" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  title={p.link_publico_ativo ? "Link ativo" : "Compartilhar via link"}
                  onClick={() => p.link_publico_ativo ? setShareModal(p) : handleCompartilhar(p)}
                  disabled={shareLoading[p.id]}
                  className={p.link_publico_ativo ? "text-blue-600 border-blue-200 hover:bg-blue-50" : ""}
                >
                  {shareLoading[p.id] ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Link2 className="w-3.5 h-3.5" />
                  )}
                </Button>
                <Button size="sm" variant="outline" title="Exportar DOCX" onClick={() => download(p)} disabled={docxLoading[p.id]}>
                  {docxLoading[p.id] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                </Button>
                <Button size="sm" variant="outline" className="text-red-600 hover:bg-red-50" onClick={() => remove(p.id)} title="Excluir">
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// Modal: Recibo de Honorários
// ════════════════════════════════════════════════════════════════════════════
const ReciboModal = ({ ptam, onClose, onGerado }) => {
  const { toast } = useToast();
  const [valor, setValor] = useState(ptam?.honorarios ? String(ptam.honorarios) : '');
  const [forma, setForma] = useState('PIX');
  const [data, setData] = useState(new Date().toISOString().slice(0, 10));
  const [gerando, setGerando] = useState(false);
  const [reciboGerado, setReciboGerado] = useState(Boolean(ptam?.recibo_emitido));

  const handleGerar = async (e) => {
    e.preventDefault();
    const valorNum = parseFloat(String(valor).replace(',', '.'));
    if (!valorNum || valorNum <= 0) {
      toast({ title: 'Informe um valor válido', variant: 'destructive' });
      return;
    }
    setGerando(true);
    try {
      await ptamExtrasAPI.gerarRecibo(ptam.id, {
        valor_honorarios: valorNum,
        forma_pagamento: forma,
        data_pagamento: data,
      });
      toast({ title: 'Recibo gerado com sucesso!' });
      setReciboGerado(true);
      if (onGerado) onGerado();
    } catch (err) {
      toast({ title: err.response?.data?.detail || 'Erro ao gerar recibo', variant: 'destructive' });
    } finally {
      setGerando(false);
    }
  };

  const handleBaixar = async () => {
    try {
      const blob = await ptamExtrasAPI.downloadRecibo(ptam.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `RECIBO_PTAM_${(ptam.numero_ptam || 'sem-numero').replace(/\//g, '-')}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast({ title: 'Erro ao baixar recibo', variant: 'destructive' });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
          <X className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
            <Receipt className="w-5 h-5 text-amber-700" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900 text-base">Recibo de Honorários</h2>
            <p className="text-xs text-gray-500">PTAM {ptam.numero_ptam || ptam.number}</p>
          </div>
        </div>

        <form onSubmit={handleGerar} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Valor dos honorários (R$) <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              inputMode="decimal"
              required
              value={valor}
              onChange={e => setValor(e.target.value)}
              placeholder="0,00"
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Forma de pagamento</label>
              <select
                value={forma}
                onChange={e => setForma(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500"
              >
                <option value="PIX">PIX</option>
                <option value="Dinheiro">Dinheiro</option>
                <option value="Transferência bancária">Transferência bancária</option>
                <option value="Boleto">Boleto</option>
                <option value="Cartão de crédito">Cartão de crédito</option>
                <option value="Cartão de débito">Cartão de débito</option>
                <option value="Cheque">Cheque</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data do pagamento</label>
              <input
                type="date"
                value={data}
                onChange={e => setData(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500"
              />
            </div>
          </div>

          <Button
            type="submit"
            disabled={gerando}
            className="w-full bg-amber-500 hover:bg-amber-600 text-white font-bold gap-2"
          >
            {gerando ? <><Loader2 className="w-4 h-4 animate-spin" />Gerando...</> : <><Receipt className="w-4 h-4" />Gerar recibo</>}
          </Button>

          {reciboGerado && (
            <Button
              type="button"
              variant="outline"
              onClick={handleBaixar}
              className="w-full gap-2 text-amber-800 border-amber-200 hover:bg-amber-50"
            >
              <Download className="w-4 h-4" />
              Baixar PDF do recibo
            </Button>
          )}
        </form>
      </div>
    </div>
  );
};


// ════════════════════════════════════════════════════════════════════════════
// Modal: Envio via Telegram
// ════════════════════════════════════════════════════════════════════════════
const TelegramModal = ({ ptam, onClose }) => {
  const { toast } = useToast();
  const [chatId, setChatId] = useState(localStorage.getItem('avalieimob_telegram_chat_id') || '');
  const [legenda, setLegenda] = useState(`Segue o laudo PTAM ${ptam.numero_ptam || ptam.number}`);
  const [enviando, setEnviando] = useState(false);

  const handleEnviar = async (e) => {
    e.preventDefault();
    if (!chatId.trim()) {
      toast({ title: 'Informe o chat_id ou @username', variant: 'destructive' });
      return;
    }
    setEnviando(true);
    try {
      await ptamExtrasAPI.enviarTelegram(ptam.id, chatId.trim(), legenda);
      localStorage.setItem('avalieimob_telegram_chat_id', chatId.trim());
      toast({ title: 'Enviado via Telegram!' });
      onClose();
    } catch (err) {
      toast({ title: err.response?.data?.detail || 'Erro ao enviar Telegram', variant: 'destructive' });
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
          <X className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-sky-100 flex items-center justify-center">
            <Send className="w-5 h-5 text-sky-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900 text-base">Enviar via Telegram</h2>
            <p className="text-xs text-gray-500">PTAM {ptam.numero_ptam || ptam.number}</p>
          </div>
        </div>

        <form onSubmit={handleEnviar} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Chat ID ou @usuario <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={chatId}
              onChange={e => setChatId(e.target.value)}
              placeholder="ex: @joaosilva ou 123456789"
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-sky-500 font-mono"
            />
            <p className="text-xs text-gray-500 mt-1">
              Pra grupo, use o ID numérico (começa com -100). O destinatário precisa ter
              iniciado conversa com o bot.
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Legenda</label>
            <textarea
              rows={3}
              value={legenda}
              onChange={(e) => setLegenda(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm resize-none focus:outline-none focus:border-sky-500"
            />
          </div>

          <Button
            type="submit"
            disabled={enviando}
            className="w-full bg-sky-500 hover:bg-sky-600 text-white font-bold gap-2"
          >
            {enviando ? <><Loader2 className="w-4 h-4 animate-spin" />Enviando...</> : <><Send className="w-4 h-4" />Enviar via Telegram</>}
          </Button>
        </form>
      </div>
    </div>
  );
};


export default PtamList;
