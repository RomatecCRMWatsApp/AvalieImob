// @module SmartFileInput — upload de documentos (PDF, DOCX, JPG, PNG)
// Mobile: abre galeria/câmera para imagens, seletor de arquivo para todos os tipos
// Desktop: seletor de arquivo tradicional aceitando múltiplos formatos
import React, { useRef, useState } from 'react';
import { Camera, Image, FolderOpen, X, Loader2, FileText } from 'lucide-react';
import { useIsMobile } from '../../hooks/useIsMobile';
import { compressFile, getGeoSilent } from '../../utils/photoUtils';

const SmartFileInput = ({
  onFile,
  onFiles,
  multiple = true,
  label = 'Documentos',
  slot,
  disabled = false,
  preview = true,
  accept = '.pdf,.docx,.doc,.jpg,.jpeg,.png', // Todos os tipos aceitos
  maxSizeMB = 10,
}) => {
  const isMobile = useIsMobile();
  const [previews, setPreviews] = useState([]);
  const [loading, setLoading] = useState(false);

  const isImage = (filename) => /\.(jpg|jpeg|png|gif|webp|bmp)$/i.test(filename);
  const isPdf = (filename) => /\.pdf$/i.test(filename);
  const isDoc = (filename) => /\.(docx|doc)$/i.test(filename);

  const getFileIcon = (filename) => {
    if (isPdf(filename)) return '📄';
    if (isDoc(filename)) return '📝';
    if (isImage(filename)) return '🖼️';
    return '📎';
  };

  const processFiles = async (files) => {
    if (!files?.length) return;
    setLoading(true);
    try {
      const fileList = multiple ? Array.from(files) : [files[0]];
      
      // Validar tamanho
      const validFiles = fileList.filter(f => {
        const sizeMB = f.size / (1024 * 1024);
        if (sizeMB > maxSizeMB) {
          alert(`Arquivo ${f.name} excede ${maxSizeMB}MB`);
          return false;
        }
        return true;
      });

      // Processar imagens (comprimir), outros arquivos manter original
      const processed = await Promise.all(
        validFiles.map(async (f) => {
          if (isImage(f.name)) {
            const compressed = await compressFile(f);
            const geo = await getGeoSilent();
            const timestamp = new Date().toISOString();
            return Object.assign(compressed, { 
              _gps: geo, 
              _ts: timestamp, 
              _slot: slot,
              _type: 'image'
            });
          }
          // PDF/DOCX manter original
          return Object.assign(f, { 
            _type: isPdf(f.name) ? 'pdf' : 'doc',
            _ts: new Date().toISOString(),
            _slot: slot 
          });
        })
      );

      const newPreviews = processed.map((f) => ({
        file: f,
        url: isImage(f.name) ? URL.createObjectURL(f) : null,
        name: f.name,
        size: f.size,
        type: f._type,
        icon: getFileIcon(f.name),
        timestamp: f._ts,
      }));

      const next = multiple ? [...previews, ...newPreviews] : newPreviews;
      setPreviews(next);
      if (onFiles) onFiles(next.map((p) => p.file));
      if (onFile) onFile(processed[0]);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => { processFiles(e.target.files); e.target.value = ''; };

  const removePreview = (idx) => {
    const next = previews.filter((_, i) => i !== idx);
    setPreviews(next);
    if (onFiles) onFiles(next.map((p) => p.file));
  };

  const base = 'flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium min-h-[48px] cursor-pointer select-none transition-all';
  const act = disabled ? 'opacity-50 cursor-not-allowed' : 'hover:brightness-110 active:scale-95';

  // Input accept para mobile (câmera só imagens, galeria/arquivo aceita tudo)
  const cameraAccept = 'image/*';
  const fileAccept = accept;

  return (
    <div className="space-y-3">
      {label && <p className="text-sm font-medium text-[#c8ffd8]">{label}</p>}

      {isMobile ? (
        <div className="flex flex-wrap gap-2">
          {/* Câmera - só imagens */}
          <label className={`${base} ${act} text-white border-2 border-[#00ff88]`} style={{ background: '#006633' }}>
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Camera className="w-5 h-5" />}
            Câmera
            <input type="file" accept={cameraAccept} capture="environment" multiple={multiple}
              disabled={disabled} className="hidden" onChange={handleChange} />
          </label>
          {/* Galeria - aceita imagens e documentos */}
          <label className={`${base} ${act} text-[#c8ffd8] border border-[#1a4030]`} style={{ background: '#0a1810' }}>
            <Image className="w-5 h-5" />
            Galeria
            <input type="file" accept={fileAccept} multiple={multiple}
              disabled={disabled} className="hidden" onChange={handleChange} />
          </label>
        </div>
      ) : (
        <label className={`${base} ${act} text-[#c8ffd8] border-2 border-dashed border-[#1a4030]`} style={{ background: '#0a1810' }}>
          {loading ? <Loader2 className="w-5 h-5 animate-spin text-[#00ff88]" /> : <FolderOpen className="w-5 h-5 text-[#00ff88]" />}
          Selecionar Arquivo (PDF, DOCX, JPG, PNG)
          <input type="file" accept={fileAccept} multiple={multiple}
            disabled={disabled} className="hidden" onChange={handleChange} />
        </label>
      )}

      {preview && previews.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {previews.map((p, i) => (
            <div key={i} className="relative rounded-md overflow-hidden flex flex-col items-center justify-center"
              style={{ 
                width: isImage(p.name) ? 80 : 100, 
                height: isImage(p.name) ? 80 : 100, 
                border: '2px solid #00ff88', 
                borderRadius: 6, 
                boxShadow: '0 0 6px #00ff8844',
                background: '#0a1810'
              }}>
              {isImage(p.name) && p.url ? (
                <img src={p.url} alt={p.name} className="w-full h-full object-cover" />
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-2">
                  <span className="text-2xl">{p.icon}</span>
                  <span className="text-[8px] text-[#c8ffd8] truncate max-w-[90px] mt-1">
                    {p.name.length > 15 ? p.name.substring(0, 12) + '...' : p.name}
                  </span>
                </div>
              )}
              <button type="button" onClick={() => removePreview(i)}
                className="absolute top-0.5 right-0.5 bg-red-600 text-white rounded-full p-0.5 hover:bg-red-700">
                <X className="w-3 h-3" />
              </button>
              <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-[9px] text-[#c8ffd8] truncate px-1 py-0.5 text-center">
                {(p.size / 1024).toFixed(0)}KB
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SmartFileInput;
