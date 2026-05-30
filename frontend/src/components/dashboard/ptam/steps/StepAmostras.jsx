// @module ptam/steps/StepAmostras — Step 6: Amostras de Mercado (cards de pesquisa, análise)
import React, { useState, useMemo } from 'react';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { Button } from '../../../ui/button';
import { Plus, Trash2, Search, AlertTriangle } from 'lucide-react';
import { SectionHeader, AiButton } from '../shared/primitives';
import { emptyMarketSample, computeStatsNBR } from '../ptamHelpers';
import ImageUploader from '../ImageUploader';
import { BuscaAmostras } from '../BuscaAmostras';

const FieldLabel = ({ children }) => (
  <label className="block text-[11px] font-medium text-gray-500 mb-1">{children}</label>
);

const MarketSampleCard = ({ s, onChange, onRemove, idx, isSaneada }) => {
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
    <div className={`rounded-xl border p-4 transition ${isSaneada ? 'border-red-200 bg-red-50/60' : 'border-gray-200 bg-white hover:border-emerald-200'}`}>
      {/* Cabeçalho do card */}
      <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-gray-100">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`flex items-center justify-center w-7 h-7 rounded-full text-sm font-semibold ${isSaneada ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-800'}`}>
            {idx + 1}
          </span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${tipoBadge}`}>{tipoLabel}</span>
          {isSaneada && (
            <span className="flex items-center gap-1 text-xs text-red-600">
              <AlertTriangle className="w-3.5 h-3.5" /> Eliminada pelo saneamento (±10% da média)
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wide text-gray-400">R$/m²</div>
            <div className={`text-base font-bold ${isSaneada ? 'text-red-600 line-through' : 'text-emerald-800'}`}>
              {s.value_per_sqm > 0
                ? `R$ ${Number(s.value_per_sqm).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}`
                : '—'}
            </div>
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
            title="Remover amostra"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Corpo: campos rotulados + foto */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div className="sm:col-span-2">
            <FieldLabel>Endereço</FieldLabel>
            <Input value={s.address || ''} onChange={(e) => onChange({ ...s, address: e.target.value })} placeholder="Rua, número" className="h-9" />
          </div>
          <div>
            <FieldLabel>Bairro</FieldLabel>
            <Input value={s.neighborhood || ''} onChange={(e) => onChange({ ...s, neighborhood: e.target.value })} placeholder="Bairro" className="h-9" />
          </div>
          <div>
            <FieldLabel>Área (m²)</FieldLabel>
            <Input type="number" value={s.area || ''} onChange={(e) => handleValue('area', e.target.value)} placeholder="0" className="h-9" />
          </div>
          <div>
            <FieldLabel>Valor (R$)</FieldLabel>
            <Input type="number" value={s.value || ''} onChange={(e) => handleValue('value', e.target.value)} placeholder="0" className="h-9" />
          </div>
          <div>
            <FieldLabel>Tipo da amostra</FieldLabel>
            <select
              value={s.tipo_amostra || 'oferta'}
              onChange={(e) => onChange({ ...s, tipo_amostra: e.target.value })}
              className="w-full h-9 rounded-md border border-gray-200 px-2 text-sm bg-white focus:outline-none focus:border-emerald-400"
            >
              <option value="oferta">Oferta de Mercado</option>
              <option value="consolidada">Consolidada / Comercializada</option>
            </select>
          </div>
          <div>
            <FieldLabel>Fonte</FieldLabel>
            <Input value={s.source || ''} onChange={(e) => onChange({ ...s, source: e.target.value })} placeholder="Imobiliária, portal, contato..." className="h-9" />
          </div>
          <div>
            <FieldLabel>Data da coleta</FieldLabel>
            <Input type="date" value={s.collection_date || ''} onChange={(e) => onChange({ ...s, collection_date: e.target.value })} className="h-9" />
          </div>
          <div>
            <FieldLabel>Telefone</FieldLabel>
            <Input value={s.contact_phone || ''} onChange={(e) => onChange({ ...s, contact_phone: e.target.value })} placeholder="(00) 00000-0000" className="h-9" />
          </div>
        </div>

        {/* Foto da amostra */}
        <div className="lg:w-56 shrink-0">
          <FieldLabel>Foto da amostra</FieldLabel>
          <ImageUploader
            images={s.foto ? [s.foto] : []}
            onImagesChange={(ids) => onChange({ ...s, foto: ids[0] || null })}
            maxImages={1}
            single
            label=""
          />
        </div>
      </div>
    </div>
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

      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-3 flex-wrap">
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
        <div className="space-y-4">
          {samples.map((s, i) => (
            <MarketSampleCard
              key={s._key || `ms-${i}`}
              s={s}
              idx={i}
              onChange={(ns) => update(i, ns)}
              onRemove={() => remove(i)}
              isSaneada={stats.indices_saneadas.includes(i)}
            />
          ))}
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
