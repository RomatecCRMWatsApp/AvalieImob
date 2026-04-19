import React, { useState, useEffect, useCallback } from 'react';
import { FileText, Plus, Download, Eye, Sparkles, Search, Loader2, Trash2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { useToast } from '../../hooks/use-toast';
import { evaluationsAPI, clientsAPI, propertiesAPI } from '../../lib/api';

const statusColor = (s) => ({ 'Emitido': 'bg-emerald-100 text-emerald-800', 'Em revisão': 'bg-amber-100 text-amber-800', 'Em andamento': 'bg-blue-100 text-blue-800', 'Rascunho': 'bg-gray-100 text-gray-700' }[s] || 'bg-gray-100');

const Evaluations = () => {
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [clients, setClients] = useState([]);
  const [props, setProps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [viewer, setViewer] = useState(null);
  const [form, setForm] = useState({ type: 'PTAM', method: 'Comparativo Direto', client_id: '', property_id: '', value: 0 });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [e, c, p] = await Promise.all([evaluationsAPI.list(), clientsAPI.list(), propertiesAPI.list()]);
      setItems(e); setClients(c); setProps(p);
    } catch (err) { console.warn('Failed to load evaluations', err); toast({ title: 'Erro ao carregar', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const filtered = items.filter(e => (e.code || '').toLowerCase().includes(query.toLowerCase()));
  const clientName = (id) => clients.find(c => c.id === id)?.name || '—';
  const propRef = (id) => props.find(p => p.id === id)?.ref || '—';

  const create = async () => {
    try {
      const e = await evaluationsAPI.create(form);
      setItems([e, ...items]);
      toast({ title: 'Laudo criado', description: e.code });
      setOpen(false);
    } catch (e) { toast({ title: 'Erro', description: e.response?.data?.detail, variant: 'destructive' }); }
  };
  const updateStatus = async (e, status) => {
    try {
      const updated = await evaluationsAPI.update(e.id, { ...e, status });
      setItems(items.map(x => x.id === e.id ? updated : x));
      toast({ title: 'Status atualizado' });
    } catch { toast({ title: 'Erro', variant: 'destructive' }); }
  };
  const remove = async (id) => { if (!window.confirm('Remover?')) return; try { await evaluationsAPI.remove(id); setItems(items.filter(x => x.id !== id)); toast({ title: 'Removido' }); } catch { toast({ title: 'Erro', variant: 'destructive' }); } };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div><h1 className="font-display text-3xl font-bold text-gray-900">Laudos e PTAM</h1><p className="text-gray-600 mt-1">Pareceres técnicos e laudos de avaliação.</p></div>
        <Button onClick={() => setOpen(true)} className="bg-emerald-900 hover:bg-emerald-800 text-white"><Plus className="w-4 h-4 mr-2" />Novo laudo</Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <Input value={query} onChange={(e) => setQuery(e.target.value)} className="pl-10 bg-white" placeholder="Buscar por código..." />
      </div>

      {loading ? (
        <div className="py-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-800" /></div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(e => (
            <div key={e.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-900/10 flex items-center justify-center"><FileText className="w-5 h-5 text-emerald-900" /></div>
                <div className="flex items-center gap-2">
                  <Badge className={statusColor(e.status)}>{e.status}</Badge>
                  <button onClick={() => remove(e.id)} className="p-1.5 hover:bg-red-50 rounded text-red-600"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <div className="text-xs font-semibold text-emerald-700 tracking-wider">{e.code}</div>
              <div className="font-semibold text-gray-900 mt-1">{e.type} · {e.method}</div>
              <div className="text-xs text-gray-500 mt-1 truncate">{clientName(e.client_id)} · {propRef(e.property_id)}</div>
              <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
                <div><div className="text-[10px] text-gray-500 uppercase">Valor avaliado</div><div className="text-sm font-bold brand-green">R$ {Number(e.value || 0).toLocaleString('pt-BR')}</div></div>
                <div className="text-right"><div className="text-[10px] text-gray-500 uppercase">Amostras</div><div className="text-sm font-semibold">{e.samples || 0}</div></div>
              </div>
              <div className="flex gap-2 mt-4">
                <Button size="sm" variant="outline" className="flex-1" onClick={() => setViewer(e)}><Eye className="w-3.5 h-3.5 mr-1" />Ver</Button>
                {e.status !== 'Emitido' && <Button size="sm" className="flex-1 bg-emerald-900 text-white hover:bg-emerald-800" onClick={() => updateStatus(e, 'Emitido')}>Emitir</Button>}
                {e.status === 'Emitido' && <Button size="sm" variant="outline" className="flex-1" onClick={() => toast({ title: 'Em breve', description: 'Geração de PDF na próxima fase' })}><Download className="w-3.5 h-3.5 mr-1" />PDF</Button>}
              </div>
            </div>
          ))}
          {filtered.length === 0 && <div className="col-span-full text-center py-12 text-gray-400">Nenhum laudo cadastrado</div>}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Novo laudo / PTAM</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-sm font-medium">Tipo</label><Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="PTAM">PTAM</SelectItem><SelectItem value="Laudo">Laudo de Avaliação</SelectItem><SelectItem value="Garantia Safra">Garantia - Safra</SelectItem><SelectItem value="Garantia Rebanho">Garantia - Rebanho</SelectItem></SelectContent></Select></div>
              <div><label className="text-sm font-medium">Método</label><Select value={form.method} onValueChange={(v) => setForm({ ...form, method: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="Comparativo Direto">Comparativo Direto</SelectItem><SelectItem value="Evolutivo">Evolutivo</SelectItem><SelectItem value="Avaliação Agronômica">Avaliação Agronômica</SelectItem></SelectContent></Select></div>
            </div>
            <div><label className="text-sm font-medium">Cliente</label><Select value={form.client_id} onValueChange={(v) => setForm({ ...form, client_id: v })}><SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger><SelectContent>{clients.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="text-sm font-medium">Imóvel/Garantia</label><Select value={form.property_id} onValueChange={(v) => setForm({ ...form, property_id: v })}><SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger><SelectContent>{props.map(p => <SelectItem key={p.id} value={p.id}>{p.ref} — {p.subtype}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="text-sm font-medium">Valor avaliado (R$)</label><Input type="number" value={form.value} onChange={(e) => setForm({ ...form, value: Number(e.target.value) })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button><Button onClick={create} className="bg-emerald-900 hover:bg-emerald-800 text-white">Criar laudo</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!viewer} onOpenChange={(o) => !o && setViewer(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{viewer?.code}</DialogTitle></DialogHeader>
          {viewer && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 p-4 bg-emerald-50/40 rounded-lg">
                <div><div className="text-xs text-gray-500">Tipo</div><div className="font-semibold">{viewer.type}</div></div>
                <div><div className="text-xs text-gray-500">Método</div><div className="font-semibold">{viewer.method}</div></div>
                <div><div className="text-xs text-gray-500">Cliente</div><div className="font-semibold">{clientName(viewer.client_id)}</div></div>
                <div><div className="text-xs text-gray-500">Valor</div><div className="font-bold brand-green text-lg">R$ {Number(viewer.value || 0).toLocaleString('pt-BR')}</div></div>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 mb-2"><Sparkles className="w-3.5 h-3.5" />FUNDAMENTAÇÃO SUGERIDA</div>
                <p className="text-sm text-gray-700 leading-relaxed">O valor foi determinado mediante aplicação do Método {viewer.method}, conforme NBR 14.653 da ABNT. Use o Assistente IA para gerar fundamentação técnica personalizada para este laudo.</p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Evaluations;
