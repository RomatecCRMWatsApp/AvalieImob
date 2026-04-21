// @module Garantias/steps/StepConclusao — Rural: Step 7 — Considerações Finais e Responsável Técnico

import React from 'react';
import { SectionTitle, Field, Input, Textarea } from './shared.js';

const StepConclusao = ({ form, set, setNested }) => {
  const r = form.responsavel || {};
  return (
    <div className="space-y-6">
      <SectionTitle>Considerações Finais</SectionTitle>
      <Field label="Considerações">
        <Textarea value={form.consideracoes} onChange={(e) => set('consideracoes', e.target.value)} rows={4} />
      </Field>
      <Field label="Ressalvas">
        <Textarea value={form.ressalvas} onChange={(e) => set('ressalvas', e.target.value)} rows={3} />
      </Field>

      <SectionTitle>Responsável Técnico</SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Nome do Responsável" required>
          <Input value={r.nome} onChange={(e) => setNested('responsavel', 'nome', e.target.value)} />
        </Field>
        <Field label="CRECI">
          <Input value={r.creci} onChange={(e) => setNested('responsavel', 'creci', e.target.value)} />
        </Field>
        <Field label="CNAI">
          <Input value={r.cnai} onChange={(e) => setNested('responsavel', 'cnai', e.target.value)} />
        </Field>
        <Field label="Registro Complementar (CREA/CAU)">
          <Input value={r.registro} onChange={(e) => setNested('responsavel', 'registro', e.target.value)} />
        </Field>
      </div>
    </div>
  );
};

export default StepConclusao;
