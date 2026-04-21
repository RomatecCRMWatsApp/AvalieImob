// @module Semoventes/steps/Step3Rebanho — Step 3 — Composição do Rebanho por Categoria

import React from 'react';
import { Plus, Trash2, Layers } from 'lucide-react';
import { Button } from '../../../ui/button';
import { SectionTitle, Field, Inp, Sel, fmtCurrency, getCategoriaOptions, EMPTY_CATEGORIA } from './shared.js';

const Step3Rebanho = ({ form, set }) => {
  const categorias = form.categorias || [];
  const catOptions = getCategoriaOptions(form.tipo_semovente);

  const addCategoria = () => {
    set('categorias', [...categorias, { ...EMPTY_CATEGORIA }]);
  };

  const removeCategoria = (idx) => {
    const updated = categorias.filter((_, i) => i !== idx);
    recalcTotals(updated);
  };

  const updateCategoria = (idx, field, value) => {
    const updated = categorias.map((c, i) => {
      if (i !== idx) return c;
      const next = { ...c, [field]: value };
      if (field === 'valor_unitario' || field === 'quantidade') {
        const qty = field === 'quantidade' ? (parseInt(value) || 0) : (parseInt(next.quantidade) || 0);
        const vu  = field === 'valor_unitario' ? (parseFloat(value) || 0) : (parseFloat(next.valor_unitario) || 0);
        next.valor_total = qty * vu;
      }
      if (field === 'quantidade') next.quantidade = parseInt(value) || 0;
      return next;
    });
    recalcTotals(updated);
  };

  const recalcTotals = (cats) => {
    const totalCabecas = cats.reduce((s, c) => s + (parseInt(c.quantidade) || 0), 0);
    const totalUA = cats.reduce((s, c) => {
      const kg  = parseFloat(c.peso_medio_kg) || 0;
      const qty = parseInt(c.quantidade) || 0;
      return s + (kg > 0 ? (qty * kg) / 450 : 0);
    }, 0);
    set('categorias', cats);
    set('total_cabecas', totalCabecas);
    set('total_ua', Math.round(totalUA * 10) / 10);
    const totalVM = cats.reduce((s, c) => s + (parseFloat(c.valor_total) || 0), 0);
    set('valor_mercado_total', Math.round(totalVM * 100) / 100);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionTitle>Composição do Rebanho</SectionTitle>
        <Button size="sm" onClick={addCategoria} className="bg-emerald-900 hover:bg-emerald-800 text-white">
          <Plus className="w-3.5 h-3.5 mr-1" />Adicionar Categoria
        </Button>
      </div>

      {categorias.length === 0 ? (
        <div className="text-center py-10 border-2 border-dashed border-emerald-200 rounded-xl text-gray-500">
          <Layers className="w-8 h-8 mx-auto mb-2 text-emerald-300" />
          <p className="text-sm">Clique em "Adicionar Categoria" para inserir o rebanho</p>
        </div>
      ) : (
        <div className="space-y-4">
          {categorias.map((cat, idx) => {
            const isEquino  = form.tipo_semovente === 'equino';
            const isMatriz  = cat.categoria === 'matrizes' || cat.categoria === 'matriz_suina' || cat.categoria === 'ovelha';
            const isEngorda = cat.categoria === 'bois_engorda';
            return (
              <div key={idx} className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold text-emerald-800">Categoria {idx + 1}</span>
                  <button onClick={() => removeCategoria(idx)} className="text-red-400 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="grid md:grid-cols-3 gap-3">
                  <Field label="Categoria" required>
                    <Sel value={cat.categoria} onChange={(e) => updateCategoria(idx, 'categoria', e.target.value)}>
                      <option value="">Selecionar...</option>
                      {catOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </Sel>
                  </Field>
                  <Field label="Quantidade (cabeças)">
                    <Inp type="number" value={cat.quantidade} onChange={(e) => updateCategoria(idx, 'quantidade', e.target.value)} />
                  </Field>
                  <Field label="Raça">
                    <Inp value={cat.raca} onChange={(e) => updateCategoria(idx, 'raca', e.target.value)} placeholder="Ex.: Nelore, Angus..." />
                  </Field>
                  <Field label="Faixa Etária">
                    <Inp value={cat.faixa_etaria} onChange={(e) => updateCategoria(idx, 'faixa_etaria', e.target.value)} placeholder="Ex.: 2-3 anos" />
                  </Field>
                  <Field label="Peso Médio (kg)" hint="Usado para calcular UA">
                    <Inp type="number" value={cat.peso_medio_kg} onChange={(e) => updateCategoria(idx, 'peso_medio_kg', parseFloat(e.target.value) || 0)} />
                  </Field>
                  <Field label="Reg. Genealógico">
                    <Inp value={cat.registro_genealogico} onChange={(e) => updateCategoria(idx, 'registro_genealogico', e.target.value)} placeholder="PO, PC, PN..." />
                  </Field>
                  <Field label="Valor Unitário (R$)">
                    <Inp type="number" value={cat.valor_unitario} onChange={(e) => updateCategoria(idx, 'valor_unitario', parseFloat(e.target.value) || 0)} />
                  </Field>
                  <Field label="Valor Total (R$)">
                    <div className="flex items-center h-9 px-3 rounded-lg border border-gray-200 bg-emerald-50 text-sm font-semibold text-emerald-900">
                      {fmtCurrency(cat.valor_total)}
                    </div>
                  </Field>
                  {isMatriz && (
                    <>
                      <Field label="Taxa de Prenhez (%)">
                        <Inp type="number" value={cat.taxa_prenhez ?? ''} onChange={(e) => updateCategoria(idx, 'taxa_prenhez', parseFloat(e.target.value) || null)} />
                      </Field>
                      <Field label="Produção de Leite (L/dia)">
                        <Inp type="number" value={cat.producao_leite ?? ''} onChange={(e) => updateCategoria(idx, 'producao_leite', parseFloat(e.target.value) || null)} />
                      </Field>
                    </>
                  )}
                  {isEngorda && (
                    <>
                      <Field label="Arrobas Estimadas (@)">
                        <Inp type="number" value={cat.arrobas_estimadas ?? ''} onChange={(e) => updateCategoria(idx, 'arrobas_estimadas', parseFloat(e.target.value) || null)} />
                      </Field>
                      <Field label="Estágio">
                        <Sel value={cat.estagio ?? ''} onChange={(e) => updateCategoria(idx, 'estagio', e.target.value)}>
                          <option value="">Selecionar...</option>
                          <option value="confinamento">Confinamento</option>
                          <option value="semiconfinamento">Semiconfinamento</option>
                          <option value="pastagem">Pastagem</option>
                        </Sel>
                      </Field>
                    </>
                  )}
                  {isEquino && (
                    <Field label="Aptidão">
                      <Sel value={cat.aptidao ?? ''} onChange={(e) => updateCategoria(idx, 'aptidao', e.target.value)}>
                        <option value="">Selecionar...</option>
                        <option value="corrida">Corrida</option>
                        <option value="trabalho">Trabalho</option>
                        <option value="esporte">Esporte</option>
                        <option value="lazer">Lazer</option>
                      </Sel>
                    </Field>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Totais */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
          <div className="text-xs text-emerald-600 font-semibold uppercase tracking-wider">Total Cabeças</div>
          <div className="text-2xl font-bold text-emerald-900 mt-1">{form.total_cabecas || 0}</div>
        </div>
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
          <div className="text-xs text-emerald-600 font-semibold uppercase tracking-wider">Total UA</div>
          <div className="text-2xl font-bold text-emerald-900 mt-1">{(form.total_ua || 0).toFixed(1)}</div>
          <div className="text-[10px] text-emerald-600 mt-0.5">1 UA = 450 kg</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
          <div className="text-xs text-amber-700 font-semibold uppercase tracking-wider">Valor de Mercado</div>
          <div className="text-lg font-bold text-amber-900 mt-1">{fmtCurrency(form.valor_mercado_total)}</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Lotação (UA/ha)">
          <Inp type="number" value={form.lotacao_ua_ha} onChange={(e) => set('lotacao_ua_ha', parseFloat(e.target.value) || 0)} />
        </Field>
      </div>
    </div>
  );
};

export default Step3Rebanho;
