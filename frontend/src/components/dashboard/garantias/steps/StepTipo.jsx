// @module Garantias/steps/StepTipo — Rural: Step 1 — Tipo de Garantia, Modalidade e Finalidade

import React from 'react';
import { SectionTitle, TIPO_OPTIONS, MODALIDADE_OPTIONS, FINALIDADE_OPTIONS, isBancario } from './shared.js';

const StepTipo = ({ form, set }) => {
  const tipo = form.tipo_garantia;
  return (
    <div className="space-y-6">
      <SectionTitle>Tipo de Garantia</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {TIPO_OPTIONS.map(({ value, label, desc, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => set('tipo_garantia', value)}
            className={`flex flex-col items-start gap-2 p-4 rounded-xl border-2 text-left transition ${
              tipo === value
                ? 'border-emerald-700 bg-emerald-50'
                : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
            }`}
          >
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${tipo === value ? 'bg-emerald-900' : 'bg-gray-100'}`}>
              <Icon className={`w-5 h-5 ${tipo === value ? 'text-white' : 'text-gray-600'}`} />
            </div>
            <div>
              <div className="font-semibold text-sm text-gray-900">{label}</div>
              <div className="text-[11px] text-gray-500 leading-tight mt-0.5">{desc}</div>
            </div>
          </button>
        ))}
      </div>

      <SectionTitle>Modalidade Financeira</SectionTitle>
      <div className="grid md:grid-cols-2 gap-3">
        {MODALIDADE_OPTIONS.map(({ value, label, desc }) => (
          <button
            key={value}
            type="button"
            onClick={() => set('modalidade_financeira', value)}
            className={`flex flex-col items-start gap-1 p-3 rounded-xl border-2 text-left transition ${
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

      <SectionTitle>Finalidade (Crédito Rural / Outros)</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {FINALIDADE_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => set('finalidade', value)}
            className={`px-4 py-2.5 rounded-lg border-2 text-sm font-medium transition ${
              form.finalidade === value
                ? 'border-emerald-700 bg-emerald-50 text-emerald-900'
                : 'border-gray-200 text-gray-700 hover:border-emerald-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {isBancario(form) && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-800">
          Modalidade bancária detectada. Avance pelo wizard para preencher os campos específicos da Res. CMN 4.676/2018.
        </div>
      )}
    </div>
  );
};

export default StepTipo;
