// @module ptam/PtamPreviewAoVivo — preview ao vivo do PDF do PTAM (debounce + iframe).
import React, { useState, useEffect, useRef } from 'react';
import { ptamAPI } from '../../../lib/api';

export default function PtamPreviewAoVivo({ form }) {
  const [pdfUrl, setPdfUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState(null);
  const debounceRef = useRef();
  const urlRef = useRef(null);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(gerar, 900);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form]);

  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  const gerar = async () => {
    setLoading(true);
    setErro(null);
    try {
      const blob = await ptamAPI.previewPdf(form);
      const url = URL.createObjectURL(blob);
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      urlRef.current = url;
      setPdfUrl(url);
    } catch (e) {
      setErro('Não foi possível gerar o preview.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: '#14241a', borderRadius: 12, overflow: 'hidden',
      border: '1px solid rgba(76,175,80,0.18)',
    }}>
      <div style={{
        padding: '10px 16px', borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ fontSize: 14 }}>📄</span>
        <span style={{
          fontSize: 11, fontWeight: 600, color: '#B8860B',
          letterSpacing: '0.8px', textTransform: 'uppercase',
        }}>
          Preview do Laudo
        </span>
        {loading && (
          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
            ↻ Atualizando…
          </span>
        )}
      </div>

      <div style={{ flex: 1, position: 'relative', background: '#f5f5f0', minHeight: 360 }}>
        {!pdfUrl && !loading && !erro && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', color: '#888', gap: 8,
          }}>
            <span style={{ fontSize: 30 }}>⏳</span>
            <span style={{ fontSize: 13 }}>Preencha os campos pra ver o preview</span>
          </div>
        )}
        {erro && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
            justifyContent: 'center', color: '#c0392b', fontSize: 13, padding: 16, textAlign: 'center',
          }}>
            {erro}
          </div>
        )}
        {pdfUrl && (
          <iframe
            src={pdfUrl}
            style={{ width: '100%', height: '100%', border: 'none' }}
            title="Preview do PTAM"
          />
        )}
      </div>

      <div style={{
        padding: '7px 14px', borderTop: '1px solid rgba(255,255,255,0.06)',
        fontSize: 10.5, color: 'rgba(255,255,255,0.32)', textAlign: 'center',
      }}>
        Atualiza automaticamente enquanto você preenche — é o PDF que será gerado.
      </div>
    </div>
  );
}
