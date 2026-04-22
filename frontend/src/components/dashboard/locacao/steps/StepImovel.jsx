// @module locacao/steps/StepImovel — Step 3: Identificação do Imóvel para Locação
import React from 'react';
import { Field, Input, Textarea, Select, Grid } from '../shared/primitives';
import { IMOVEL_TIPO_OPTIONS, CONSERVACAO_OPTIONS, PADRAO_OPTIONS } from '../locacaoHelpers';

const fmt = (v) =>
  v > 0
    ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v)
    : '';

export const StepImovel = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const area   = parseFloat(form.imovel_area_a_considerar) || 0;
  const vm2    = parseFloat(form.valor_m2) || 0;
  const total  = area > 0 && vm2 > 0 ? area * vm2 : 0;

  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">3. Identificação do Imóvel</h3>
      <Grid cols={2}>
        <Field label="Endereço" className="md:col-span-2">
          <Input value={form.imovel_endereco} onChange={e => set('imovel_endereco', e.target.value)} placeholder="Rua, número, complemento" />
        </Field>
        <Field label="Bairro">
          <Input value={form.imovel_bairro} onChange={e => set('imovel_bairro', e.target.value)} />
        </Field>
        <Field label="Cidade">
          <Input value={form.imovel_cidade} onChange={e => set('imovel_cidade', e.target.value)} />
        </Field>
        <Field label="Estado">
          <Input value={form.imovel_estado} onChange={e => set('imovel_estado', e.target.value)} placeholder="UF" maxLength={2} />
        </Field>
        <Field label="CEP">
          <Input value={form.imovel_cep} onChange={e => set('imovel_cep', e.target.value)} placeholder="00000-000" />
        </Field>
        <Field label="Matrícula">
          <Input value={form.imovel_matricula} onChange={e => set('imovel_matricula', e.target.value)} />
        </Field>
        <Field label="Cartório de Registro">
          <Input value={form.imovel_cartorio} onChange={e => set('imovel_cartorio', e.target.value)} />
        </Field>
        <Field label="Tipo do Imóvel" className="md:col-span-2">
          <Select
            value={form.imovel_tipo}
            onChange={e => set('imovel_tipo', e.target.value)}
            options={IMOVEL_TIPO_OPTIONS}
            placeholder="Selecione..."
          />
        </Field>
        <Field label="Área do Terreno (m²) — referência">
          <Input type="number" step="0.01" value={form.imovel_area_terreno} onChange={e => set('imovel_area_terreno', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Área Construída (m²) — referência">
          <Input type="number" step="0.01" value={form.imovel_area_construida} onChange={e => set('imovel_area_construida', parseFloat(e.target.value) || 0)} />
        </Field>
      </Grid>

      {/* ── Seção de cálculo simplificada ─────────────────────────────── */}
      <div className="border border-emerald-300 rounded-xl p-5 bg-emerald-50 space-y-4">
        <p className="text-sm font-semibold text-emerald-900">Cálculo do Valor de Locação</p>
        <p className="text-xs text-emerald-700">
          Informe a área a ser considerada no cálculo e o valor unitário (R$/m²).
          O valor final será: <strong>Área considerada × R$/m²</strong>.
        </p>

        <Grid cols={2}>
          <Field label="Área a ser considerada no cálculo (m²) *" full>
            <Input
              type="number"
              step="0.01"
              required
              value={form.imovel_area_a_considerar ?? ''}
              onChange={e => set('imovel_area_a_considerar', e.target.value === '' ? null : parseFloat(e.target.value))}
              placeholder="Ex: 150 — pode ser igual ao terreno, construída ou outro valor"
              className="border-emerald-400 focus:ring-emerald-600"
            />
            <p className="mt-1 text-xs text-gray-500">
              Pode ser igual à área do terreno ({form.imovel_area_terreno || 0} m²), à área construída ({form.imovel_area_construida || 0} m²) ou outro valor definido pelo avaliador.
            </p>
          </Field>
          <Field label="Valor unitário R$/m² adotado *">
            <Input
              type="number"
              step="0.01"
              required
              value={form.valor_m2 ?? ''}
              onChange={e => set('valor_m2', e.target.value === '' ? null : parseFloat(e.target.value))}
              placeholder="Ex: 855,77"
              className="border-emerald-400 focus:ring-emerald-600"
            />
          </Field>
        </Grid>

        {/* Pré-visualização do cálculo */}
        {total > 0 && (
          <div className="mt-2 p-3 bg-white rounded-lg border border-emerald-200 text-xs text-gray-700 space-y-1">
            <p className="font-semibold text-emerald-800 mb-1">Pré-visualização:</p>
            <p>
              {fmt(vm2)}/m² × {area} m²
              {' = '}
              <strong className="text-emerald-700">{fmt(total)}</strong>
            </p>
          </div>
        )}
      </div>

      <Grid cols={2}>
        <Field label="Idade Aparente (anos)">
          <Input type="number" value={form.imovel_idade} onChange={e => set('imovel_idade', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Nº de Quartos">
          <Input type="number" min={0} value={form.imovel_num_quartos} onChange={e => set('imovel_num_quartos', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Estado de Conservação">
          <Select value={form.imovel_estado_conservacao} onChange={e => set('imovel_estado_conservacao', e.target.value)} options={CONSERVACAO_OPTIONS} placeholder="Selecione..." />
        </Field>
        <Field label="Padrão de Acabamento">
          <Select value={form.imovel_padrao_acabamento} onChange={e => set('imovel_padrao_acabamento', e.target.value)} options={PADRAO_OPTIONS} placeholder="Selecione..." />
        </Field>
        <Field label="Nº de Banheiros">
          <Input type="number" min={0} value={form.imovel_num_banheiros} onChange={e => set('imovel_num_banheiros', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Vagas de Garagem">
          <Input type="number" min={0} value={form.imovel_num_vagas} onChange={e => set('imovel_num_vagas', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Piscina" className="flex items-center gap-2 pt-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.imovel_piscina} onChange={e => set('imovel_piscina', e.target.checked)} className="w-4 h-4 accent-emerald-700" />
            <span className="text-sm text-gray-700">Possui piscina</span>
          </label>
        </Field>
        <Field label="Características Adicionais" className="md:col-span-2">
          <Textarea value={form.imovel_caracteristicas} onChange={e => set('imovel_caracteristicas', e.target.value)} placeholder="Churrasqueira, área de lazer, varanda..." />
        </Field>
      </Grid>
    </div>
  );
};
