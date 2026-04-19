import React from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';

const PropertyFormDialog = ({ open, onOpenChange, form, setForm, onSave, saving, editing, clients }) => {
  const update = (field) => (e) => {
    const value = e.target ? e.target.value : e;
    setForm({ ...form, [field]: value });
  };
  const updateNumber = (field) => (e) => setForm({ ...form, [field]: Number(e.target.value) });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editing ? 'Editar imóvel' : 'Novo imóvel / garantia'}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium">Referência</label>
            <Input value={form.ref} onChange={update('ref')} placeholder="APT-001" />
          </div>
          <div>
            <label className="text-sm font-medium">Cliente</label>
            <Select value={form.client_id} onValueChange={(v) => setForm({ ...form, client_id: v })}>
              <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
              <SelectContent>
                {clients.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm font-medium">Tipo</label>
            <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Urbano">Urbano</SelectItem>
                <SelectItem value="Rural">Rural</SelectItem>
                <SelectItem value="Garantia">Garantia (grãos, safra, bovinos)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm font-medium">Subtipo</label>
            <Input value={form.subtype} onChange={update('subtype')} placeholder="Apartamento, Fazenda, Safra Soja..." />
          </div>
          <div className="col-span-2">
            <label className="text-sm font-medium">Endereço</label>
            <Input value={form.address} onChange={update('address')} />
          </div>
          <div>
            <label className="text-sm font-medium">Cidade/UF</label>
            <Input value={form.city} onChange={update('city')} />
          </div>
          <div>
            <label className="text-sm font-medium">Status</label>
            <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Rascunho">Rascunho</SelectItem>
                <SelectItem value="Em andamento">Em andamento</SelectItem>
                <SelectItem value="Concluído">Concluído</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm font-medium">Área total</label>
            <Input type="number" value={form.area} onChange={updateNumber('area')} />
          </div>
          <div>
            <label className="text-sm font-medium">Área construída</label>
            <Input type="number" value={form.built_area} onChange={updateNumber('built_area')} />
          </div>
          <div className="col-span-2">
            <label className="text-sm font-medium">Valor estimado (R$)</label>
            <Input type="number" value={form.value} onChange={updateNumber('value')} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={onSave} disabled={saving} className="bg-emerald-900 hover:bg-emerald-800 text-white">
            {saving ? 'Salvando...' : 'Salvar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default PropertyFormDialog;
