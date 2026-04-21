import React, { useRef, useState } from 'react';
import { Upload, X, Image } from 'lucide-react';
import { tviAPI } from '../../../../lib/api';
import { useToast } from '../../../../hooks/use-toast';

const PhotoUploader = ({ vistoriaId, ambiente = 'Geral', photos = [], onUploaded }) => {
  const { toast } = useToast();
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [previews, setPreviews] = useState(photos);

  const handleFiles = async (files) => {
    if (!files?.length || !vistoriaId) return;
    setUploading(true);
    try {
      const fd = new FormData();
      Array.from(files).forEach(f => fd.append('files', f));
      fd.append('ambiente', ambiente);
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
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="w-full border-2 border-dashed border-gray-200 rounded-xl p-6
                   flex flex-col items-center gap-2 hover:border-emerald-400 transition-colors
                   text-gray-400 hover:text-emerald-700 disabled:opacity-50"
      >
        <Upload className="w-6 h-6" />
        <span className="text-sm">{uploading ? 'Enviando...' : `Adicionar fotos — ${ambiente}`}</span>
        <span className="text-xs">JPG, PNG, WEBP</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/*"
        className="hidden"
        onChange={e => handleFiles(e.target.files)}
      />

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
              <button
                type="button"
                onClick={() => removePreview(i)}
                className="absolute top-1 right-1 w-5 h-5 rounded-full bg-red-500 text-white
                           flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
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
