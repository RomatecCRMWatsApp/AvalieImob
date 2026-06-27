// @module documentos-externos/ModalSignatarios — cadastro de N signatários (papel livre c/
// sugestões) + quick-add a partir do cadastro de Clientes.
import React, { useState, useEffect, useCallback } from 'react';
import { X, Plus, Trash2, UserPlus, Check } from 'lucide-react';
import { documentosExternosAPI, clientsAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

const PAPEIS = ['Vendedor', 'Compradora', 'Comprador', 'Cônjuge anuente do vendedor',
  'Cônjuge anuente do comprador', 'Representante legal', 'Procurador', 'Testemunha 1',
  'Testemunha 2', 'Avalista', 'Fiador', 'Anuente'];

const soDig = (v) => String(v || '').replace(/\D/g, '');

export default function ModalSignatarios({ doc, onClose, onChanged }) {
  const { toast } = useToast();
  const [sigs, setSigs] = useState(doc.signatarios || []);
  const [clientes, setClientes] = useState([]);
  const [form, setForm] = useState({ nome: '', cpf_cnpj: '', papel: '', whatsapp: '', email: '' });
  const [busy, setBusy] = useState(false);
  const [salvarNoCadastro, setSalvarNoCadastro] = useState(true);
  const [foneEdit, setFoneEdit] = useState({}); // sid -> WhatsApp editável

  const recarregar = useCallback(async () => {
    try { const d = await documentosExternosAPI.obter(doc.id); setSigs(d.signatarios || []); onChanged && onChanged(d); }
    catch { /* noop */ }
  }, [doc.id, onChanged]);

  useEffect(() => { clientsAPI.list().then((d) => setClientes(Array.isArray(d) ? d : [])).catch(() => {}); }, []);

  const selecionarCliente = (cid) => {
    const c = clientes.find((x) => String(x.id) === String(cid));
    if (!c) return;
    setForm((f) => ({ ...f, nome: c.name || c.nome || '', cpf_cnpj: soDig(c.doc || c.cpf_cnpj || ''),
      whatsapp: soDig(c.phone || c.telefone || c.whatsapp || ''), email: c.email || '' }));
  };

  const adicionar = async () => {
    if (!form.nome.trim()) { toast({ title: 'Informe o nome', variant: 'destructive' }); return; }
    setBusy(true);
    try {
      await documentosExternosAPI.addSignatario(doc.id, {
        nome: form.nome.trim(), cpf_cnpj: soDig(form.cpf_cnpj),
        papel: form.papel.trim() || 'Signatário', whatsapp: soDig(form.whatsapp), email: form.email.trim() || null });
      // cadastra também no cadastro de Clientes (reutilizável no dropdown), sem bloquear o signatário
      if (salvarNoCadastro && form.nome.trim()) {
        try {
          await clientsAPI.create({ name: form.nome.trim(), doc: soDig(form.cpf_cnpj),
            phone: soDig(form.whatsapp), email: form.email.trim() || '' });
          clientsAPI.list().then((d) => setClientes(Array.isArray(d) ? d : [])).catch(() => {});
        } catch { /* duplicado/erro de cadastro não impede o signatário */ }
      }
      setForm({ nome: '', cpf_cnpj: '', papel: '', whatsapp: '', email: '' });
      await recarregar();
    } catch (e) {
      toast({ title: 'Erro ao adicionar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const salvarFone = async (s) => {
    try {
      await documentosExternosAPI.editSignatario(doc.id, s.id, { whatsapp: soDig(foneEdit[s.id]) });
      setFoneEdit((f) => { const n = { ...f }; delete n[s.id]; return n; });
      await recarregar();
      toast({ title: 'Número de envio atualizado' });
    } catch (e) {
      toast({ title: 'Erro ao salvar número', description: e?.response?.data?.detail || '', variant: 'destructive' });
    }
  };

  const remover = async (sid) => {
    try { await documentosExternosAPI.delSignatario(doc.id, sid); await recarregar(); }
    catch (e) { toast({ title: 'Erro ao remover', description: e?.response?.data?.detail || '', variant: 'destructive' }); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold text-emerald-950">Signatários · {doc.codigo}</h3>
          <button onClick={onClose}><X /></button>
        </div>

        {/* Lista atual */}
        <div className="space-y-2 mb-5">
          {sigs.length === 0 && <p className="text-sm text-gray-500">Nenhum signatário ainda.</p>}
          {sigs.map((s) => {
            const editando = foneEdit[s.id] !== undefined;
            const valor = editando ? foneEdit[s.id] : (s.whatsapp || '');
            const mudou = editando && soDig(foneEdit[s.id]) !== soDig(s.whatsapp);
            return (
              <div key={s.id} className="border rounded-lg px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-semibold text-gray-900 truncate">{s.nome}
                    <span className="ml-2 text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">{s.papel}</span>
                  </div>
                  {s.status !== 'assinado' && (
                    <button onClick={() => remover(s.id)} className="text-red-500 p-1"><Trash2 className="w-4 h-4" /></button>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-[11px] text-gray-400 shrink-0">Nº de envio:</span>
                  <input className="flex-1 border rounded-lg px-2 py-1 text-[13px] disabled:bg-gray-50"
                         placeholder="55 DDD número" value={valor} disabled={s.status === 'assinado'}
                         onChange={(e) => setFoneEdit((f) => ({ ...f, [s.id]: e.target.value }))} />
                  {mudou && (
                    <button onClick={() => salvarFone(s)}
                            className="flex items-center gap-1 text-emerald-700 text-xs border border-emerald-300 rounded-lg px-2 py-1 hover:bg-emerald-50">
                      <Check className="w-3.5 h-3.5" /> Salvar
                    </button>
                  )}
                </div>
                <div className="text-[11px] text-gray-400 mt-1">{s.cpf_cnpj || '—'} · {s.status}</div>
              </div>
            );
          })}
        </div>

        {/* Quick-add de cliente */}
        <div className="flex items-center gap-2 mb-3">
          <UserPlus className="w-4 h-4 text-emerald-700" />
          <select className="border rounded-lg p-2 text-sm flex-1" defaultValue=""
                  onChange={(e) => { selecionarCliente(e.target.value); e.target.value = ''; }}>
            <option value="" disabled>Adicionar do cadastro de clientes…</option>
            {clientes.map((c) => <option key={c.id} value={c.id}>{c.name || c.nome}</option>)}
          </select>
        </div>

        {/* Form de novo signatário */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
          <input className="border rounded-lg p-2 text-sm" placeholder="Nome completo"
                 value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
          <input className="border rounded-lg p-2 text-sm" placeholder="CPF/CNPJ"
                 value={form.cpf_cnpj} onChange={(e) => setForm({ ...form, cpf_cnpj: e.target.value })} />
          <input className="border rounded-lg p-2 text-sm" placeholder="Papel (ex.: Vendedor)" list="papeis-doc-ext"
                 value={form.papel} onChange={(e) => setForm({ ...form, papel: e.target.value })} />
          <datalist id="papeis-doc-ext">{PAPEIS.map((p) => <option key={p} value={p} />)}</datalist>
          <input className="border rounded-lg p-2 text-sm" placeholder="WhatsApp (55DDDNUMERO)"
                 value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} />
          <input className="border rounded-lg p-2 text-sm sm:col-span-2" placeholder="E-mail (opcional)"
                 value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <label className="flex items-center gap-2 text-[12px] text-gray-600 mb-3">
          <input type="checkbox" checked={salvarNoCadastro} onChange={(e) => setSalvarNoCadastro(e.target.checked)} />
          Cadastrar também no meu cadastro de Clientes (reutilizar depois)
        </label>
        <div className="flex justify-between">
          <button onClick={adicionar} disabled={busy}
                  className="flex items-center gap-1.5 px-4 py-2 bg-emerald-700 text-white rounded-lg text-sm disabled:opacity-50">
            <Plus className="w-4 h-4" /> Adicionar signatário
          </button>
          <button onClick={onClose} className="px-4 py-2 border rounded-lg text-sm">Concluir</button>
        </div>
      </div>
    </div>
  );
}
