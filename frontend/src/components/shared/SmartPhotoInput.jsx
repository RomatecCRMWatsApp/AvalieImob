// @module SmartPhotoInput — upload inteligente: câmera nativa no mobile, arquivo no desktop
import React, { useRef, useState } from 'react';
import { Camera, Image, FolderOpen, X, Loader2 } from 'lucide-react';
import { useIsMobile } from '../../hooks/useIsMobile';
import { compressFile, getGeoSilent } from '../../utils/photoUtils';

const SmartPhotoInput = ({
  onPhoto,
  onPhotos,
  multiple = true,
  label = 'Fotos',
  slot,
  disabled = false,
  preview = true,
}) => {
  const isMobile = useIsMobile();
  const [previews, setPreviews] = useState([]);
  const [loading, setLoading] = useState(false);

  const processFiles = async (files) => {
    if (!files?.length) return;
    setLoading(true);
    try {
      const fileList = multiple ? Array.from(files) : [files[0]];
      const [compressed, geo] = await Promise.all([
        Promise.all(fileList.map(compressFile)),
        getGeoSilent(),
      ]);
      const timestamp = new Date().toISOString();
      const enriched = compressed.map((f) => Object.assign(f, { _gps: geo, _ts: timestamp, _slot: slot }));
      const newPreviews = enriched.map((f) => ({
        file: f, url: URL.createObjectURL(f), name: f.name,
        size: f.size, gps: geo, timestamp,
      }));
      const next = multiple ? [...previews, ...newPreviews] : newPreviews;
      setPreviews(next);
      if (onPhotos) onPhotos(next.map((p) => p.file));
      if (onPhoto) onPhoto(enriched[0]);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => { processFiles(e.target.files); e.target.value = ''; };

  const removePreview = (idx) => {
    const next = previews.filter((_, i) => i !== idx);
    setPreviews(next);
    if (onPhotos) onPhotos(next.map((p) => p.file));
  };

  const base = 'flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium min-h-[48px] cursor-pointer select-none transition-all';
  const act = disabled ? 'opacity-50 cursor-not-allowed' : 'hover:brightness-110 active:scale-95';

  return (
    <div className="space-y-3">
      {label && <p className="text-sm font-medium text-[#c8ffd8]">{label}</p>}

      {isMobile ? (
        <div className="flex flex-wrap gap-2">
          <label className={`${base} ${act} text-white border-2 border-[#00ff88]`} style={{ background: '#006633' }}>
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Camera className="w-5 h-5" />}
            Câmera
            <input type="file" accept="image/*" capture="environment" multiple={multiple}
              disabled={disabled} className="hidden" onChange={handleChange} />
          </label>
          <label className={`${base} ${act} text-[#c8ffd8] border border-[#1a4030]`} style={{ background: '#0a1810' }}>
            <Image className="w-5 h-5" />
            Galeria
            <input type="file" accept="image/*" multiple={multiple}
              disabled={disabled} className="hidden" onChange={handleChange} />
          </label>
        </div>
      ) : (
        <label className={`${base} ${act} text-[#c8ffd8] border-2 border-dashed border-[#1a4030]`} style={{ background: '#0a1810' }}>
          {loading ? <Loader2 className="w-5 h-5 animate-spin text-[#00ff88]" /> : <FolderOpen className="w-5 h-5 text-[#00ff88]" />}
          Selecionar Arquivo
          <input type="file" accept="image/*" multiple={multiple}
            disabled={disabled} className="hidden" onChange={handleChange} />
        </label>
      )}

      {preview && previews.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {previews.map((p, i) => (
            <div key={i} className="relative rounded-md overflow-hidden"
              style={{ width: 80, height: 80, border: '2px solid #00ff88', borderRadius: 6, boxShadow: '0 0 6px #00ff8844' }}>
              <img src={p.url} alt={p.name} className="w-full h-full object-cover" />
              <button type="button" onClick={() => removePreview(i)}
                className="absolute top-0.5 right-0.5 bg-red-600 text-white rounded-full p-0.5 hover:bg-red-700">
                <X className="w-3 h-3" />
              </button>
              <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-[9px] text-[#c8ffd8] truncate px-1 py-0.5">
                {(p.size / 1024).toFixed(0)}KB
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SmartPhotoInput;
