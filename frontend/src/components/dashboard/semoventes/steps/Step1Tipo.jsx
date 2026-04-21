// @module Semoventes/steps/Step1Tipo — Step 1 — Espécie Animal, Operação Bancária e Status

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { SectionTitle, Field, Inp, Sel, TIPO_OPTIONS, MODALIDADE_OPTIONS } from './shared.js';

const Step1Tipo = ({ form, set }) => (
  <div className="space-y-6">
    {/* Alerta CRMV */}
    <div className="flex items-start gap-3 bg-red-50 border-2 border-red-300 rounded-xl px-4 py-4">
      <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <div>
        <div className="font-bold text-red-800 text-sm">ALERTA LEGAL — CRMV OBRIGATÓRIO</div>
        <p className="text-sm text-red-700 mt-1">
          Avaliação de semoventes para penhor rural exige obrigatoriamente <strong>Médico Veterinário com CRMV ativo</strong>.
          Laudo sem CRMV/CZO é <strong>nulo</strong> para fins bancários.
          (CFMV Res. 722/2002 · Dec.-Lei 167/1967 arts. 9-19 · MCR BACEN Cap. 6)
        </p>
      </div>
    </div>

    <SectionTitle>Espécie Animal</SectionTitle>
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {TIPO_OPTIONS.map(({ value, label, desc, icon: Icon }) => (
        <button
          key={value}
          type="button"
          onClick={() => set('tipo_semovente', value)}
          className={`flex flex-col items-start gap-2 p-4 rounded-xl border-2 text-left transition ${
            form.tipo_semovente === value
              ? 'border-emerald-700 bg-emerald-50'
              : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
          }`}
        >
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${form.tipo_semovente === value ? 'bg-emerald-900' : 'bg-gray-100'}`}>
            <Icon className={`w-5 h-5 ${form.tipo_semovente === value ? 'text-white' : 'text-gray-600'}`} />
          </div>
          <div>
            <div className="font-semibold text-sm text-gray-900">{label}</div>
            <div className="text-[11px] text-gray-500 leading-tight mt-0.5">{desc}</div>
          </div>
        </button>
      ))}
    </div>

    <SectionTitle>Operação Bancária</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Instituição Financeira" required>
        <Inp value={form.instituicao_financeira} onChange={(e) => set('instituicao_financeira', e.target.value)} placeholder="Ex.: Banco do Brasil S.A." />
      </Field>
      <Field label="Modalidade de Crédito" required>
        <Sel value={form.modalidade_credito} onChange={(e) => set('modalidade_credito', e.target.value)}>
          {MODALIDADE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </Sel>
      </Field>
      <Field label="Valor do Crédito (R$)">
        <Inp type="number" value={form.valor_credito} onChange={(e) => set('valor_credito', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Status">
        <Sel value={form.status} onChange={(e) => set('status', e.target.value)}>
          <option value="rascunho">Rascunho</option>
          <option value="em_andamento">Em Andamento</option>
          <option value="concluido">Concluído</option>
        </Sel>
      </Field>
    </div>
  </div>
);

export default Step1Tipo;
