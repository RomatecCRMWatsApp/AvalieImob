import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Search, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';
import { useToast } from '../../hooks/use-toast';
import { propertiesAPI, clientsAPI } from '../../lib/api';
import PropertyCard from './PropertyCard';
import PropertyFormDialog from './PropertyFormDialog';

const empty = {
  ref: '', client_id: '', type: 'Urbano', subtype: '', address: '', city: '',
  area: 0, built_area: 0, value: 0, status: 'Rascunho',
};

const toFormState = (p) => ({
  ref: p.ref, client_id: p.client_id || '', type: p.type, subtype: p.subtype || '',
  address: p.address || '', city: p.city || '',
  area: p.area || 0, built_area: p.built_area || 0, value: p.value || 0, status: p.status,
});

const filterProperties = (items, tab, query) => {
  const q = query.toLowerCase();
  return items.filter((p) => {
    const matchesTab = tab === 'todos' || (p.type || '').toLowerCase() === tab;
    const matchesQuery = (p.ref || '').toLowerCase().includes(q) || (p.address || '').toLowerCase().includes(q);
    return matchesTab && matchesQuery;
  });
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
      setItems(p);
      setClients(c);
    } catch (err) {
      console.warn('Failed to load properties', err);
      toast({ title: 'Erro ao carregar dados', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm(empty);
    setOpen(true);
  };

  const openEdit = (p) => {
    setEditing(p.id);
    setForm(toFormState(p));
    setOpen(true);
  };

  const save = async () => {
    if (!form.ref || !form.address) {
      toast({ title: 'Preencha referência e endereço', variant: 'destructive' });
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        const u = await propertiesAPI.update(editing, form);
        setItems(items.map((p) => (p.id === editing ? u : p)));
        toast({ title: 'Imóvel atualizado' });
      } else {
        const c = await propertiesAPI.create(form);
        setItems([c, ...items]);
        toast({ title: 'Imóvel cadastrado' });
      }
      setOpen(false);
      setForm(empty);
      setEditing(null);
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Remover este imóvel?')) return;
    try {
      await propertiesAPI.remove(id);
      setItems(items.filter((p) => p.id !== id));
      toast({ title: 'Removido' });
    } catch {
      toast({ title: 'Erro ao remover', variant: 'destructive' });
    }
  };

  const clientName = (id) => clients.find((c) => c.id === id)?.name || '—';
  const filtered = filterProperties(items, tab, query);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-gray-900">Imóveis e Garantias</h1>
          <p className="text-gray-600 mt-1">Urbanos, rurais, grãos, safra, bovinos e equipamentos.</p>
        </div>
        <Button onClick={openCreate} className="bg-emerald-900 hover:bg-emerald-800 text-white">
          <Plus className="w-4 h-4 mr-2" />Novo imóvel
        </Button>
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
        <div className="py-16 flex justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-800" />
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((p) => (
            <PropertyCard
              key={p.id}
              property={p}
              clientName={clientName(p.client_id)}
              onEdit={() => openEdit(p)}
              onRemove={() => remove(p.id)}
            />
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full text-center py-12 text-gray-400">Nenhum imóvel cadastrado</div>
          )}
        </div>
      )}

      <PropertyFormDialog
        open={open}
        onOpenChange={setOpen}
        form={form}
        setForm={setForm}
        onSave={save}
        saving={saving}
        editing={editing}
        clients={clients}
      />
    </div>
  );
};

export default Properties;
