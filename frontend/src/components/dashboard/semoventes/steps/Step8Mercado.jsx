// @module Semoventes/steps/Step8Mercado — Step 8 — Cotações de Mercado

import React from 'react';
import { SectionTitle, Field, Inp } from './shared.js';

const Step8Mercado = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Cotações de Mercado</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Cotação da Arroba (@) — R$/@ boi gordo">
        <Inp type="number" value={form.cotacao_arroba_valor} onChange={(e) => set('cotacao_arroba_valor', parseFloat(e.target.value) || 0)} placeholder="Ex.: 295.50" />
      </Field>
      <Field label="Data de Referência da Cotação">
        <Inp type="date" value={form.cotacao_arroba_data} onChange={(e) => set('cotacao_arroba_data', e.target.value)} />
      </Field>
      <Field label="Fonte da Cotação" hint="B3, CEPEA/ESALQ, SCOT Consultoria, bolsa local">
        <Inp value={form.cotacao_fonte} onChange={(e) => set('cotacao_fonte', e.target.value)} placeholder="Ex.: CEPEA/ESALQ — 19/04/2026" />
      </Field>
      <Field label="Cotação Bezerro (R$/cabeça)">
        <Inp type="number" value={form.cotacao_bezerro} onChange={(e) => set('cotacao_bezerro', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Cotação Vaca (R$/cabeça)">
        <Inp type="number" value={form.cotacao_vaca} onChange={(e) => set('cotacao_vaca', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Cotação Touro PO (R$/cabeça)">
        <Inp type="number" value={form.cotacao_touro_po} onChange={(e) => set('cotacao_touro_po', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>
  </div>
);

export default Step8Mercado;
