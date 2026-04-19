import React, { useState, useEffect } from 'react';
import { TrendingUp, Plus, Loader2, Trash2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { useToast } from '../../hooks/use-toast';
import { samplesAPI } from '../../lib/api';

const empty = { ref: '', type: 'Apartamento', area: 0, value: 0, source: '', neighborhood: '', date: new Date().toISOString().split('T')[0] };

const Samples = () => {
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);

  const load = async () => {
    setLoading(true);
    try { setItems(await samplesAPI.list()); }
    catch { toast({ title: 'Erro ao carregar', variant: 'destructive' }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const avg = items.length ? items.reduce((a, b) => a + (b.price_per_sqm || 0), 0) / items.length : 0;
  const min = items.length ? Math.min(...items.map(s => s.price_per_sqm || 0)) : 0;
  const max = items.length ? Math.max(...items.map(s => s.price_per_sqm || 0)) : 0;

  const save = async () => {
    if (!form.ref || !form.value || !form.area) { toast({ title: 'Preencha os campos', variant: 'destructive' }); return; }
    try {
      const s = await samplesAPI.create(form);
      setItems([s, ...items]);
      toast({ title: 'Amostra adicionada' });
      setOpen(false); setForm(empty);
    } catch (e) { toast({ title: 'Erro', description: e.response?.data?.detail, variant: 'destructive' }); }
  };
  const remove = async (id) => { try { await samplesAPI.remove(id); setItems(items.filter(s => s.id !== id)); toast({ title: 'Removida' }); } catch { toast({ title: 'Erro', variant: 'destructive' }); } };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div><h1 className="font-display text-3xl font-bold text-gray-900">Amostras de Mercado</h1><p className="text-gray-600 mt-1">Elementos comparativos para o Método Comparativo Direto.</p></div>
        <Button onClick={() => setOpen(true)} className="bg-emerald-900 hover:bg-emerald-800 text-white"><Plus className="w-4 h-4 mr-2" />Nova amostra</Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200"><div className="flex items-center gap-2 text-xs text-gray-500 mb-1"><TrendingUp className="w-3.5 h-3.5" />PREÇO MÉDIO</div><div className="font-display text-2xl font-bold brand-green">R$ {avg.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}/m²</div></div>
        <div className="bg-white p-5 rounded-xl border border-gray-200"><div className="text-xs text-gray-500 mb-1">MÍNIMO</div><div className="font-display text-2xl font-bold text-gray-900">R$ {min.toLocaleString('pt-BR')}/m²</div></div>
        <div className="bg-white p-5 rounded-xl border border-gray-200"><div className="text-xs text-gray-500 mb-1">MÁXIMO</div><div className="font-display text-2xl font-bold text-gray-900">R$ {max.toLocaleString('pt-BR')}/m²</div></div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="py-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-800" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500"><tr><th className="text-left py-3 px-4">Ref</th><th className="text-left py-3 px-4">Tipo</th><th className="text-left py-3 px-4">Bairro</th><th className="text-right py-3 px-4">Área</th><th className="text-right py-3 px-4">Valor</th><th className="text-right py-3 px-4">R$/m²</th><th className="text-left py-3 px-4">Fonte</th><th /></tr></thead>
            <tbody>
              {items.map(s => (
                <tr key={s.id} className="border-t border-gray-100 hover:bg-emerald-50/30">
                  <td className="py-3 px-4 font-semibold text-emerald-800">{s.ref}</td>
                  <td className="py-3 px-4">{s.type}</td>
                  <td className="py-3 px-4">{s.neighborhood}</td>
                  <td className="py-3 px-4 text-right">{s.area} m²</td>
                  <td className="py-3 px-4 text-right">R$ {Number(s.value).toLocaleString('pt-BR')}</td>
                  <td className="py-3 px-4 text-right font-semibold">R$ {Number(s.price_per_sqm).toLocaleString('pt-BR')}</td>
                  <td className="py-3 px-4 text-xs text-gray-500">{s.source}</td>
                  <td className="py-3 px-2"><button onClick={() => remove(s.id)} className="p-1.5 hover:bg-red-50 rounded text-red-600"><Trash2 className="w-4 h-4" /></button></td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan={8} className="text-center py-10 text-gray-400">Nenhuma amostra cadastrada</td></tr>}
            </tbody>
          </table>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nova amostra de mercado</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-sm font-medium">Referência</label><Input value={form.ref} onChange={(e) => setForm({ ...form, ref: e.target.value })} placeholder="AM-006" /></div>
            <div><label className="text-sm font-medium">Tipo</label><Input value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} /></div>
            <div><label className="text-sm font-medium">Bairro</label><Input value={form.neighborhood} onChange={(e) => setForm({ ...form, neighborhood: e.target.value })} /></div>
            <div><label className="text-sm font-medium">Fonte</label><Input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} /></div>
            <div><label className="text-sm font-medium">Área (m²)</label><Input type="number" value={form.area} onChange={(e) => setForm({ ...form, area: Number(e.target.value) })} /></div>
            <div><label className="text-sm font-medium">Valor (R$)</label><Input type="number" value={form.value} onChange={(e) => setForm({ ...form, value: Number(e.target.value) })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button><Button onClick={save} className="bg-emerald-900 hover:bg-emerald-800 text-white">Adicionar</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Samples;
