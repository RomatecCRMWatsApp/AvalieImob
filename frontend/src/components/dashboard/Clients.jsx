import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Search, Edit, Trash2, Phone, Mail, MapPin, Loader2, DownloadCloud } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { useToast } from '../../hooks/use-toast';
import { clientsAPI } from '../../lib/api';

const empty = () => ({
  name: '', type: 'Pessoa Física', doc: '',
  rg: '', orgao_emissor: '', nacionalidade: 'Brasileiro(a)', estado_civil: '', profissao: '', data_nascimento: '',
  nome_fantasia: '', inscricao_estadual: '', inscricao_municipal: '', representante_legal: '', representante_cpf: '',
  phone: '', phone2: '', email: '',
  cep: '', endereco: '', numero: '', complemento: '', bairro: '', city: '', uf: '',
  observacoes: '',
});

const ESTADO_CIVIL = ['Solteiro(a)', 'Casado(a)', 'Divorciado(a)', 'Viúvo(a)', 'União Estável', 'Separado(a)'];

const Field = ({ label, value, onChange, type = 'text', placeholder = '', span = 1 }) => (
  <div className={span === 2 ? 'col-span-2' : ''}>
    <label className="text-xs font-semibold text-gray-600">{label}</label>
    <Input type={type} value={value ?? ''} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} className="mt-1" />
  </div>
);

const SectionTitle = ({ children }) => (
  <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 border-b border-emerald-100 pb-1 pt-1">{children}</div>
);

