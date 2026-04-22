// @module PhotoUploader — TVI: upload de fotos por ambiente; mobile usa câmera nativa
import React, { useState } from 'react';
import { X, Image, Loader2 } from 'lucide-react';
import { tviAPI } from '../../../../lib/api';
import { useToast } from '../../../../hooks/use-toast';
import { useIsMobile } from '../../../../hooks/useIsMobile';
import SmartPhotoInput from '../../../shared/SmartPhotoInput';

const PhotoUploader = ({ vistoriaId, ambiente = 'Geral', photos = [], onUploaded }) => {
  const { toast } = useToast();
  const isMobile = useIsMobile();
  const [uploading, setUploading] = useState(false);
  const [previews, setPreviews] = useState(photos);

  const uploadFiles = async (files) => {
    if (!files?.length || !vistoriaId) return;
    setUploading(true);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append('files', f));
      fd.append('ambiente', ambiente);
      // Inclui GPS e timestamp se disponíveis nos arquivos enriquecidos
      const gps = files[0]?._gps;
      const ts = files[0]?._ts;
      if (gps) { fd.append('gps_lat', String(gps.lat)); fd.append('gps_lng', String(gps.lng)); }
      if (ts) fd.append('timestamp', ts);
      const result = await tviAPI.uploadPhotos(vistoriaId, fd);
      const newPreviews = [...previews, ...(result.photos || [])];
      setPreviews(newPreviews);
      onUploaded && onUploaded(newPreviews);
      toast({ title: `${files.length} foto(s) enviada(s)` });
    } catch {
      toast({ title: 'Erro ao enviar fotos', variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const removePreview = (idx) => {
    const next = previews.filter((_, i) => i !== idx);
    setPreviews(next);
    onUploaded && onUploaded(next);
  };

  return (
    <div className="space-y-3">
      {uploading && (
        <div className="flex items-center gap-2 text-sm text-[#00ff88]">
          <Loader2 className="w-4 h-4 animate-spin" /> Enviando {ambiente}...
        </div>
      )}

      {isMobile ? (
        <SmartPhotoInput
          label={`Fotos — ${ambiente}`}
          multiple
          preview={false}
          onPhotos={(files) => uploadFiles(files)}
        />
      ) : (
        <label className="w-full border-2 border-dashed border-gray-200 rounded-xl p-6 flex flex-col items-center gap-2 hover:border-emerald-400 transition-colors text-gray-400 hover:text-emerald-700 cursor-pointer">
          <span className="text-sm">{`Adicionar fotos — ${ambiente}`}</span>
          <span className="text-xs">JPG, PNG, WEBP</span>
          <input type="file" multiple accept="image/*" className="hidden"
            onChange={(e) => { uploadFiles(Array.from(e.target.files || [])); e.target.value = ''; }} />
        </label>
      )}

      {previews.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
          {previews.map((p, i) => (
            <div key={i} className="relative group rounded-lg overflow-hidden border border-gray-200 aspect-square bg-gray-50">
              {p.url ? (
                <img src={p.url} alt={p.legenda || ambiente} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Image className="w-6 h-6 text-gray-300" />
                </div>
              )}
              <button type="button" onClick={() => removePreview(i)}
                className="absolute top-1 right-1 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <X className="w-3 h-3" />
              </button>
              {p.legenda && (
                <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[10px] px-1.5 py-0.5 truncate">
                  {p.legenda}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PhotoUploader;
