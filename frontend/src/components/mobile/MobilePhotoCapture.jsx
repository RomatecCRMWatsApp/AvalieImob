// @module MobilePhotoCapture — captura de foto via câmera nativa, compressão, suporte offline
import React, { useRef, useState } from 'react';
import { Camera, X, CheckCircle2 } from 'lucide-react';

const MAX_WIDTH = 1200;
const QUALITY = 0.75;

function compressImage(file) {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ratio = Math.min(MAX_WIDTH / img.width, 1);
      canvas.width = img.width * ratio;
      canvas.height = img.height * ratio;
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL('image/jpeg', QUALITY));
    };
    img.src = url;
  });
}

const MobilePhotoCapture = ({ onCapture, label = 'Foto', maxPhotos = 10 }) => {
  const inputRef = useRef(null);
  const [previews, setPreviews] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleChange = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setLoading(true);
    try {
      const compressed = await Promise.all(files.map(compressImage));
      const next = [...previews, ...compressed].slice(0, maxPhotos);
      setPreviews(next);
      onCapture && onCapture(next);
    } finally {
      setLoading(false);
      e.target.value = '';
    }
  };

  const remove = (idx) => {
    const next = previews.filter((_, i) => i !== idx);
    setPreviews(next);
    onCapture && onCapture(next);
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {previews.map((src, i) => (
          <div key={i} className="relative w-20 h-20 rounded-xl overflow-hidden border border-gray-200">
            <img src={src} alt={`Foto ${i + 1}`} className="w-full h-full object-cover" />
            <button
              type="button"
              onClick={() => remove(i)}
              className="absolute top-0.5 right-0.5 bg-red-600 text-white rounded-full p-0.5"
            >
              <X className="w-3 h-3" />
            </button>
            <CheckCircle2 className="absolute bottom-0.5 left-0.5 w-3 h-3 text-emerald-400" />
          </div>
        ))}
        {previews.length < maxPhotos && (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={loading}
            className="w-20 h-20 rounded-xl border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-400 hover:border-emerald-500 hover:text-emerald-600 active:scale-95 transition-all"
          >
            <Camera className="w-6 h-6 mb-1" />
            <span className="text-xs">{loading ? '...' : label}</span>
          </button>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        multiple
        className="hidden"
        onChange={handleChange}
      />
      {previews.length > 0 && (
        <p className="text-xs text-gray-500">
          {previews.length}/{maxPhotos} fotos · comprimidas para upload
        </p>
      )}
    </div>
  );
};

export default MobilePhotoCapture;
