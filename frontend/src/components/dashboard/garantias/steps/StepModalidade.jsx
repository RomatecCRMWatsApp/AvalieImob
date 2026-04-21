// @module Garantias/steps/StepModalidade — Bancário: Step 1 — Modalidade Financeira e Instituição

import React from 'react';
import {
  AlertaCRECI, AlertaSFH,
  SectionTitle, Field, Input, Select,
  MODALIDADE_OPTIONS, BANCOS_OPTIONS, isSfhFgts,
} from './shared.js';

const StepModalidade = ({ form, set }) => (
  <div className="space-y-6">
    <AlertaCRECI />
    <SectionTitle>Modalidade Financeira</SectionTitle>
    <div className="grid md:grid-cols-2 gap-3">
      {MODALIDADE_OPTIONS.map(({ value, label, desc }) => (
        <button
          key={value}
          type="button"
          onClick={() => {
            set('modalidade_financeira', value);
            if (value === 'sfh_fgts') set('ltv_maximo', 80);
            if (value === 'sfh_fgts' || value === 'sfi_bancario' || value === 'alienacao_fiduciaria') {
              set('validade_laudo_meses', 12);
            }
          }}
          className={`flex flex-col items-start gap-1 p-4 rounded-xl border-2 text-left transition ${
            form.modalidade_financeira === value
              ? 'border-emerald-700 bg-emerald-50'
              : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
          }`}
        >
          <div className="font-semibold text-sm text-gray-900">{label}</div>
          <div className="text-[11px] text-gray-500 leading-tight">{desc}</div>
        </button>
      ))}
    </div>

    {isSfhFgts(form) && <AlertaSFH />}

    <SectionTitle>Instituição Financeira Credora</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Instituição Financeira" required>
        <Select value={form.instituicao_financeira} onChange={(e) => set('instituicao_financeira', e.target.value)}>
          <option value="">Selecionar banco...</option>
          {BANCOS_OPTIONS.map((b) => <option key={b} value={b}>{b}</option>)}
        </Select>
      </Field>
      <Field label="Valor do Financiamento (R$)" required>
        <Input
          type="number"
          value={form.valor_financiamento}
          onChange={(e) => set('valor_financiamento', parseFloat(e.target.value) || 0)}
        />
      </Field>
      <Field label="LTV Máximo (%)" hint="80% para SFH | 90% SFI conforme CMN 4.676/2018">
        <Input
          type="number"
          value={form.ltv_maximo}
          onChange={(e) => set('ltv_maximo', parseFloat(e.target.value) || 0)}
        />
      </Field>
      <Field label="Prazo do Financiamento (meses)">
        <Input
          type="number"
          value={form.prazo_financiamento_meses}
          onChange={(e) => set('prazo_financiamento_meses', parseInt(e.target.value) || 0)}
        />
      </Field>
    </div>

    <SectionTitle>Tipo e Finalidade do Bem</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Tipo de Bem em Garantia">
        <Select value={form.tipo_garantia} onChange={(e) => set('tipo_garantia', e.target.value)}>
          <option value="imovel_urbano">Imóvel Urbano</option>
          <option value="imovel_rural">Imóvel Rural</option>
          <option value="apartamento">Apartamento</option>
          <option value="casa">Casa</option>
          <option value="comercial">Imóvel Comercial</option>
          <option value="terreno">Terreno</option>
        </Select>
      </Field>
      <Field label="Finalidade do Crédito">
        <Select value={form.finalidade_credito} onChange={(e) => set('finalidade_credito', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="aquisicao">Aquisição</option>
          <option value="reforma">Reforma / Ampliação</option>
          <option value="construcao">Construção</option>
          <option value="refinanciamento">Refinanciamento</option>
        </Select>
      </Field>
    </div>
  </div>
);

export default StepModalidade;
