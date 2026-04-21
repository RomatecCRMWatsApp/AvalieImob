// @module locacao/steps/StepObjetivo — Step 2: Objetivo da Avaliação de Locação
import React from 'react';
import { Field, Textarea, Select, Grid } from '../shared/primitives';
import { OBJETIVO_OPTIONS, TIPO_LOCACAO_OPTIONS } from '../locacaoHelpers';

export const StepObjetivo = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">2. Objetivo da Avaliação</h3>
      <Grid cols={2}>
        <Field label="Finalidade">
          <Select
            value={form.objetivo}
            onChange={e => set('objetivo', e.target.value)}
            options={OBJETIVO_OPTIONS}
            placeholder="Selecione a finalidade"
          />
        </Field>
        <Field label="Tipo de Locação">
          <Select
            value={form.tipo_locacao}
            onChange={e => set('tipo_locacao', e.target.value)}
            options={TIPO_LOCACAO_OPTIONS}
          />
        </Field>
        {form.objetivo === 'outros' && (
          <Field label="Descreva o objetivo" className="md:col-span-2">
            <Textarea value={form.objetivo_outros} onChange={e => set('objetivo_outros', e.target.value)} placeholder="Descreva a finalidade..." />
          </Field>
        )}
        <Field label="Base Legal" className="md:col-span-2">
          <Textarea
            rows={2}
            value={form.base_legal_locacao}
            onChange={e => set('base_legal_locacao', e.target.value)}
            placeholder="Lei 8.245/1991..."
          />
        </Field>
      </Grid>
    </div>
  );
};
