// @module ptam/FotosLaudo — Adaptador entre o estado do laudo (IDs de imagem) e o
// PhotoGrid (objetos {url, legenda, gps}). Mantém legenda por foto e faz o upload.
// O badge GPS é display-only (buscado do EXIF via metadata); o PDF recalcula o GPS.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { uploadAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import PhotoGrid from './PhotoGrid';

// IDs (string) OU objetos {image_id, legenda} -> dados base (sem gps).
function baseList(list) {
  return (list || []).map((f) => {
    if (typeof f === 'string') {
      return { image_id: f, legenda: '' };
    }
    return { image_id: f.image_id || f.id || '', legenda: f.legenda || '' };
  });
}

// Formato persistido no laudo (objeto enxuto). gps é recalculado no PDF.
function toStored(items) {
  return (items || []).map((p) => ({ image_id: p.image_id, legenda: p.legenda || '' }));
}

export default function FotosLaudo({ value, onChange, maxImages = 50 }) {
  const { toast } = useToast();
  const base = baseList(value);
  // gpsMap: image_id -> bool (tem GPS/EXIF). Display-only, não persiste.
  const [gpsMap, setGpsMap] = useState({});
  const checkedRef = useRef(new Set());

  // Busca metadata (GPS/EXIF) das fotos ainda não verificadas — só para o badge.
  useEffect(() => {
    let cancel = false;
    (async () => {
      for (const f of base) {
        const id = f.image_id;
        if (!id || checkedRef.current.has(id)) continue;
        checkedRef.current.add(id);
        try {
          const m = await uploadAPI.imageMetadata(id);
          if (cancel) return;
          if (m && (m.tem_dados || m.tem_gps || m.gps)) {
            setGpsMap((prev) => ({ ...prev, [id]: true }));
          }
        } catch {
          /* sem metadata — segue sem badge */
        }
      }
    })();
    return () => { cancel = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [base.map((f) => f.image_id).join(',')]);

  const photos = base.map((f) => ({
    image_id: f.image_id,
    url: f.image_id ? uploadAPI.getImageUrl(f.image_id) : '',
    legenda: f.legenda || '',
    gps: !!gpsMap[f.image_id],
  }));

  const handleChange = useCallback((next) => {
    onChange(toStored(next));
  }, [onChange]);

  const handleUpload = useCallback(async (files) => {
    const atuais = baseList(value);
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
          if (pg && pg.id) novos.push({ image_id: pg.id, legenda: '' });
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
