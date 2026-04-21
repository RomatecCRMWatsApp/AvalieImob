// @module ptam/steps/StepResultado — Step 11: Resultado da Avaliação (valor unitário, total, intervalo, validade)
import React from 'react';
import { Input } from '../../../ui/input';
import { Field, SectionHeader, StatBox } from '../shared/primitives';

const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export const StepResultado = ({ form, setForm }) => {
  const val = Number(form.resultado_valor_total || 0);
  const inf = val * 0.85;
  const sup = val * 1.15;
  const area = Number(form.imovel_area_construida || form.imovel_area_terreno || form.property_area_sqm || 0);
  const vuCalc = area > 0 ? val / area : 0;

  return (
    <div>
      <SectionHeader
        title="11. Resultado da Avaliação"
        subtitle="Preencha ou confirme o valor de avaliação do imóvel."
      />

      {val > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatBox label="Valor Unitário (R$/m²)" value={fmtBRL(form.resultado_valor_unitario || vuCalc)} />
          <StatBox label="Valor Total" value={fmtBRL(val)} />
          <StatBox label="Área de Referência (m²)" value={area || '—'} unit="m²" />
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <Field label="Valor Unitário (R$/m²)">
          <Input
            type="number" step="0.01"
            value={form.resultado_valor_unitario}
            onChange={(e) => setForm({ ...form, resultado_valor_unitario: Number(e.target.value) })}
            placeholder="0,00"
          />
        </Field>
        <Field label="Valor Total (R$)">
          <Input
            type="number" step="0.01"
            value={form.resultado_valor_total}
            onChange={(e) => {
              const v = Number(e.target.value);
              setForm({ ...form, resultado_valor_total: v, total_indemnity: v });
            }}
            placeholder="0,00"
          />
        </Field>
        <Field label="Intervalo Inferior (R$)">
          <Input
            type="number" step="0.01"
            value={form.resultado_intervalo_inf || inf}
            onChange={(e) => setForm({ ...form, resultado_intervalo_inf: Number(e.target.value) })}
            placeholder="R$ automático (−15%)"
          />
        </Field>
        <Field label="Intervalo Superior (R$)">
          <Input
            type="number" step="0.01"
            value={form.resultado_intervalo_sup || sup}
            onChange={(e) => setForm({ ...form, resultado_intervalo_sup: Number(e.target.value) })}
            placeholder="R$ automático (+15%)"
          />
        </Field>
        <Field label="Campo de Arbítrio — mínimo (R$)">
          <Input
            type="number" step="0.01"
            value={form.campo_arbitrio_min || inf}
            onChange={(e) => setForm({ ...form, campo_arbitrio_min: Number(e.target.value) })}
            placeholder="−15% do valor"
          />
        </Field>
        <Field label="Campo de Arbítrio — máximo (R$)">
          <Input
            type="number" step="0.01"
            value={form.campo_arbitrio_max || sup}
            onChange={(e) => setForm({ ...form, campo_arbitrio_max: Number(e.target.value) })}
            placeholder="+15% do valor"
          />
        </Field>
        <Field label="Grau de Precisão (NBR 14653-1 item 9)">
          <select
            value={form.grau_precisao || 'I'}
            onChange={(e) => setForm({ ...form, grau_precisao: e.target.value })}
            className="w-full h-9 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="I">Grau I</option>
            <option value="II">Grau II</option>
            <option value="III">Grau III</option>
          </select>
        </Field>
        <Field label="Prazo de validade do laudo (meses)">
          <Input
            type="number" min="1" max="24"
            value={form.prazo_validade_meses || 6}
            onChange={(e) => setForm({ ...form, prazo_validade_meses: Number(e.target.value) })}
          />
        </Field>
        <Field label="Data de referência da avaliação">
          <Input
            type="date"
            value={form.resultado_data_referencia || ''}
            onChange={(e) => setForm({ ...form, resultado_data_referencia: e.target.value })}
          />
        </Field>
        <Field label="Validade do laudo (data)">
          <Input
            type="date"
            value={form.resultado_prazo_validade || ''}
            onChange={(e) => setForm({ ...form, resultado_prazo_validade: e.target.value })}
          />
        </Field>
        <Field label="Valor total por extenso" full>
          <Input
            value={form.total_indemnity_words || ''}
            onChange={(e) => setForm({ ...form, total_indemnity_words: e.target.value })}
            placeholder="Ex: Um milhão, duzentos e cinquenta mil reais"
          />
        </Field>
      </div>

      {val > 0 && (
        <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
          <div className="text-xs text-emerald-700 uppercase tracking-wider mb-2">Intervalo de valores sugerido (±15%)</div>
          <div className="flex items-center gap-6 text-sm text-emerald-900">
            <span className="font-medium">Mínimo: {fmtBRL(inf)}</span>
            <span className="text-gray-400">•</span>
            <span className="font-bold text-lg">{fmtBRL(val)}</span>
            <span className="text-gray-400">•</span>
            <span className="font-medium">Máximo: {fmtBRL(sup)}</span>
          </div>
        </div>
      )}
    </div>
  );
};
