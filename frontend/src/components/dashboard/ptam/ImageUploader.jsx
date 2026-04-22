// @module ImageUploader — reutilizável; mobile usa SmartPhotoInput, desktop usa drop zone
import React, { useRef, useState } from 'react';
import { Upload, X, Loader2, Image as ImageIcon, FileText } from 'lucide-react';
import { uploadAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { useIsMobile } from '../../../hooks/useIsMobile';
import SmartPhotoInput from '../../shared/SmartPhotoInput';

const ImageUploader = ({
  images = [],
  onImagesChange,
  maxImages = 20,
  label = 'Fotos',
  accept = 'image/jpeg,image/jpg,image/png,image/webp,application/pdf',
  single = false,
}) => {
  const { toast } = useToast();
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [contentTypes, setContentTypes] = useState({});
  const isMobile = useIsMobile();

  const canAdd = single ? images.length === 0 : images.length < maxImages;
  const isPdf = (id) => contentTypes[id] === 'application/pdf';

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    const fileList = Array.from(files);
    const remaining = single ? 1 : maxImages - images.length;
    const toUpload = fileList.slice(0, remaining);
    if (!toUpload.length) {
      toast({ title: `Limite de ${single ? 1 : maxImages} imagem(ns) atingido`, variant: 'destructive' });
      return;
    }
    setUploading(true);
    const newIds = [];
    const newTypes = {};
    for (const file of toUpload) {
      if (file.size > 5 * 1024 * 1024) {
        toast({ title: 'Arquivo muito grande. Máximo: 5MB', variant: 'destructive' });
        continue;
      }
      try {
        const res = await uploadAPI.uploadImage(file);
        newIds.push(res.id);
        if (res.content_type) newTypes[res.id] = res.content_type;
      } catch (err) {
        toast({ title: err.response?.data?.detail || 'Erro ao enviar imagem', variant: 'destructive' });
      }
    }
    setUploading(false);
    if (newIds.length > 0) {
      setContentTypes((prev) => ({ ...prev, ...newTypes }));
      onImagesChange(single ? newIds : [...images, ...newIds]);
    }
  };

  const handleRemove = async (imageId) => {
    try { await uploadAPI.deleteImage(imageId); } catch { /* silent */ }
    setContentTypes((prev) => { const n = { ...prev }; delete n[imageId]; return n; });
    onImagesChange(images.filter((id) => id !== imageId));
  };

  // Mobile: SmartPhotoInput lida com câmera/galeria; nós recebemos File[] e fazemos upload
  if (isMobile && canAdd) {
    return (
      <div className="space-y-3">
        {uploading && (
          <div className="flex items-center gap-2 text-sm text-[#00ff88]">
            <Loader2 className="w-4 h-4 animate-spin" /> Enviando...
          </div>
        )}
        <SmartPhotoInput
          label={label && `${label}${!single ? ` (${images.length}/${maxImages})` : ''}`}
          multiple={!single}
          preview={false}
          onPhotos={(files) => handleFiles(files)}
          onPhoto={(file) => handleFiles([file])}
        />
        {images.length > 0 && (
          <div className="grid grid-cols-3 gap-2">
            {images.map((id) => (
              <div key={id} className="relative group rounded-lg overflow-hidden border border-[#00ff88] aspect-square bg-[#0a1810]">
                {isPdf(id) ? (
                  <div className="w-full h-full flex flex-col items-center justify-center gap-1 bg-red-950">
                    <FileText className="w-7 h-7 text-red-400" /><span className="text-xs text-red-400">PDF</span>
                  </div>
                ) : (
                  <img src={uploadAPI.getImageUrl(id)} alt="uploaded" className="w-full h-full object-cover" />
                )}
                <button type="button" onClick={() => handleRemove(id)}
                  className="absolute top-1 right-1 w-6 h-6 bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition hover:bg-red-700">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Desktop: comportamento original (drag & drop)
  return (
    <div className="space-y-3">
      {label && (
        <div className="flex items-center justify-between">
          <label className="block text-sm font-medium text-gray-700">{label}</label>
          {!single && <span className="text-xs text-gray-400">{images.length}/{maxImages}</span>}
        </div>
      )}
      {canAdd && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
          onClick={() => inputRef.current?.click()}
          className={`flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 border-dashed cursor-pointer transition ${dragging ? 'border-emerald-500 bg-emerald-50' : 'border-emerald-200 bg-emerald-50/40 hover:bg-emerald-50 hover:border-emerald-400'}`}
        >
          {uploading ? <Loader2 className="w-6 h-6 animate-spin text-emerald-700" /> : <Upload className="w-6 h-6 text-emerald-700" />}
          <span className="text-sm text-emerald-800 font-medium">
            {uploading ? 'Enviando...' : single ? 'Clique ou arraste uma foto' : `Clique ou arraste${images.length > 0 ? ' mais fotos' : ' fotos'}`}
          </span>
          <span className="text-xs text-gray-500">JPG, PNG, WebP ou PDF — máx 5 MB</span>
          <input ref={inputRef} type="file" accept={accept} multiple={!single} className="hidden"
            onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }} />
        </div>
      )}
      {images.length > 0 && (
        <div className={`grid gap-2 ${single ? 'grid-cols-1' : 'grid-cols-3 sm:grid-cols-4 md:grid-cols-5'}`}>
          {images.map((id) => (
            <div key={id} className={`relative group rounded-lg overflow-hidden border border-gray-200 bg-gray-50 ${single ? 'h-40' : 'aspect-square'}`}>
              {isPdf(id) ? (
                <div className="w-full h-full flex flex-col items-center justify-center gap-1 bg-red-50">
                  <FileText className="w-8 h-8 text-red-500" /><span className="text-xs text-red-600 font-medium">PDF</span>
                </div>
              ) : (
                <>
                  <img src={uploadAPI.getImageUrl(id)} alt="uploaded" className="w-full h-full object-cover"
                    onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }} />
                  <div className="hidden w-full h-full items-center justify-center"><ImageIcon className="w-6 h-6 text-gray-400" /></div>
                </>
              )}
              <button type="button" onClick={() => handleRemove(id)}
                className="absolute top-1 right-1 w-6 h-6 bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition hover:bg-red-700">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ImageUploader;
