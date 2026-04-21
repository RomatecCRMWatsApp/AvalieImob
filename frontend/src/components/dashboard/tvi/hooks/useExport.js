import { useState, useCallback } from 'react';
import { tviAPI } from '../../../../lib/api';

export function useExport() {
  const [loading, setLoading] = useState({});

  const setL = (id, key, val) => setLoading(prev => ({ ...prev, [`${id}_${key}`]: val }));

  const exportPdf = useCallback(async (id, filename) => {
    setL(id, 'pdf', true);
    try {
      // endpoint futuro: GET /api/tvi/vistoria/{id}/pdf
      const res = await tviAPI.get(`${id}/pdf`);
      const blob = new Blob([res], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || `TVI_${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Exportação PDF ainda não disponível.');
    } finally {
      setL(id, 'pdf', false);
    }
  }, []);

  const exportDocx = useCallback(async (id, filename) => {
    setL(id, 'docx', true);
    try {
      alert('Exportação DOCX em breve.');
    } finally {
      setL(id, 'docx', false);
    }
  }, []);

  const shareWhatsApp = useCallback((vistoria) => {
    const txt = encodeURIComponent(
      `TVI — ${vistoria.titulo || vistoria.id}\nModelo: ${vistoria.modelo_nome || ''}`
    );
    window.open(`https://wa.me/?text=${txt}`, '_blank');
  }, []);

  const shareEmail = useCallback((vistoria) => {
    const sub = encodeURIComponent(`TVI — ${vistoria.titulo || vistoria.id}`);
    const body = encodeURIComponent(`Vistoria: ${vistoria.titulo || vistoria.id}`);
    window.open(`mailto:?subject=${sub}&body=${body}`, '_blank');
  }, []);

  return { loading, exportPdf, exportDocx, shareWhatsApp, shareEmail };
}
