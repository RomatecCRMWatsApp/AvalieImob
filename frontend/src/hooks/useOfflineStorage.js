// @module useOfflineStorage — IndexedDB via idb para vistorias offline (TVI)
import { openDB } from 'idb';
import { useEffect, useCallback, useState } from 'react';
import { tviAPI } from '@/lib/api';

const DB_NAME = 'avalieimob-offline';
const DB_VERSION = 1;
const STORE = 'vistorias-pendentes';

async function getDB() {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, { keyPath: 'localId' });
        store.createIndex('status', 'status');
      }
    },
  });
}

export function useOfflineStorage() {
  const [pendingCount, setPendingCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);

  const refreshCount = useCallback(async () => {
    const db = await getDB();
    const all = await db.getAll(STORE);
    setPendingCount(all.filter((v) => v.status === 'pending').length);
  }, []);

  useEffect(() => {
    refreshCount();

    const handleSync = () => syncPending();
    window.addEventListener('avalieimob:sync-pending', handleSync);
    window.addEventListener('online', handleSync);

    return () => {
      window.removeEventListener('avalieimob:sync-pending', handleSync);
      window.removeEventListener('online', handleSync);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const saveVistoria = useCallback(async (data) => {
    const db = await getDB();
    const localId = `local_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const record = {
      localId,
      status: 'pending',
      createdAt: new Date().toISOString(),
      data,
    };
    await db.put(STORE, record);
    await refreshCount();
    return localId;
  }, [refreshCount]);

  const getPendingVistorias = useCallback(async () => {
    const db = await getDB();
    const all = await db.getAll(STORE);
    return all.filter((v) => v.status === 'pending');
  }, []);

  const markSynced = useCallback(async (localId) => {
    const db = await getDB();
    const record = await db.get(STORE, localId);
    if (record) {
      await db.put(STORE, { ...record, status: 'synced' });
      await refreshCount();
    }
  }, [refreshCount]);

  const syncPending = useCallback(async () => {
    if (!navigator.onLine || isSyncing) return;
    setIsSyncing(true);
    try {
      const pending = await getPendingVistorias();
      for (const item of pending) {
        try {
          await tviAPI.create(item.data);
          await markSynced(item.localId);
        } catch {
          // keep as pending, retry next time
        }
      }
    } finally {
      setIsSyncing(false);
      await refreshCount();
    }
  }, [getPendingVistorias, markSynced, isSyncing, refreshCount]);

  return {
    saveVistoria,
    getPendingVistorias,
    syncPending,
    pendingCount,
    isSyncing,
  };
}
