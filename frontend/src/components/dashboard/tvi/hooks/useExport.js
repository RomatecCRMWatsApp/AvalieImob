import { useState, useCallback } from 'react';
import { tviAPI } from '../../../../lib/api';

export function useExport() {
  const [loading, setLoading] = useState({});

  const setL = (id, key, val) => setLoading(prev => ({ ...prev, [`${id}_${key}`]: val }));

  const exportPdf = useCallback(async (id, filename) => {
    setL(id, 'pdf', true);
    try {
      const blobData = await tviAPI.exportPdf(id);
      const blob = new Blob([blobData], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || `TVI_${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Erro ao exportar PDF. Tente novamente.');
    } finally {
      setL(id, 'pdf', false);
    }
  }, []);

  const exportDocx = useCallback(async (id, filename) => {
    setL(id, 'docx', true);
    try {
      const blobData = await tviAPI.exportDocx(id);
      const blob = new Blob([blobData], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || `TVI_${id}.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Erro ao exportar DOCX. Tente novamente.');
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
