// @module locacao/steps/StepResultado — Step 10: Resultado — Valor de Locação
import React from 'react';
import { Field, Input, Textarea, Select, Grid } from '../shared/primitives';
import { fmtCurrency } from '../locacaoHelpers';

export const StepResultado = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">10. Resultado — Valor de Locação</h3>

      {form.valor_locacao_estimado && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
          <p className="text-xs text-emerald-600 uppercase tracking-wider font-semibold mb-1">Valor Mensal Estimado</p>
          <p className="text-3xl font-bold text-emerald-900">{fmtCurrency(form.valor_locacao_estimado)}<span className="text-base font-medium text-emerald-600">/mês</span></p>
          {form.valor_locacao_por_extenso && <p className="text-xs text-emerald-700 mt-1">({form.valor_locacao_por_extenso})</p>}
        </div>
      )}

      <Grid cols={3}>
        <Field label="Valor Mensal Estimado (R$)" className="md:col-span-3">
          <Input
            type="number"
            value={form.valor_locacao_estimado ?? ''}
            onChange={e => set('valor_locacao_estimado', e.target.value ? parseFloat(e.target.value) : null)}
            placeholder="0,00"
            className="text-lg font-semibold"
          />
        </Field>
        <Field label="Valor Mínimo (R$)">
          <Input type="number" value={form.valor_locacao_minimo ?? ''} onChange={e => set('valor_locacao_minimo', e.target.value ? parseFloat(e.target.value) : null)} />
        </Field>
        <Field label="Valor Máximo (R$)">
          <Input type="number" value={form.valor_locacao_maximo ?? ''} onChange={e => set('valor_locacao_maximo', e.target.value ? parseFloat(e.target.value) : null)} />
        </Field>
        <Field label="Valor por Extenso" className="md:col-span-3">
          <Input value={form.valor_locacao_por_extenso} onChange={e => set('valor_locacao_por_extenso', e.target.value)} placeholder="Três mil reais por mês" />
        </Field>
        <Field label="Data de Referência">
          <Input type="date" value={form.resultado_data_referencia} onChange={e => set('resultado_data_referencia', e.target.value)} />
        </Field>
        <Field label="Prazo de Validade do Parecer" className="md:col-span-2">
          <Input value={form.resultado_prazo_validade} onChange={e => set('resultado_prazo_validade', e.target.value)} placeholder="6 meses a partir da data de emissão" />
        </Field>
      </Grid>

      <Field label="Conclusão / Parecer Técnico">
        <Textarea rows={5} value={form.conclusion_text} onChange={e => set('conclusion_text', e.target.value)} placeholder="Com base na pesquisa de mercado realizada, conclui-se que o valor de locação do imóvel avaliado é..." />
      </Field>

      <Grid cols={2}>
        <Field label="Pressupostos">
          <Textarea rows={3} value={form.consideracoes_pressupostos} onChange={e => set('consideracoes_pressupostos', e.target.value)} placeholder="Este parecer foi elaborado com base em..." />
        </Field>
        <Field label="Ressalvas e Limitações">
          <Textarea rows={3} value={form.consideracoes_ressalvas} onChange={e => set('consideracoes_ressalvas', e.target.value)} placeholder="Este parecer não considera..." />
        </Field>
      </Grid>

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">Base Legal</p>
        <p>{form.base_legal_locacao || 'Lei 8.245/1991 — Art. 565 a 578 do Código Civil'}</p>
        <p className="mt-1 text-blue-600">NBR 14653-1 e 14653-2 — ABNT</p>
      </div>

      <div className="flex items-center gap-3">
        <Field label="Status do Parecer" className="flex-1">
          <Select
            value={form.status}
            onChange={e => set('status', e.target.value)}
            options={[
              { value: 'Rascunho', label: 'Rascunho' },
              { value: 'Em revisão', label: 'Em revisão' },
              { value: 'Emitido', label: 'Emitido' },
            ]}
          />
        </Field>
      </div>
    </div>
  );
};
