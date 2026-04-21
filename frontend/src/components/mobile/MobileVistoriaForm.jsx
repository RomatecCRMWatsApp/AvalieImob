// @module MobileVistoriaForm — formulário TVI otimizado para toque, offline, GPS
import React, { useState, useEffect, useCallback } from 'react';
import { ChevronRight, ChevronLeft, Save, Loader2 } from 'lucide-react';
import MobilePhotoCapture from './MobilePhotoCapture';
import MobileSignature from './MobileSignature';
import { useOfflineStorage } from '@/hooks/useOfflineStorage';
import { tviAPI } from '@/lib/api';
import { VistoriaFields } from './vistoria-fields';

const DRAFT_KEY = 'avalieimob_tvi_draft';
const SECTIONS = ['Identificação', 'Localização', 'Características', 'Fotos', 'Assinatura'];

export const defaultForm = {
  solicitante: '', locatario: '', imovel_endereco: '',
  lat: '', lng: '',
  tipo_imovel: '', area_total: '', num_quartos: '', num_banheiros: '',
  estado_conservacao: '', observacoes: '',
  fotos: [], assinatura: null,
};

const MobileVistoriaForm = ({ modelId, onSuccess, onCancel }) => {
  const [section, setSection] = useState(0);
  const [form, setForm] = useState(() => {
    try {
      const draft = localStorage.getItem(DRAFT_KEY);
      return draft ? { ...defaultForm, ...JSON.parse(draft) } : { ...defaultForm };
    } catch { return { ...defaultForm }; }
  });
  const [submitting, setSubmitting] = useState(false);
  const { saveVistoria } = useOfflineStorage();

  useEffect(() => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(form));
  }, [form]);

  const set = useCallback((key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSubmit = async () => {
    setSubmitting(true);
    const payload = { ...form, model_id: modelId };
    try {
      if (navigator.onLine) {
        await tviAPI.create(payload);
      } else {
        await saveVistoria(payload);
      }
      localStorage.removeItem(DRAFT_KEY);
      onSuccess && onSuccess();
    } catch {
      await saveVistoria(payload);
      localStorage.removeItem(DRAFT_KEY);
      onSuccess && onSuccess();
    } finally {
      setSubmitting(false);
    }
  };

  const isLast = section === SECTIONS.length - 1;

  return (
    <div className="flex flex-col h-full max-w-xl mx-auto">
      <div className="px-4 pt-4 pb-2">
        <div className="flex gap-1 mb-2">
          {SECTIONS.map((_, i) => (
            <div key={i}
              className={`h-1 flex-1 rounded-full transition-colors ${i <= section ? 'bg-emerald-600' : 'bg-gray-200'}`}
            />
          ))}
        </div>
        <p className="text-xs text-gray-500">{section + 1}/{SECTIONS.length} · {SECTIONS[section]}</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <VistoriaFields
          section={section}
          form={form}
          set={set}
          PhotoCapture={<MobilePhotoCapture onCapture={(p) => set('fotos', p)} maxPhotos={20} />}
          Signature={<MobileSignature value={form.assinatura} onChange={(s) => set('assinatura', s)} />}
        />
      </div>

      <div className="px-4 py-3 border-t border-gray-100 flex gap-3">
        {section > 0 && (
          <button type="button" onClick={() => setSection((s) => s - 1)}
            className="flex items-center gap-1 px-4 py-3 rounded-xl border border-gray-300 text-sm text-gray-700 hover:bg-gray-50 min-h-[48px] active:scale-95 transition-all">
            <ChevronLeft className="w-4 h-4" /> Anterior
          </button>
        )}
        <div className="flex-1" />
        {onCancel && section === 0 && (
          <button type="button" onClick={onCancel}
            className="px-4 py-3 rounded-xl border border-gray-200 text-sm text-gray-500 hover:bg-gray-50 min-h-[48px]">
            Cancelar
          </button>
        )}
        {!isLast ? (
          <button type="button" onClick={() => setSection((s) => s + 1)}
            className="flex items-center gap-1 px-5 py-3 rounded-xl bg-emerald-700 text-white text-sm font-medium hover:bg-emerald-800 active:scale-95 transition-all min-h-[48px]">
            Próximo <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button type="button" onClick={handleSubmit} disabled={submitting}
            className="flex items-center gap-2 px-5 py-3 rounded-xl bg-emerald-700 text-white text-sm font-semibold hover:bg-emerald-800 active:scale-95 transition-all min-h-[48px] disabled:opacity-60">
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {navigator.onLine ? 'Enviar Vistoria' : 'Salvar Offline'}
          </button>
        )}
      </div>
    </div>
  );
};

export default MobileVistoriaForm;
