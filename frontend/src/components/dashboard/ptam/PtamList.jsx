import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, FileText, Download, Trash2, Loader2, Calendar, DollarSign, FileDown } from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { ptamAPI } from '../../../lib/api';

const PtamList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState({});
  const [docxLoading, setDocxLoading] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try { setItems(await ptamAPI.list()); }
    catch (err) { console.warn(err); toast({ title: 'Erro ao carregar', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

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

  return (
    <div className="space-y-6">
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
