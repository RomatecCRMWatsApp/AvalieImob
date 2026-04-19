import React, { useRef, useState } from 'react';
import { Upload, X, Loader2, Image as ImageIcon, FileText } from 'lucide-react';
import { uploadAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

/**
 * ImageUploader — componente reutilizável de upload de imagens.
 *
 * Props:
 *  - images: string[]     → array de IDs das imagens já salvas
 *  - onImagesChange: fn   → callback(newIds: string[])
 *  - maxImages: number    → limite de imagens (padrão 20)
 *  - label: string        → rótulo da seção
 *  - accept: string       → tipos aceitos (padrão image/*)
 *  - single: bool         → se true, aceita apenas 1 imagem (substitui)
 */
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
  // Tracks content_type per id so we can render PDF icon vs image thumbnail
  const [contentTypes, setContentTypes] = useState({});

  const canAdd = single ? images.length === 0 : images.length < maxImages;
  const isPdf = (imageId) => contentTypes[imageId] === 'application/pdf';

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;

    const fileList = Array.from(files);
    const remaining = single ? 1 : maxImages - images.length;
    const toUpload = fileList.slice(0, remaining);

    if (toUpload.length === 0) {
      toast({ title: `Limite de ${single ? 1 : maxImages} imagem(ns) atingido`, variant: 'destructive' });
      return;
    }

    setUploading(true);
    const newIds = [];
    const newTypes = {};
    for (const file of toUpload) {
      if (file.size > 5 * 1024 * 1024) {
        toast({ title: `Arquivo "${file.name}" muito grande (máx 5 MB)`, variant: 'destructive' });
        continue;
      }
      try {
        const res = await uploadAPI.uploadImage(file);
        newIds.push(res.id);
        if (res.content_type) newTypes[res.id] = res.content_type;
      } catch (err) {
        const detail = err.response?.data?.detail || 'Erro ao enviar imagem';
        toast({ title: detail, variant: 'destructive' });
      }
    }
    setUploading(false);

    if (newIds.length > 0) {
      setContentTypes((prev) => ({ ...prev, ...newTypes }));
      const updated = single ? newIds : [...images, ...newIds];
      onImagesChange(updated);
    }
  };

  const handleInputChange = (e) => {
    handleFiles(e.target.files);
    e.target.value = '';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleRemove = async (imageId) => {
    try {
      await uploadAPI.deleteImage(imageId);
    } catch {
      // silent — remove from UI even if API fails
    }
    setContentTypes((prev) => {
      const next = { ...prev };
      delete next[imageId];
      return next;
    });
    onImagesChange(images.filter((id) => id !== imageId));
  };

  return (
    <div className="space-y-3">
      {label && (
        <div className="flex items-center justify-between">
          <label className="block text-sm font-medium text-gray-700">{label}</label>
          {!single && (
            <span className="text-xs text-gray-400">{images.length}/{maxImages}</span>
          )}
        </div>
      )}

      {/* Drop zone / upload button */}
      {canAdd && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`
            flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 border-dashed cursor-pointer transition
            ${dragging
              ? 'border-emerald-500 bg-emerald-50'
              : 'border-emerald-200 bg-emerald-50/40 hover:bg-emerald-50 hover:border-emerald-400'}
          `}
        >
          {uploading ? (
            <Loader2 className="w-6 h-6 animate-spin text-emerald-700" />
          ) : (
            <Upload className="w-6 h-6 text-emerald-700" />
          )}
          <span className="text-sm text-emerald-800 font-medium">
            {uploading
              ? 'Enviando...'
              : single
              ? 'Clique ou arraste uma foto'
              : `Clique ou arraste${images.length > 0 ? ' mais fotos' : ' fotos'}`}
          </span>
          <span className="text-xs text-gray-500">JPG, PNG, WebP ou PDF — máx 5 MB por arquivo</span>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            multiple={!single}
            className="hidden"
            onChange={handleInputChange}
          />
        </div>
      )}

      {/* Thumbnails grid */}
      {images.length > 0 && (
        <div className={`grid gap-2 ${single ? 'grid-cols-1' : 'grid-cols-3 sm:grid-cols-4 md:grid-cols-5'}`}>
          {images.map((imageId) => (
            <div
              key={imageId}
              className={`relative group rounded-lg overflow-hidden border border-gray-200 bg-gray-50 ${single ? 'h-40' : 'aspect-square'}`}
            >
              {isPdf(imageId) ? (
                /* PDF card */
                <div className="w-full h-full flex flex-col items-center justify-center gap-1 bg-red-50">
                  <FileText className="w-8 h-8 text-red-500" />
                  <span className="text-xs text-red-600 font-medium">PDF</span>
                </div>
              ) : (
                /* Image thumbnail */
                <>
                  <img
                    src={uploadAPI.getImageUrl(imageId)}
                    alt="uploaded"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                  />
                  <div className="hidden w-full h-full items-center justify-center">
                    <ImageIcon className="w-6 h-6 text-gray-400" />
                  </div>
                </>
              )}
              <button
                type="button"
                onClick={() => handleRemove(imageId)}
                className="absolute top-1 right-1 w-6 h-6 bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition hover:bg-red-700"
                title="Remover"
              >
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
