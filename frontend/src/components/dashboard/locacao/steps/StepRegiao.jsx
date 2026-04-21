// @module locacao/steps/StepRegiao — Step 4: Caracterização da Região para Locação
import React from 'react';
import { Field, Input, Textarea, Grid } from '../shared/primitives';

export const StepRegiao = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">4. Caracterização da Região</h3>
      <Grid cols={2}>
        <Field label="Infraestrutura Urbana" className="md:col-span-2">
          <Textarea value={form.regiao_infraestrutura} onChange={e => set('regiao_infraestrutura', e.target.value)} placeholder="Pavimentação, iluminação, saneamento..." />
        </Field>
        <Field label="Serviços Públicos" className="md:col-span-2">
          <Textarea value={form.regiao_servicos_publicos} onChange={e => set('regiao_servicos_publicos', e.target.value)} placeholder="Transporte, saúde, educação..." />
        </Field>
        <Field label="Uso Predominante">
          <Input value={form.regiao_uso_predominante} onChange={e => set('regiao_uso_predominante', e.target.value)} placeholder="Residencial, Comercial, Misto..." />
        </Field>
        <Field label="Padrão Construtivo da Região">
          <Input value={form.regiao_padrao_construtivo} onChange={e => set('regiao_padrao_construtivo', e.target.value)} placeholder="Alto, Médio, Simples..." />
        </Field>
        <Field label="Tendência de Mercado">
          <Input value={form.regiao_tendencia_mercado} onChange={e => set('regiao_tendencia_mercado', e.target.value)} placeholder="Valorização, estabilidade, desvalorização..." />
        </Field>
        <Field label="Zoneamento">
          <Input value={form.zoneamento} onChange={e => set('zoneamento', e.target.value)} placeholder="ZR1, ZC2..." />
        </Field>
        <Field label="Observações da Região" className="md:col-span-2">
          <Textarea value={form.regiao_observacoes} onChange={e => set('regiao_observacoes', e.target.value)} rows={4} />
        </Field>
      </Grid>
    </div>
  );
};
