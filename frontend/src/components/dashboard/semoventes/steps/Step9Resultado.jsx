// @module Semoventes/steps/Step9Resultado — Step 9 — Resultado da Avaliação e Fator de Liquidez

import React from 'react';
import { SectionTitle, Field, Inp, fmtCurrency } from './shared.js';

const Step9Resultado = ({ form, set }) => {
  const vm  = parseFloat(form.valor_mercado_total) || 0;
  const fl  = parseFloat(form.fator_liquidez) || 0.65;
  const valorGarantia = Math.round(vm * fl * 100) / 100;

  const handleFatorLiquidez = (v) => {
    const fl2 = parseFloat(v) || 0.65;
    set('fator_liquidez', fl2);
    set('valor_garantia_aceito', Math.round(vm * fl2 * 100) / 100);
  };

  return (
    <div className="space-y-6">
      <SectionTitle>Planilha de Avaliação por Categoria</SectionTitle>

      {(form.categorias || []).length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-emerald-900 text-white">
                <th className="px-3 py-2 text-left font-semibold">Categoria</th>
                <th className="px-3 py-2 text-right font-semibold">Qtd</th>
                <th className="px-3 py-2 text-left font-semibold">Raça</th>
                <th className="px-3 py-2 text-right font-semibold">Vl. Unit.</th>
                <th className="px-3 py-2 text-right font-semibold">Vl. Total</th>
              </tr>
            </thead>
            <tbody>
              {form.categorias.map((c, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-3 py-2 capitalize">{c.categoria.replace(/_/g, ' ')}</td>
                  <td className="px-3 py-2 text-right">{c.quantidade}</td>
                  <td className="px-3 py-2">{c.raca || '—'}</td>
                  <td className="px-3 py-2 text-right">{fmtCurrency(c.valor_unitario)}</td>
                  <td className="px-3 py-2 text-right font-semibold">{fmtCurrency(c.valor_total)}</td>
                </tr>
              ))}
              <tr className="bg-emerald-50 font-bold border-t-2 border-emerald-300">
                <td className="px-3 py-2 text-emerald-900">TOTAL</td>
                <td className="px-3 py-2 text-right text-emerald-900">{form.total_cabecas}</td>
                <td className="px-3 py-2"></td>
                <td className="px-3 py-2"></td>
                <td className="px-3 py-2 text-right text-emerald-900">{fmtCurrency(form.valor_mercado_total)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-gray-400 italic">Nenhuma categoria cadastrada — retorne ao Step 3 para adicionar o rebanho.</p>
      )}

      <SectionTitle>Fator de Liquidez e Garantia</SectionTitle>
      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <Field
            label={`Fator de Liquidez: ${(form.fator_liquidez * 100).toFixed(0)}%`}
            hint="MCR BACEN Cap. 6 — semoventes têm liquidez menor que imóveis. Padrão: 65%"
          >
            <input
              type="range"
              min="0.60"
              max="0.75"
              step="0.01"
              value={form.fator_liquidez || 0.65}
              onChange={(e) => handleFatorLiquidez(e.target.value)}
              className="w-full accent-emerald-700"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>60%</span>
              <span>65% (padrão)</span>
              <span>75%</span>
            </div>
          </Field>
        </div>
        <div className="space-y-3">
          <Field label="LTV Recomendado (%)" hint="Loan-To-Value">
            <Inp type="number" value={form.ltv_recomendado} onChange={(e) => set('ltv_recomendado', parseFloat(e.target.value) || 65)} />
          </Field>
          <Field label="Validade do Laudo (meses)">
            <Inp type="number" value={form.validade_laudo_meses} onChange={(e) => set('validade_laudo_meses', parseInt(e.target.value) || 6)} />
          </Field>
        </div>
      </div>

      {/* Cards de resultado */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
          <div className="text-xs text-emerald-700 font-semibold uppercase tracking-wider mb-1">Valor de Mercado</div>
          <div className="text-2xl font-bold text-emerald-900">{fmtCurrency(form.valor_mercado_total)}</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <div className="text-xs text-amber-700 font-semibold uppercase tracking-wider mb-1">Fator Liquidez</div>
          <div className="text-2xl font-bold text-amber-900">{((form.fator_liquidez || 0.65) * 100).toFixed(0)}%</div>
        </div>
        <div className="bg-emerald-900 rounded-xl p-5">
          <div className="text-xs text-emerald-200 font-semibold uppercase tracking-wider mb-1">Valor da Garantia</div>
          <div className="text-2xl font-bold text-white">{fmtCurrency(valorGarantia)}</div>
        </div>
      </div>

      <Field label="Seguro Recomendado (R$)" hint="Valor de seguro agrícola/pecuário recomendado">
        <Inp type="number" value={form.seguro_recomendado_valor} onChange={(e) => set('seguro_recomendado_valor', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>
  );
};

export default Step9Resultado;
