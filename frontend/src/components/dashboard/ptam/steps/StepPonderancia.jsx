// @module ptam/steps/StepPonderancia — Step 8b: Cálculo de Ponderância (filtragem 50%/150% da média)
import React from 'react';
import { Button } from '../../../ui/button';
import { SectionHeader } from '../shared/primitives';

const fmtBrl = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const fmtBrlM2 = (v) =>
  `${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/m²`;

const fmt2 = (v) => Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const StepPonderancia = ({ form, setForm }) => {
  const samples = (form.market_samples || []).filter((s) => Number(s.area || 0) > 0 && Number(s.value || 0) > 0);

  const samplesWithVpm = samples.map((s) => ({
    ...s,
    _vpm: Number(s.area) > 0 ? Number(s.value) / Number(s.area) : 0,
  }));

  const eliminadas = form.ponderancia_eliminadas || [];

  const calcular = () => {
    if (samplesWithVpm.length === 0) return;
    const vpms = samplesWithVpm.map((s) => s._vpm);
    const mediaSimples = vpms.reduce((a, b) => a + b, 0) / vpms.length;
    const limInf = mediaSimples * 0.5;
    const limSup = mediaSimples * 1.5;

    const novasEliminadas = samplesWithVpm
      .map((s, idx) => ({ idx, vpm: s._vpm }))
      .filter(({ vpm }) => vpm < limInf || vpm > limSup)
      .map(({ idx }) => idx);

    const restantes = samplesWithVpm.filter((_, i) => !novasEliminadas.includes(i));
    const mediaFinal =
      restantes.length > 0
        ? restantes.reduce((a, s) => a + s._vpm, 0) / restantes.length
        : 0;

    const area = Number(form.imovel_area_construida || form.imovel_area_terreno || form.property_area_sqm || 0);
    const valorFinal = mediaFinal * area;

    setForm((f) => ({
      ...f,
      ponderancia_media: Math.round(mediaFinal * 100) / 100,
      ponderancia_limite_inf: Math.round(limInf * 100) / 100,
      ponderancia_limite_sup: Math.round(limSup * 100) / 100,
      ponderancia_eliminadas: novasEliminadas,
      ponderancia_valor_final: Math.round(valorFinal * 100) / 100,
    }));
  };

  const usarNoLaudo = () => {
    if (!form.ponderancia_media) return;
    const area = Number(form.imovel_area_construida || form.imovel_area_terreno || form.property_area_sqm || 0);
    const valorFinal = form.ponderancia_valor_final || form.ponderancia_media * area;
    setForm((f) => ({
      ...f,
      resultado_valor_unitario: form.ponderancia_media,
      resultado_valor_total: Math.round(valorFinal * 100) / 100,
      total_indemnity: Math.round(valorFinal * 100) / 100,
    }));
  };

  const area = Number(form.imovel_area_construida || form.imovel_area_terreno || form.property_area_sqm || 0);
  const calculado = form.ponderancia_media != null && form.ponderancia_media > 0;
  const restantesCount = samplesWithVpm.length - eliminadas.length;

  return (
    <div>
      <SectionHeader
        title="8b. Cálculo de Ponderância"
        subtitle="Filtra amostras fora da faixa de 50%–150% da média e calcula a média ponderada final."
      />

      {samples.length === 0 ? (
        <div className="p-6 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm">
          Nenhuma amostra com área e valor preenchidos. Volte ao passo 6 e cadastre as amostras.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-gray-200 mb-5">
            <table className="w-full text-sm min-w-[640px]">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
                <tr>
                  <th className="px-3 py-2 text-center">Nº</th>
                  <th className="px-3 py-2 text-left">Bairro</th>
                  <th className="px-3 py-2 text-center">Quartos</th>
                  <th className="px-3 py-2 text-right">Área Total (m²)</th>
                  <th className="px-3 py-2 text-right">Valor Total (R$)</th>
                  <th className="px-3 py-2 text-right">Valor/m²</th>
                  <th className="px-3 py-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {samplesWithVpm.map((s, i) => {
                  const eliminada = eliminadas.includes(i);
                  const rowBg = calculado ? (eliminada ? 'bg-red-50' : 'bg-green-50') : 'bg-white';
                  const textDecor = calculado && eliminada ? 'line-through text-red-400' : '';
                  return (
                    <tr key={s._key || i} className={`border-t border-gray-100 ${rowBg}`}>
                      <td className={`px-3 py-2 text-center font-mono text-gray-500 ${textDecor}`}>{i + 1}</td>
                      <td className={`px-3 py-2 ${textDecor}`}>{s.neighborhood || s.address || '—'}</td>
                      <td className={`px-3 py-2 text-center ${textDecor}`}>{s.quartos || '—'}</td>
                      <td className={`px-3 py-2 text-right ${textDecor}`}>
                        {Number(s.area || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className={`px-3 py-2 text-right ${textDecor}`}>{fmtBrl(s.value)}</td>
                      <td className={`px-3 py-2 text-right font-semibold ${calculado && !eliminada ? 'text-emerald-800' : textDecor || 'text-gray-700'}`}>
                        R$ {s._vpm.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {calculado ? (
                          eliminada
                            ? <span className="text-xs font-semibold text-red-600 bg-red-100 px-2 py-0.5 rounded-full">Eliminada</span>
                            : <span className="text-xs font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">OK</span>
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex justify-center mb-6">
            <Button
              type="button"
              onClick={calcular}
              className="bg-emerald-900 hover:bg-emerald-800 text-white px-8 py-2 text-sm font-semibold"
            >
              Calcular Ponderância
            </Button>
          </div>

          {calculado && (() => {
            const amostrasValidas = samplesWithVpm.filter((_, i) => !eliminadas.includes(i));
            const N = amostrasValidas.length;
            const peso = N > 0 ? 1 / N : 0;
            const somaVpm = amostrasValidas.reduce((acc, s) => acc + s._vpm, 0);

            return (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Limite Inferior</div>
                    <div className="text-base font-bold text-gray-800">R$ {fmt2(form.ponderancia_limite_inf)}/m²</div>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Limite Superior</div>
                    <div className="text-base font-bold text-gray-800">R$ {fmt2(form.ponderancia_limite_sup)}/m²</div>
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
                    <div className="text-xs text-red-600 uppercase tracking-wider mb-1">Eliminadas</div>
                    <div className="text-base font-bold text-red-700">{eliminadas.length}</div>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center">
                    <div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Restantes</div>
                    <div className="text-base font-bold text-emerald-800">{restantesCount}</div>
                  </div>
                </div>

                <div className="bg-emerald-50 border-2 border-emerald-300 rounded-xl p-5">
                  <div className="text-xs text-emerald-700 uppercase tracking-wider mb-2">
                    Fórmula: Σ Valores Restantes / {restantesCount} amostras restantes
                  </div>
                  <div className="text-3xl font-bold text-emerald-900 mb-1">
                    Média Ponderada Final: R$ {fmt2(form.ponderancia_media)}/m²
                  </div>
                </div>

                {N > 0 && (
                  <div className="rounded-xl border border-emerald-200 bg-white overflow-hidden">
                    <div className="bg-emerald-800 text-white px-4 py-2.5">
                      <div className="text-sm font-semibold">Ponderação dos Valores</div>
                      <div className="text-xs text-emerald-200 mt-0.5">Apenas amostras válidas (não eliminadas) — peso igualitário 1/N</div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm min-w-[540px]">
                        <thead className="bg-emerald-50 text-xs text-emerald-800 uppercase tracking-wider">
                          <tr>
                            <th className="px-3 py-2 text-center">Nº</th>
                            <th className="px-3 py-2 text-left">Bairro</th>
                            <th className="px-3 py-2 text-right">Valor/m²</th>
                            <th className="px-3 py-2 text-center">Peso (1/{N})</th>
                            <th className="px-3 py-2 text-right">Valor Ponderado</th>
                          </tr>
                        </thead>
                        <tbody>
                          {amostrasValidas.map((s, idx) => {
                            const valorPonderado = s._vpm * peso;
                            return (
                              <tr key={s._key || idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-emerald-50/40'}>
                                <td className="px-3 py-2 text-center font-mono text-gray-500">{idx + 1}</td>
                                <td className="px-3 py-2 text-gray-700">{s.neighborhood || s.address || '—'}</td>
                                <td className="px-3 py-2 text-right font-semibold text-emerald-800">R$ {fmt2(s._vpm)}</td>
                                <td className="px-3 py-2 text-center text-gray-600">{(peso * 100).toFixed(4)}%</td>
                                <td className="px-3 py-2 text-right font-semibold text-gray-800">R$ {fmt2(valorPonderado)}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                        <tfoot className="border-t-2 border-emerald-300 bg-emerald-100">
                          <tr>
                            <td colSpan={2} className="px-3 py-2.5 text-sm font-bold text-emerald-900">SOMA ({N} amostras)</td>
                            <td className="px-3 py-2.5 text-right font-bold text-emerald-900">R$ {fmt2(somaVpm)}</td>
                            <td className="px-3 py-2.5 text-center font-bold text-emerald-900">100%</td>
                            <td className="px-3 py-2.5 text-right font-bold text-emerald-900">R$ {fmt2(form.ponderancia_media)}</td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>

                    <div className="border-t border-emerald-100 bg-emerald-50/60 px-4 py-3 space-y-1.5">
                      <div className="text-xs font-semibold text-emerald-800 uppercase tracking-wider mb-2">Cálculo Passo a Passo</div>
                      <div className="text-sm text-gray-700">
                        <span className="font-medium">1.</span> Soma dos Valor/m² válidos:{' '}
                        <span className="font-bold text-emerald-800">
                          {amostrasValidas.map((s) => `R$ ${fmt2(s._vpm)}`).join(' + ')} = R$ {fmt2(somaVpm)}
                        </span>
                      </div>
                      <div className="text-sm text-gray-700">
                        <span className="font-medium">2.</span> Dividido por N (amostras válidas):{' '}
                        <span className="font-bold text-emerald-800">R$ {fmt2(somaVpm)} ÷ {N}</span>
                      </div>
                      <div className="text-sm text-gray-700 flex items-center gap-2">
                        <span className="font-medium">3.</span>
                        <span className="text-base font-bold text-emerald-900">
                          = Média Ponderada Final: R$ {fmt2(form.ponderancia_media)}/m²
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="border-t border-gray-100 pt-4">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-3">
                    <label className="text-sm font-medium text-gray-700 whitespace-nowrap">Área do imóvel avaliando (m²):</label>
                    <span className="font-semibold text-gray-900">
                      {area > 0
                        ? area.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' m²'
                        : <span className="text-amber-600 text-sm">Preencha a área no step do imóvel (passo 5)</span>}
                    </span>
                  </div>

                  {area > 0 && (
                    <div className="bg-gradient-to-r from-amber-50 to-yellow-50 border-2 border-amber-400 rounded-xl p-5">
                      <div className="text-xs text-amber-700 uppercase tracking-wider mb-1">
                        Valor Final = {fmtBrlM2(form.ponderancia_media)} × {area.toLocaleString('pt-BR')} m²
                      </div>
                      <div className="text-3xl font-bold text-amber-800">
                        Valor do Imóvel: {fmtBrl(form.ponderancia_valor_final)}
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex justify-end">
                  <Button
                    type="button"
                    onClick={usarNoLaudo}
                    className="bg-amber-600 hover:bg-amber-700 text-white px-6 py-2 text-sm font-semibold"
                  >
                    Usar este valor no laudo
                  </Button>
                </div>
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
};
