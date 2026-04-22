// @module locacao/steps/StepFotos — Step 9: Documentação Fotográfica da Locação
import React, { useState } from 'react';
import { Field, Textarea } from '../shared/primitives';
import { uploadAPI } from '../../../../lib/api';
import { useToast } from '../../../../hooks/use-toast';
import { useIsMobile } from '../../../../hooks/useIsMobile';
import SmartPhotoInput from '../../../shared/SmartPhotoInput';

export const StepFotos = ({ form, setForm }) => {
  const { toast } = useToast();
  const [uploading, setUploading] = useState(false);
  const isMobile = useIsMobile();

  const handleUpload = async (files, field) => {
    if (!files?.length) return;
    setUploading(true);
    try {
      const urls = await Promise.all(
        files.map((f) => uploadAPI.uploadImage(f).then((r) => r.url || r.image_url || r.id))
      );
      setForm((prev) => ({ ...prev, [field]: [...(prev[field] || []), ...urls] }));
    } catch {
      toast({ title: 'Erro ao fazer upload', variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const removePhoto = (field, idx) => {
    setForm((prev) => ({ ...prev, [field]: prev[field].filter((_, i) => i !== idx) }));
  };

  const PhotoGrid = ({ field, label }) => (
    <Field label={label}>
      <div className="flex flex-wrap gap-2 mb-2">
        {(form[field] || []).map((url, i) => (
          <div key={i} className="relative w-20 h-20 rounded-xl overflow-hidden border border-gray-200">
            <img src={url.startsWith('http') ? url : uploadAPI.getImageUrl(url)} alt="" className="w-full h-full object-cover" />
            <button onClick={() => removePhoto(field, i)}
              className="absolute top-0 right-0 bg-red-500 text-white text-xs w-5 h-5 flex items-center justify-center rounded-bl-xl">×</button>
          </div>
        ))}
        {!isMobile && (
          <label className="w-20 h-20 border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-emerald-400 transition text-gray-400 text-xs text-center">
            <span className="text-2xl leading-none">+</span>
            <input type="file" multiple accept="image/*" className="hidden"
              onChange={(e) => { handleUpload(Array.from(e.target.files || []), field); e.target.value = ''; }} />
          </label>
        )}
      </div>
      {isMobile && (
        <SmartPhotoInput
          label=""
          multiple
          preview={false}
          onPhotos={(files) => handleUpload(files, field)}
        />
      )}
    </Field>
  );

  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">9. Documentação Fotográfica</h3>
      {uploading && <p className="text-sm text-emerald-700 animate-pulse">Enviando imagens...</p>}
      <PhotoGrid field="fotos_imovel" label="Fotos do Imóvel" />
      <PhotoGrid field="fotos_documentos" label="Documentos Digitalizados" />
      <Field label="Documentos Analisados">
        <Textarea
          rows={3}
          value={(form.documentos_analisados || []).join('\n')}
          onChange={(e) => setForm((f) => ({ ...f, documentos_analisados: e.target.value.split('\n').filter(Boolean) }))}
          placeholder="Um documento por linha&#10;Ex: Matrícula do Imóvel&#10;IPTU 2025"
        />
      </Field>
    </div>
  );
};
