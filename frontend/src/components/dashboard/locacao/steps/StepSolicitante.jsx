// @module locacao/steps/StepSolicitante — Step 1: Identificação do Solicitante
import React from 'react';
import { Field, Input, Grid } from '../shared/primitives';

export const StepSolicitante = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">1. Identificação do Solicitante</h3>
      {form.numero_locacao && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-2 text-sm">
          <span className="text-blue-600 font-semibold">Número: </span>
          <span className="font-mono text-blue-900">{form.numero_locacao}</span>
        </div>
      )}
      <Grid cols={2}>
        <Field label="Nome / Razão Social" className="md:col-span-2">
          <Input value={form.solicitante_nome} onChange={e => set('solicitante_nome', e.target.value)} placeholder="Nome completo ou razão social" />
        </Field>
        <Field label="CPF / CNPJ">
          <Input value={form.solicitante_cpf} onChange={e => set('solicitante_cpf', e.target.value)} placeholder="000.000.000-00" />
        </Field>
        <Field label="Telefone">
          <Input value={form.solicitante_telefone} onChange={e => set('solicitante_telefone', e.target.value)} placeholder="(00) 00000-0000" />
        </Field>
        <Field label="E-mail" className="md:col-span-2">
          <Input type="email" value={form.solicitante_email} onChange={e => set('solicitante_email', e.target.value)} placeholder="email@exemplo.com" />
        </Field>
        <Field label="Endereço Completo" className="md:col-span-2">
          <Input value={form.solicitante_endereco} onChange={e => set('solicitante_endereco', e.target.value)} placeholder="Rua, número, complemento, cidade - UF" />
        </Field>
      </Grid>
    </div>
  );
};
