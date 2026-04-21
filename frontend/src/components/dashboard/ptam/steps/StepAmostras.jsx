// @module ptam/steps/StepAmostras — Step 6: Amostras de Mercado (tabela de pesquisa, análise)
import React from 'react';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { Button } from '../../../ui/button';
import { Plus, Trash2 } from 'lucide-react';
import { SectionHeader, AiButton } from '../shared/primitives';
import { emptyMarketSample } from '../ptamHelpers';
import ImageUploader from '../ImageUploader';

const MarketSampleRow = ({ s, onChange, onRemove, idx }) => {
  const handleValue = (field, raw) => {
    const v = Number(raw);
    const area = field === 'area' ? v : Number(s.area || 0);
    const value = field === 'value' ? v : Number(s.value || 0);
    const vpm = area > 0 ? Math.round((value / area) * 100) / 100 : 0;
    onChange({ ...s, [field]: v, value_per_sqm: vpm });
  };

  const tipoLabel = s.tipo_amostra === 'consolidada' ? 'Consolidada' : 'Oferta';
  const tipoBadge = s.tipo_amostra === 'consolidada'
    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
    : 'bg-amber-100 text-amber-800 border-amber-300';

  return (
    <tr className="border-t border-gray-100 text-sm">
      <td className="px-2 py-1.5 text-center text-gray-400 font-mono">{idx + 1}</td>
      <td className="px-2 py-1.5"><Input value={s.address || ''} onChange={(e) => onChange({ ...s, address: e.target.value })} placeholder="Endereço" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5"><Input value={s.neighborhood || ''} onChange={(e) => onChange({ ...s, neighborhood: e.target.value })} placeholder="Bairro" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-24"><Input type="number" value={s.area || ''} onChange={(e) => handleValue('area', e.target.value)} placeholder="m²" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-28"><Input type="number" value={s.value || ''} onChange={(e) => handleValue('value', e.target.value)} placeholder="R$" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-24 text-center font-semibold text-emerald-800">
        {s.value_per_sqm > 0 ? `R$ ${Number(s.value_per_sqm).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}` : '—'}
      </td>
      <td className="px-2 py-1.5 w-36">
        <div className="space-y-1">
          <select
            value={s.tipo_amostra || 'oferta'}
            onChange={(e) => onChange({ ...s, tipo_amostra: e.target.value })}
            className="w-full text-xs h-8 rounded border border-gray-200 px-1 focus:outline-none focus:border-emerald-400"
          >
            <option value="oferta">Oferta de Mercado</option>
            <option value="consolidada">Consolidada / Comercializada</option>
          </select>
          <span className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border ${tipoBadge}`}>
            {tipoLabel}
          </span>
        </div>
      </td>
      <td className="px-2 py-1.5"><Input value={s.source || ''} onChange={(e) => onChange({ ...s, source: e.target.value })} placeholder="Fonte" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-28"><Input type="date" value={s.collection_date || ''} onChange={(e) => onChange({ ...s, collection_date: e.target.value })} className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-28"><Input value={s.contact_phone || ''} onChange={(e) => onChange({ ...s, contact_phone: e.target.value })} placeholder="Telefone" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-24">
        <ImageUploader
          images={s.foto ? [s.foto] : []}
          onImagesChange={(ids) => onChange({ ...s, foto: ids[0] || null })}
          maxImages={1}
          single
          label=""
        />
      </td>
      <td className="px-2 py-1.5">
        <button type="button" onClick={onRemove} className="p-1.5 text-red-500 hover:bg-red-50 rounded">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </td>
    </tr>
  );
};

export const StepAmostras = ({ form, setForm, onAi, aiLoading }) => {
  const samples = form.market_samples || [];
  const add = () => setForm({ ...form, market_samples: [...samples, emptyMarketSample()] });
  const update = (i, ns) => setForm({ ...form, market_samples: samples.map((s, idx) => idx === i ? ns : s) });
  const remove = (i) => setForm({ ...form, market_samples: samples.filter((_, idx) => idx !== i) });

  const validCount = samples.filter((s) => (s.value_per_sqm || 0) > 0).length;

  return (
    <div>
      <SectionHeader
        title="6. Amostras de Mercado"
        subtitle="Cadastre as amostras coletadas para a pesquisa de mercado (mínimo 3)."
      />

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{samples.length} amostra(s) cadastrada(s)</span>
          {validCount < 3 && (
            <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-0.5">
              Adicione pelo menos 3 amostras com área e valor
            </span>
          )}
          {validCount >= 3 && (
            <span className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-2 py-0.5">
              {validCount} amostras com R$/m²
            </span>
          )}
        </div>
        <Button type="button" onClick={add} className="bg-emerald-900 hover:bg-emerald-800 text-white text-sm">
          <Plus className="w-4 h-4 mr-1" /> Nova amostra
        </Button>
      </div>

      {samples.length === 0 ? (
        <div className="text-center py-12 bg-emerald-50/40 rounded-xl border-2 border-dashed border-emerald-200 text-gray-500">
          Nenhuma amostra cadastrada. Clique em "Nova amostra" para começar.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="w-full text-sm min-w-[1050px]">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="px-2 py-2 text-center">#</th>
                <th className="px-2 py-2 text-left">Endereço</th>
                <th className="px-2 py-2 text-left">Bairro</th>
                <th className="px-2 py-2 text-left">Área (m²)</th>
                <th className="px-2 py-2 text-left">Valor (R$)</th>
                <th className="px-2 py-2 text-center">R$/m²</th>
                <th className="px-2 py-2 text-left">Tipo</th>
                <th className="px-2 py-2 text-left">Fonte</th>
                <th className="px-2 py-2 text-left">Data coleta</th>
                <th className="px-2 py-2 text-left">Telefone</th>
                <th className="px-2 py-2 text-left">Foto</th>
                <th className="px-2 py-2" />
              </tr>
            </thead>
            <tbody>
              {samples.map((s, i) => (
                <MarketSampleRow
                  key={s._key || `ms-${i}`}
                  s={s}
                  idx={i}
                  onChange={(ns) => update(i, ns)}
                  onRemove={() => remove(i)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mt-3">
        Amostras consolidadas (venda/locacao efetivada) tem maior peso na avaliacao conforme NBR 14653.
      </p>

      <div className="mt-6">
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Análise de mercado (texto descritivo)</label>
        <Textarea
          value={form.market_analysis || ''}
          onChange={(e) => setForm({ ...form, market_analysis: e.target.value })}
          rows={4}
          placeholder="Descreva o comportamento do mercado imobiliário local, oferta, demanda, liquidez..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('market_analysis')} loading={aiLoading === 'market_analysis'} />
        </div>
      </div>
    </div>
  );
};
