// @module Garantias/steps/StepResultadoRural — Rural: Step 6 — Resultado da Avaliação Rural

import React from 'react';
import { SectionTitle, Field, Input, Select } from './shared.js';

const StepResultadoRural = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Resultado da Avaliação</SectionTitle>
    <div className="grid md:grid-cols-3 gap-4">
      <Field label="Valor Unitário (R$)">
        <Input type="number" value={form.valor_unitario} onChange={(e) => set('valor_unitario', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Valor Total (R$)" required>
        <Input type="number" value={form.valor_total} onChange={(e) => set('valor_total', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Status">
        <Select value={form.status} onChange={(e) => set('status', e.target.value)}>
          <option value="rascunho">Rascunho</option>
          <option value="em_andamento">Em Andamento</option>
          <option value="concluido">Concluído</option>
        </Select>
      </Field>
      <Field label="Intervalo Inferior (R$)">
        <Input type="number" value={form.resultado_intervalo_inf} onChange={(e) => set('resultado_intervalo_inf', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Intervalo Superior (R$)">
        <Input type="number" value={form.resultado_intervalo_sup} onChange={(e) => set('resultado_intervalo_sup', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>
    <Field label="Valor por Extenso">
      <Input value={form.resultado_em_extenso} onChange={(e) => set('resultado_em_extenso', e.target.value)} placeholder="Ex.: Um milhão e duzentos mil reais" />
    </Field>
    {form.valor_total > 0 && (
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
        <div className="text-xs text-emerald-700 font-semibold uppercase tracking-wider mb-1">Valor Total Avaliado</div>
        <div className="text-3xl font-bold text-emerald-900">
          {Number(form.valor_total).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
        </div>
      </div>
    )}
  </div>
);

export default StepResultadoRural;
