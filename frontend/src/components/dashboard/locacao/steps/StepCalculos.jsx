// @module locacao/steps/StepCalculos — Step 6: Cálculos e Metodologia da Locação
import React from 'react';
import { Field, Input, Textarea, Select, Grid } from '../shared/primitives';
import { fmtCurrency } from '../locacaoHelpers';

export const StepCalculos = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const calcularEstatisticas = () => {
    const samples = form.market_samples || [];
    const valores = samples.map(s => s.valor_por_m2).filter(v => v > 0);
    if (valores.length === 0) return;
    const media = valores.reduce((a, b) => a + b, 0) / valores.length;
    const sorted = [...valores].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const mediana = sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    const desvio = Math.sqrt(valores.reduce((a, b) => a + Math.pow(b - media, 2), 0) / valores.length);
    const cv = (desvio / media) * 100;
    setForm(f => ({
      ...f,
      calc_media: parseFloat(media.toFixed(2)),
      calc_mediana: parseFloat(mediana.toFixed(2)),
      calc_desvio_padrao: parseFloat(desvio.toFixed(2)),
      calc_coef_variacao: parseFloat(cv.toFixed(2)),
    }));
  };

  // Cálculo do valor final: valor_m2 × area_a_considerar
  const calcularValorFinal = () => {
    const area = parseFloat(form.imovel_area_a_considerar) || 0;
    const vm2  = parseFloat(form.valor_m2) || 0;
    if (area > 0 && vm2 > 0) {
      set('valor_locacao_estimado', parseFloat((vm2 * area).toFixed(2)));
    }
  };

  const temConfiguracao =
    (parseFloat(form.imovel_area_a_considerar) || 0) > 0 &&
    (parseFloat(form.valor_m2) || 0) > 0;

  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">6. Cálculos e Metodologia</h3>
      <Field label="Metodologia Aplicada">
        <Input value={form.methodology} onChange={e => set('methodology', e.target.value)} />
      </Field>
      <Field label="Justificativa da Metodologia">
        <Textarea value={form.methodology_justification} onChange={e => set('methodology_justification', e.target.value)} rows={3} />
      </Field>

      <div className="flex flex-wrap justify-end gap-3">
        <button
          onClick={calcularEstatisticas}
          className="text-sm bg-emerald-900 text-white px-4 py-2 rounded-xl hover:bg-emerald-800 transition"
        >
          Calcular Estatísticas das Amostras
        </button>
        {temConfiguracao && (
          <button
            onClick={calcularValorFinal}
            className="text-sm bg-amber-700 text-white px-4 py-2 rounded-xl hover:bg-amber-600 transition"
          >
            Calcular Valor Final pelas Áreas
          </button>
        )}
      </div>

      {/* Resumo do cálculo */}
      {temConfiguracao && (() => {
        const area  = parseFloat(form.imovel_area_a_considerar) || 0;
        const vm2   = parseFloat(form.valor_m2) || 0;
        const total = vm2 * area;
        const fmtBRL = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);
        return (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm space-y-2">
            <p className="font-semibold text-amber-900">Configuração do cálculo:</p>
            <p className="text-gray-700 text-xs">
              {fmtBRL(vm2)}/m² × {area} m²
              {' = '}
              <strong>{fmtBRL(total)}</strong>
            </p>
            {total > 0 && (
              <p className="font-semibold text-amber-800 border-t border-amber-200 pt-2 mt-1">
                Valor estimado: {fmtBRL(total)}
              </p>
            )}
          </div>
        );
      })()}

      <Grid cols={2}>
        <Field label="Média R$/m²">
          <Input type="number" value={form.calc_media} onChange={e => set('calc_media', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Mediana R$/m²">
          <Input type="number" value={form.calc_mediana} onChange={e => set('calc_mediana', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Desvio Padrão">
          <Input type="number" value={form.calc_desvio_padrao} onChange={e => set('calc_desvio_padrao', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Coeficiente de Variação (%)">
          <Input type="number" value={form.calc_coef_variacao} onChange={e => set('calc_coef_variacao', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Grau de Fundamentação (NBR 14653)">
          <Select
            value={form.calc_grau_fundamentacao}
            onChange={e => set('calc_grau_fundamentacao', e.target.value)}
            options={[{ value: 'I', label: 'Grau I' }, { value: 'II', label: 'Grau II' }, { value: 'III', label: 'Grau III' }]}
            placeholder="Selecione..."
          />
        </Field>
        <Field label="Fatores de Homogeneização">
          <Input value={form.calc_fatores_homogeneizacao} onChange={e => set('calc_fatores_homogeneizacao', e.target.value)} placeholder="Fator localização, padrão, área..." />
        </Field>
        <Field label="Observações dos Cálculos" className="md:col-span-2">
          <Textarea rows={3} value={form.calc_observacoes} onChange={e => set('calc_observacoes', e.target.value)} />
        </Field>
      </Grid>
    </div>
  );
};
