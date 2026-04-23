import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, FileText, Download, Trash2, Loader2, Calendar, DollarSign, FileDown, Mail, X, Send, Lock, Link2, Eye, Check, Copy, ExternalLink } from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { ptamAPI } from '../../../lib/api';

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
                </div>
              </div>
              <div className="text-xs font-semibold text-emerald-700 tracking-wider">PTAM {p.number}</div>
              <div className="font-semibold text-gray-900 mt-1 line-clamp-1">{p.property_label || p.property_address || '(sem título)'}</div>
              <div className="text-xs text-gray-500 mt-1 line-clamp-1">{p.solicitante || '—'}</div>
              <div className="mt-4 pt-4 border-t border-gray-100 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs text-gray-600"><DollarSign className="w-3 h-3" />R$ {Number(p.total_indemnity || 0).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}</div>
                <div className="flex items-center gap-1.5 text-xs text-gray-500"><Calendar className="w-3 h-3" />{p.updated_at ? new Date(p.updated_at).toLocaleDateString('pt-BR') : '—'}</div>
              </div>
              <div className="flex gap-2 mt-4">
                <Button size="sm" className="flex-1 bg-emerald-900 hover:bg-emerald-800 text-white" onClick={() => nav(`/dashboard/ptam/${p.id}`)}>Editar</Button>
                <Button size="sm" variant="outline" title="Enviar por E-mail" onClick={() => setEmailModal(p)}
                  className="text-emerald-700 hover:bg-emerald-50 border-emerald-200">
                  <Mail className="w-3.5 h-3.5" />
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  title={p.link_publico_ativo ? "Link ativo" : "Compartilhar"}
                  onClick={() => p.link_publico_ativo ? setShareModal(p) : handleCompartilhar(p)}
                  disabled={shareLoading[p.id]}
                  className={p.link_publico_ativo ? "text-blue-600 border-blue-200 hover:bg-blue-50" : ""}
                >
                  {shareLoading[p.id] ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : p.link_publico_ativo ? (
                    <Link2 className="w-3.5 h-3.5" />
                  ) : (
                    <Link2 className="w-3.5 h-3.5" />
                  )}
                </Button>
                <Button size="sm" variant="outline" title="Exportar PDF" onClick={() => downloadPdf(p)} disabled={pdfLoading[p.id]}>
                  {pdfLoading[p.id] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5" />}
                </Button>
                <Button size="sm" variant="outline" title="Exportar DOCX" onClick={() => download(p)} disabled={docxLoading[p.id]}>
                  {docxLoading[p.id] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                </Button>
                <Button size="sm" variant="outline" className="text-red-600 hover:bg-red-50" onClick={() => remove(p.id)}><Trash2 className="w-3.5 h-3.5" /></Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PtamList;