const Clients = () => {
  const { toast } = useToast();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty());
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setClients(await clientsAPI.list());
    } catch (err) {
      console.warn('Failed to load clients', err);
      toast({ title: 'Erro ao carregar clientes', variant: 'destructive' });
    } finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const isPJ = form.type === 'Pessoa Jurídica';

  const filtered = clients.filter(c =>
    (c.name || '').toLowerCase().includes(query.toLowerCase()) ||
    (c.doc || '').includes(query) ||
    (c.city || '').toLowerCase().includes(query.toLowerCase())
  );

  const save = async () => {
    if (!form.name) { toast({ title: 'Informe o nome/razão social', variant: 'destructive' }); return; }
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
      setOpen(false); setForm(empty()); setEditing(null);
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setSaving(false); }
  };

  const edit = (c) => { setEditing(c.id); setForm({ ...empty(), ...c }); setOpen(true); };
  const novo = () => { setEditing(null); setForm(empty()); setOpen(true); };

  const remove = async (id) => {
    if (!window.confirm('Remover este cliente?')) return;
    try { await clientsAPI.remove(id); setClients(clients.filter(c => c.id !== id)); toast({ title: 'Cliente removido' }); }
    catch { toast({ title: 'Erro ao remover', variant: 'destructive' }); }
  };

  const importar = async () => {
    setImporting(true);
    try {
      const res = await clientsAPI.importarPtam();
      toast({ title: `${res.importados} cliente(s) importado(s) dos laudos`, description: res.importados === 0 ? 'Nenhum novo cliente encontrado nos PTAMs.' : undefined });
      await load();
    } catch (e) {
      toast({ title: 'Erro ao importar', description: e.response?.data?.detail || e.message, variant: 'destructive' });
    } finally { setImporting(false); }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-[#B8860B] dark:text-amber-400">Clientes</h1>
          <p className="text-gray-600 mt-1">Gerencie sua base de clientes.</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={importar} disabled={importing} variant="outline" className="border-emerald-700 text-emerald-800 hover:bg-emerald-50">
            {importing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <DownloadCloud className="w-4 h-4 mr-2" />} Importar dos laudos
          </Button>
          <Button onClick={novo} className="bg-emerald-900 hover:bg-emerald-800 text-white">
            <Plus className="w-4 h-4 mr-2" /> Novo cliente
          </Button>
        </div>
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
                <tr className="border-b border-gray-200"><th className="text-left py-3 px-3">Cliente</th><th className="text-left py-3 px-3">Tipo</th><th className="text-left py-3 px-3">Contato</th><th className="text-left py-3 px-3">Cidade</th><th className="text-left py-3 px-3">Origem</th><th className="text-right py-3 px-3">Ações</th></tr>
              </thead>
              <tbody>
                {filtered.map(c => (
                  <tr key={c.id} className="border-b border-gray-100 hover:bg-emerald-50/30">
                    <td className="py-3 px-3"><div className="font-semibold text-gray-900">{c.name}</div><div className="text-xs text-gray-500">{c.doc || '—'}</div></td>
                    <td className="py-3 px-3"><span className="text-xs px-2 py-1 bg-emerald-50 text-emerald-800 rounded-full">{c.type}</span></td>
                    <td className="py-3 px-3"><div className="flex items-center gap-1.5 text-xs text-gray-600"><Phone className="w-3 h-3" />{c.phone || '—'}</div><div className="flex items-center gap-1.5 text-xs text-gray-600 mt-1"><Mail className="w-3 h-3" />{c.email || '—'}</div></td>
                    <td className="py-3 px-3"><div className="flex items-center gap-1 text-sm text-gray-700"><MapPin className="w-3 h-3 text-gray-400" />{c.city || '—'}{c.uf ? `/${c.uf}` : ''}</div></td>
                    <td className="py-3 px-3">
                      {c.origem === 'ptam'
                        ? <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">PTAM</span>
                        : <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">Manual</span>}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button onClick={() => edit(c)} className="p-2 hover:bg-emerald-50 rounded-lg text-emerald-800"><Edit className="w-4 h-4" /></button>
                      <button onClick={() => remove(c.id)} className="p-2 hover:bg-red-50 rounded-lg text-red-600"><Trash2 className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan={6} className="text-center py-10 text-gray-400">Nenhum cliente cadastrado</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? 'Editar cliente' : 'Novo cliente'}</DialogTitle></DialogHeader>

          <div className="space-y-4">
            <SectionTitle>Identificação</SectionTitle>
            <div className="grid grid-cols-2 gap-3">
              <Field label={isPJ ? 'Razão Social' : 'Nome Completo'} value={form.name} onChange={(v) => set('name', v)} span={2} />
              <div>
                <label className="text-xs font-semibold text-gray-600">Tipo</label>
                <Select value={form.type} onValueChange={(v) => set('type', v)}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Pessoa Física">Pessoa Física</SelectItem>
                    <SelectItem value="Pessoa Jurídica">Pessoa Jurídica</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Field label={isPJ ? 'CNPJ' : 'CPF'} value={form.doc} onChange={(v) => set('doc', v)} />
            </div>

            {!isPJ ? (
              <>
                <SectionTitle>Qualificação (Pessoa Física)</SectionTitle>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="RG" value={form.rg} onChange={(v) => set('rg', v)} />
                  <Field label="Órgão Emissor" value={form.orgao_emissor} onChange={(v) => set('orgao_emissor', v)} placeholder="SSP/MA" />
                  <Field label="Nacionalidade" value={form.nacionalidade} onChange={(v) => set('nacionalidade', v)} />
                  <div>
                    <label className="text-xs font-semibold text-gray-600">Estado Civil</label>
                    <Select value={form.estado_civil || undefined} onValueChange={(v) => set('estado_civil', v)}>
                      <SelectTrigger className="mt-1"><SelectValue placeholder="—" /></SelectTrigger>
                      <SelectContent>{ESTADO_CIVIL.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <Field label="Profissão" value={form.profissao} onChange={(v) => set('profissao', v)} />
                  <Field label="Data de Nascimento" type="date" value={form.data_nascimento} onChange={(v) => set('data_nascimento', v)} />
                </div>
              </>
            ) : (
              <>
                <SectionTitle>Dados da Empresa (Pessoa Jurídica)</SectionTitle>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Nome Fantasia" value={form.nome_fantasia} onChange={(v) => set('nome_fantasia', v)} span={2} />
                  <Field label="Inscrição Estadual" value={form.inscricao_estadual} onChange={(v) => set('inscricao_estadual', v)} />
                  <Field label="Inscrição Municipal" value={form.inscricao_municipal} onChange={(v) => set('inscricao_municipal', v)} />
                  <Field label="Representante Legal" value={form.representante_legal} onChange={(v) => set('representante_legal', v)} />
                  <Field label="CPF do Representante" value={form.representante_cpf} onChange={(v) => set('representante_cpf', v)} />
                </div>
              </>
            )}

            <SectionTitle>Contato</SectionTitle>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Telefone" value={form.phone} onChange={(v) => set('phone', v)} placeholder="(99) 99999-9999" />
              <Field label="Telefone 2" value={form.phone2} onChange={(v) => set('phone2', v)} />
              <Field label="E-mail" type="email" value={form.email} onChange={(v) => set('email', v)} span={2} />
            </div>

            <SectionTitle>Endereço</SectionTitle>
            <div className="grid grid-cols-6 gap-3">
              <div className="col-span-2"><Field label="CEP" value={form.cep} onChange={(v) => set('cep', v)} /></div>
              <div className="col-span-4"><Field label="Logradouro" value={form.endereco} onChange={(v) => set('endereco', v)} /></div>
              <div className="col-span-1"><Field label="Nº" value={form.numero} onChange={(v) => set('numero', v)} /></div>
              <div className="col-span-2"><Field label="Complemento" value={form.complemento} onChange={(v) => set('complemento', v)} /></div>
              <div className="col-span-3"><Field label="Bairro" value={form.bairro} onChange={(v) => set('bairro', v)} /></div>
              <div className="col-span-4"><Field label="Cidade" value={form.city} onChange={(v) => set('city', v)} /></div>
              <div className="col-span-2"><Field label="UF" value={form.uf} onChange={(v) => set('uf', v)} /></div>
            </div>

            <SectionTitle>Observações</SectionTitle>
            <textarea value={form.observacoes} onChange={(e) => set('observacoes', e.target.value)} rows={2}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600" />
          </div>

          <DialogFooter className="mt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} disabled={saving} className="bg-emerald-900 hover:bg-emerald-800 text-white">{saving ? 'Salvando...' : 'Salvar'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Clients;
