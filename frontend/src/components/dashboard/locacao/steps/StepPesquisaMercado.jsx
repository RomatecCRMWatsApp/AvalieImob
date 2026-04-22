// @module locacao/steps/StepPesquisaMercado — Step 5: Pesquisa de Mercado (amostras de locação)
import React, { useState } from 'react';
import { Field, Input, Textarea, Grid } from '../shared/primitives';
import SmartPhotoInput from '../../../shared/SmartPhotoInput';
import { uploadAPI } from '../../../../lib/api';
import { useToast } from '../../../../hooks/use-toast';
import { X } from 'lucide-react';

export const StepPesquisaMercado = ({ form, setForm }) => {
  const { toast } = useToast();
  const [uploadingIdx, setUploadingIdx] = useState(null);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const samples = form.market_samples || [];

  const addSample = () => {
    setForm(f => ({
      ...f,
      market_samples: [...(f.market_samples || []), {
        address: '', neighborhood: '', area: 0, valor_aluguel: 0,
        valor_por_m2: 0, source: '', collection_date: '', contact_phone: '', notes: '',
        tipo_amostra: 'oferta', foto_url: ''
      }]
    }));
  };

  const removeSample = (idx) => {
    setForm(f => ({ ...f, market_samples: f.market_samples.filter((_, i) => i !== idx) }));
  };

  const updateSample = (idx, field, value) => {
    setForm(f => {
      const arr = [...f.market_samples];
      arr[idx] = { ...arr[idx], [field]: value };
      if (field === 'valor_aluguel' || field === 'area') {
        const aluguel = parseFloat(field === 'valor_aluguel' ? value : arr[idx].valor_aluguel) || 0;
        const area = parseFloat(field === 'area' ? value : arr[idx].area) || 1;
        arr[idx].valor_por_m2 = area > 0 ? parseFloat((aluguel / area).toFixed(2)) : 0;
      }
      return { ...f, market_samples: arr };
    });
  };

  const handlePhotoUpload = async (file, idx) => {
    if (!file) return;
    setUploadingIdx(idx);
    try {
      const result = await uploadAPI.uploadImage(file);
      const url = result.url || result.image_url || result.id;
      updateSample(idx, 'foto_url', url);
    } catch {
      toast({ title: 'Erro ao fazer upload da foto', variant: 'destructive' });
    } finally {
      setUploadingIdx(null);
    }
  };

  const removePhoto = (idx) => {
    updateSample(idx, 'foto_url', '');
  };

  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">5. Pesquisa de Mercado</h3>

      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">{samples.length} amostra(s) cadastrada(s)</p>
        <button
          onClick={addSample}
          className="text-sm text-emerald-700 border border-emerald-300 rounded-xl px-3 py-1.5 hover:bg-emerald-50 transition"
        >
          + Adicionar Amostra
        </button>
      </div>

      {samples.map((s, idx) => (
        <div key={idx} className="border border-gray-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-700">Amostra {idx + 1}</span>
            <button onClick={() => removeSample(idx)} className="text-red-400 hover:text-red-600 text-xs transition">Remover</button>
          </div>
          <Grid cols={2}>
            <Field label="Endereço" className="md:col-span-2">
              <Input value={s.address} onChange={e => updateSample(idx, 'address', e.target.value)} />
            </Field>
            <Field label="Bairro">
              <Input value={s.neighborhood} onChange={e => updateSample(idx, 'neighborhood', e.target.value)} />
            </Field>
            <Field label="Área (m²)">
              <Input type="number" value={s.area} onChange={e => updateSample(idx, 'area', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Valor do Aluguel (R$)">
              <Input type="number" value={s.valor_aluguel} onChange={e => updateSample(idx, 'valor_aluguel', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="R$/m²">
              <Input readOnly value={s.valor_por_m2 || 0} className="bg-gray-50" />
            </Field>
            <Field label="Fonte / Anúncio">
              <Input value={s.source} onChange={e => updateSample(idx, 'source', e.target.value)} placeholder="Zap, VivaReal, Direto..." />
            </Field>
            <Field label="Data de Coleta">
              <Input type="date" value={s.collection_date} onChange={e => updateSample(idx, 'collection_date', e.target.value)} />
            </Field>
            <Field label="Contato">
              <Input value={s.contact_phone} onChange={e => updateSample(idx, 'contact_phone', e.target.value)} />
            </Field>
            <Field label="Observações" className="md:col-span-2">
              <Textarea rows={2} value={s.notes} onChange={e => updateSample(idx, 'notes', e.target.value)} />
            </Field>
            <Field label="Tipo da Amostra" className="md:col-span-2">
              <div className="space-y-1">
                <select
                  value={s.tipo_amostra || 'oferta'}
                  onChange={e => updateSample(idx, 'tipo_amostra', e.target.value)}
                  className="w-full text-sm rounded-md border border-gray-200 px-2 py-1.5 focus:outline-none focus:border-emerald-400"
                >
                  <option value="oferta">Oferta de Mercado</option>
                  <option value="consolidada">Consolidada / Comercializada</option>
                </select>
                {s.tipo_amostra === 'consolidada' ? (
                  <span className="inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-emerald-100 text-emerald-800 border-emerald-300">Consolidada</span>
                ) : (
                  <span className="inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-amber-100 text-amber-800 border-amber-300">Oferta</span>
                )}
              </div>
            </Field>
            <Field label="Foto da Amostra" className="md:col-span-2">
              {s.foto_url ? (
                <div className="flex items-start gap-3">
                  <div className="relative w-24 h-24 rounded-xl overflow-hidden border border-gray-200 flex-shrink-0">
                    <img
                      src={s.foto_url.startsWith('http') ? s.foto_url : uploadAPI.getImageUrl(s.foto_url)}
                      alt={`Amostra ${idx + 1}`}
                      className="w-full h-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => removePhoto(idx)}
                      className="absolute top-0 right-0 bg-red-500 text-white text-xs w-5 h-5 flex items-center justify-center rounded-bl-xl hover:bg-red-600 transition"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Foto adicionada. Clique no × para remover.</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {uploadingIdx === idx ? (
                    <p className="text-xs text-emerald-700 animate-pulse">Enviando foto...</p>
                  ) : (
                    <label className="flex items-center gap-2 text-sm text-gray-600 border border-dashed border-gray-300 rounded-lg px-3 py-2 cursor-pointer hover:border-emerald-400 hover:text-emerald-700 transition w-fit">
                      <span>+ Adicionar foto</span>
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={e => {
                          const file = e.target.files?.[0];
                          if (file) handlePhotoUpload(file, idx);
                          e.target.value = '';
                        }}
                      />
                    </label>
                  )}
                  <p className="text-xs text-gray-400">Opcional — foto do anúncio ou do imóvel comparativo</p>
                </div>
              )}
            </Field>
          </Grid>
        </div>
      ))}

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mt-1">
        Amostras consolidadas (locacao efetivada) tem maior peso na avaliacao conforme NBR 14653.
      </p>

      <Field label="Análise do Mercado">
        <Textarea rows={5} value={form.market_analysis} onChange={e => set('market_analysis', e.target.value)} placeholder="Descreva o comportamento do mercado, oferta e demanda, sazonalidade..." />
      </Field>
    </div>
  );
};
