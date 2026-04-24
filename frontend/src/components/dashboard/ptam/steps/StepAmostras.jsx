// @module ptam/steps/StepAmostras — Step 6: Amostras de Mercado (tabela de pesquisa, análise)
import React, { useState, useMemo } from 'react';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { Button } from '../../../ui/button';
import { Plus, Trash2, Search, AlertTriangle } from 'lucide-react';
import { SectionHeader, AiButton } from '../shared/primitives';
import { emptyMarketSample, computeStatsNBR } from '../ptamHelpers';
import ImageUploader from '../ImageUploader';
import { BuscaAmostras } from '../BuscaAmostras';

const MarketSampleRow = ({ s, onChange, onRemove, idx, isSaneada }) => {
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

  // Estilos para amostras saneadas (eliminadas)
  const rowClass = isSaneada
    ? 'bg-red-50 border-t border-red-100 text-sm'
    : 'border-t border-gray-100 text-sm';

  return (
    <tr className={rowClass}>
      <td className="px-2 py-1.5 text-center">
        <span className={`font-mono ${isSaneada ? 'text-red-500' : 'text-gray-400'}`}>{idx + 1}</span>
        {isSaneada && (
          <div className="group relative inline-block ml-1">
            <AlertTriangle className="w-3.5 h-3.5 text-red-500 inline" />
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block w-64 p-2 bg-gray-800 text-white text-xs rounded shadow-lg z-10">
              Eliminada por estar fora do intervalo de saneamento (±10% da média inicial)
            </span>
          </div>
        )}
      </td>
      <td className="px-2 py-1.5"><Input value={s.address || ''} onChange={(e) => onChange({ ...s, address: e.target.value })} placeholder="Endereço" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5"><Input value={s.neighborhood || ''} onChange={(e) => onChange({ ...s, neighborhood: e.target.value })} placeholder="Bairro" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-24"><Input type="number" value={s.area || ''} onChange={(e) => handleValue('area', e.target.value)} placeholder="m²" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-28"><Input type="number" value={s.value || ''} onChange={(e) => handleValue('value', e.target.value)} placeholder="R$" className="text-xs h-8" /></td>
      <td className={`px-2 py-1.5 w-24 text-center font-semibold ${isSaneada ? 'text-red-600 line-through' : 'text-emerald-800'}`}>
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
  const samples = useMemo(() => form.market_samples ?? [], [form.market_samples]);
  const [showBusca, setShowBusca] = useState(false);
  const add = () => setForm({ ...form, market_samples: [...samples, emptyMarketSample()] });
  const update = (i, ns) => setForm({ ...form, market_samples: samples.map((s, idx) => idx === i ? ns : s) });
  const remove = (i) => setForm({ ...form, market_samples: samples.filter((_, idx) => idx !== i) });

  // Calcular estatísticas NBR para destacar amostras saneadas
  const stats = useMemo(() => computeStatsNBR(samples), [samples]);

  const handleImport = (novasAmostras) => {
    const amostrasFormatadas = novasAmostras.map(a => ({
      ...emptyMarketSample(),
      address: a.address,
      neighborhood: a.neighborhood,
      area: a.area,
      value: a.value,
      value_per_sqm: a.value_per_sqm,
      source: a.source,
      collection_date: a.collection_date,
      contact_phone: a.contact_phone,
      notes: a.notes,
      tipo_amostra: a.tipo_amostra,
      foto: a.thumbnail,
    }));
    setForm({ ...form, market_samples: [...samples, ...amostrasFormatadas] });
    setShowBusca(false);
  };

  const validCount = samples.filter((s) => (s.value_per_sqm || 0) > 0).length;
  const saneadasCount = stats.indices_saneadas.length;

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
        <div className="flex gap-2">
          <Button 
            type="button" 
            variant="outline"
            onClick={() => setShowBusca(true)} 
            className="border-emerald-300 text-emerald-700 hover:bg-emerald-50 text-sm"
          >
            <Search className="w-4 h-4 mr-1" /> Buscar no ZAP / VivaReal
          </Button>
          <Button type="button" onClick={add} className="bg-emerald-900 hover:bg-emerald-800 text-white text-sm">
            <Plus className="w-4 h-4 mr-1" /> Nova amostra
          </Button>
        </div>
      </div>

      {/* Resumo de Saneamento */}
      {stats.n_total > 0 && (
        <div className={`mb-4 p-3 rounded-lg border ${
          stats.n_validas < 3 
            ? 'bg-red-50 border-red-200' 
            : saneadasCount > 0 
              ? 'bg-amber-50 border-amber-200' 
              : 'bg-emerald-50 border-emerald-200'
        }`}>
          <div className="flex items-center gap-2">
            {stats.n_validas < 3 ? (
              <AlertTriangle className="w-4 h-4 text-red-500" />
            ) : saneadasCount > 0 ? (
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            ) : null}
            <span className={`text-sm font-medium ${
              stats.n_validas < 3 ? 'text-red-700' : saneadasCount > 0 ? 'text-amber-700' : 'text-emerald-700'
            }`}>
              {stats.n_validas} amostra(s) válida(s) de {stats.n_total} inserida(s)
              {saneadasCount > 0 && ` — ${saneadasCount} eliminada(s) pelo saneamento`}
            </span>
          </div>
          {stats.n_validas < 3 && (
            <p className="text-xs text-red-600 mt-1">
              Mínimo 3 amostras válidas necessárias para PTAM conforme NBR 14653-2
            </p>
          )}
          {saneadasCount > 0 && (
            <p className="text-xs text-amber-600 mt-1">
              Amostras eliminadas por estarem fora do intervalo de saneamento (±10% da média inicial)
            </p>
          )}
        </div>
      )}

      <BuscaAmostras
        open={showBusca}
        onClose={() => setShowBusca(false)}
        onImport={handleImport}
        cidadeDefault={form.property_city || ''}
        estadoDefault={form.property_state || ''}
      />

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
                  isSaneada={stats.indices_saneadas.includes(i)}
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
