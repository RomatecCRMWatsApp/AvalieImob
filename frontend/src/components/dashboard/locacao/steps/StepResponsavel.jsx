// @module locacao/steps/StepResponsavel — Step 8: Responsável Técnico da Locação
import React from 'react';
import { Field, Input, Select, Grid } from '../shared/primitives';

export const StepResponsavel = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">8. Responsável Técnico</h3>
      <Grid cols={2}>
        <Field label="Nome Completo" className="md:col-span-2">
          <Input value={form.responsavel_nome} onChange={e => set('responsavel_nome', e.target.value)} />
        </Field>
        <Field label="Tipo de Profissional">
          <Select
            value={form.tipo_profissional}
            onChange={e => set('tipo_profissional', e.target.value)}
            options={[
              { value: 'corretor', label: 'Corretor de Imóveis' },
              { value: 'engenheiro', label: 'Engenheiro Civil' },
              { value: 'arquiteto', label: 'Arquiteto e Urbanista' },
              { value: 'agrimensor', label: 'Agrimensor' },
              { value: 'perito', label: 'Perito Judicial' },
            ]}
          />
        </Field>
        <Field label="CRECI">
          <Input value={form.responsavel_creci} onChange={e => set('responsavel_creci', e.target.value)} placeholder="CRECI/SP 123456" />
        </Field>
        <Field label="CNAI">
          <Input value={form.responsavel_cnai} onChange={e => set('responsavel_cnai', e.target.value)} placeholder="CNAI 12345" />
        </Field>
        <Field label="Registro Profissional (CREA/CAU)">
          <Input value={form.registro_profissional} onChange={e => set('registro_profissional', e.target.value)} />
        </Field>
        <Field label="ART / RRT (número)">
          <Input value={form.art_rrt_numero} onChange={e => set('art_rrt_numero', e.target.value)} />
        </Field>
        <Field label="Prazo de Validade (meses)">
          <Input type="number" value={form.prazo_validade_meses} onChange={e => set('prazo_validade_meses', parseInt(e.target.value) || 6)} />
        </Field>
        <Field label="Cidade de Emissão">
          <Input value={form.conclusion_city} onChange={e => set('conclusion_city', e.target.value)} />
        </Field>
        <Field label="Data de Emissão">
          <Input type="date" value={form.conclusion_date} onChange={e => set('conclusion_date', e.target.value)} />
        </Field>
      </Grid>
    </div>
  );
};
