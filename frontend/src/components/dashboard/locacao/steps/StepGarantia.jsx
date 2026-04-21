// @module locacao/steps/StepGarantia — Step 7: Condições da Locação e Garantia
import React from 'react';
import { Field, Input, Select, Grid } from '../shared/primitives';
import { GARANTIA_OPTIONS } from '../locacaoHelpers';

export const StepGarantia = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">7. Condições da Locação e Garantia</h3>
      <Grid cols={2}>
        <Field label="Garantia Locatícia">
          <Select value={form.garantia_locacao} onChange={e => set('garantia_locacao', e.target.value)} options={GARANTIA_OPTIONS} placeholder="Selecione..." />
        </Field>
        <Field label="Prazo Sugerido da Locação">
          <Input value={form.prazo_locacao} onChange={e => set('prazo_locacao', e.target.value)} placeholder="Ex: 30 meses" />
        </Field>
        <Field label="Fator de Locação (%)">
          <Input type="number" step="0.01" value={form.fator_locacao ?? ''} onChange={e => set('fator_locacao', e.target.value ? parseFloat(e.target.value) : null)} placeholder="Ex: 0.50" />
        </Field>
        <Field label="Grau de Precisão (NBR 14653)">
          <Select
            value={form.grau_precisao}
            onChange={e => set('grau_precisao', e.target.value)}
            options={[{ value: 'I', label: 'Grau I — 15%' }, { value: 'II', label: 'Grau II — 11,25%' }, { value: 'III', label: 'Grau III — 7,5%' }]}
          />
        </Field>
        <Field label="Campo Arbítrio — Mínimo (R$)">
          <Input type="number" value={form.campo_arbitrio_min} onChange={e => set('campo_arbitrio_min', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Campo Arbítrio — Máximo (R$)">
          <Input type="number" value={form.campo_arbitrio_max} onChange={e => set('campo_arbitrio_max', parseFloat(e.target.value) || 0)} />
        </Field>
      </Grid>
    </div>
  );
};
