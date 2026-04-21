// @module OfflineBadge — indicador online/offline e pendentes de sync no header
import React, { useState, useEffect } from 'react';
import { WifiOff, Wifi, RefreshCw } from 'lucide-react';
import { useOfflineStorage } from '@/hooks/useOfflineStorage';

const OfflineBadge = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const { pendingCount, isSyncing, syncPending } = useOfflineStorage();

  useEffect(() => {
    const goOnline = () => setIsOnline(true);
    const goOffline = () => setIsOnline(false);
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);

  if (isOnline && pendingCount === 0) return null;

  return (
    <div className="flex items-center gap-2">
      {!isOnline && (
        <span className="flex items-center gap-1 bg-red-100 text-red-700 text-xs px-2 py-1 rounded-full font-medium">
          <WifiOff className="w-3 h-3" />
          Offline
        </span>
      )}
      {pendingCount > 0 && (
        <button
          onClick={syncPending}
          disabled={isSyncing || !isOnline}
          className="flex items-center gap-1 bg-amber-100 text-amber-800 text-xs px-2 py-1 rounded-full font-medium hover:bg-amber-200 disabled:opacity-60 transition-colors"
          title="Sincronizar vistorias pendentes"
        >
          <RefreshCw className={`w-3 h-3 ${isSyncing ? 'animate-spin' : ''}`} />
          {pendingCount} {pendingCount === 1 ? 'pendente' : 'pendentes'}
          {isOnline && !isSyncing && ' · Sincronizar'}
        </button>
      )}
      {isOnline && pendingCount > 0 && (
        <span className="flex items-center gap-1 text-emerald-700 text-xs">
          <Wifi className="w-3 h-3" /> Online
        </span>
      )}
    </div>
  );
};

export default OfflineBadge;
