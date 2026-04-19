import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Search, Edit, Trash2, Building2, Trees, Wheat, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';
import { useToast } from '../../hooks/use-toast';
import { propertiesAPI, clientsAPI } from '../../lib/api';

const empty = { ref: '', client_id: '', type: 'Urbano', subtype: '', address: '', city: '', area: 0, built_area: 0, value: 0, status: 'Rascunho' };

const typeIcon = (t) => {
  if (t === 'Urbano') return Building2;
  if (t === 'Rural') return Trees;
  return Wheat;
};
const typeColor = (t) => {
  if (t === 'Urbano') return 'bg-blue-50 text-blue-800';
  if (t === 'Rural') return 'bg-emerald-50 text-emerald-800';
  return 'bg-amber-50 text-amber-800';
};
const statusColor = (s) => {
  if (s === 'Concluído') return 'bg-emerald-100 text-emerald-800';
  if (s === 'Em andamento') return 'bg-amber-100 text-amber-800';
  return 'bg-gray-100 text-gray-700';
};

const Properties = () => {
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('todos');
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, c] = await Promise.all([propertiesAPI.list(), clientsAPI.list()]);
      setItems(p); setClients(c);
    } catch (err) { console.warn('Failed to load properties', err); toast({ title: 'Erro ao carregar dados', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const filtered = items.filter(p =>
    (tab === 'todos' || (p.type || '').toLowerCase() === tab) &&
    ((p.ref || '').toLowerCase().includes(query.toLowerCase()) || (p.address || '').toLowerCase().includes(query.toLowerCase()))
  );

  const save = async () => {
    if (!form.ref || !form.address) { toast({ title: 'Preencha referência e endereço', variant: 'destructive' }); return; }
    setSaving(true);
    try {
      if (editing) {
        const u = await propertiesAPI.update(editing, form);
        setItems(items.map(p => p.id === editing ? u : p));
        toast({ title: 'Imóvel atualizado' });
      } else {
        const c = await propertiesAPI.create(form);
        setItems([c, ...items]);
        toast({ title: 'Imóvel cadastrado' });
      }
      setOpen(false); setForm(empty); setEditing(null);
    } catch (e) { toast({ title: 'Erro ao salvar', description: e.response?.data?.detail || e.message, variant: 'destructive' }); }
    finally { setSaving(false); }
  };
  const edit = (p) => { setEditing(p.id); setForm({ ref: p.ref, client_id: p.client_id || '', type: p.type, subtype: p.subtype || '', address: p.address || '', city: p.city || '', area: p.area || 0, built_area: p.built_area || 0, value: p.value || 0, status: p.status }); setOpen(true); };
  const remove = async (id) => { if (!window.confirm('Remover?')) return; try { await propertiesAPI.remove(id); setItems(items.filter(p => p.id !== id)); toast({ title: 'Removido' }); } catch { toast({ title: 'Erro', variant: 'destructive' }); } };
  const clientName = (id) => clients.find(c => c.id === id)?.name || '—';

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div><h1 className="font-display text-3xl font-bold text-gray-900">Imóveis e Garantias</h1><p className="text-gray-600 mt-1">Urbanos, rurais, grãos, safra, bovinos e equipamentos.</p></div>
        <Button onClick={() => { setEditing(null); setForm(empty); setOpen(true); }} className="bg-emerald-900 hover:bg-emerald-800 text-white"><Plus className="w-4 h-4 mr-2" />Novo imóvel</Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-white border border-gray-200">
          <TabsTrigger value="todos">Todos</TabsTrigger>
          <TabsTrigger value="urbano">Urbanos</TabsTrigger>
          <TabsTrigger value="rural">Rurais</TabsTrigger>
          <TabsTrigger value="garantia">Garantias</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <Input value={query} onChange={(e) => setQuery(e.target.value)} className="pl-10 bg-white" placeholder="Buscar por referência ou endereço..." />
      </div>

      {loading ? (
        <div className="py-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-800" /></div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(p => {
            const Icon = typeIcon(p.type);
            return (
              <div key={p.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className={`w-10 h-10 rounded-lg ${typeColor(p.type)} flex items-center justify-center`}><Icon className="w-5 h-5" /></div>
                  <div className="flex gap-1">
                    <button onClick={() => edit(p)} className="p-1.5 hover:bg-emerald-50 rounded text-emerald-800"><Edit className="w-4 h-4" /></button>
                    <button onClick={() => remove(p.id)} className="p-1.5 hover:bg-red-50 rounded text-red-600"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
                <div className="text-xs font-semibold text-emerald-700 tracking-wider">{p.ref}</div>
                <div className="font-semibold text-gray-900 mt-1">{p.subtype || p.type}</div>
                <div className="text-xs text-gray-600 mt-1 line-clamp-2">{p.address}</div>
                <div className="text-xs text-gray-500 mt-1">{p.city}</div>
                <div className="grid grid-cols-2 gap-2 mt-4 pt-4 border-t border-gray-100">
                  <div><div className="text-[10px] text-gray-500 uppercase">Área</div><div className="text-sm font-semibold">{p.area} m²</div></div>
                  <div><div className="text-[10px] text-gray-500 uppercase">Valor</div><div className="text-sm font-semibold brand-green">R$ {Number(p.value || 0).toLocaleString('pt-BR')}</div></div>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(p.status)}`}>{p.status}</span>
                  <span className="text-xs text-gray-500 truncate max-w-[150px]">{clientName(p.client_id)}</span>
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && <div className="col-span-full text-center py-12 text-gray-400">Nenhum imóvel cadastrado</div>}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{editing ? 'Editar imóvel' : 'Novo imóvel / garantia'}</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-sm font-medium">Referência</label><Input value={form.ref} onChange={(e) => setForm({ ...form, ref: e.target.value })} placeholder="APT-001" /></div>
            <div><label className="text-sm font-medium">Cliente</label><Select value={form.client_id} onValueChange={(v) => setForm({ ...form, client_id: v })}><SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger><SelectContent>{clients.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="text-sm font-medium">Tipo</label><Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="Urbano">Urbano</SelectItem><SelectItem value="Rural">Rural</SelectItem><SelectItem value="Garantia">Garantia (grãos, safra, bovinos)</SelectItem></SelectContent></Select></div>
            <div><label className="text-sm font-medium">Subtipo</label><Input value={form.subtype} onChange={(e) => setForm({ ...form, subtype: e.target.value })} placeholder="Apartamento, Fazenda, Safra Soja..." /></div>
            <div className="col-span-2"><label className="text-sm font-medium">Endereço</label><Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
            <div><label className="text-sm font-medium">Cidade/UF</label><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
            <div><label className="text-sm font-medium">Status</label><Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="Rascunho">Rascunho</SelectItem><SelectItem value="Em andamento">Em andamento</SelectItem><SelectItem value="Concluído">Concluído</SelectItem></SelectContent></Select></div>
            <div><label className="text-sm font-medium">Área total</label><Input type="number" value={form.area} onChange={(e) => setForm({ ...form, area: Number(e.target.value) })} /></div>
            <div><label className="text-sm font-medium">Área construída</label><Input type="number" value={form.built_area} onChange={(e) => setForm({ ...form, built_area: Number(e.target.value) })} /></div>
            <div className="col-span-2"><label className="text-sm font-medium">Valor estimado (R$)</label><Input type="number" value={form.value} onChange={(e) => setForm({ ...form, value: Number(e.target.value) })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button><Button onClick={save} disabled={saving} className="bg-emerald-900 hover:bg-emerald-800 text-white">{saving ? 'Salvando...' : 'Salvar'}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Properties;
