import React, { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, Plus, RotateCcw, Loader2, X } from 'lucide-react';
import { cndAPI } from '../../../../lib/api';
import { useConsulta } from '../../cnd/hooks/useCND';

const PROVIDER_LABELS = {
  receita: 'Receita Federal',
  pgfn: 'PGFN - Dívida Ativa',
  tst: 'TST - Trabalhista',
  trf1: 'TRF1 - Justiça Federal',
  tjma: 'TJMA - Justiça Estadual',
  cnib: 'CNIB - Indisponibilidade',
  rfb_cadastro: 'Situação Cadastral',
};

const TIPOS = ['Vendedor', 'Comprador', 'Proprietário', 'Empresa'];

function maskDoc(v) {
  const d = v.replace(/\D/g, '').slice(0, 14);
  if (d.length <= 11) return d.replace(/(\d{3})(\d{3})(\d{3})(\d{0,2})/, (_, a, b, c, e) => [a, b, c].filter(Boolean).join('.') + (e ? '-' + e : ''));
  return d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2})/, (_, a, b, c, dd, e) => `${a}.${b}.${c}/${dd}${e ? '-' + e : ''}`);
}

function ResumoBadges({ consulta }) {
  const { consulta: data } = useConsulta(consulta.id);
  const certs = data?.certidoes || [];
  const n = certs.filter(c => c.resultado === 'negativa' || c.status === 'negativa').length;
  const p = certs.filter(c => c.resultado === 'positiva' || c.status === 'positiva').length;
  const i = certs.filter(c => c.resultado === 'indisponivel' || c.status === 'indisponivel').length;

  if (!certs.length) return <span className="text-xs text-gray-400">Processando...</span>;

  return (
    <div className="flex flex-wrap gap-1 mt-1">
      <span className="px-2 py-0.5 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-700 font-medium">{n} Negativa{n !== 1 ? 's' : ''}</span>
      {p > 0 && <span className="px-2 py-0.5 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-700 font-medium">{p} Positiva{p !== 1 ? 's' : ''}</span>}
      {i > 0 && <span className="px-2 py-0.5 bg-gray-100 border border-gray-200 rounded text-xs text-gray-500 font-medium">{i} Indisp.</span>}
    </div>
  );
}

function NovaConsultaModal({ ptamId, onSuccess, onClose }) {
  const [form, setForm] = useState({ cpf_cnpj: '', nome_parte: '', tipo_parte: 'Vendedor', data_nascimento: '', finalidade: '' });
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState('');
  const isCPF = form.cpf_cnpj.replace(/\D/g, '').length <= 11;

  const set = (e) => {
    const { name, value } = e.target;
    setForm(p => ({ ...p, [name]: name === 'cpf_cnpj' ? maskDoc(value) : value }));
  };

  const submit = async (e) => {
    e.preventDefault(); setErr('');
    const raw = form.cpf_cnpj.replace(/\D/g, '');
    if (raw.length !== 11 && raw.length !== 14) { setErr('CPF ou CNPJ inválido.'); return; }
    if (!form.finalidade.trim()) { setErr('Informe a finalidade.'); return; }
    setSubmitting(true);
    try {
      const body = { ...form, cpf_cnpj: raw, ptam_id: ptamId };
      if (!isCPF) delete body.data_nascimento;
      const res = await cndAPI.consultar(body);
      onSuccess(res.consulta_id);
    } catch (ex) {
      setErr(ex?.response?.data?.detail || 'Erro ao iniciar consulta.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
        <h3 className="font-bold text-gray-900 mb-4">Nova Consulta CND</h3>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">CPF ou CNPJ *</label>
            <input name="cpf_cnpj" value={form.cpf_cnpj} onChange={set} placeholder="000.000.000-00" required
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 font-mono" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Nome completo *</label>
              <input name="nome_parte" value={form.nome_parte} onChange={set} placeholder="Nome da parte" required
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Tipo *</label>
              <select name="tipo_parte" value={form.tipo_parte} onChange={set}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 bg-white">
                {TIPOS.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
          </div>
          {isCPF && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Data de nascimento</label>
              <input type="date" name="data_nascimento" value={form.data_nascimento} onChange={set}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400" />
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Finalidade *</label>
            <textarea name="finalidade" value={form.finalidade} onChange={set} rows={2} required
              placeholder="Ex: Avaliação de garantia para financiamento"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 resize-none" />
          </div>
          {err && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{err}</p>}
          <button type="submit" disabled={submitting}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-900 text-white font-semibold text-sm hover:bg-emerald-800 disabled:opacity-60">
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
            {submitting ? 'Aguarde...' : 'Consultar Certidões'}
          </button>
        </form>
      </div>
    </div>
  );
}

export function StepCertidoes({ form }) {
  const ptamId = form.id || null;
  const [consultas, setConsultas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const load = useCallback(async () => {
    if (!ptamId) return;
    setLoading(true);
    try {
      const data = await cndAPI.getConsultasPtam(ptamId);
      setConsultas(data || []);
    } catch { /* silencioso */ } finally { setLoading(false); }
  }, [ptamId]);

  useEffect(() => { load(); }, [load]);

  const handleSuccess = () => { setShowModal(false); load(); };

  if (!ptamId) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-emerald-900 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Certidões das Partes (CND)</h3>
            <p className="text-sm text-gray-500">Salve o PTAM primeiro para consultar certidões.</p>
          </div>
        </div>
        <p className="text-sm text-gray-400 bg-gray-50 rounded-xl px-4 py-3">
          Salve o PTAM como rascunho antes de consultar certidões CND das partes.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {showModal && <NovaConsultaModal ptamId={ptamId} onSuccess={handleSuccess} onClose={() => setShowModal(false)} />}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-900 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Certidões das Partes (CND)</h3>
            <p className="text-sm text-gray-500">Receita Federal, PGFN, TST, TRF1, TJMA e mais</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-600 hover:bg-gray-50">
            <RotateCcw className="w-3.5 h-3.5" />Atualizar
          </button>
          <button onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-900 text-white text-sm font-semibold hover:bg-emerald-800">
            <Plus className="w-4 h-4" />Consultar CND das Partes
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-emerald-700" /></div>
      ) : consultas.length === 0 ? (
        <div className="bg-gray-50 rounded-xl border border-dashed border-gray-200 px-6 py-8 text-center">
          <ShieldCheck className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Nenhuma consulta CND vinculada a este PTAM.</p>
          <p className="text-xs text-gray-400 mt-1">Clique em "Consultar CND das Partes" para iniciar.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {consultas.map(c => (
            <div key={c.id} className="bg-white rounded-xl border border-gray-200 px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-gray-800 text-sm">{c.nome_parte}</p>
                  <p className="text-xs text-gray-500 font-mono">{c.cpf_cnpj} — {c.tipo_parte}</p>
                  <ResumoBadges consulta={c} />
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  c.status === 'concluido' ? 'bg-emerald-100 text-emerald-700' :
                  c.status === 'processando' ? 'bg-blue-100 text-blue-700' :
                  c.status === 'erro' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-500'
                }`}>{c.status}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
