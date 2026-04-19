import React, { useState, useEffect } from 'react';
import { Plus, Search, Edit, Trash2, Phone, Mail, MapPin, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { useToast } from '../../hooks/use-toast';
import { clientsAPI } from '../../lib/api';

const empty = { name: '', type: 'Pessoa Física', doc: '', phone: '', email: '', city: '' };

const Clients = () => {
  const { toast } = useToast();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await clientsAPI.list();
      setClients(data);
    } catch {
      toast({ title: 'Erro ao carregar clientes', variant: 'destructive' });
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const filtered = clients.filter(c =>
    (c.name || '').toLowerCase().includes(query.toLowerCase()) ||
    (c.doc || '').includes(query) ||
    (c.city || '').toLowerCase().includes(query.toLowerCase())
  );

  const save = async () => {
    if (!form.name || !form.doc) { toast({ title: 'Preencha nome e documento', variant: 'destructive' }); return; }
    setSaving(true);
    try {
      if (editing) {
        const updated = await clientsAPI.update(editing, form);
        setClients(clients.map(c => c.id === editing ? updated : c));
        toast({ title: 'Cliente atualizado' });
      } else {
        const created = await clientsAPI.create(form);
        setClients([created, ...clients]);
        toast({ title: 'Cliente cadastrado' });
      }
      setOpen(false); setForm(empty); setEditing(null);
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setSaving(false); }
  };

  const edit = (c) => { setEditing(c.id); setForm({ name: c.name, type: c.type, doc: c.doc, phone: c.phone || '', email: c.email || '', city: c.city || '' }); setOpen(true); };
  const remove = async (id) => {
    if (!window.confirm('Remover este cliente?')) return;
    try { await clientsAPI.remove(id); setClients(clients.filter(c => c.id !== id)); toast({ title: 'Cliente removido' }); }
    catch { toast({ title: 'Erro ao remover', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-gray-900">Clientes</h1>
          <p className="text-gray-600 mt-1">Gerencie sua base de clientes.</p>
        </div>
        <Button onClick={() => { setEditing(null); setForm(empty); setOpen(true); }} className="bg-emerald-900 hover:bg-emerald-800 text-white">
          <Plus className="w-4 h-4 mr-2" /> Novo cliente
        </Button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input value={query} onChange={(e) => setQuery(e.target.value)} className="pl-10" placeholder="Buscar por nome, CPF/CNPJ ou cidade..." />
        </div>

        {loading ? (
          <div className="py-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-800" /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500 uppercase tracking-wider">
                <tr className="border-b border-gray-200"><th className="text-left py-3 px-3">Cliente</th><th className="text-left py-3 px-3">Tipo</th><th className="text-left py-3 px-3">Contato</th><th className="text-left py-3 px-3">Cidade</th><th className="text-right py-3 px-3">Ações</th></tr>
              </thead>
              <tbody>
                {filtered.map(c => (
                  <tr key={c.id} className="border-b border-gray-100 hover:bg-emerald-50/30">
                    <td className="py-3 px-3"><div className="font-semibold text-gray-900">{c.name}</div><div className="text-xs text-gray-500">{c.doc}</div></td>
                    <td className="py-3 px-3"><span className="text-xs px-2 py-1 bg-emerald-50 text-emerald-800 rounded-full">{c.type}</span></td>
                    <td className="py-3 px-3"><div className="flex items-center gap-1.5 text-xs text-gray-600"><Phone className="w-3 h-3" />{c.phone || '—'}</div><div className="flex items-center gap-1.5 text-xs text-gray-600 mt-1"><Mail className="w-3 h-3" />{c.email || '—'}</div></td>
                    <td className="py-3 px-3"><div className="flex items-center gap-1 text-sm text-gray-700"><MapPin className="w-3 h-3 text-gray-400" />{c.city || '—'}</div></td>
                    <td className="py-3 px-3 text-right">
                      <button onClick={() => edit(c)} className="p-2 hover:bg-emerald-50 rounded-lg text-emerald-800"><Edit className="w-4 h-4" /></button>
                      <button onClick={() => remove(c.id)} className="p-2 hover:bg-red-50 rounded-lg text-red-600"><Trash2 className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan={5} className="text-center py-10 text-gray-400">Nenhum cliente cadastrado</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editing ? 'Editar cliente' : 'Novo cliente'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><label className="text-sm font-medium">Nome/Razão social</label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-sm font-medium">Tipo</label><Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="Pessoa Física">Pessoa Física</SelectItem><SelectItem value="Pessoa Jurídica">Pessoa Jurídica</SelectItem></SelectContent></Select></div>
              <div><label className="text-sm font-medium">CPF/CNPJ</label><Input value={form.doc} onChange={(e) => setForm({ ...form, doc: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-sm font-medium">Telefone</label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
              <div><label className="text-sm font-medium">E-mail</label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
            </div>
            <div><label className="text-sm font-medium">Cidade/UF</label><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button><Button onClick={save} disabled={saving} className="bg-emerald-900 hover:bg-emerald-800 text-white">{saving ? 'Salvando...' : 'Salvar'}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Clients;
