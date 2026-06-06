// @module dashboard/incra/AdminIncra — Cadastro/gestão das tabelas INCRA (Valores de Terra Nua).
// Acesso restrito a admin (a rota POST/DELETE exige papel admin no backend).
import React, { useEffect, useState } from 'react';
import { incraAPI } from '@/lib/api';
import { Plus, Trash2, Save, Loader2 } from 'lucide-react';

const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

const faixaVazia = () => ({ faixa: '', vr_min: '', vr_max: '', vr_medio: '' });

export default function AdminIncra() {
  const hoje = new Date();
  const [tabelas, setTabelas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [form, setForm] = useState({
    regiao: '',
    municipio: '',
    ano: hoje.getFullYear(),
    mes: hoje.getMonth() + 1,
    vigencia: `${MESES[hoje.getMonth()]}/${hoje.getFullYear()}`,
    fonte: 'INCRA/SR-26/MA',
    faixas: [faixaVazia()],
  });

  const carregar = () => {
    setLoading(true);
    incraAPI
      .listar()
      .then((d) => setTabelas(Array.isArray(d) ? d : []))
      .catch(() => setTabelas([]))
      .finally(() => setLoading(false));
  };
  useEffect(carregar, []);

  const setFaixa = (i, campo, valor) =>
    setForm((f) => ({
      ...f,
      faixas: f.faixas.map((fx, k) => (k === i ? { ...fx, [campo]: valor } : fx)),
    }));
  const addFaixa = () => setForm((f) => ({ ...f, faixas: [...f.faixas, faixaVazia()] }));
  const rmFaixa = (i) =>
    setForm((f) => ({ ...f, faixas: f.faixas.filter((_, k) => k !== i) }));

  const salvar = async () => {
    setMsg(null);
    const faixas = form.faixas
      .filter((fx) => fx.faixa && (Number(fx.vr_min) || Number(fx.vr_max)))
      .map((fx) => ({
        faixa: fx.faixa.trim(),
        vr_min: Number(fx.vr_min) || 0,
        vr_max: Number(fx.vr_max) || 0,
        vr_medio: Number(fx.vr_medio) || 0,
      }));
    if (!form.regiao.trim()) return setMsg({ tipo: 'erro', txt: 'Informe a região.' });
    if (!faixas.length) return setMsg({ tipo: 'erro', txt: 'Informe ao menos uma faixa válida.' });
    setSaving(true);
    try {
      await incraAPI.criar({
        regiao: form.regiao.trim(),
        municipio: form.municipio.trim() || null,
        ano: Number(form.ano),
        mes: Number(form.mes),
        vigencia: form.vigencia.trim(),
        fonte: form.fonte.trim(),
        faixas,
      });
      setMsg({ tipo: 'ok', txt: 'Tabela INCRA cadastrada.' });
      setForm((f) => ({ ...f, faixas: [faixaVazia()] }));
      carregar();
    } catch (e) {
      const detail = e?.response?.data?.detail || 'Erro ao salvar.';
      setMsg({ tipo: 'erro', txt: typeof detail === 'string' ? detail : 'Erro ao salvar.' });
    } finally {
      setSaving(false);
    }
  };

  const remover = async (id) => {
    if (!window.confirm('Remover esta tabela INCRA?')) return;
    try {
      await incraAPI.remover(id);
      carregar();
    } catch {
      setMsg({ tipo: 'erro', txt: 'Não foi possível remover.' });
    }
  };

  const inputCls =
    'w-full h-9 rounded-md border border-gray-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500';

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Tabelas INCRA — Valores de Terra Nua</h1>
        <p className="text-sm text-gray-500">
          Cadastre as tabelas publicadas pelo INCRA. A mais recente por região/município é usada
          automaticamente nos laudos rurais.
        </p>
      </div>

      {msg && (
        <div
          className={`p-3 rounded-lg text-sm border ${
            msg.tipo === 'ok'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
              : 'bg-red-50 border-red-200 text-red-700'
          }`}
        >
          {msg.txt}
        </div>
      )}

      {/* Formulário */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Nova tabela</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="col-span-2">
            <label className="block text-xs text-gray-500 mb-1">Região *</label>
            <input className={inputCls} value={form.regiao}
              onChange={(e) => setForm({ ...form, regiao: e.target.value })}
              placeholder="Ex: Médio Mearim / MA" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Município (opcional)</label>
            <input className={inputCls} value={form.municipio}
              onChange={(e) => setForm({ ...form, municipio: e.target.value })}
              placeholder="Ex: Açailândia" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Ano</label>
            <input type="number" className={inputCls} value={form.ano}
              onChange={(e) => setForm({ ...form, ano: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Mês</label>
            <select className={inputCls} value={form.mes}
              onChange={(e) => setForm({ ...form, mes: e.target.value })}>
              {MESES.map((m, i) => (
                <option key={i} value={i + 1}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Vigência</label>
            <input className={inputCls} value={form.vigencia}
              onChange={(e) => setForm({ ...form, vigencia: e.target.value })}
              placeholder="Jan/2025" />
          </div>
          <div className="col-span-2">
            <label className="block text-xs text-gray-500 mb-1">Fonte</label>
            <input className={inputCls} value={form.fonte}
              onChange={(e) => setForm({ ...form, fonte: e.target.value })}
              placeholder="INCRA/SR-26/MA" />
          </div>
        </div>

        {/* Faixas */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Faixas (R$/ha)</span>
            <button type="button" onClick={addFaixa}
              className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-900">
              <Plus className="w-4 h-4" /> Adicionar faixa
            </button>
          </div>
          <div className="space-y-2">
            {form.faixas.map((fx, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 items-center">
                <input className={`${inputCls} col-span-5`} value={fx.faixa}
                  onChange={(e) => setFaixa(i, 'faixa', e.target.value)}
                  placeholder="Ex: Até 1 módulo fiscal" />
                <input type="number" className={`${inputCls} col-span-2`} value={fx.vr_min}
                  onChange={(e) => setFaixa(i, 'vr_min', e.target.value)} placeholder="Mín" />
                <input type="number" className={`${inputCls} col-span-2`} value={fx.vr_max}
                  onChange={(e) => setFaixa(i, 'vr_max', e.target.value)} placeholder="Máx" />
                <input type="number" className={`${inputCls} col-span-2`} value={fx.vr_medio}
                  onChange={(e) => setFaixa(i, 'vr_medio', e.target.value)} placeholder="Médio (auto)" />
                <button type="button" onClick={() => rmFaixa(i)}
                  className="col-span-1 flex justify-center text-red-500 hover:text-red-700">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-end">
          <button type="button" onClick={salvar} disabled={saving}
            className="inline-flex items-center gap-2 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-60 text-white text-sm font-semibold px-5 py-2.5 rounded-lg">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Salvar tabela
          </button>
        </div>
      </div>

      {/* Lista */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Tabelas cadastradas</h2>
        {loading ? (
          <div className="text-sm text-gray-500">Carregando…</div>
        ) : tabelas.length === 0 ? (
          <div className="text-sm text-gray-400">Nenhuma tabela cadastrada ainda.</div>
        ) : (
          <div className="space-y-2">
            {tabelas.map((t) => (
              <div key={t.id} className="flex items-start justify-between border border-gray-100 rounded-lg p-3">
                <div className="text-sm">
                  <div className="font-medium text-gray-800">
                    {t.regiao}{t.municipio ? ` · ${t.municipio}` : ''}
                    <span className="text-gray-400 font-normal"> — {t.vigencia}</span>
                    {t.ativo === false && <span className="ml-2 text-xs text-red-500">(inativa)</span>}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">{t.fonte} · {(t.faixas || []).length} faixa(s)</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {(t.faixas || []).map((f, i) => (
                      <span key={i} className="mr-3">{f.faixa}: {fmtBRL(f.vr_min)}–{fmtBRL(f.vr_max)}</span>
                    ))}
                  </div>
                </div>
                <button type="button" onClick={() => remover(t.id)}
                  className="text-red-500 hover:text-red-700 ml-3" title="Remover">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
