// @hook useDocumentoUpload — upload de documentos do imóvel (PDF convertido p/ TIFF no backend)
import { useState, useCallback } from 'react';
import { api, API_BASE } from '../lib/api';

/**
 * Upload de um documento anexo de imóvel. O backend converte PDFs automaticamente
 * em TIFF 300 DPI (uma página por arquivo) + JPEG de preview; imagens diretas
 * (JPG/PNG/WebP) e fotografias são armazenadas sem conversão.
 *
 * @param {string} imovelId  id do imóvel (collection properties)
 */
export function useDocumentoUpload(imovelId) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * @param {string} tipo  chave do documento (ex.: 'ccir', 'matricula', 'fotografias')
   * @param {File}   file  arquivo selecionado
   * @returns {Promise<object|null>} DocumentoAnexo retornado pelo backend, ou null em erro
   */
  const upload = useCallback(async (tipo, file) => {
    setLoading(true);
    setError(null);
    const form = new FormData();
    form.append('file', file);
    try {
      const { data } = await api.post(
        `/imoveis/${imovelId}/documentos/${tipo}`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      return data; // { id, paginas, convertido, arquivos_preview, arquivos_tiff, ... }
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.message || 'Erro no upload.';
      setError(detail);
      return null;
    } finally {
      setLoading(false);
    }
  }, [imovelId]);

  const remove = useCallback(async (tipo, documentoId) => {
    setError(null);
    try {
      await api.delete(`/imoveis/${imovelId}/documentos/${tipo}/${documentoId}`);
      return true;
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Erro ao remover.');
      return false;
    }
  }, [imovelId]);

  // URLs de leitura (token vai no header via interceptor do axios; para <img> use o
  // endpoint com o axios/blob se precisar de auth — o GET exige assinatura ativa).
  const arquivoUrl = useCallback((tipo, documentoId, kind = 'preview', pagina = 1) =>
    `${API_BASE}/imoveis/${imovelId}/documentos/${tipo}/${documentoId}/arquivo?kind=${kind}&pagina=${pagina}`,
  [imovelId]);

  return { upload, remove, arquivoUrl, loading, error };
}

export default useDocumentoUpload;
