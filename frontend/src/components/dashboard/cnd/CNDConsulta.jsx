import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileSearch, RotateCcw, Download } from 'lucide-react';
import { cndAPI } from '../../../lib/api';
import { useConsulta } from './hooks/useCND';
import CNDResultCard from './CNDResultCard';

const TIPOS = ['Vendedor', 'Comprador', 'Proprietário', 'Empresa'];

function maskDoc(v) {
  const d = v.replace(/\D/g, '').slice(0, 14);
  if (d.length <= 11) return d.replace(/(\d{3})(\d{3})(\d{3})(\d{0,2})/, (_, a, b, c, e) => [a, b, c].filter(Boolean).join('.') + (e ? '-' + e : ''));
  return d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2})/, (_, a, b, c, dd, e) => `${a}.${b}.${c}/${dd}${e ? '-' + e : ''}`);
}

function Resumo({ certs }) {
  const n = certs.filter(c => c.status === 'negativa').length;
  const p = certs.filter(c => c.status === 'positiva').length;
  const i = certs.filter(c => c.status === 'indisponivel').length;
  return (
    <div className="flex flex-wrap gap-2">
      <span className="px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700 font-semibold">{n} Negativa{n !== 1 ? 's' : ''}</span>
      {p > 0 && <span className="px-3 py-1.5 bg-yellow-50 border border-yellow-200 rounded-xl text-sm text-yellow-700 font-semibold">{p} Positiva{p !== 1 ? 's' : ''}</span>}
      {i > 0 && <span className="px-3 py-1.5 bg-gray-100 border border-gray-200 rounded-xl text-sm text-gray-500 font-semibold">{i} Indisponível{i !== 1 ? 'is' : ''}</span>}
    </div>
  );
}

function Input({ label, ...props }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <input {...props} className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 transition-colors" />
    </div>
  );
}

export default function CNDConsulta() {
  const [params] = useSearchParams();
  const preId = params.get('id');
  const [step, setStep] = useState(preId ? 2 : 1);
  const [consultaId, setConsultaId] = useState(preId || null);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState('');
  const [form, setForm] = useState({ cpf_cnpj: '', nome_parte: '', tipo_parte: 'Vendedor', data_nascimento: '', finalidade: '' });
  const { consulta } = useConsulta(consultaId);
  const isCPF = form.cpf_cnpj.replace(/\D/g, '').length <= 11;

  useEffect(() => { if (consulta && consulta.status !== 'processando') setStep(3); }, [consulta]);

  const set = (e) => { const { name, value } = e.target; setForm(p => ({ ...p, [name]: name === 'cpf_cnpj' ? maskDoc(value) : value })); };

  const submit = async (e) => {
    e.preventDefault(); setErr('');
    const raw = form.cpf_cnpj.replace(/\D/g, '');
    if (raw.length !== 11 && raw.length !== 14) { setErr('CPF ou CNPJ inválido.'); return; }
    if (!form.finalidade.trim()) { setErr('Informe a finalidade.'); return; }
    setSubmitting(true);
    try {
      const body = { ...form, cpf_cnpj: raw }; if (!isCPF) delete body.data_nascimento;
      const res = await cndAPI.consultar(body);
      setConsultaId(res.consulta_id); setStep(2);
    } catch (e) { setErr(e?.response?.data?.detail || 'Erro ao iniciar consulta.'); }
    finally { setSubmitting(false); }
  };

  const reset = () => { setStep(1); setConsultaId(null); setForm({ cpf_cnpj: '', nome_parte: '', tipo_parte: 'Vendedor', data_nascimento: '', finalidade: '' }); };

  const baixarTodas = async () => {
    if (!consulta?.certidoes) return;
    for (const c of consulta.certidoes.filter(c => c.status !== 'indisponivel' && c.status !== 'processando')) {
      try { const r = await cndAPI.downloadCertidao(consultaId, c.provider); if (r.pdf_base64) { const a = document.createElement('a'); a.href = `data:application/pdf;base64,${r.pdf_base64}`; a.download = r.filename || `certidao_${c.provider}.pdf`; a.click(); await new Promise(r => setTimeout(r, 300)); } } catch { /**/ }
    }
  };

  const certs = consulta?.certidoes || [];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-emerald-900 flex items-center justify-center"><FileSearch className="w-5 h-5 text-white" /></div>
        <div><h2 className="text-xl font-bold text-gray-900">Consulta de Certidões CND</h2><p className="text-sm text-gray-500">Receita Federal, PGFN, TST, TRF1, TJMA, CNIB e mais</p></div>
      </div>

      {step === 1 && (
        <form onSubmit={submit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h3 className="font-semibold text-gray-800">Dados da parte</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input label="CPF ou CNPJ *" name="cpf_cnpj" value={form.cpf_cnpj} onChange={set} placeholder="000.000.000-00 ou 00.000.000/0000-00" required style={{ fontFamily: 'monospace' }} />
            </div>
            <Input label="Nome completo *" name="nome_parte" value={form.nome_parte} onChange={set} placeholder="Nome da parte" required />
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Tipo da parte *</label>
              <select name="tipo_parte" value={form.tipo_parte} onChange={set} className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 bg-white">
                {TIPOS.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            {isCPF && <Input label="Data de nascimento" type="date" name="data_nascimento" value={form.data_nascimento} onChange={set} />}
            <div className={isCPF ? '' : 'sm:col-span-2'}>
              <label className="block text-xs font-medium text-gray-600 mb-1">Finalidade *</label>
              <textarea name="finalidade" value={form.finalidade} onChange={set} rows={2} placeholder="Ex: Avaliação de garantia para financiamento" required className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 resize-none" />
            </div>
          </div>
          {err && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{err}</p>}
          <button type="submit" disabled={submitting} className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-900 text-white font-semibold text-sm hover:bg-emerald-800 disabled:opacity-60">
            {submitting ? <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Aguarde...</> : <><FileSearch className="w-4 h-4" />Consultar Certidões</>}
          </button>
        </form>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
            <span className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
            <div><p className="font-semibold text-blue-800 text-sm">Consultando certidões...</p><p className="text-xs text-blue-600 mt-0.5">Aguarde. Resultados aparecem automaticamente.</p></div>
          </div>
          {certs.length > 0 && <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{certs.map(c => <CNDResultCard key={c.provider} certidao={c} consultaId={consultaId} />)}</div>}
        </div>
      )}

      {step === 3 && consulta && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-2"><p className="font-semibold text-gray-800">{consulta.nome_parte}</p><Resumo certs={certs} /></div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={baixarTodas} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-emerald-900 text-white text-sm font-medium hover:bg-emerald-800"><Download className="w-4 h-4" />Baixar Todas</button>
              <button onClick={reset} className="flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-700 hover:bg-gray-50"><RotateCcw className="w-4 h-4" />Reconsultar</button>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{certs.map(c => <CNDResultCard key={c.provider} certidao={c} consultaId={consultaId} />)}</div>
        </div>
      )}
    </div>
  );
}
