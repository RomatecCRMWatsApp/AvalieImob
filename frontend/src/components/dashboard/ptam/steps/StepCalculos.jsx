// @module ptam/steps/StepCalculos — Step 8: Cálculos e Tratamento Estatístico (estatísticas automáticas das amostras)
import React, { useEffect } from 'react';
import { Textarea } from '../../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { SectionHeader, StatBox, AiButton } from '../shared/primitives';
import { computeStats } from '../ptamHelpers';

const FUNDAMENTACAO_TEXTS = {
  I: {
    title: 'Grau I — Fundamentação Mínima',
    text: 'Exige no mínimo 3 dados de mercado, com identificação dos fatores relevantes. Permite tratamento por fatores ou inferência estatística simplificada. Aplicável quando há limitação de dados disponíveis na região.',
  },
  II: {
    title: 'Grau II — Fundamentação Intermediária',
    text: 'Exige no mínimo 6 dados de mercado verificados, com apresentação de estatísticas descritivas. Requer tratamento por fatores com justificativa ou modelo de regressão com significância mínima de 80%. Indicado para avaliações de maior responsabilidade.',
  },
  III: {
    title: 'Grau III — Fundamentação Máxima',
    text: 'Exige no mínimo 10 dados de mercado verificados e visitados. Requer modelo de regressão com nível de significância de 90% ou superior, com análise de micronumerosidade. Obrigatório para desapropriações, perícias judiciais e financiamentos de grande porte.',
  },
};

export const StepCalculos = ({ form, setForm, onAi, aiLoading }) => {
  const samples = form.market_samples || [];
  const auto = computeStats(samples);

  useEffect(() => {
    if (samples.length > 0) {
      setForm((f) => ({
        ...f,
        calc_media: auto.media,
        calc_mediana: auto.mediana,
        calc_desvio_padrao: auto.desvio_padrao,
        calc_coef_variacao: auto.coef_variacao,
      }));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [samples.length]);

  const validSamples = samples.filter((s) => (s.value_per_sqm || 0) > 0);
  const cvClass = auto.coef_variacao <= 15 ? 'text-emerald-700' : auto.coef_variacao <= 30 ? 'text-amber-600' : 'text-red-600';

  return (
    <div>
      <SectionHeader
        title="8. Cálculos e Tratamento Estatístico"
        subtitle="Estatísticas calculadas automaticamente com base nas amostras coletadas."
      />

      {validSamples.length === 0 ? (
        <div className="p-6 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm mb-6">
          Nenhuma amostra com área e valor informados. Volte ao passo 6 e preencha as amostras.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <StatBox label="Média R$/m²" value={auto.media} unit={`${validSamples.length} amostras`} />
            <StatBox label="Mediana R$/m²" value={auto.mediana} />
            <StatBox label="Desvio Padrão" value={auto.desvio_padrao} />
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-center">
              <div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">CV (%)</div>
              <div className={`text-2xl font-bold ${cvClass}`}>
                {auto.coef_variacao.toFixed(2)}%
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {auto.coef_variacao <= 15 ? 'Homogêneo' : auto.coef_variacao <= 30 ? 'Heterogêneo' : 'Muito heterogêneo'}
              </div>
            </div>
          </div>

          <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 mb-6">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500 uppercase">
                <tr>
                  <th className="text-left py-1.5 px-2">#</th>
                  <th className="text-left py-1.5 px-2">Endereço / Bairro</th>
                  <th className="text-right py-1.5 px-2">Área (m²)</th>
                  <th className="text-right py-1.5 px-2">Valor (R$)</th>
                  <th className="text-right py-1.5 px-2">R$/m²</th>
                </tr>
              </thead>
              <tbody>
                {validSamples.map((s, i) => (
                  <tr key={s._key || i} className="border-t border-gray-100">
                    <td className="py-1.5 px-2 text-gray-400">{i + 1}</td>
                    <td className="py-1.5 px-2">{s.address || s.neighborhood || '—'}</td>
                    <td className="py-1.5 px-2 text-right">{Number(s.area || 0).toLocaleString('pt-BR')}</td>
                    <td className="py-1.5 px-2 text-right">{Number(s.value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td>
                    <td className="py-1.5 px-2 text-right font-semibold text-emerald-800">
                      {Number(s.value_per_sqm || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Grau de Fundamentação (NBR 14.653-2)</label>
          <div className="flex gap-4 items-start">
            <div className="w-56 shrink-0">
              <Select value={form.calc_grau_fundamentacao} onValueChange={(v) => setForm({ ...form, calc_grau_fundamentacao: v })}>
                <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="I">Grau I</SelectItem>
                  <SelectItem value="II">Grau II</SelectItem>
                  <SelectItem value="III">Grau III</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.calc_grau_fundamentacao && (() => {
              const info = FUNDAMENTACAO_TEXTS[form.calc_grau_fundamentacao];
              return info ? (
                <div className="flex-1 flex gap-2.5 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
                  <svg className="w-4 h-4 mt-0.5 text-amber-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <p className="text-xs font-semibold text-amber-800 mb-0.5">{info.title}</p>
                    <p className="text-xs text-amber-700 leading-relaxed">{info.text}</p>
                  </div>
                </div>
              ) : null;
            })()}
          </div>
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Fatores de Homogeneização aplicados</label>
          <Textarea
            value={form.calc_fatores_homogeneizacao || ''}
            onChange={(e) => setForm({ ...form, calc_fatores_homogeneizacao: e.target.value })}
            rows={3}
            placeholder="Descreva os fatores aplicados: localização, área, padrão construtivo, etc."
          />
          <div className="mt-1 flex justify-end">
            <AiButton onClick={() => onAi('calc_fatores_homogeneizacao')} loading={aiLoading === 'calc_fatores_homogeneizacao'} />
          </div>
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Observações sobre os cálculos</label>
          <Textarea
            value={form.calc_observacoes || ''}
            onChange={(e) => setForm({ ...form, calc_observacoes: e.target.value })}
            rows={3}
            placeholder="Outliers descartados, ajustes realizados, limitações dos dados..."
          />
          <div className="mt-1 flex justify-end">
            <AiButton onClick={() => onAi('calc_observacoes')} loading={aiLoading === 'calc_observacoes'} />
          </div>
        </div>
      </div>
    </div>
  );
};
