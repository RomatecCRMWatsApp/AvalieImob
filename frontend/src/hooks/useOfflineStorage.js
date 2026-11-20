// @module useOfflineStorage — estado da fila de vistorias do aparelho (ver lib/filaOffline).
import { useEffect, useCallback, useState } from 'react';
import {
  listar, enfileirar, sincronizar, tentarDeNovo, remover, estaSincronizando,
} from '@/lib/filaOffline';

export function useOfflineStorage() {
  const [itens, setItens] = useState([]);
  const [isSyncing, setIsSyncing] = useState(estaSincronizando());

  const atualizar = useCallback(async () => {
    try {
      const lista = await listar();
      lista.sort((a, b) => (b.criadoEm || '').localeCompare(a.criadoEm || ''));
      setItens(lista);
    } catch {
      setItens([]);
    }
    setIsSyncing(estaSincronizando());
  }, []);

  useEffect(() => {
    atualizar();
    // ao abrir a tela com internet, tenta mandar o que ficou pendente
    if (navigator.onLine) sincronizar();
    const aoMudar = () => atualizar();
    const aoIniciar = () => setIsSyncing(true);
    const aoVoltarRede = () => sincronizar();
    window.addEventListener('avalieimob:fila-mudou', aoMudar);
    window.addEventListener('avalieimob:fila-sincronizando', aoIniciar);
    window.addEventListener('online', aoVoltarRede);
    return () => {
      window.removeEventListener('avalieimob:fila-mudou', aoMudar);
      window.removeEventListener('avalieimob:fila-sincronizando', aoIniciar);
      window.removeEventListener('online', aoVoltarRede);
    };
  }, [atualizar]);

  return {
    itens,
    pendingCount: itens.filter((i) => i.status === 'pendente').length,
    falhasCount: itens.filter((i) => i.status === 'falhou').length,
    isSyncing,
    enfileirar,
    syncPending: sincronizar,
    tentarDeNovo,
    descartar: async (localId) => { await remover(localId); atualizar(); },
  };
}
