// @module hooks/useSyncAmostras — Sincronização silenciosa das amostras do PTAM
// com o Banco Global de Amostras (repositório de paradigmas).
//
// O backend já sincroniza automaticamente no save do PTAM (best-effort). Este hook
// é uma camada extra opcional disparada pelo wizard logo após o PUT/POST, garantindo
// reflexo imediato mesmo se o save retornar antes de o hook backend concluir.
import { useCallback } from 'react';
import { amostrasAPI } from '../lib/api';

export const useSyncAmostras = () => {
  const syncAmostras = useCallback(async (ptamId) => {
    if (!ptamId) return;
    try {
      await amostrasAPI.syncPtam(ptamId);
      // Silencioso por design — não polui a UX com toast de sucesso.
    } catch (err) {
      console.warn('[AvalieImob] Sync amostras falhou silenciosamente:', err);
    }
  }, []);

  return { syncAmostras };
};

export default useSyncAmostras;
