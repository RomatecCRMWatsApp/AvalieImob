// @module ptam/FotosLaudo — Adaptador entre o estado do laudo (IDs de imagem) e o
// PhotoGrid (objetos {url, legenda, gps}). Mantém legenda por foto e faz o upload.
import React, { useCallback } from 'react';
import { uploadAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import PhotoGrid from './PhotoGrid';

// IDs (string) OU objetos {image_id, legenda, gps} -> objetos do PhotoGrid.
function toPhotos(list) {
  return (list || []).map((f) => {
    if (typeof f === 'string') {
      return { image_id: f, url: uploadAPI.getImageUrl(f), legenda: '', gps: false };
    }
    const id = f.image_id || f.id || '';
    return {
      image_id: id,
      url: f.url || (id ? uploadAPI.getImageUrl(id) : ''),
      legenda: f.legenda || '',
      gps: !!f.gps,
    };
  });
}

// PhotoGrid -> formato persistido no laudo (objeto enxuto com legenda).
function toStored(photos) {
  return (photos || []).map((p) => ({
    image_id: p.image_id,
    legenda: p.legenda || '',
    gps: !!p.gps,
  }));
}

export default function FotosLaudo({ value, onChange, maxImages = 50 }) {
  const { toast } = useToast();
  const photos = toPhotos(value);

  const handleChange = useCallback((next) => {
    onChange(toStored(next));
  }, [onChange]);

  const handleUpload = useCallback(async (files) => {
    const atuais = toPhotos(value);
    const espaco = maxImages - atuais.length;
    if (espaco <= 0) {
      toast({ title: `Limite de ${maxImages} fotos atingido`, variant: 'destructive' });
      return;
    }
    const novos = [];
    for (const file of Array.from(files).slice(0, espaco)) {
      if (file.size > 5 * 1024 * 1024) {
        toast({ title: 'Arquivo muito grande (máx 5MB)', variant: 'destructive' });
        continue;
      }
      try {
        const res = await uploadAPI.uploadImage(file);
        const pages = Array.isArray(res.pages) && res.pages.length
          ? res.pages
          : [{ id: res.id }];
        for (const pg of pages) {
          if (pg && pg.id) novos.push({ image_id: pg.id, legenda: '', gps: false });
        }
      } catch (e) {
        toast({ title: 'Erro ao enviar foto', variant: 'destructive' });
      }
    }
    if (novos.length) {
      onChange([...toStored(atuais), ...novos]);
    }
  }, [value, onChange, maxImages, toast]);

  return <PhotoGrid photos={photos} onChange={handleChange} onUpload={handleUpload} />;
}
