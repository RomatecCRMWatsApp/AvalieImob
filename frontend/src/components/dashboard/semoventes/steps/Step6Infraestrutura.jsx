// @module Semoventes/steps/Step6Infraestrutura — Step 6 — Infraestrutura da Propriedade

import React from 'react';
import { SectionTitle, Field, Inp, Sel, Txta } from './shared.js';

const Step6Infraestrutura = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Infraestrutura da Propriedade</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Capacidade de Suporte (UA/ha)">
        <Inp type="number" value={form.capacidade_suporte_ua_ha} onChange={(e) => set('capacidade_suporte_ua_ha', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Disponibilidade de Água">
        <Sel value={form.disponibilidade_agua} onChange={(e) => set('disponibilidade_agua', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="abundante">Abundante (rios, represas, poços artesianos)</option>
          <option value="suficiente">Suficiente</option>
          <option value="limitada">Limitada (dependente de chuvas)</option>
          <option value="critica">Crítica</option>
        </Sel>
      </Field>
      <Field label="Instalações Existentes" hint="Curral, balança, brete, embarcadouro, etc.">
        <Txta
          value={form.instalacoes}
          onChange={(e) => set('instalacoes', e.target.value)}
          rows={3}
          placeholder="Descreva as instalações presentes na propriedade..."
        />
      </Field>
      <Field label="Estado de Conservação das Instalações">
        <Sel value={form.estado_conservacao_instalacoes} onChange={(e) => set('estado_conservacao_instalacoes', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="otimo">Ótimo</option>
          <option value="bom">Bom</option>
          <option value="regular">Regular</option>
          <option value="precario">Precário</option>
        </Sel>
      </Field>
      <Field label="Capacidade de Confinamento (cabeças)">
        <Inp type="number" value={form.capacidade_confinamento} onChange={(e) => set('capacidade_confinamento', parseInt(e.target.value) || 0)} />
      </Field>
    </div>
  </div>
);

export default Step6Infraestrutura;
