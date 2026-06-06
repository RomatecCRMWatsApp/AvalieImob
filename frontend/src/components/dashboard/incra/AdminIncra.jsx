// @module dashboard/incra/AdminIncra — Cadastro/gestão das tabelas INCRA (Valores de Terra Nua).
// Acesso restrito a admin (a rota POST/DELETE exige papel admin no backend).
import React, { useEffect, useState } from 'react';
import { incraAPI } from '@/lib/api';
import { Plus, Trash2, Save, Loader2, Pencil, X } from 'lucide-react';

const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

const faixaVazia = () => ({ faixa: '', vr_min: '', vr_max: '', vr_medio: '', n_amostras: '' });
const fatorVazio = () => ({ fator: '', variavel: '', faixa_ajuste: '' });
const formVazio = (hoje) => ({
  regiao: '',
  municipio: '',
  municipios: '',
  polo_regional: '',
  norma: 'NBR 14653-3:2019',
  ano: hoje.getFullYear(),
  mes: hoje.getMonth() + 1,
  vigencia: `${MESES[hoje.getMonth()]}/${hoje.getFullYear()}`,
  fonte: 'INCRA/SR-21-MA',
  faixas: [faixaVazia()],
  fatores: [],
  notas: '',
});

export default function AdminIncra() {
  const hoje = new Date();
  const [tabelas, setTabelas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(() => formVazio(hoje));

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

  const setFator = (i, campo, valor) =>
    setForm((f) => ({
      ...f,
      fatores: (f.fatores || []).map((ft, k) => (k === i ? { ...ft, [campo]: valor } : ft)),
    }));
  const addFator = () => setForm((f) => ({ ...f, fatores: [...(f.fatores || []), fatorVazio()] }));
  const rmFator = (i) =>
    setForm((f) => ({ ...f, fatores: (f.fatores || []).filter((_, k) => k !== i) }));

  const salvar = async () => {
    setMsg(null);
    const faixas = form.faixas
      .filter((fx) => fx.faixa && (Number(fx.vr_min) || Number(fx.vr_max)))
      .map((fx) => ({
        faixa: fx.faixa.trim(),
        vr_min: Number(fx.vr_min) || 0,
        vr_max: Number(fx.vr_max) || 0,
        vr_medio: Number(fx.vr_medio) || 0,
        n_amostras: fx.n_amostras === '' || fx.n_amostras == null ? null : Number(fx.n_amostras),
      }));
    const fatores = (form.fatores || [])
      .filter((ft) => (ft.fator || '').trim())
      .map((ft) => ({
        fator: ft.fator.trim(),
        variavel: (ft.variavel || '').trim(),
        faixa_ajuste: (ft.faixa_ajuste || '').trim(),
      }));
    if (!form.regiao.trim()) return setMsg({ tipo: 'erro', txt: 'Informe a região.' });
    if (!faixas.length) return setMsg({ tipo: 'erro', txt: 'Informe ao menos uma faixa válida.' });
    const payload = {
      regiao: form.regiao.trim(),
      municipio: form.municipio.trim() || null,
      municipios: (form.municipios || '').split(',').map((s) => s.trim()).filter(Boolean),
      polo_regional: (form.polo_regional || '').trim() || null,
      norma: (form.norma || '').trim() || 'NBR 14653-3:2019',
      ano: Number(form.ano),
      mes: Number(form.mes),
      vigencia: form.vigencia.trim(),
      fonte: form.fonte.trim(),
      faixas,
      fatores,
      notas: (form.notas || '').trim() || null,
    };
    setSaving(true);
    try {
      if (editingId) {
        await incraAPI.editar(editingId, payload);
        setMsg({ tipo: 'ok', txt: 'Tabela INCRA atualizada.' });
      } else {
        await incraAPI.criar(payload);
        setMsg({ tipo: 'ok', txt: 'Tabela INCRA cadastrada.' });
      }
      cancelarEdicao();
      carregar();
    } catch (e) {
      const detail = e?.response?.data?.detail || 'Erro ao salvar.';
      setMsg({ tipo: 'erro', txt: typeof detail === 'string' ? detail : 'Erro ao salvar.' });
    } finally {
      setSaving(false);
    }
  };

  const editar = (t) => {
    setEditingId(t.id);
    setMsg(null);
    setForm({
      regiao: t.regiao || '',
      municipio: t.municipio || '',
      municipios: Array.isArray(t.municipios) ? t.municipios.join(', ') : '',
      polo_regional: t.polo_regional || '',
      norma: t.norma || 'NBR 14653-3:2019',
      ano: t.ano || hoje.getFullYear(),
      mes: t.mes || hoje.getMonth() + 1,
      vigencia: t.vigencia || '',
      fonte: t.fonte || '',
      faixas: (t.faixas && t.faixas.length
        ? t.faixas.map((f) => ({
            faixa: f.faixa || '',
            vr_min: f.vr_min ?? '',
            vr_max: f.vr_max ?? '',
            vr_medio: f.vr_medio ?? '',
            n_amostras: f.n_amostras ?? '',
          }))
        : [faixaVazia()]),
      fatores: (t.fatores || []).map((ft) => ({
        fator: ft.fator || '',
        variavel: ft.variavel || '',
        faixa_ajuste: ft.faixa_ajuste || '',
      })),
      notas: t.notas || '',
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const cancelarEdicao = () => {
    setEditingId(null);
    setForm(formVazio(hoje));
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

  const inserirExemplo = async () => {
    setMsg(null);
    try {
      const r = await incraAPI.seedExemplo();
      setMsg({
        tipo: 'ok',
        txt: r?.ja_existia
          ? 'As tabelas RAMT-MA 2022 (polos Imperatriz e Buriticupu) já estavam cadastradas.'
          : `RAMT-MA 2022 inserida (${r?.inseridas || 0} polo(s)). Valores VTI R$/ha — atualize por IPCA-E até a data-base.`,
      });
      carregar();
    } catch (e) {
      const detail = e?.response?.data?.detail || 'Erro ao inserir exemplo.';
      setMsg({ tipo: 'erro', txt: typeof detail === 'string' ? detail : 'Erro ao inserir exemplo.' });
    }
  };

  const inputCls =
    'w-full h-9 rounded-md border border-gray-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500';

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Tabelas INCRA — Valores de Terra Nua</h1>
          <p className="text-sm text-gray-500">
            Cadastre as tabelas publicadas pelo INCRA. A mais recente por região/município é usada
            automaticamente nos laudos rurais.
          </p>
        </div>
        <button type="button" onClick={inserirExemplo}
          className="shrink-0 text-xs font-medium text-emerald-700 border border-emerald-300 hover:bg-emerald-50 rounded-lg px-3 py-2">
          Inserir RAMT-MA 2022 (2 polos)
        </button>
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
      <div className={`bg-white rounded-xl border p-4 space-y-4 ${editingId ? 'border-emerald-400 ring-1 ring-emerald-200' : 'border-gray-200'}`}>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">
            {editingId ? 'Editando tabela' : 'Nova tabela'}
          </h2>
          {editingId && (
            <button type="button" onClick={cancelarEdicao}
              className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700">
              <X className="w-3.5 h-3.5" /> Cancelar edição
            </button>
          )}
        </div>
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
          <div className="col-span-2 sm:col-span-3">
            <label className="block text-xs text-gray-500 mb-1">Municípios cobertos (separados por vírgula)</label>
            <input className={inputCls} value={form.municipios}
              onChange={(e) => setForm({ ...form, municipios: e.target.value })}
              placeholder="Ex: Açailândia, Cidelândia, Itinga, Imperatriz..." />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Polo regional</label>
            <input className={inputCls} value={form.polo_regional}
              onChange={(e) => setForm({ ...form, polo_regional: e.target.value })}
              placeholder="Ex: Imperatriz / Açailândia" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Norma</label>
            <input className={inputCls} value={form.norma}
              onChange={(e) => setForm({ ...form, norma: e.target.value })}
              placeholder="NBR 14653-3:2019" />
          </div>
          <div className="col-span-2 sm:col-span-1">
            <label className="block text-xs text-gray-500 mb-1">Fonte</label>
            <input className={inputCls} value={form.fonte}
              onChange={(e) => setForm({ ...form, fonte: e.target.value })}
              placeholder="INCRA/SR-21-MA" />
          </div>
        </div>

        {/* Faixas / tipologias */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Tipologias de uso (VTI R$/ha)</span>
            <button type="button" onClick={addFaixa}
              className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-900">
              <Plus className="w-4 h-4" /> Adicionar tipologia
            </button>
          </div>
          <div className="grid grid-cols-12 gap-2 mb-1 px-1 text-[10px] uppercase tracking-wide text-gray-400">
            <span className="col-span-4">Tipologia de uso</span>
            <span className="col-span-2 text-right">Mín</span>
            <span className="col-span-2 text-right">Médio</span>
            <span className="col-span-2 text-right">Máx</span>
            <span className="col-span-1 text-right">N</span>
            <span className="col-span-1" />
          </div>
          <div className="space-y-2">
            {form.faixas.map((fx, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 items-center">
                <input className={`${inputCls} col-span-4`} value={fx.faixa}
                  onChange={(e) => setFaixa(i, 'faixa', e.target.value)}
                  placeholder="Ex: Pastagem formada — cap. alta" />
                <input type="number" className={`${inputCls} col-span-2 text-right`} value={fx.vr_min}
                  onChange={(e) => setFaixa(i, 'vr_min', e.target.value)} placeholder="Mín" />
                <input type="number" className={`${inputCls} col-span-2 text-right`} value={fx.vr_medio}
                  onChange={(e) => setFaixa(i, 'vr_medio', e.target.value)} placeholder="Médio" />
                <input type="number" className={`${inputCls} col-span-2 text-right`} value={fx.vr_max}
                  onChange={(e) => setFaixa(i, 'vr_max', e.target.value)} placeholder="Máx" />
                <input type="number" className={`${inputCls} col-span-1 text-right`} value={fx.n_amostras}
                  onChange={(e) => setFaixa(i, 'n_amostras', e.target.value)} placeholder="N" />
                <button type="button" onClick={() => rmFaixa(i)}
                  className="col-span-1 flex justify-center text-red-500 hover:text-red-700">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Fatores de homogeneização */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Fatores de homogeneização (NBR 14653-3)</span>
            <button type="button" onClick={addFator}
              className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-900">
              <Plus className="w-4 h-4" /> Adicionar fator
            </button>
          </div>
          <div className="space-y-2">
            {(form.fatores || []).map((ft, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 items-center">
                <input className={`${inputCls} col-span-4`} value={ft.fator}
                  onChange={(e) => setFator(i, 'fator', e.target.value)} placeholder="Fator (ex: Localização)" />
                <input className={`${inputCls} col-span-5`} value={ft.variavel}
                  onChange={(e) => setFator(i, 'variavel', e.target.value)} placeholder="Variável" />
                <input className={`${inputCls} col-span-2`} value={ft.faixa_ajuste}
                  onChange={(e) => setFator(i, 'faixa_ajuste', e.target.value)} placeholder="0,70 – 1,30" />
                <button type="button" onClick={() => rmFator(i)}
                  className="col-span-1 flex justify-center text-red-500 hover:text-red-700">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {(form.fatores || []).length === 0 && (
              <p className="text-xs text-gray-400">Opcional — fatores de ajuste exibidos no laudo.</p>
            )}
          </div>
        </div>

        {/* Notas técnicas */}
        <div>
          <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">Notas técnicas</label>
          <textarea className={`${inputCls} h-20 py-2 resize-y`} value={form.notas}
            onChange={(e) => setForm({ ...form, notas: e.target.value })}
            placeholder="Observações da fonte (VTI vs VTN, atualização IPCA-E, etc.)" />
        </div>

        <div className="flex justify-end">
          <button type="button" onClick={salvar} disabled={saving}
            className="inline-flex items-center gap-2 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-60 text-white text-sm font-semibold px-5 py-2.5 rounded-lg">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {editingId ? 'Salvar alterações' : 'Salvar tabela'}
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
                <div className="flex items-center gap-2 ml-3 shrink-0">
                  <button type="button" onClick={() => editar(t)}
                    className="text-emerald-600 hover:text-emerald-800" title="Editar">
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button type="button" onClick={() => remover(t.id)}
                    className="text-red-500 hover:text-red-700" title="Excluir">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
